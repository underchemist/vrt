from osgeo import gdal, osr
import uuid


def create_tif(xsize=8, ysize=8, count=1, dtype=None):
    if not dtype:
        dtype = gdal.GDT_Byte
    driver = gdal.GetDriverByName("GTiff")
    src = driver.Create(f"/vsimem/{uuid.uuid4()}", xsize, ysize, count, dtype)
    src.FlushCache()

    return src


def create_srs(epsg=4326):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)

    return srs
