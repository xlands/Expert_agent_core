from typing import List, Dict, Optional
import sys
import os

# 将项目根目录添加到 sys.path
# 假设此文件位于 src/memory/summarizer.py
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.llm import LLM # 假设 LLM 类在 src/llm.py 中

def summarize_history(history: List[Dict[str, str]], llm: Optional[LLM] = None) -> str:
    """
    根据传入的对话 history 返回摘要。

    Args:
        history: 对话历史记录，格式为 [{"role": "user/assistant", "content": "..."}].
        llm: 可选的 LLM 实例。如果未提供，则会创建一个默认实例。

    Returns:
        对话历史的摘要文本。
    """
    if not llm:
        llm = LLM() # 使用默认模型初始化

    # 构建提示词
    prompt = "请根据以下对话历史记录，生成一个简洁的摘要，捕捉核心内容和关键信息：\n\n"
    for message in history:
        prompt += f"{message['role'].capitalize()}: {message['content']}\n"
    prompt += "\n摘要：" # 指示模型生成摘要

    # 调用 LLM 生成摘要
    # 注意：我们直接将构建好的完整 prompt 作为 user message 传递
    # 因为 generate 函数期望的是消息列表，而不是单个长字符串 prompt
    messages_for_llm = [
        {"role": "user", "content": prompt}
    ]

    # 根据 llm.py 的 generate 函数接口调整调用
    summary = llm.generate(
        messages=messages_for_llm,
        # 可以根据需要调整模型或其他参数
        # model="your_preferred_model_alias",
        # temperature=0.7,
        # ...
    )

    # generate 默认返回 content 字符串
    return summary

# 示例用法
if __name__ == "__main__":
    # 示例对话历史
    sample_history = [
        {"role": "user", "content": "你好，请问小米 SU7 这款车怎么样？"},
        {"role": "assistant", "content": "小米 SU7 是一款备受关注的电动轿车，它在设计、性能和智能化方面都有不错的表现。您对哪方面比较感兴趣？"},
        {"role": "user", "content": "我想了解一下它的智能驾驶功能。"}, 
        {"role": "assistant", "content": "小米 SU7 配备了 Xiaomi Pilot 智能驾驶系统，支持高速领航、城市领航（逐步开放）等功能，硬件配置包括激光雷达、高清摄像头等，旨在提供安全可靠的辅助驾驶体验。"}
    ]

    # 创建 LLM 实例 (可选，summarize_history 内部会创建)
    # llm_instance = LLM()

    # 生成摘要
    # summary_text = summarize_history(sample_history, llm=llm_instance)
    summary_text = summarize_history(sample_history)

    print("对话历史:")
    for msg in sample_history:
        print(f"- {msg['role'].capitalize()}: {msg['content']}")
    print("\n摘要:")
    print(summary_text)

    # 另一个例子
    another_history = [
        {"role": "user", "content": "我想预订一张明天从北京到上海的火车票。"},
        {"role": "assistant", "content": "好的，请问您希望什么时间出发？是否有座位等级偏好？"},
        {"role": "user", "content": "早上 9 点左右出发，二等座就可以。"},
        {"role": "assistant", "content": "正在为您查询... 早上 9:05 有一趟 G1 次列车，二等座有票，票价 553 元。您看可以吗？"},
        {"role": "user", "content": "可以，就订这张吧。"}
    ]
    another_summary = summarize_history(another_history)
    print("\n---\n对话历史:")
    for msg in another_history:
        print(f"- {msg['role'].capitalize()}: {msg['content']}")
    print("\n摘要:")
    print(another_summary) 