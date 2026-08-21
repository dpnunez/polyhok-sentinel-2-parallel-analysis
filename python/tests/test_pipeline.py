import json
import os
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from sentinel2_prepare.artifacts import ArtifactError, validate_crop
from sentinel2_prepare.metadata import ProductMetadata
from sentinel2_prepare.pipeline import PipelineError, prepare_scene
from sentinel2_prepare.raster import PreparedBands

TEST_SIZES = (2, 4, 8)
TEST_CLASSES = {2: "small", 4: "medium", 8: "large"}


def product(root: Path, checksum: str = "a" * 64) -> ProductMetadata:
    safe = (
        root
        / "fixtures"
        / "sentinel-2"
        / "scenes"
        / "input"
        / "source"
        / "product.SAFE"
    )
    safe.mkdir(parents=True, exist_ok=True)
    names = ("B04.jp2", "B08.jp2", "MTD_MSIL2A.xml", "MTD_TL.xml")
    paths = [safe / name for name in names]
    for path in paths:
        path.write_bytes(path.name.encode())
    return ProductMetadata(
        product_id="S2C_PRODUCT",
        tile_id="T22HCK",
        sensing_time_utc="2026-06-20T13:31:51Z",
        b04_path=paths[0],
        b08_path=paths[1],
        product_metadata_path=paths[2],
        tile_metadata_path=paths[3],
        boa_offset_b04=-1000,
        boa_offset_b08=-1000,
        quantification=10000,
        nodata=0,
        saturated=65535,
        source_checksum=checksum,
    )


def prepared(size: int) -> PreparedBands:
    values = np.arange(size * size, dtype=np.float32).reshape(size, size)
    return PreparedBands(
        b04=values,
        b08=values + 1,
        width=size,
        height=size,
        row_offset=10,
        column_offset=20,
        crs="EPSG:32722",
        pixel_size=(10.0, -10.0),
        origin=(300000.0, 6500020.0),
    )


@pytest.fixture
def controlled_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> ProductMetadata:
    source = product(tmp_path)
    monkeypatch.setattr("sentinel2_prepare.pipeline.CROP_SIZES", TEST_SIZES)
    monkeypatch.setattr("sentinel2_prepare.artifacts.SIZE_CLASSES", TEST_CLASSES)
    monkeypatch.setattr("sentinel2_prepare.pipeline.discover_product", lambda _: source)
    monkeypatch.setattr(
        "sentinel2_prepare.pipeline.prepare_window",
        lambda _product, size: prepared(size),
    )
    return source


def safe_path(source: ProductMetadata) -> Path:
    return source.b04_path.parent


def manifest(root: Path) -> dict:
    path = root / "fixtures" / "sentinel-2" / "manifest.json"
    return json.loads(path.read_text())


