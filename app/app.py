import logging
import os
import re
import secrets
import string
from contextlib import contextmanager
from urllib.parse import urlsplit

import psycopg2
import redis
from flask import Flask, jsonify, redirect, request, send_from_directory
from psycopg2 import errors
from werkzeug.middleware.proxy_fix import ProxyFix
from url_utils import build_short_url

ROOT = os.path.dirname(os.path.dirname(__file__))
FRONTEND = os.path.join(ROOT, "frontend")
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.logger.setLevel(logging.INFO)
ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase
ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{1,30}$")
RESERVED = {"", "api", "health", "shorten", "favicon.ico", "robots.txt", "static"}
_schema_ready = False


def get_db():
    url = os.getenv("DATABASE_URL")
    if url:
        options = {"sslmode": os.environ["PGSSLMODE"]} if os.getenv("PGSSLMODE") else {}
        return psycopg2.connect(url, **options)
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "db"), port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "urlshortener"), user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"), sslmode=os.getenv("POSTGRES_SSLMODE", "prefer"),
    )


def create_cache():
    if os.getenv("REDIS_URL"):
        return redis.from_url(os.environ["REDIS_URL"], decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
    return redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=int(os.getenv("REDIS_PORT", 6379)),
                       password=os.getenv("REDIS_PASSWORD") or None, decode_responses=True,
                       socket_connect_timeout=1, socket_timeout=1)


cache = create_cache()


@contextmanager
def db_session():
    conn = get_db()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def ensure_schema():
    global _schema_ready
    if _schema_ready:
        return
    with db_session() as conn, conn.cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS urls (
            id SERIAL PRIMARY KEY, long_url TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("ALTER TABLE urls ADD COLUMN IF NOT EXISTS alias VARCHAR(30)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS urls_alias_unique ON urls(alias) WHERE alias IS NOT NULL")
        # Preserve pre-migration links by reserving each existing ID's old base62 path.
        cur.execute("SELECT id FROM urls WHERE alias IS NULL ORDER BY id")
        for (record_id,) in cur.fetchall():
            cur.execute("UPDATE urls SET alias = %s WHERE id = %s AND alias IS NULL", (base62_encode(record_id), record_id))
    _schema_ready = True


def base62_encode(num):
    if num == 0:
        return ALPHABET[0]
    out = ""
    while num:
        num, remainder = divmod(num, 62)
        out = ALPHABET[remainder] + out
    return out


def base62_decode(code):
    value = 0
    for char in code:
        if char not in ALPHABET:
            raise ValueError("Invalid short code")
        value = value * 62 + ALPHABET.index(char)
    return value


def valid_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return False
    try:
        parts = urlsplit(value.strip())
        return parts.scheme in {"http", "https"} and bool(parts.hostname)
    except ValueError:
        return False


def cache_get(alias):
    try:
        return cache.get("url:" + alias)
    except redis.RedisError:
        app.logger.warning("Redis lookup failed; using PostgreSQL")
        return None


def cache_set(alias, url):
    try:
        cache.setex("url:" + alias, 86400, url)
    except redis.RedisError:
        app.logger.warning("Redis write failed; continuing without cache")


@app.get("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.get("/<path:asset>")
def frontend_asset(asset):
    if asset in {"app.js", "config.js", "styles.css"}:
        return send_from_directory(FRONTEND, asset)
    return redirect_url(asset)


def shorten():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not valid_url(data.get("url")):
        return jsonify({"error": "Enter a valid http or https URL."}), 400
    requested = data.get("custom_alias", data.get("alias", ""))
    if requested is None:
        requested = ""
    if not isinstance(requested, str):
        return jsonify({"error": "Custom alias must be text."}), 400
    alias = requested.strip()
    if alias and (not ALIAS_RE.fullmatch(alias) or alias.lower() in RESERVED):
        return jsonify({"error": "Alias must be 1–30 letters, numbers, hyphens or underscores and cannot be a reserved path."}), 400
    ensure_schema()
    try:
        with db_session() as conn, conn.cursor() as cur:
            if alias:
                cur.execute("INSERT INTO urls (long_url, alias) VALUES (%s, %s) RETURNING id", (data["url"].strip(), alias))
                url_id = cur.fetchone()[0]
            else:
                # Random aliases avoid exposing record counts; the unique index handles simultaneous requests.
                for _ in range(5):
                    alias = "".join(secrets.choice(ALPHABET) for _ in range(6))
                    cur.execute("INSERT INTO urls (long_url, alias) VALUES (%s, %s) ON CONFLICT (alias) WHERE alias IS NOT NULL DO NOTHING RETURNING id", (data["url"].strip(), alias))
                    row = cur.fetchone()
                    if row:
                        url_id = row[0]
                        break
                else:
                    return jsonify({"error": "Could not generate an available alias. Try again."}), 503
    except errors.UniqueViolation:
        return jsonify({"error": "That custom alias is already taken. Choose another."}), 409
    cache_set(alias, data["url"].strip())
    public_base = os.getenv("PUBLIC_BASE_URL", "").strip()
    if not public_base:
        # Local development fallback only. Production setup must provide PUBLIC_BASE_URL.
        public_base = request.host_url
    return jsonify({"short_url": build_short_url(public_base, alias), "alias": alias, "short_code": alias}), 201


app.add_url_rule("/shorten", "shorten_url", shorten, methods=["POST"])
app.add_url_rule("/api/shorten", "api_shorten_url", shorten, methods=["POST"])


@app.get("/health")
def health():
    return jsonify({"status": "healthy"})


def redirect_url(alias):
    if alias.lower() in RESERVED:
        return jsonify({"error": "Short URL not found"}), 404
    target = cache_get(alias)
    if not target:
        try:
            ensure_schema()
            with db_session() as conn, conn.cursor() as cur:
                cur.execute("SELECT long_url FROM urls WHERE alias = %s", (alias,))
                row = cur.fetchone()
            if not row:
                return jsonify({"error": "Short URL not found"}), 404
            target = row[0]
            cache_set(alias, target)
        except Exception:
            app.logger.exception("Redirect lookup failed")
            return jsonify({"error": "Short link is temporarily unavailable."}), 503
    return redirect(target, code=302)


@app.errorhandler(500)
def internal_error(_error):
    return jsonify({"error": "An internal error occurred."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
