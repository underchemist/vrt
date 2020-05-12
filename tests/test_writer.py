import pytest
import xmlschema

from vrt_writer import VRTWriter

from .conftest import create_tif, create_srs


def test_to_string():
    vrt = VRTWriter()

    assert vrt.to_string() == b"<VRTDataset />\n"


def test_to_file(tmp_path):
    test_vrt = tmp_path.joinpath("test.vrt")
    vrt = VRTWriter()
    vrt.to_file(test_vrt)

    assert test_vrt.exists()
    with test_vrt.open() as f:
        assert f.read() == "<VRTDataset />\n"


def test_clear():
    vrt = VRTWriter()
    vrt.add_vrtdataset(8, 8)
    not_empty = vrt.to_string()
    vrt.clear()
    empty = vrt.to_string()
    assert empty != not_empty


def test_add_vrtdataset_int():
    vrt = VRTWriter()
    vrt.add_vrtdataset(8, 8)

    assert vrt.to_string() == b'<VRTDataset rasterXSize="8" rasterYSize="8" />\n'


def test_add_vrtdataset_float():
    vrt = VRTWriter()
    vrt.add_vrtdataset(8.0, 8.0)

    assert not vrt.is_valid
    with pytest.raises(xmlschema.XMLSchemaEncodeError):
        vrt.to_string()


def test_add_vrtdataset_subclass():
    vrt = VRTWriter()
    subclasses = ("VRTWarpedDataset", "VRTPansharpenedDataset")
    for subclass in subclasses:
        vrt.add_vrtdataset(8, 8, subclass=subclass)
        assert vrt.is_valid


def test_add_vrtdataset_invalid_subclass():
    vrt = VRTWriter()
    with pytest.raises(ValueError):
        vrt.add_vrtdataset(8, 8, subclass="NotVRTWarpedDataset")


pytest.mark.parametrize()


def test_add_srs_srs():
    srs = create_srs()
    vrt = VRTWriter()
    vrt.add_vrtdataset(8, 8)
    vrt.add_srs(srs=srs)

    expected = b'<VRTDataset rasterXSize="8" rasterYSize="8">\n    <SRS>GEOGCS[&amp;quot;WGS 84&amp;quot;,DATUM[&amp;quot;WGS_1984&amp;quot;,SPHEROID[&amp;quot;WGS 84&amp;quot;,6378137,298.257223563,AUTHORITY[&amp;quot;EPSG&amp;quot;,&amp;quot;7030&amp;quot;]],AUTHORITY[&amp;quot;EPSG&amp;quot;,&amp;quot;6326&amp;quot;]],PRIMEM[&amp;quot;Greenwich&amp;quot;,0,AUTHORITY[&amp;quot;EPSG&amp;quot;,&amp;quot;8901&amp;quot;]],UNIT[&amp;quot;degree&amp;quot;,0.0174532925199433,AUTHORITY[&amp;quot;EPSG&amp;quot;,&amp;quot;9122&amp;quot;]],AXIS[&amp;quot;Latitude&amp;quot;,NORTH],AXIS[&amp;quot;Longitude&amp;quot;,EAST],AUTHORITY[&amp;quot;EPSG&amp;quot;,&amp;quot;4326&amp;quot;]]</SRS>\n</VRTDataset>\n'
    assert vrt.is_valid
    assert vrt.to_string() == expected

    vrt.clear()
    vrt.add_vrtdataset(8, 8)
    vrt.add_srs(wkt=srs.ExportToWkt())

    assert vrt.is_valid
    assert vrt.to_string() == expected


def test_add_geotransform():
    vrt = VRTWriter()
    vrt.add_vrtdataset(8, 8)
    vrt.add_geotransform((-123.0, 0.005, 0.0, 49.0, 0.0, 0.005))

    assert vrt.is_valid
    assert (
        vrt.to_string()
        == b'<VRTDataset rasterXSize="8" rasterYSize="8">\n    <GeoTransform>-123.0, 0.005, 0.0, 49.0, 0.0, 0.005</GeoTransform>\n</VRTDataset>\n'
    )


def test_add_geotransform_invalid():
    vrt = VRTWriter()
    vrt.add_vrtdataset(8, 8)
    with pytest.raises(ValueError):
        vrt.add_geotransform(tuple())
