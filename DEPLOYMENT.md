# Shortly deployment

## Local Docker Compose

Install Docker Desktop. From the repository root run:

```sh
docker compose up --build
```

Open http://localhost:5000. Flask serves the frontend, API, redirects, and `/health` from the same origin. Compose starts PostgreSQL and Redis first and waits for their health checks. PostgreSQL data persists in the named `postgres_data` volume. `docker compose down` stops the containers and preserves that volume. Do not remove the volume if you need its records.

## Railway services

Create one Railway project with three services:

1. PostgreSQL.
2. Redis.
3. Shortly backend, connected to this GitHub repository.

Set the backend service's build context to the repository root so Railway uses the root `Dockerfile`. The image installs `app/requirements.txt`, includes `app/` and `frontend/`, and runs Gunicorn on Railway's supplied `PORT`. The Flask service hosts the website at `/`, the API at `/shorten` (also `/api/shorten`), health status at `/health`, and redirects at `/<alias>`.

In the backend service's Variables settings, configure:

| Variable | Value | Required |
| --- | --- | --- |
| `DATABASE_URL` | Railway PostgreSQL service reference / connection URL | Yes |
| `REDIS_URL` | Railway Redis service reference / connection URL | Recommended; PostgreSQL is used if Redis is unavailable |
| `PUBLIC_BASE_URL` | Confirmed HTTPS public origin of the Shortly backend | Yes |
| `PGSSLMODE` | `require` if the PostgreSQL provider requires SSL mode override | Optional |
| `PORT` | Supplied by Railway | Railway managed |

`.env.example` documents local development values. Docker Compose supplies its own database and Redis service settings and does not load that file. Do not copy real database or Redis credentials into the repository or frontend.

## Public domain

Generate a public domain for the backend service in Railway. The requested `https://shortly.up.railway.app` is not confirmed until Railway reports it available. If that name is unavailable, use the domain Railway assigns. Set `PUBLIC_BASE_URL` to the confirmed `https://` origin and redeploy the backend. Flask uses this value when returning each complete short URL; the frontend uses the returned URL as-is.

The frontend and API share the same origin, so no separate frontend service or CORS configuration is needed.

## Deploy and redeploy manually

Connect the Railway backend service to the repository and use Railway's manual deployment controls to deploy the current GitHub revision. Later, push changes to GitHub yourself, then trigger a manual redeploy in Railway. This repository does not configure automatic deployment. Changing the public domain requires updating `PUBLIC_BASE_URL` and redeploying.

The backend applies an additive, idempotent database change on first use to add the unique alias field. Existing rows receive their former base62 paths, preserving existing links. It does not drop tables or records.

## Basic production verification

After deployment:

1. Open the backend domain and confirm the Shortly page loads.
2. Open `/health` and confirm it returns `{"status":"healthy"}`.
3. Shorten one URL without a custom alias and another with a custom alias.
4. Confirm both returned URLs use the configured Railway domain and open the expected destination.
5. Try a duplicate or reserved alias and confirm the API returns a clear error.
