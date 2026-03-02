# Project Setup

The first step, to run the backend, is creating a `.env.local` file on the backend root directory (`~/abaca-app/rest-api`). The repository contains a `.env-example` file for reference. Next comes creating the Docker container. A Dockerfile for Abaca’s API can be found in the `/rest-api` directory, with the following content:

```docker
# <WARNING>
# Everything within sections like <TAG> is generated and can
# be automatically replaced on deployment. You can disable
# this functionality by simply removing the wrapping tags.
# </WARNING>

# <DOCKER_FROM>
FROM divio/base:2.2-py3.9-slim-buster
# </DOCKER_FROM>

# Install system dependencies needed to install project dependencies 
# weasyprint requires: gcc
# pyscopg2 requires: libpq-dev
RUN apt-get update && apt-get -y install gcc libpq-dev

# Make use of Divio's wheels server:
ENV PIP_INDEX_URL=${PIP_INDEX_URL:-https://wheels.aldryn.net/v1/aldryn-extras+pypi/${WHEELS_PLATFORM:-aldryn-baseproject-py3}/+simple/} \
    WHEELSPROXY_URL=${WHEELSPROXY_URL:-https://wheels.aldryn.net/v1/aldryn-extras+pypi/${WHEELS_PLATFORM:-aldryn-baseproject-py3}/}

# Install project dependencies
COPY requirements.* /app/
COPY addons-dev /app/addons-dev/
RUN pip install --no-deps --requirement requirements.txt

# <SOURCE>
COPY . /app
# </SOURCE>

# Temporary fix for incompatibility issue caused by ongoing Divio upgrade of database engine.
RUN apt-get update && apt-get install -y apt-transport-https && apt-get install -y gnupg
RUN sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt buster-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
RUN apt-get update && apt-get -y install postgresql-client-13

# Install dependencies & project fonts for PDF Generator (Weasyprint)
RUN apt-get update && apt-get -y install fontconfig build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
RUN cd /tmp && \
  wget https://assets.abaca.app/hkgrotesk/grotesk--light-normal.ttf && \
  wget https://assets.abaca.app/hkgrotesk/grotesk--regular-normal.ttf && \
  wget https://assets.abaca.app/hkgrotesk/grotesk--regular-italic.ttf && \
  wget https://assets.abaca.app/hkgrotesk/grotesk--semiBold-normal.ttf && \
  wget https://assets.abaca.app/hkgrotesk/grotesk--semiBold-italic.ttf && \
  wget https://assets.abaca.app/hkgrotesk/grotesk--bold-normal.ttf && \
  wget https://assets.abaca.app/hkgrotesk/grotesk--bold-italic.ttf && \
  mv * /usr/local/share/fonts && \
  fc-cache -v

RUN cp /app/aldryn-celery-script.sh /usr/local/bin/aldryn-celery
RUN chmod +x /usr/local/bin/aldryn-celery

RUN DJANGO_MODE=build python manage.py collectstatic --noinput
```

Having Docker installed, a new container can be created and launched by running the following command on a command line:

```bash
# In ~/abaca-app/rest-api
docker-compose up -d web
```

Once the container is running, execute Django’s database migrations by running:

```bash
# ~/abaca-app/rest-api
docker-compose exec web ./manage.py migrate
```

Lastly, to populate the local database with mock data, run:

```bash
# ~/abaca-app/rest-api
docker-compose exec web ./manage.py database_savepoint -a setup
```

You can now access the Django Admin panel by visiting the URL configured in the `.env-local` file – http://localhost:8080 by default.