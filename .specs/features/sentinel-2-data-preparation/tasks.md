# Sentinel-2 Data Preparation Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** The skill is the source of truth for the per-task cycle, adequacy review, atomic commits, Verifier and discrimination sensor.

**If the skill cannot be activated, STOP and tell the user.**

**Design**: `.specs/features/sentinel-2-data-preparation/design.md`
**Status**: In Progress

## Test Coverage Matrix

> Generated from `README.md`, `docs/sentinel-2-data-preparation.md`, `mix.exs`, existing ExUnit tests and the feature spec. No repository-wide coverage policy exists, so strong defaults apply. The CUDA test is a separate opt-in profile.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Python metadata, raster, artifact and pipeline domain | unit | All branches; 1:1 mapping to PREP/SAFE/EDGE criteria owned by the module | `python/tests/test_*.py` | `python/.venv/bin/python -m pytest python/tests -q` |
| Python CLI | integration | Success plus every documented input, conversion and publication failure path | `python/tests/test_cli.py` | `python/.venv/bin/python -m pytest python/tests/test_cli.py -q` |
| Elixir validator, reader and public API | unit | All tagged-tuple outcomes; 1:1 mapping to ORCH/READ/SAFE/EDGE criteria | `test/sentinel_2/**/*_test.exs` | `mix test --exclude gpu test/sentinel_2` |
| External-process and cross-language boundary | integration | Success, nonzero exit, invalid artifacts, timeout, duplicate scene and Python-to-Elixir values/NaN | `test/integration/**/*_test.exs` | `mix test --exclude gpu test/integration` |
| Project/package configuration and fixture schema | none | Build gate only | `mix.exs`, `python/pyproject.toml`, `fixtures/sentinel-2/` | build gate only |
| Existing PolyHok CUDA integration | opt-in integration | Existing GPU round trip remains executable explicitly | `test/poly_hok_test.exs` | `mix test --include gpu test/poly_hok_test.exs` |

## Gate Check Commands

> Generated from the Mix project, planned PEP 621 project and existing tests. The Python venv is installed once in T1.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Python unit tasks | `python/.venv/bin/python -m pytest python/tests -q` |
| Full | Elixir or integration tasks | `python/.venv/bin/python -m pytest python/tests -q && mix test --exclude gpu` |
| Build | Phase completion or config-only tasks | `python/.venv/bin/python -m ruff check python && python/.venv/bin/python -m pytest python/tests -q && mix format --check-formatted && mix compile --warnings-as-errors && mix test --exclude gpu` |

## Execution Plan

Phases execute sequentially. Tasks execute in order inside each phase.

```text
Phase 1: T1 -> T2 -> T3
Phase 2: T4 -> T5 -> T6 -> T7 -> T8
Phase 3: T9 -> T10 -> T11 -> T12 -> T13
Phase 4: T14 -> T15
```

## Task Breakdown

### Phase 1: Reproducible Foundation

#### T1: Create the Python project and CPU test environment

**What**: Declare the installable Python package, CLI, runtime/dev dependencies, Ruff rules and a smoke test; create the ignored local venv and install the `dev` extra.
**Where**: `python/`
**Depends on**: None
**Reuses**: Python 3.11 decision and PEP 621.
**Requirement**: Success criterion “testes Python e Elixir sem GPU”.

**Tools**:

- MCP: official package documentation already researched
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [x] `python/pyproject.toml` declares Python `>=3.11`, compatible NumPy/Rasterio/Pillow ranges, pytest and Ruff.
- [x] `sentinel2-prepare` resolves to the package CLI.
- [x] `.venv` is ignored and an import smoke test passes.
- [x] Quick gate passes with at least 1 Python test and no skipped tests.

**Tests**: unit
**Gate**: quick
**Commit**: `build(preparation): add Python preparation project`

#### T2: Make the CUDA integration test opt-in

