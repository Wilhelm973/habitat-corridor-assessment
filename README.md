🌲 智能生境与生态廊道评估系统
本系统是一个端到端的自动化空间分析流水线，专为濒危野生动物的生境质量评估与生态廊道连通性分析而设计。系统融合了多源地理空间数据（遥感影像、DEM、矢量路网等），利用机器学习算法与电路理论，为国家公园与自然保护区的空间规划提供科学、直观的数据支撑。

✨ 核心功能与工作流
本系统实现了从原始数据读入到最终评估报告生成的全自动闭环：

1. 智能数据预处理 (Data Preprocessing)
自动处理由于数据源不同导致的坐标系冲突和分辨率差异。支持一键完成矢量裁剪、栅格重投影（如统一至 EPSG:4547）、重采样以及距离变量（距道路、距水系）的自动计算。

1. 生境适宜性建模 (Habitat Modeling)
基于随机森林 (Random Forest) 算法，结合输入的物种出现点 (Occurrence points) 与伪背景点，分析地形、植被指数 (NDVI)、土地利用类型等多维环境因子，全自动预测并输出研究区高精度的生境适宜度热力图。

1. 景观连通性分析 (Connectivity Analysis)
基于电路理论 (Circuit Theory) 与最小代价路径 (Least Cost Path)，智能识别核心生境斑块，并计算斑块间的电流密度。系统内置了“抓大放小”的噪点过滤机制，精准提取关键生态廊道与生态“夹点”（Pinchpoints）。

1. 管理指标评估与报告 (Management Reporting)
综合上述空间分析结果，自动生成包含生境面积统计、破碎化指数、人类干扰威胁预警的 HTML 评估报告，并可一键导出供一线巡护员使用的 GPS 关键监测点位表格。

🛠️ 技术栈
核心语言: Python 3.x

空间数据处理: GeoPandas, Rasterio, Shapely

机器学习建模: Scikit-learn

开源数据接入: OSMnx (OpenStreetMap 矢量自动抓取)

可视化出图: Matplotlib, Contextily (在线底图融合)

🚀 快速上手
1. 准备数据
将收集到的目标区域数据（DEM、NDVI、土地利用栅格，以及路网、物种点位等矢量/表格文件）放入 sample_data/ 目录。

2. 配置参数
在 config.yaml 中修改输入文件路径，并可灵活调整随机森林参数、廊道阻力阈值等核心指标。

3. 一键运行
在终端中执行以下命令，即可启动全流程评估：

Bash
python main.py --full --config sample_data/sample_config.yaml
4. 查看成果
运行结束后，所有处理好的标准化栅格、矢量图层、可视化渲染图以及 management_report.html 均会自动保存在 output/ 文件夹中。