import os
import json
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
import re
from src.llm import LLM
from src.agent.analyzer.base_analyzer import BaseAnalyzer
from src.tools.analysis_tools import (
    calculate_brand_mentions,
    calculate_sentiment_distribution,
    extract_feature_dimensions,
    extract_competitor_relationships,
    extract_keyword_analysis,
    analyze_content_with_llm,
    extract_user_quotes,
    get_top_heat_posts,
    extract_top_k_contents,
    calculate_content_heat
)

class BrandAnalyzer(BaseAnalyzer):
    """品牌分析师，负责分析品牌声量、情感和特征"""
    
    def __init__(self, output_dir: str = None):
        """
        初始化品牌分析师
        
        Args:
            output_dir: 可选输出目录，用于保存分析结果
        """
        super().__init__(output_dir)
    
    def analyze_brand_mentions(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析品牌声量
        
        Args:
            data: 原始数据列表
            
        Returns:
            Dict[str, Any]: 品牌声量分析结果
        """
        # 使用analysis_tools中的函数计算品牌提及频次和占比
        brand_mentions = calculate_brand_mentions(data)
        
        # 只保留前10个品牌
        top_brands = sorted(brand_mentions.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
        
        # 提取相关的用户原声
        brand_quotes = []
        if top_brands:
            top_brand = top_brands[0][0]
            # 确保提取足够数量的不同原声
            brand_quotes = extract_user_quotes(data, brand_filter=top_brand, max_quotes=10)
            
            # 过滤，确保原声URLs不重复
            seen_urls = set()
            filtered_quotes = []
            for quote in brand_quotes:
                url = quote.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    filtered_quotes.append(quote)
                    if len(filtered_quotes) >= 5:  # 限制为最多5条原声
                        break
                        
            brand_quotes = filtered_quotes
        
        # 生成分析结果
        result = {
            "title": "品牌声量分析",
            "insights": []
        }
        
        if top_brands:
            # 计算第一名品牌与第二名的差距
            percentage_diff = ""
            if len(top_brands) > 1:
                first_percent = top_brands[0][1]["percentage"]
                second_percent = top_brands[1][1]["percentage"]
                diff = first_percent - second_percent
                percentage_diff = f"，领先第二名品牌 {diff:.1f}%"
            
            result["insights"].append({
                "content": f"在所有评论和内容中，{top_brands[0][0]}品牌讨论热度最高，占比达{top_brands[0][1]['percentage']}%{percentage_diff}",
                "data_support": {
                    "品牌": top_brands[0][0],
                    "讨论热度占比": f"{top_brands[0][1]['percentage']}%"
                },
                "user_quotes": brand_quotes,
                "visualization": {
                    "chart_type": "柱状图",
                    "brands": [b[0] for b in top_brands],
                    "percentages": [b[1]["percentage"] for b in top_brands]
                }
            })
        
        # 保存结果到文件
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            output_path = os.path.join(self.output_dir, "brand_mentions_analysis.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result
    
    def analyze_brand_sentiment(self, data: List[Dict[str, Any]] = None, brand_filter: str = None) -> Dict[str, Any]:
        """分析品牌情感

        Args:
            data: 可选的数据列表，如果不传入则从数据库获取
            brand_filter: 可选的品牌过滤条件，如果提供则只分析该品牌

        Returns:
            Dict[str, Any]: 包含品牌情感分析结果和用户原声的字典
        """
        # 导入正确的模块
        from src.tools.analysis_tools import calculate_percentages

        # 如果没有传入数据，从数据库获取
        if data is None:
            # 确保导入路径正确
            from src.agent.analyzer.data_loader import load_data
            data = load_data()

        if not data:
            return {"error": "没有找到数据"}

        # 收集所有品牌提及
        brand_mentions = {}
        brand_sentiments = {}

        for item in data:
            # 检查是否有品牌提及
            if "brand_mentions" in item:
                brands = []
                
                # 支持列表和字典两种格式
                if isinstance(item["brand_mentions"], list):
                    brands = item["brand_mentions"]
                elif isinstance(item["brand_mentions"], dict):
                    brands = list(item["brand_mentions"].keys())
                
                # 如果有品牌过滤，只分析该品牌
                if brand_filter:
                    if brand_filter not in brands:
                        continue
                    brands = [brand_filter]
                
                for brand in brands:
                    # 初始化品牌统计
                    if brand not in brand_mentions:
                        brand_mentions[brand] = 0
                        brand_sentiments[brand] = {"positive": 0, "neutral": 0, "negative": 0}
                    
                    brand_mentions[brand] += 1
                    
                    # 处理品牌情感
                    if "brand_sentiments" in item and brand in item["brand_sentiments"]:
                        sentiment = item["brand_sentiments"][brand]
                        if sentiment in brand_sentiments[brand]:
                            brand_sentiments[brand][sentiment] += 1

        # 如果没有找到品牌数据
        if not brand_mentions:
            return {"error": "没有找到品牌数据"}

        # 计算情感百分比
        brand_sentiment_result = []
        
        for brand, mention_count in sorted(brand_mentions.items(), key=lambda x: x[1], reverse=True):
            sentiment_counts = brand_sentiments[brand]
            total_sentiment = sum(sentiment_counts.values())
            
            # 如果没有情感数据，默认全部为中性
            if total_sentiment == 0:
                percentages = {"positive": 0, "neutral": 100, "negative": 0}
            else:
                percentages = calculate_percentages(sentiment_counts)
            
            brand_sentiment_result.append({
                "brand": brand,
                "mentions": mention_count,
                "sentiments": {
                    "positive": percentages["positive"],
                    "neutral": percentages["neutral"],
                    "negative": percentages["negative"]
                }
            })
        
        # 提取用户原声
        all_quotes = []
        
        # 首先尝试提取有情感标签的原声
        positive_quotes = extract_user_quotes(data, brand_filter=brand_filter, 
                                           max_quotes=6, feature_filter="positive")
        negative_quotes = extract_user_quotes(data, brand_filter=brand_filter, 
                                           max_quotes=6, feature_filter="negative")
        neutral_quotes = extract_user_quotes(data, brand_filter=brand_filter, 
                                          max_quotes=3, feature_filter="neutral")
        
        # 如果情感标签原声不足，再提取一些一般原声补充
        if len(positive_quotes) < 2 and len(negative_quotes) < 2 and len(neutral_quotes) < 1:
            general_quotes = extract_user_quotes(data, brand_filter=brand_filter, max_quotes=10)
            for quote in general_quotes:
                quote["sentiment"] = "未标记"
                all_quotes.append(quote)
        else:
            # 添加原声并标记情感
            for quote in positive_quotes:
                quote["sentiment"] = "正面"
                all_quotes.append(quote)
            
            for quote in negative_quotes:
                quote["sentiment"] = "负面"
                all_quotes.append(quote)
            
            for quote in neutral_quotes:
                quote["sentiment"] = "中性"
                all_quotes.append(quote)
        
        # 限制原声总数
        all_quotes = all_quotes[:10]
        
        return {
            "brand_sentiment": brand_sentiment_result,
            "user_quotes": all_quotes
        }

class CompetitorAnalyzer(BaseAnalyzer):
    """竞争分析师，负责分析竞争对手和竞争关系"""
    
    def __init__(self, output_dir: str = None):
        """
        初始化竞争分析师
        
        Args:
            output_dir: 可选输出目录，用于保存分析结果
        """
        super().__init__(output_dir)
    
    def analyze_competitor_relationships(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析主品牌与竞争对手的关系
        
        Args:
            data: 原始数据列表
            
        Returns:
            Dict[str, Any]: 竞争关系分析结果
        """
        # 使用LLM分析竞争关系
        competitor_analysis = extract_competitor_relationships(data)
        
        # 处理分析结果
        result = {
            "title": "竞争对手分析",
            "insights": []
        }
        
        if not competitor_analysis:
            return result
        
        # 获取主品牌
        main_brand = list(competitor_analysis.keys())[0] if competitor_analysis else None
        if not main_brand:
            return result
        
        # 获取竞争对手排序列表
        competitors = competitor_analysis.get(main_brand, {}).get("competitors", {})
        competitor_list = sorted(competitors.items(), key=lambda x: len(x[1]["wavering_quotes"]) + len(x[1]["flowing_out_quotes"]), reverse=True)
        
        if not competitor_list:
            return result
        
        # 获取排名第一的竞品
        top_competitor = {"brand": competitor_list[0][0], "data": competitor_list[0][1]}
        
        # 获取决策因素
        decision_factors = competitor_analysis.get(main_brand, {}).get("decision_factors", [])
        
        # 收集有代表性的竞争原声
        user_quotes = []
        seen_urls = set()  # 跟踪已使用的URL，避免重复
        
        # 从原始数据中提取有关竞品关系的原声
        for item in data:
            # 跳过没有URL的条目
            if "url" not in item or not item["url"]:
                continue
                
            # 检查是否同时提到了主品牌和竞争品牌
            main_brand_mentioned = False
            competitor_mentioned = False
            
            if "brand_mentions" in item:
                if isinstance(item["brand_mentions"], dict):
                    main_brand_mentioned = main_brand in item["brand_mentions"]
                    competitor_mentioned = top_competitor["brand"] in item["brand_mentions"]
                elif isinstance(item["brand_mentions"], list):
                    main_brand_mentioned = main_brand in item["brand_mentions"]
                    competitor_mentioned = top_competitor["brand"] in item["brand_mentions"]
            
            if main_brand_mentioned and competitor_mentioned:
                # 检查URL是否已使用
                if item["url"] in seen_urls:
                    continue
                    
                # 检查内容是否包含"摇摆"或"流出"相关词汇
                user_flow_type = None
                if "detail_desc" in item:
                    detail = item["detail_desc"].lower()
                    if "比较" in detail or "对比" in detail or "选择" in detail or "纠结" in detail:
                        user_flow_type = "用户摇摆"
                    elif "放弃" in detail or "选择了" in detail or "购买了" in detail:
                        user_flow_type = "用户流出"
                
                if user_flow_type:
                    # 提取一个代表性的原声片段
                    content = item.get("detail_desc", "")[:200]
                    
                    if content:
                        user_quotes.append({
                            "content": content,
                            "type": user_flow_type,
                            "brands": [main_brand, top_competitor["brand"]],
                            "url": item["url"],
                            "heat_value": item.get("heat_value", 0),
                            "like_count": item.get("like_count", 0)
                        })
                        seen_urls.add(item["url"])
            
            # 检查评论
            if "comments_data" in item and isinstance(item["comments_data"], list):
                for i, comment_data in enumerate(item["comments_data"]):
                    comment = comment_data["comment_content"]
                    
                    # 检查评论是否同时提到主品牌和竞争品牌
                    main_mentioned = main_brand.lower() in comment.lower()
                    competitor_mentioned = top_competitor["brand"].lower() in comment.lower()
                    
                    if main_mentioned and competitor_mentioned:
                        # 为评论生成唯一URL
                        comment_url = f"{item['url']}#comment-{i}" if item.get('url') else f"comment-{i}"
                        
                        if comment_url in seen_urls:
                            continue
                            
                        # 检查内容是否包含"摇摆"或"流出"相关词汇
                        user_flow_type = None
                        if "比较" in comment or "对比" in comment or "选择" in comment or "纠结" in comment:
                            user_flow_type = "用户摇摆"
                        elif "放弃" in comment or "选择了" in comment or "购买了" in comment:
                            user_flow_type = "用户流出"
                        
                        if user_flow_type:
                            user_quotes.append({
                                "content": comment[:200],
                                "type": user_flow_type,
                                "brands": [main_brand, top_competitor["brand"]],
                                "url": comment_url,
                                "is_comment": True,
                                "heat_value": comment_data.get("comment_heat_value", 0),  # 使用评论自带的热度值
                                "like_count": comment_data.get("comment_like_count", 0)  # 使用评论自带的点赞数
                            })
                            seen_urls.add(comment_url)
        
        # 如果没有足够的原声，添加一些通用的
        if len(user_quotes) < 4:
            # 添加LLM分析产生的原声示例
            wavering_quotes = top_competitor["data"].get("wavering_quotes", [])
            flowing_out_quotes = top_competitor["data"].get("flowing_out_quotes", [])
            
            for i, quote in enumerate(wavering_quotes):
                if len(user_quotes) >= 4:
                    break
                    
                artificial_url = f"artificial-wavering-{i}"
                if artificial_url not in seen_urls:
                    user_quotes.append({
                        "content": quote,
                        "type": "用户摇摆",
                        "brands": [main_brand, top_competitor["brand"]],
                        "heat_value": 0  # 人工生成的引用默认热度为0
                    })
                    seen_urls.add(artificial_url)
            
            for i, quote in enumerate(flowing_out_quotes):
                if len(user_quotes) >= 4:
                    break
                    
                artificial_url = f"artificial-flowout-{i}"
                if artificial_url not in seen_urls:
                    user_quotes.append({
                        "content": quote,
                        "type": "用户流出",
                        "brands": [main_brand, top_competitor["brand"]],
                        "heat_value": 0  # 人工生成的引用默认热度为0
                    })
                    seen_urls.add(artificial_url)
        
        # 按热度排序前确保所有引用都有heat_value字段
        for quote in user_quotes:
            if "heat_value" not in quote:
                quote["heat_value"] = 0
                
        # 按互动热度排序，使用get方法避免缺失字段错误
        user_quotes.sort(key=lambda x: int(x.get("heat_value", 0)), reverse=True)
        
        # 限制为最多4条
        user_quotes = user_quotes[:4]
        
        # 构建网络图节点和链接
        nodes = [
            {"id": main_brand, "group": 1}
        ]
        
        links = []
        
        # 添加竞争品牌节点和基础链接
        for i, competitor in enumerate(competitor_list[:4]):  # 最多展示4个竞争对手
            nodes.append({"id": competitor[0], "group": 2})
            
            # 基础关系链接
            links.append({
                "source": main_brand,
                "target": competitor[0],
                "type": "基础关系",
                "value": 1
            })
            
            # 用户摇摆链接
            oscillation_quotes = [q for q in user_quotes if q["type"] == "用户摇摆" and q["brands"][1] == competitor[0]]
            if oscillation_quotes:
                links.append({
                    "source": main_brand,
                    "target": competitor[0],
                    "type": "用户摇摆",
                    "value": 2,
                    "quotes": [q["content"] for q in oscillation_quotes[:2]]
                })
            
            # 用户流出链接
            outflow_quotes = [q for q in user_quotes if q["type"] == "用户流出" and q["brands"][1] == competitor[0]]
            if outflow_quotes:
                links.append({
                    "source": main_brand,
                    "target": competitor[0],
                    "type": "用户流出",
                    "value": 3,
                    "quotes": [q["content"] for q in outflow_quotes[:2]]
                })
        
        # 准备用于洞察生成的数据
        competition_type = top_competitor["data"].get("type", "直接竞争")
        strengths = top_competitor["data"].get("strengths", [])
        weaknesses = top_competitor["data"].get("weaknesses", [])
        
        insight_data = {
            "competitor_analysis": {
                "main_brand": main_brand,
                "top_competitor": top_competitor["brand"],
                "competition_type": competition_type,
                "competitors_count": len(competitor_list),
                "wavering_quotes_count": len(top_competitor["data"].get("wavering_quotes", [])),
                "flowing_out_quotes_count": len(top_competitor["data"].get("flowing_out_quotes", [])),
                "user_decision_factors": decision_factors,
                "strengths": strengths,
                "weaknesses": weaknesses
            }
        }
        
        # 使用LLM生成数据驱动的洞察
        insight = self.generate_data_driven_insight(insight_data, "competitor")
        
        # 构建分析结果
        result = {
            "title": "竞争对手分析",
            "insights": [
                {
                    "content": insight["content"],
                    "data_support": {
                        "主品牌": main_brand,
                        "主要竞争对手": top_competitor["brand"],
                        "竞争类型": competition_type,
                        "竞争优势": strengths,
                        "竞争劣势": weaknesses,
                        "用户决策因素": decision_factors
                    },
                    "user_quotes": user_quotes,
                    "visualization": {
                        "chart_type": "网络图",
                        "nodes": nodes,
                        "links": links,
                        "relationship_types": ["基础关系", "用户摇摆", "用户流出"]
                    }
                }
            ]
        }
        
        # 保存结果到文件
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            output_path = os.path.join(self.output_dir, "competitor_analysis.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result

class FeatureAnalyzer(BaseAnalyzer):
    """产品特征分析师，使用LLM发现用户真正关心的维度"""
    
    def __init__(self, output_dir: str = None):
        """
        初始化产品特征分析师
        
        Args:
            output_dir: 可选输出目录，用于保存分析结果
        """
        super().__init__(output_dir)
    
    def analyze_product_features(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析产品特征和各品牌在不同特征上的表现
        
        Args:
            data: 原始数据列表
            
        Returns:
            Dict[str, Any]: 产品特征分析结果
        """
        # 使用LLM分析提取产品特征
        feature_analysis = extract_feature_dimensions(data)
        
        if not feature_analysis or "dimensions" not in feature_analysis:
            return {
                "title": "产品特征分析",
                "insights": []
            }
        
        # 提取维度列表
        dimensions = feature_analysis["dimensions"]
        
        if not dimensions:
            return {
                "title": "产品特征分析",
                "insights": []
            }
        
        # 获取品牌得分和维度排序
        max_dimension = ""
        max_score = 0
        max_brand = ""
        
        brands = []
        scores = []
        
        for brand, brand_scores in feature_analysis["brand_scores"].items():
            brands.append(brand)
            brand_score_list = []
            
            # 品牌得分在这里是一个列表，不是字典，需要按索引处理
            for i, dimension in enumerate(dimensions):
                # 确保索引在有效范围内
                if i < len(brand_scores):
                    score = brand_scores[i]
                else:
                    score = 0
                    
                brand_score_list.append(score)
                
                # 更新最高分的维度和品牌
                if score > max_score:
                    max_score = score
                    max_dimension = dimensions[i] if i < len(dimensions) else ""
                    max_brand = brand
            
            scores.append(brand_score_list)
        
        # 为每个特征收集相关的用户原声
        dimension_quotes = {}
        seen_urls = set()  # 用于追踪已使用的URL，避免重复
        
        # 首先为最重要的维度收集原声
        for dimension in dimensions[:5]:  # 只处理前5个维度
            # 获取当前维度的原声
            dimension_quotes[dimension] = []
            
            # 使用特征筛选从原始数据中提取原声
            for item in data:
                # 如果已经为该维度收集了足够的原声，则跳过
                if len(dimension_quotes[dimension]) >= 3:
                    break
                
                if "url" not in item or not item["url"] or item["url"] in seen_urls:
                    continue
                
                # 检查内容是否提及该特征
                feature_mentioned = False
                if "detail_desc" in item:
                    feature_mentioned = dimension.lower() in item["detail_desc"].lower()
                
                if feature_mentioned:
                    # 确定提到的品牌
                    mentioned_brand = None
                    if "brand_mentions" in item:
                        for brand in brands:
                            if brand in item["brand_mentions"]:
                                mentioned_brand = brand
                                break
                    
                    if mentioned_brand:
                        dimension_quotes[dimension].append({
                            "content": item["detail_desc"][:200],
                            "dimension": dimension,
                            "brand": mentioned_brand,
                            "url": item["url"],
                            "title": item.get("title", ""),
                            "like_count": item.get("like_count", 0),
                            "comment_count": item.get("comment_count", 0),
                            "collect_count": item.get("collect_count", 0),
                            "heat_value": item.get("heat_value", 0)
                        })
                        seen_urls.add(item["url"])
            
            # 如果从内容中没有找到足够的原声，从评论中查找
            if len(dimension_quotes[dimension]) < 3:
                for item in data:
                    if "comments" not in item or not isinstance(item["comments"], list):
                        continue
                    
                    if len(dimension_quotes[dimension]) >= 3:
                        break
                    
                    if "url" not in item or not item["url"]:
                        continue
                    
                    for i, comment in enumerate(item["comments"]):
                        if not comment or not isinstance(comment, str):
                            continue
                        
                        if len(dimension_quotes[dimension]) >= 3:
                            break
                        
                        # 检查评论是否提及该特征
                        feature_mentioned = dimension.lower() in comment.lower()
                        
                        if feature_mentioned:
                            # 确定提到的品牌
                            mentioned_brand = None
                            for brand in brands:
                                if brand.lower() in comment.lower():
                                    mentioned_brand = brand
                                    break
                            
                            if mentioned_brand:
                                comment_url = f"{item['url']}#comment-{i}"
                                if comment_url not in seen_urls:
                                    dimension_quotes[dimension].append({
                                        "content": comment[:200],
                                        "dimension": dimension,
                                        "brand": mentioned_brand,
                                        "url": comment_url,
                                        "title": item.get("title", "评论"),
                                        "like_count": item.get("like_count", 0),
                                        "comment_count": item.get("comment_count", 0),
                                        "is_comment": True
                                    })
                                    seen_urls.add(comment_url)
        
        # 合并所有维度的原声
        all_quotes = []
        for dimension, quotes in dimension_quotes.items():
            all_quotes.extend(quotes)
        
        # 如果没有足够的原声，补充一些通用原声
        if len(all_quotes) < 3:
            additional_quotes = extract_user_quotes(data, max_quotes=3-len(all_quotes))
            for quote in additional_quotes:
                quote["dimension"] = max_dimension  # 为通用原声指定最重要的维度
            all_quotes.extend(additional_quotes)
        
        # 按用户互动数据排序
        all_quotes.sort(key=lambda x: int(x.get("heat_value", 0)), reverse=True)
        
        # 准备用于洞察生成的数据
        insight_data = {
            "feature_analysis": {
                "dimensions": dimensions,
                "brands": brands,
                "scores": scores,
                "max_dimension": max_dimension,
                "max_brand": max_brand,
                "max_score": max_score
            }
        }
        
        # 使用LLM生成数据驱动的洞察
        insight = self.generate_data_driven_insight(insight_data, "feature")
        
        # 生成分析结果
        result = {
            "title": "产品特征分析",
            "insights": [
                {
                    "content": insight["content"],
                    "data_support": {
                        "品牌": max_brand,
                        "关键维度": max_dimension,
                        "各维度得分": scores,
                        "所有维度": dimensions
                    },
                    "user_quotes": all_quotes[:3],  # 只保留前3条引用
                    "visualization": {
                        "chart_type": "雷达图",
                        "dimensions": dimensions,
                        "brands": brands[:8],  # 展示前8个品牌
                        "scores": scores[:8]  # 展示前8个品牌的分数
                    }
                }
            ]
        }
        
        # 保存结果到文件
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            output_path = os.path.join(self.output_dir, "feature_analysis.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result

class KeywordAnalyzer(BaseAnalyzer):
    """关键词分析师，使用LLM发现真实用户表达"""
    
    def __init__(self, output_dir: str = None):
        """
        初始化关键词分析师
        
        Args:
            output_dir: 可选输出目录，用于保存分析结果
        """
        super().__init__(output_dir)
    
    def analyze_keywords(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析关键词
        
        Args:
            data: 原始数据列表
            
        Returns:
            Dict[str, Any]: 关键词分析结果
        """
        # 使用LLM提取关键词分析
        keywords_analysis = extract_keyword_analysis(data)
        
        # 生成结果
        result = {
            "title": "关键词分析",
            "insights": []
        }
        
        if not keywords_analysis:
            return result
        
        # 选择热度最高的品牌进行分析
        brand_counts = calculate_brand_mentions(data)
        if not brand_counts:
            return result
            
        top_brands = sorted(brand_counts.items(), key=lambda x: x[1]["count"], reverse=True)
        if not top_brands:
            return result
            
        top_brand = top_brands[0][0]
        
        if top_brand not in keywords_analysis:
            return result
            
        brand_keywords = keywords_analysis[top_brand]
        
        # 提取正面关键词
        positive_keywords = brand_keywords.get("positive_keywords", [])
        # 提取负面关键词
        negative_keywords = brand_keywords.get("negative_keywords", [])
        
        if not positive_keywords and not negative_keywords:
            return result
            
        # 找出权重最高的正面和负面关键词
        top_positive = max(positive_keywords, key=lambda x: x.get("weight", 0)) if positive_keywords else None
        top_negative = max(negative_keywords, key=lambda x: x.get("weight", 0)) if negative_keywords else None
        
        # 收集正面和负面关键词的用户原声
        positive_quotes = []
        negative_quotes = []
        
        # 从品牌原声中提取关键词相关的内容
        quotes = extract_user_quotes(data, brand_filter=top_brand, max_quotes=20)
        
        # 寻找包含关键词的原声
        for quote in quotes:
            content = quote.get("content", "").lower()
            url = quote.get("url", "")
            
            if not content or not url:
                continue
            
            # 为正面和负面关键词收集原声
            positive_words = [kw.get("text", "").lower() for kw in positive_keywords[:5]]
            negative_words = [kw.get("text", "").lower() for kw in negative_keywords[:5]]
            
            if positive_words and any(word in content for word in positive_words):
                sentiment = "正面"
                if len(positive_quotes) < 3:
                    positive_quotes.append({
                        "content": quote["content"],
                        "url": url,
                        "sentiment": sentiment,
                        "heat_value": quote.get("heat_value", 0),
                        "like_count": quote.get("like_count", 0)
                    })
            elif negative_words and any(word in content for word in negative_words):
                sentiment = "负面"
                if len(negative_quotes) < 3:
                    negative_quotes.append({
                        "content": quote["content"],
                        "url": url,
                        "sentiment": sentiment,
                        "heat_value": quote.get("heat_value", 0),
                        "like_count": quote.get("like_count", 0)
                    })
            
            all_quotes = positive_quotes + negative_quotes
            if len(positive_quotes) >= 3 and len(negative_quotes) >= 3:
                break
        
        # 准备用于洞察生成的数据
        insight_data = {
            "keyword_analysis": {
                "brand": top_brand,
                "top_positive_keyword": top_positive,
                "top_negative_keyword": top_negative,
                "positive_keywords_count": len(positive_keywords),
                "negative_keywords_count": len(negative_keywords)
            }
        }
        
        # 使用LLM生成数据驱动的洞察
        insight = self.generate_data_driven_insight(insight_data, "keyword")
        
        # 正面关键词洞察
        positive_insight = self.generate_data_driven_insight({
            "keyword_type": "positive",
            "brand": top_brand,
            "top_keyword": top_positive,
            "keywords": positive_keywords[:10]
        }, "positive_keyword")
        
        # 负面关键词洞察
        negative_insight = self.generate_data_driven_insight({
            "keyword_type": "negative",
            "brand": top_brand,
            "top_keyword": top_negative,
            "keywords": negative_keywords[:10]
        }, "negative_keyword")
        
        # 构建正面关键词数据支持
        positive_data_support = {"品牌": top_brand}
        if top_positive:
            positive_data_support["热门正面关键词"] = top_positive.get("text", "")
            positive_data_support["权重"] = top_positive.get("weight", 0)
        
        # 构建负面关键词数据支持
        negative_data_support = {"品牌": top_brand}
        if top_negative:
            negative_data_support["热门负面关键词"] = top_negative.get("text", "")
            negative_data_support["权重"] = top_negative.get("weight", 0)
        
        # 生成分析结果
        result = {
            "title": "关键词分析",
            "insights": [
                {
                    "content": positive_insight["content"],
                    "data_support": positive_data_support,
                    "user_quotes": positive_quotes,
                    "visualization": {
                        "chart_type": "词云图",
                        "sentiment": "正面",
                        "words": [
                            {"text": kw.get("text", ""), "weight": kw.get("weight", 1), "sentiment": "正面"}
                            for kw in sorted(positive_keywords, key=lambda x: x.get("weight", 0), reverse=True)[:20]
                        ]
                    }
                },
                {
                    "content": negative_insight["content"],
                    "data_support": negative_data_support,
                    "user_quotes": negative_quotes,
                    "visualization": {
                        "chart_type": "词云图",
                        "sentiment": "负面",
                        "words": [
                            {"text": kw.get("text", ""), "weight": kw.get("weight", 1), "sentiment": "负面"}
                            for kw in sorted(negative_keywords, key=lambda x: x.get("weight", 0), reverse=True)[:20]
                        ]
                    }
                }
            ]
        }
        
        # 保存结果到文件
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            output_path = os.path.join(self.output_dir, "keyword_analysis.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result

class TrendAnalyzer(BaseAnalyzer):
    """趋势分析师，展示热门帖子和讨论趋势"""
    
    def __init__(self, output_dir: str = None):
        """
        初始化趋势分析师
        
        Args:
            output_dir: 可选输出目录，用于保存分析结果
        """
        super().__init__(output_dir)
    
    def analyze_trends(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析行业趋势
        
        Args:
            data: 原始数据列表
            
        Returns:
            Dict[str, Any]: 行业趋势分析结果
        """
        # 获取热门帖子
        top_posts = get_top_heat_posts(data, top_n=10)
        
        if not top_posts:
            return {
                "title": "行业趋势分析",
                "insights": []
            }
        
        # 按时间排序的热门话题
        topics_by_date = sorted(top_posts, key=lambda x: x.get("created_date", ""), reverse=True)
        
        # 提取每个帖子包含的品牌
        for post in topics_by_date:
            post["brands_list"] = list(post.get("brand_mentions", {}).keys())
        
        # 构建用户原声
        user_quotes = []
        seen_urls = set()  # 用于追踪URL唯一性
        
        # 从热门帖子中提取原声
        for post in top_posts[:6]:  # 最多提取6个帖子的原声
            if len(user_quotes) >= 3:
                break
                
            url = post.get("url", "")
            if not url or url in seen_urls:
                continue
                
            # 计算帖子提到的品牌
            brands = post.get("brands_list", [])
            brands_str = ", ".join(brands[:3]) if brands else ""
            
            seen_urls.add(url)
            user_quotes.append({
                "content": post.get("detail_desc", "")[:200],
                "url": url,
                "title": post.get("title", ""),
                "heat_value": post.get("heat_value", 0),
                "brands": brands_str,
                "created_date": post.get("created_date", "")
            })
        
        # 如果没有足够的原声，从原始数据中提取更多
        if len(user_quotes) < 3:
            # 按热度排序获取热门帖子
            extra_quotes = []
            for item in data:
                if len(extra_quotes) >= 3-len(user_quotes):
                    break
                    
                url = item.get("url", "")
                if not url or url in seen_urls:
                    continue
                    
                heat = item.get("heat_value", 0)
                if heat <= 0:
                    continue
                
                # 获取品牌列表
                brands = []
                if "brand_mentions" in item and isinstance(item["brand_mentions"], dict):
                    brands = list(item["brand_mentions"].keys())
                
                brands_str = ", ".join(brands[:3]) if brands else ""
                
                seen_urls.add(url)
                extra_quotes.append({
                    "content": item.get("detail_desc", "")[:200],
                    "url": url,
                    "title": item.get("title", ""),
                    "heat_value": heat,
                    "brands": brands_str,
                    "created_date": item.get("created_date", "")
                })
            
            # 按热度排序
            extra_quotes.sort(key=lambda x: int(x.get("heat_value", 0)), reverse=True)
            user_quotes.extend(extra_quotes)
        
        # 限制为前3条
        user_quotes = user_quotes[:3]
        
        # 生成最热门的前三个话题
        hot_topics = []
        for i, post in enumerate(top_posts[:3]):
            hot_topics.append({
                "title": post.get("title", f"热门话题{i+1}"),
                "heat_value": post.get("heat_value", 0),
                "brands": post.get("brands_list", []),
                "created_date": post.get("created_date", ""),
                "url": post.get("url", "")
            })
        
        # 生成分析结果
        result = {
            "title": "行业趋势分析",
            "insights": []
        }
        
        if hot_topics:
            top_topic = hot_topics[0]
            brands_str = ", ".join(top_topic.get("brands", [])[:3])
            
            # 准备用于洞察生成的数据
            insight_data = {
                "trend_analysis": {
                    "top_topic": {
                        "title": top_topic.get('title', '热门话题'),
                        "heat_value": top_topic.get('heat_value', 0),
                        "brands": top_topic.get('brands', []),
                        "created_date": top_topic.get('created_date', '')
                    },
                    "all_topics": [
                        {
                            "title": topic.get('title', f'话题{i+1}'),
                            "heat_value": topic.get('heat_value', 0),
                            "brands": topic.get('brands', [])
                        } for i, topic in enumerate(hot_topics)
                    ]
                }
            }
            
            # 使用LLM生成数据驱动的洞察
            insight = self.generate_data_driven_insight(insight_data, "trend")
            
            result["insights"].append({
                "content": insight["content"],
                "data_support": {
                    "热门话题": top_topic.get('title', '热门话题'),
                    "热度值": top_topic.get('heat_value', 0),
                    "涉及品牌": top_topic.get('brands', [])
                },
                "user_quotes": user_quotes,
                "visualization": {
                    "chart_type": "热度条形图",
                    "topics": [topic.get("title", f"话题{i+1}") for i, topic in enumerate(hot_topics)],
                    "heat_values": [topic.get("heat_value", 0) for topic in hot_topics]
                },
                "hot_topics": hot_topics
            })
        
        # 保存结果到文件
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            output_path = os.path.join(self.output_dir, "trend_analysis.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result

class IPAnalyzer(BaseAnalyzer):
    """IP分析师，负责分析用户地理分布"""
    
    def __init__(self, output_dir: str = None):
        """
        初始化IP分析师
        
        Args:
            output_dir: 可选输出目录，用于保存分析结果
        """
        super().__init__(output_dir)
    
    def analyze_ip_distribution(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析用户地理分布情况，根据热度加权
        
        Args:
            data: 原始数据列表
            
        Returns:
            Dict[str, Any]: 地理分布分析结果
        """
        # 初始化地理数据统计
        location_heat = defaultdict(float)
        post_location_count = Counter()
        comment_location_count = Counter()
        
        # 收集地理数据和热度
        for item in data:
            # 处理发帖者位置
            location = item.get("location", "未知")
            if location and location != "未知":
                # 计算热度
                heat_value = calculate_content_heat(item)
                location_heat[location] += heat_value
                post_location_count[location] += 1
            
            # 处理评论者位置
            if "comments_data" in item and isinstance(item["comments_data"], list):
                for comment in item["comments_data"]:
                    comment_location = comment.get("comment_location", "未知")
                    if comment_location and comment_location != "未知":
                        # 计算评论热度
                        comment_heat = calculate_content_heat(comment, is_comment=True)
                        location_heat[comment_location] += comment_heat
                        comment_location_count[comment_location] += 1
        
        # 按热度排序获取前15个地区
        top_locations = sorted(location_heat.items(), key=lambda x: x[1], reverse=True)[:15]
        
        # 输出可视化数据
        visualization_data = [
            {"location": loc, "heat": heat, "post_count": post_location_count[loc], "comment_count": comment_location_count[loc]}
            for loc, heat in top_locations
        ]
        
        # 生成分析结果
        result = {
            "title": "用户地理分布分析",
            "insights": [
                {
                    "content": f"数据显示，{top_locations[0][0]}地区的用户互动热度最高，热度值达到{top_locations[0][1]:.1f}，其中包含{post_location_count[top_locations[0][0]]}条发帖和{comment_location_count[top_locations[0][0]]}条评论。",
                    "data_support": {
                        "热度最高地区": top_locations[0][0],
                        "热度值": top_locations[0][1],
                        "发帖数": post_location_count[top_locations[0][0]],
                        "评论数": comment_location_count[top_locations[0][0]]
                    },
                    "visualization": {
                        "chart_type": "柱状图",
                        "data": visualization_data
                    }
                }
            ]
        }
        
        # 保存结果到文件
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            output_path = os.path.join(self.output_dir, "ip_distribution_analysis.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result