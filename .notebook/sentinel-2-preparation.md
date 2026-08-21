# Sentinel-2 Preparation
> Python producer with a filesystem contract and supervised Elixir consumer

Entry: `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/preparation.ex:prepare()`
Flow: API → Registry name → DynamicSupervisor → Port worker → Python CLI → manifest-last publication → artifact validation

Producer: `python/src/sentinel2_prepare/pipeline.py:prepare_scene()`
- Metadata/discovery: `python/src/sentinel2_prepare/metadata.py:discover_product()`
- Window conversion: `python/src/sentinel2_prepare/raster.py:prepare_window()`
- Artifact contract: `python/src/sentinel2_prepare/artifacts.py:write_crop()`
- Commit point: `fixtures/sentinel-2/manifest.json`; `.partial` files are never readable state

Consumer: `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/artifact_validator.ex:validate()`
- Process lifecycle: `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/preparation_worker.ex`
- Binary import: `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/prepared_reader.ex:read_crop()`
- Same-scene serialization: `PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparationRegistry`

Operations: `README.md` and `fixtures/sentinel-2/README.md`
Verification: `test/integration/python_elixir_contract_test.exs`

Updated: 2026-08-20
