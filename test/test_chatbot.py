import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agent.chatbot import GreetingBot

def test_greeting_bot():
    """测试迎宾机器人的基本功能"""
    bot = GreetingBot()
    
    # # 测试普通对话
    # print("\n=== 测试普通对话 ===")
    # user_input = "你好，能介绍一下你可以做什么吗？"
    # messages = [{"role": "user", "content": user_input}]
    # print(f"用户: {user_input}")
    # print("机器人回复:")
    # for chunk in bot.chat(messages):
    #     print(chunk, end="", flush=True)
    # print("\n")
    
    # 测试带有明确品牌的查询
    print("\n=== 测试品牌分析查询 ===")
    user_input = "我想了解一下小米汽车的用户评价"
    messages = [{"role": "user", "content": user_input}]
    print(f"用户: {user_input}")
    print("机器人回复:")
    for chunk in bot.chat(messages):
        print(chunk, end="", flush=True)
    print("\n")
    
    # 测试竞品分析查询
    print("\n=== 测试竞品分析查询 ===")
    user_input = "帮我做一下特斯拉和小鹏的竞品分析"
    messages = [{"role": "user", "content": user_input}]
    print(f"用户: {user_input}")
    print("机器人回复:")
    for chunk in bot.chat(messages):
        print(chunk, end="", flush=True)
    print("\n")

if __name__ == "__main__":
    test_greeting_bot() 