import numpy as np
from osgeo import gdal, osr

# Input and output paths
input_dtm = r"C:/Users/user/Desktop/UvA/YEAR 2/Thesis/LiDAR/DTM data/Merged_DTM.tif"
output_dtm = r"C:/Users/user/Desktop/UvA/YEAR 2/Thesis/LiDAR/DTM data/Merged_DTM_masked.tif"

# Open the input DTM
ds = gdal.Open(input_dtm)
band = ds.GetRasterBand(1)
elevation = band.ReadAsArray().astype(np.float32)

# Mask water (elevation == 0) as NaN
masked_elevation = np.where(elevation == 0, np.nan, elevation)

# Create output file
driver = gdal.GetDriverByName('GTiff')
out_ds = driver.Create(
    output_dtm,
    ds.RasterXSize,
    ds.RasterYSize,
    1,
    gdal.GDT_Float32
)
out_ds.SetGeoTransform(ds.GetGeoTransform())
out_ds.SetProjection(ds.GetProjection())

# Write the masked array
out_band = out_ds.GetRasterBand(1)
out_band.WriteArray(masked_elevation)
out_band.SetNoDataValue(np.nan)
out_band.FlushCache()

# Clean up
del out_band
out_ds = None
ds = None

print(f"Masked DTM saved to {output_dtm}") 