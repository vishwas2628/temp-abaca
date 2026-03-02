# <WARNING>
# Everything within sections like <TAG> is generated and can
# be automatically replaced on deployment. You can disable
# this functionality by simply removing the wrapping tags.
# </WARNING>

# <DOCKER_FROM>
FROM divio/base:1.0-py3.9-slim-bookworm
# debina buster has rreached extended lts and cant be used without
# paying for the support
# FROM divio/base:2.2-py3.9-slim-buster
# </DOCKER_FROM>

# Install system dependencies needed to install project dependencies 
# weasyprint requires: gcc
# pyscopg2 requires: libpq-dev
RUN apt-get update && apt-get -y install gcc libpq-dev
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
RUN echo 'source $HOME/.cargo/env' >> $HOME/.bash

# Make use of Divio's wheels server:
ENV PIP_INDEX_URL=${PIP_INDEX_URL:-https://wheels.aldryn.net/v1/aldryn-extras+pypi/${WHEELS_PLATFORM:-aldryn-baseproject-py3}/+simple/} \
  WHEELSPROXY_URL=${WHEELSPROXY_URL:-https://wheels.aldryn.net/v1/aldryn-extras+pypi/${WHEELS_PLATFORM:-aldryn-baseproject-py3}/}



# Install project dependencies
COPY requirements.* /app/
COPY addons-dev /app/addons-dev/
RUN pip install --upgrade pip

RUN pip uninstall pyopenssl
RUN pip uninstall cryptography
RUN pip install pyopenssl
RUN pip install cryptography

RUN pip install --no-deps --requirement requirements.txt

# <SOURCE>
COPY . /app
# </SOURCE>

# Temporary fix for incompatibility issue caused by ongoing Divio upgrade of database engine.
RUN apt-get update && apt-get install -y apt-transport-https && apt-get install -y gnupg
RUN sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
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
