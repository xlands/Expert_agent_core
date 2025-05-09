import unittest
import json
import requests
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 测试服务器地址
BASE_URL = "http://localhost:8001"  # 根据实际运行地址调整

class TestSummaryEndpoint(unittest.TestCase):
    """测试对话摘要接口"""

    def test_summary_endpoint(self):
        """测试摘要接口基本功能"""
        # 构造测试数据
        test_data = {
            "conversation_id": "test123",
            "messages": [
                {"role": "user", "content": "小米14和华为Mate60哪个好？"},
                {"role": "assistant", "content": "这取决于您的需求。小米14的性能更强，而华为Mate60的拍照更出色。"},
                {"role": "user", "content": "我更关心电池续航。"}
            ]
        }

        # 发送请求到已运行的服务
        response = requests.post(
            f"{BASE_URL}/v1/conversation/summary",
            json=test_data
        )

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('summary', data)
        self.assertEqual(data['conversation_id'], "test123")
        # 由于使用实际LLM，不验证具体摘要内容，只确保返回了摘要

    def test_summary_with_model_id(self):
        """测试指定模型ID的情况"""
        # 构造测试数据，包含model_id
        test_data = {
            "conversation_id": "test456",
            "model_id": "deepseek-v3",
            "messages": [
                {"role": "user", "content": "特斯拉Model 3的功能如何？"},
                {"role": "assistant", "content": "特斯拉Model 3是一款电动汽车，具有自动驾驶辅助等功能。"}
            ]
        }

        # 发送请求
        response = requests.post(
            f"{BASE_URL}/v1/conversation/summary",
            json=test_data
        )

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('summary', data)
        self.assertEqual(data['conversation_id'], "test456")

    def test_summary_missing_messages(self):
        """测试缺少必要参数的情况"""
        # 缺少messages字段
        test_data = {
            "conversation_id": "test789"
            # 故意不提供messages
        }

        # 发送请求
        response = requests.post(
            f"{BASE_URL}/v1/conversation/summary",
            json=test_data
        )

        # 验证错误响应
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'BAD_REQUEST_400')

if __name__ == '__main__':
    unittest.main()
