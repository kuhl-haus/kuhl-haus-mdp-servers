ARG BASE_IMAGE=python:3.14
FROM ${BASE_IMAGE}
WORKDIR /app

COPY . /app/

# Install package and all dependencies from pyproject.toml
RUN pip install --no-cache-dir .

EXPOSE 4201/tcp
CMD ["uvicorn", "kuhl_haus.servers.mdp_server:app", \
     "--host", "0.0.0.0", \
     "--port", "4201", \
     "--timeout-keep-alive", "75", \
     "--timeout-graceful-shutdown", "30", \
     "--log-level", "info", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
