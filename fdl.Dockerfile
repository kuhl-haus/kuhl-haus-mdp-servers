ARG BASE_IMAGE=python:3.14
FROM ${BASE_IMAGE}
WORKDIR /tmp

COPY requirements.txt /tmp/

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -f /tmp/requirements.txt

WORKDIR /app

COPY . /app/

# Install in editable mode
RUN pip install --no-cache-dir -e .

EXPOSE 4200/tcp
CMD ["uvicorn", "kuhl_haus.servers.fdl_server:app", "--host", "0.0.0.0", "--port", "4200"]
