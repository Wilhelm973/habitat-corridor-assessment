import osmnx as ox
import geopandas as gpd
from shapely.geometry import box
import warnings
warnings.filterwarnings('ignore')

def download_dongzhai_vectors():
    # 董寨保护区边界框 (西, 南, 东, 北) - 使用国际通用顺序
    west, south, east, north = 114.15, 31.85, 114.32, 32.02
    
    # 🌟 核心修复：直接生成一个明确的多边形边界，免疫 OSMnx 版本更新带来的参数顺序Bug
    bounding_poly = box(west, south, east, north)
    
    print("开始从 OpenStreetMap 抓取董寨矢量数据...")

    # 1. 抓取道路网络
    try:
        print("正在获取道路数据...")
        roads = ox.features_from_polygon(bounding_poly, tags={'highway': True})
        if not roads.empty:
            roads = roads[roads.geometry.type.isin(['LineString', 'MultiLineString'])]
            clean_and_save_shp(roads, 'dongzhai_roads.shp')
        else:
            print("  --> 未找到道路数据。")
    except Exception as e:
        print(f"道路获取失败: {e}")

    # 2. 抓取水系网络
    try:
        print("正在获取水系数据...")
        rivers = ox.features_from_polygon(bounding_poly, tags={'waterway': True, 'natural': 'water'})
        if not rivers.empty:
            # 🌟 核心修复：过滤掉多边形（湖泊），只保留线型的河流和溪流，以满足 Shapefile 的单一类型限制
            rivers = rivers[rivers.geometry.type.isin(['LineString', 'MultiLineString'])]
            
            if not rivers.empty:
                clean_and_save_shp(rivers, 'dongzhai_rivers.shp')
            else:
                print("  --> 过滤后没有线型水系数据。")
        else:
            print("  --> 未找到水系数据。")
    except Exception as e:
        print(f"水系获取失败: {e}")

    # 3. 抓取村庄居民点
    try:
        print("正在获取村庄数据...")
        villages = ox.features_from_polygon(bounding_poly, tags={'place': ['village', 'hamlet', 'town']})
        if not villages.empty:
            villages = villages[villages.geometry.type.isin(['Point', 'Polygon'])]
            clean_and_save_shp(villages, 'dongzhai_villages.shp')
        else:
            print("  --> 未找到村庄数据。")
    except Exception as e:
        print(f"村庄获取失败: {e}")

    print("所有矢量数据抓取并处理完毕！")

def clean_and_save_shp(gdf, filename):
    """清理复杂属性列以兼容Shapefile格式并保存"""
    if gdf.empty:
        return
        
    keep_cols = ['geometry', 'name']
    for col in gdf.columns:
        if col in ['highway', 'waterway', 'natural', 'place']:
            keep_cols.append(col)
            
    gdf_clean = gdf[[c for c in keep_cols if c in gdf.columns]].copy()
    
    # 🌟 核心修复：安全处理空值(NaN)，防止转换为字符串或整数时报错
    for col in gdf_clean.columns:
        if col != 'geometry':
            # 将缺失数据填为"未知"，然后再安全转换为字符串
            gdf_clean[col] = gdf_clean[col].fillna('未知').astype(str)
            
    gdf_clean.to_file(filename, encoding='utf-8')
    print(f"  --> 已保存至: {filename}")

if __name__ == "__main__":
    download_dongzhai_vectors()