import geopandas as gpd
from shapely.geometry import box

# 董寨的边界框坐标
west, south, east, north = 114.15, 31.85, 114.32, 32.02
boundary_geom = box(west, south, east, north)

# 创建并保存为多边形 Shapefile
gdf = gpd.GeoDataFrame({'name': ['Dongzhai Reserve']}, geometry=[boundary_geom], crs="EPSG:4326")
gdf.to_file('sample_data/dongzhai_boundary.shp', encoding='utf-8')
print("董寨矩形边界 dongzhai_boundary.shp 已成功生成！")