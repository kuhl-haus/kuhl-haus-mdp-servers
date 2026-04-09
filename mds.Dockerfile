ARG BASE_IMAGE=python:3.14
FROM ${BASE_IMAGE}
WORKDIR /app

COPY . /app/

# Install package and all dependencies from pyproject.toml
RUN pip install --no-cache-dir .

EXPOSE 4205/tcp
CMD ["uvicorn", "kuhl_haus.servers.mds_server:app", "--host", "0.0.0.0", "--port", "4205"]
