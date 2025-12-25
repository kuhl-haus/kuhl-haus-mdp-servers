ARG BASE_IMAGE=ghcr.io/kuhl-haus/kuhl-haus-mdp:latest
FROM ${BASE_IMAGE}
WORKDIR /app

COPY . /app/

# Install in editable mode
RUN pip install --no-cache-dir -e .

EXPOSE 4202/tcp
CMD ["uvicorn", "kuhl_haus.servers.wds_server:app", "--host", "0.0.0.0", "--port", "4202"]
