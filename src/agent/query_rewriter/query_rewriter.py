from typing import List, Dict, Any
import json
from src.llm import LLM
from src.prompt.tools import QUERY_REWRITE_SYSTEM_PROMPT, KEYWORD_GEN_SYSTEM_PROMPT

class QueryRewriter:
    """查询改写器，负责将用户简单查询转换为结构化的分析任务"""
    
    def __init__(self):
        self.llm = LLM()
        
    def query_rewrite(self, query: str) -> Dict[str, Any]:
        """将简单查询改写为结构化的背景、任务描述和关键词 (简化版)。"""
        messages = [
            {"role": "user", "content": f"现在，请帮我改写这个查询：\n{query}"}
        ]

        response = self.llm.generate(
            messages=messages,
            system_prompt=QUERY_REWRITE_SYSTEM_PROMPT, 
            model='deepseek-v3-online',
            json_output=True
        )

        background = response['background']
        task = response['task']
        keywords_result = self.generate_keywords(background, task)
        
        return {
            'background': background,
            'task': task,
            'keywords': keywords_result
        }

    def generate_keywords(self, background: str, task: str) -> Dict[str, Any]:
        """生成各平台的检索关键词 (简化版)。"""
        user_content = f"背景：{background}\n任务：{task}"
        messages = [
            {"role": "user", "content": user_content}
        ]

        response = self.llm.generate(
            messages=messages,
            system_prompt=KEYWORD_GEN_SYSTEM_PROMPT, # 使用导入的常量
            model='deepseek-v3-online',
            # model='deepseek-v3',
            json_output=True
        )
        
        _ = response['xiaohongshu'] 
        _ = response['douyin']
        return response
        
if __name__ == "__main__":
    query = '帮我做一下小米汽车的竞品分析'
    query_rewriter = QueryRewriter()
    result = query_rewriter.query_rewrite(query)
    print(f"背景: {result['background']}")
    print(f"任务: {result['task']}")
    print(f"小红书关键词: {result['keywords']['xiaohongshu']}")
    print(f"抖音关键词: {result['keywords']['douyin']}")