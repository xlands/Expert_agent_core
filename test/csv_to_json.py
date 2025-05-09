import csv
import json
import os

def csv_to_json(csv_file_paths, json_file_path, json_fields=None):
    """
    将多个CSV文件合并转换为一个JSON文件，支持处理某些字段是JSON dumps后的结构。
    
    :param csv_file_paths: 输入的CSV文件路径列表
    :param json_file_path: 输出的JSON文件路径
    :param json_fields: 需要解析为JSON的字段列表，默认为None
    """
    all_rows = []
    
    # 处理多个CSV文件
    for csv_file_path in csv_file_paths:
        # 读取CSV文件
        with open(csv_file_path, mode='r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            rows = list(csv_reader)
            
            # 处理JSON字段
            if json_fields:
                for row in rows:
                    for field in json_fields:
                        if field in row and row[field]:  # 确保字段存在且非空
                            try:
                                # 尝试将字段解析为JSON
                                row[field] = json.loads(row[field])
                            except json.JSONDecodeError:
                                # 如果解析失败，保持原样
                                print(f"Warning: Field '{field}' in file {csv_file_path} is not valid JSON. Keeping original value.")
                
            # 合并数据
            all_rows.extend(rows)
    
    # 将结果写入JSON文件
    with open(json_file_path, mode='w', encoding='utf-8') as json_file:
        json.dump(all_rows, json_file, indent=4, ensure_ascii=False)

    print(f"CSV files have been merged and converted to JSON file '{json_file_path}'.")

# 示例用法
if __name__ == "__main__":
    # 定义输入文件路径
    data_dir = "data/test_server_data"
    csv_file_paths = [
        os.path.join(data_dir, "30万mpv_xhs.csv"),
        os.path.join(data_dir, "30万mpv_dy.csv")
    ]
    
    # 定义输出文件路径
    json_file_path = os.path.join(data_dir, "30万mpv.json")
    
    # 定义需要解析为JSON的字段（如有需要）
    json_fields = []  # 根据实际CSV内容填写需要解析的JSON字段
    
    # 调用函数进行转换
    csv_to_json(csv_file_paths, json_file_path, json_fields)