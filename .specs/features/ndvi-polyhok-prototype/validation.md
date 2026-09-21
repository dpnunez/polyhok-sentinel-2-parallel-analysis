# Validation: ndvi-polyhok-prototype - PASS ✅

**Date**: 2026-09-21
**Spec**: `.specs/features/ndvi-polyhok-prototype/spec.md`  
**Diff range**: `35f20db..bbf674e`
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 | ✅ Done | GPU calculation, validation and measurable boundaries are implemented; Full and Build gates pass. |
| T2 | ✅ Done | Binary and metadata persistence are implemented; Build gate passes. |
| T3 | ✅ Done | Signed-zero and unclamped-output assertions are present and discriminating. |
| T4 | ✅ Done | The metadata-last failure assertion kills early-metadata publication. |

All four tasks are marked done in `tasks.md`. No task is partial or blocked.

## Spec-Anchored Acceptance Criteria

| Criterion | Spec-defined outcome | `file:line` + assertion/evidence | Result |
| --------- | -------------------- | -------------------------------- | ------ |
| NDVI-01 | Valid B04 and B08 tensors are transferred from host to GPU. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:10` calls the distinct H2D boundary; `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:18` calls `PolyHok.new_gnx/1` once for each tensor; `test/sentinel_2/ndvi_test.exs:77-87` executes the valid composition and asserts all six returned positions. | ✅ PASS |
| NDVI-02 | Exactly one kernel call produces the NDVI matrix. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:24-36` contains the feature's single `Ske.map2/3` invocation; `test/sentinel_2/ndvi_test.exs:77-87` asserts the six results from one public operation. | ✅ PASS |
| NDVI-03 | Each thread processes at most one in-bounds linear position. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:47-53` computes one `id`, guards `id < size`, and writes only `a3[id]`; `test/sentinel_2/ndvi_test.exs:78-87` asserts every position of a six-element, non-block-multiple result. | ✅ PASS |
| NDVI-04 | Finite inputs with nonzero denominator produce the exact float32 NDVI formula. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:31` returns `(b08 - b04) / (b08 + b04)`; `test/sentinel_2/ndvi_test.exs:82-84` asserts `0.5`, `0.0`, and `-0.5` with absolute tolerance `1.0e-6`. | ✅ PASS |
| NDVI-05 | NaN in either band produces NaN at the corresponding position. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:28-29` propagates the invalid denominator expression; `test/sentinel_2/ndvi_test.exs:86-87` asserts `nan_b04 == :nan` and `nan_b08 == :nan`. | ✅ PASS |
| NDVI-06 | An exactly positive-zero or negative-zero denominator produces NaN. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:28-29` compares the float32 denominator exactly with zero and writes NaN by `0/0`; `test/sentinel_2/ndvi_test.exs:85` asserts the positive-zero case and `test/sentinel_2/ndvi_test.exs:103-108` asserts `[-0.0 + -0.0]` returns `:nan`. | ✅ PASS |
| NDVI-07 | Every nonzero denominator, including the smallest subnormal, is divided without epsilon. | `test/sentinel_2/ndvi_test.exs:92-98` constructs the minimum positive float32 by bits and asserts the exact result `[1.0]`; `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:28-31` contains no epsilon threshold. | ✅ PASS |
| NDVI-08 | Results are not clamped or subjected to thematic/geospatial processing. | `test/sentinel_2/ndvi_test.exs:103-108` asserts the out-of-range result `-3.0`; `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:27-35` contains only the numerical policy. Mutation M2 injected a clamp to `-1.0` and the assertion failed. | ✅ PASS |
| NDVI-09 | The completed GPU result is transferred to the host exactly once. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:12-14` calls `to_host/1` once after `run_kernel/2`; `test/sentinel_2/ndvi_test.exs:77-87` observes the returned host tensor. | ✅ PASS |
| NDVI-10 | The public result is a direct float32 tensor with unchanged shape and linear correspondence. | `test/sentinel_2/ndvi_test.exs:78-87` destructures positions in order and asserts `Nx.type(result) == {:f, 32}` and `Nx.shape(result) == {2, 3}`. | ✅ PASS |
| NDVI-11 | A non-Nx input raises `ArgumentError` before PolyHok. | `test/sentinel_2/ndvi_test.exs:10-16` asserts the exact exception class and band-specific message for both inputs; validation precedes H2D at `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:8-10`. | ✅ PASS |
| NDVI-12 | A non-float32 input raises `ArgumentError` before PolyHok. | `test/sentinel_2/ndvi_test.exs:23-29` asserts `ArgumentError` and the required type for both bands; type validation is at `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:77-80`. | ✅ PASS |
| NDVI-13 | A non-2D or zero-sized tensor raises `ArgumentError` before PolyHok. | `test/sentinel_2/ndvi_test.exs:36-42` asserts both rank failures and `test/sentinel_2/ndvi_test.exs:49-55` asserts both zero-dimension failures. | ✅ PASS |
| NDVI-14 | Different shapes raise `ArgumentError` before PolyHok. | `test/sentinel_2/ndvi_test.exs:59-64` passes `{1, 2}` and `{2, 1}` and asserts the exact `ArgumentError` message; the check precedes H2D at `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:68-74`. | ✅ PASS |
| NDVI-15 | Native PolyHok/NIF/CUDA/allocation failures propagate without partial success. | `test/sentinel_2/ndvi_test.exs:68-70` asserts the original `FunctionClauseError` at the public D2H boundary; `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:7-15` contains no rescue or success wrapper. | ✅ PASS |
| NDVI-16 | H2D, kernel, and D2H remain independently invocable operations. | Public boundaries are defined at `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:17-18`, `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:20-37`, and `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:39-40`; `test/sentinel_2/ndvi_test.exs:68-70` invokes D2H independently. | ✅ PASS |
| NDVI-17 | Data preparation remains outside calculation and kernel duration. | `test/sentinel_2/ndvi_test.exs:74-77` builds Nx tensors directly and calls `Ndvi.compute/2`; `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:1-91` has no preparation dependency. | ✅ PASS |
| NDVI-18 | The public operation composes H2D → kernel → D2H and has no CPU NDVI path. | The order is explicit at `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:10-14`; `test/sentinel_2/ndvi_test.exs:77-87` asserts the GPU composition's outcomes. | ✅ PASS |
| NDVI-19 | Equal finite bands produce `0.0f`. | `test/sentinel_2/ndvi_test.exs:75-83` supplies `0.4/0.4` and asserts zero within `1.0e-6`. | ✅ PASS |
| NDVI-20 | B04 greater than B08 preserves the negative result without clamp. | `test/sentinel_2/ndvi_test.exs:74-84` supplies `0.6/0.2` and asserts `-0.5`; the stronger out-of-range negative assertion is at `test/sentinel_2/ndvi_test.exs:103-108`. | ✅ PASS |
| NDVI-21 | The minimum nonzero float32 denominator is divided normally. | `test/sentinel_2/ndvi_test.exs:92-98` constructs bit pattern `1`, uses it as the denominator, and asserts `[1.0]`. | ✅ PASS |
| NDVI-22 | Threads beyond the element count perform no input read or output write. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:48-52` guards the only indexed accesses and assignment with `id < size`; `test/sentinel_2/ndvi_test.exs:74-87` uses six elements, not a multiple of the block size, and asserts exactly six ordered outputs. | ✅ PASS |
| NDVI-23 | Persistence writes exact headerless little-endian row-major float32 bytes and `height*width*4` size. | `test/sentinel_2/ndvi_result_writer_test.exs:17-22` asserts 24 bytes and the complete literal byte sequence; conversion is at `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi/result_writer.ex:23-26`. | ✅ PASS |
| NDVI-24 | Metadata contains width, height, type, byte order, order, filename, and SHA-256. | `test/sentinel_2/ndvi_result_writer_test.exs:24-34` asserts equality of the complete seven-field map and decoded JSON, including a recomputed SHA-256. | ✅ PASS |
| NDVI-25 | Final metadata is promoted after the complete binary and is the observable commit point. | Promotion order is binary then metadata at `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi/result_writer.ex:31-36`; `test/sentinel_2/ndvi_result_writer_test.exs:70-78` blocks final binary promotion and asserts no final metadata. Mutation M3 moved metadata promotion first and this assertion failed. | ✅ PASS |
| NDVI-26 | Write or validation failure returns an error without valid final metadata. | `test/sentinel_2/ndvi_result_writer_test.exs:59-67` asserts `{:error, :eisdir}` on partial-binary write failure and no metadata; `test/sentinel_2/ndvi_result_writer_test.exs:70-78` asserts the same invariant on final binary promotion failure. Validation precedes publication at `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi/result_writer.ex:31-36`. | ✅ PASS |
| NDVI-27 | Persistence remains explicit and separate from all GPU stages. | `test/sentinel_2/ndvi_result_writer_test.exs:11` invokes `ResultWriter.write/2` explicitly; `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi/result_writer.ex:1-77` has no PolyHok or calculation call. | ✅ PASS |

