"""Discovery and metadata parsing for one Sentinel-2 L2A product."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


class MetadataError(ValueError):
    """Raised when a SAFE product does not satisfy the preparation contract."""


@dataclass(frozen=True)
class ProductMetadata:
    product_id: str
    tile_id: str
    sensing_time_utc: str
    b04_path: Path
    b08_path: Path
    product_metadata_path: Path
    tile_metadata_path: Path
    boa_offset_b04: float
    boa_offset_b08: float
    quantification: float
    nodata: int
    saturated: int
    source_checksum: str


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _elements(root: ET.Element, name: str) -> list[ET.Element]:
    return [element for element in root.iter() if _local_name(element.tag) == name]


def _required_text(root: ET.Element, name: str) -> str:
    values = [element.text.strip() for element in _elements(root, name) if element.text]
    if len(values) != 1 or not values[0]:
        raise MetadataError(f"expected exactly one valid {name}")
    return values[0]


def _required_number(root: ET.Element, name: str) -> float:
    text = _required_text(root, name)
    try:
        value = float(text)
    except ValueError as error:
        raise MetadataError(f"invalid numeric value for {name}") from error
    if not value == value:
        raise MetadataError(f"invalid numeric value for {name}")
    return value


def _band_offset(root: ET.Element, band_id: str, band_name: str) -> float:
    matches = [
        element
        for element in _elements(root, "BOA_ADD_OFFSET")
        if element.attrib.get("band_id") == band_id
    ]
    if len(matches) != 1 or not matches[0].text:
        raise MetadataError(f"expected one BOA_ADD_OFFSET for {band_name}")
    try:
        value = float(matches[0].text.strip())
    except ValueError as error:
        raise MetadataError(f"invalid BOA_ADD_OFFSET for {band_name}") from error
    if not value == value:
        raise MetadataError(f"invalid BOA_ADD_OFFSET for {band_name}")
    return value


def _special_values(root: ET.Element) -> tuple[int, int]:
    values: dict[str, int] = {}
    for special in _elements(root, "Special_Values"):
        texts = _elements(special, "SPECIAL_VALUE_TEXT")
        indices = _elements(special, "SPECIAL_VALUE_INDEX")
        if len(texts) != 1 or len(indices) != 1:
            continue
        name = (texts[0].text or "").strip().upper()
        try:
            values[name] = int((indices[0].text or "").strip())
        except ValueError as error:
            raise MetadataError(f"invalid {name or 'special'} value") from error
    if "NODATA" not in values or "SATURATED" not in values:
        raise MetadataError("NODATA and SATURATED values are required")
    return values["NODATA"], values["SATURATED"]


def _parse_xml(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError) as error:
        raise MetadataError(f"cannot parse required metadata: {path.name}") from error


def _one_path(paths: list[Path], description: str) -> Path:
    if len(paths) != 1:
        raise MetadataError(f"expected exactly one {description}, found {len(paths)}")
    return paths[0]


def _source_checksum(safe_path: Path, paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(safe_path).as_posix()):
        relative = path.relative_to(safe_path).as_posix().encode()
        digest.update(len(relative).to_bytes(4, "little"))
        digest.update(relative)
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def discover_product(safe_path: Path) -> ProductMetadata:
    """Discover one aligned pair candidate and parse its required XML metadata."""
    safe_path = safe_path.resolve()
    if not safe_path.is_dir() or safe_path.suffix != ".SAFE":
        raise MetadataError(f"SAFE product directory not found: {safe_path}")

    product_xml = _one_path(list(safe_path.glob("MTD_MSIL2A.xml")), "MTD_MSIL2A.xml")
    b04_path = _one_path(
        list(safe_path.glob("GRANULE/*/IMG_DATA/R10m/*_B04_10m.jp2")),
        "B04 10 m raster",
    )
    b08_path = _one_path(
        list(safe_path.glob("GRANULE/*/IMG_DATA/R10m/*_B08_10m.jp2")),
        "B08 10 m raster",
    )
    b04_granule = b04_path.parents[2]
    b08_granule = b08_path.parents[2]
    if b04_granule != b08_granule:
        raise MetadataError("B04 and B08 belong to different granules")
    tile_xml = _one_path(list(b04_granule.glob("MTD_TL.xml")), "MTD_TL.xml")

    product_root = _parse_xml(product_xml)
    tile_root = _parse_xml(tile_xml)
    product_id = _required_text(product_root, "PRODUCT_URI").removesuffix(".SAFE")
    tile_identity = _required_text(tile_root, "TILE_ID")
    tile_match = re.search(r"T\d{2}[A-Z]{3}", tile_identity)
    if tile_match is None:
        raise MetadataError("TILE_ID does not contain a Sentinel-2 tile identifier")
    sensing_time = _required_text(tile_root, "SENSING_TIME")
    quantification = _required_number(product_root, "BOA_QUANTIFICATION_VALUE")
    if quantification <= 0:
        raise MetadataError("BOA_QUANTIFICATION_VALUE must be positive")
    nodata, saturated = _special_values(product_root)
    paths = (b04_path, b08_path, product_xml, tile_xml)

    return ProductMetadata(
        product_id=product_id,
        tile_id=tile_match.group(0),
        sensing_time_utc=sensing_time,
        b04_path=b04_path,
        b08_path=b08_path,
        product_metadata_path=product_xml,
        tile_metadata_path=tile_xml,
        boa_offset_b04=_band_offset(product_root, "3", "B04"),
        boa_offset_b08=_band_offset(product_root, "7", "B08"),
        quantification=quantification,
        nodata=nodata,
        saturated=saturated,
        source_checksum=_source_checksum(safe_path, paths),
    )
