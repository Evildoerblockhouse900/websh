FROM python:3-slim

RUN apt-get update && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -r -s /bin/false websh

WORKDIR /app
COPY server.py .

USER websh

ENV PORT=8765 HOST=0.0.0.0 SESSION_TIMEOUT=300 MAX_SESSIONS=10

EXPOSE 8765

CMD ["python3", "server.py"]
