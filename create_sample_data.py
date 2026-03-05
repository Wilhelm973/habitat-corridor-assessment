#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例数据生成脚本
功能：创建用于测试的模拟数据
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.transform import Affine
from shapely.geometry import Polygon, Point, LineString
import random
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SampleDataCreator:
    """示例数据创建类"""
    
    def __init__(self, output_dir='./sample_data'):
        """初始化"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 研究区域参数（模拟一个10km×10km的区域）
        self.xmin = 117.0  # 经度
        self.ymin = 31.5   # 纬度
        self.xmax = 117.1
        self.ymax = 31.6
        self.crs_wgs84 = 'EPSG:4326'
        self.crs_projected = 'EPSG:4547'  # CGCS2000 3度带
        
        # 栅格参数
        self.resolution = 30  # 30米分辨率
        self.width = 333      # 10km / 30m ≈ 333像元
        self.height = 333
    
    def create_boundary(self):
        """创建保护区边界"""
        logger.info("创建保护区边界数据")
        
        # 创建多边形边界
        polygon = Polygon([
            (self.xmin, self.ymin),
            (self.xmax, self.ymin),
            (self.xmax, self.ymax),
            (self.xmin, self.ymax)
        ])
        
        # 创建GeoDataFrame
        gdf = gpd.GeoDataFrame(
            {'name': ['自然保护区']},
            geometry=[polygon],
            crs=self.crs_wgs84
        )
        
        # 投影到目标坐标系
        gdf = gdf.to_crs(self.crs_projected)
        
        # 保存文件
        output_path = self.output_dir / 'reserve_boundary.shp'
        gdf.to_file(output_path)
        
        logger.info(f"保护区边界已创建: {output_path}")
        return output_path
    
    def create_species_points(self, n_points=50):
        """创建物种出现点数据"""
        logger.info(f"创建物种出现点数据 ({n_points}个点)")
        
        # 在边界内随机生成点
        points = []
        for _ in range(n_points):
            # 在边界内随机生成坐标
            x = random.uniform(self.xmin, self.xmax)
            y = random.uniform(self.ymin, self.ymax)
            
            # 偏向某些区域（模拟物种偏好）
            if random.random() > 0.7:
                # 70%的点集中在中心区域
                x = random.uniform(self.xmin + 0.03, self.xmax - 0.03)
                y = random.uniform(self.ymin + 0.03, self.ymax - 0.03)
            
            points.append(Point(x, y))
        
        # 创建DataFrame
        df = pd.DataFrame({
            'species': ['白冠长尾雉'] * n_points,
            'date': pd.date_range('2024-01-01', periods=n_points).strftime('%Y-%m-%d'),
            'camera_id': [f'CAM_{i:03d}' for i in range(1, n_points + 1)],
            'longitude': [p.x for p in points],
            'latitude': [p.y for p in points]
        })
        
        # 保存CSV
        csv_path = self.output_dir / 'species_occurrence.csv'
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        logger.info(f"物种出现点数据已创建: {csv_path}")
        return csv_path
    
    def create_roads(self):
        """创建道路数据"""
        logger.info("创建道路数据")
        
        # 创建几条模拟道路
        roads = []
        
        # 主道路（横穿保护区）
        road1 = LineString([
            (self.xmin + 0.02, self.ymin + 0.05),
            (self.xmax - 0.02, self.ymin + 0.05)
        ])
        roads.append({'name': 'G205国道', 'type': '国道', 'geometry': road1})
        
        # 次要道路
        road2 = LineString([
            (self.xmin + 0.1, self.ymin + 0.02),
            (self.xmin + 0.1, self.ymax - 0.02)
        ])
        roads.append({'name': '县道X001', 'type': '县道', 'geometry': road2})
        
        # 土路
        road3 = LineString([
            (self.xmin + 0.05, self.ymin + 0.3),
            (self.xmin + 0.15, self.ymin + 0.25),
            (self.xmin + 0.2, self.ymin + 0.35)
        ])
        roads.append({'name': '巡护土路', 'type': '土路', 'geometry': road3})
        
        # 创建GeoDataFrame
        gdf = gpd.GeoDataFrame(roads, crs=self.crs_wgs84)
        gdf = gdf.to_crs(self.crs_projected)
        
        # 保存文件
        output_path = self.output_dir / 'roads.shp'
        gdf.to_file(output_path)
        
        logger.info(f"道路数据已创建: {output_path}")
        return output_path
    
    def create_villages(self):
        """创建村庄数据"""
        logger.info("创建村庄数据")
        
        # 创建几个模拟村庄
        villages = []
        
        village_locations = [
            (self.xmin + 0.08, self.ymin + 0.08, '张家村'),
            (self.xmin + 0.15, self.ymin + 0.25, '李家庄'),
            (self.xmax - 0.08, self.ymax - 0.08, '王家屯')
        ]
        
        for x, y, name in village_locations:
            # 创建村庄多边形（圆形缓冲区）
            center = Point(x, y)
            village_poly = center.buffer(0.005)  # 约500米半径
            
            villages.append({
                'name': name,
                'population': random.randint(100, 500),
                'geometry': village_poly
            })
        
        # 创建GeoDataFrame
        gdf = gpd.GeoDataFrame(villages, crs=self.crs_wgs84)
        gdf = gdf.to_crs(self.crs_projected)
        
        # 保存文件
        output_path = self.output_dir / 'villages.shp'
        gdf.to_file(output_path)
        
        logger.info(f"村庄数据已创建: {output_path}")
        return output_path
    
    def create_rivers(self):
        """创建水系数据"""
        logger.info("创建水系数据")
        
        # 创建模拟河流
        rivers = []
        
        # 主河流
        river1 = LineString([
            (self.xmin + 0.25, self.ymin),
            (self.xmin + 0.2, self.ymin + 0.3),
            (self.xmin + 0.15, self.ymax)
        ])
        rivers.append({'name': '清水河', 'type': '河流', 'geometry': river1})
        
        # 支流
        river2 = LineString([
            (self.xmin + 0.35, self.ymin + 0.2),
            (self.xmin + 0.25, self.ymin + 0.3),
            (self.xmin + 0.2, self.ymin + 0.4)
        ])
        rivers.append({'name': '小溪', 'type': '溪流', 'geometry': river2})
        
        # 创建GeoDataFrame
        gdf = gpd.GeoDataFrame(rivers, crs=self.crs_wgs84)
        gdf = gdf.to_crs(self.crs_projected)
        
        # 保存文件
        output_path = self.output_dir / 'rivers.shp'
        gdf.to_file(output_path)
        
        logger.info(f"水系数据已创建: {output_path}")
        return output_path
    
    def create_dem(self):
        """创建数字高程模型（DEM）"""
        logger.info("创建数字高程模型")
        
        # 创建变换
        transform = Affine.translation(self.xmin, self.ymax) * \
                   Affine.scale((self.xmax - self.xmin) / self.width,
                               -(self.ymax - self.ymin) / self.height)
        
        # 创建地形数据（模拟山地地形）
        x = np.linspace(0, 2*np.pi, self.width)
        y = np.linspace(0, 2*np.pi, self.height)
        X, Y = np.meshgrid(x, y)
        
        # 模拟复杂地形
        dem = (
            500 +  # 基准海拔
            200 * np.sin(X) * np.cos(Y) +  # 主要山脉
            100 * np.sin(2*X) * np.cos(2*Y) +  # 次要地形
            50 * np.random.randn(self.height, self.width)  # 随机噪声
        )
        
        # 确保正值
        dem = np.maximum(dem, 300)
        
        # 保存GeoTIFF
        output_path = self.output_dir / 'dem.tif'
        
        with rasterio.open(
            output_path, 'w',
            driver='GTiff',
            height=self.height,
            width=self.width,
            count=1,
            dtype=np.float32,
            crs=self.crs_wgs84,
            transform=transform,
            nodata=-9999
        ) as dst:
            dst.write(dem.astype(np.float32), 1)
        
        logger.info(f"DEM数据已创建: {output_path}")
        return output_path
    
    def create_ndvi(self):
        """创建植被指数（NDVI）"""
        logger.info("创建植被指数数据")
        
        # 创建变换
        transform = Affine.translation(self.xmin, self.ymax) * \
                   Affine.scale((self.xmax - self.xmin) / self.width,
                               -(self.ymax - self.ymin) / self.height)
        
        # 创建NDVI数据（-1到1之间）
        # 模拟植被分布：中心区域植被较好，边缘较差
        center_x = self.width // 2
        center_y = self.height // 2
        
        ndvi = np.zeros((self.height, self.width))
        
        for i in range(self.height):
            for j in range(self.width):
                # 计算到中心的距离
                distance = np.sqrt((i - center_y)**2 + (j - center_x)**2)
                max_distance = np.sqrt(center_x**2 + center_y**2)
                
                # 距离越近，NDVI越高
                base_ndvi = 0.8 - 0.6 * (distance / max_distance)
                
                # 添加随机变化
                ndvi[i, j] = base_ndvi + 0.2 * np.random.randn()
        
        # 限制在-1到1之间
        ndvi = np.clip(ndvi, -1, 1)
        
        # 保存GeoTIFF
        output_path = self.output_dir / 'ndvi.tif'
        
        with rasterio.open(
            output_path, 'w',
            driver='GTiff',
            height=self.height,
            width=self.width,
            count=1,
            dtype=np.float32,
            crs=self.crs_wgs84,
            transform=transform,
            nodata=-9999
        ) as dst:
            dst.write(ndvi.astype(np.float32), 1)
        
        logger.info(f"NDVI数据已创建: {output_path}")
        return output_path
    
    def create_landuse(self):
        """创建土地利用数据"""
        logger.info("创建土地利用数据")
        
        # 创建变换
        transform = Affine.translation(self.xmin, self.ymax) * \
                   Affine.scale((self.xmax - self.xmin) / self.width,
                               -(self.ymax - self.ymin) / self.height)
        
        # 土地利用分类代码
        # 1: 森林, 2: 草地, 3: 农田, 4: 水域, 5: 建设用地, 6: 裸地
        
        landuse = np.zeros((self.height, self.width), dtype=np.uint8)
        
        # 随机分配土地利用类型（但有一定规律）
        for i in range(self.height):
            for j in range(self.width):
                # 根据位置决定土地利用
                if i < self.height * 0.3:  # 北部区域
                    landuse[i, j] = 1 if random.random() > 0.3 else 2  # 森林或草地
                elif i < self.height * 0.6:  # 中部区域
                    landuse[i, j] = 3 if random.random() > 0.5 else 2  # 农田或草地
                else:  # 南部区域
                    landuse[i, j] = 1 if random.random() > 0.4 else 6  # 森林或裸地
                
                # 添加一些水域
                if random.random() < 0.05:
                    landuse[i, j] = 4
                
                # 添加一些建设用地（主要在边缘）
                if (i < 20 or i > self.height - 20 or 
                    j < 20 or j > self.width - 20) and random.random() < 0.1:
                    landuse[i, j] = 5
        
        # 保存GeoTIFF
        output_path = self.output_dir / 'landuse.tif'
        
        with rasterio.open(
            output_path, 'w',
            driver='GTiff',
            height=self.height,
            width=self.width,
            count=1,
            dtype=np.uint8,
            crs=self.crs_wgs84,
            transform=transform,
            nodata=0
        ) as dst:
            dst.write(landuse, 1)
        
        logger.info(f"土地利用数据已创建: {output_path}")
        return output_path
    
    def create_all_sample_data(self):
        """创建所有示例数据"""
        logger.info("=" * 50)
        logger.info("开始创建示例数据")
        logger.info("=" * 50)
        
        # 创建所有数据文件
        self.create_boundary()
        self.create_species_points(50)
        self.create_roads()
        self.create_villages()
        self.create_rivers()
        self.create_dem()
        self.create_ndvi()
        self.create_landuse()
        
        # 创建配置文件
        self.create_sample_config()
        
        logger.info("=" * 50)
        logger.info("示例数据创建完成")
        logger.info(f"所有文件保存在: {self.output_dir}")
        logger.info("=" * 50)
    
    def create_sample_config(self):
        """创建示例配置文件"""
        config_content = f"""# 白冠长尾雉生境评估系统 - 示例配置