**Status**: ✅ 27/27 criteria match the spec-defined outcome. There are 0 uncovered criteria and 0 spec-precision gaps.

## Edge Cases

- [x] NDVI-19: equal finite inputs return `0.0f`.
- [x] NDVI-20: negative results remain negative and unclamped.
- [x] NDVI-21: the minimum nonzero float32 denominator is divided without epsilon.
- [x] NDVI-22: a six-element launch exercises excess threads behind the bounds guard.
- [x] NDVI-06: both positive-zero cancellation and explicit negative-zero inputs return NaN.

## Gate Check

- **Gate command**: `python/.venv/bin/python -m ruff check python && python/.venv/bin/python -m pytest python/tests -q && mix format --check-formatted && mix compile --warnings-as-errors && mix test --exclude gpu && mix test --include gpu test/sentinel_2/ndvi_test.exs`
- **Sandbox attempt**: the CUDA stage exited 139 after the CPU stages passed; this is an environment/GPU isolation failure, not a test assertion failure.
- **Authorized GPU run**: PASS, exit 0.
- **Ruff**: pass.
- **Python**: 74 passed, 0 failed, 0 skipped.
- **Elixir CPU stage**: 58 discovered, 54 executed, 0 failed, 4 excluded by `:gpu`.
- **Elixir targeted CUDA stage**: 9 executed, 0 failed. This command runs the six non-GPU tests in `ndvi_test.exs` plus the three GPU-tagged tests.
- **Excluded in CPU stage**: one legacy PolyHok GPU smoke test and the three NDVI GPU tests; the three feature tests ran in the CUDA stage.
- **Test count before feature (`35f20db`)**: 45 discovered, 44 executed, 0 failed, 1 GPU excluded.
- **Test count after feature (`bbf674e`)**: 58 discovered, 54 executed in the CPU stage, 0 failed, 4 GPU excluded.
- **Delta**: +13 tests total, comprising 10 additional CPU tests and 3 additional GPU tests.
- **Integrity**: the feature diff adds both scoped test files and deletes no test. No pre-existing assertion was weakened.

