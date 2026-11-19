# Shortly deployment guide

## Architecture

The Flask application serves both the static Shortly frontend and its API, and handles short-link redirects. Railway PostgreSQL is the permanent store; Redis is an optional cache. This keeps deployment to one Railway web service plus the PostgreSQL and Redis services. A separate static service would require another public API origin and CORS configuration without adding value for this small frontend.

Railway should deploy the repository root `Dockerfile`. The image includes `app/` and `frontend/`; Gunicorn binds to Railway's `PORT`. Docker Compose uses the same Dockerfile pattern for local development.

## Local development

Install Docker Desktop, then from the repository root run:

```sh
docker compose up --build
```

Open http://localhost:5000. The compose setup persists PostgreSQL data in `postgres_data`, and the frontend and API share the Flask origin. Stop services with `docker compose down`; the named database volume remains. Do not remove that volume if you need its records.

The sample `.env.example` documents the application settings. Compose supplies its local PostgreSQL and Redis host settings directly. To run Flask outside Docker, install `app/requirements.txt` and set `POSTGRES_HOST=localhost`, `REDIS_HOST=localhost`, and `PUBLIC_BASE_URL=http://localhost:5000`.

## Environment variables

| Variable | Purpose | Railway service | Example (no secrets) | Required |
| --- | --- | --- | --- | --- |
| `DATABASE_URL` | PostgreSQL connection string; use Railway's PostgreSQL reference variable | Backend | `${{Postgres.DATABASE_URL}}` | Yes |
| `REDIS_URL` | Redis-compatible cache connection string; use Railway's Redis reference variable | Backend | `${{Redis.REDIS_URL}}` | Recommended; redirects fall back to PostgreSQL if cache is offline |
| `PUBLIC_BASE_URL` | Origin used to create shareable short links | Backend | `https://shortly.up.railway.app` | Yes in production |
| `FRONTEND_URL` | Allowed browser origin(s) for cross-origin API use | Backend | `https://shortly-frontend.up.railway.app` | Optional; same-origin frontend needs no CORS |
| `PORT` | HTTP listen port supplied by Railway | Backend | Supplied by Railway | Railway managed |
| `PGSSLMODE` | Optional PostgreSQL SSL mode override | Backend | `require` | Optional; set only if the provider requires it |

`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `REDIS_HOST`, `REDIS_PORT`, and `REDIS_PASSWORD` are local fallback settings. Railway deployments should use `DATABASE_URL` and `REDIS_URL` instead. Never place real credentials in this repository or frontend files.

## Railway setup and deployment

1. Create one Railway project and add PostgreSQL and Redis services. Wait until each service is ready.
2. Add a backend service from this GitHub repository, using the repository root as its build context. Railway should detect the root `Dockerfile`. No deployment has been performed from this workspace.
3. In the backend service variables, set `DATABASE_URL` and `REDIS_URL` using Railway's service reference variables, and set `PUBLIC_BASE_URL` to the eventual backend public URL. Railway supplies `PORT`.
4. Generate the backend public domain in Railway. The requested `https://shortly.up.railway.app` is only a desired name; Railway must confirm it is available. If not, use the domain Railway assigns. Set `PUBLIC_BASE_URL` to that confirmed HTTPS origin and redeploy.
5. The backend domain serves the frontend at `/`, the API at `/shorten` (also `/api/shorten`), health at `/health`, and redirects at `/<alias>`. Set `FRONTEND_URL` only if you later host the frontend on a different origin; list the exact HTTPS origin(s), comma separated.
6. Visit the root page and `/health`, shorten a URL with and without a custom alias, and open each short link. Confirm generated links use the backend domain and HTTPS.

The frontend and short-link domain are the same origin in this minimal deployment. If you later split the frontend, configure its build-time `API_BASE_URL` to the backend origin, set backend `FRONTEND_URL` to the frontend's exact origin, and keep `PUBLIC_BASE_URL` set to the backend domain.

## Database compatibility

At first application use, the backend runs additive, idempotent SQL to add `urls.alias` and its unique index. Existing rows receive their former base62 ID paths as aliases, so existing links remain valid. `app/init.sql` contains the same additive migration for fresh local databases. Railway does not automatically execute `init.sql`; the application performs this safe migration when needed. No records are dropped.

## Manual updates and rollback

Push code changes to GitHub only when you choose; Railway can then build and deploy the repository's root Dockerfile. Alternatively use Railway's manual redeploy controls. To change the public short-link domain later, update `PUBLIC_BASE_URL` and redeploy. Existing aliases do not change, but their displayed origin will reflect the value used when each link was created. Back up PostgreSQL before any future schema changes.

## Pre-publish checklist

- [ ] Railway generated and confirmed the backend domain; it is set as `PUBLIC_BASE_URL`.
- [ ] `DATABASE_URL` and `REDIS_URL` reference the intended Railway services.
- [ ] `/health` returns healthy and the root page loads over HTTPS.
- [ ] Automatic and custom aliases work; duplicate and reserved aliases show clear errors.
- [ ] Redirects work after cache miss and with Redis temporarily unavailable.
- [ ] `FRONTEND_URL` is exact if the frontend uses a separate origin.
- [ ] No secrets are committed, and the Railway PostgreSQL service has a backup plan.
