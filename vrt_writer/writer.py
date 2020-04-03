"""GDAL VRT writing classes and methods."""
import pickle
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Sequence
from xml.sax.saxutils import escape

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
    schema = get_vrt_schema()
    DATASET_SUBCLASSES = ("VRTWarpedDataset", "VRTPansharpenedDataset")

    def __init__(self):
        self.vrt = dict()

    def add_vrtdataset(self, xsize, ysize, subclass=None):
        if subclass is not None and subclass not in self.DATASET_SUBCLASSES:
            raise ValueError(f"Invalid subclass {subclass} for VRTDataset element.")

        self.update_element(
            "VRTDataset",
            {"@rasterXSize": xsize, "@rasterYSize": ysize},
            {"@subClass": subclass},
        )

    def add_SRS(self, srs=None, wkt=None, user_input=None):
        pass

    def to_string(self):
        """Return a string representation of VRTDataset."""
        return ET.tostring(self.schema.encode(self.vrt))

    def to_file(self, path):
        """Write VRTDataset to file.

        Args:
            path (str or Pathlike): Path to write VRTDataset to.
        """
        path = Path(path)
        with path.open("wb") as f:
            f.write(self.to_string())

    def update_element(self, element, mapping, optional_mapping=None):
        """Update element of `vrt` corresponding to a valid VRT xml element.

        Args:
            element (str): Name of VRT element to update.
            mapping (dict): A dict containing required attributes and subelements of `element`.
            optional_mapping (dict): A dict containing optional attributes of `element`.
                Any key-value pairs will be added to the `element` provided the value is not
                None.
        """
        if optional_mapping:
            optional_mapping = {
                key: value for key, value in optional_mapping.items() if value
            }

        d = {**mapping, **optional_mapping}

        if element == "VRTDataset":
            self.vrt.update(d)
        else:
            self.vrt.update(element=d)

    @property
    def is_valid(self):
        return self.schema.is_valid(self.schema.encode(self.vrt))

    def clear(self):
        """Clear VRTDataset contents."""
        self.vrt = dict()
