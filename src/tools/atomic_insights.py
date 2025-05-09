import os
import csv
import json
import re
import sys
from tqdm import tqdm
import time
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
import math
import concurrent.futures
from functools import partial
import logging

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.llm import LLM
from src.utils.extract_markdown import extract_structured_data, extract_json_from_markdown

# 关闭httpx详细日志
logging.getLogger("httpx").setLevel(logging.WARNING)

def batch_analyze_brand_mentions(full_contents: List[str], llm: LLM, batch_size: int = 20) -> List[Dict]:
    """批量分析品牌提及频次"""
    brand_mentions_prompts = []
    for content in full_contents:
        prompt = f"""
        分析以下内容中提到的品牌及其频次:
        
        {content[:2000]}
        
        请输出JSON格式:
        {{
            "品牌名称1": 提及次数,
            "品牌名称2": 提及次数,
            ...
        }}
        
        只返回JSON格式，不要其他解释。
        """
        brand_mentions_prompts.append(prompt)

    # 转换为ChatML格式
    brand_mentions_messages = [[{"role": "user", "content": p}] for p in brand_mentions_prompts]

    # 批量处理
    brand_mentions_responses = []
    for i in tqdm(range(0, len(brand_mentions_messages), batch_size), desc="批量分析品牌提及"):
        batch_messages = brand_mentions_messages[i:i+batch_size]
        batch_results = llm.batch_generate(batch_messages)
        brand_mentions_responses.extend(batch_results)
    
    # 解析结果
    brand_mentions_list = []
    for response in brand_mentions_responses:
        result = extract_structured_data(response, 'json')
        brand_mentions_list.append(result)
    
    return brand_mentions_list

def batch_analyze_user_competition(full_contents: List[str], brand_mentions_list: List[Dict], llm: LLM, batch_size: int = 20) -> List[Dict]:
    """批量分析用户竞争情况"""
    competition_prompts = []
    
    for i, content in enumerate(full_contents):
        brand_context = ""
        if i < len(brand_mentions_list):
            top_brands = sorted(brand_mentions_list[i].items(), key=lambda x: x[1], reverse=True)[:5]
            if top_brands:
                brand_context = "在此内容中发现的主要品牌：" + ", ".join([f"{b}({c}次)" for b, c in top_brands]) + "\n\n"
        
        prompt = f"""
        {brand_context}分析以下内容中的用户竞争情况:
        
        {content[:2000]}
        
        请分析所有品牌之间的竞争关系，特别注意用户从一个品牌转向另一个品牌的迹象。
        
        请输出JSON格式:
        {{
            "brand_pairs": [
                {{
                    "type": "摇摆/流出",
                    "source_brand": "品牌A",
                    "target_brand": "品牌B",
                    "evidence": "用户原文证据（截取相关段落）"
                }}
            ],
            "reason": "整体分析"
        }}
        
        流出关系的判定：当用户对一个品牌持贬义态度并同时对另一个品牌持褒义态度时，判定为从贬义品牌流出到褒义品牌。
        只返回JSON格式，不要其他解释。
        """
        competition_prompts.append(prompt)

    # 转换为ChatML格式
    competition_messages = [[{"role": "user", "content": p}] for p in competition_prompts]

    # 批量处理
    competition_responses = []
    for i in tqdm(range(0, len(competition_messages), batch_size), desc="批量分析用户竞争情况"):
        batch_messages = competition_messages[i:i+batch_size]
        batch_results = llm.batch_generate(batch_messages)
        competition_responses.extend(batch_results)
    
    # 解析结果
    user_competitions = []
    for response in competition_responses:
        result = extract_structured_data(response, 'json')
        user_competitions.append(result)
    
    return user_competitions

