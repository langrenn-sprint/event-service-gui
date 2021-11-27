FROM python:3.9

RUN mkdir -p /usr/app
WORKDIR /usr/app

RUN pip install --upgrade pip
RUN pip install "poetry==1.1.6"
COPY poetry.lock pyproject.toml /usr/app/

# Project initialization:
RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction --no-ansi

ADD event_service_gui /usr/app/event_service_gui

EXPOSE 8080

CMD gunicorn "event_service_gui:create_app"  --config=event_service_gui/gunicorn_config.py --worker-class aiohttp.GunicornWebWorker
