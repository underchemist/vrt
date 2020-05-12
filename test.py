import vrt_writer

from osgeo import gdal, osr

vrt = vrt_writer.VRTWriter()
src = gdal.Open("test.vrt")
vrt.add_vrtdataset(xsize=src.RasterXSize, ysize=src.RasterYSize)
for domain in src.GetMetadataDomainList():
    vrt.add_metadata(src.GetMetadata(domain), domain=domain)

for idx, band in enumerate(
    (src.GetRasterBand(i) for i in range(1, src.RasterCount + 1)), start=1
):
    vrt.add_vrtrasterband(idx, dtype="Float64", subclass="VRTDerivedRasterBand")
    vrt.add_pixelfunc(idx, "dB")
    blockxsize, blockysize = band.GetBlockSize()
    vrt.add_source(
        idx,
        src.GetDescription(),
        idx,
        src_xsize=src.RasterXSize,
        src_ysize=src.RasterYSize,
        src_dtype=gdal.GetDataTypeName(band.DataType),
        src_block_xsize=blockxsize,
        src_block_ysize=blockysize,
        relative=True,
    )

vrt.to_file("test2.vrt")
