FROM python:3.8-slim-buster
WORKDIR /app
RUN pip install --no-cache-dir -U pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r ./requirements.txt
COPY ircrssfeedbot ircrssfeedbot
RUN groupadd -g 999 app && \
    useradd -r -m -u 999 -g app app
USER app
ENTRYPOINT ["python", "-m", "ircrssfeedbot"]
CMD ["--config-path", "/config/config.yaml"]
STOPSIGNAL SIGINT
