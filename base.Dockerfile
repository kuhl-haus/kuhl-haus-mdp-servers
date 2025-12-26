ARG BASE_IMAGE=ghcr.io/kuhl-haus/kuhl-haus-mdp:latest
FROM ${BASE_IMAGE}
WORKDIR /app

COPY . /app/

# Install in editable mode
RUN pip install --no-cache-dir -e .
