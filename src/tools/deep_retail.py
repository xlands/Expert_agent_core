import os
import json
from typing import Dict, List

class DeepRetail:
    """暂时用读文件模拟从社媒平台爬取数据"""
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = data_dir
        
    def fetch_data(self, keywords: Dict[str, List[str]]) -> List[Dict]:
        """根据关键词从本地文件夹读取爬虫结果

        Args:
            keywords: 各平台的关键词列表，格式为：
            {
                "xiaohongshu": ["关键词1", "关键词2", ...],
                "douyin": ["关键词1", "关键词2", ...]
            }

        Returns:
            List[Dict]: 爬取的数据列表
        """
        result = []
        
        # 遍历每个平台的关键词
        for platform, platform_keywords in keywords.items():
            # 构建文件名（假设文件名格式为：平台_关键词1_关键词2.csv）
            filename = f"{platform}_{'_'.join(platform_keywords)}.csv"
            filepath = os.path.join(self.data_dir, filename)
            
            # 检查文件是否存在
            if os.path.exists(filepath):
                # 读取CSV文件
                import pandas as pd
                df = pd.read_csv(filepath)
                # 将DataFrame转换为字典列表
                data = df.to_dict('records')
                result.extend(data)
            else:
                print(f"文件不存在: {filepath}")
        
        return result 