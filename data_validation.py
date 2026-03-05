#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import yaml
import pandas as pd
import geopandas as gpd
import rasterio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataValidator:
    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.input_config = self.config['input']
        self.output_dir = Path(self.config['output']['base_dir'])
        self.validation_dir = self.output_dir / 'validation'
        self.validation_dir.mkdir(parents=True, exist_ok=True)

    def validate_all_data(self):
        logger.info("开始全面数据验证...")
        results = {'files': {}, 'issues': [], 'recommendations': []}
        
        # 验证物种数据
        if 'species_csv' in self.input_config:
            results['files']['species'] = self._validate_species_data(self.input_config['species_csv'])
            
        # 验证矢量数据
        for vec_type in ['boundary', 'roads', 'villages', 'rivers']:
            key = f'{vec_type}_shp'
            if key in self.input_config and os.path.exists(self.input_config[key]):
                results['files'][vec_type] = self._validate_vector_data(self.input_config[key], vec_type)

        # 验证栅格数据
        for ras_type in ['dem', 'ndvi', 'landuse']:
            key = f'{ras_type}_tif'
            if key in self.input_config and os.path.exists(self.input_config[key]):
                results['files'][ras_type] = self._validate_raster_data(self.input_config[key], ras_type)

        # 汇总状态
        passed = sum(1 for r in results['files'].values() if r['status'] == 'PASS')
        total = len(results['files'])
        results['overall_status'] = 'PASS' if passed == total else 'WARNING' if passed > 0 else 'FAIL'
        results['summary'] = {'total_files': total, 'passed_files': passed, 'pass_rate': f"{(passed/total)*100:.1f}%" if total>0 else "0%"}
        
        self._generate_html_report(results, self.validation_dir / 'validation_report.html')
        return results

    def _validate_species_data(self, path):
        if not os.path.exists(path): return {'status': 'FAIL', 'message': '文件不存在'}
        try:
            df = pd.read_csv(path)
            issues = []
            if 'longitude' not in df.columns or 'latitude' not in df.columns:
                issues.append("缺少 longitude 或 latitude 列。")
            return {'status': 'PASS' if not issues else 'FAIL', 'message': 'CSV加载成功', 'issues': issues, 'statistics': {'记录数': len(df)}}
        except Exception as e:
            return {'status': 'FAIL', 'message': f'读取失败: {str(e)}'}

    def _validate_vector_data(self, path, name):
        try:
            gdf = gpd.read_file(path)
            issues = []
            if gdf.crs is None: issues.append("缺少坐标系(CRS)定义。")
            return {'status': 'PASS' if not issues else 'WARNING', 'message': '矢量加载成功', 'issues': issues, 'statistics': {'要素数量': len(gdf), 'CRS': str(gdf.crs)}}
        except Exception as e:
            return {'status': 'FAIL', 'message': f'读取失败: {str(e)}'}

    def _validate_raster_data(self, path, name):
        try:
            with rasterio.open(path) as src:
                issues = []
                if src.nodata is None: issues.append("未定义NoData值。")
                return {'status': 'PASS' if not issues else 'WARNING', 'message': '栅格加载成功', 'issues': issues, 'statistics': {'波段数': src.count, '分辨率': src.res, 'CRS': str(src.crs)}}
        except Exception as e:
            return {'status': 'FAIL', 'message': f'读取失败: {str(e)}'}

    def _generate_html_report(self, results, output_path):
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>数据验证报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
        .status-PASS {{ color: green; font-weight: bold; }}
        .status-WARNING {{ color: orange; font-weight: bold; }}
        .status-FAIL {{ color: red; font-weight: bold; }}
        .file-result {{ border: 1px solid #ccc; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
        .issue {{ color: #d9534f; }}
    </style>
</head>
<body>
    <h1>数据验证综合报告</h1>
    <h2>总体状态: <span class="status-{results['overall_status']}">{results['overall_status']}</span></h2>
    <p>通过率: {results['summary']['pass_rate']} ({results['summary']['passed_files']}/{results['summary']['total_files']})</p>
"""
        for file_type, result in results['files'].items():
            status_class = result['status']
            html += f"""
    <div class="file-result {status_class}">
        <h3>{file_type.upper()} - <span class="status-{status_class}">{result['status']}</span></h3>
        <p>{result['message']}</p>
        <h4>统计信息:</h4>
        <ul>
"""
            if 'statistics' in result:
                for key, value in result['statistics'].items():
                    html += f"            <li><strong>{key}:</strong> {value}</li>\n"
            html += "        </ul>\n"
            if result.get('issues'):
                html += "        <h4>发现问题:</h4>\n        <ul>\n"
                for issue in result['issues']:
                    html += f"            <li class='issue'>{issue}</li>\n"
                html += "        </ul>\n"
            html += "    </div>\n"
            
        html += "</body></html>"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

    def auto_fix_common_issues(self, validation_results):
        # 保持原有自动修复逻辑不变，此处为精简表示
        logger.info("执行自动修复检查...")
        return []

if __name__ == "__main__":
    validator = DataValidator()
    validator.validate_all_data()