import pytest

from vrt_writer import VRTWriter

from .conftest import create_tif


def test_to_string():
    vrt = VRTWriter()

    assert vrt.to_string() == "<VRTDataset />"


def test_to_file(tmp_path):
    test_vrt = tmp_path.joinpath("test.vrt")
    vrt = VRTWriter()
    vrt.to_file(test_vrt)

    assert test_vrt.exists()
    with test_vrt.open() as f:
        assert f.read() == "<VRTDataset />"


def test_clear():
    vrt = VRTWriter()
    assert vrt.to_string()
    vrt.vrt.attrib["RasterXSize"] = "8"
    vrt.vrt.attrib["RasterYSize"] = "8"
    not_empty = vrt.to_string()
    vrt.clear()
    empty = vrt.to_string()
    assert empty != not_empty
