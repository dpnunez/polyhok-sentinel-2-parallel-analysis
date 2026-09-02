from pathlib import Path

import pytest

from sentinel2_prepare.metadata import MetadataError, discover_product

PRODUCT_XML = """\
<n1:Level-2A_User_Product xmlns:n1="urn:test">
  <PRODUCT_URI>S2C_MSIL2A_20260620T133151_N0511_R081_T22HCK_20260620T170000.SAFE</PRODUCT_URI>
  <BOA_QUANTIFICATION_VALUE>10000</BOA_QUANTIFICATION_VALUE>
  <BOA_ADD_OFFSET band_id="3">-1000</BOA_ADD_OFFSET>
  <BOA_ADD_OFFSET band_id="7">-900</BOA_ADD_OFFSET>
  <Special_Values><SPECIAL_VALUE_TEXT>NODATA</SPECIAL_VALUE_TEXT><SPECIAL_VALUE_INDEX>0</SPECIAL_VALUE_INDEX></Special_Values>
  <Special_Values><SPECIAL_VALUE_TEXT>SATURATED</SPECIAL_VALUE_TEXT><SPECIAL_VALUE_INDEX>65535</SPECIAL_VALUE_INDEX></Special_Values>
</n1:Level-2A_User_Product>
"""

TILE_XML = """\
<n1:Level-2A_Tile_ID xmlns:n1="urn:test">
  <TILE_ID>S2C_OPER_MSI_L2A_TL_TEST_20260620T133151_A000001_T22HCK_N05.11</TILE_ID>
  <SENSING_TIME>2026-06-20T13:31:51.000Z</SENSING_TIME>
</n1:Level-2A_Tile_ID>
"""


def make_safe(tmp_path: Path) -> Path:
    safe = tmp_path / "product.SAFE"
    raster_dir = safe / "GRANULE" / "L2A_T22HCK_TEST" / "IMG_DATA" / "R10m"
    raster_dir.mkdir(parents=True)
    (safe / "MTD_MSIL2A.xml").write_text(PRODUCT_XML)
    (raster_dir.parents[1] / "MTD_TL.xml").write_text(TILE_XML)
    (raster_dir / "T22HCK_B04_10m.jp2").write_bytes(b"b04")
    (raster_dir / "T22HCK_B08_10m.jp2").write_bytes(b"b08")
    return safe


def test_discovers_one_product_and_parses_xml_values(tmp_path: Path) -> None:
    safe = make_safe(tmp_path)

    product = discover_product(safe)

    assert product.product_id == (
        "S2C_MSIL2A_20260620T133151_N0511_R081_T22HCK_20260620T170000"
    )
    assert product.tile_id == "T22HCK"
    assert product.sensing_time_utc == "2026-06-20T13:31:51.000Z"
    assert product.b04_path.name == "T22HCK_B04_10m.jp2"
    assert product.b08_path.name == "T22HCK_B08_10m.jp2"
    assert product.product_metadata_path == safe / "MTD_MSIL2A.xml"
    assert product.tile_metadata_path.name == "MTD_TL.xml"
    assert product.boa_offset_b04 == -1000.0
    assert product.boa_offset_b08 == -900.0
    assert product.quantification == 10000.0
    assert product.nodata == 0
    assert product.saturated == 65535
    assert len(product.source_checksum) == 64


@pytest.mark.parametrize(
    ("relative_path", "message"),
    [
        ("MTD_MSIL2A.xml", "MTD_MSIL2A.xml"),
        ("GRANULE/L2A_T22HCK_TEST/MTD_TL.xml", "MTD_TL.xml"),
        ("GRANULE/L2A_T22HCK_TEST/IMG_DATA/R10m/T22HCK_B04_10m.jp2", "B04"),
        ("GRANULE/L2A_T22HCK_TEST/IMG_DATA/R10m/T22HCK_B08_10m.jp2", "B08"),
    ],
)
def test_rejects_a_missing_required_file(
    tmp_path: Path, relative_path: str, message: str
) -> None:
    safe = make_safe(tmp_path)
    (safe / relative_path).unlink()

    with pytest.raises(MetadataError, match=message):
        discover_product(safe)


def test_rejects_duplicate_required_band(tmp_path: Path) -> None:
    safe = make_safe(tmp_path)
    raster_dir = safe / "GRANULE" / "L2A_T22HCK_TEST" / "IMG_DATA" / "R10m"
    (raster_dir / "duplicate_B04_10m.jp2").write_bytes(b"duplicate")

    with pytest.raises(MetadataError, match="exactly one B04"):
        discover_product(safe)


def test_rejects_bands_from_different_granules(tmp_path: Path) -> None:
    safe = make_safe(tmp_path)
    first = safe / "GRANULE" / "L2A_T22HCK_TEST" / "IMG_DATA" / "R10m"
    second = safe / "GRANULE" / "L2A_T22HCK_OTHER" / "IMG_DATA" / "R10m"
    second.mkdir(parents=True)
    (first / "T22HCK_B08_10m.jp2").rename(second / "T22HCK_B08_10m.jp2")

    with pytest.raises(MetadataError, match="different granules"):
        discover_product(safe)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (
            "<BOA_QUANTIFICATION_VALUE>10000</BOA_QUANTIFICATION_VALUE>",
            "",
            "BOA_QUANTIFICATION_VALUE",
        ),
        (
            "<BOA_QUANTIFICATION_VALUE>10000</BOA_QUANTIFICATION_VALUE>",
            "<BOA_QUANTIFICATION_VALUE>0</BOA_QUANTIFICATION_VALUE>",
            "must be positive",
        ),
        ("<BOA_ADD_OFFSET band_id=\"3\">-1000</BOA_ADD_OFFSET>", "", "B04"),
        (
            "<SPECIAL_VALUE_TEXT>NODATA</SPECIAL_VALUE_TEXT>",
            "<SPECIAL_VALUE_TEXT>OTHER</SPECIAL_VALUE_TEXT>",
            "NODATA",
        ),
    ],
)
def test_rejects_missing_or_invalid_radiometric_metadata(
    tmp_path: Path, old: str, new: str, message: str
) -> None:
    safe = make_safe(tmp_path)
    product_xml = safe / "MTD_MSIL2A.xml"
    product_xml.write_text(product_xml.read_text().replace(old, new))

    with pytest.raises(MetadataError, match=message):
        discover_product(safe)


def test_rejects_invalid_xml_before_raster_conversion(tmp_path: Path) -> None:
    safe = make_safe(tmp_path)
    (safe / "MTD_MSIL2A.xml").write_text("<broken>")

    with pytest.raises(MetadataError, match="cannot parse required metadata"):
        discover_product(safe)
