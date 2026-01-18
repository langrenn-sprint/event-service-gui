# webserver

Her finner du en enkel webserver som generer html sider basert på innhold fra backend tjenester event-service, user-service, competition-format-service, race-service og photo-service.

## Architecture

Layers:
- templates: presentation layer, in html and javascript
- views: routing functions, maps representations to/from model
- services: enforce validation, calls adapter-layer for storing/retrieving objects
- models: model-classes
- adapters: adapters to external services

## Slik går du fram for å kjøre dette lokalt

## Environment variables

To run the service locally, you need to supply a set of environment variables. A simple way to solve this is to supply a .env file in the root directory.

A minimal .env:

```Zsh
JWT_SECRET=secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=password
COMPETITION_FORMAT_HOST_PORT=8094
COMPETITION_FORMAT_HOST_SERVER=localhost
DB_USER=event-service
DB_PASSWORD=secret
EVENTS_HOST_SERVER=localhost
EVENTS_HOST_PORT=8082
ERROR_FILE=error.log
FERNET_KEY=23EHUWpP_MyKey_MyKeyhxndWqyc0vO-MyKeySMyKey=
JWT_EXP_DELTA_SECONDS=3600
LOGGING_LEVEL=INFO
RACE_HOST_SERVER=localhost
RACE_HOST_PORT=8088
USERS_HOST_SERVER=localhost
USERS_HOST_PORT=8086

## Requirement for development

Install [uv](https://docs.astral.sh/uv/), e.g.:

```Zsh
% curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Then install the dependencies and activate virtual env:

```Zsh
uv sync
source .venv/bin/activate
```

## Start the server locally

```Zsh
% uv run adev runserver -p 8080 event_service_gui
```

## Running the service in Docker

```Zsh
% docker build -t ghcr.io/langrenn-sprint/event-service-gui:test .
% docker run --env-file .env -p 8080:8080 -d ghcr.io/langrenn-sprint/event-service-gui:test
```

The easier way would be with docker-compose:

```Zsh
docker compose up --build
```

## Running tests

We use [pytest](https://docs.pytest.org/en/latest/) for contract testing.

To run linters, checkers and tests:

```Zsh
% uv run poe release
```

To run tests with logging, do:

```Zsh
% uv run pytest -m integration -- --log-cli-level=DEBUG
```
