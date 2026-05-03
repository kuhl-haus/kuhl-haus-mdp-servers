.. image:: https://img.shields.io/github/license/kuhl-haus/kuhl-haus-mdp-servers
    :alt: License
    :target: https://github.com/kuhl-haus/kuhl-haus-mdp-servers/blob/mainline/LICENSE.txt
.. image:: https://img.shields.io/pypi/v/kuhl-haus-mdp-servers.svg
    :alt: PyPI
    :target: https://pypi.org/project/kuhl-haus-mdp-servers/
.. image:: https://static.pepy.tech/badge/kuhl-haus-mdp-servers/month
    :alt: Downloads
    :target: https://pepy.tech/project/kuhl-haus-mdp-servers
.. image:: https://github.com/kuhl-haus/kuhl-haus-mdp-servers/actions/workflows/build-images.yml/badge.svg
    :alt: Build Status
    :target: https://github.com/kuhl-haus/kuhl-haus-mdp-servers/actions/workflows/build-images.yml
.. image:: https://github.com/kuhl-haus/kuhl-haus-mdp-servers/actions/workflows/publish-to-pypi.yml/badge.svg
    :alt: Publish to PyPI
    :target: https://github.com/kuhl-haus/kuhl-haus-mdp-servers/actions/workflows/publish-to-pypi.yml
.. image:: https://github.com/kuhl-haus/kuhl-haus-mdp-servers/actions/workflows/codeql.yml/badge.svg
    :alt: CodeQL Advanced
    :target: https://github.com/kuhl-haus/kuhl-haus-mdp-servers/actions/workflows/codeql.yml
.. image:: https://img.shields.io/github/issues/kuhl-haus/kuhl-haus-mdp-servers
    :alt: GitHub issues
    :target: https://github.com/kuhl-haus/kuhl-haus-mdp-servers/issues
.. image:: https://img.shields.io/github/issues-pr/kuhl-haus/kuhl-haus-mdp-servers
    :alt: GitHub pull requests
    :target: https://github.com/kuhl-haus/kuhl-haus-mdp-servers/pulls

|

=======================
kuhl-haus-mdp-servers
=======================

Container image build repository for market data platform data plane servers.

Overview
========

This package provides the server entry points and Docker container images for the
Kuhl Haus Market Data Platform (MDP) data plane. Each server wraps components from
the `kuhl-haus-mdp <https://pypi.org/project/kuhl-haus-mdp/>`_ library and runs as
an independently scalable container in Kubernetes.

Servers
-------

**Market Data Listener (MDL)**
  WebSocket client connecting to Massive.com, routing events to RabbitMQ queues
  with minimal processing overhead.

**Market Data Processor (MDP)**
  Horizontally-scalable event processor with semaphore-based concurrency,
  delegating to pluggable analyzers and writing results to Redis cache.

**Leaderboard Analyzer (LBA)**
  Redis pub/sub consumer running leaderboard and trade analyzers with sequential
  message processing.

**Widget Data Service (WDS)**
  FastAPI/WebSocket-to-Redis bridge providing real-time streaming to client
  applications with fan-out pattern.

**Finlight Data Listener (FDL)**
  WebSocket client connecting to Finlight, subscribing to real-time financial
  news feeds and publishing enriched articles to RabbitMQ queues.

**Finlight Data Processor (FDP)**
  RabbitMQ consumer processing enriched news articles from the FDL queue,
  running ``FinlightDataAnalyzer`` to cache articles in Redis and publish
  updates to downstream consumers.

Each server has a standard Dockerfile and an OpenTelemetry-instrumented variant
(``*_otel.Dockerfile``) for production observability.

Container Images
----------------

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Server
     - Dockerfile
     - Entry Point
   * - MDL
     - ``mdl.Dockerfile`` / ``mdl_otel.Dockerfile``
     - ``kuhl_haus.servers.mdl_server:app``
   * - MDP
     - ``mdp.Dockerfile`` / ``mdp_otel.Dockerfile``
     - ``kuhl_haus.servers.mdp_server:app``
   * - LBA
     - ``lba.Dockerfile`` / ``lba_otel.Dockerfile``
     - ``kuhl_haus.servers.lba_server:app``
   * - WDS
     - ``wds.Dockerfile`` / ``wds_otel.Dockerfile``
     - ``kuhl_haus.servers.wds_server:app``
   * - FDL
     - ``fdl.Dockerfile`` / ``fdl_otel.Dockerfile``
     - ``kuhl_haus.servers.fdl_server:app``
   * - FDP
     - ``fdp.Dockerfile`` / ``fdp_otel.Dockerfile``
     - ``kuhl_haus.servers.fdp_server:app``

All images extend ``base.Dockerfile``, which installs dependencies and the package
in editable mode.

Code Organization
-----------------

The platform consists of four main packages:

- **Market data processing library** (`kuhl-haus-mdp <https://github.com/kuhl-haus/kuhl-haus-mdp>`_) - Core library with shared data processing logic
- **Backend Services** (`kuhl-haus-mdp-servers <https://github.com/kuhl-haus/kuhl-haus-mdp-servers>`_) - Market data listener, processor, and widget service
- **Frontend Application** (`kuhl-haus-mdp-app <https://github.com/kuhl-haus/kuhl-haus-mdp-app>`_) - Web-based user interface and API
- **Deployment Automation** (`kuhl-haus-mdp-deployment <https://github.com/kuhl-haus/kuhl-haus-mdp-deployment>`_) - Docker Compose, Ansible playbooks and Kubernetes manifests for environment provisioning

Configuration
-------------

All servers are configured via environment variables. See the
`Configuration Reference <https://kuhl-haus-mdp.readthedocs.io/en/latest/configuration.html>`_
for the full list of variables per server, including defaults and descriptions.

Documentation
-------------

For architecture details, component descriptions, and API reference, see the
`kuhl-haus-mdp documentation on Read the Docs <https://kuhl-haus-mdp.readthedocs.io/en/latest/>`_.

Additional Resources
--------------------

📖 **Blog Posts:**

All of my blog posts related to Kuhl Haus MDP are tagged with ``#kuhl-haus-mdp`` and listed in reverse chronological order at `oldschool-engineer.dev/tags/#kuhl-haus-mdp <https://oldschool-engineer.dev/tags/#kuhl-haus-mdp>`_.

The 5-part series where it all began:

- `Part 1: Why I Built It <https://oldschool-engineer.dev/side%20projects/2026/01/16/what-i-built-after-quitting-amazon-spoiler-its-a-stock-scanner.html>`_
- `Part 2: How to Run It <https://oldschool-engineer.dev/side%20projects/2026/01/21/what-i-built-after-quitting-amazon-spoiler-its-a-stock-scanner-part-2.html>`_
- `Part 3: How to Deploy It <https://oldschool-engineer.dev/infrastructure/2026/01/31/what-i-built-after-quitting-amazon-spoiler-its-a-stock-scanner-part-3.html>`_
- `Part 4: Evolution from Prototype to Production <https://oldschool-engineer.dev/software%20engineering/2026/02/11/what-i-built-after-quitting-amazon-spoiler-its-a-stock-scanner-part-4.html>`_
- `Part 5: Wave 1 Complete: Bugs, Bottlenecks, and Breaking 1,000 msg/s <https://oldschool-engineer.dev/software%20engineering/2026/02/23/what-i-built-after-quitting-amazon-spoiler-its-a-stock-scanner-part-5.html>`_
