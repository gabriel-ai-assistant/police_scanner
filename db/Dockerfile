FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY init.sql /app/init.sql
COPY migrations/ /app/migrations/
COPY docker_migrate.py /app/docker_migrate.py

CMD ["python", "docker_migrate.py"]
