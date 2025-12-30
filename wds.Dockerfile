ARG BASE_IMAGE=python:3.12
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

EXPOSE 4202/tcp
CMD ["uvicorn", "kuhl_haus.servers.wds_server:app", "--host", "0.0.0.0", "--port", "4202"]
