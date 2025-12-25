ARG BASE_IMAGE=ghcr.io/kuhl-haus/kuhl-haus-mdp:latest
FROM ${BASE_IMAGE}
WORKDIR /app

COPY . /app/

# Install in editable mode
RUN pip install --no-cache-dir -e .

EXPOSE 4201/tcp
CMD ["uvicorn", "kuhl_haus.servers.mdp_server:app", \
     "--host", "0.0.0.0", \
     "--port", "4201", \
     "--timeout-keep-alive", "75", \
     "--timeout-graceful-shutdown", "30", \
     "--log-level", "info", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
