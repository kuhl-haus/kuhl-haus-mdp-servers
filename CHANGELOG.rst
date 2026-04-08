=========
Changelog
=========
Version 0.3.0 (2026-04-08)
==========================

- `ec00614 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/ec00614>`_ scripts: add update-changelog.sh and CONTRIBUTING.rst (#50)

  update-changelog.sh: copied from kuhl-haus-mdp. Maintainer-only release tool.

  CONTRIBUTING.rst: slim version — full docs live in kuhl-haus-mdp.

- `e861f18 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/e861f18>`_ feat: split REDIS_URL into MDC_REDIS_URL and WDC_REDIS_URL; pin mdp to 0.4.0 (#49)

  * feat: split REDIS_URL into MDC_REDIS_URL and WDC_REDIS_URL; pin mdp to 0.4.0

  - lba_server: MDC_REDIS_URL → AnalyzerOptions; WDC_REDIS_URL → MassiveDataProcessor

  - mdp_server: MDC_REDIS_URL → AnalyzerOptions (shared); WDC_REDIS_URL → all processors

  - fdp_server: MDC_REDIS_URL → AnalyzerOptions; WDC_REDIS_URL → FinlightDataProcessor

  - wds_server: WDC_REDIS_URL → widget data reads (no MDC needed)

  - mdl_server: redis_url removed entirely (was POC leftover, never used)

  Defaults: MDC=redis://mdc:mdc@localhost:6379/0, WDC=redis://mdc:mdc@localhost:6379/1

  refs #48

  * fix(tests): update fdp_server tests for mdc_redis_url/wdc_redis_url

  redis_url replaced by mdc_redis_url + wdc_redis_url in Settings.

- `e79944c <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/e79944c>`_ Version bump kuhl-haus-mdp to 0.3.15

  Updated health check behavior so that k8s can recycle the pod when it is unhealthy.

  ref: https://github.com/kuhl-haus/kuhl-haus-mdp/commit/91dee10375417107c1d19bb9f3eb3c60f52ee773

  Fixes a bug in MDL where a transient failure in get_market_status() kills the reconnect loop permanently.

  ref: https://github.com/kuhl-haus/kuhl-haus-mdp/issues/66

- `93a8c2b <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/93a8c2b>`_ Annotate listener_kwargs with typing imports

  Add Any and Dict to the typing imports and annotate listener_kwargs as Dict[str, Any]. This improves static type clarity for the listener kwargs object without changing runtime behavior.

- `71ee072 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/71ee072>`_ feat(FDPServer): add NEWS_FEED_CACHE_TTL and NEWS_TICKER_CACHE_TTL env vars; pin mdp to 0.3.14 (#47)

  * feat(FDPServer): add NEWS_FEED_CACHE_TTL and NEWS_TICKER_CACHE_TTL env vars; pin mdp to 0.3.14

  Wire two new AnalyzerOptions.kwargs entries to environment variables:

  - NEWS_FEED_CACHE_TTL (default: MarketDataCacheTTL.NEWS_FEED_LATEST = 1 day)

  - NEWS_TICKER_CACHE_TTL (default: MarketDataCacheTTL.NEWS_TICKER = 3 days)

  Pins kuhl-haus-mdp to 0.3.14 which adds the configurable TTL support

  in FinlightDataAnalyzer.

  refs kuhl-haus/kuhl-haus-project-roadmap#1

  * ci: retrigger — 0.3.14 now available on PyPI

- `44a2ff7 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/44a2ff7>`_ chore: pin kuhl-haus-mdp to 0.3.13 (#46)

  Picks up perf(LeaderboardAnalyzer): eliminate redundant hgetall for

  quote publication (refs kuhl-haus-mdp#62).

- `f1670c3 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/f1670c3>`_ docs(CLAUDE): add bug workflow — test first directive (#45)
- `94e46fb <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/94e46fb>`_ feat(fdp_server): wire AnalyzerOptions with env-configurable cache limits (#44)

  Pins kuhl-haus-mdp to 0.3.12 (AnalyzerOptions.kwargs + FinlightDataProcessor

  required analyzer_options param + FinlightDataAnalyzer configurable limits).

  Settings additions:

  - FINLIGHT_API_KEY: Finlight API key (optional, passed to AnalyzerOptions)

  - NEWS_FEED_LIST_MAX: max articles in news feed cache (default: 10000)

  - NEWS_TICKER_LIST_MAX: max articles per ticker cache key (default: 100)

  AnalyzerOptions is constructed from settings at startup and passed to

  FinlightDataProcessor, which forwards it to FinlightDataAnalyzer.

  Cache limits can now be tuned per deployment via environment variables

  without code changes.

- `04d2a0c <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/04d2a0c>`_ chore: pin kuhl-haus-mdp to 0.3.11 (#43)

  Picks up prev_day_open/high/low fields added to LeaderboardAnalyzer

  symbol metadata (kuhl-haus/kuhl-haus-mdp#55).

  refs #42

- `960e100 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/960e100>`_ fix(wds): use SIGTERM via asyncio.create_task instead of BackgroundTasks+sys.exit (#41)

  BackgroundTasks runs in a thread pool. sys.exit() / SystemExit raised in a

  worker thread only kills that thread — the main uvicorn process keeps running,

  which is why the health checks still passed after /restart was called.

  Fix: use asyncio.create_task() to schedule an async coroutine that calls

  os.kill(os.getpid(), signal.SIGTERM) after 500ms. This runs in the event

  loop and signals the actual process, which uvicorn handles gracefully.

  k8s restartPolicy:Always then brings up a fresh instance.

- `491dee4 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/491dee4>`_ Change /restart route from POST to GET

  Update the FastAPI route decorator so the /restart endpoint accepts GET requests instead of POST (status_code remains 200). No other logic in the handler was modified; clients that previously POST to /restart will need to use GET after this change.

- `67c9e17 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/67c9e17>`_ feat(wds): add POST /restart endpoint for operational recovery (refs #39) (#40)

  When WDS enters a failed state (pub/sub delivery stops), the recovery

  path required k8s deployment rollout. POST /restart provides a simpler

  alternative: returns 200 immediately, then exits with code 0 after

  500ms. Kubernetes restartPolicy:Always brings up a fresh instance.

  Use case: quick recovery from pub/sub stall without k8s access.

  Endpoint is unauthenticated (WDS is internal-only, not externally exposed).

- `083122e <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/083122e>`_ chore: pin kuhl-haus-mdp to v0.3.10 (#37)

  v0.3.10 fixes quote:{symbol} pub/sub — now published on every agg

  event from every LBA instance, not just on throttled leaderboard

  publish. Quote widget now updates live.

- `8ef7f77 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/8ef7f77>`_ chore: pin kuhl-haus-mdp to v0.3.9 (#36)

  v0.3.9 fixes two bugs in widget_data_service._handle_pubsub():

  - RuntimeError on concurrent disconnect (set iteration snapshot)

  - TypeError in logger.error() exc_info call

  Reported in kuhl-haus-mdp-servers#35.

- `eeca730 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/eeca730>`_ chore: pin kuhl-haus-mdp to v0.3.8 (#34)

  v0.3.8 adds per-symbol quote pub/sub feed (quote:{symbol}) via

  LeaderboardAnalyzer for the upcoming Quote widget.

- `0f3f636 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/0f3f636>`_ Bump kuhl-haus-mdp to 0.3.7

  Update pyproject.toml to require kuhl-haus-mdp==0.3.7 (was 0.3.6). This increments the dependency version to pick up the latest fixes or improvements in the kuhl-haus-mdp package.

- `d9a26eb <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/d9a26eb>`_ feat(wds_server): extract optional limit from get action (closes #47 step 2) (#33)

  * test(wds_server): add tests for get action limit param

  Tests assert that limit is extracted from the message and passed to

  get_cache(). Tests fail at this commit (red phase).

  * test(wds_server): add tests for get action limit param

  Tests assert limit=0 (default) and limit=N are extracted from the

  message and passed to get_cache(). Tests pass at this commit (green).

  * feat(wds_server): extract optional limit from get action and pass to get_cache (closes #47 step 2)

  Extract optional limit field from get cache messages and pass to

  get_cache(cache_key, limit=limit). Default is 0 (fetch all).

  Document the limit variant in the websocket endpoint docstring.


Version 0.2.1 (2026-03-27)
==========================

- `2fb72ba <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/2fb72ba>`_ ci: add test step to build-package job in publish-to-pypi workflow (#32)
- `c6329d3 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/c6329d3>`_ docs: add FDL and FDP servers to README (#31)

Version 0.2.0 (2026-03-26)
==========================

- `8426bd7 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/8426bd7>`_ replace MARKET_DATA_LISTENER_AUTO_START_ENABLED with discrete vars

  Replace the shared MARKET_DATA_LISTENER_AUTO_START_ENABLED with service-specific variables:

  MDL: MDL_AUTO_START_ENABLED

  FDL: FDL_AUTO_START_ENABLED

  Related: https://github.com/kuhl-haus/kuhl-haus-mdp/pull/43

- `a8cf961 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/a8cf961>`_ Bump kuhl-haus-mdp to version 0.3.6

  https://github.com/kuhl-haus/kuhl-haus-mdp/pull/42

- `6dbdc3e <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/6dbdc3e>`_ Bump kuhl-haus-mdp to 0.3.5

  Update dependency version in pyproject.toml from kuhl-haus-mdp 0.3.4 to 0.3.5. This pulls in the latest patch release for kuhl-haus-mdp (likely bug fixes or minor improvements). No other changes in this changeset.

  https://github.com/kuhl-haus/kuhl-haus-mdp-servers/issues/29

- `a2eba0b <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/a2eba0b>`_ Bump kuhl-haus-mdp to 0.3.4

  Update pyproject.toml to bump the kuhl-haus-mdp dependency from 0.3.2 to 0.3.4 to pick up upstream fixes and improvements. No other changes included in this commit.

- `3b160e5 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/3b160e5>`_ docs: update CLAUDE.md — no requirements.txt, use pip install .[testing] (#28)
- `d440b91 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/d440b91>`_ Support selectable Finlight listener and update defaults

  Introduce dynamic listener selection and modernize server defaults.

  - Add FINLIGHT_DATA_LISTENER_CLASS setting (default FinlightSimpleListener) and import FinlightSimpleListener.

  - Instantiate listener class at startup from a small registry (FinlightSimpleListener or FinlightDataListener), build appropriate kwargs, and raise ValueError for unknown classes.

  - Rename module globals to `fdq` and `fdl` and update all usages (start/stop/restart, health, settings endpoints).

  - Switch Finlight queues API usage to pass `queues` to listeners (instead of message_handler) and include SimpleListener-specific kwargs.

  - Update Settings defaults: message_ttl_ms -> 900000, finlight_language -> "en", and default parsing for TICKERS/SOURCES to use "*" when provided.

  - Add asyncio import and typing Union for listener typing.

  - Update and extend tests to patch FinlightSimpleListener, validate new defaults, assert listener instantiation behavior, and add tests for selecting FinlightDataListener and for invalid listener class handling.

  These changes allow selecting between listener implementations at runtime and align defaults with current operational expectations.

- `a2fd803 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/a2fd803>`_ Add FDL/FDP Docker image build steps

  Add GitHub Actions steps to build and push FDL and FDP Docker images (and their OTel auto-instrumented variants) using docker/build-push-action@v6. Each step builds from its respective Dockerfile (fdl.Dockerfile, fdl_otel.Dockerfile, fdp.Dockerfile, fdp_otel.Dockerfile), targets linux/amd64, pushes to GHCR with both ${env.IMAGE_TAG} and latest tags, and uses GHA caching. These steps publish additional service images.

- `e3e33f7 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/e3e33f7>`_ feat: wire FinlightDataAnalyzer into fdp_server (#27)
- `5ce6ed9 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/5ce6ed9>`_ chore: consolidate deps into pyproject.toml, delete requirements txt files (closes #25) (#26)

  - Pin kuhl-haus-mdp==0.3.2 in pyproject.toml [project.dependencies]

  - Add importlib_metadata, setuptools-scm to pyproject.toml

  - Add pdm and setuptools-scm to [project.optional-dependencies].testing

  - All Dockerfiles: replace requirements.txt install with pip install .

  - LBA and MDP Dockerfiles: restore uvicorn params (timeout, proxy-headers, etc.)

  - LBA port corrected to 4210

  - build-images.yml + publish-to-pypi.yml: replace requirements-build.txt with pip install .[testing]

  - Delete requirements.txt and requirements-build.txt

- `e6f66f0 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/e6f66f0>`_ ci: add test and Codecov coverage step to build-images workflow (#21)

  * ci: add test and Codecov coverage step to build-images workflow

  Adds a build-and-test job that runs before build-docker:

  - Installs package with testing extras (pytest, pytest-asyncio, etc.)

  - Runs pytest with branch coverage reporting

  - Uploads coverage artifact on every run

  - Uploads to Codecov on tag pushes only (matching publish-to-pypi.yml pattern)

  build-docker now depends on build-and-test.

  Co-Authored-By: Tom Pounders <git@oldschool.engineer>

  * ci: add pull_request trigger; skip Docker build on PRs

  Tests now run on every PR via build-and-test job.

  build-docker is gated on non-PR events to avoid pushing

  images on every PR.

  Co-Authored-By: Tom Pounders <git@oldschool.engineer>

  ---------

  Co-authored-by: Tom Pounders <git@oldschool.engineer>

- `835955a <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/835955a>`_ fix: update default ports for FDL (4203) and FDP (4204) (#20)

  Port assignments for docker-compose single-host deployment:

  SCP:  8000

  MDL:  4200

  MDP:  4201

  WDS:  4202

  FDL:  4203  (was 4200)

  FDP:  4204  (was 4202)

  LBA:  4210

  Updates fdl_server.py, fdp_server.py, all four Dockerfiles, and the

  FDP test default port assertion.

  Co-authored-by: Tom Pounders <git@oldschool.engineer>

- `862f5d3 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/862f5d3>`_ docs: add Configuration section to README pointing to docs (#19)

  Co-authored-by: Tom Pounders <git@oldschool.engineer>

- `410e15b <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/410e15b>`_ feat: FDP server (FinlightDataProcessor) (#18)

  * test: add FDP server unit tests (TDD — tests first, red phase)

  * feat: implement FDP server (FinlightDataProcessor) (closes #16)

  Adds fdp_server.py FastAPI entry point wrapping FinlightDataProcessor.

  Single async processor consuming from the 'news' queue. Mirrors mdp_server

  pattern but without parallelism (news feed vs. high-throughput tick stream).

  Settings: RABBITMQ_URL, REDIS_URL, FDP_QUEUE_NAME, PREFETCH_COUNT,

  MAX_CONCURRENCY, SERVER_PORT (4202), LOG_LEVEL, CONTAINER_IMAGE, IMAGE_VERSION.

  Also adds fdp.Dockerfile, fdp_otel.Dockerfile, fdp_server entry point

  in pyproject.toml, and FDP rows in CLAUDE.md.

  25 tests, all passing.

  ---------

  Co-authored-by: Tom Pounders <git@oldschool.engineer>

- `24f447f <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/24f447f>`_ feat: FDL server (FinlightDataListener + FinlightDataQueues) (#17)

  * test: add FDL server unit tests (TDD — tests first, red phase)

  * feat: implement FDL server (FinlightDataListener + FinlightDataQueues) (closes #15)

  Adds fdl_server.py FastAPI entry point composing FinlightDataQueues and

  FinlightDataListener. Mirrors mdl_server.py pattern with Finlight-specific

  settings (FINLIGHT_API_KEY, filter params) and endpoints (/query, /tickers,

  /sources, /language, /start, /stop, /restart, /, /health).

  Also adds fdl.Dockerfile, fdl_otel.Dockerfile, fdl_server entry point in

  pyproject.toml, and asgi-lifespan to test dependencies.

  Test fix: added asgi-lifespan LifespanManager to fixtures — httpx 0.28

  ASGITransport does not trigger FastAPI lifespan without it.

  34 tests, all passing.

  Co-Authored-By: Tom Pounders <git@oldschool.engineer>

- `3143516 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/3143516>`_ ci: bump Docker actions to Node.js 24-compatible versions (#12) (#13)
- `15107a5 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/15107a5>`_ docs: update blog links to canonical oldschool-engineer.dev (#10) (#11)
- `ac513d3 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/ac513d3>`_ fix: replace broken dependency submission workflow with component-detection (#9)

  The original workflow used actions/dependency-submission which does not

  exist. Replace with advanced-security/component-detection-dependency-

  submission-action@v0.1.3 (the same action backing GitHub's automatic

  submission), with Python 3.14 configured via setup-python to handle the

  kuhl-haus-mdp>=0.1.17 requirement for Python 3.14.

  Co-authored-by: Tom Pounders <git@oldschool.engineer>

- `abf084b <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/abf084b>`_ fix: add explicit dependency submission workflow for Python 3.14 (#8)

  The GitHub Automatic Dependency Submission (Python) workflow fails because

  it runs pip-compile on Python 3.12 (GHA default), which cannot resolve

  kuhl-haus-mdp>=0.1.17 (all versions require Python >=3.14).

  This explicit workflow uses Python 3.14 and overrides the auto-generated

  submission, resolving the failure.

  Closes #7

  Co-authored-by: Tom Pounders <git@oldschool.engineer>

- `f50d36f <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/f50d36f>`_ docs: add CLAUDE.md and AGENTS.md for AI agent maintainers (#6)

  Closes #5

  Co-authored-by: Tom Pounders <git@oldschool.engineer>


Version 0.1.27 (2026-02-25)
===========================

- `675d276 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/675d276>`_ Bump kuhl-haus-mdp to 0.2.28

  Update requirements.txt to use kuhl-haus-mdp==0.2.28 (was 0.2.27). This applies a patch-level dependency bump to pick up fixes in the new release; no other changes included.

- `3e9c226 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/3e9c226>`_ Bump kuhl-haus-mdp to 0.2.27

  Update requirements.txt to pin kuhl-haus-mdp==0.2.27 (patch bump from 0.2.26). No other dependency changes.

- `0fe5167 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/0fe5167>`_ Add link for Part 5 of the project documentation

Version 0.1.26 (2026-02-23)
===========================

- `328305c <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/328305c>`_ Scale HALTS processors with parallelism

  Replace the single HALTS MassiveDataProcessor startup with a loop that creates settings.parallelism workers. Each worker is named mdp_HALTS_<i>, started via process_manager.start_worker, and appended to massive_data_processors. This aligns HALTS with other queues' parallelism to improve throughput and consistency.


Version 0.1.25 (2026-02-23)
===========================

- `e588788 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/e588788>`_ Bump kuhl-haus-mdp to 0.2.26

  Update requirements.txt to use kuhl-haus-mdp==0.2.26 (was 0.2.24). Patch bump for the kuhl-haus-mdp dependency.

- `5ad6e88 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/5ad6e88>`_ Update README badges and expand content

  Replace GitHub release badge with Pepy downloads badge and adjust badge ordering. Rework README overview into a concise package description and add a new "Servers" section describing MDL, MDP, LBA, and WDS. Introduce a Container Images table (Dockerfile variants and entry points) and note OpenTelemetry variants and base image usage. Add a Documentation link and remove the large legacy "Components Summary"/architecture sections to simplify and focus the README on containerized server artifacts and usage.

- `08cd679 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/08cd679>`_ Replace README.md with README.rst

  Convert repository README from Markdown to reStructuredText: remove README.md and add README.rst with the migrated content. Delete the local docs/Market_Data_Processing_C4.png (diagram now referenced remotely in the new RST). Update pyproject.toml to point readme = "README.rst".

- `29b68e9 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/29b68e9>`_ Bump kuhl-haus-mdp to 0.2.24

  Update requirements.txt to use kuhl-haus-mdp==0.2.24 (was 0.2.20). No other dependency changes.


Version 0.1.24 (2026-02-19)
===========================

- `cbc588e <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/cbc588e>`_ Update README and bump kuhl-haus-mdp to 0.2.20

  Expand README with a clear project overview, architecture, key features, component summaries, and links to related repositories and blog posts; add detailed code-library references for MDL, MDQ, MDP, MDC, WDS, SCP, and miscellaneous helpers to help developers navigate the codebase. Also bump kuhl-haus-mdp dependency from 0.2.19 to 0.2.20 in requirements.txt.


Version 0.1.23 (2026-02-19)
===========================

- `a976c6a <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/a976c6a>`_ Bump kuhl-haus-mdp to 0.2.19

  Update requirements.txt to pin kuhl-haus-mdp at 0.2.19 (was 0.2.17). This brings in upstream fixes/updates for that package; no other dependencies were modified.


Version 0.1.22 (2026-02-18)
===========================

- `8002a83 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/8002a83>`_ Add publisher_confirms setting and bump mdp

  Introduce a new Settings field (publisher_confirms) driven by MDQ_PUBLISHER_CONFIRMS (defaults to true) to control RabbitMQ publisher confirms, and pass it to MassiveDataQueues during app lifespan setup. Also bump kuhl-haus-mdp to 0.2.17 in requirements.txt to align with the change.

  https://github.com/kuhl-haus/kuhl-haus-mdp/issues/3


Version 0.1.21 (2026-02-18)
===========================

- `59fce46 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/59fce46>`_ Move OpenTelemetry deps to Dockerfiles

  Update OT setup: install opentelemetry-distro in all *_otel.Dockerfile files (removed the --no-cache-dir flag) and tidy mdl_otel.Dockerfile formatting. Remove individual OpenTelemetry packages (opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-otlp) from pyproject.toml so instrumentation is provided by the container image instead of project deps. Affects: lba_otel.Dockerfile, mdl_otel.Dockerfile, mdp_otel.Dockerfile, wds_otel.Dockerfile, and pyproject.toml.

  https://github.com/kuhl-haus/kuhl-haus-mdp/issues/3


Version 0.1.20 (2026-02-18)
===========================

- `fc5e882 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/fc5e882>`_ Bump kuhl-haus-mdp to 0.2.16

  Update requirements.txt to use kuhl-haus-mdp==0.2.16 (was 0.2.15) to pick up the latest package fixes/updates.

- `51ab1dd <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/51ab1dd>`_ Group MDP processors by queue and spawn workers

  Refactor MDP server to track processors per queue type (aggregate, trades, quotes, halts) by replacing the flat list with a dict. Add imports for MassiveDataAnalyzer and TopTradesAnalyzer and spawn queue-specific MassiveDataProcessor workers: multiple workers for AGGREGATE/TRADES/QUOTES (using TopTradesAnalyzer for trades and MassiveDataAnalyzer for quotes) and a single worker for HALTS. Update health_check to report processor statuses grouped by queue type and adjust naming scheme for started workers.

- `70058cc <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/70058cc>`_ Install opentelemetry-distro in OTel-specific Dockerfiles

  Add explicit pip install of opentelemetry-distro to lba_otel, mdl_otel, mdp_otel and wds_otel Dockerfiles. Remove OpenTelemetry packages (opentelemetry-distro from pyproject.toml and opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-otlp, opentelemetry-distro from requirements.txt) and bump kuhl-haus-mdp to 0.2.15. This moves the OpenTelemetry distro installation into the container build, ensuring the distro is present at runtime and avoiding duplicating it as a project dependency.

  https://github.com/kuhl-haus/kuhl-haus-mdp/issues/3

- `9782d38 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/9782d38>`_ Add OTel Dockerfiles and update workflow

  Introduce OpenTelemetry auto-instrumented Dockerfiles for MDL, MDP, LBA, and WDS (mdl_otel.Dockerfile, mdp_otel.Dockerfile, lba_otel.Dockerfile, wds_otel.Dockerfile) and update GitHub Actions (build-images.yml) to build and push both standard and OTel variants. Remove opentelemetry-bootstrap from the shared base Dockerfiles and adjust non-OTel CMDs to run uvicorn directly (no opentelemetry-instrument). Also reorder the workflow so the server base image is built last. These changes add explicit OTel images while reverting the standard images to pre-v0.1.14 behavior.

  https://github.com/kuhl-haus/kuhl-haus-mdp/issues/3

- `a4aba82 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/a4aba82>`_ Revert distributed tracing changes introduced in MDL v0.1.18

  Update requirements.txt to upgrade kuhl-haus-mdp from 0.2.13 to 0.2.14 to revert distributed tracing changes to MDL.

  https://github.com/kuhl-haus/kuhl-haus-mdp/issues/3


Version 0.1.19 (2026-02-13)
===========================

- `a060570 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/a060570>`_ Bump kuhl-haus-mdp to 0.2.13

  Update requirements.txt to upgrade kuhl-haus-mdp from 0.2.12 to 0.2.13 (patch version bump). No other dependencies were changed.


Version 0.1.18 (2026-02-13)
===========================

- `18afe8b <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/18afe8b>`_ Bump kuhl-haus-mdp to 0.2.12

  Update requirements.txt to use kuhl-haus-mdp==0.2.12 (was 0.2.11). This upgrades the dependency to the latest patch release; pull in any bug fixes or minor improvements provided by the new version.

- `00a9754 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/00a9754>`_ Add OpenTelemetry deps and bump kuhl-haus-mdp

  Add opentelemetry-distro and opentelemetry-exporter-otlp to pyproject.toml to enable the OpenTelemetry distro and OTLP exporting. Also bump kuhl-haus-mdp from 0.2.10 to 0.2.11 in requirements.txt (patch dependency update).

  https://github.com/kuhl-haus/kuhl-haus-mdp-servers/issues/2

- `58b85b3 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/58b85b3>`_ Bump kuhl-haus-mdp to 0.2.10

  Update requirements.txt to pin kuhl-haus-mdp at 0.2.10 (previously 0.2.9). No other dependency lines were changed; this ensures the project uses the latest upstream release.

- `322589c <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/322589c>`_ Add OpenTelemetry observability to WDS

  Introduce OpenTelemetry tracing and metrics to the Widget Data Service websocket server. Adds a new src/kuhl_haus/servers/observability.py module that exposes get_tracer/get_meter (with package version fallback) and wires opentelemetry dependencies into pyproject.toml and requirements.txt. Instrument wds_server: create tracer/meter and counters (exceptions, unauthorized_exceptions, disconnects, auth, subscribe, unsubscribe, cache_get), add tracing spans around auth and message processing, and increment relevant metrics on events and errors to improve monitoring and troubleshooting of websocket flows.

  https://github.com/kuhl-haus/kuhl-haus-mdp-servers/issues/2


Version 0.1.17 (2026-02-11)
===========================

- `0b712c3 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/0b712c3>`_ Use structured logging in servers

  Bump kuhl-haus-mdp to 0.2.9 and switch server modules (lba_server, mdl_server, mdp_server, wds_server) to a centralized structured logging setup. Import and call kuhl_haus.mdp.helpers.structured_logging.setup_logging(settings.log_level) and remove the previous per-file logging_format and direct logging.root configuration. Also stop passing a logger into MassiveDataQueues/MassiveDataListener in mdl_server. This centralizes log formatting and level configuration across servers.

- `6c1e39a <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/6c1e39a>`_ Run build-images workflow on mainline and v* tags

  Update the workflow push triggers: normalize the branches key to a list (mainline) and add a tags pattern ('v*') so the build-images workflow runs on version tags as well as pushes to the mainline branch. This ensures image builds are produced for release tags (e.g., v1.0).

- `5c8b018 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/5c8b018>`_ Bump kuhl-haus-mdp to 0.2.7

  Update requirements.txt to pin kuhl-haus-mdp at 0.2.7 (was 0.2.6). This brings in the latest patch release of kuhl-haus-mdp; no other dependency changes were made.


Version 0.1.16 (2026-02-09)
===========================

- `34b7f36 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/34b7f36>`_ Bump kuhl-haus-mdp to 0.2.6

  Update requirements.txt to pin kuhl-haus-mdp at 0.2.6 (previously 0.2.5) to keep the dependency version current.

- `16c057f <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/16c057f>`_ Bump kuhl-haus-mdp to 0.2.5

  Update requirements.txt to use kuhl-haus-mdp==0.2.5 instead of 0.2.4. This upgrades the package to the latest patch release which may include bug fixes or minor improvements.

- `6f47b25 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/6f47b25>`_ Bump kuhl-haus-mdp to 0.2.4

  Update requirements.txt to pin kuhl-haus-mdp==0.2.4 (previously 0.2.3). This upgrades the package to the new patch release; no other dependencies were modified.


Version 0.1.15 (2026-02-06)
===========================

- `3d80297 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/3d80297>`_ Removed old status dict from LBA/MDP health checks
- `e4af0ba <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/e4af0ba>`_ Upgrade to kuhl-haus-mdp 0.2.3
- `35f01df <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/35f01df>`_ Oops... processors, not processes
- `f171ee5 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/f171ee5>`_ Adjusting health check output on MDP and LBA

  This will make it easier to scrape via prometheus + json_exporter

- `c0b8863 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/c0b8863>`_ Upgrade to kuhl-haus-mdp 0.2.2

  * Taking in MDP metrics changes

  * Adding parallelism, max_concurrency, and prefetch_count to health check

- `50701e7 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/50701e7>`_ Upgrade to kuhl-haus-mdp v0.2.1
- `de860d7 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/de860d7>`_ Added parallelism to MDP server

  * Removed all API except for the health check. (It was janky as hell even when it did work.  Easier to just restart the pod.)

  * MDP will be treated as a vertically scalable component capable of running many high concurrency workloads in parallel. (i.e., it will run all multiple analyzers where LBA server only runs the Leaderboard Analyzer)

- `044295f <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/044295f>`_ FINALLY fixed the Pydantic error

  Seriously... /facepalm I should've thought a little more critically about the error and looked at the code.  Ugh!

- `b194185 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/b194185>`_ Fixed PydanticUserError due to non-annotated attribute

  pydantic.errors.PydanticUserError: A non-annotated attribute was detected: `logging_format_json = '{ "timestamp": "%(asctime)s", "filename": "%(filename)s", "function": "%(funcName)s", "line": "%(lineno)d", "level": "%(levelname)s", "pid": "%(process)d", "thr": "%(thread)d", "message": "%(message)s"}'`. All model fields require a type annotation; if `logging_format_json` is not meant to be a field, you may be able to resolve this error by annotating it as a `ClassVar` or updating `model_config['ignored_types']`.

  For further information visit https://errors.pydantic.dev/2.12/u/model-field-missing-annotation

- `1f5d9d6 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/1f5d9d6>`_ Added logging format option plus LBA options tweak

  * Default logging to JSON format.  Override via LOGGING_FORMAT environment variable.  (Example: export LOGGING_FORMAT='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

  * Added PREFETCH_COUNT and MAX_CONCURRENCY environment variable overrides for LBA server.

  PREFETCH_COUNT: Number of messages to fetch from RabbitMQ

  MAX_CONCURRENCY: Maximum number of messages to handle concurrently

- `9d72b4e <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/9d72b4e>`_ [0.2.0] Leaderboard Analyzer

  * MDP server runs a single-process version of LBA

  * LBA server runs multi-process version of LBA


Version 0.1.14 (2026-02-04)
===========================

- `b0bd7d6 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/b0bd7d6>`_ Python 3.14 Upgrade + Add OTEL

  https://opentelemetry.io/docs/zero-code/python/

- `628e8d2 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/628e8d2>`_ Add 'service' to health check output on WDS and MDP

Version 0.1.13 (2026-02-02)
===========================

- `c103bb5 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/c103bb5>`_ Oops
- `bc19b5d <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/bc19b5d>`_ Adding status_code output for JSON-export/Prometheus integration
- `1351d91 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/1351d91>`_ Change WDS health check status to int from string

  Testing support for Prometheus scraping via json-exporter


Version 0.1.12 (2026-01-14)
===========================

- `4f199e0 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/4f199e0>`_ Upgrade to kuhl-haus-mdp v0.1.16

Version 0.1.11 (2026-01-13)
===========================

- `d0de498 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/d0de498>`_ Upgrade to kuhl-haus-mdp v0.1.15

Version 0.1.10 (2026-01-09)
===========================

- `8823243 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/8823243>`_ Upgrade to kuhl-haus-mdp 0.1.14
- `2dbfe2d <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/2dbfe2d>`_ Upgrade to kuhl-haus-mdp v0.1.13
- `fe33cde <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/fe33cde>`_ Default MDL subscriptions - firehose mode

  All supported subscription types are enabled by default. Override in environment variables or get everything - firehose mode is now the default mode.


Version 0.1.9 (2026-01-08)
==========================

- `cfa6f7f <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/cfa6f7f>`_ kuhl-haus-mdp v0.1.12

Version 0.1.8 (2026-01-08)
==========================

- `d22a30c <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/d22a30c>`_ kuhl-haus-mdp v0.1.11

Version 0.1.7 (2026-01-06)
==========================

- `196ad12 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/196ad12>`_ Upgrade to MDP 0.1.10
- `dfb8136 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/dfb8136>`_ Upgrade to kuhl-haus-mdp v0.1.9

Version 0.1.6 (2026-01-05)
==========================

- `834ed8e <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/834ed8e>`_ Upgrade to MDP version 0.1.8

  Fix the MASSIVE_SUBSCRIPTIONS environment variable import.

- `039e780 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/039e780>`_ Update to kuhl-haus-mdp v0.1.7
- `af537e2 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/af537e2>`_ Update to kuhl-haus-mdp v0.1.6
- `a984076 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/a984076>`_ Add badge for publishing to PyPI

Version 0.1.5 (2025-12-31)
==========================

- `e18a002 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/e18a002>`_ Upgrade to MDP 0.1.3
- `4cb51e9 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/4cb51e9>`_ Update publish-to-pypi.yml

  only release on tag pushes

- `3409a38 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/3409a38>`_ Build images on mainline; PyPI on mainline + tagged

Version 0.1.4 (2025-12-30)
==========================

- `9681212 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/9681212>`_ kuhl-haus-mdp 0.1.1
- `ce4695e <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/ce4695e>`_ Add local dev files to .gitignore

Version 0.1.3 (2025-12-29)
==========================

- `ad4cb4e <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/ad4cb4e>`_ Version locked to kuhl-haus-mdp==0.1.0
- `ef0fd84 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/ef0fd84>`_ Set default massive sub to AM.*
- `a6805cf <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/a6805cf>`_ Removed restart functionality on WDS
- `605d0ee <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/605d0ee>`_ Added component description.

Version 0.1.2 (2025-12-28)
==========================

- `203822b <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/203822b>`_ only release on tag pushes
- `ab97d24 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/ab97d24>`_ Add github release as dependency for publishing to test PyPI
- `9cf320b <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/9cf320b>`_ Fixed LICENSE path
- `cc37ba9 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/cc37ba9>`_ Change build backend to PDM

Version 0.1.1 (2025-12-28)
==========================

- `e0ed72e <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/e0ed72e>`_ [patch] Mitigate information exposure through an exception

  https://github.com/kuhl-haus/kuhl-haus-mdp-servers/security/code-scanning/2

- `b664cad <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/b664cad>`_ Create SECURITY.md
- `300fbe5 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/300fbe5>`_ Update .gitignore

Version 0.1.0 (2025-12-26)
==========================

- `95034b3 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/95034b3>`_ Dynamic versioning
- `4aa5f05 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/4aa5f05>`_ Add base image build

Version 0.0.3 (2025-12-26)
==========================

- `69f4c4d <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/69f4c4d>`_ v0.0.3
- `5c23edb <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/5c23edb>`_ Fixed 'need' import missed after renaming build-and-test to build-package

Version 0.0.2 (2025-12-26)
==========================

- `fa428ba <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/fa428ba>`_ version 0.0.2
- `787208b <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/787208b>`_ Install build dependencies for PyPI publication

Version 0.0.1 (2025-12-26)
==========================

- `de78d3e <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/de78d3e>`_ Fixed workflow names
- `b0d51f4 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/b0d51f4>`_ Create publish-to-pypi.yml
- `bd569ea <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/bd569ea>`_ Removed commented out code
- `fe2c0c7 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/fe2c0c7>`_ Fix mdp server package name permission denied error
- `0feb16a <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/0feb16a>`_ Remove Github release; not needed
- `31a3092 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/31a3092>`_ Create GitHub Release
- `21f975e <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/21f975e>`_ Initial commit
- `a44f4b2 <https://github.com/kuhl-haus/kuhl-haus-mdp-servers/commit/a44f4b2>`_ Initial commit

