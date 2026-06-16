FROM python:3.13-slim-bookworm

RUN pip install --no-cache-dir pytest pytest-json-ctrf

# Bake tests into the verifier image — harbor does NOT upload tests/ at verify time
COPY . /tests/

# Pre-create artifact and log directories
RUN mkdir -p /app /logs/verifier
