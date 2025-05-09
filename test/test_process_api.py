import json
import os
import requests
import time

def test_process_api():
    """测试数据处理接口"""
    
    # 设置API端点
    api_url = "http://localhost:8001/v1/data/processing"
    
    # 加载测试数据
    test_data_file = "test/test_raw_data.json"
    with open(test_data_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    print(f"已加载 {len(raw_data)} 条记录")
    
    # 构建请求数据
    request_payload = {
        "raw_data": raw_data
    }
    
    # 发送HTTP请求
    print("正在发送请求到数据处理API...")
    start_time = time.time()
    response = requests.post(api_url, json=request_payload, timeout=5000)
    duration = time.time() - start_time
    print(f"请求完成，耗时: {duration:.2f}秒")
    
    # 处理响应
    result = response.json()
    processed_data = result["content"]
    print(f"成功处理 {len(processed_data)} 条数据")
    
    # 保存处理结果到文件
    output_file = "test/test_process_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)
    print(f"处理结果已保存到: {output_file}")

if __name__ == "__main__":
    test_process_api()
