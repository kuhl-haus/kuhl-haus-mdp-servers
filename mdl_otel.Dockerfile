ARG BASE_IMAGE=python:3.14
FROM ${BASE_IMAGE}
WORKDIR /app

COPY . /app/

# Install package and all dependencies from pyproject.toml
RUN pip install --no-cache-dir .
RUN pip install opentelemetry-distro
RUN opentelemetry-bootstrap -a install

EXPOSE 4200/tcp
CMD ["opentelemetry-instrument", "uvicorn", "kuhl_haus.servers.mdl_server:app", "--host", "0.0.0.0", "--port", "4200"]
