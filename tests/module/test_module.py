import sys
from unittest import mock
from importlib import reload

import pytest

import vrt_writer


def test_get_gdal_version_installed():
    with mock.patch("vrt_writer.gdal", create=True, __version__="3.0.4") as mock_gdal:
        GDAL_VERSION = vrt_writer.get_gdal_version()
        assert GDAL_VERSION.major == 3
        assert GDAL_VERSION.minor == 0
        assert GDAL_VERSION.patch == 4
