import tomllib
from importlib.metadata import entry_points
from pathlib import Path

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