def analyze_brands_for_content(content: str, brands: List[str], llm: LLM, batch_size: int = 5) -> Dict[str, Dict]:
    """为单条内容分析多个品牌，保持结果与品牌的映射关系"""
    if not brands:
        return {}
    
    # 为每个品牌生成分析提示
    prompts = []
    for brand in brands:
        prompt = f"""
        分析以下文本中关于"{brand}"品牌的评价:
        
        {content[:2000]}
        
        请输出JSON格式:
        {{
            "sentiment": "positive/neutral/negative",  // 总体情感倾向
            "features": {{  // 提到的产品特征及评价
                "特征1": "评价",
                "特征2": "评价"
            }},
            "strengths": [  // 优势列表
                {{"feature": "特性名称", "description": "详细描述"}},
            ],
            "weaknesses": [  // 劣势列表
                {{"feature": "特性名称", "description": "详细描述"}},
            ]
        }}
        
        只返回JSON格式，不要其他解释。
        """
        prompts.append(prompt)
    
    # 转换为ChatML格式
    messages = [[{"role": "user", "content": p}] for p in prompts]
    
    # 批量处理
    responses = []
    for i in range(0, len(messages), batch_size):
        batch_messages = messages[i:i+batch_size]
        batch_results = llm.batch_generate(batch_messages)
        responses.extend(batch_results)
    
    # 解析结果并映射到品牌
    brand_analysis = {}
    for brand, response in zip(brands, responses):
        result = extract_structured_data(response, 'json')
        brand_analysis[brand] = result
    
    return brand_analysis

