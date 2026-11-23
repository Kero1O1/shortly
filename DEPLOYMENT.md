# Shortly deployment

## Local Docker Compose

Install Docker Desktop. From the repository root run:

```sh
docker compose up --build
```

Open http://localhost:5000. Flask serves the frontend, API, redirects, and `/health` from the same origin. Compose starts PostgreSQL and Redis first and waits for their health checks. PostgreSQL data persists in the named `postgres_data` volume. `docker compose down` stops the containers and preserves that volume. Do not remove the volume if you need its records.

## Railway services

Production runs in one Railway project with three services:

1. PostgreSQL — permanent storage.
2. Redis — alias cache.
3. Shortly backend, connected to this GitHub repository.

The backend service builds from the repository root so Railway uses the root `Dockerfile`. The image installs `app/requirements.txt`, includes `app/` and `frontend/`, and runs Gunicorn on Railway's supplied `PORT`. The Flask service hosts the website at `/`, the API at `/shorten` (also `/api/shorten`), health status at `/health`, and redirects at `/<alias>`.

The backend service's variables are:

| Variable | Value | Required |
| --- | --- | --- |
| `DATABASE_URL` | Railway PostgreSQL service reference / connection URL | Yes |
| `REDIS_URL` | Railway Redis service reference / connection URL | Recommended; PostgreSQL is used if Redis is unavailable |
| `PUBLIC_BASE_URL` | `https://shortly-production-9ce7640d.up.railway.app` | Yes |
| `PGSSLMODE` | `require` if the PostgreSQL provider requires SSL mode override | Optional |
| `PORT` | Supplied by Railway | Railway managed |

`.env.example` documents local development values. Docker Compose supplies its own database and Redis service settings and does not load that file. Do not copy real database or Redis credentials into the repository or frontend.

## Public domain

The backend service is served at `https://shortly-production-9ce7640d.up.railway.app`, and `PUBLIC_BASE_URL` is set to it. Flask uses this value when returning each complete short URL; the frontend uses the returned URL as-is. Changing the domain means updating `PUBLIC_BASE_URL` and redeploying the backend.

In Railway, `PUBLIC_BASE_URL` should contain only the backend's public origin, for example `https://shortly-production-9ce7640d.up.railway.app`. Do not append the hostname again as a path segment. A real path prefix is supported when intentionally used.

The frontend and API share the same origin, so no separate frontend service or CORS configuration is needed.

## Deploy and redeploy manually

The backend service is connected to this repository, but a push to GitHub does not deploy by itself. To ship a change, push to GitHub, then trigger a manual redeploy of the backend service in Railway. This repository does not configure automatic deployment.

The backend applies an additive, idempotent database change on first use to add the unique alias field. Existing rows receive their former base62 paths, preserving existing links. It does not drop tables or records.

## Production verification

To check a deployment:

1. Open the backend domain and confirm the Shortly page loads.
2. Open `/health` and confirm it returns `{"status":"healthy"}`.
3. Shorten one URL without a custom alias and another with a custom alias.
4. Confirm both returned URLs use the configured Railway domain and open the expected destination.
5. Try a duplicate or reserved alias and confirm the API returns a clear error.