**What**: Tag the existing GPU test and exclude that tag by default without weakening its assertions.
**Where**: `test/`
**Depends on**: T1
**Reuses**: Existing `PolyHokTest` and ExUnit configuration.
**Requirement**: Success criterion “testes Python e Elixir sem GPU”.

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [x] `mix test` omits only the tagged GPU case and all CPU cases pass.
- [x] `mix test --include gpu test/poly_hok_test.exs` still selects the original case.
- [x] No assertion in the CUDA test is changed or removed.
- [x] Full gate passes with at least 2 CPU tests and 0 failures.

**Tests**: unit
**Gate**: full
**Commit**: `test(preparation): make CUDA integration opt-in`

#### T3: Define the versioned fixture index

**What**: Add the empty manifest v1 and fixture instructions while preserving ignore rules for generated data.
**Where**: `fixtures/sentinel-2/`
**Depends on**: T2
**Reuses**: `.gitignore`, normative fixture layout.
**Requirement**: SAFE-07.

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [x] `manifest.json` is valid JSON with `schema_version: 1` and an empty scenes map.
- [x] Fixture README documents source placement, CLI use and versioned/generated files.
- [x] Build gate passes with no generated binary or preview tracked.

**Tests**: none, matrix marks fixture schema/config as build-only
**Gate**: build
**Commit**: `docs(preparation): add Sentinel-2 fixture index`

### Phase 2: Python Producer

#### T4: Discover and parse one Sentinel-2 L2A product

**What**: Implement deterministic discovery of B04, B08 and both metadata XML files plus radiometric and identity parsing.
**Where**: `python/src/sentinel2_prepare/metadata.py`
**Depends on**: T3
**Reuses**: `xml.etree.ElementTree`, filename/layout contract.
**Requirement**: PREP-01, EDGE-01, EDGE-02.

**Tools**:

- MCP: official Sentinel product references in project docs
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [x] One controlled `.SAFE` resolves exactly one product/tile and correct B04/B08/XML paths.
- [x] Offsets, quantification, NODATA and SATURATED are read from XML, never hardcoded.
- [x] Missing, duplicate or invalid required values fail before raster conversion.
- [x] Quick gate passes with at least 8 metadata cases and no skipped tests.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(preparation): parse Sentinel-2 product metadata`

#### T5: Convert aligned raster windows

**What**: Validate complete grid equality, derive the three centered windows and convert each paired window to little-endian float32 with a shared invalid mask.
**Where**: `python/src/sentinel2_prepare/raster.py`
**Depends on**: T4
**Reuses**: Rasterio `Window`, NumPy.
**Requirement**: PREP-02, PREP-03, PREP-04, PREP-05, PREP-06, PREP-07, PREP-13.

**Tools**:

- MCP: official Rasterio window documentation already researched
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [x] Width, height, CRS, transform, pixel size, origin and bounds must all match.
- [x] Offsets equal `floor((tile - crop) / 2)` for 1024, 4096 and 8192.
- [x] Both bands use the same Rasterio window and exact metadata conversion values.
- [x] Any NODATA/SATURATED in either band produces NaN in both outputs.
- [x] No resampling, reprojection, clipping or NDVI operation exists.
- [x] Undersized or misaligned inputs fail without prepared output.
- [x] Quick gate passes with at least 10 raster cases and no skipped tests.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(preparation): convert aligned Sentinel-2 windows`

#### T6: Write and validate crop artifacts

**What**: Write headerless band binaries, complete metadata and paired grayscale preview, then reread and validate the crop.
**Where**: `python/src/sentinel2_prepare/artifacts.py`
**Depends on**: T5
**Reuses**: NumPy `<f4`, Pillow, SHA-256.
**Requirement**: PREP-08, PREP-09, PREP-10, PREP-11.

**Tools**:

