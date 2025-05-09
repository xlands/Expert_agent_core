"""
提取 Markdown 中的结构化数据的工具函数

用于从 LLM 返回的可能包含 Markdown 格式的文本中提取结构化内容。
"""

import re
import json
from typing import Dict, Any, Optional, Union, Tuple

def extract_json_from_markdown(text: str) -> Optional[Dict[str, Any]]:
    """
    从可能包含 Markdown 格式的文本中提取 JSON 内容
    
    参数:
        text: 可能包含 Markdown 格式的文本
        
    返回:
        解析后的 JSON 对象，如果提取或解析失败则返回 None
    """
    # 尝试直接解析，可能本身就是 JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 ```json ... ``` 格式的内容
    json_pattern = r'```(?:json)?\s*([\s\S]*?)```'
    matches = re.findall(json_pattern, text)
    
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    
    # 尝试提取 { ... } 格式的内容（最外层的大括号对）
    brace_pattern = r'({[\s\S]*?})'
    matches = re.findall(brace_pattern, text)
    
    for match in matches:
        try:
            # 尝试解析可能的 JSON 对象
            result = json.loads(match.strip())
            # 确认结果是字典类型，而不是数组或原始值
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            continue
    
    return None

def extract_html_from_markdown(text: str) -> Optional[str]:
    """
    从可能包含 Markdown 格式的文本中提取 HTML 内容
    
    参数:
        text: 可能包含 Markdown 格式的文本
        
    返回:
        提取的 HTML 字符串，如果提取失败则返回 None
    """
    # 尝试提取 ```html ... ``` 格式的内容
    html_pattern = r'```(?:html)?\s*([\s\S]*?)```'
    matches = re.findall(html_pattern, text)
    
    if matches:
        return matches[0].strip()
    
    # 尝试提取 <html>...</html> 格式的内容
    html_root_pattern = r'(?:<html>[\s\S]*?</html>)'
    matches = re.findall(html_root_pattern, text, re.IGNORECASE)
    
    if matches:
        return matches[0].strip()
    
    # 尝试提取 <body>...</body> 格式的内容
    body_pattern = r'(?:<body>[\s\S]*?</body>)'
    matches = re.findall(body_pattern, text, re.IGNORECASE)
    
    if matches:
        return matches[0].strip()
    
    # 尝试提取包含多个 HTML 标签的内容
    has_html_tags = re.search(r'<[a-z][^>]*>[\s\S]*?</[a-z][^>]*>', text, re.IGNORECASE)
    if has_html_tags:
        return text.strip()
    
    return None

def extract_structured_data(text: str, data_type: str = 'json', original_data: Optional[Dict[str, Any]] = None) -> Union[Dict[str, Any], str, None]:
    """
    从文本中提取指定类型的结构化数据，并可选地合并原始数据
    
    参数:
        text: 可能包含结构化数据的文本
        data_type: 要提取的数据类型，可以是 'json' 或 'html'
        original_data: 原始数据字典，用于合并到提取的 JSON 数据中
        
    返回:
        如果 data_type 是 'json'，返回字典或None
        如果 data_type 是 'html'，返回字符串或None
    """
    if data_type.lower() == 'json':
        data = extract_json_from_markdown(text)
        
        # 如果提取成功，且有原始数据需要合并
        if data is not None and original_data is not None:
            # 合并原始数据，保留提取数据中的同名字段
            combined_data = {**original_data, **data}
            return combined_data
        
        return data
    
    elif data_type.lower() == 'html':
        return extract_html_from_markdown(text)
    
    else:
        # 不支持的数据类型
        return None

# 示例用法
if __name__ == "__main__":
    # JSON 提取示例
    markdown_json = '''
    # 分析结果
    
    以下是数据分析:
    
    ```json
    {
        "brand_mentions": {
            "小米": 5,
            "特斯拉": 3
        },
        "sentiment": "positive"
    }
    ```
    '''
    
    original_data = {
        "heat": 100,
    }
    
    data = extract_structured_data(markdown_json, 'json', original_data)
    print(f"JSON 提取结果: {data}")
    
    # HTML 提取示例
    markdown_html = '''
    # 可视化结果
    
    ```html
    <div style="color: blue;">
        <h1>品牌分析</h1>
        <p>这是一个示例 HTML</p>
    </div>
    ```
    '''
    
    data = extract_structured_data(markdown_html, 'html')
    print(f"\nHTML 提取结果: {data}") 