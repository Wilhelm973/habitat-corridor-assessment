import pandas as pd
import numpy as np
import random

def generate_dongzhai_points(n_points=50):
    # 董寨保护区大致经纬度范围
    lon_min, lon_max = 114.15, 114.32
    lat_min, lat_max = 31.85, 32.02
    
    data = []
    for _ in range(n_points):
        # 加上一点正态分布，模拟物种聚集效应
        lon = np.clip(random.gauss((lon_min+lon_max)/2, 0.04), lon_min, lon_max)
        lat = np.clip(random.gauss((lat_min+lat_max)/2, 0.04), lat_min, lat_max)
        
        data.append({
            'longitude': round(lon, 6),
            'latitude': round(lat, 6),
            'species': '白冠长尾雉'
        })
        
    df = pd.DataFrame(data)
    df.to_csv('dongzhai_species_occurrence.csv', index=False)
    print(f"成功生成 {n_points} 个董寨区域测试点位，已保存为 dongzhai_species_occurrence.csv")

if __name__ == "__main__":
    generate_dongzhai_points()