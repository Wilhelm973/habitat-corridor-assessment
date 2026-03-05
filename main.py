#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
白冠长尾雉生境评估系统 - 主控制程序
功能：集成所有模块，提供命令行界面和批处理支持
"""

import os
import sys
import yaml
import argparse
import logging
from pathlib import Path
import time
from datetime import datetime
from data_validation import DataValidator

# 添加模块路径
sys.path.append(str(Path(__file__).parent))

# 导入各功能模块
from data_preprocessing import DataPreprocessor
from habitat_modeling import HabitatModeler
from connectivity_analysis import ConnectivityAnalyzer
from management_tools import ManagementTools

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('habitat_assessment.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HabitatAssessmentSystem:
    """生境评估系统主类"""
    
    def __init__(self, config_path='config.yaml'):
        """初始化系统"""
        self.config_path = config_path
        
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 创建输出目录
        self.output_dir = Path(self.config['output']['base_dir'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化各模块
        self.preprocessor = None
        self.modeler = None
        self.analyzer = None
        self.manager = None
        
        # 结果存储
        self.results = {
            'preprocessing': None,
            'modeling': None,
            'connectivity': None,
            'management': None
        }
    
    def initialize_modules(self):
        """初始化所有模块"""
        logger.info("初始化系统模块...")
        
        self.preprocessor = DataPreprocessor(self.config_path)
        self.modeler = HabitatModeler(self.config_path)
        self.analyzer = ConnectivityAnalyzer(self.config_path)
        self.manager = ManagementTools(self.config_path)
        
        logger.info("系统模块初始化完成")
    
    def check_input_files(self):
        """检查输入文件是否存在"""
        logger.info("检查输入文件...")
        
        input_config = self.config['input']
        missing_files = []
        
        # 检查必要文件
        required_files = [
            ('species_csv', '物种出现点数据'),
            ('boundary_shp', '保护区边界'),
            ('dem_tif', '数字高程模型'),
            ('ndvi_tif', '植被指数'),
            ('landuse_tif', '土地利用')
        ]
        
        for file_key, description in required_files:
            if file_key in input_config:
                file_path = input_config[file_key]
                if not os.path.exists(file_path):
                    missing_files.append(f"{description}: {file_path}")
        
        if missing_files:
            logger.error("以下必要文件缺失:")
            for missing in missing_files:
                logger.error(f"  {missing}")
            return False
        
        # 检查可选文件
        optional_files = [
            ('roads_shp', '道路数据'),
            ('villages_shp', '村庄数据'),
            ('rivers_shp', '水系数据')
        ]
        
        for file_key, description in optional_files:
            if file_key in input_config:
                file_path = input_config[file_key]
                if not os.path.exists(file_path):
                    logger.warning(f"可选文件缺失 - {description}: {file_path}")
        
        logger.info("输入文件检查完成")
        return True
    
    def run_preprocessing(self):
        """运行数据预处理"""
        logger.info("=" * 60)
        logger.info("阶段1: 数据预处理")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        try:
            result = self.preprocessor.run_full_preprocessing()
            self.results['preprocessing'] = result
            
            if result:
                elapsed = time.time() - start_time
                logger.info(f"数据预处理完成，耗时: {elapsed:.1f}秒")
                return True
            else:
                logger.error("数据预处理失败")
                return False
                
        except Exception as e:
            logger.error(f"数据预处理出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def run_habitat_modeling(self):
        """运行生境建模"""
        logger.info("=" * 60)
        logger.info("阶段2: 生境适宜性建模")
        logger.info("=" * 60)
        
        if not self.results['preprocessing']:
            logger.error("请先运行数据预处理")
            return False
        
        start_time = time.time()
        
        try:
            result = self.modeler.run_full_modeling(self.results['preprocessing'])
            self.results['modeling'] = result
            
            if result:
                elapsed = time.time() - start_time
                logger.info(f"生境建模完成，耗时: {elapsed:.1f}秒")
                return True
            else:
                logger.error("生境建模失败")
                return False
                
        except Exception as e:
            logger.error(f"生境建模出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def run_connectivity_analysis(self):
        """运行连通性分析"""
        logger.info("=" * 60)
        logger.info("阶段3: 景观连通性分析")
        logger.info("=" * 60)
        
        if not self.results['modeling']:
            logger.error("请先运行生境建模")
            return False
        
        start_time = time.time()
        
        try:
            suitability_path = self.results['modeling']['suitability_raster']
            result = self.analyzer.run_full_connectivity_analysis(suitability_path)
            self.results['connectivity'] = result
            
            if result:
                elapsed = time.time() - start_time
                logger.info(f"连通性分析完成，耗时: {elapsed:.1f}秒")
                return True
            else:
                logger.error("连通性分析失败")
                return False
                
        except Exception as e:
            logger.error(f"连通性分析出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def run_management_analysis(self):
        """运行管理分析"""
        logger.info("=" * 60)
        logger.info("阶段4: 管理指标分析")
        logger.info("=" * 60)
        
        if not self.results['modeling'] or not self.results['connectivity']:
            logger.error("请先运行前序分析")
            return False
        
        start_time = time.time()
        
        try:
            habitat_stats = self.results['modeling']['area_statistics']
            connectivity_stats = self.results['connectivity']['area_statistics']
            classification_path = self.results['modeling']['classification_raster']
            patches_info = self.results['connectivity']['patches_info']
            
            pinchpoints_path = None
            if 'pinchpoints' in self.results['connectivity']:
                pinchpoints_path = self.results['connectivity']['pinchpoints']
            
            result = self.manager.run_full_management_analysis(
                habitat_stats, connectivity_stats,
                classification_path, patches_info,
                pinchpoints_path
            )
            
            self.results['management'] = result
            
            if result:
                elapsed = time.time() - start_time
                logger.info(f"管理分析完成，耗时: {elapsed:.1f}秒")
                return True
            else:
                logger.error("管理分析失败")
                return False
                
        except Exception as e:
            logger.error(f"管理分析出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def run_full_pipeline(self):
        """运行完整分析流程"""
        logger.info("=" * 60)
        logger.info("开始白冠长尾雉生境评估完整流程")
        logger.info("=" * 60)
        
        total_start_time = time.time()
        
        # 1. 检查输入文件
        if not self.check_input_files():
            logger.error("输入文件检查失败，流程终止")
            return False
        
        # 2. 初始化模块
        self.initialize_modules()
        
        # 3. 运行各阶段分析
        stages = [
            ("数据预处理", self.run_preprocessing),
            ("生境建模", self.run_habitat_modeling),
            ("连通性分析", self.run_connectivity_analysis),
            ("管理分析", self.run_management_analysis)
        ]
        
        success_count = 0
        for stage_name, stage_func in stages:
            logger.info(f"\n开始执行: {stage_name}")
            
            if stage_func():
                success_count += 1
                logger.info(f"{stage_name} 成功完成")
            else:
                logger.error(f"{stage_name} 失败，流程终止")
                break
        
        # 4. 生成总结报告
        total_elapsed = time.time() - total_start_time
        
        if success_count == len(stages):
            logger.info("=" * 60)
            logger.info("🎉 所有分析阶段成功完成！")
            logger.info(f"总耗时: {total_elapsed:.1f}秒")
            logger.info("=" * 60)
            
            # 输出结果摘要
            self.print_summary()
            
            return True
        else:
            logger.error("=" * 60)
            logger.error(f"❌ 分析流程部分失败 ({success_count}/{len(stages)} 阶段成功)")
            logger.error(f"总耗时: {total_elapsed:.1f}秒")
            logger.error("=" * 60)
            
            return False
    
    def print_summary(self):
        """打印分析结果摘要"""
        logger.info("\n" + "=" * 60)
        logger.info("分析结果摘要")
        logger.info("=" * 60)
        
        # 生境质量结果
        if self.results['modeling']:
            habitat_stats = self.results['modeling']['area_statistics']
            logger.info("1. 生境质量评估:")
            logger.info(f"   高质量生境: {habitat_stats['high_quality_area']:.1f} 公顷")
            logger.info(f"   中等质量生境: {habitat_stats['medium_quality_area']:.1f} 公顷")
            logger.info(f"   低质量生境: {habitat_stats['low_quality_area']:.1f} 公顷")
            logger.info(f"   总面积: {habitat_stats['total_area']:.1f} 公顷")
        
        # 连通性结果
        if self.results['connectivity']:
            connectivity_stats = self.results['connectivity']['area_statistics']
            logger.info("\n2. 景观连通性分析:")
            logger.info(f"   生态廊道面积: {connectivity_stats.get('corridor_area_ha', 0):.1f} 公顷")
            logger.info(f"   瓶颈区域面积: {connectivity_stats.get('pinchpoint_area_ha', 0):.1f} 公顷")
        
        # 管理建议
        if self.results['management']:
            report_data = self.results['management']
            logger.info("\n3. 管理建议摘要:")
            for rec in report_data['management_recommendations'][:3]:  # 显示前3条建议
                logger.info(f"   {rec['category']}: {rec['recommendation']}")
        
        # 输出文件位置
        logger.info("\n4. 输出文件:")
        logger.info(f"   所有结果保存在: {self.output_dir}")
        logger.info(f"   综合报告: {self.output_dir / 'reports' / 'management_report.html'}")
        logger.info(f"   巡护坐标: {self.output_dir / 'reports' / 'patrol_points_gps.csv'}")
        
        logger.info("\n" + "=" * 60)
    
    def run_single_stage(self, stage_name):
        """运行单个分析阶段"""
        stage_map = {
            'preprocessing': ('数据预处理', self.run_preprocessing),
            'modeling': ('生境建模', self.run_habitat_modeling),
            'connectivity': ('连通性分析', self.run_connectivity_analysis),
            'management': ('管理分析', self.run_management_analysis)
        }
        
        if stage_name not in stage_map:
            logger.error(f"未知的分析阶段: {stage_name}")
            logger.error("可用阶段: preprocessing, modeling, connectivity, management")
            return False
        
        stage_display, stage_func = stage_map[stage_name]
        
        logger.info(f"运行单个阶段: {stage_display}")
        
        # 初始化模块
        self.initialize_modules()
        
        # 运行指定阶段
        return stage_func()
    
    def check_input_files(self):
        """全面增强版：调用 DataValidator 进行数据预检"""
        logger.info("启动智能数据验证机制...")
        validator = DataValidator(self.config_path)
        val_results = validator.validate_all_data()
        
        if val_results['overall_status'] == 'FAIL':
            logger.error("数据验证未通过，存在致命错误！详细问题请查看:")
            for issue in val_results.get('issues', []):
                logger.error(f"  - {issue}")
            logger.error(f"HTML报告路径: {validator.validation_dir / 'validation_report.html'}")
            return False
        elif val_results['overall_status'] == 'WARNING':
            logger.warning("数据验证存在警告，系统将尝试自动修复并继续...")
            validator.auto_fix_common_issues(val_results)
            return True
            
        logger.info("数据验证完美通过！")
        return True

def run_full_pipeline(self):
        """运行完整分析流程"""
        logger.info("=" * 60)
        logger.info("开始白冠长尾雉生境评估完整流程")
        logger.info("=" * 60)
        
        total_start_time = time.time()
        
        # 1. 强制前置执行验证模块 (增强版)
        if not self.check_input_files():
            logger.error("数据质量不达标，流程终止")
            return False
        
        # 2. 初始化模块
        self.initialize_modules()
        
        # 3. 运行各阶段分析
        stages = [
            ("数据预处理", self.run_preprocessing),
            ("生境建模", self.run_habitat_modeling),
            ("连通性分析", self.run_connectivity_analysis),
            ("管理分析", self.run_management_analysis)
        ]
        
        success_count = 0
        for stage_name, stage_func in stages:
            logger.info(f"\n开始执行: {stage_name}")
            
            if stage_func():
                success_count += 1
                logger.info(f"{stage_name} 成功完成")
            else:
                logger.error(f"{stage_name} 失败，流程终止")
                break
        
        # 4. 生成总结报告
        total_elapsed = time.time() - total_start_time
        
        if success_count == len(stages):
            logger.info("=" * 60)
            logger.info("🎉 所有分析阶段成功完成！")
            logger.info(f"总耗时: {total_elapsed:.1f}秒")
            logger.info("=" * 60)
            
            # 输出结果摘要
            self.print_summary()
            
            return True
        else:
            logger.error("=" * 60)
            logger.error(f"❌ 分析流程部分失败 ({success_count}/{len(stages)} 阶段成功)")
            logger.error(f"总耗时: {total_elapsed:.1f}秒")
            logger.error("=" * 60)
            
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='白冠长尾雉生境评估系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 运行完整流程
  python main.py --full
  
  # 运行单个阶段
  python main.py --stage preprocessing
  python main.py --stage modeling
  python main.py --stage connectivity
  python main.py --stage management
  
  # 使用自定义配置文件
  python main.py --full --config my_config.yaml
  
  # 查看帮助
  python main.py --help
        """
    )
    
    parser.add_argument('--full', action='store_true',
                       help='运行完整分析流程')
    parser.add_argument('--stage', type=str, choices=['preprocessing', 'modeling', 
                                                     'connectivity', 'management'],
                       help='运行单个分析阶段')
    parser.add_argument('--config', type=str, default='config.yaml',
                       help='配置文件路径 (默认: config.yaml)')
    parser.add_argument('--check', action='store_true',
                       help='仅检查输入文件，不运行分析')
    
    args = parser.parse_args()
    
    # 检查配置文件是否存在
    if not os.path.exists(args.config):
        logger.error(f"配置文件不存在: {args.config}")
        logger.info("请创建配置文件或使用 --config 指定正确的路径")
        return 1
    
    # 创建系统实例
    system = HabitatAssessmentSystem(args.config)
    
    # 根据参数执行相应操作
    if args.check:
        # 仅检查文件
        system.check_input_files()
        return 0
    
    elif args.full:
        # 运行完整流程
        success = system.run_full_pipeline()
        return 0 if success else 1
    
    elif args.stage:
        # 运行单个阶段
        success = system.run_single_stage(args.stage)
        return 0 if success else 1
    
    else:
        # 显示帮助
        parser.print_help()
        return 0

if __name__ == "__main__":
    # 记录开始时间
    start_time = datetime.now()
    logger.info(f"程序开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 运行主程序
    exit_code = main()
    
    # 记录结束时间
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"程序结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"总运行时间: {duration}")
    
    sys.exit(exit_code)