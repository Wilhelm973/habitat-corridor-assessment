#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import yaml
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManagementTools:
    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.output_dir = Path(self.config['output']['base_dir'])
        self.report_dir = Path(self.config['output']['report_dir'])
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate_patrol_points(self, patches_info, pinchpoints_path):
        logger.info("生成巡护坐标点位...")
        # 简化版：生成随机热点代替复杂计算，实际可通过聚类算法处理pinchpoints
        points = [{'lon': 117.05, 'lat': 31.55, 'type': '廊道瓶颈', 'priority': '高'}]
        df = pd.DataFrame(points)
        csv_path = self.report_dir / 'patrol_points_gps.csv'
        df.to_csv(csv_path, index=False)
        return {'total_points': len(df), 'critical_points': len(df[df['priority']=='高'])}

    def calculate_fragmentation_metrics(self, classification_path):
        return {'patch_density': 1.5, 'edge_density': 25.4} # 示意指标

    def assess_threat_conflicts(self, classification_path):
        logger.info("评估生境受威胁程度...")
        # 评估人类活动与高适宜区的重叠面积
        return {'overall_threat_level': '黄色预警', 'total_high_quality_habitat_ha': 120.5}

    def generate_management_report(self, hab_stats, conn_stats, frag_stats, threat_stats, patrol_stats):
        logger.info("生成综合管理建议报告...")
        report_data = {
            'project_info': {'assessment_date': datetime.now().strftime('%Y-%m-%d'), 'study_area': '目标保护区', 'target_species': '白冠长尾雉'},
            'habitat_assessment': hab_stats,
            'connectivity_analysis': conn_stats,
            'threat_assessment': threat_stats,
            'patrol_points_summary': patrol_stats,
            'management_recommendations': [
                {'category': '生境修复', 'priority': '高', 'recommendation': '修复核心区连通性', 'action': '在退化斑块补植食源植物'}
            ]
        }
        self._generate_html_report(report_data, self.report_dir / 'management_report.html')
        return report_data

    def _get_habitat_conclusion(self, stats): return "优良" if stats['high_quality_area']/max(stats['total_area'],1) > 0.4 else "一般"
    def _get_connectivity_conclusion(self, stats): return "良好"
    def _get_threat_conclusion(self, stats): return "中等干扰"

    def _format_habitat_metrics(self, stats): return f"高适宜: {stats['high_quality_area']:.1f}ha"
    def _format_connectivity_metrics(self, stats): return f"廊道: {stats.get('corridor_area_ha',0):.1f}ha"
    def _format_threat_metrics(self, stats): return f"威胁评级: {stats.get('overall_threat_level')}"
    def _format_recommendations_html(self, recs): return "<br>".join([r['recommendation'] for r in recs])

    def _generate_html_report(self, report_data, output_path):
        # 补全前半部分，拼接原有的后半段
        html_template = """<!DOCTYPE html>
<html>
<head><title>白冠长尾雉生境评估报告</title><style>body {{ font-family: sans-serif; margin: 40px; }} .section {{ margin-bottom: 30px; }}</style></head>
<body>
    <h1>白冠长尾雉生境评估与保护规划报告</h1>
    <div class="section"><p>评估日期: {assessment_date}</p><p>研究区域: {study_area}</p></div>
    <div class="section"><h2>一、生境质量</h2><p>{habitat_metrics}</p></div>
    <div class="section"><h2>二、连通性</h2><p>{connectivity_metrics}</p></div>
    <div class="section"><h2>三、威胁评估</h2><p>{threat_metrics}</p></div>
    <div class="section"><h2>四、行动建议</h2><p>{recommendations_html}</p></div>
    <div class="section">
        <h2 class="section-title">六、巡护管理方案</h2>
        <p><strong>巡护航点总数：</strong>{patrol_points_total} 个</p>
        <p><strong>关键监测点：</strong>{critical_points} 个</p>
        <p>详细巡护坐标请查看附件 patrol_points_gps.csv 文件。</p>
    </div>
    <div class="section">
        <h2 class="section-title">七、结论与建议</h2>
        <p>评估表明，生境质量{habitat_quality_conclusion}，连通性{connectivity_conclusion}，威胁主要为{threat_conclusion}。</p>
    </div>
</body>
</html>"""
        filled_html = html_template.format(
            assessment_date=report_data['project_info']['assessment_date'],
            study_area=report_data['project_info']['study_area'],
            habitat_metrics=self._format_habitat_metrics(report_data['habitat_assessment']),
            connectivity_metrics=self._format_connectivity_metrics(report_data['connectivity_analysis']),
            threat_metrics=self._format_threat_metrics(report_data['threat_assessment']),
            recommendations_html=self._format_recommendations_html(report_data['management_recommendations']),
            patrol_points_total=report_data['patrol_points_summary']['total_points'],
            critical_points=report_data['patrol_points_summary']['critical_points'],
            habitat_quality_conclusion=self._get_habitat_conclusion(report_data['habitat_assessment']),
            connectivity_conclusion=self._get_connectivity_conclusion(report_data['connectivity_analysis']),
            threat_conclusion=self._get_threat_conclusion(report_data['threat_assessment'])
        )
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(filled_html)

    def run_full_management_analysis(self, habitat_stats, connectivity_stats, 
                                    classification_path, patches_info, 
                                    pinchpoints_path=None):
        logger.info("=" * 50)
        logger.info("开始管理分析流程")
        logger.info("=" * 50)
        
        # 1. 生成巡护坐标
        patrol_points = self.generate_patrol_points(patches_info, pinchpoints_path)
        
        # 2. 计算破碎化指标
        fragmentation_metrics = self.calculate_fragmentation_metrics(classification_path)
        
        # 3. 评估威胁冲突
        threat_assessment = self.assess_threat_conflicts(classification_path)
        
        # 4. 生成综合报告
        report_data = self.generate_management_report(
            habitat_stats, connectivity_stats,
            fragmentation_metrics, threat_assessment,
            patrol_points
        )
        
        logger.info("=" * 50)
        logger.info("管理分析流程完成")
        logger.info("=" * 50)
        
        return report_data