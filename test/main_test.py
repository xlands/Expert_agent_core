#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests
import time
import os
import random

# API基础URL
BASE_URL = "http://localhost:8001"

# 定义测试查询列表
TEST_QUERIES = [
    "针对社媒上发现的前10条最火推广视频，分别分析它们的视频结构、文案设计、开头吸引点及结尾引导策略。",
    # "为了推广即将发布的汽车新品，我们需要一些独特的创意点子。请分析市场上类似产品的成功案例，并结合我们的产品特点提出创新性的内容建议。"
    # "我们需要对这条关于汽车的介绍进行优化，以便通过我们的品牌账号发布到小红书和抖音。请根据我们账号的历史高赞内容分析报告1来调整文案风格，使其更符合我们品牌的调性。"
]

# 测试结果保存目录
TEST_OUTPUT_DIR = "test/output"
USER_QUERY_RESULT_FILE = os.path.join(TEST_OUTPUT_DIR, "user_query_result.json")
DATA_PROCESSING_RESULT_FILE = os.path.join(TEST_OUTPUT_DIR, "data_processing_result.json")
SERVER_QUERY_RESULT_FILE = os.path.join(TEST_OUTPUT_DIR, "server_query_result.json")

# 确保输出目录存在
os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)

def save_to_file(data, file_path):
    """保存数据到文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_from_file(file_path, default=None):
    """从文件加载数据"""
    if not os.path.exists(file_path):
        return default
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def step1_user_query(session, conversation_id, qa_id, user_id):
    """步骤1: 发送用户查询 (query_type = user)"""
    
    # 随机选择一个查询
    query = TEST_QUERIES[0]  # 直接使用第一个查询
    
    url = f"{BASE_URL}/v1/streaming/query"
    payload = {
        "query_type": "user",
        "qa_id": str(qa_id),
        "user_id": str(user_id),
        "conversation_id": str(conversation_id),
        "content": {
            "messages": [
                {"role": "user", "content": query}
            ]
        }
    }
    
    response = session.post(url, json=payload, stream=True)
    
    if response.status_code != 200:
        raise Exception(f"用户查询请求失败: {response.text}")
    
    received_crawl_task = False
    crawl_task_content = None
    all_responses = []
    
    # 接收并处理流式响应
    for line in response.iter_lines():
        if line:
            data = json.loads(line.decode('utf-8'))
            all_responses.append(data)  # 保存所有响应
            task_type = data.get('task_type')
            
            if task_type == 'crawl_task':
                received_crawl_task = True
                crawl_task_content = data.get('content')
            
    return all_responses  # 返回所有响应

def step2_data_processing(session):
    """步骤2: 数据处理接口测试"""
    
    # 修改为使用正确路径的server_data.json
    data_path = "data/test_server_data/server_data.json"
    
    # 读取JSON文件
    with open(data_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    # 确保test_data是列表
    if not isinstance(test_data, list):
        raise Exception("测试数据必须是列表类型")
    
    url = f"{BASE_URL}/v1/data/processing"
    payload = {
        "raw_data": test_data
    }
    
    response = session.post(url, json=payload)
    
    if response.status_code != 200:
        raise Exception(f"数据处理请求失败: {response.text}")
    
    response_data = response.json()
    
    # 验证响应结构
    if 'content' not in response_data:
        raise Exception("数据处理响应缺少'content'字段")
    
    processed_data = response_data['content']
    
    # 保存结果到文件 - 确保结果被正确保存
    save_to_file(processed_data, DATA_PROCESSING_RESULT_FILE)
    
    return processed_data

def step3_server_query(session, conversation_id, qa_id, user_id, processed_data):
    """步骤3: 服务器查询 (query_type = server)"""
    
    if not processed_data:
        error_msg = "没有处理过的数据，无法执行服务器查询"
        raise Exception(error_msg)
    
    url = f"{BASE_URL}/v1/streaming/query"
    payload = {
        "query_type": "server",
        "qa_id": str(qa_id),
        "user_id": str(user_id),
        "conversation_id": str(conversation_id),
        "content": {
            "collected_data": processed_data
        }
    }
    
    response = session.post(url, json=payload, stream=True)
    
    if response.status_code != 200:
        raise Exception(f"服务器查询请求失败: {response.text}")
    
    # 跟踪任务状态
    received_stream = False
    received_report = False
    received_done = False
    final_report_path = None
    stream_count = 0
    report_count = 0
    error_count = 0
    
    # 保存所有错误消息以便后续分析
    all_errors = []
    
    # 接收并处理流式响应
    for line in response.iter_lines():
        if line:
            data = json.loads(line.decode('utf-8'))
            task_type = data.get('task_type')
            content = data.get('content', {})
            
            if task_type == 'stream':
                stream_count += 1
                received_stream = True
            
            elif task_type == 'report':
                report_count += 1
                received_report = True
            
            elif task_type == 'done':
                received_done = True
                if isinstance(content, dict):
                    final_report_path = content.get('final_report_path')
            
            elif task_type == 'error':
                error_count += 1
                all_errors.append({
                    "error_count": error_count,
                    "content": content,
                    "timestamp": time.time()
                })
    
    # 保存所有错误信息到文件，以便后续分析
    if all_errors:
        error_file = os.path.join(TEST_OUTPUT_DIR, "server_query_errors.json")
        save_to_file(all_errors, error_file)
    
    if not received_stream and not received_done:
        raise Exception("服务器查询未返回必要的响应")
    
    return final_report_path

def test_user_query():
    """测试1: 用户查询"""
    
    session = requests.Session()
    conversation_id = int(time.time())
    qa_id = random.randint(10000, 99999)
    user_id = random.randint(10000, 99999)
    
    # 保存会话信息供后续测试使用
    session_info = {
        "conversation_id": conversation_id,
        "qa_id": qa_id,
        "user_id": user_id
    }
    save_to_file(session_info, os.path.join(TEST_OUTPUT_DIR, "session_info.json"))
    
    result = step1_user_query(session, conversation_id, qa_id, user_id)
    
    # 保存结果
    if result:
        save_to_file(result, USER_QUERY_RESULT_FILE)
    
    return result

def test_data_processing():
    """测试2: 数据处理接口"""
    
    session = requests.Session()
    result = step2_data_processing(session)
    
    # 保存结果
    if result:
        save_to_file(result, DATA_PROCESSING_RESULT_FILE)
    
    return result

def test_server_query():
    """测试3: 服务器查询"""
    
    # 加载会话信息
    session_info = load_from_file(os.path.join(TEST_OUTPUT_DIR, "session_info.json"), {})
    conversation_id = session_info.get("conversation_id", int(time.time()))
    qa_id = session_info.get("qa_id", random.randint(10000, 99999))
    user_id = session_info.get("user_id", random.randint(10000, 99999))
    
    # 加载上一步的处理结果
    processed_data = load_from_file(DATA_PROCESSING_RESULT_FILE, [])
    
    session = requests.Session()
    result = step3_server_query(session, conversation_id, qa_id, user_id, processed_data)
    
    # 保存结果
    result_data = {
        "final_report_path": result,
        "timestamp": time.time()
    }
    save_to_file(result_data, SERVER_QUERY_RESULT_FILE)
    
    return result

def run_complete_test_flow():
    """执行完整的测试流程"""
    
    # 创建会话以维持连接
    session = requests.Session()
    
    # 生成唯一会话ID
    conversation_id = int(time.time())
    qa_id = random.randint(10000, 99999)
    user_id = random.randint(10000, 99999)
    
    # 步骤1: 发送用户查询 (query_type = user)
    step1_user_query(session, conversation_id, qa_id, user_id)
    
    # # 步骤2: 数据处理接口测试
    # processed_data = step2_data_processing(session)
    test_process_data_path = "test/test_process_data.json"
    processed_data = load_from_file(test_process_data_path)
    
    # 步骤3: 服务器查询 (query_type = server) - 直接使用step2返回的处理结果
    report_path = step3_server_query(session, conversation_id, qa_id, user_id, processed_data)
    
    return report_path

def main():
    """主函数，选择要执行的测试"""
    
    # 确保输出目录存在
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    
    # 创建日志文件
    log_file = os.path.join(TEST_OUTPUT_DIR, f"test_log_{int(time.time())}.txt")
    
    # 执行完整的测试流程
    print("执行完整测试流程...")
    final_report_path = run_complete_test_flow()
    
    if final_report_path:
        print(f"测试成功完成，最终报告路径: {final_report_path}")
    else:
        print("测试完成，但未生成最终报告")
    
    return 0  # 返回成功码

if __name__ == "__main__":
    main()
