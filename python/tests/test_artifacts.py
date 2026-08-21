import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from sentinel2_prepare.artifacts import (
    REQUIRED_METADATA_FIELDS,
    ArtifactError,
    SceneIdentity,
    validate_crop,
    write_crop,
)
from sentinel2_prepare.metadata import ProductMetadata
from sentinel2_prepare.raster import PreparedBands


def scene(root: Path) -> SceneIdentity:
    source = root / "fixtures" / "sentinel-2" / "source" / "product.SAFE"
    source.mkdir(parents=True)
    b04 = source / "B04_10m.jp2"
    b08 = source / "B08_10m.jp2"
    product_xml = source / "MTD_MSIL2A.xml"
    tile_xml = source / "MTD_TL.xml"
    for path in (b04, b08, product_xml, tile_xml):
        path.write_bytes(path.name.encode())
    product = ProductMetadata(
        product_id="S2C_PRODUCT",
        tile_id="T22HCK",
        sensing_time_utc="2026-06-20T13:31:51Z",
        b04_path=b04,
        b08_path=b08,
        product_metadata_path=product_xml,
        tile_metadata_path=tile_xml,
        boa_offset_b04=-1000,
        boa_offset_b08=-900,
        quantification=10000,
        nodata=0,
        saturated=65535,
        source_checksum="a" * 64,
    )
    return SceneIdentity("s2c-t22hck-20260620t133151", product)


def bands(*, with_values: bool = False) -> PreparedBands:
    b04 = np.zeros((1024, 1024), dtype=np.float32)
    b08 = np.zeros((1024, 1024), dtype=np.float32)
    if with_values:
        b04[0, :4] = [np.nan, 0.0, 0.5, 1.0]
        b08[0, :4] = [np.nan, 100.0, 150.0, 200.0]
    return PreparedBands(
        b04=b04,
        b08=b08,
        width=1024,
        height=1024,
        row_offset=4978,
        column_offset=4978,
        crs="EPSG:32722",
        pixel_size=(10.0, -10.0),
        origin=(300000.0, 6500020.0),
    )


def write_valid_crop(root: Path, *, with_values: bool = False) -> tuple[Path, dict]:
    metadata = write_crop(root, scene(root), bands(with_values=with_values))
    return root / metadata["metadata_path"], metadata


def test_writes_exact_little_endian_headerless_row_major_binaries(
    tmp_path: Path,
) -> None:
    metadata_path, metadata = write_valid_crop(tmp_path, with_values=True)
    b04_path = tmp_path / metadata["path_b04"]

    assert b04_path.stat().st_size == 1024 * 1024 * 4
    assert b04_path.read_bytes()[:16] == np.array(
        [np.nan, 0.0, 0.5, 1.0], dtype="<f4"
    ).tobytes(order="C")
    assert metadata_path.is_file()


