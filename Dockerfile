FROM python:3.12

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.
ADD . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen

# Expose the application port.
EXPOSE 8080

# Run the application.
CMD ["/app/.venv/bin/gunicorn", "event_service_gui:create_app",  "--config=event_service_gui/gunicorn_config.py", "--worker-class", "aiohttp.GunicornWebWorker"]
