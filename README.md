# webserver

Her finner du en enkel webserver som generer html basert på csv-filer i test-data

## Slik går du fram for å kjøre dette lokalt

## Utvikle og kjøre lokalt

### Krav til programvare

- [pyenv](https://github.com/pyenv/pyenv) (recommended)
- [poetry](https://python-poetry.org/)
- [nox](https://nox.thea.codes/en/stable/)
- [nox-poetry](https://pypi.org/project/nox-poetry/)

### Installere programvare

```Shell
% git clone https://github.com/langrenn-sprint/event-service-gui.git
% cd evnt-service-gui
% pyenv install 3.9.1
% pyenv local 3.9.1
% pipx install poetry
% pipx install nox
% pipx inject nox nox-poetry
% poetry install
```

## oppdatere

```Shell
% poetry update / poetry add <module>
```

## Miljøvariable

Du må sette opp ei .env fil med miljøvariable. Eksempel:

```Shell
JWT_SECRET=secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=password
COMPETITION_FORMAT_HOST_PORT=8094
COMPETITION_FORMAT_HOST_SERVER=localhost
DB_USER=event-service
DB_PASSWORD=secret
EVENTS_HOST_SERVER=localhost
EVENTS_HOST_PORT=8082
FERNET_KEY=23EHUWpP_MyKey_MyKeyhxndWqyc0vO-MyKeySMyKey=
JWT_EXP_DELTA_SECONDS=3600
LOGGING_LEVEL=INFO
RACE_HOST_SERVER=localhost
RACE_HOST_PORT=8088
USERS_HOST_SERVER=localhost
USERS_HOST_PORT=8086
```

### Config gcloud

```Shell
gcloud -v
gcloud auth login
gcloud config set project langrenn-sprint
gcloud auth configure-docker
```

### Starte services i docker

```Shell
docker-compose pull #oppdatere images
docker-compose up --build
docker-compose up --build event-service race-service user-service mongodb competition-format-service
```

Denne fila _skal_ ligge i .dockerignore og .gitignore

### Kjøre webserver lokalt

## Start lokal webserver mha aiohttp-devtools(adev)

```Shell
% source .env
% poetry run adev runserver -p 8080 event_service_gui
```

### Teste manuelt

Enten åpne din nettleser på <http://localhost:8080/>

Eller via curl:

```Shell
% curl -i http://localhost:8080/
```

Når du endrer koden i event_service_gui, vil webserveren laste applikasjonen på nytt autoamtisk ved lagring.

## Referanser

aiohttp: <https://docs.aiohttp.org/>
