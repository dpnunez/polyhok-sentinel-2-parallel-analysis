# NDVI via PolyHok Prototype Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: activate it by name and
follow its Execute flow and Critical Rules. The skill governs the per-task gate,
atomic commit, adequacy review, independent Verifier and discrimination sensor.

**If the skill cannot be activated, STOP and tell the user.**

**Design**: `.specs/features/ndvi-polyhok-prototype/design.md`
**Status**: Done

## Test Coverage Matrix

> Generated from `README.md`, `docs/ndvi-numerical-contract.md`, `mix.exs`,
> `test/test_helper.exs`, existing ExUnit tests and the feature spec. No
> repository-wide coverage policy exists, so strong defaults apply. CUDA tests
> remain explicit and opt-in.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| NDVI calculation and input validation | unit + GPU integration | Every NDVI-01..22 outcome covered by assertions or structural source evidence; all six approved pixels execute together | `test/sentinel_2/ndvi_test.exs` | `mix test --exclude gpu test/sentinel_2/ndvi_test.exs` |
| PolyHok CUDA kernel boundary | GPU integration | One `2x3` launch proves finite, NaN, order, type, shape and non-block-multiple behavior; one `1x1` launch proves the smallest nonzero float32 is divided without epsilon | `test/sentinel_2/ndvi_test.exs` | `mix test --include gpu test/sentinel_2/ndvi_test.exs` |
| NDVI result persistence | unit | Every NDVI-23..27 field, byte, checksum and failure-publication outcome maps to an assertion | `test/sentinel_2/ndvi_result_writer_test.exs` | `mix test --exclude gpu test/sentinel_2/ndvi_result_writer_test.exs` |

## Gate Check Commands

> Generated from `README.md`, `mix.exs` and the existing test profiles.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | CPU-only unit feedback | `mix test --exclude gpu` |
| Full | NDVI kernel task | `mix test --exclude gpu && mix test --include gpu test/sentinel_2/ndvi_test.exs` |
| Build | Final phase completion | `python/.venv/bin/python -m ruff check python && python/.venv/bin/python -m pytest python/tests -q && mix format --check-formatted && mix compile --warnings-as-errors && mix test --exclude gpu && mix test --include gpu test/sentinel_2/ndvi_test.exs` |

## Execution Plan

Tasks execute sequentially in one phase.

```text
Phase 1: T1 -> T2
```

## Task Breakdown

### Phase 1: Prototype

#### T1: Implement the NDVI GPU operation

**What**: Add the public NDVI calculation module with structural validation and
separate H2D, single-kernel and D2H operations.
**Where**: `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex`
**Depends on**: None
**Reuses**: `PolyHok.new_gnx/1`, `Ske.map2/3`, `PolyHok.get_gnx/1`.
**Requirement**: NDVI-01 through NDVI-22.

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [x] Invalid non-tensor, type, rank, empty and mismatched inputs raise `ArgumentError` before GPU access.
- [x] `compute/2` composes the three public boundaries in H2D, kernel and D2H order.
- [x] `run_kernel/2` invokes `Ske.map2/3` once with the exact float32 NDVI policy and no CPU implementation.
- [x] One tagged `2x3` GPU test asserts the three finite literals, three NaNs, type, shape and pixel order; a tagged `1x1` case asserts the smallest nonzero float32 is divided.
- [x] Full gate passes with 53 CPU tests and 8 selected NDVI tests, with no disabled new tests.

**Tests**: unit + GPU integration in `test/sentinel_2/ndvi_test.exs`
**Gate**: full
**Commit**: `feat(ndvi): add PolyHok GPU calculation`

#### T2: Persist NDVI results atomically

**What**: Add the explicit result writer for a little-endian float32 binary and
metadata-last JSON publication.
**Where**: `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi/result_writer.ex`
**Depends on**: T1
**Reuses**: `PreparedReader.normalize_little_endian/2`, Jason, `:crypto`.
**Requirement**: NDVI-23 through NDVI-27.

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [x] A valid tensor writes exact headerless bytes and all seven metadata fields with matching SHA-256.
- [x] Re-reading the binary preserves finite and NaN positions, shape and row-major order.
- [x] Invalid tensors and controlled I/O failures return errors without publishing final metadata.
- [x] Publication renames the validated binary before renaming metadata into its final path.
- [x] Build gate passes with at least 56 CPU tests and no disabled new tests.

**Tests**: unit in `test/sentinel_2/ndvi_result_writer_test.exs`
**Gate**: build
**Commit**: `feat(ndvi): persist NDVI result artifacts`

## Phase Execution Map

```text
Phase 1: T1 ------> T2
```

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1 | One calculation module plus co-located tests | Granular |
| T2 | One persistence module plus co-located tests | Granular |

## Diagram-Definition Cross-Check

| Task | Depends On | Diagram Shows | Status |
| ---- | ---------- | ------------- | ------ |
| T1 | None | No incoming edge | Match |
| T2 | T1 | T1 -> T2 | Match |

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | NDVI calculation and CUDA boundary | unit + GPU integration | unit + GPU integration | OK |
| T2 | NDVI result persistence | unit | unit | OK |

## Requirement Traceability

| Task | Requirements | Status |
| ---- | ------------ | ------ |
| T1 | NDVI-01 through NDVI-22 | Done |
| T2 | NDVI-23 through NDVI-27 | Done |
