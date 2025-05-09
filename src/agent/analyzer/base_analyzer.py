import os
import json
from typing import Dict, List, Any
from src.llm import LLM
from src.utils.extract_markdown import extract_structured_data

class BaseAnalyzer:
    """分析器基类，提供通用功能和属性"""
    
    def __init__(self, output_dir: str = None):
        """
        初始化分析器基类
        
        Args:
            output_dir: 可选输出目录，用于保存分析结果
        """
        self.output_dir = output_dir
        self.llm = LLM(model="deepseek-v3")
    
    def generate_data_driven_insight(self, data: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """使用LLM根据分析数据生成洞察
        
        Args:
            data: 分析数据
            analysis_type: 分析类型，例如"sentiment", "keyword", "feature"等
            
        Returns:
            Dict[str, Any]: 生成的洞察
        """
        # 构建系统提示词
        system_prompt = """你是一个数据分析专家，请根据用户提供的数据生成洞察发现。
        
请遵循以下要求：
1. 基于数据找出最重要的、有价值的发现
2. 不要使用任何预设模板，完全从数据中发掘真实洞察
3. 确保洞察具体、直接并基于事实
4. 仅返回JSON格式数据，不要包含任何其他文本或解释
5. JSON结构必须包含content字段，该字段应包含基于数据的观察和分析

格式要求：
{
    "content": "这里是根据数据生成的洞察内容，应当直接反映数据事实"
}"""

        # 将数据转换为字符串
        data_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        # 构建用户消息
        user_message = f"""请根据以下数据生成洞察发现：

{data_str}

请直接返回JSON格式，包含content字段，内容应完全基于上述数据。"""

        # 构建消息列表
        messages = [{"role": "user", "content": user_message}]
        
        # 调用LLM生成洞察
        response = self.llm.generate(messages, system_prompt=system_prompt)
        
        # 使用extract_structured_data处理响应
        result = extract_structured_data(response, 'json')
        
        # 如果无法提取有效JSON或没有content字段，则提供默认结构
        if result is None:
            return {"content": "无法从数据中提取有意义的洞察。"}
        
        if "content" not in result:
            result = {"content": response}
            
        return result
    
    def save_result(self, result: Dict[str, Any], filename: str) -> None:
        """保存分析结果到文件
        
        Args:
            result: 分析结果
            filename: 文件名
        """
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            output_path = os.path.join(self.output_dir, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)