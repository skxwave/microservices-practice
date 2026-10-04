# CLAUDE.md

Practice/playground repo for microservice infrastructure and distributed patterns (Outbox, Saga). See [README.md](README.md) for setup and commands.

## Layout

- `users/`, `products/`: FastAPI + SQLAlchemy async + Alembic + Kafka producer. `main.py` holds the routes, `src/` the rest.
- `notifications/`: plain aiokafka consumer, a single `main.py`, no web server.
- `infrastructure/`: compose files, nginx config, justfile. Treat it as a separate repo that happens to build from `../<service>`.

## Rules of this repo

- Services are fully isolated: own `pyproject.toml`, `uv.lock`, `Dockerfile`, `.dockerignore`, `.env`. Build context is the service directory. No uv workspace, no shared code between services.
- Settings come from `src/config.py` (pydantic-settings). No `os.getenv` or `load_dotenv` in service code. `notifications` is the exception and uses `os.environ` (it has no pydantic dependency).
- One Kafka producer per app, created in the FastAPI lifespan (`src/events.py`). Never create a producer per request.
- Inter-service calls go over HTTP by service name inside the compose network (`USER_SERVICE_URL=http://users:8000`).
- Config is split. Compose gets service env from `infrastructure/docker-compose.yml`. Local runs get it from `<service>/.env`. Update both when adding a variable, plus the `.env.template`.
- `docker-compose.dev.yml` is dev-only (published ports, reload, kafka-ui). It is never loaded implicitly; the justfile passes `-f` explicitly.
- DB credentials are per service. Never share a user between databases.

## Adding a service

1. Create `<svc>/` with `pyproject.toml`, `uv.lock` (`uv lock`), `Dockerfile` and `.dockerignore`, copied from an existing service.
2. Add to `infrastructure/docker-compose.yml`: db, `<svc>-migrate` (if it has a DB), the service itself, and its DB creds in `.env.template`.
3. Add an nginx `upstream` and `location /api/<svc>` in `infrastructure/nginx/nginx.conf`.
4. Give it its own justfile with `dev`, `test` and `lint` recipes.
5. `just infra` currently lists infra services by name, so add new infra services there too.

## Commands

- Run from `infrastructure/`: `just up`, `just infra`, `just reset`, `just migrate <svc>`.
- Run from a service dir: `just dev`, `just test`, `just lint`, `just makemigration "msg"`.
- Verify touched services with `just lint` and `just test` (users, products). Notifications has lint only.

## Gotchas

- Docker builds use `python:3.14-slim` and `pip install uv` because `ghcr.io` was unreachable on the owner's network. Do not switch back to the `ghcr.io/astral-sh/uv` image.
- Compose project name is `microservices`. Changing it, or per-service DB credentials, orphans existing volumes; use `just reset`.
- Kafka advertises two listeners: `kafka:9092` (inside Docker) and `localhost:9094` (host). Containers use the first, local `just dev` runs use the second.
- Ruff is limited to `E4, E7, E9, F`. Legacy files (migrations, models) fail the wider default rules, and are not to be reformatted unprompted.
- Tests mock the DB with `AsyncMock` and set env in `tests/conftest.py` before importing `main`. They need no Kafka or Postgres.

## Known issues

- `users/main.py` exposes `POST /debug/user_create_event` in every environment.
- `products/src/services/user_service.py` returns `None` despite the `UserDTO` annotation and creates an httpx client per call.
- Route handlers build response models by hand instead of `model_validate`.
- Events are published after the DB commit with no outbox, so a Kafka failure loses the event. This is the planned Outbox exercise.
- The healthcheck interval (10s) in the Dockerfiles is aggressive. Proposed, not yet approved or applied: `--interval=30s --start-interval=2s` and `timeout=2` on `urlopen`.
