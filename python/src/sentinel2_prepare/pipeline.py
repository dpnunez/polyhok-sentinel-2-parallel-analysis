"""Atomic scene preparation and integrity-based reuse."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from sentinel2_prepare.artifacts import SceneIdentity, validate_crop, write_crop
from sentinel2_prepare.metadata import ProductMetadata, discover_product
from sentinel2_prepare.raster import CROP_SIZES, prepare_window


class PipelineError(RuntimeError):
    """Raised when a scene transaction cannot be completed safely."""


def scene_id_for(product: ProductMetadata) -> str:
    satellite = product.product_id.split("_", 1)[0].lower()
    sensing = re.sub(r"[^0-9T]", "", product.sensing_time_utc).lower()[:15]
    if not re.fullmatch(r"s2[a-c]", satellite) or len(sensing) != 15:
        raise PipelineError("product identity cannot produce a stable scene-id")
    return f"{satellite}-{product.tile_id.lower()}-{sensing}"


def _read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists() and default is not None:
        return default
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise PipelineError(f"cannot read JSON state: {path}") from error
    if not isinstance(value, dict):
        raise PipelineError(f"JSON state must be an object: {path}")
    return value


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f"{path.name}.partial")
    with partial.open("w") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(partial, path)


def _crop_metadata_paths(root: Path, scene_id: str) -> list[Path]:
    prepared = (
        root / "fixtures" / "sentinel-2" / "scenes" / scene_id / "prepared"
    )
    return [prepared / f"{size}x{size}" / "metadata.json" for size in CROP_SIZES]


def _source_state(
    root: Path,
    safe_path: Path,
    product: ProductMetadata,
    source_uri: str | None,
) -> dict[str, Any]:
    try:
        relative_safe = safe_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise PipelineError("SAFE product must be inside the project root") from error
    return {
        "product_id": product.product_id,
        "tile_id": product.tile_id,
        "sensing_time_utc": product.sensing_time_utc,
        "source_checksum": product.source_checksum,
        "source_path": relative_safe,
        "source_uri": source_uri,
    }


def _reusable(
    root: Path,
    scene_id: str,
    product: ProductMetadata,
    manifest: dict[str, Any],
    source_state: dict[str, Any],
) -> dict[str, Any] | None:
    scenes = manifest.get("scenes")
    entry = scenes.get(scene_id) if isinstance(scenes, dict) else None
    if not isinstance(entry, dict):
        return None
    expected_paths = _crop_metadata_paths(root, scene_id)
    expected_relative = [path.relative_to(root).as_posix() for path in expected_paths]
    if entry != {
        "status": "prepared",
        "product_id": product.product_id,
        "source_checksum": product.source_checksum,
        "crops": expected_relative,
    }:
        return None
    source_path = expected_paths[0].parents[2] / "source.json"
    try:
        if _read_json(source_path) != source_state:
            return None
        crops = [validate_crop(root, path) for path in expected_paths]
    except (PipelineError, ValueError, OSError):
        return None
    return {
        "scene_id": scene_id,
        "product_id": product.product_id,
        "source_checksum": product.source_checksum,
        "crops": crops,
        "reused": True,
    }


def _rewrite_staged_metadata(
    staged_metadata: Path, staged_crop: Path, final_crop: Path, root: Path
) -> None:
    metadata = _read_json(staged_metadata)
    for name, filename in (
        ("path_b04", "b04.f32"),
        ("path_b08", "b08.f32"),
        ("metadata_path", "metadata.json"),
        ("preview_path", "preview.png"),
    ):
        metadata[name] = (final_crop / filename).relative_to(root).as_posix()
    staged_metadata.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


def _publish_crops(stage: Path, prepared: Path, root: Path) -> list[dict[str, Any]]:
    for size in CROP_SIZES:
        staged_crop = stage / f"{size}x{size}"
        final_crop = prepared / f"{size}x{size}"
        final_crop.mkdir(parents=True, exist_ok=True)
        staged_metadata = staged_crop / "metadata.json"
        _rewrite_staged_metadata(staged_metadata, staged_crop, final_crop, root)
        for filename in ("b04.f32", "b08.f32", "preview.png", "metadata.json"):
            os.replace(staged_crop / filename, final_crop / filename)
    metadata_paths = _crop_metadata_paths(root, prepared.parent.name)
    return [validate_crop(root, path) for path in metadata_paths]


def prepare_scene(
    safe_path: Path, root: Path, source_uri: str | None = None
) -> dict[str, Any]:
    """Prepare all benchmark crops and commit the manifest after validation."""
    root = root.resolve()
    safe_path = safe_path.resolve()
    product = discover_product(safe_path)
    scene_id = scene_id_for(product)
    fixture_root = root / "fixtures" / "sentinel-2"
    manifest_path = fixture_root / "manifest.json"
    manifest = _read_json(manifest_path, {"schema_version": 1, "scenes": {}})
    if manifest.get("schema_version") != 1 or not isinstance(
        manifest.get("scenes"), dict
    ):
        raise PipelineError("manifest.json must use schema_version 1 with a scenes map")
    source_state = _source_state(root, safe_path, product, source_uri)
    reused = _reusable(root, scene_id, product, manifest, source_state)
    if reused is not None:
        return reused

    scene_dir = fixture_root / "scenes" / scene_id
    prepared = scene_dir / "prepared"
    stage = scene_dir / "prepared.partial"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    identity = SceneIdentity(scene_id, product)

    try:
        for size in CROP_SIZES:
            bands = prepare_window(product, size)
            write_crop(root, identity, bands, stage / f"{size}x{size}")
            del bands

        _atomic_json(scene_dir / "source.json", source_state)
        crops = _publish_crops(stage, prepared, root)
        entry = {
            "status": "prepared",
            "product_id": product.product_id,
            "source_checksum": product.source_checksum,
            "crops": [crop["metadata_path"] for crop in crops],
        }
        updated_scenes = {**manifest["scenes"], scene_id: entry}
        updated_manifest = {**manifest, "scenes": updated_scenes}
        _atomic_json(manifest_path, updated_manifest)
    except OSError as error:
        raise PipelineError(f"cannot publish prepared scene: {error}") from error

    if stage.exists():
        shutil.rmtree(stage)
    return {
        "scene_id": scene_id,
        "product_id": product.product_id,
        "source_checksum": product.source_checksum,
        "crops": crops,
        "reused": False,
    }
