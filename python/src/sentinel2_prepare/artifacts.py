"""Writing and validation of prepared Sentinel-2 crop artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from sentinel2_prepare.metadata import ProductMetadata
from sentinel2_prepare.raster import PreparedBands

SIZE_CLASSES = {1024: "small", 4096: "medium", 8192: "large"}
REQUIRED_METADATA_FIELDS = {
    "product_id",
    "tile_id",
    "sensing_time_utc",
    "size_class",
    "source_b04",
    "source_b08",
    "width",
    "height",
    "data_type",
    "byte_order",
    "memory_order",
    "crs",
    "pixel_size",
    "origin",
    "row_offset",
    "column_offset",
    "boa_offset_b04",
    "boa_offset_b08",
    "boa_quantification_value",
    "source_nodata_value",
    "source_saturated_value",
    "checksum_b04_prepared",
    "checksum_b08_prepared",
    "path_b04",
    "path_b08",
    "metadata_path",
    "preview_path",
}


class ArtifactError(ValueError):
    """Raised when a prepared crop does not satisfy the artifact contract."""


@dataclass(frozen=True)
class SceneIdentity:
    scene_id: str
    product: ProductMetadata


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise ArtifactError(f"artifact path is outside project root: {path}") from error


def _inside_root(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ArtifactError("artifact path must be project-relative")
    path = (root.resolve() / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise ArtifactError("artifact path escapes project root") from error
    return path


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _panel(values: np.ndarray) -> Image.Image:
    finite = np.isfinite(values)
    scaled = np.zeros(values.shape, dtype=np.uint8)
    if finite.any():
        low, high = np.percentile(values[finite], (2, 98))
        if high > low:
            contrast = (values[finite] - low) / (high - low)
            scaled[finite] = np.clip(contrast * 255, 0, 255).astype(np.uint8)
    image = Image.fromarray(scaled)
    if image.width > 1024 or image.height > 1024:
        image.thumbnail((1024, 1024), Image.Resampling.BILINEAR)
    return image


def _write_preview(path: Path, b04: np.ndarray, b08: np.ndarray) -> None:
    left = _panel(b04)
    right = _panel(b08)
    preview = Image.new("L", (left.width + right.width, max(left.height, right.height)))
    preview.paste(left, (0, 0))
    preview.paste(right, (left.width, 0))
    preview.save(path)


def write_crop(
    root: Path,
    scene: SceneIdentity,
    bands: PreparedBands,
    destination: Path | None = None,
) -> dict[str, Any]:
    """Write a crop and return only after rereading and validating it."""
    if bands.width != bands.height or bands.width not in SIZE_CLASSES:
        raise ArtifactError("crop dimensions must be 1024, 4096 or 8192 square")
    if bands.b04.shape != (bands.height, bands.width):
        raise ArtifactError("B04 shape does not match crop dimensions")
    if bands.b08.shape != (bands.height, bands.width):
        raise ArtifactError("B08 shape does not match crop dimensions")

    root = root.resolve()
    crop_dir = destination or (
        root
        / "fixtures"
        / "sentinel-2"
        / "scenes"
        / scene.scene_id
        / "prepared"
        / f"{bands.width}x{bands.height}"
    )
    crop_dir.mkdir(parents=True, exist_ok=True)
    b04_path = crop_dir / "b04.f32"
    b08_path = crop_dir / "b08.f32"
    metadata_path = crop_dir / "metadata.json"
    preview_path = crop_dir / "preview.png"

    np.ascontiguousarray(bands.b04, dtype="<f4").tofile(b04_path)
    np.ascontiguousarray(bands.b08, dtype="<f4").tofile(b08_path)
    _write_preview(preview_path, bands.b04, bands.b08)

    product = scene.product
    metadata: dict[str, Any] = {
        "product_id": product.product_id,
        "tile_id": product.tile_id,
        "sensing_time_utc": product.sensing_time_utc,
        "size_class": SIZE_CLASSES[bands.width],
        "source_b04": _relative(root, product.b04_path),
        "source_b08": _relative(root, product.b08_path),
        "width": bands.width,
        "height": bands.height,
        "data_type": "float32",
        "byte_order": "little-endian",
        "memory_order": "row-major",
        "crs": bands.crs,
        "pixel_size": list(bands.pixel_size),
        "origin": list(bands.origin),
        "row_offset": bands.row_offset,
        "column_offset": bands.column_offset,
        "boa_offset_b04": product.boa_offset_b04,
        "boa_offset_b08": product.boa_offset_b08,
        "boa_quantification_value": product.quantification,
        "source_nodata_value": product.nodata,
        "source_saturated_value": product.saturated,
        "checksum_b04_prepared": _checksum(b04_path),
        "checksum_b08_prepared": _checksum(b08_path),
        "path_b04": _relative(root, b04_path),
        "path_b08": _relative(root, b08_path),
        "metadata_path": _relative(root, metadata_path),
        "preview_path": _relative(root, preview_path),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return validate_crop(root, metadata_path)


def validate_crop(root: Path, metadata_path: Path) -> dict[str, Any]:
    """Validate metadata, byte layout, shape and checksums for one crop."""
    root = root.resolve()
    try:
        metadata = json.loads(metadata_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactError(f"cannot read crop metadata: {metadata_path}") from error
    if not isinstance(metadata, dict):
        raise ArtifactError("crop metadata must be a JSON object")
    missing = REQUIRED_METADATA_FIELDS - metadata.keys()
    if missing:
        fields = ", ".join(sorted(missing))
        raise ArtifactError(f"crop metadata missing fields: {fields}")
    if metadata["data_type"] != "float32":
        raise ArtifactError("data_type must be float32")
    if metadata["byte_order"] != "little-endian":
        raise ArtifactError("byte_order must be little-endian")
    if metadata["memory_order"] != "row-major":
        raise ArtifactError("memory_order must be row-major")
    width = metadata["width"]
    height = metadata["height"]
    dimensions_are_valid = (
        isinstance(width, int)
        and isinstance(height, int)
        and width > 0
        and height > 0
    )
    if not dimensions_are_valid:
        raise ArtifactError("crop dimensions must be positive integers")

    declared_metadata_path = _inside_root(root, metadata["metadata_path"])
    if declared_metadata_path != metadata_path.resolve():
        raise ArtifactError("metadata_path does not identify this metadata file")
    expected_bytes = width * height * 4
    for band in ("b04", "b08"):
        path = _inside_root(root, metadata[f"path_{band}"])
        try:
            if path.stat().st_size != expected_bytes:
                raise ArtifactError(f"{band} has invalid byte size")
        except OSError as error:
            raise ArtifactError(f"cannot read prepared {band}") from error
        expected_checksum = metadata[f"checksum_{band}_prepared"]
        if _checksum(path) != expected_checksum:
            raise ArtifactError(f"{band} checksum mismatch")
        values = np.fromfile(path, dtype="<f4")
        try:
            values.reshape((height, width), order="C")
        except ValueError as error:
            raise ArtifactError(f"{band} shape mismatch") from error
    _inside_root(root, metadata["preview_path"])
    return metadata