def collect_all_fields(parsed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """收集所有数据项中的字段，生成字段全集及默认值"""
    all_fields = {}
    
    # 收集所有可能的字段
    for item in parsed_data:
        for key, value in item.items():
            if key not in all_fields:
                # 根据值类型设置合适的默认值
                if isinstance(value, str):
                    all_fields[key] = ""
                elif isinstance(value, list):
                    all_fields[key] = []
                elif isinstance(value, dict):
                    all_fields[key] = {}
                elif isinstance(value, int):
                    all_fields[key] = 0
                elif isinstance(value, float):
                    all_fields[key] = 0.0
                elif isinstance(value, bool):
                    all_fields[key] = False
                else:
                    all_fields[key] = None
    
    return all_fields

def normalize_data_fields(data_item: Dict[str, Any], all_fields: Dict[str, Any]) -> Dict[str, Any]:
    """标准化不同来源的数据字段，确保字段的一致性"""
    # 创建新的标准化字典，首先包含所有可能的字段和默认值
    normalized_item = dict(all_fields)
    
    # 用数据项中的实际值覆盖默认值
    for key, value in data_item.items():
        normalized_item[key] = value
    
    # 处理comments_data - 如果是字符串则转换为JSON对象
    if isinstance(normalized_item['comments_data'], str):
        # 对空字符串特殊处理，避免JSON解析错误
        if normalized_item['comments_data'] == "":
            normalized_item['comments_data'] = []
        else:
            normalized_item['comments_data'] = json.loads(normalized_item['comments_data'])
    
    # 处理author_data - 如果是字符串则转换为JSON对象
    if 'author_data' in normalized_item and isinstance(normalized_item['author_data'], str):
        # 对空字符串特殊处理，避免JSON解析错误
        if normalized_item['author_data'] == "":
            normalized_item['author_data'] = {}
        else:
            normalized_item['author_data'] = json.loads(normalized_item['author_data'])
    
    # 处理author_recent_content - 如果是字符串则转换为JSON对象
    if 'author_recent_content' in normalized_item and isinstance(normalized_item['author_recent_content'], str):
        # 对空字符串特殊处理，避免JSON解析错误
        if normalized_item['author_recent_content'] == "":
            normalized_item['author_recent_content'] = []
        else:
            normalized_item['author_recent_content'] = json.loads(normalized_item['author_recent_content'])
    
    return normalized_item

def atomic_insights(parsed_data: List[Dict[str, Any]], output_dir: str = None, model_id="doubao-lite") -> List[Dict]:
    """增强版内容分析函数，处理已解析的数据列表，使用并行处理提高效率"""
    start_time = time.time()
    print(f"开始处理 {len(parsed_data)} 条数据，使用模型: {model_id}")
    
    llm = LLM(model=model_id)

    if not parsed_data:
        return []
    
    # 1. 收集所有字段，生成字段全集
    all_fields = collect_all_fields(parsed_data)
    print(f"收集到 {len(all_fields)} 个不同字段")

    # 2. 并行标准化数据字段
    normalize_with_fields = partial(normalize_data_fields, all_fields=all_fields)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        normalized_data = list(executor.map(normalize_with_fields, parsed_data))
    print(f"数据标准化完成，处理了 {len(normalized_data)} 条记录")

    # 3. 构建内容
    full_contents = []
    for item in normalized_data:
        author_name = item['author_name'] 
        title = item['title']
        source = item['source'].lower()
        detail_desc = item['detail_desc']
        
        main_content = f"{author_name}：{title} {detail_desc}\n"
        
        comments_text = ""
        comments_data = item['comments_data']
        if comments_data:
            for comment in comments_data:
                if not isinstance(comment, dict):
                    continue
                comment_user = comment.get('comment_user_nick', "")
                comment_content = comment.get('comment_content', "")
                comment_location = comment.get('comment_location', "")
                comment_date = comment.get('comment_date', "")
                
                location_info = f"[{comment_location}]" if comment_location else ""
                date_info = f"({comment_date})" if comment_date else ""
                comments_text += f"{comment_user}{location_info}{date_info}：{comment_content}\n"
        
        full_content = main_content + comments_text
        full_contents.append(full_content)

    # 4. 分析品牌提及 (每条内容独立分析)
    brand_mentions_list = batch_analyze_brand_mentions(full_contents, llm, batch_size=20)
    print(f"品牌提及分析完成，总耗时: {time.time() - start_time:.2f}秒")
    
    # 5. 分析用户竞争情况 (每条内容独立分析)
    user_competitions = batch_analyze_user_competition(full_contents, brand_mentions_list, llm, batch_size=20)
    print(f"用户竞争分析完成，总耗时: {time.time() - start_time:.2f}秒")
    
    # 6. 每条内容单独分析品牌情感和特性
    all_brand_analysis = []
    
    for i, content in enumerate(tqdm(full_contents, desc="分析品牌情感和特性")):
        # 提取当前内容的主要品牌（最多5个）
        if i < len(brand_mentions_list) and brand_mentions_list[i]:
            main_brands = sorted(brand_mentions_list[i].items(), key=lambda x: x[1], reverse=True)[:5]
            top_brands = [brand for brand, _ in main_brands if brand]
            
            # 为当前内容分析所有主要品牌
            content_brand_analysis = analyze_brands_for_content(content, top_brands, llm)
        else:
            content_brand_analysis = {}
        
        all_brand_analysis.append(content_brand_analysis)
    
    print(f"品牌情感和特性分析完成，总耗时: {time.time() - start_time:.2f}秒")
    
    # 7. 整合所有结果
    processed_data = []
    
    for i, item in enumerate(normalized_data):
        # 复制原始数据
        processed_item = {k: v for k, v in item.items()}
        
        # 添加品牌提及和用户竞争分析结果
        processed_item['brand_mentions'] = brand_mentions_list[i] if i < len(brand_mentions_list) else {}
        processed_item['user_competition'] = user_competitions[i] if i < len(user_competitions) else {}
        
        # 从品牌分析中提取情感、特性和优劣势
        brand_analysis = all_brand_analysis[i] if i < len(all_brand_analysis) else {}
        
        brand_sentiments = {}
        brand_features = {}
        brand_strengths_weaknesses = {}
        
        for brand, analysis in brand_analysis.items():
                
            # 提取情感
            brand_sentiments[brand] = analysis.get('sentiment', 'neutral')
            
            # 提取特性
            brand_features[brand] = analysis.get('features', {})
            
            # 提取优劣势
            strengths = analysis.get('strengths', [])
            weaknesses = analysis.get('weaknesses', [])
            brand_strengths_weaknesses[brand] = {
                "strengths": strengths,
                "weaknesses": weaknesses
            }
        
        processed_item['brand_sentiments'] = brand_sentiments
        processed_item['brand_features'] = brand_features
        processed_item['brand_analysis'] = brand_strengths_weaknesses
        
        processed_data.append(processed_item)
    
    # 8. 输出结果
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_jsonl_path = os.path.join(output_dir, "atomic_insights_results.json")
        with open(output_jsonl_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)

    total_time = time.time() - start_time
    print(f"原子化分析完成，共处理 {len(parsed_data)} 条数据，总耗时: {total_time:.2f}秒，平均每条 {total_time/len(parsed_data):.2f}秒")
    
    return processed_data