- MCP: official Pillow and NumPy package documentation
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [x] Each binary is row-major IEEE 754 `<f4`, headerless and exactly `width * height * 4` bytes.
- [x] Every metadata field from section 7.2 exists with project-relative paths and matching checksums.
- [x] Preview places B04 left/B08 right, uses independent finite p2/p98, black NaN and maximum 2048x1024.
- [x] Reread checks size, dtype, shape, order and checksum before returning success.
- [x] Quick gate passes with at least 8 artifact cases and no skipped tests.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(preparation): publish validated crop artifacts`

#### T7: Commit scenes atomically and reuse only valid output

**What**: Implement the scene transaction, source identity, atomic promotion, manifest-last publication and integrity-based reuse.
**Where**: `python/src/sentinel2_prepare/pipeline.py`
**Depends on**: T6
**Reuses**: AD-002, metadata/raster/artifact modules.
**Requirement**: PREP-12, SAFE-01, SAFE-02, SAFE-03, SAFE-04, SAFE-05, EDGE-04.

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [x] New files use `.partial` in the destination filesystem and are atomically renamed only after validation.
- [x] `manifest.json` is replaced atomically after all three crops validate.
- [x] Failed writes never create a prepared manifest entry; readers can ignore orphan/temporary files.
- [x] Valid existing source, metadata, sizes and checksums return success without changing six binary mtimes.
- [x] Changed source identity or checksum forces regeneration.
- [x] Quick gate passes with at least 8 transaction/reuse cases and no skipped tests.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(preparation): commit prepared scenes atomically`

#### T8: Expose the Python preparation CLI

**What**: Implement argument parsing, stable diagnostics and process exit semantics around the preparation pipeline.
**Where**: `python/src/sentinel2_prepare/cli.py`
**Depends on**: T7
**Reuses**: `prepare_scene/3`, project-relative root.
**Requirement**: PREP-14, EDGE-01, EDGE-02, EDGE-04.

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [x] A valid invocation exits 0 and writes a diagnostic containing the prepared `scene-id`.
- [x] Invalid input, metadata, space/permission and pipeline failures exit nonzero with actionable stderr.
- [x] The success diagnostic is machine-readable JSON without matrix content.
- [x] Build gate passes with at least 5 CLI cases and no skipped tests.

**Tests**: integration
**Gate**: build
**Commit**: `feat(preparation): add Sentinel-2 preparation CLI`

### Phase 3: Elixir Consumer and Orchestrator

#### T9: Start the preparation supervision tree

**What**: Start a unique scene Registry and DynamicSupervisor from the Mix application and add Jason.
**Where**: `mix.exs`
**Depends on**: T8
**Reuses**: OTP Application, Logger, existing Nx transitively through PolyHok.
**Requirement**: ORCH-09, SAFE-06.

**Tools**:

- MCP: official Elixir supervision/Registry documentation already researched
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [x] The application starts Registry and DynamicSupervisor under one-for-one supervision.
- [x] Jason is locked and available without changing the PolyHok dependency.
- [x] Dynamic names use Registry terms rather than generated atoms.
- [x] Full gate passes with at least 3 supervision cases and no skipped tests.

**Tests**: unit
**Gate**: full
**Commit**: `feat(preparation): supervise scene preparation workers`

#### T10: Validate published artifacts in Elixir

**What**: Decode and validate the manifest, three metadata files, six binaries and SHA-256 hashes into a prepared-scene descriptor.
**Where**: `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/artifact_validator.ex`
**Depends on**: T9
**Reuses**: Jason, `:crypto`, AD-002.
**Requirement**: ORCH-05, ORCH-06, ORCH-07, SAFE-03, SAFE-04, SAFE-05, EDGE-05.

**Tools**:

- MCP: official Jason documentation already researched
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [x] Only a prepared manifest entry with exactly 1024, 4096 and 8192 metadata is accepted.
- [x] Paths remain under project root and every metadata field, file size and checksum matches.
- [x] Invalid JSON, missing files, mismatched sizes/checksums or stale source returns `{:error, reason}`.
- [x] Success returns scene ID, relative paths and the three crop metadata maps.
- [x] Full gate passes with at least 7 validator cases and no skipped tests.

**Tests**: unit
**Gate**: full
**Commit**: `feat(preparation): validate prepared scene artifacts`

#### T11: Read prepared bands as Nx tensors

**What**: Load each validated band as little-endian row-major float32 and reshape it without materializing float lists.
**Where**: `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/prepared_reader.ex`
**Depends on**: T10
**Reuses**: Nx BinaryBackend and validated metadata.
**Requirement**: READ-01, READ-02, READ-03, READ-04, READ-05, EDGE-05.

