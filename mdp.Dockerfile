ARG BASE_IMAGE=python:3.14
FROM ${BASE_IMAGE}
WORKDIR /tmp

COPY requirements.txt /tmp/

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -f /tmp/requirements.txt

RUN opentelemetry-bootstrap -a install

WORKDIR /app

COPY . /app/

# Install in editable mode
RUN pip install --no-cache-dir -e .

EXPOSE 4201/tcp
CMD ["opentelemetry-instrument", "uvicorn", "kuhl_haus.servers.mdp_server:app", \
     "--host", "0.0.0.0", \
     "--port", "4201", \
     "--timeout-keep-alive", "75", \
     "--timeout-graceful-shutdown", "30", \
     "--log-level", "info", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
