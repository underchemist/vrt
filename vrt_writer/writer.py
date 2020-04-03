"""GDAL VRT writing classes and methods."""
import pickle
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Sequence

import xmlschema

from . import schemas

try:
    import importlib.resources as pkg_resources
except ImportError:
    # https://stackoverflow.com/questions/6028000/how-to-read-a-static-file-from-inside-a-python-package
    import importlib_resources as pkg_resources


def get_vrt_schema():
    """Load gdal VRT xml schema as xmlschema.XMLSchema object, used for encoding and decoding data structures.

    First try loading from pickle, otherwise parse from xsd file.

    Returns:
        (xmlschema.XMLSchema): Parsed schema object.
    """
    try:
        with pkg_resources.open_binary(schemas, "gdalvrt.pickle") as f:
            schema = pickle.load(f)
    except:
        with pkg_resources.open_text(schemas, "gdalvrt.xsd") as f:
            schema = xmlschema.XMLSchema(f)

    return schema


class VRTWriter:
    def __init__(self):
        self.vrt = ET.Element("VRTDataset")

    def add_dataset(
        self,
        dataset=None,
        xsize=None,
        ysize=None,
        geotransform=None,
        gcps=None,
        metadata=None,
    ):
        if dataset:
            xsize = dataset.RasterXSize
            ysize = dataset.RasterYSize
            geotransform = dataset.GetGeoTransform()
            metadata = {
                domain: dataset.GetMetadata(domain)
                for domain in dataset.GetMetadataDomainList()
            }
        if not dataset:
            if not any((xsize, ysize, (geotransform or gcps))):
                raise TypeError("")
            if not metadata:
                metadata = {"": dict()}

        # serialize
        xsize = str(xsize)
        ysize = str(ysize)
        geotransform = ",".join(map(str, geotransform))
        gcps

        self.vrt.attrib["RasterXSize"] = xsize

    def to_string(self):
        """Return a string representation of VRTDataset."""
        return ET.tostring(self.vrt).decode()

    def to_file(self, path):
        """Write VRTDataset to file.

        Args:
            path (str or Pathlike): Path to write VRTDataset to.
        """
        path = Path(path)
        with path.open("wb") as f:
            f.write(ET.tostring(self.vrt))

    def clear(self):
        """Clear VRTDataset contents."""
        self.vrt = ET.Element("VRTDataset")