def test_commits_three_valid_crops_and_manifest_last(
    tmp_path: Path,
    controlled_pipeline: ProductMetadata,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replacements: list[Path] = []
    real_replace = os.replace

    def recording_replace(source: Path, destination: Path) -> None:
        replacements.append(Path(destination))
        real_replace(source, destination)

    monkeypatch.setattr("sentinel2_prepare.pipeline.os.replace", recording_replace)

    result = prepare_scene(safe_path(controlled_pipeline), tmp_path, "copernicus:test")

    assert result["scene_id"] == "s2c-t22hck-20260620t133151"
    assert result["reused"] is False
    assert [crop["width"] for crop in result["crops"]] == [2, 4, 8]
    assert replacements[-1] == tmp_path / "fixtures" / "sentinel-2" / "manifest.json"
    entry = manifest(tmp_path)["scenes"][result["scene_id"]]
    assert entry == {
        "status": "prepared",
        "product_id": "S2C_PRODUCT",
        "source_checksum": "a" * 64,
        "crops": [crop["metadata_path"] for crop in result["crops"]],
    }
    for crop in result["crops"]:
        assert validate_crop(tmp_path, tmp_path / crop["metadata_path"]) == crop


def test_stages_new_outputs_under_a_partial_directory(
    tmp_path: Path,
    controlled_pipeline: ProductMetadata,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destinations: list[Path] = []
    from sentinel2_prepare.pipeline import write_crop as real_write_crop

    def recording_write(
        root: Path, identity: object, bands: object, destination: Path
    ) -> dict:
        destinations.append(destination)
        return real_write_crop(root, identity, bands, destination)

    monkeypatch.setattr("sentinel2_prepare.pipeline.write_crop", recording_write)

    prepare_scene(safe_path(controlled_pipeline), tmp_path)

    assert [path.parent.name for path in destinations] == ["prepared.partial"] * 3
    assert not destinations[0].parent.exists()


def test_failure_before_validation_never_adds_a_manifest_entry(
    tmp_path: Path,
    controlled_pipeline: ProductMetadata,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    from sentinel2_prepare.pipeline import write_crop as real_write_crop

    def failing_write(
        root: Path, identity: object, bands: object, destination: Path
    ) -> dict:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ArtifactError("controlled failure")
        return real_write_crop(root, identity, bands, destination)

    monkeypatch.setattr("sentinel2_prepare.pipeline.write_crop", failing_write)

    with pytest.raises(ArtifactError, match="controlled failure"):
        prepare_scene(safe_path(controlled_pipeline), tmp_path)

    assert not (tmp_path / "fixtures/sentinel-2/manifest.json").exists()
    stage = (
        tmp_path
        / "fixtures"
        / "sentinel-2"
        / "scenes"
        / "s2c-t22hck-20260620t133151"
        / "prepared.partial"
    )
    assert stage.exists()


def test_reuses_valid_output_without_touching_six_binary_mtimes(
    tmp_path: Path,
    controlled_pipeline: ProductMetadata,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = prepare_scene(safe_path(controlled_pipeline), tmp_path, "copernicus:test")
    binaries = [
        tmp_path / crop[field]
        for crop in first["crops"]
        for field in ("path_b04", "path_b08")
    ]
    mtimes = [path.stat().st_mtime_ns for path in binaries]
    monkeypatch.setattr(
        "sentinel2_prepare.pipeline.prepare_window",
        lambda *_args: pytest.fail("valid output must not be regenerated"),
    )

    second = prepare_scene(safe_path(controlled_pipeline), tmp_path, "copernicus:test")

    assert second["reused"] is True
    assert [path.stat().st_mtime_ns for path in binaries] == mtimes


def test_corrupt_binary_forces_regeneration(
    tmp_path: Path,
    controlled_pipeline: ProductMetadata,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = prepare_scene(safe_path(controlled_pipeline), tmp_path)
    (tmp_path / first["crops"][0]["path_b04"]).write_bytes(b"corrupt")
    calls: list[int] = []

    def regenerate(_product: ProductMetadata, size: int) -> PreparedBands:
        calls.append(size)
        return prepared(size)

    monkeypatch.setattr("sentinel2_prepare.pipeline.prepare_window", regenerate)

    second = prepare_scene(safe_path(controlled_pipeline), tmp_path)

    assert second["reused"] is False
    assert calls == [2, 4, 8]


def test_changed_source_identity_forces_regeneration(
    tmp_path: Path,
    controlled_pipeline: ProductMetadata,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepare_scene(safe_path(controlled_pipeline), tmp_path)
    changed = replace(controlled_pipeline, source_checksum="b" * 64)
    monkeypatch.setattr(
        "sentinel2_prepare.pipeline.discover_product", lambda _: changed
    )
    calls: list[int] = []
    monkeypatch.setattr(
        "sentinel2_prepare.pipeline.prepare_window",
        lambda _product, size: calls.append(size) or prepared(size),
    )

    result = prepare_scene(safe_path(controlled_pipeline), tmp_path)

    assert result["source_checksum"] == "b" * 64
    assert calls == [2, 4, 8]


def test_source_identity_is_published_before_manifest(
    tmp_path: Path, controlled_pipeline: ProductMetadata
) -> None:
    result = prepare_scene(safe_path(controlled_pipeline), tmp_path, "copernicus:test")
    source_path = (
        tmp_path
        / "fixtures"
        / "sentinel-2"
        / "scenes"
        / result["scene_id"]
        / "source.json"
    )

    source = json.loads(source_path.read_text())

    assert source == {
        "product_id": "S2C_PRODUCT",
        "tile_id": "T22HCK",
        "sensing_time_utc": "2026-06-20T13:31:51Z",
        "source_checksum": "a" * 64,
        "source_path": (
            "fixtures/sentinel-2/scenes/input/source/product.SAFE"
        ),
        "source_uri": "copernicus:test",
    }
    assert not Path(source["source_path"]).is_absolute()


def test_publication_error_does_not_update_manifest(
    tmp_path: Path,
    controlled_pipeline: ProductMetadata,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_replace = os.replace

    def fail_manifest(source: Path, destination: Path) -> None:
        if Path(destination).name == "manifest.json":
            raise OSError("permission denied")
        real_replace(source, destination)

    monkeypatch.setattr("sentinel2_prepare.pipeline.os.replace", fail_manifest)

    with pytest.raises(PipelineError, match="cannot publish prepared scene"):
        prepare_scene(safe_path(controlled_pipeline), tmp_path)

    assert not (tmp_path / "fixtures/sentinel-2/manifest.json").exists()


def test_invalid_existing_manifest_is_not_silently_overwritten(
    tmp_path: Path, controlled_pipeline: ProductMetadata
) -> None:
    manifest_path = tmp_path / "fixtures" / "sentinel-2" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("not-json")

    with pytest.raises(PipelineError, match="cannot read JSON state"):
        prepare_scene(safe_path(controlled_pipeline), tmp_path)

    assert manifest_path.read_text() == "not-json"
