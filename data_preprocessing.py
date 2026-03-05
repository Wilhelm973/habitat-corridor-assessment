#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据预处理模块
功能：自动对齐不同来源的GIS数据，生成统一格式的环境变量图层
"""

import os
import yaml
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.enums import Resampling as RasterResampling
import fiona
from shapely.geometry import box, mapping
import warnings
warnings.filterwarnings('ignore')
from pathlib import Path
import logging
from tqdm import tqdm

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataPreprocessor:
    """数据预处理类，负责空间数据的对齐和标准化"""
    
    def __init__(self, config_path='config.yaml'):
        """初始化预处理器"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 创建输出目录
        self.output_dir = Path(self.config['output']['base_dir'])
        self.raster_dir = Path(self.config['output']['raster_dir'])
        self.vector_dir = Path(self.config['output']['vector_dir'])
        
        for dir_path in [self.output_dir, self.raster_dir, self.vector_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # 设置目标坐标系和分辨率
        self.target_crs = self.config['processing']['target_crs']
        self.target_res = self.config['processing']['target_resolution']
        
    def load_species_data(self, csv_path=None):
        """加载物种出现点数据"""
        if csv_path is None:
            csv_path = self.config['input']['species_csv']
        
        logger.info(f"加载物种数据: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # 检查必要的列
        required_cols = ['longitude', 'latitude', 'species']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"CSV文件必须包含'{col}'列")
        
        # 转换为GeoDataFrame
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df.longitude, df.latitude),
            crs='EPSG:4326'  # WGS84
        )
        
        # 投影到目标坐标系
        gdf = gdf.to_crs(self.target_crs)
        
        # 保存处理后的数据
        output_path = self.vector_dir / 'species_points.shp'
        gdf.to_file(output_path)
        logger.info(f"物种数据已保存至: {output_path}")
        
        return gdf
    
    def load_and_process_vector(self, shp_path, layer_name):
        """加载并处理矢量数据"""
        logger.info(f"加载矢量数据: {shp_path}")
        
        try:
            gdf = gpd.read_file(shp_path)
            
            # 如果数据没有CRS，假设为WGS84
            if gdf.crs is None:
                gdf.crs = 'EPSG:4326'
                logger.warning(f"{layer_name} 数据没有CRS，已假设为WGS84")
            
            # 投影到目标坐标系
            if gdf.crs != self.target_crs:
                gdf = gdf.to_crs(self.target_crs)
            
            # 保存处理后的数据
            output_path = self.vector_dir / f'{layer_name}.shp'
            gdf.to_file(output_path)
            
            logger.info(f"{layer_name} 数据已处理并保存")
            return gdf
            
        except Exception as e:
            logger.error(f"处理 {layer_name} 数据时出错: {e}")
            return None
    
    def load_and_process_raster(self, raster_path, layer_name):
        """加载并处理栅格数据"""
        logger.info(f"加载栅格数据: {raster_path}")
        
        try:
            with rasterio.open(raster_path) as src:
                # 获取原始信息
                src_crs = src.crs
                src_transform = src.transform
                src_width = src.width
                src_height = src.height
                src_bounds = src.bounds
                
                logger.info(f"原始数据信息 - CRS: {src_crs}, 分辨率: {src_transform[0]:.2f}m")
                
                # 如果CRS不同，需要重投影
                if src_crs != self.target_crs:
                    logger.info(f"重投影 {layer_name} 到 {self.target_crs}")
                    
                    # 计算目标变换
                    transform, width, height = calculate_default_transform(
                        src_crs, self.target_crs,
                        src_width, src_height,
                        *src_bounds
                    )
                    
                    # 创建目标数组
                    destination = np.zeros((src.count, height, width))
                    
                    # 重投影
                    reproject(
                        source=rasterio.band(src, 1),
                        destination=destination[0],
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=self.target_crs,
                        resampling=Resampling.bilinear
                    )
                    
                    # 更新元数据
                    src_transform = transform
                    src_width = width
                    src_height = height
                    src_bounds = rasterio.transform.array_bounds(
                        height, width, transform
                    )
                
                # 如果分辨率不同，需要重采样
                current_res = src_transform[0]
                if abs(current_res - self.target_res) > 0.1:
                    logger.info(f"重采样 {layer_name} 到 {self.target_res}m")
                    
                    # 计算新的尺寸
                    scale_factor = current_res / self.target_res
                    new_width = int(src_width * scale_factor)
                    new_height = int(src_height * scale_factor)
                    
                    # 计算新的变换
                    new_transform = rasterio.Affine(
                        self.target_res, src_transform[1],
                        src_transform[2], src_transform[3],
                        -self.target_res, src_transform[5]
                    )
                    
                    # 读取数据并重采样
                    data = src.read(1)
                    from scipy.ndimage import zoom
                    resampled_data = zoom(data, scale_factor, order=1)
                    
                    # 更新数据
                    data = resampled_data
                    src_transform = new_transform
                    src_width = new_width
                    src_height = new_height
                else:
                    data = src.read(1)
                
                # 保存处理后的栅格
                output_path = self.raster_dir / f'{layer_name}.tif'
                self._save_raster(
                    data, output_path, src_transform,
                    self.target_crs, src.nodata
                )
                
                logger.info(f"{layer_name} 栅格已处理并保存")
                return output_path
                
        except Exception as e:
            logger.error(f"处理 {layer_name} 栅格时出错: {e}")
            return None
    
    def _save_raster(self, data, output_path, transform, crs, nodata=None):
        """保存栅格数据"""
        with rasterio.open(
            output_path, 'w',
            driver='GTiff',
            height=data.shape[0],
            width=data.shape[1],
            count=1,
            dtype=data.dtype,
            crs=crs,
            transform=transform,
            nodata=nodata
        ) as dst:
            dst.write(data, 1)
    
    def calculate_distance_layers(self, boundary_gdf):
        """计算距离变量图层"""
        logger.info("开始计算距离变量图层")
        
        # 获取研究区域边界
        study_area = boundary_gdf.unary_union
        bounds = study_area.bounds
        
        # 创建基础栅格
        xmin, ymin, xmax, ymax = bounds
        width = int((xmax - xmin) / self.target_res)
        height = int((ymax - ymin) / self.target_res)
        
        transform = rasterio.Affine(
            self.target_res, 0, xmin,
            0, -self.target_res, ymax
        )
        
        # 加载矢量数据
        vectors = {}
        for layer in ['roads', 'villages', 'rivers']:
            shp_key = f'{layer}_shp'
            if shp_key in self.config['input']:
                shp_path = self.config['input'][shp_key]
                if os.path.exists(shp_path):
                    vectors[layer] = self.load_and_process_vector(shp_path, layer)
        
        # 计算距离栅格
        distance_layers = {}
        
        for layer_name, gdf in vectors.items():
            if gdf is not None:
                logger.info(f"计算距离{layer_name}图层")
                
                # 创建距离栅格
                distance_raster = np.full((height, width), np.inf, dtype=np.float32)
                
                # 计算每个像元到最近要素的距离
                for i in tqdm(range(height), desc=f"处理{layer_name}"):
                    for j in range(width):
                        # 计算像元中心坐标
                        x = xmin + (j + 0.5) * self.target_res
                        y = ymax - (i + 0.5) * self.target_res
                        
                        # 计算到所有要素的最小距离
                        point = gpd.points_from_xy([x], [y])[0]
                        distances = gdf.geometry.distance(point)
                        min_distance = distances.min()
                        
                        distance_raster[i, j] = min_distance
                
                # 保存距离图层
                output_path = self.raster_dir / f'distance_to_{layer_name}.tif'
                self._save_raster(
                    distance_raster, output_path,
                    transform, self.target_crs, np.inf
                )
                
                distance_layers[layer_name] = output_path
                logger.info(f"距离{layer_name}图层已保存: {output_path}")
        
        return distance_layers
    
    def calculate_terrain_features(self, dem_path):
        """从DEM计算地形特征（坡度、坡向）"""
        logger.info("开始计算地形特征")
        
        try:
            with rasterio.open(dem_path) as src:
                dem = src.read(1)
                transform = src.transform
                crs = src.crs
                
                # 计算坡度
                from scipy.ndimage import sobel
                dx = sobel(dem, axis=1) / (8 * transform[0])
                dy = sobel(dem, axis=0) / (8 * -transform[4])
                slope = np.arctan(np.sqrt(dx**2 + dy**2)) * 180 / np.pi
                
                # 计算坡向
                aspect = np.arctan2(dy, -dx) * 180 / np.pi
                aspect = (aspect + 360) % 360  # 转换为0-360度
                
                # 保存坡度图层
                slope_path = self.raster_dir / 'slope.tif'
                self._save_raster(slope, slope_path, transform, crs, src.nodata)
                
                # 保存坡向图层
                aspect_path = self.raster_dir / 'aspect.tif'
                self._save_raster(aspect, aspect_path, transform, crs, src.nodata)
                
                logger.info(f"地形特征已计算: {slope_path}, {aspect_path}")
                return slope_path, aspect_path
                
        except Exception as e:
            logger.error(f"计算地形特征时出错: {e}")
            return None, None
    
    def clip_to_study_area(self, boundary_gdf):
        """将所有栅格数据裁剪到研究区域"""
        logger.info("开始裁剪数据到研究区域")
        
        # 获取研究区域几何
        study_area = [mapping(boundary_gdf.unary_union)]
        
        # 处理所有栅格文件
        raster_files = list(self.raster_dir.glob('*.tif'))
        
        for raster_file in tqdm(raster_files, desc="裁剪栅格"):
            clipped_path = self.raster_dir / f'clipped_{raster_file.name}'
            try:
                # 1. 打开原文件，进行裁剪
                with rasterio.open(raster_file) as src:
                    out_image, out_transform = mask(
                        src, study_area, crop=True, all_touched=True
                    )
                    out_meta = src.meta.copy()
                    out_meta.update({
                        "height": out_image.shape[1],
                        "width": out_image.shape[2],
                        "transform": out_transform
                    })
                # 此时随着 with 块结束，原文件(src)已经自动关闭，释放了文件锁
                
                # 2. 写入裁剪后的新文件
                with rasterio.open(clipped_path, 'w', **out_meta) as dst:
                    dst.write(out_image)
                
                # 3. 删除原文件并重命名新文件 (放在 with 块外面，Windows 就不会报错了)
                raster_file.unlink()
                clipped_path.rename(raster_file)
                    
            except Exception as e:
                logger.warning(f"裁剪 {raster_file.name} 时出错: {e}")
        
        logger.info("数据裁剪完成")
    
    def create_environmental_stack(self):
        """创建环境变量堆栈"""
        logger.info("创建环境变量堆栈")
        
        # 收集所有环境变量文件
        env_files = {}
        
        # 基础环境变量
        base_layers = ['dem', 'ndvi', 'landuse', 'slope', 'aspect']
        for layer in base_layers:
            file_path = self.raster_dir / f'{layer}.tif'
            if file_path.exists():
                env_files[layer] = str(file_path)
        
        # 距离变量
        distance_layers = ['distance_to_roads', 'distance_to_villages', 'distance_to_rivers']
        for layer in distance_layers:
            file_path = self.raster_dir / f'{layer}.tif'
            if file_path.exists():
                env_files[layer] = str(file_path)
        
        # 保存环境变量列表
        env_list_path = self.output_dir / 'environmental_variables.txt'
        with open(env_list_path, 'w', encoding='utf-8') as f:
            for name, path in env_files.items():
                f.write(f"{name}: {path}\n")
        
        logger.info(f"环境变量堆栈已创建，共 {len(env_files)} 个变量")
        logger.info(f"变量列表已保存至: {env_list_path}")
        
        return env_files
    
    def run_full_preprocessing(self):
        """运行完整的数据预处理流程"""
        logger.info("=" * 50)
        logger.info("开始数据预处理流程")
        logger.info("=" * 50)
        
        # 1. 加载物种数据
        species_gdf = self.load_species_data()
        
        # 2. 加载保护区边界
        boundary_gdf = self.load_and_process_vector(
            self.config['input']['boundary_shp'],
            'reserve_boundary'
        )
        
        if boundary_gdf is None:
            logger.error("无法加载保护区边界数据，流程终止")
            return None
        
        # 3. 处理基础栅格数据
        raster_layers = ['dem', 'ndvi', 'landuse']
        for layer in raster_layers:
            tif_key = f'{layer}_tif'
            if tif_key in self.config['input']:
                self.load_and_process_raster(
                    self.config['input'][tif_key],
                    layer
                )
        
        # 4. 计算地形特征
        dem_path = self.raster_dir / 'dem.tif'
        if dem_path.exists():
            self.calculate_terrain_features(dem_path)
        
        # 5. 计算距离变量
        self.calculate_distance_layers(boundary_gdf)
        
        # 6. 裁剪到研究区域
        self.clip_to_study_area(boundary_gdf)
        
        # 7. 创建环境变量堆栈
        env_files = self.create_environmental_stack()
        
        logger.info("=" * 50)
        logger.info("数据预处理流程完成")
        logger.info("=" * 50)
        
        return {
            'species_data': species_gdf,
            'boundary': boundary_gdf,
            'environmental_variables': env_files
        }

def main():
    """主函数"""
    # 加载配置
    config_path = 'config.yaml'
    
    # 创建预处理器
    preprocessor = DataPreprocessor(config_path)
    
    # 运行完整流程
    result = preprocessor.run_full_preprocessing()
    
    if result:
        logger.info("预处理成功完成！")
        logger.info(f"物种点数: {len(result['species_data'])}")
        logger.info(f"环境变量数: {len(result['environmental_variables'])}")
    else:
        logger.error("预处理失败")

if __name__ == "__main__":
    main()