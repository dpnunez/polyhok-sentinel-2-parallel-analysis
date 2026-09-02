from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from affine import Affine
from rasterio.coords import BoundingBox

from sentinel2_prepare.metadata import ProductMetadata
from sentinel2_prepare.raster import (
    RasterError,
    centered_window,
    inspect_grid,
    prepare_window,
)

DEFAULT_TRANSFORM = Affine(10, 0, 300000, 0, -10, 6500020)


class FakeDataset:
    def __init__(
        self,
        values: np.ndarray,
        *,
        crs: str = "EPSG:32722",
        transform: Affine = DEFAULT_TRANSFORM,
        bounds: BoundingBox | None = None,
    ) -> None:
        self.values = values
        self.height, self.width = values.shape
        self.crs = crs
        self.transform = transform
        self.bounds = bounds or BoundingBox(
            transform.c,
            transform.f + transform.e * self.height,
            transform.c + transform.a * self.width,
            transform.f,
        )
        self.read_windows: list[object] = []

    def __enter__(self) -> "FakeDataset":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, band: int, *, window: object) -> np.ndarray:
        assert band == 1
        self.read_windows.append(window)
        rows = slice(int(window.row_off), int(window.row_off + window.height))
        columns = slice(int(window.col_off), int(window.col_off + window.width))
        return self.values[rows, columns]


def product() -> ProductMetadata:
    return ProductMetadata(
        product_id="product",
        tile_id="T22HCK",
        sensing_time_utc="2026-06-20T13:31:51Z",
        b04_path=Path("b04.jp2"),
        b08_path=Path("b08.jp2"),
        product_metadata_path=Path("MTD_MSIL2A.xml"),
        tile_metadata_path=Path("MTD_TL.xml"),
        boa_offset_b04=-1000,
        boa_offset_b08=-900,
        quantification=10000,
        nodata=0,
        saturated=65535,
        source_checksum="a" * 64,
    )


def install_sources(monkeypatch: pytest.MonkeyPatch, *sources: FakeDataset) -> None:
    by_path = {Path("b04.jp2"): sources[0], Path("b08.jp2"): sources[1]}
    monkeypatch.setattr("sentinel2_prepare.raster.rasterio.open", by_path.__getitem__)


def test_inspects_complete_matching_grid(monkeypatch: pytest.MonkeyPatch) -> None:
    sources = (FakeDataset(np.ones((10, 12))), FakeDataset(np.ones((10, 12))))
    install_sources(monkeypatch, *sources)

    grid = inspect_grid(product())

    assert (grid.width, grid.height) == (12, 10)
    assert grid.crs == "EPSG:32722"
    assert grid.pixel_size == (10.0, -10.0)
    assert grid.origin == (300000.0, 6500020.0)
    assert grid.bounds == (300000.0, 6499920.0, 300120.0, 6500020.0)


@pytest.mark.parametrize(
    ("field", "second"),
    [
        ("width", FakeDataset(np.ones((10, 11)))),
        ("height", FakeDataset(np.ones((9, 12)))),
        ("crs", FakeDataset(np.ones((10, 12)), crs="EPSG:4326")),
        (
            "origin",
            FakeDataset(
                np.ones((10, 12)),
                transform=Affine(10, 0, 300010, 0, -10, 6500020),
            ),
        ),
        (
            "pixel_size",
            FakeDataset(
                np.ones((10, 12)),
                transform=Affine(20, 0, 300000, 0, -10, 6500020),
            ),
        ),
        (
            "bounds",
            FakeDataset(
                np.ones((10, 12)),
                bounds=BoundingBox(300000, 6499910, 300120, 6500020),
            ),
        ),
    ],
)
def test_rejects_each_grid_mismatch(
    monkeypatch: pytest.MonkeyPatch, field: str, second: FakeDataset
) -> None:
    install_sources(monkeypatch, FakeDataset(np.ones((10, 12))), second)

    with pytest.raises(RasterError, match=field):
        inspect_grid(product())


@pytest.mark.parametrize(
    ("size", "offset"), [(1024, 4978), (4096, 3442), (8192, 1394)]
)
def test_centers_each_benchmark_window(size: int, offset: int) -> None:
    window = centered_window(10980, 10980, size)

    assert (window.row_off, window.col_off) == (offset, offset)
    assert (window.height, window.width) == (size, size)


def test_converts_both_bands_with_one_window_and_shared_mask(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    b04 = FakeDataset(
        np.array(
            [
                [1000, 2000, 3000, 4000],
                [5000, 0, 7000, 8000],
                [9000, 10000, 11000, 12000],
                [13000, 14000, 15000, 16000],
            ],
            dtype=np.uint16,
        )
    )
    b08 = FakeDataset(
        np.array(
            [
                [400, 1400, 2400, 3400],
                [4400, 5400, 65535, 7400],
                [8400, 9400, 10400, 11400],
                [12400, 13400, 14400, 15400],
            ],
            dtype=np.uint16,
        )
    )
    install_sources(monkeypatch, b04, b08)

    prepared = prepare_window(product(), 2)

    np.testing.assert_allclose(
        prepared.b04,
        np.array([[np.nan, np.nan], [0.9, 1.0]], dtype="<f4"),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        prepared.b08,
        np.array([[np.nan, np.nan], [0.85, 0.95]], dtype="<f4"),
        equal_nan=True,
    )
    assert prepared.b04.dtype == np.dtype("<f4")
    assert prepared.b08.dtype == np.dtype("<f4")
    assert b04.read_windows[0] is b08.read_windows[0]
    assert (prepared.row_offset, prepared.column_offset) == (1, 1)


def test_preserves_reflectance_outside_zero_one_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = FakeDataset(np.array([[500, 12000], [1000, 2000]], dtype=np.uint16))
    second = FakeDataset(np.array([[400, 11900], [900, 1900]], dtype=np.uint16))
    install_sources(monkeypatch, first, second)

    prepared = prepare_window(replace(product(), boa_offset_b08=-1000), 2)

    assert prepared.b04[0, 0] == pytest.approx(-0.05)
    assert prepared.b04[0, 1] == pytest.approx(1.1)


def test_rejects_an_undersized_grid_before_reading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = (FakeDataset(np.ones((4, 4))), FakeDataset(np.ones((4, 4))))
    install_sources(monkeypatch, *sources)

    with pytest.raises(RasterError, match="cannot contain"):
        prepare_window(product(), 5)

    assert sources[0].read_windows == []
    assert sources[1].read_windows == []