input:
  # 物种数据
  species_csv: "{(self.output_dir / 'species_occurrence.csv').as_posix()}"
  
  # 矢量数据
  boundary_shp: "{(self.output_dir / 'reserve_boundary.shp').as_posix()}"
  roads_shp: "{(self.output_dir / 'roads.shp').as_posix()}"
  villages_shp: "{(self.output_dir / 'villages.shp').as_posix()}"
  rivers_shp: "{(self.output_dir / 'rivers.shp').as_posix()}"
  
  # 栅格数据
  dem_tif: "{(self.output_dir / 'dem.tif').as_posix()}"
  ndvi_tif: "{(self.output_dir / 'ndvi.tif').as_posix()}"
  landuse_tif: "{(self.output_dir / 'landuse.tif').as_posix()}"

# 其他配置保持不变...
processing:
  target_crs: "EPSG:4547"
  target_resolution: 30
  buffer_distance: 5000
  resample_method: "bilinear"
# ... 其余配置使用默认值
"""
        
        # 保存配置文件
        config_path = self.output_dir / 'sample_config.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        logger.info(f"示例配置文件已创建: {config_path}")

def main():
    """主函数"""
    # 创建示例数据
    creator = SampleDataCreator('./sample_data')
    creator.create_all_sample_data()
    
    print("\n🎉 示例数据创建完成！")
    print("\n使用方法:")
    print("1. 复制 sample_config.yaml 为 config.yaml")
    print("2. 运行: python main.py --full")
    print("\n或直接测试:")
    print(f"python main.py --full --config {creator.output_dir / 'sample_config.yaml'}")

if __name__ == "__main__":
    main()