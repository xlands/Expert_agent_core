import json
from typing import Dict, List, Any
from collections import Counter
from src.llm import LLM
from src.utils.extract_markdown import extract_structured_data

# 添加这个函数，用于计算情感百分比
def calculate_percentages(counts: Dict[str, int]) -> Dict[str, float]:
    """计算情感百分比
    
    Args:
        counts: 包含各类别计数的字典
        
    Returns:
        Dict[str, float]: 包含各类别百分比的字典
    """
    total = sum(counts.values())
    
    if total == 0:
        # 避免除以零，如果总数为0则返回默认值
        return {key: 0 for key in counts}
        
    return {key: round((count / total) * 100, 2) for key, count in counts.items()}

def calculate_brand_mentions(data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """计算品牌提及频次和占比，使用热度加权
    
    Args:
        data: 原始数据列表
        
    Returns:
        Dict[str, Dict[str, Any]]: 品牌名称、热度加权提及次数和占比
    """
    # 使用热度加权的品牌提及计数
    brand_mentions = Counter()
    
    for item in data:
        # 获取内容热度值
        heat_value = int(item.get("heat_value", 1))
        if not heat_value:
            heat_value = 1
            
        # 处理文章中的品牌提及 - 支持字典和列表两种格式
        if "brand_mentions" in item:
            if isinstance(item["brand_mentions"], dict):
                # 字典格式：{"品牌名": 出现次数}
                for brand, count in item["brand_mentions"].items():
                    # 使用热度值和提及次数的乘积作为权重
                    brand_mentions[brand] += count * heat_value
            elif isinstance(item["brand_mentions"], list):
                # 列表格式：["品牌名1", "品牌名2"]
                for brand in item["brand_mentions"]:
                    # 列表中每个品牌按1次计数，使用热度加权
                    brand_mentions[brand] += 1 * heat_value
    
    # 计算总热度权重
    total_mentions = sum(brand_mentions.values())
    
    # 构建结果字典，包含热度权重和占比
    result = {}
    for brand, heat_weighted_count in brand_mentions.items():
        percentage = (heat_weighted_count / total_mentions * 100) if total_mentions > 0 else 0
        result[brand] = {
            "count": heat_weighted_count,  # 热度加权后的计数
            "percentage": round(percentage, 2)
        }
    
    return result

def extract_user_quotes(data: List[Dict[str, Any]], min_length: int = 10, max_quotes: int = 10, 
                       brand_filter: str = None, feature_filter: str = None) -> List[Dict[str, Any]]:
    """提取用户原声，支持按品牌或特征筛选
    
    Args:
        data: 原始数据列表
        min_length: 原声最小长度
        max_quotes: 最大提取数量
        brand_filter: 品牌筛选条件(可选)
        feature_filter: 特征筛选条件(可选)
        
    Returns:
        List[Dict[str, Any]]: 用户原声列表，每项包含content, url, brand等信息
    """
    quotes = []
    used_urls = set()  # 跟踪已使用的URL，避免重复
    used_contents = set()  # 跟踪已使用的内容，避免内容重复
    
    for item in data:
        # 检查是否包含品牌筛选条件
        if brand_filter and "brand_mentions" in item:
            # 支持两种格式的品牌提及检查
            if isinstance(item["brand_mentions"], dict):
                # 字典格式：检查品牌是否在键中
                if brand_filter not in item["brand_mentions"]:
                    continue
            elif isinstance(item["brand_mentions"], list):
                # 列表格式：检查品牌是否在列表中
                if brand_filter not in item["brand_mentions"]:
                    continue
            else:
                # 其他格式：跳过
                continue
        
        # 获取互动数据
        like_count = item.get("like_count", 0)
        comment_count = item.get("comment_count", 0)
        collect_count = item.get("collect_count", 0)
        share_count = item.get("share_count", 0)
        url = item.get("url", "")
        title = item.get("title", "")
        
        # 确保URL不为空，如果为空则跳过
        if not url:
            continue
            
        # 提取帖子内容为原声
        if "detail_desc" in item and isinstance(item["detail_desc"], str) and len(item["detail_desc"]) >= min_length:
            content_snippet = item["detail_desc"][:200]  # 限制长度
            
            # 检查内容是否重复
            if content_snippet in used_contents:
                continue
                
            # 检查特征筛选条件
            if not feature_filter or (feature_filter.lower() in item["detail_desc"].lower()):
                # 检查URL是否已被使用
                if url in used_urls:
                    # 为同一URL的不同内容生成唯一标识
                    modified_url = f"{url}#content-{len(quotes)}"
                else:
                    modified_url = url
                    used_urls.add(url)
                
                used_contents.add(content_snippet)
                
                quotes.append({
                    "content": content_snippet,
                    "url": modified_url,
                    "title": title,
                    "heat_value": item.get("heat_value", 0),
                    "like_count": like_count,
                    "comment_count": comment_count,
                    "collect_count": collect_count,
                    "share_count": share_count,
                    "brand": brand_filter
                })
        
        # 提取评论为原声
        for comment_data in item["comments_data"][:5]:  # 每篇文章最多取5条评论
            if comment_data and "comment_content" in comment_data:
                comment_content = comment_data["comment_content"]
                if comment_content and len(comment_content) >= min_length:
                    content_snippet = comment_content[:200]  # 限制评论长度
                    
                    # 检查内容是否重复
                    if content_snippet in used_contents:
                        continue
                        
                    # 检查特征筛选条件
                    if not feature_filter or (feature_filter.lower() in content_snippet.lower()):
                        # 检查URL是否已被使用
                        if url in used_urls:
                            # 为同一URL的不同内容生成唯一标识
                            modified_url = f"{url}#comment-{len(quotes)}"
                        else:
                            modified_url = url
                            used_urls.add(url)
                        
                        used_contents.add(content_snippet)
                        
                        quotes.append({
                            "content": content_snippet,
                            "url": modified_url,
                            "title": title,
                            "heat_value": item.get("heat_value", 0),
                            "like_count": like_count,
                            "comment_count": comment_count,
                            "collect_count": collect_count,
                            "share_count": share_count,
                            "brand": brand_filter,
                            "is_comment": True
                        })
    
    # 按热度排序并限制数量
    # 首先按热度值排序
    sorted_quotes = sorted(quotes, key=lambda x: int(x.get("heat_value", 0)), reverse=True)
    
    # 如果热度值相同，则按点赞数排序
    sorted_quotes = sorted(sorted_quotes, key=lambda x: (int(x.get("heat_value", 0)), int(x.get("like_count", 0))), reverse=True)
    
    return sorted_quotes[:max_quotes]

def extract_top_k_contents(data: List[Dict[str, Any]], k: int = 20) -> str:
    """提取最热门的K条内容和评论，用于LLM分析
    
    Args:
        data: 原始数据列表
        k: 提取的内容数量
        
    Returns:
        str: 拼接的内容文本
    """
    # 计算每条内容的热度
    contents_with_heat = []
    
    for item in data:
        # 使用heat_value作为热度值
        heat = item.get("heat_value", 0)
        if not heat and "heat_value" not in item:
            # 如果没有heat_value字段，计算简化版热度
            heat = 0
            if "like_count" in item:
                heat += item.get("like_count", 0)
            if "comment_count" in item:
                heat += 4 * item.get("comment_count", 0)
            if "collect_count" in item:
                heat += item.get("collect_count", 0)
            
        # 提取内容
        content = {
            "title": item.get("title", "无标题"),
            "detail": item.get("detail_desc", "")[:500],  # 限制长度
            "heat": heat,
            "comments": [],
            "url": item.get("url", "")
        }
        
        # 添加评论
        if "comments" in item and isinstance(item["comments"], list):
            for comment in item["comments"][:5]:  # 每篇文章最多取5条评论
                if comment and isinstance(comment, str):
                    content["comments"].append(comment[:200])  # 限制评论长度
        
        contents_with_heat.append(content)
    
    # 按热度排序并提取前k条
    sorted_contents = sorted(contents_with_heat, key=lambda x: x["heat"], reverse=True)[:k]
    
    # 拼接内容
    result_text = ""
    for i, content in enumerate(sorted_contents):
        result_text += f"内容{i+1}[热度{content['heat']}]: {content['title']}\n"
        result_text += f"内容详情: {content['detail']}\n"
        result_text += f"链接: {content['url']}\n"
        
        if content["comments"]:
            result_text += "评论:\n"
            for j, comment in enumerate(content["comments"]):
                result_text += f"  - 评论{j+1}: {comment}\n"
        
        result_text += "\n---\n\n"
    
    return result_text

def analyze_content_with_llm(data: List[Dict[str, Any]], analysis_type: str, top_k: int = 20) -> Dict[str, Any]:
    """使用LLM对内容进行分析
    
    Args:
        data: 原始数据列表
        analysis_type: 分析类型 (features|keywords|competitors)
        top_k: 分析的top内容数量
        
    Returns:
        Dict[str, Any]: 分析结果
    """
    llm = LLM(model="deepseek-v3")
    
    # 提取热门内容
    top_contents = extract_top_k_contents(data, top_k)
    
    # 提取所有品牌
    brand_mentions = calculate_brand_mentions(data)
    top_brands = sorted(brand_mentions.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
    brands_str = ", ".join([brand for brand, _ in top_brands])
    
    # 构建统一的系统提示词
    system_prompt = """你是一个数据分析专家，需要根据提供的数据进行分析并返回JSON格式结果。
    
重要提示：
1. 只返回JSON格式的数据，不要包含任何其他文本、注释或解释
2. 不要使用```json或任何其他Markdown标记
3. 确保JSON格式正确，所有括号、引号都必须正确闭合
4. 直接输出原始JSON，不要添加任何前缀或后缀"""

    # 根据分析类型构建用户消息
    if analysis_type == "features":
        user_content = f"""分析以下内容中用户讨论的产品特征维度，不要使用预设的特征类别，而是从文本中发现用户真正关心的维度：
        
品牌列表：{brands_str}
        
内容样本：
{top_contents}
        
请输出JSON格式：
{{
    "特征维度分析": {{
        "发现的维度": ["维度1", "维度2", "维度3", "维度4", "维度5"],
        "品牌维度得分": [
            {{
                "品牌": "品牌名1",
                "各维度得分": [5, 4, 3, 2, 1]
            }},
            {{
                "品牌": "品牌名2",
                "各维度得分": [4, 5, 2, 3, 1]
            }}
        ],
        "维度用户原声": [
            {{
                "维度": "维度1",
                "原声": ["示例1", "示例2", "示例3"]
            }}
        ]
    }}
}}"""
    elif analysis_type == "keywords":
        user_content = f"""分析以下内容中关于各品牌的热门关键词，不要使用预设的词汇表，而是从文本中发现用户的真实表达：
        
品牌列表：{brands_str}
        
内容样本：
{top_contents}
        
请输出JSON格式：
{{
    "关键词分析": [
        {{
            "品牌": "品牌名1",
            "正面关键词": [
                {{"text": "正面词1", "weight": 10}},
                {{"text": "正面词2", "weight": 8}},
                ... 至少20个
            ],
            "负面关键词": [
                {{"text": "负面词1", "weight": 9}},
                {{"text": "负面词2", "weight": 7}},
                ... 至少20个
            ],
            "原声示例": [
                {{"关键词": "关键词1", "情感": "正面", "原声": ["示例1", "示例2"]}},
                {{"关键词": "关键词2", "情感": "负面", "原声": ["示例1", "示例2"]}}
            ]
        }}
    ]
}}"""
    elif analysis_type == "competitors":
        user_content = f"""分析以下内容中品牌间的竞争关系，找出用户摇摆和流出的证据：
        
品牌列表：{brands_str}
        
内容样本：
{top_contents}
        
请输出JSON格式：
{{
    "竞争关系分析": {{
        "主要品牌": "主品牌名",
        "竞争格局": [
            {{
                "竞品": "竞品名1",
                "竞争类型": "直接竞争/间接竞争",
                "用户摇摆证据": ["示例1", "示例2"],
                "用户流出证据": ["示例1", "示例2"],
                "竞争优劣势": {{"优势": ["点1", "点2"], "劣势": ["点1", "点2"]}}
            }}
        ],
        "用户决策因素": ["因素1", "因素2", "因素3"]
    }}
}}"""
    else:
        # 通用分析
        user_content = f"""分析以下内容中各品牌的关键信息，包括用户关注点、评价趋势、特色表达等：
        
品牌列表：{brands_str}
        
内容样本：
{top_contents}
        
请输出JSON格式：
{{
    "综合分析": [
        {{
            "品牌": "品牌名1",
            "主要关注点": ["点1", "点2", "点3"],
            "独特表达": ["表达1", "表达2", "表达3"],
            "用户原声": ["示例1", "示例2", "示例3"]
        }}
    ]
}}"""
    
    # 创建ChatML格式的消息列表
    messages = [{"role": "user", "content": user_content}]
    
    # 调用LLM并添加结果处理
    response = llm.generate(messages, system_prompt=system_prompt)
    
    # 使用extract_structured_data从响应中提取结构化数据
    return extract_structured_data(response, 'json')


def get_top_heat_posts(data: List[Dict[str, Any]], top_n: int = 3) -> List[Dict[str, Any]]:
    """获取热度最高的帖子
    
    Args:
        data: 原始数据列表
        top_n: 返回的帖子数量
        
    Returns:
        List[Dict[str, Any]]: 热度最高的帖子列表
    """
    # 筛选有效帖子
    valid_posts = []
    for item in data:
        heat = item.get("heat_value", 0)
        if heat and isinstance(heat, (int, float)) and heat > 0:
            valid_posts.append({
                "title": item.get("title", "无标题"),
                "detail": item.get("detail_desc", "")[:200],  # 限制长度
                "heat_value": heat,
                "url": item.get("url", ""),
                "created_date": item.get("created_date", ""),
                "brand_mentions": item.get("brand_mentions", {})
            })
    
    # 按热度排序并返回前top_n条
    return sorted(valid_posts, key=lambda x: int(x["heat_value"]), reverse=True)[:top_n]

def calculate_sentiment_distribution(data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """计算各品牌的情感分布
    
    Args:
        data: 原始数据列表
        
    Returns:
        Dict[str, Dict[str, Any]]: 品牌情感分布，包含正面、中性、负面占比
    """
    # 初始化结果字典
    result = {}
    
    # 统计各品牌情感数量
    brand_sentiment_counts = {}
    total_counts = {}
    
    # 遍历所有数据
    for item in data:
        # 只处理有brand_sentiments字段的数据
        if "brand_sentiments" not in item or not isinstance(item["brand_sentiments"], dict):
            continue
            
        # 获取热度，用于加权
        heat_value = item.get("heat_value", 1)
        if not heat_value:
            heat_value = 1
            
        # 遍历该数据中的品牌情感
        for brand, sentiment in item["brand_sentiments"].items():
            # 初始化该品牌的计数器
            if brand not in brand_sentiment_counts:
                brand_sentiment_counts[brand] = {
                    "positive": 0,
                    "neutral": 0,
                    "negative": 0
                }
                total_counts[brand] = 0
                
            # 增加对应情感计数
            sentiment_lower = sentiment.lower()
            if sentiment_lower in ["positive", "正面"]:
                brand_sentiment_counts[brand]["positive"] += heat_value
            elif sentiment_lower in ["negative", "负面"]:
                brand_sentiment_counts[brand]["negative"] += heat_value
            else:  # 默认中性
                brand_sentiment_counts[brand]["neutral"] += heat_value
                
            # 增加总计数
            total_counts[brand] += heat_value
    
    # 计算各品牌情感占比
    for brand, counts in brand_sentiment_counts.items():
        total = total_counts[brand]
        if total > 0:
            result[brand] = {
                "positive": round((counts["positive"] / total) * 100, 1),
                "neutral": round((counts["neutral"] / total) * 100, 1),
                "negative": round((counts["negative"] / total) * 100, 1)
            }
            
            # 确保总和为100%
            total_pct = result[brand]["positive"] + result[brand]["neutral"] + result[brand]["negative"]
            if total_pct != 100.0:
                diff = 100.0 - total_pct
                # 按比例分配差值
                if total_pct > 0:
                    ratio = 100.0 / total_pct
                    result[brand]["positive"] = round(result[brand]["positive"] * ratio, 1)
                    result[brand]["neutral"] = round(result[brand]["neutral"] * ratio, 1)
                    result[brand]["negative"] = round(result[brand]["negative"] * ratio, 1)
                else:
                    # 如果总和为0，设置为默认值
                    result[brand]["neutral"] = 100.0
    
    return result

def extract_feature_dimensions(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """使用LLM提取内容中的特征维度
    
    Args:
        data: 原始数据列表
        
    Returns:
        Dict[str, Any]: 特征维度分析结果
    """
    # 使用定制的分析函数获取特征维度
    llm = LLM(model="deepseek-v3")
    
    # 提取热门内容
    top_contents = extract_top_k_contents(data, 20)
    
    # 提取所有品牌
    brand_mentions = calculate_brand_mentions(data)
    top_brands = sorted(brand_mentions.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
    brands_str = ", ".join([brand for brand, _ in top_brands])
    
    # 构建系统提示词
    system_prompt = """你是一个数据分析专家，需要根据提供的数据进行分析并返回JSON格式结果。
    
重要提示：
1. 只返回JSON格式的数据，不要包含任何其他文本、注释或解释
2. 不要使用```json或任何其他Markdown标记
3. 确保JSON格式正确，所有括号、引号都必须正确闭合
4. 直接输出原始JSON，不要添加任何前缀或后缀"""

    # 构建用户消息
    user_content = f"""请分析以下内容中用户讨论的产品特征维度，不要使用预设的特征类别，而是从文本中发现用户真正关心的维度：

品牌列表：{brands_str}

内容样本：
{top_contents}

重要说明：
1. 请找出8个用户最关心的产品特征维度
2. 为每个品牌在这8个维度上打分（1-5分）
3. 为每个维度提供用户原声示例

请输出JSON格式：
{{
    "特征维度分析": {{
        "发现的维度": ["维度1", "维度2", "维度3", "维度4", "维度5", "维度6", "维度7", "维度8"],
        "品牌维度得分": [
            {{
                "品牌": "品牌名1",
                "各维度得分": [5, 4, 3, 2, 1, 4, 3, 5]
            }},
            {{
                "品牌": "品牌名2",
                "各维度得分": [4, 5, 2, 3, 1, 2, 4, 3]
            }}
        ],
        "维度用户原声": [
            {{
                "维度": "维度1",
                "原声": ["示例1", "示例2", "示例3"]
            }}
        ]
    }}
}}"""

    # 创建ChatML格式的消息列表
    messages = [{"role": "user", "content": user_content}]
    
    # 调用LLM并处理结果
    response = llm.generate(messages, system_prompt=system_prompt)
    
    # 使用extract_structured_data从响应中提取结构化数据
    result = extract_structured_data(response, 'json')
    
    if result is None:
        return {}
    
    # 创建结果字典
    feature_analysis = {}
    
    # 如果有特征维度分析
    if "特征维度分析" in result:
        analysis = result["特征维度分析"]
        
        # 提取维度列表
        if "发现的维度" in analysis:
            feature_analysis["dimensions"] = analysis["发现的维度"]
        
        # 提取品牌得分
        feature_analysis["brand_scores"] = {}
        if "品牌维度得分" in analysis:
            for brand_score in analysis["品牌维度得分"]:
                if "品牌" in brand_score and "各维度得分" in brand_score:
                    feature_analysis["brand_scores"][brand_score["品牌"]] = brand_score["各维度得分"]
        
        # 提取维度原声
        feature_analysis["dimension_quotes"] = {}
        if "维度用户原声" in analysis:
            for dim_quote in analysis["维度用户原声"]:
                if "维度" in dim_quote and "原声" in dim_quote:
                    feature_analysis["dimension_quotes"][dim_quote["维度"]] = dim_quote["原声"]
    
    return feature_analysis

def extract_keyword_analysis(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """使用LLM提取关键词分析
    
    Args:
        data: 原始数据列表
        
    Returns:
        Dict[str, Any]: 关键词分析结果
    """
    # 使用自定义提示词进行关键词分析
    llm = LLM(model="deepseek-v3")
    
    # 提取热门内容
    top_contents = extract_top_k_contents(data, 20)
    
    # 提取所有品牌
    brand_mentions = calculate_brand_mentions(data)
    top_brands = sorted(brand_mentions.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
    brands_str = ", ".join([brand for brand, _ in top_brands])
    
    # 构建系统提示词
    system_prompt = """你是一个数据分析专家，需要根据提供的数据进行分析并返回JSON格式结果。
    
重要提示：
1. 只返回JSON格式的数据，不要包含任何其他文本、注释或解释
2. 不要使用```json或任何其他Markdown标记
3. 确保JSON格式正确，所有括号、引号都必须正确闭合
4. 直接输出原始JSON，不要添加任何前缀或后缀"""
    
    # 构建用户消息
    user_content = f"""请详细分析以下内容中关于各品牌的热门关键词，不要使用预设的词汇表，而是从文本中发现用户的真实表达：
        
品牌列表：{brands_str}

内容样本：
{top_contents}

重要说明：
1. 请分别提取正面评价和负面评价关键词
2. 每个情感类型至少提供20个关键词（如果文本中有足够关键词）
3. 为每个关键词提供权重(1-10)和原声示例

请输出JSON格式：
{{
    "关键词分析": [
        {{
            "品牌": "品牌名1",
            "正面关键词": [
                {{"text": "正面词1", "weight": 10}},
                {{"text": "正面词2", "weight": 8}},
                ... 至少20个
            ],
            "负面关键词": [
                {{"text": "负面词1", "weight": 9}},
                {{"text": "负面词2", "weight": 7}},
                ... 至少20个
            ],
            "原声示例": [
                {{"关键词": "关键词1", "情感": "正面", "原声": ["示例1", "示例2"]}},
                {{"关键词": "关键词2", "情感": "负面", "原声": ["示例1", "示例2"]}}
            ]
        }}
    ]
}}"""

    # 创建ChatML格式的消息列表
    messages = [{"role": "user", "content": user_content}]
    
    # 调用LLM并处理结果
    response = llm.generate(messages, system_prompt=system_prompt)
    
    # 使用extract_structured_data从响应中提取结构化数据
    result = extract_structured_data(response, 'json')
    
    if result is None or "关键词分析" not in result:
        return {}
    
    # 直接使用原始结构，不提供默认值
    keyword_analysis = {}
    
    for brand_keywords in result["关键词分析"]:
        if "品牌" not in brand_keywords:
            continue
            
        brand = brand_keywords["品牌"]
        
        # 初始化品牌数据结构 - 使用空列表而非默认值
        keyword_analysis[brand] = {}
        
        # 处理正面关键词
        if "正面关键词" in brand_keywords:
            positive_keywords = brand_keywords["正面关键词"]
            keyword_analysis[brand]["positive_keywords"] = positive_keywords
            
            # 为正面关键词添加情感标记
            for kw in positive_keywords:
                if isinstance(kw, dict) and "text" in kw:
                    kw["情感"] = "正面"
        else:
            keyword_analysis[brand]["positive_keywords"] = []
        
        # 处理负面关键词
        if "负面关键词" in brand_keywords:
            negative_keywords = brand_keywords["负面关键词"] 
            keyword_analysis[brand]["negative_keywords"] = negative_keywords
            
            # 为负面关键词添加情感标记
            for kw in negative_keywords:
                if isinstance(kw, dict) and "text" in kw:
                    kw["情感"] = "负面"
        else:
            keyword_analysis[brand]["negative_keywords"] = []
        
        # 处理原声示例
        if "原声示例" in brand_keywords:
            examples = {}
            for example in brand_keywords["原声示例"]:
                if "关键词" in example and "原声" in example:
                    examples[example["关键词"]] = example["原声"]
            
            keyword_analysis[brand]["examples"] = examples
    
    return keyword_analysis

def extract_competitor_relationships(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """使用LLM提取竞争关系分析
    
    Args:
        data: 原始数据列表
        
    Returns:
        Dict[str, Any]: 竞争关系分析结果
    """
    result = analyze_content_with_llm(data, "competitors")
    
    # 标准化结果
    competitor_analysis = {}
    
    if "竞争关系分析" in result and isinstance(result["竞争关系分析"], dict):
        main_brand = result["竞争关系分析"].get("主要品牌", "")
        
        if main_brand:
            competitor_analysis[main_brand] = {
                "competitors": {},
                "decision_factors": result["竞争关系分析"].get("用户决策因素", [])
            }
            
            # 处理竞争格局
            for competitor in result["竞争关系分析"].get("竞争格局", []):
                comp_name = competitor.get("竞品", "")
                if not comp_name:
                    continue
                    
                competitor_analysis[main_brand]["competitors"][comp_name] = {
                    "type": competitor.get("竞争类型", "直接竞争"),
                    "wavering_quotes": competitor.get("用户摇摆证据", []),
                    "flowing_out_quotes": competitor.get("用户流出证据", []),
                    "strengths": competitor.get("竞争优劣势", {}).get("优势", []),
                    "weaknesses": competitor.get("竞争优劣势", {}).get("劣势", [])
                }
    
    return competitor_analysis

def calculate_content_heat(item: Dict[str, Any], is_comment: bool = False) -> float:
    """计算内容热度值
    
    计算公式: 热度值 = 4×评论数(对评论则为二级评论数) + 点赞数 + 收藏数(评论无)
    
    Args:
        item: 内容数据
        is_comment: 是否为评论
        
    Returns:
        float: 热度值
    """
    heat_value = 0
    
    # 对于原始帖子
    if not is_comment:
        # 获取评论数并确保是整数
        comment_count = item.get("comment_count", 0)
        if isinstance(comment_count, str):
            try:
                comment_count = int(comment_count)
            except ValueError:
                comment_count = 0
        
        # 获取点赞数并确保是整数
        like_count = item.get("like_count", 0)
        if isinstance(like_count, str):
            try:
                like_count = int(like_count)
            except ValueError:
                like_count = 0
        
        # 获取收藏数并确保是整数
        collect_count = item.get("collect_count", 0)
        if isinstance(collect_count, str):
            try:
                collect_count = int(collect_count)
            except ValueError:
                collect_count = 0
        
        # 应用热度计算公式
        heat_value = 4 * comment_count + like_count + collect_count
    
    # 对于评论
    else:
        # 获取二级评论/回复数并确保是整数
        reply_count = item.get("comment_reply_count", 0)
        if isinstance(reply_count, str):
            try:
                reply_count = int(reply_count)
            except ValueError:
                reply_count = 0
                
        # 获取评论点赞数并确保是整数
        like_count = item.get("comment_like_count", 0)
        if isinstance(like_count, str):
            try:
                like_count = int(like_count)
            except ValueError:
                like_count = 0
        
        # 评论没有收藏数，应用评论热度计算公式
        heat_value = 4 * reply_count + like_count
    
    return heat_value