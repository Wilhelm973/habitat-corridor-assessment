#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
import joblib
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText
import yaml
import logging
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText
import matplotlib as mpl

# --- 新增：强制配置 matplotlib 支持中文显示 ---
mpl.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'FangSong', 'Arial Unicode MS']
mpl.rcParams['axes.unicode_minus'] = False
# ---------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HabitatModeler:
    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.output_dir = Path(self.config['output']['base_dir'])
        self.raster_dir = Path(self.config['output']['raster_dir'])
        self.figures_dir = Path(self.config['output']['figures_dir'])
        for d in [self.raster_dir, self.figures_dir]:
            d.mkdir(parents=True, exist_ok=True)
        self.model_config = self.config['habitat_model']

    def extract_environmental_values(self, species_gdf, env_files):
        logger.info("提取出现点的环境变量...")
        coords = [(geom.x, geom.y) for geom in species_gdf.geometry]
        data = {'presence': 1}
        
        for var_name, raster_path in env_files.items():
            if var_name in self.model_config['predictors']:
                with rasterio.open(raster_path) as src:
                    values = [val[0] for val in src.sample(coords)]
                    data[var_name] = values
        return pd.DataFrame(data).replace([np.inf, -np.inf], np.nan).dropna()

    def generate_absence_points(self, env_df, boundary_gdf, n_samples):
        logger.info("生成伪背景点(Absence)...")
        # 简化版：随机生成属性数据作为背景
        # 实际应用中需要基于研究区栅格随机采样
        absence_data = env_df.copy()
        for col in absence_data.columns:
            if col != 'presence':
                np.random.shuffle(absence_data[col].values)
        absence_data['presence'] = 0
        return absence_data.sample(n=min(n_samples, len(absence_data)))

    def prepare_training_data(self, env_df, absence_df):
        df = pd.concat([env_df, absence_df])
        feature_cols = [c for c in df.columns if c != 'presence']
        X = df[feature_cols]
        y = df['presence']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        return X_train, X_test, y_train, y_test, feature_cols, None

    def train_random_forest(self, X_train, y_train, feature_cols):
        logger.info("训练随机森林模型...")
        params = self.model_config['random_forest']
        rf = RandomForestClassifier(
            n_estimators=params['n_estimators'],
            max_depth=params['max_depth'],
            random_state=42
        )
        rf.fit(X_train, y_train)
        importance = dict(zip(feature_cols, rf.feature_importances_))
        return rf, importance

    def evaluate_model(self, model, X_test, y_test):
        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1]
        perf = {
            'accuracy': float(accuracy_score(y_test, preds)),
            'auc': float(roc_auc_score(y_test, probs))
        }
        logger.info(f"模型评估 - 准确率: {perf['accuracy']:.3f}, AUC: {perf['auc']:.3f}")
        return perf

    def predict_habitat_suitability(self, model, scaler, feature_cols, env_files):
        logger.info("预测全区生境适宜性...")
        # 读取参考栅格属性
        ref_path = env_files[feature_cols[0]]
        with rasterio.open(ref_path) as src:
            meta = src.meta.copy()
            shape = src.shape
        
        # 堆叠特征
        stack = np.zeros((len(feature_cols), shape[0], shape[1]))
        for i, col in enumerate(feature_cols):
            with rasterio.open(env_files[col]) as src:
                # 添加 out_shape=shape 参数，强制所有图层对齐到参考图层的尺寸
                stack[i] = src.read(1, out_shape=shape)
        
        # 展平并预测
        pixels = stack.reshape(len(feature_cols), -1).T
        # 处理 NaN 和 Inf 
        valid_idx = np.isfinite(pixels).all(axis=1)
        suitability_flat = np.full(pixels.shape[0], np.nan)
        
        if valid_idx.sum() > 0:
            probs = model.predict_proba(pixels[valid_idx])[:, 1]
            suitability_flat[valid_idx] = probs
            
        suitability = suitability_flat.reshape(shape)
        
        # 保存适宜性图
        out_path = self.raster_dir / 'habitat_suitability.tif'
        meta.update(dtype=rasterio.float32, nodata=np.nan)
        with rasterio.open(out_path, 'w', **meta) as dst:
            dst.write(suitability.astype(rasterio.float32), 1)
        
        # 延续原有的可视化代码
        valid_values = suitability[~np.isnan(suitability)]
        mean_val = np.mean(valid_values)
        std_val = np.std(valid_values)
        max_val = np.max(valid_values)
        min_val = np.min(valid_values)
        
        plt.figure(figsize=(10, 8))
        im = plt.imshow(suitability, cmap='viridis')
        plt.colorbar(im, label='Suitability (0-1)')
        stats_text = f"均值: {mean_val:.3f}\n标准差: {std_val:.3f}\n最大值: {max_val:.3f}"
        plt.gca().add_artist(AnchoredText(stats_text, loc='upper left', frameon=True))
        viz_path = self.figures_dir / 'habitat_suitability_map.png'
        plt.savefig(viz_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return out_path

    def classify_habitat_quality(self, suitability_path):
        # 保持原有逻辑
        thresholds = self.config['management']['habitat_classification']
        with rasterio.open(suitability_path) as src:
            suit = src.read(1)
            meta = src.meta.copy()
            
        cls_arr = np.zeros_like(suit, dtype=np.uint8)
        mask = ~np.isnan(suit)
        cls_arr[mask & (suit < thresholds['medium_quality'])] = 1
        cls_arr[mask & (suit >= thresholds['medium_quality']) & (suit < thresholds['high_quality'])] = 2
        cls_arr[mask & (suit >= thresholds['high_quality'])] = 3
        
        out_path = self.raster_dir / 'habitat_classification.tif'
        meta.update(dtype=rasterio.uint8, nodata=0)
        with rasterio.open(out_path, 'w', **meta) as dst:
            dst.write(cls_arr, 1)
            
        pixel_ha = abs(meta['transform'][0] * meta['transform'][4]) / 10000
        stats = {
            'low_quality_area': np.sum(cls_arr == 1) * pixel_ha,
            'medium_quality_area': np.sum(cls_arr == 2) * pixel_ha,
            'high_quality_area': np.sum(cls_arr == 3) * pixel_ha,
        }
        stats['total_area'] = sum(stats.values())
        return out_path, stats

    def run_full_modeling(self, prep_result):
        env_df = self.extract_environmental_values(prep_result['species_data'], prep_result['environmental_variables'])
        abs_df = self.generate_absence_points(env_df, prep_result['boundary'], len(env_df)*2)
        X_train, X_test, y_train, y_test, feats, scaler = self.prepare_training_data(env_df, abs_df)
        model, imp = self.train_random_forest(X_train, y_train, feats)
        perf = self.evaluate_model(model, X_test, y_test)
        suit_path = self.predict_habitat_suitability(model, scaler, feats, prep_result['environmental_variables'])
        cls_path, stats = self.classify_habitat_quality(suit_path)
        return {'suitability_raster': suit_path, 'classification_raster': cls_path, 'area_statistics': stats, 'model_performance': perf}