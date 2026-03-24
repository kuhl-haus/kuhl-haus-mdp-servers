ARG BASE_IMAGE=python:3.14
FROM ${BASE_IMAGE}
WORKDIR /tmp

COPY requirements.txt /tmp/

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -f /tmp/requirements.txt

RUN pip install opentelemetry-distro

WORKDIR /app

COPY . /app/

# Install in editable mode
RUN pip install --no-cache-dir -e .
RUN opentelemetry-bootstrap -a install

EXPOSE 4202/tcp
CMD ["opentelemetry-instrument", "uvicorn", "kuhl_haus.servers.fdp_server:app", "--host", "0.0.0.0", "--port", "4202"]
