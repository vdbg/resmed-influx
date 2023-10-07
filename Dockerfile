# Alpine for smaller size
FROM python:3.11-alpine

# Create a system account
RUN addgroup -S resmed && adduser -S resmed -G resmed

# Due to https://github.com/closeio/ciso8601/issues/98,
# when replacing "influxdb-client" with "influxdb-client[cisco]" in
# requirements.txt, the line below needs to be uncommented,
# which significantly increases the size of the docker image.
# RUN apk add --no-cache build-base

USER resmed

WORKDIR /app

# Prevents Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED 1
# Install location of upgraded pip
ENV PATH /home/resmed/.local/bin:$PATH

RUN pip install --no-cache-dir --disable-pip-version-check --upgrade pip

COPY requirements.txt     /app

RUN  pip install --no-cache-dir -r ./requirements.txt

COPY *.py                 /app/
COPY *.sh                 /app/
RUN chmod +x entrypoint.sh
COPY myair_client/*.py    /app/myair_client/
COPY template.config.toml /app/

ENTRYPOINT python main.py
