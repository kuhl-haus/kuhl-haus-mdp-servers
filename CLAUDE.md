# CLAUDE.md — kuhl-haus-mdp-servers

## Overview

Container image build repository for the Kuhl Haus Market Data Platform (MDP) data plane servers. Each server wraps components from [`kuhl-haus-mdp`](https://github.com/kuhl-haus/kuhl-haus-mdp) and runs as an independently scalable container in Kubernetes.

**PyPI:** https://pypi.org/project/kuhl-haus-mdp-servers/  
**Platform documentation:** https://kuhl-haus-mdp.readthedocs.io

## Platform Context

**Platform repositories:**
- **kuhl-haus-mdp** — Core library (this repo depends on it)
- **kuhl-haus-mdp-servers** *(this repo)* — Server entry points and Docker images
- **kuhl-haus-mdp-app** — Service Control Plane (SCP) web application
- **kuhl-haus-mdp-deployment** — Kubernetes/Ansible deployment automation

## Servers

| Server | Acronym | Role |
|---|---|---|
| Finlight Data Listener | FDL | WebSocket client → Finlight news API; routes articles to RabbitMQ news queue |
| Finlight Data Processor | FDP | Async RabbitMQ consumer for Finlight news articles; delegates to analyzers; writes to Redis |
| Market Data Listener | MDL | WebSocket client → Massive.com; routes events to RabbitMQ with minimal processing |
| Market Data Processor | MDP | Horizontally-scalable event processor; semaphore-based concurrency (500 tasks); delegates to pluggable analyzers; writes to Redis |
| Leaderboard Analyzer | LBA | Redis pub/sub consumer; runs leaderboard and trade analyzers with sequential processing |
| Widget Data Service | WDS | FastAPI/WebSocket-to-Redis bridge; real-time fan-out streaming to client applications |

All servers emit OpenTelemetry traces/metrics and structured JSON logs.

## Code Organization

```
src/kuhl_haus/servers/
├── fdl_server.py         # Finlight Data Listener server entry point
├── fdp_server.py         # Finlight Data Processor server entry point
├── lba_server.py         # Leaderboard Analyzer server entry point
├── mdl_server.py         # Market Data Listener server entry point
├── mdp_server.py         # Market Data Processor server entry point
├── wds_server.py         # Widget Data Service (FastAPI/WebSocket) entry point
└── observability.py      # Shared OpenTelemetry instrumentation setup

# Dockerfiles — one standard + one OTel-instrumented variant per server
base.Dockerfile           # Shared base image
fdl.Dockerfile / fdl_otel.Dockerfile
fdp.Dockerfile / fdp_otel.Dockerfile
mdl.Dockerfile / mdl_otel.Dockerfile
mdp.Dockerfile / mdp_otel.Dockerfile
lba.Dockerfile / lba_otel.Dockerfile
wds.Dockerfile / wds_otel.Dockerfile
```

## Entry Points

Defined in `pyproject.toml`:

```
fdl_server = "kuhl_haus.servers.fdl_server:app"
lba_server = "kuhl_haus.servers.lba_server:app"
mdl_server = "kuhl_haus.servers.mdl_server:app"
mdp_server = "kuhl_haus.servers.mdp_server:app"
wds_server = "kuhl_haus.servers.wds_server:app"
```

## Development

**Language:** Python 3.14+  
**Package manager:** PDM  
**Build backend:** pdm-backend + setuptools-scm (version from git tags)  
**Primary dependency:** `kuhl-haus-mdp` (core library, version-pinned in `pyproject.toml`)

```bash
pip install -e ".[testing]"
```

> ⚠️ **No requirements.txt files.** This repo does not use `requirements.txt` or `requirements-build.txt`. All dependencies are declared in `pyproject.toml`. Do **not** create or install from requirements text files. Use `pip install -e ".[testing]"` for development and testing.

> ⚠️ **Build order matters:** In CI, always run `pdm build` before `pdm install`. Running `pdm install` first regenerates `pdm.lock`, making the working tree dirty — pdm-backend appends `+d<date>` to dirty builds, which PyPI rejects (PEP 440 local version identifiers).

## Docker Images

Each server has two image variants:
- **Standard** (`mdl.Dockerfile`, etc.) — production image
- **OTel** (`mdl_otel.Dockerfile`, etc.) — includes OpenTelemetry auto-instrumentation

Images are published to `ghcr.io/kuhl-haus/`.

## CI/CD (GitHub Actions)

| Workflow | Trigger | Purpose |
|---|---|---|
| `build-images.yml` | push/tag on mainline | Build and push Docker images to GHCR |
| `publish-to-pypi.yml` | version tag push | Build and publish Python package to PyPI |
| `codeql.yml` | push/PR | CodeQL security analysis |

## Branch and Merge Conventions

- **Default branch:** `mainline`
- **Squash merge only** — org-level enforcement; merge commits and rebase are disabled
- All PRs target `mainline`; use feature branches for all changes
- Version tags drive PyPI and Docker image releases — tag format: `vX.Y.Z`


## Bug Workflow — Test First

When a bug is reported, **do not start by fixing it**.

1. **Write a failing test** that reproduces the bug first
2. Confirm the test fails (proving the bug exists)
3. Then fix the bug and prove it with a passing test