def test_writes_all_metadata_fields_with_relative_paths_and_checksums(
    tmp_path: Path,
) -> None:
    _, metadata = write_valid_crop(tmp_path)

    assert REQUIRED_METADATA_FIELDS <= metadata.keys()
    prepared = (
        "fixtures/sentinel-2/scenes/s2c-t22hck-20260620t133151/prepared/1024x1024"
    )
    expected = {
        "product_id": "S2C_PRODUCT",
        "tile_id": "T22HCK",
        "sensing_time_utc": "2026-06-20T13:31:51Z",
        "size_class": "small",
        "source_b04": "fixtures/sentinel-2/source/product.SAFE/B04_10m.jp2",
        "source_b08": "fixtures/sentinel-2/source/product.SAFE/B08_10m.jp2",
        "width": 1024,
        "height": 1024,
        "data_type": "float32",
        "byte_order": "little-endian",
        "memory_order": "row-major",
        "crs": "EPSG:32722",
        "pixel_size": [10.0, -10.0],
        "origin": [300000.0, 6500020.0],
        "row_offset": 4978,
        "column_offset": 4978,
        "boa_offset_b04": -1000,
        "boa_offset_b08": -900,
        "boa_quantification_value": 10000,
        "source_nodata_value": 0,
        "source_saturated_value": 65535,
        "path_b04": f"{prepared}/b04.f32",
        "path_b08": f"{prepared}/b08.f32",
        "metadata_path": f"{prepared}/metadata.json",
        "preview_path": f"{prepared}/preview.png",
    }
    assert {field: metadata[field] for field in expected} == expected
    for field in (
        "source_b04",
        "source_b08",
        "path_b04",
        "path_b08",
        "metadata_path",
        "preview_path",
    ):
        assert not Path(metadata[field]).is_absolute()
    for band in ("b04", "b08"):
        content = (tmp_path / metadata[f"path_{band}"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == metadata[
            f"checksum_{band}_prepared"
        ]


def test_preview_places_independently_scaled_bands_side_by_side_with_black_nan(
    tmp_path: Path,
) -> None:
    from sentinel2_prepare.artifacts import _write_preview

    path = tmp_path / "preview.png"
    b04 = np.array([[np.nan, 0.0], [0.5, 1.0]], dtype=np.float32)
    b08 = np.array([[np.nan, 100.0], [150.0, 200.0]], dtype=np.float32)
    _write_preview(path, b04, b08)

    with Image.open(path) as preview:
        pixels = np.asarray(preview)

    assert pixels.shape == (2, 4)
    assert pixels[0, 0] == 0
    assert pixels[0, 2] == 0
    assert pixels[1, 1] == 255
    assert pixels[1, 3] == 255


def test_preview_is_never_larger_than_2048_by_1024(tmp_path: Path) -> None:
    from sentinel2_prepare.artifacts import _write_preview

    path = tmp_path / "preview.png"
    values = np.ones((1200, 1200), dtype=np.float32)
    _write_preview(path, values, values)

    with Image.open(path) as preview:
        assert preview.size == (2048, 1024)


def test_rereads_a_valid_crop_with_declared_shape_and_order(tmp_path: Path) -> None:
    metadata_path, metadata = write_valid_crop(tmp_path)

    validated = validate_crop(tmp_path, metadata_path)

    assert validated == metadata


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("data_type", "float64", "data_type"),
        ("byte_order", "big-endian", "byte_order"),
        ("memory_order", "column-major", "memory_order"),
    ],
)
def test_rejects_invalid_binary_contract(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    metadata_path, metadata = write_valid_crop(tmp_path)
    metadata[field] = value
    metadata_path.write_text(json.dumps(metadata))

    with pytest.raises(ArtifactError, match=message):
        validate_crop(tmp_path, metadata_path)


def test_rejects_wrong_byte_size(tmp_path: Path) -> None:
    metadata_path, metadata = write_valid_crop(tmp_path)
    (tmp_path / metadata["path_b04"]).write_bytes(b"short")

    with pytest.raises(ArtifactError, match="invalid byte size"):
        validate_crop(tmp_path, metadata_path)


def test_rejects_wrong_checksum(tmp_path: Path) -> None:
    metadata_path, metadata = write_valid_crop(tmp_path)
    metadata["checksum_b08_prepared"] = "0" * 64
    metadata_path.write_text(json.dumps(metadata))

    with pytest.raises(ArtifactError, match="checksum mismatch"):
        validate_crop(tmp_path, metadata_path)


def test_rejects_artifact_path_outside_project_root(tmp_path: Path) -> None:
    metadata_path, metadata = write_valid_crop(tmp_path)
    metadata["path_b04"] = "../outside.f32"
    metadata_path.write_text(json.dumps(metadata))

    with pytest.raises(ArtifactError, match="escapes project root"):
        validate_crop(tmp_path, metadata_path)


def test_rejects_non_benchmark_crop_dimensions(tmp_path: Path) -> None:
    invalid = bands()
    invalid = PreparedBands(
        **{**invalid.__dict__, "width": 512, "height": 512}
    )

    with pytest.raises(ArtifactError, match="1024, 4096 or 8192"):
        write_crop(tmp_path, scene(tmp_path), invalid)
