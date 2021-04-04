FROM python:3.9-slim-buster as build
WORKDIR /app
COPY requirements.txt .
RUN set -x && \
    apt-get update && apt-get -y install gcc && \
    sed -i 's/@SECLEVEL=2/@SECLEVEL=1/' /etc/ssl/openssl.cnf && \
    pip install --no-cache-dir -U pip wheel && \
    pip install --no-cache-dir -r ./requirements.txt
# Note: Regarding SECLEVEL, see https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=927461
# Lowering the SECLEVEL causes more https certificates to be valid.
COPY ircrssfeedbot ircrssfeedbot
RUN set -x && \
    groupadd -g 999 app && \
    useradd -r -m -u 999 -g app app && \
    mkdir -v ./.ircrssfeedbot_cache && \
    chown -v app:app ./.ircrssfeedbot_cache
USER app
ENTRYPOINT ["python", "-m", "ircrssfeedbot"]
CMD ["--config-path", "/config/config.yaml"]
STOPSIGNAL SIGINT

FROM build as test
WORKDIR /app
#RUN set -x && python -m ircrssfeedbot -h
USER root
COPY Makefile pylintrc pyproject.toml requirements-dev.in setup.cfg ./
RUN set -x && \
    pip install --no-cache-dir -U -r requirements-dev.in && \
#    pip freeze --all && \
    apt-get -y install make && \
    make test

FROM build
