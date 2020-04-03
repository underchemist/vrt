"""Library for easily building and writing GDAL VRT datasets."""

import importlib.metadata
from collections import namedtuple

from osgeo import gdal

from . import constants, writer
from .writer import VRTWriter


def get_gdal_version():
    ver = gdal.__version__
    major, minor, patch = map(int, ver.split("."))
    GdalVersion = namedtuple("GdalVersion", ["major", "minor", "patch"])

    return GdalVersion(major=major, minor=minor, patch=patch)


__version__ = importlib.metadata.version(__name__)
GDAL_VERSION = get_gdal_version()
