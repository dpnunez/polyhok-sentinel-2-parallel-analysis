import tomllib
from importlib.metadata import entry_points
from pathlib import Path
from subprocess import run

import pytest

import sentinel2_prepare

PYTHON_ROOT = Path(__file__).parents[1]
PROJECT_ROOT = PYTHON_ROOT.parent


def test_project_declares_supported_runtime_and_test_dependencies() -> None:
    project = tomllib.loads((PYTHON_ROOT / "pyproject.toml").read_text())

    assert project["project"]["requires-python"] == ">=3.11"
    assert project["project"]["dependencies"] == [
        "numpy>=2.0,<2.4",
        "pillow>=11,<13",
        "rasterio>=1.4,<1.5",
    ]
    assert project["project"]["optional-dependencies"]["dev"] == [
        "pytest>=8,<10",
        "ruff>=0.12,<1",
    ]


def test_package_import_and_cli_registration() -> None:
    assert sentinel2_prepare.__version__ == "0.1.0"
    console_scripts = {
        entry_point.name: entry_point.value
        for entry_point in entry_points(group="console_scripts")
    }
    assert console_scripts["sentinel2-prepare"] == "sentinel2_prepare.cli:main"


def test_local_virtual_environment_is_ignored() -> None:
    ignore_rules = (PROJECT_ROOT / ".gitignore").read_text().splitlines()

    assert "/python/.venv/" in ignore_rules


@pytest.mark.parametrize(
    "generated_path",
    [
        "python/.venv/bin/python",
        "python/src/sentinel2_prepare/__pycache__/metadata.pyc",
        "python/src/sentinel2_prepare.egg-info/PKG-INFO",
        "python/.pytest_cache/v/cache/nodeids",
        "python/.ruff_cache/cache.db",
        "fixtures/sentinel-2/scenes/example/source/product.SAFE/manifest.safe",
        "fixtures/sentinel-2/scenes/example/source/B04.jp2",
        "fixtures/sentinel-2/scenes/example/source/B08.tif",
        "fixtures/sentinel-2/scenes/example/source/B08.tiff",
        "fixtures/sentinel-2/scenes/example/prepared/1024x1024/b04.f32",
        "fixtures/sentinel-2/scenes/example/prepared/1024x1024/debug.bin",
        "fixtures/sentinel-2/scenes/example/prepared/1024x1024/debug.npy",
        "fixtures/sentinel-2/scenes/example/prepared/1024x1024/debug.npz",
        "fixtures/sentinel-2/scenes/example/prepared/1024x1024/preview.png",
        "fixtures/sentinel-2/scenes/example/prepared.partial/orphan.partial",
        "fixtures/sentinel-2/scenes/example/prepared/orphan.tmp",
    ],
)
def test_generated_environment_and_fixture_paths_are_ignored(
    generated_path: str,
) -> None:
    result = git("check-ignore", "--no-index", generated_path)

    assert result.returncode == 0
    assert result.stdout.rstrip().endswith(generated_path)


def test_required_repository_files_and_metadata_paths_remain_versionable() -> None:
    tracked_contract = [
        "fixtures/sentinel-2/README.md",
        "fixtures/sentinel-2/manifest.json",
        "python/src/sentinel2_prepare/pipeline.py",
        "python/tests/test_pipeline.py",
        "lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/preparation.ex",
        "test/integration/python_elixir_contract_test.exs",
    ]

    for path in tracked_contract:
        result = git("ls-files", "--error-unmatch", path)
        assert result.returncode == 0
        assert result.stdout.strip() == path

    for path in [
        "fixtures/sentinel-2/scenes/example/source.json",
        "fixtures/sentinel-2/scenes/example/prepared/1024x1024/metadata.json",
    ]:
        result = git("check-ignore", "--no-index", path)
        assert result.returncode == 1
        assert result.stdout == ""


def test_no_generated_environment_or_fixture_artifact_is_tracked() -> None:
    tracked = git("ls-files")

    assert tracked.returncode == 0
    assert [path for path in tracked.stdout.splitlines() if is_generated(path)] == []


def git(*arguments: str):
    return run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def is_generated(value: str) -> bool:
    path = Path(value)
    parts = path.parts
    generated_directories = {".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
    generated_suffixes = {
        ".jp2",
        ".tif",
        ".tiff",
        ".f32",
        ".bin",
        ".npy",
        ".npz",
        ".tmp",
        ".partial",
    }

    return (
        bool(generated_directories.intersection(parts))
        or any(part.endswith((".SAFE", ".egg-info")) for part in parts)
        or path.suffix.lower() in generated_suffixes
        or (path.name == "preview.png" and "prepared" in parts)
    )
