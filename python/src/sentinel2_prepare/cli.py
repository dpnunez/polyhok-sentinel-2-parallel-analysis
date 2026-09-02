"""Command-line entrypoint for Sentinel-2 preparation."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from sentinel2_prepare.artifacts import ArtifactError
from sentinel2_prepare.metadata import MetadataError
from sentinel2_prepare.pipeline import PipelineError, prepare_scene
from sentinel2_prepare.raster import RasterError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel2-prepare",
        description="Prepare Sentinel-2 L2A B04/B08 benchmark crops.",
    )
    parser.add_argument("--safe", required=True, type=Path, help="L2A .SAFE directory")
    parser.add_argument(
        "--root", required=True, type=Path, help="project root containing fixtures/"
    )
    parser.add_argument("--source-uri", help="optional source provenance URI")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run preparation and emit a bounded machine-readable diagnostic."""
    arguments = _parser().parse_args(argv)
    try:
        prepared = prepare_scene(arguments.safe, arguments.root, arguments.source_uri)
    except (MetadataError, RasterError, ArtifactError, PipelineError, OSError) as error:
        diagnostic = {
            "status": "error",
            "error": type(error).__name__,
            "message": str(error),
        }
        print(json.dumps(diagnostic, sort_keys=True), file=sys.stderr)
        return 1

    diagnostic = {
        "status": "prepared",
        "scene_id": prepared["scene_id"],
        "reused": prepared["reused"],
    }
    print(json.dumps(diagnostic, sort_keys=True))
    return 0
