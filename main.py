import json
import os
import traceback
from datetime import datetime
from pathlib import Path
import matplotlib
import platform
import pandas as pd
import glob

from src.tools.atomic_insights import atomic_insights
from src.llm import LLM
from prompt.report import query_rewrite, report_generation, competitive_product_analysis
from src.agent.query_rewriter import QueryRewriter
from src.utils.logger import create_logger, create_output_directory
from src.tools.deep_retail import DeepRetail
from src.agent.analyzer.analyzers import (
    BrandAnalyzer,
    CompetitorAnalyzer,
    FeatureAnalyzer,
    KeywordAnalyzer,
    TrendAnalyzer,
    IPAnalyzer,
)
from src.agent.report_generator import ReportGenerator, ReportLLMGenerator

# 设置matplotlib字体，根据操作系统选择合适的字体
system = platform.system()
if system == 'Windows':
    matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun']
elif system == 'Darwin':  # macOS
    matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
else:  # Linux或其他
    matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'WenQuanYi Zen Hei', 'WenQuanYi Micro Hei']
matplotlib.rcParams['axes.unicode_minus'] = False

def main():
    # 0. 初始化查询和输出目录
    query = "帮我做一下小米汽车的竞品分析"
    # query = "马登工装"
    output_dir = create_output_directory(query)
    
    # 初始化日志记录器，使用默认log_dir参数即可
    logger = create_logger(query, log_dir=os.path.join(output_dir, "logs"))
    logger.log_custom(f"输出目录创建完成: {output_dir}")
    
    # # 1. 任务编排
    # pass
    
    # # 2. 查询重写
    # query_rewrite_start = logger.log_step_start("查询重写")
    # query_rewriter = QueryRewriter()
    # structured_query = query_rewriter.query_rewrite(query)
    # logger.log_step_result(query_rewrite_start, "查询已重写为结构化格式", structured_query)
    
    # # 3. 生成搜索关键词
    # keywords_start = logger.log_step_start("关键词生成")
    # platform_keywords = query_rewriter.generate_keywords(structured_query)
    # logger.log_step_result(keywords_start, "已生成各平台搜索关键词", platform_keywords)
    
    # # 4. 根据关键词从社媒爬取数据
    # deep_retail = DeepRetail()
    # data = deep_retail.fetch_data(platform_keywords)
    # logger.log_step_result("数据爬取", "已从本地文件夹读取爬虫结果", data)
    
    # # 5. 解析原子数据
    # input_csv = ['data/帮我做一下小米汽车的竞品分析/新能源汽车推荐.csv','data/帮我做一下小米汽车的竞品分析/新能源汽车推荐_新能源汽车推荐.csv']
    # output_json = os.path.join(output_dir, "data", "竞品分析结果.json")
    # data_parse_start = logger.log_step_start("数据解析")
    # logger.log_file_input(input_csv)
    
    # result_data = atomic_insights(input_csv, output_json, model_id='doubao-lite')
    # logger.log_data_count(result_data)
    # logger.log_data_sample(result_data)
    # logger.log_step_result(data_parse_start, "数据解析完成")

    # 6. 生成子报告
    result_data = json.load(open('data/帮我做一下小米汽车的竞品分析/竞品分析结果.json', 'r'))
    reports_dir = os.path.join(output_dir, "reports")
    data_dir = os.path.join(output_dir, "data")
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    sub_reports_start = logger.log_step_start("子报告生成")
    logger.log_custom("开始生成分析子报告")
    
    # 初始化各种分析器
    logger.log_custom("初始化分析器...")
    brand_analyzer = BrandAnalyzer(output_dir=data_dir)
    competitor_analyzer = CompetitorAnalyzer(output_dir=data_dir)
    feature_analyzer = FeatureAnalyzer(output_dir=data_dir)
    keyword_analyzer = KeywordAnalyzer(output_dir=data_dir)
    trend_analyzer = TrendAnalyzer(output_dir=data_dir)
    ip_analyzer = IPAnalyzer(output_dir=data_dir)
    logger.log_custom("所有分析器初始化完成")
    
    # 生成各个子报告
    sub_reports = []
    
    # 品牌声量分析
    logger.log_custom("\n=== 开始品牌声量分析 ===")
    logger.log_custom("思考过程：分析品牌在评论中的提及频次，识别最受关注的品牌")
    brand_mentions_start = logger.log_step_start("品牌声量分析")
    brand_mentions_report = brand_analyzer.analyze_brand_mentions(result_data)
    brand_mentions_time = logger.log_step_result(brand_mentions_start, 
                                               f"发现洞察：{brand_mentions_report['insights'][0]['content'] if brand_mentions_report['insights'] else '无洞察'}")
    sub_reports.append(brand_mentions_report)
    
    # 品牌情感分析
    logger.log_custom("\n=== 开始品牌情感分析 ===")
    logger.log_custom("思考过程：分析用户对各品牌的情感倾向，计算正面、中性、负面评价的比例")
    brand_sentiment_start = logger.log_step_start("品牌情感分析")
    brand_sentiment_report = brand_analyzer.analyze_brand_sentiment(result_data)
    brand_sentiment_time = logger.log_step_result(brand_sentiment_start, 
                                                f"发现洞察：{brand_sentiment_report['insights'][0]['content'] if brand_sentiment_report['insights'] else '无洞察'}")
    sub_reports.append(brand_sentiment_report)
    
    # 竞品分析
    logger.log_custom("\n=== 开始竞品分析 ===")
    logger.log_custom("思考过程：分析品牌间的竞争关系，识别主要竞争对手和竞争类型")
    competitor_start = logger.log_step_start("竞品分析")
    competitor_report = competitor_analyzer.analyze_competitor_relationships(result_data)
    competitor_time = logger.log_step_result(competitor_start, 
                                           f"发现洞察：{competitor_report['insights'][0]['content'] if competitor_report['insights'] else '无洞察'}")
    sub_reports.append(competitor_report)
    
    # 产品特征分析
    logger.log_custom("\n=== 开始产品特征分析 ===")
    logger.log_custom("思考过程：分析用户关注的产品维度，评估各品牌在不同维度的表现")
    feature_start = logger.log_step_start("产品特征分析")
    feature_report = feature_analyzer.analyze_product_features(result_data)
    feature_time = logger.log_step_result(feature_start, 
                                        f"发现洞察：{feature_report['insights'][0]['content'] if feature_report['insights'] else '无洞察'}")
    sub_reports.append(feature_report)
    
    # 关键词分析
    logger.log_custom("\n=== 开始关键词分析 ===")
    logger.log_custom("思考过程：提取用户讨论中的高频关键词，分析品牌特色和用户关注点")
    keyword_start = logger.log_step_start("关键词分析")
    keyword_report = keyword_analyzer.analyze_keywords(result_data)
    keyword_time = logger.log_step_result(keyword_start, 
                                        f"发现洞察：{keyword_report['insights'][0]['content'] if keyword_report['insights'] else '无洞察'}")
    sub_reports.append(keyword_report)
    
    # 趋势分析
    logger.log_custom("\n=== 开始趋势分析 ===")
    logger.log_custom("思考过程：分析行业热点话题和发展趋势，获取热门讨论帖子")
    trend_start = logger.log_step_start("趋势分析")
    trend_report = trend_analyzer.analyze_trends(result_data)
    trend_time = logger.log_step_result(trend_start, 
                                      f"发现洞察：{trend_report['insights'][0]['content'] if trend_report['insights'] else '无洞察'}")
    sub_reports.append(trend_report)
    
    # IP分布分析
    logger.log_custom("\n=== 开始用户地理分布分析 ===")
    logger.log_custom("思考过程：分析用户地理分布情况，识别不同地区的用户活跃度和品牌偏好")
    ip_start = logger.log_step_start("用户地理分布分析")
    ip_report = ip_analyzer.analyze_ip_distribution(result_data)
    ip_time = logger.log_step_result(ip_start, 
                                  f"发现洞察：{ip_report['insights'][0]['content'] if ip_report['insights'] else '无洞察'}")
    sub_reports.append(ip_report)
    
    # 记录总体执行情况
    logger.log_custom("\n=== 子报告生成统计 ===")
    
    # 记录生成的子报告信息
    report_files = [
        "brand_mentions_analysis.json",
        "brand_sentiment_analysis.json",
        "competitor_analysis.json",
        "feature_analysis.json",
        "keyword_analysis.json",
        "trend_analysis.json",
        "ip_distribution_analysis.json",
    ]
    logger.log_custom("\n=== 子报告文件生成情况 ===")
    for filename in report_files:
        report_path = os.path.join(data_dir, filename)
        if os.path.exists(report_path):
            file_size = os.path.getsize(report_path) / 1024  # 转换为KB
            with open(report_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                insight_count = len(content.get("insights", []))
            logger.log_custom(f"- {filename}：{file_size:.1f}KB，包含{insight_count}个洞察")
    
    logger.log_step_result(sub_reports_start, f"子报告生成完成，共生成 {len(sub_reports)} 个子报告")
    
    # 7. 生成总报告
    report_start = logger.log_step_start("总报告生成")
    logger.log_custom("\n=== 开始生成总报告 ===")
    logger.log_custom("思考过程：整合所有子报告的洞察，生成完整的分析报告")
    
    # 使用报告生成器生成最终报告
    report_generator = ReportLLMGenerator(logger=logger)
    report_generator.set_output_dir(os.path.join(output_dir, "reports"))
    report_generator.set_data_dir(os.path.join(output_dir, "data"))
    final_report_path = os.path.join(output_dir, "reports", "final_report.html")

    # 从data_dir读取子报告数据，不再传递sub_reports参数
    report_generator.generate_report([], final_report_path)
    logger.log_file_output(final_report_path)
    
    logger.log_step_result(report_start, f"总报告生成完成")
    
    # 完成记录，保存日志
    log_file, total_time = logger.finalize()
    print(f"执行日志已保存到: {log_file}")
    print(f"总耗时：{total_time:.2f}秒")
    print(f"所有输出文件保存在: {output_dir}")

if __name__ == '__main__':
    main()