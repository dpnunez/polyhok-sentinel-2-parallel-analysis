"""Aligned raster window preparation for Sentinel-2 B04 and B08."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import rasterio
from rasterio.windows import Window

from sentinel2_prepare.metadata import ProductMetadata

CROP_SIZES = (1024, 4096, 8192)


class RasterError(ValueError):
    """Raised when source rasters cannot satisfy the preparation contract."""


@dataclass(frozen=True)
class Grid:
    width: int
    height: int
    crs: str
    transform: object
    bounds: tuple[float, float, float, float]
    pixel_size: tuple[float, float]
    origin: tuple[float, float]


@dataclass(frozen=True)
class PreparedBands:
    b04: np.ndarray
    b08: np.ndarray
    width: int
    height: int
    row_offset: int
    column_offset: int
    crs: str
    pixel_size: tuple[float, float]
    origin: tuple[float, float]


def _grid(dataset: object) -> Grid:
    transform = dataset.transform
    return Grid(
        width=dataset.width,
        height=dataset.height,
        crs=str(dataset.crs),
        transform=transform,
        bounds=tuple(dataset.bounds),
        pixel_size=(float(transform.a), float(transform.e)),
        origin=(float(transform.c), float(transform.f)),
    )


def _validate_grid_pair(b04: object, b08: object) -> Grid:
    first = _grid(b04)
    second = _grid(b08)
    fields = ("width", "height", "crs", "origin", "pixel_size", "bounds", "transform")
    mismatches = [
        field for field in fields if getattr(first, field) != getattr(second, field)
    ]
    if mismatches:
        raise RasterError(f"B04/B08 grid mismatch: {', '.join(mismatches)}")
    return first


def inspect_grid(product: ProductMetadata) -> Grid:
    """Return the common grid after validating every spatial property."""
    with (
        rasterio.open(product.b04_path) as b04,
        rasterio.open(product.b08_path) as b08,
    ):
        return _validate_grid_pair(b04, b08)


def centered_window(width: int, height: int, size: int) -> Window:
    """Build the deterministic square crop window documented by the project."""
    if size <= 0 or width < size or height < size:
        raise RasterError(f"grid {width}x{height} cannot contain {size}x{size} crop")
    return Window((width - size) // 2, (height - size) // 2, size, size)


def _convert(
    b04_dn: np.ndarray,
    b08_dn: np.ndarray,
    product: ProductMetadata,
) -> tuple[np.ndarray, np.ndarray]:
    invalid = (
        (b04_dn == product.nodata)
        | (b04_dn == product.saturated)
        | (b08_dn == product.nodata)
        | (b08_dn == product.saturated)
    )
    quantification = np.float32(product.quantification)
    b04 = (
        b04_dn.astype(np.float32) + np.float32(product.boa_offset_b04)
    ) / quantification
    b08 = (
        b08_dn.astype(np.float32) + np.float32(product.boa_offset_b08)
    ) / quantification
    b04[invalid] = np.nan
    b08[invalid] = np.nan
    return b04.astype("<f4", copy=False), b08.astype("<f4", copy=False)


def prepare_window(product: ProductMetadata, size: int) -> PreparedBands:
    """Read one common window and convert both bands to prepared reflectance."""
    with (
        rasterio.open(product.b04_path) as b04_source,
        rasterio.open(product.b08_path) as b08_source,
    ):
        grid = _validate_grid_pair(b04_source, b08_source)
        window = centered_window(grid.width, grid.height, size)
        b04_dn = b04_source.read(1, window=window)
        b08_dn = b08_source.read(1, window=window)

    b04, b08 = _convert(b04_dn, b08_dn, product)
    return PreparedBands(
        b04=b04,
        b08=b08,
        width=size,
        height=size,
        row_offset=int(window.row_off),
        column_offset=int(window.col_off),
        crs=grid.crs,
        pixel_size=grid.pixel_size,
        origin=grid.origin,
    )
