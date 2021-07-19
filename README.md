# webserver

Her finner du en enkel webserver som generer html basert på csv-filer i test-data

## Slik går du fram for å kjøre dette lokalt

## Utvikle og kjøre lokalt
### Krav til programvare
- [pyenv](https://github.com/pyenv/pyenv) (recommended)
- [poetry](https://python-poetry.org/)
- [nox](https://nox.thea.codes/en/stable/)
- [nox-poetry](https://pypi.org/project/nox-poetry/)

### Installere programvare:
```
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
```
% poetry update / poetry add <module>
```

## Miljøvariable
```
Du kan sette opp ei .env fil med miljøvariable. Eksempel:
HOST_PORT=8080
```

### Config gcloud
```
gcloud -v
gcloud auth login
gcloud config set project langrenn-sprint
gcloud auth configure-docker

### Starte services i docker
docker-compose pull #oppdatere images
docker-compose up --build
docker-compose up --build event-service  user-service mongodb

Denne fila _skal_ ligge i .dockerignore og .gitignore
### Kjøre webserver lokalt
```

## Start lokal webserver mha aiohttp-devtools(adev):
```
% source .env
% cd src && poetry run adev runserver -p 8080 event_service_gui
```
### Teste manuelt
Enten åpne din nettleser på http://localhost:8080/

Eller via curl:
```
% curl -i http://localhost:8080/
```
Når du endrer koden i event_service_gui, vil webserveren laste applikasjonen på nytt autoamtisk ved lagring.

# Referanser
aiohttp: https://docs.aiohttp.org/
