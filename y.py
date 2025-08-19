import geopandas as gpd

# Baca shapefile
gdf = gpd.read_file("Data/ADMINISTRASIDESA_AR_25K.shp")

# Simpan ke GeoJSON
gdf.to_file("filedata.geojson", driver="GeoJSON")