**Tools**:

- MCP: official Nx binary documentation already researched
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [x] Relative paths resolve only from configured project root.
- [x] Byte-size mismatch returns exactly `{:error, :invalid_byte_size}` before `Nx.from_binary/2`.
- [x] Both tensors have type `{:f, 32}`, shape `{height, width}`, row-major values and preserved NaNs.
- [x] Big-endian hosts would swap each 32-bit word before Nx import; little-endian hosts do not copy for swapping.
- [x] Full gate passes with at least 6 reader cases and no skipped tests.

**Tests**: unit
**Gate**: full
**Commit**: `feat(preparation): read prepared bands into Nx tensors`

#### T12: Execute Python in a supervised worker

**What**: Implement the per-scene GenServer that owns a Port, captures diagnostics/status, enforces timeout and logs the terminal result.
**Where**: `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/preparation_worker.ex`
**Depends on**: T11
**Reuses**: Port, Logger, ArtifactValidator.
**Requirement**: ORCH-01, ORCH-03, ORCH-04, ORCH-08, ORCH-10, EDGE-03, EDGE-06.

**Tools**:

- MCP: official Elixir Port and Logger documentation already researched
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [ ] Executable and entrypoint are checked and passed with separate `:args`; no shell interpolation exists.
- [ ] Worker decides only after `{:exit_status, status}` and validates artifacts only for status 0.
- [ ] Nonzero status, missing executable and timeout return the exact documented error class.
- [ ] Timeout closes the Port, remains an error despite late output and never trusts output without validation.
- [ ] One terminal log includes scene ID, duration, result and bounded diagnostic without matrix bytes.
- [ ] Full gate passes with at least 8 controlled-process cases and no skipped tests.

**Tests**: integration
**Gate**: full
**Commit**: `feat(preparation): run Python preparation workers`

#### T13: Expose the composable Elixir preparation API

**What**: Start one uniquely named worker per scene, wait synchronously without blocking schedulers and normalize all outcomes to tagged tuples.
**Where**: `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/preparation.ex`
**Depends on**: T12
**Reuses**: Registry, DynamicSupervisor, PreparationWorker.
**Requirement**: ORCH-02, ORCH-07, ORCH-09, ORCH-11, SAFE-06.

**Tools**:

- MCP: official GenServer/Registry documentation already researched
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [ ] Public return values are only `{:ok, prepared_scene}` or `{:error, reason}`.
- [ ] Caller waits through message receive while unrelated BEAM processes continue running.
- [ ] A second active request for the same scene returns `{:error, :already_running}`.
- [ ] Different workers terminate after success, failure or timeout and release Registry names.
- [ ] Build gate passes with at least 5 API/concurrency cases and no skipped tests.

**Tests**: integration
**Gate**: build
**Commit**: `feat(preparation): expose supervised preparation API`

### Phase 4: Contract Integration

#### T14: Prove the Python-Elixir artifact contract

**What**: Add a controlled cross-language fixture that Python writes and Elixir reads, plus end-to-end process outcome cases.
**Where**: `test/integration/`
**Depends on**: T13
**Reuses**: Python CLI, Preparation API, PreparedReader.
**Requirement**: PREP-11, PREP-14, ORCH-04, ORCH-05, ORCH-06, ORCH-07, ORCH-08, READ-02, READ-04, SAFE-03, SAFE-04, SAFE-06.

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [ ] Python writes controlled finite values and NaNs that Elixir reads with exact type, shape, values and invalid positions.
- [ ] Controlled executable cases prove nonzero, timeout, status-zero-invalid-artifacts and success-plus-valid-artifacts.
- [ ] Interruption leaves no prepared manifest entry; rerun of valid output preserves all six binary mtimes.
- [ ] Concurrent same-scene calls prove one active request and one `:already_running` result.
- [ ] Full gate passes with at least 4 cross-boundary cases and no skipped tests.

