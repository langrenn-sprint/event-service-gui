FROM python:3.11

RUN mkdir -p /app
WORKDIR /app

RUN pip install --upgrade pip
RUN pip install "poetry==1.4.1"
COPY poetry.lock pyproject.toml /app/

# Project initialization:
RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction --no-ansi

ADD event_service_gui /app/event_service_gui

EXPOSE 8080

CMD gunicorn "event_service_gui:create_app"  --config=event_service_gui/gunicorn_config.py --worker-class aiohttp.GunicornWebWorker
