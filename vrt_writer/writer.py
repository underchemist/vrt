"""GDAL VRT writing classes and methods."""
import itertools
import pickle
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Sequence
from xml.sax import saxutils

import xmlschema
from osgeo import gdal, osr

from . import schemas
from .constants import VALID_SRS

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


def escape(s):
    """Escape a string for embeding in xml. For example required for WKT strings."""
    return saxutils.escape(s, entities={"'": "&apos;", '"': "&quot;"})


class VRTWriter:
    schema = get_vrt_schema()
    VRTDATASET_SUBCLASSES = ("VRTWarpedDataset", "VRTPansharpenedDataset")
    VRTRASTERBAND_SUBCLASSES = ("VRTRawRasterBand", "VRTDerivedRasterBand")
    REPEATABLE_ELEMENTS = ("Metadata", "VRTRasterBand", "Overview", "SimpleSource")
    REPEATABLE_ELEMENTS_KEY_FUNC = dict(
        zip(
            REPEATABLE_ELEMENTS,
            (
                lambda d: d["@domain"],
                lambda d: d["@band"],
                lambda d: d["SourceFilename"],
                lambda d: d["SourceBand"],
            ),
        )
    )
    VRTRASTERBAND_COLOR_INTERP = (
        "Gray",
        "Palette",
        "Red",
        "Green",
        "Blue",
        "Alpha",
        "Hue",
        "Saturation",
        "Lightness",
        "Cyan",
        "Magenta",
        "Yellow",
        "Black",
        "Unknown",
    )
    VRTRASTERBAND_PIX_FUNC = (
        "real",
        "imag",
        "complex",
        "mod",
        "phase",
        "conj",
        "sum",
        "diff",
        "mul",
        "cmul",
        "inv",
        "intensity",
        "sqrt",
        "log10",
        "dB",
        "dB2amp",
        "dB2pow",
    )

    def __init__(self):
        self.vrt = dict()

    def add_vrtdataset(self, xsize, ysize, subclass=None):
        """Add the root element of a VRTDataset.

        Args:
            xsize (int): A positive integer describing total width in pixels of dataset.
            ysize (int): A positive integer describing total height in pixels of dataset.
            subclass (str, optional): Optional subclass attribute of VRTDataset. Valid
                values are `'VRTWarpedDataset'` or `'VRTPansharpenedDataset'`. Defaults to
                None.

        Raises:
            ValueError: If subclass has invalid value.
        """
        if subclass is not None and subclass not in self.VRTDATASET_SUBCLASSES:
            raise ValueError(f"Invalid subclass {subclass} for VRTDataset element.")

        self.update_element(
            "VRTDataset",
            {"@rasterXSize": xsize, "@rasterYSize": ysize},
            {"@subClass": subclass},
        )

    def add_srs(self, srs=None, wkt=None, user_input=None, axis_mapping=None):
        """Add SRS element to VRTDataset.

        Note:
            Wkt representations as strings will have special characters `<`, `>`, `&`,
            `'`, and `"` escaped.
        Args:
            srs (osr.SpatialReference, optional): A SpatialReference object representing
                CRS of dataset. The wkt representation srs will be used in the VRTDataset.
            wkt (str, optional): Wkt representation of a CRS of a dataset.
            user_input (str, optional): Any valid input to osr.SetFromUserInput. Note that
                user_input is not escaped, so use srs or wkt for Wkt representations.
            axis_mapping (Sequence, optional): An optional attribute of SRS element.
                Describes mapping between data axis and CRS axis. If None, implies a
                GIS_TRADITIONAL_GIS_ORDER to CRS axis mapping strategy. Only valid in GDAL >=
                3.

        Raises:
            ValueError: If srs is not a valid SpatialReference object.
            ValueError: If not at least one of srs, wkt, or user_input is defined.
        """
        if srs and isinstance(srs, osr.SpatialReference):
            if not srs.Validate() == VALID_SRS:
                raise ValueError("srs is not a valid SpatialReference object.")
            wkt = escape(srs.ExportToWkt())
        elif wkt and isinstance(wkt, str):
            wkt = escape(wkt)
        elif user_input and isinstance(user_input, str):
            pass
        else:
            raise ValueError(
                "Invalid use of input arguments. One of srs, wkt, or user_input should be used."
            )

        if axis_mapping:
            if not isinstance(axis_mapping, Sequence):
                raise ValueError(
                    "axis_mapping should sequence of values mapping the axis order of CRS to axis order of coordinate transform metadata."
                )

        self.update_element(
            "SRS", {"$": wkt or user_input}, {"@dataAxisToSRSAxisMapping": axis_mapping}
        )

    def add_geotransform(self, geotransform):
        """Add GeoTransform element to VRTDataset.

        Args:
            geotransform (Sequence): Geotransform for VRTDataset.

        Raises:
            ValueError: If geotransform is not a six element sequence of values.
        """
        if not isinstance(geotransform, Sequence) or len(geotransform) != 6:
            raise ValueError("geotransform must be a six element sequence of values.")

        self.update_element("GeoTransform", {"$": ", ".join(map(str, geotransform))})

    def add_gcps(self, gcps, srs=None):
        if not isinstance(gcps, Sequence) and not isinstance(gcps[0], gdal.GCP):
            raise ValueError("gcps must be a Sequence of gdal.GCP objects.")
        if srs and isinstance(srs, osr.SpatialReference):
            if not srs.Validate() == VALID_SRS:
                raise ValueError("srs is not a valid SpatialReference object.")
        else:
            raise ValueError("srs is not a valid SpatialReference object.")

        wkt = escape(srs.ExportToWkt())
        axis_mapping = (
            None
            if not hasattr(srs, "GetDataAxisToSRSAxisMapping")
            else ",".join(map(str, srs.GetDataAxisToSRSAxisMapping()))
        )
        sub_element = {"GCP": []}
        for gcp in gcps:
            sub_element["GCP"].append(
                {
                    "@Id": gcp.Id,
                    "@Info": gcp.Info,
                    "@Pixel": gcp.GCPPixel,
                    "@Line": gcp.GCPLine,
                    "@X": gcp.GCPX,
                    "@Y": gcp.GCPY,
                    "@Z": gcp.GCPZ,
                }
            )

        self.update_element(
            "GCPList",
            sub_element,
            {"@Projection": wkt, "@dataAxisToSRSAxisMapping": axis_mapping},
        )

    def add_metadata(self, metadata, domain=None, band=None):
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be a mapping of key value pairs")
        if domain:
            if not isinstance(domain, str):
                raise ValueError("domain must be a string representing metadata domain")
        if band:
            parent = list(
                filter(lambda r: r["@band"] == band, self.vrt["VRTRasterBand"])
            )
            if len(parent) == 1:
                parent = parent[0]
            else:
                raise ValueError(f"Could not add metadata to band {band}.")
        else:
            parent = None

        sub_element = {"MDI": []}
        if not domain:
            sub_element.update({"@domain": ""})
        else:
            sub_element.update({"@domain": domain})
        for key, val in metadata.items():
            sub_element["MDI"].append({"@key": key, "$": val})

        self.update_element("Metadata", sub_element, parent=parent)

    def add_vrtrasterband(self, band, dtype="Byte", subclass=None):
        if subclass is not None and subclass not in self.VRTRASTERBAND_SUBCLASSES:
            raise ValueError(f"Invalid subclass {subclass} for VRTRasterBand element.")

        self.update_element(
            "VRTRasterBand",
            {"@band": band, "@dataType": dtype},
            {"@subClass": subclass},
        )

    def add_pixelfunc(self, band, func):
        if func not in self.VRTRASTERBAND_PIX_FUNC:
            raise ValueError("Unsupported pixel function.")

        parent = self.get_band_element(band)

        self.update_element("PixelFunctionType", {"$": func}, parent=parent)

    def add_colorinterp(self, band, interp="Gray"):
        if interp not in self.VRTRASTERBAND_COLOR_INTERP:
            raise ValueError(
                f"{interp} is not a valid color interp value. Valid values are {self.VRTRASTERBAND_COLOR_INTERP}"
            )

        parent = self.get_band_element(band)

        self.update_element("ColorInterp", {"$": interp}, parent=parent)

    def add_nodata(self, band, nodata=None, hide=False):
        if isinstance(nodata, str):
            nodata = "nan"
        if isinstance(nodata, int):
            nodata = float(nodata)
        if not isinstance(nodata, (int, float, str)):
            raise ValueError(f"NoDataValue must be a double or NaN type value.")

        parent = self.get_band_element(band)

        self.update_element("NoDataValue", {"$": nodata}, parent=parent)

        if hide:
            self.update_element(
                "HideNoDataValue", {"$": 1 if hide else 0}, parent=parent
            )

    def add_colortable(self, band, colors):
        if not (isinstance(colors, Sequence) and len(colors[0]) in (3, 4)):
            raise ValueError(f"ColorTable must be a sequence of RGB/RGBA tuples")
        parent = self.get_band_element(band)

        sub_element = {"Entry": []}
        for color in colors:
            sub_element["Entry"].append(
                {f"@c{i}": c for i, c in enumerate(color, start=1)}
            )

        self.update_element("ColorTable", sub_element, parent=parent)

    def add_description(self, band, desc):
        parent = self.get_band_element(band)

        self.update_element("Description", {"$": desc}, parent=parent)

    def add_unittype(self, band, unittype="m"):
        if unittype not in ("m", "ft"):
            raise ValueError("Invalid UnitType value. Valid values are 'm' or 'ft'.")

        parent = self.get_band_element(band)

        self.update_element("UnitType", {"$": unittype})

    def add_offset(self, band, offset=0.0):
        parent = self.get_band_element(band)

        self.update_element("Offset", {"$": offset}, parent=parent)

    def add_scale(self, band, scale=1.0):
        parent = self.get_band_element(band)

        self.update_element("Scale", {"$": scale}, parent=parent)

    def add_overview(self, band, source_filename, source_band, relative=False):
        parent = self.get_band_element(band)

        sub_element = {
            "SourceFilename": {
                "@relativeToVRT": 1 if relative else 0,
                "$": source_filename,
            },
            "SourceBand": {"$": str(source_band)},
        }

        self.update_element("Overview", sub_element, parent=parent)

    def add_categorynames(self, band):
        raise NotImplementedError

    def add_rasterattrtable(self, band):
        raise NotImplementedError

    def add_source(
        self,
        band,
        source_filename,
        source_band,
        type="Simple",
        src_xsize=None,
        src_ysize=None,
        src_dtype=None,
        src_block_xsize=None,
        src_block_ysize=None,
        src_win_xoff=None,
        src_win_yoff=None,
        src_win_xsize=None,
        src_win_ysize=None,
        dst_win_xoff=None,
        dst_win_yoff=None,
        dst_win_xsize=None,
        dst_win_ysize=None,
        relative=False,
        shared=True,
        open_options=None,
    ):
        parent = self.get_band_element(band)

        sub_element = {
            "SourceFilename": {
                "@relativeToVRT": 1 if relative else 0,
                "@shared": "1" if shared else "0",
                "$": source_filename,
            },
            "SourceBand": {"$": str(source_band)},
        }

        if any((src_xsize, src_ysize, src_block_xsize, src_block_ysize, src_dtype)):
            sub_element.update(
                {
                    "SourceProperties": {
                        "@RasterXSize": src_xsize,
                        "@RasterYSize": src_ysize,
                        "@DataType": src_dtype,
                        "@BlockXSize": src_block_xsize,
                        "@BlockYSize": src_block_ysize,
                    }
                }
            )

        if any((src_win_xoff, src_win_yoff, src_win_xsize, src_win_ysize)):
            sub_element.update(
                {
                    "SrcRect": {
                        "@xOff": src_win_xoff,
                        "@yOff": src_win_yoff,
                        "@xSize": src_win_xsize,
                        "@ySize": src_win_ysize,
                    }
                }
            )
        if any((dst_win_xoff, dst_win_yoff, dst_win_xsize, dst_win_ysize)):
            sub_element.update(
                {
                    "DstRect": {
                        "@xOff": dst_win_xoff,
                        "@yOff": dst_win_yoff,
                        "@xSize": dst_win_xsize,
                        "@ySize": dst_win_ysize,
                    }
                }
            )

        if open_options:
            sub_element.update(
                {
                    "OpenOptions": {
                        "OOI": [
                            {"@key": key, "$": val} for key, val in open_options.items()
                        ]
                    }
                }
            )

        self.update_element(f"{type}Source", sub_element, parent=parent)

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

    def get_band_element(self, band):
        element = next(filter(lambda d: d["@band"] == band, self.vrt["VRTRasterBand"]))
        if not element:
            raise ValueError(
                f"VRTRasterBand corresponding to index {band} does not exist."
            )

        return element

    def update_element(self, element, mapping, optional_mapping=None, parent=None):
        """Update element of `vrt` corresponding to a valid VRT xml element. Will overwrite element if already exists.

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
        else:
            optional_mapping = dict()

        if parent:
            node = parent
        else:
            node = self.vrt

        if element in self.REPEATABLE_ELEMENTS:
            d = []
            if element in node:
                n = len(node[element])
                touched = False
                for key, group in itertools.groupby(
                    node[element], key=self.REPEATABLE_ELEMENTS_KEY_FUNC[element]
                ):
                    if key in mapping.values():
                        d.append({**mapping, **optional_mapping})
                        touched = True
                    else:
                        d.append(list(group)[0])
                if len(d) == n and not touched:
                    d.append({**mapping, **optional_mapping})
            else:
                d.append({**mapping, **optional_mapping})
        else:
            d = {**mapping, **optional_mapping}

        if element == "VRTDataset":
            node.update(d)
        else:
            node.update({element: d})

    @property
    def is_valid(self):
        try:
            self.schema.encode(self.vrt)
            return True
        except xmlschema.XMLSchemaEncodeError:
            return False

    def clear(self):
        """Clear VRTDataset contents."""
        self.vrt = dict()