**Tests**: integration
**Gate**: full
**Commit**: `test(preparation): verify Python Elixir data contract`

#### T15: Document setup and operation

**What**: Document CPU setup, dependency installation, CLI/API use, validation, regeneration and explicit CUDA test execution; update project notebook pointers.
**Where**: `README.md`
**Depends on**: T14
**Reuses**: fixture README and existing PolyHok integration note.
**Requirement**: SAFE-07 and all feature success criteria.

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`, `codenavi`

**Done when**:

- [ ] A new contributor can install Python dependencies and run both CPU suites from documented commands.
- [ ] CLI arguments, output layout, Elixir API results and regeneration rules are documented.
- [ ] GPU test remains documented as explicit opt-in.
- [ ] `.notebook/INDEX.md` points to a concise preparation-flow note.
- [ ] Build gate passes with all CPU tests and no skipped tests.

**Tests**: none, matrix marks documentation as build-only
**Gate**: build
**Commit**: `docs(preparation): document data preparation workflow`

## Phase Execution Map

```text
Phase 1: T1 -> T2 -> T3
Phase 2: T4 -> T5 -> T6 -> T7 -> T8
Phase 3: T9 -> T10 -> T11 -> T12 -> T13
Phase 4: T14 -> T15
```

Cross-phase dependencies are the last task of the previous phase into the first task of the next phase. Within-phase arrows match each task body exactly.

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1 | One installable Python project | ✅ Granular |
| T2 | One test-profile change | ✅ Granular |
| T3 | One fixture index/schema | ✅ Granular |
| T4 | One metadata/discovery module | ✅ Granular |
| T5 | One raster conversion module | ✅ Granular |
| T6 | One artifact module | ✅ Granular |
| T7 | One scene transaction module | ✅ Granular |
| T8 | One CLI module | ✅ Granular |
| T9 | One supervision-tree change | ✅ Granular |
| T10 | One validator module | ✅ Granular |
| T11 | One reader module | ✅ Granular |
| T12 | One worker module | ✅ Granular |
| T13 | One public API module | ✅ Granular |
| T14 | One cross-language contract suite | ✅ Granular |
| T15 | One operational documentation deliverable | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | phase start | ✅ Match |
| T2 | T1 | T1 -> T2 | ✅ Match |
| T3 | T2 | T2 -> T3 | ✅ Match |
| T4 | T3 | cross-phase boundary | ✅ Match |
| T5 | T4 | T4 -> T5 | ✅ Match |
| T6 | T5 | T5 -> T6 | ✅ Match |
| T7 | T6 | T6 -> T7 | ✅ Match |
| T8 | T7 | T7 -> T8 | ✅ Match |
| T9 | T8 | cross-phase boundary | ✅ Match |
| T10 | T9 | T9 -> T10 | ✅ Match |
| T11 | T10 | T10 -> T11 | ✅ Match |
| T12 | T11 | T11 -> T12 | ✅ Match |
| T13 | T12 | T12 -> T13 | ✅ Match |
| T14 | T13 | cross-phase boundary | ✅ Match |
| T15 | T14 | T14 -> T15 | ✅ Match |

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Python package/config | unit smoke | unit | ✅ OK |
| T2 | ExUnit test profile | unit | unit | ✅ OK |
| T3 | Fixture config/schema | none | none | ✅ OK |
| T4 | Python metadata domain | unit | unit | ✅ OK |
| T5 | Python raster domain | unit | unit | ✅ OK |
| T6 | Python artifact domain | unit | unit | ✅ OK |
| T7 | Python pipeline domain | unit | unit | ✅ OK |
| T8 | Python CLI | integration | integration | ✅ OK |
| T9 | Elixir config/supervision | unit | unit | ✅ OK |
| T10 | Elixir validator | unit | unit | ✅ OK |
| T11 | Elixir reader | unit | unit | ✅ OK |
| T12 | External process worker | integration | integration | ✅ OK |
| T13 | Public/concurrency API | integration | integration | ✅ OK |
| T14 | Cross-language boundary | integration | integration | ✅ OK |
| T15 | Documentation | none | none | ✅ OK |