## Discrimination Sensor

| Mutation | File:line | Description | Result |
| -------- | --------- | ----------- | ------ |
| M1 | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:28` | Changed the exact-zero predicate from `denominator == 0.0` to `denominator == 1.0`. | ✅ Killed: targeted CUDA run reported 9 tests, 2 failures, including `zero_denominator == :nan` at `test/sentinel_2/ndvi_test.exs:85`. |
| M2 | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:31` | Injected a lower clamp that returned `-1.0` when computed NDVI was below `-1.0`. | ✅ Killed: targeted CUDA run reported 9 tests, 1 failure; `test/sentinel_2/ndvi_test.exs:108` expected `-3.0` and observed `-1.0`. |
| M3 | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi/result_writer.ex:34-36` | Promoted final metadata before attempting final binary promotion. | ✅ Killed: writer run reported 4 tests, 1 failure; `test/sentinel_2/ndvi_result_writer_test.exs:78` observed forbidden final metadata after binary promotion failed. |

**Sensor depth**: lightweight, three targeted behavior-level mutations.
**Result**: 3/3 killed. PASS ✅

The sensor used a detached temporary Git worktree under `/tmp`, never used `git stash`, and removed the worktree after the runs. The real-tree porcelain before and after sensor cleanup was identical apart from this report: the pre-existing user modification remains ` M .notebook/poly-hok-integration.md`.

## Code Quality

| Principle | Status | Evidence |
| --------- | ------ | -------- |
| Minimum code | ✅ | Two feature-specific modules; no generic GPU framework or configuration layer. |
| Surgical changes | ✅ | Functional changes are limited to NDVI calculation, persistence, and their tests. |
| No scope creep | ✅ | No CPU NDVI implementation, benchmark, metrics, imagery, or thematic processing. |
| Matches patterns | ✅ | Nx tensors, ExUnit GPU tags, Jason metadata, and partial-file promotion match project conventions. |
| Senior-engineer approval | ✅ | Exact outputs, failure states, boundary order, and publication commit point are asserted; all mutants are killed. |
| Spec-anchored outcomes | ✅ | 27/27 outcomes match precise normative values or states. |
| Per-layer coverage | ✅ | Domain requirements have direct evidence; GPU happy/edge/error behavior and writer happy/error paths are covered. |
| No unclaimed tests | ✅ | NDVI calculation tests map to NDVI-01..22; writer tests map to NDVI-23..27 or T2's invalid-input Done-when criterion. |
| Documented guidelines | ✅ | `README.md:28-40`, `README.md:96-107`, the feature `tasks.md:10-32`, and strong defaults were applied. |

`lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:42-43` contains a documented `SPEC_DEVIATION` that restores Ske JIT metadata in compiled Mix applications. It does not change the numerical contract and is exercised by the passing CUDA gate.

## Interactive UAT

Not applicable. This feature is a local GPU calculation and persistence library without an interactive user interface. Automated gates cover its observable behavior.

## Requirement Traceability

| Requirements | Previous status | Verification status |
| ------------ | --------------- | ------------------- |
| NDVI-01..27 | Implemented | ✅ Verified |

The normative `spec.md` was not modified because the Verifier's only permitted real-tree write is this report.

## Lessons Distillation

No failed AC, surviving mutant, spec-precision gap, or gate failure remains, so there is no failure lesson to persist. The existing non-blocking `SPEC_DEVIATION` suggests this reusable candidate: **register Ske JIT metadata explicitly before invoking a PolyHok kernel from a compiled Mix application**. It was not persisted because the task restricts real-tree writes to `validation.md`.

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 27/27 outcomes matched; 0 spec-precision gaps.
**Sensor**: 3/3 mutations killed.
**Gate**: PASS, 74 Python + 54 CPU Elixir + 9 targeted CUDA tests executed, 0 failures.
**Issues found**: none.
**Next step**: close the feature after the deterministic state validator passes.
