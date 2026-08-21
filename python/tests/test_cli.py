import json
import subprocess
from pathlib import Path

import pytest

from sentinel2_prepare.artifacts import ArtifactError
from sentinel2_prepare.cli import main
from sentinel2_prepare.metadata import MetadataError
from sentinel2_prepare.pipeline import PipelineError
from sentinel2_prepare.raster import RasterError


def test_success_exits_zero_with_bounded_scene_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured_arguments: tuple[Path, Path, str | None] | None = None

    def successful_prepare(safe: Path, root: Path, source_uri: str | None) -> dict:
        nonlocal captured_arguments
        captured_arguments = (safe, root, source_uri)
        return {
            "scene_id": "s2c-t22hck-20260620t133151",
            "reused": False,
            "crops": [{"b04": [[1.0]], "b08": [[2.0]]}],
        }

    monkeypatch.setattr("sentinel2_prepare.cli.prepare_scene", successful_prepare)

    status = main(
        [
            "--safe",
            str(tmp_path / "product.SAFE"),
            "--root",
            str(tmp_path),
            "--source-uri",
            "copernicus:test",
        ]
    )
    output = capsys.readouterr()

    assert status == 0
    assert json.loads(output.out) == {
        "status": "prepared",
        "scene_id": "s2c-t22hck-20260620t133151",
        "reused": False,
    }
    assert output.err == ""
    assert captured_arguments == (
        tmp_path / "product.SAFE",
        tmp_path,
        "copernicus:test",
    )


@pytest.mark.parametrize(
    "error",
    [
        MetadataError("required B04 10 m raster is missing"),
        RasterError("B04/B08 grid mismatch: crs"),
        ArtifactError("b08 checksum mismatch"),
        PipelineError("cannot publish prepared scene: permission denied"),
        OSError("no space left on device"),
    ],
)
def test_failures_exit_nonzero_with_actionable_json_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    def failing_prepare(*_args: object) -> dict:
        raise error

    monkeypatch.setattr("sentinel2_prepare.cli.prepare_scene", failing_prepare)

    status = main(["--safe", str(tmp_path / "product.SAFE"), "--root", str(tmp_path)])
    output = capsys.readouterr()
    diagnostic = json.loads(output.err)

    assert status == 1
    assert output.out == ""
    assert diagnostic == {
        "status": "error",
        "error": type(error).__name__,
        "message": str(error),
    }


def test_installed_entrypoint_rejects_missing_required_arguments() -> None:
    executable = Path(__file__).parents[1] / ".venv" / "bin" / "sentinel2-prepare"

    completed = subprocess.run(
        [executable], text=True, capture_output=True, check=False
    )

    assert completed.returncode == 2
    assert "--safe" in completed.stderr
    assert "--root" in completed.stderr
