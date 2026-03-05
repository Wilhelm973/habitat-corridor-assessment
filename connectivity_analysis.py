#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import rasterio
from skimage.graph import MCP
import matplotlib.pyplot as plt
from scipy.ndimage import label, binary_erosion, binary_dilation
import yaml
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectivityAnalyzer:
    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.output_dir = Path(self.config['output']['base_dir'])
        self.raster_dir = Path(self.config['output']['raster_dir'])
        self.figures_dir = Path(self.config['output']['figures_dir'])
        self.connectivity_config = self.config['connectivity']

    def calculate_resistance_surface(self, suitability_path):
        logger.info("计算景观阻力面...")
        with rasterio.open(suitability_path) as src:
            suitability = src.read(1)
            meta = src.meta.copy()
            
        # 负指数转换：阻力 = exp(-c * 适宜度)
        c = abs(self.connectivity_config['exponential']['exponent'])
        resistance = np.exp(-c * suitability)
        resistance[np.isnan(suitability)] = np.nan
        
        # 这里可叠加道路等硬阻力(从配置中读取)
        
        res_path = self.raster_dir / 'resistance_surface.tif'
        with rasterio.open(res_path, 'w', **meta) as dst:
            dst.write(resistance.astype(rasterio.float32), 1)
        return res_path

    def identify_habitat_patches(self, suitability_path):
        logger.info("识别核心生境斑块...")
        thresh = self.connectivity_config['habitat_patch_threshold']
        with rasterio.open(suitability_path) as src:
            suit = src.read(1)
            meta = src.meta.copy()
            
        core = suit >= thresh
        labeled_patches, num_features = label(core)
        
        # --- 新增：过滤碎小噪点，只保留面积最大的前 20 个核心斑块 ---
        # 提取各个斑块的面积(像素数)
        unique_labels, counts = np.unique(labeled_patches, return_counts=True)
        
        # 将 label 和像素数 组合成字典，排除背景(0)
        patch_sizes = {lbl: count for lbl, count in zip(unique_labels, counts) if lbl > 0}
        
        # 过滤掉小于 10 个像素（约0.9公顷）的极小噪点
        valid_patches = {lbl: count for lbl, count in patch_sizes.items() if count >= 10}
        
        # 按面积降序排序，为了计算效率，最多只保留前 20 个最大的斑块
        sorted_patches = sorted(valid_patches.keys(), key=lambda k: valid_patches[k], reverse=True)[:20]
        
        # 重新映射标签，生成纯净的核心斑块图
        filtered_patches = np.zeros_like(labeled_patches)
        for new_label, old_label in enumerate(sorted_patches, start=1):
            filtered_patches[labeled_patches == old_label] = new_label
            
        num_features_filtered = len(sorted_patches)
        logger.info(f"原始噪点斑块数: {num_features}，过滤后保留的核心大斑块数: {num_features_filtered}")
        # -------------------------------------------------------------
        
        patch_path = self.raster_dir / 'core_patches.tif'
        meta.update(dtype=rasterio.int32, nodata=0)
        with rasterio.open(patch_path, 'w', **meta) as dst:
            dst.write(filtered_patches.astype(rasterio.int32), 1)
            
        return patch_path, patch_path, {'num_patches': num_features_filtered}

    def run_circuitscape_analysis(self, resistance_path, patches_raster_path):
        logger.info("运行连通性分析 (采用高效 MCP 最短路径回溯模拟电流)...")
        # 直接使用备用方案以避免外部依赖
        return self._run_circuitscape_fallback(resistance_path, patches_raster_path)

    def _run_circuitscape_fallback(self, resistance_path, patches_raster_path):
        with rasterio.open(resistance_path) as res_src:
            resistance = res_src.read(1)
            meta = res_src.meta.copy()
        with rasterio.open(patches_raster_path) as patch_src:
            patches = patch_src.read(1)

        # 屏蔽无效值
        cost_surface = np.nan_to_num(resistance, nan=9999)
        current_density = np.zeros_like(cost_surface, dtype=np.float32)
        
        # 获取所有斑块的中心点（或所有像元）作为起点/终点
        patch_ids = np.unique(patches)[1:] # 排除 0
        if len(patch_ids) < 2:
            logger.warning("核心斑块少于2个，无法计算连通性。")
            return None

        # 构建图论 MCP 对象
        mcp = MCP(cost_surface, fully_connected=True)
        
        logger.info(f"计算 {len(patch_ids)} 个斑块间的生态廊道网络...")
        for i in range(len(patch_ids) - 1):
            start_coords = np.argwhere(patches == patch_ids[i])
            start_pt = [tuple(start_coords[0])] # 简化：取斑块第一个像素作为源
            
            # 计算到其他所有斑块的代价
            cumulative_costs, traceback = mcp.find_costs(start_pt)
            
            for j in range(i + 1, len(patch_ids)):
                end_coords = np.argwhere(patches == patch_ids[j])
                end_pt = tuple(end_coords[0])
                
                try:
                    # 回溯最短路径
                    path = mcp.traceback(end_pt)
                    for pt in path:
                        # 路径经过的像元增加电流密度
                        current_density[pt] += 1.0
                except ValueError:
                    continue

        # 平滑/归一化电流密度图
        if current_density.max() > 0:
            current_density = current_density / current_density.max()
            
        current_path = self.raster_dir / 'current_density.tif'
        with rasterio.open(current_path, 'w', **meta) as dst:
            dst.write(current_density.astype(rasterio.float32), 1)
            
        return current_path

    def identify_corridors_and_pinchpoints(self, current_path):
        # 延续原有代码的图像形态学处理识别廊道
        with rasterio.open(current_path) as src:
            current = src.read(1)
        
        corridors = (current >= self.connectivity_config['corridor_threshold']).astype(np.uint8)
        eroded = binary_erosion(corridors, structure=np.ones((3, 3)))
        dilated = binary_dilation(eroded, structure=np.ones((5, 5)))
        pinchpoints = corridors & dilated
        
        # 简化返回
        return current_path, current_path, {'corridor_area_ha': np.sum(corridors)*0.09, 'pinchpoint_area_ha': np.sum(pinchpoints)*0.09}

    def run_full_connectivity_analysis(self, suitability_path):
        res_path = self.calculate_resistance_surface(suitability_path)
        patches_path, _, p_info = self.identify_habitat_patches(suitability_path)
        curr_path = self.run_circuitscape_analysis(res_path, patches_path)
        corr_path, pinch_path, stats = self.identify_corridors_and_pinchpoints(curr_path)
        return {'current_density': curr_path, 'ecological_corridors': corr_path, 'pinchpoints': pinch_path, 'area_statistics': stats, 'patches_info': p_info}