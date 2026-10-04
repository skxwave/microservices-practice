# Microservices Practice

A playground for practicing microservice architecture. Two goals:

- **Infrastructure setup:** Docker, Compose, an nginx API gateway, Kafka, per-service databases, migrations, healthchecks and dev/prod configuration.
- **Distributed patterns:** Transactional Outbox, Saga and similar patterns, added to the services over time.

This is not a production system. Services are deliberately small so the infrastructure and the patterns stay the focus.

## Services

| Service | Role | Stack |
| --- | --- | --- |
| [users](users) | Users CRUD, publishes `UserCreated` | FastAPI, PostgreSQL, Kafka producer |
| [products](products) | Products CRUD, validates owner through the users API, publishes `ProductCreated` / `ProductUpdated` | FastAPI, PostgreSQL, Kafka producer |
| [notifications](notifications) | Consumes user and product events | Kafka consumer |
| [infrastructure](infrastructure) | Compose files, nginx gateway config, dev tooling | Docker Compose, nginx |

Each service is standalone: its own `pyproject.toml`, `uv.lock`, `Dockerfile` and `.env`. There is no shared workspace or shared code.

Kafka topics: `user.user-events.v1`, `product.product-events.v1`.

## Prerequisites

- Docker with Compose v2
- [just](https://github.com/casey/just)
- [uv](https://docs.astral.sh/uv/) and Python 3.14 (only for running services outside Docker)

## Run everything in Docker

```sh
cd infrastructure
just up
```

`just up` creates `infrastructure/.env` from `.env.template` if it's missing, builds the images and starts the stack. Migrations run automatically before each API starts.

| What | URL |
| --- | --- |
| Gateway, users | http://localhost/api/users |
| Gateway, products | http://localhost/api/products |
| Users API directly (dev only) | http://localhost:8000/docs |
| Products API directly (dev only) | http://localhost:8001/docs |
| Kafka UI (dev only) | http://localhost:8080 |

Other commands, all run from `infrastructure/`:

| Command | Effect |
| --- | --- |
| `just down` | Stop and remove containers |
| `just reset` | Same, plus delete volumes (wipes DBs and Kafka data) |
| `just build` | Rebuild images |
| `just logs [service]` | Follow logs |
| `just ps` | Show container status |
| `just migrate users` | Re-run migrations for a service |
| `just prod-up` | Production-shaped stack: no dev ports, no hot reload |

In dev mode `users` and `products` mount their source and reload on change.

## Run services locally, infrastructure in Docker

```sh
cd infrastructure && just infra          # Kafka, Kafka UI, both databases
```

Then, for each service you want to run (in separate terminals):

```sh
cd users                                 # or products, notifications
cp .env.template .env                    # first time only
uv sync
just migrate                             # users and products only
just dev
```

`users` serves on port 8000, `products` on 8001. Stop the infrastructure with `just infra-down`.

## Development

Inside `users` or `products`:

| Command | Effect |
| --- | --- |
| `just test` | Run pytest |
| `just lint` | Run ruff |
| `just makemigration "message"` | Autogenerate an Alembic migration |
| `just migrate` / `just downgrade` | Apply or revert migrations locally |

`notifications` has `just dev` and `just lint`; it has no tests yet.

## Configuration

Services read settings from environment variables (or `.env` locally); see each service's `.env.template`.

- `DB_URL`, `KAFKA_BOOTSTRAP_SERVERS`, `DEBUG`
- `USER_SERVICE_URL` (products only)

Database credentials for the Docker stack live in `infrastructure/.env`, one user and password per database. The `.env.template` values are dev defaults only.

## Roadmap

- Transactional Outbox for event publishing
- Saga for flows that span services
- Compose profiles so new services don't need manual edits in the justfile
- TLS and rate limiting on the gateway
