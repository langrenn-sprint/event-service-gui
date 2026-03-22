# Copilot Instructions for event-service-gui

## Project Overview

This is a web-based GUI application for administering sporting events. It's built with Python 3.13+ using aiohttp framework and follows a layered architecture pattern.

## Architecture

The application follows a strict layered architecture:

- **views/**: Routing functions that handle HTTP requests/responses and map to/from models
- **services/**: Business logic layer that enforces validation and calls adapters
- **adapters/**: Interface to external backend services (event-service, user-service, competition-format-service, race-service, photo-service)

**Important**: Views can call adapters directly, but adapters should not contain business logic. Business logic belongs in the services layer.

## Technology Stack

- **Language**: Python 3.13+
- **Web Framework**: aiohttp
- **Template Engine**: Jinja2
- **Session Management**: aiohttp-session with EncryptedCookieStorage
- **Authentication**: JWT (via JWT_SECRET env var)
- **Package Manager**: uv
- **Task Runner**: poethepoet (poe)

## Development Workflow

### Setup and Installation

1. Install uv package manager:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Sync dependencies:
   ```bash
   uv sync
   ```

### Running the Application

**Development server**:
```bash
uv run adev runserver -p 8080 event_service_gui
```

**Production server (gunicorn)**:
```bash
uv run gunicorn event_service_gui:create_app --bind localhost:8080 --worker-class aiohttp.GunicornWebWorker
```

**With Docker**:
```bash
docker compose up --build
```

### Testing

**Run full release process** (lint, type check, dependency check, audit, tests):
```bash
uv run poe release
```

**Run integration tests only**:
```bash
uv run poe integration_test
```

**Run contract tests only**:
```bash
uv run poe contract_test
```

**Run tests with logging**:
```bash
uv run pytest -m integration --log-cli-level=DEBUG
```

### Code Quality

**Format code**:
```bash
uv run poe format
```

**Lint and auto-fix**:
```bash
uv run poe lint
```

**Type checking**:
```bash
uv run poe pyright
```

**Check dependencies**:
```bash
uv run poe check_deps
```

**Security audit**:
```bash
uv run poe audit
```

## Coding Conventions

### Style Guide

- Use **Google-style docstrings** (configured in pyproject.toml)
- Follow **ruff** linting rules (comprehensive ruleset with specific ignores in pyproject.toml)
- Type hints are encouraged but ANN001 and ANN401 are ignored
- All test files in `tests/**/*.py` are exempt from linting rules

### Import Organization

- Use isort grouping with `event_service_gui` as first-party package
- Standard library imports first
- Third-party imports second
- First-party imports last

### Views Pattern

Views are aiohttp web.View classes with HTTP method handlers:

```python
class MyView(web.View):
    """Class representing my view."""

    async def get(self) -> web.Response:
        """Get function."""
        try:
            user = await check_login_open(self)
            # ... logic here
            return await aiohttp_jinja2.render_template_async(
                "template.html",
                self.request,
                {"key": "value"},
            )
        except Exception as e:
            logging.exception("Error description")
            return web.HTTPSeeOther(location=f"/login?informasjon={e}")
```

### Service/Adapter Pattern

Services and adapters communicate with external APIs using aiohttp ClientSession:

```python
headers = MultiDict([
    (hdrs.AUTHORIZATION, f"Bearer {token}"),
])
async with ClientSession() as session, session.get(url, headers=headers) as resp:
    if resp.status == HTTPStatus.OK:
        result = await resp.json()
    elif resp.status == HTTPStatus.UNAUTHORIZED:
        raise web.HTTPBadRequest(reason="401 Unauthorized")
    else:
        body = await resp.json()
        raise web.HTTPBadRequest(reason=f"Error - {resp.status}: {body['detail']}")
```

### Error Handling

- Use try/except blocks in views
- Log exceptions with `logging.exception()`
- Redirect to login page with informasjon parameter on errors
- Raise `web.HTTPBadRequest` or similar aiohttp exceptions in services/adapters

### Testing

- **Integration tests**: Mark with `@pytest.mark.integration`
- **Contract tests**: Mark with `@pytest.mark.contract`
- Use `pytest-aiohttp` fixtures (`aiohttp_client`)
- Mock external services with `aioresponses`
- Environment variables are configured in `pyproject.toml` under `[tool.pytest.ini_options]`

## Environment Variables

Required environment variables:

- `JWT_SECRET`: Secret for JWT token generation
- `ADMIN_USERNAME` / `ADMIN_PASSWORD`: Admin credentials
- `EVENTS_HOST_SERVER` / `EVENTS_HOST_PORT`: Event service connection
- `USERS_HOST_SERVER` / `USERS_HOST_PORT`: User service connection
- `COMPETITION_FORMAT_HOST_SERVER` / `COMPETITION_FORMAT_HOST_PORT`: Competition format service
- `RACE_HOST_SERVER` / `RACE_HOST_PORT`: Race service connection
- `FERNET_KEY`: Encryption key for session cookies
- `ERROR_FILE`: Path to error log file
- `LOGGING_LEVEL`: Logging level (default: INFO)

Keep this list in sync with `README.md` when adding new variables.
Create a `.env` file in the project root for local development.

## Important Notes

- **Never commit secrets** to the repository
- **Disable pagers** when using git commands (use `git --no-pager`)
- The application is Norwegian-focused; UI text and comments may be in Norwegian
- **Coverage requirement**: Minimum 10% (configured in pyproject.toml)
- Test files ignore coverage and linting rules
- Dependencies in `deptry.per_rule_ignores` (aiodns, certifi, cryptography, urllib3) are intentional

## File Structure

```
event_service_gui/
├── __init__.py           # Package exports create_app
├── app.py                # Application factory and setup
├── gunicorn_config.py    # Gunicorn configuration
├── views/                # HTTP request handlers
│   ├── __init__.py
│   ├── main.py
│   ├── login.py
│   ├── logout.py
│   ├── utils.py          # Shared view utilities
│   └── ...
├── services/             # Business logic and adapters
│   ├── *_adapter.py      # External service adapters
│   ├── *_service.py      # Business logic services
│   └── ...
├── templates/            # Jinja2 templates
├── static/               # Static assets
└── config/               # Configuration files

tests/
├── conftest.py           # Test fixtures
├── integration/          # Integration tests
└── contract/             # Contract tests
```

## Common Tasks

### Adding a New View

1. Create a new class in `views/` inheriting from `web.View`
2. Implement HTTP method handlers (get, post, etc.)
3. Use `check_login_open()` for authentication
4. Render templates with `aiohttp_jinja2.render_template_async()`
5. Import and add to `views/__init__.py`
6. Register route in `app.py`

### Adding a New Service/Adapter

1. Create new file in `services/`
2. Define class with async methods
3. Use environment variables for service URLs
4. Use aiohttp ClientSession for HTTP calls
5. Handle authentication with Bearer tokens
6. Raise appropriate aiohttp exceptions on errors
7. Import and use from services package

### Adding Tests

1. Create test file in appropriate directory (`integration/` or `contract/`)
2. Mark with `@pytest.mark.integration` or `@pytest.mark.contract`
3. Use `client` fixture from conftest.py for aiohttp testing
4. Mock external services with `aioresponses`
5. Run with `uv run pytest -m integration` or `uv run pytest -m contract`

## Before Committing

Always run the full release process to ensure code quality:

```bash
uv run poe release
```

This runs: lint → pyright → check_deps → audit → integration_test → contract_test
