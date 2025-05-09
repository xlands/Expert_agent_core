from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import os
import re
import json
from datetime import datetime
from src.tools.visualization_tools import VisualizationTools
from src.utils.logger import ExecutionLogger

@dataclass
class ReportTemplate:
    title: str
    sections: List[str]
    visualization_types: List[str]
    quote_types: List[str]

class ReportGenerator:
    """报告生成器，可以生成HTML格式的报告"""
    
    def __init__(self, logger=None):
        """初始化报告生成器
        
        Args:
            logger: 可选的日志记录器实例
        """
        self.output_dir = "reports"
        self.data_dir = None
        self.viz_tools = VisualizationTools()
        self.logger = logger
    
    def set_output_dir(self, output_dir: str):
        """设置输出目录

        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def set_data_dir(self, data_dir: str):
        """设置数据目录，用于读取子报告数据
        
        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def generate_report(self, sub_reports: List[Dict[str, Any]] = None, output_path: str = None) -> str:
        """根据子报告生成最终报告
        
        Args:
            sub_reports: 子报告列表，如果为None则从data_dir加载
            output_path: 输出路径，如果为None则使用时间戳命名
            
        Returns:
            str: 生成的报告文件路径
        """
        # 确保有输出路径
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"report_{timestamp}.html")
        
        # 如果传入了数据目录且未提供子报告，从数据目录加载子报告
        if self.data_dir and not sub_reports:
            self._log(f"从数据目录加载子报告: {self.data_dir}")
            sub_reports = self._load_reports_from_data_dir()
        
        if not sub_reports:
            self._log("未提供子报告数据，无法生成报告", level="error")
            return None
        
        # 生成图表
        self._log("生成数据可视化图表")
        self._generate_visualizations(sub_reports)
        
        # 生成HTML报告
        self._log("生成HTML格式报告")
        
        # 确保输出路径以.html结尾
        if not output_path.endswith(".html"):
            output_path = output_path.replace(".md", ".html")
            if not output_path.endswith(".html"):
                output_path = output_path + ".html"
        
        html_content = self._generate_html_template(
            self._get_report_title(sub_reports),
            datetime.now().strftime("%Y年%m月%d日"),
            self._extract_insights(sub_reports),
            sub_reports
        )
        
        # 写入HTML文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        self._log(f"HTML报告已生成: {output_path}")
        return output_path
    
    def _load_reports_from_data_dir(self) -> List[Dict[str, Any]]:
        """从数据目录加载所有子报告
        
        Returns:
            List[Dict[str, Any]]: 加载的子报告列表
        """
        sub_reports = []
        report_files = [
            "brand_mentions_analysis.json",
            "brand_sentiment_analysis.json",
            "competitor_analysis.json",
            "feature_analysis.json",
            "keyword_analysis.json",
            "trend_analysis.json",
        ]
        
        for report_file in report_files:
            report_path = os.path.join(self.data_dir, report_file)
            if os.path.exists(report_path):
                try:
                    with open(report_path, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                        sub_reports.append(report_data)
                        self._log(f"成功加载子报告: {report_file}")
                except Exception as e:
                    self._log(f"加载子报告出错: {report_file}, 错误: {str(e)}", level="error")
        
        return sub_reports
    
    def _extract_insights(self, reports: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """从报告中提取关键洞察
        
        Args:
            reports: 报告列表
        
        Returns:
            List[Dict[str, str]]: 洞察列表
        """
        all_insights = []
        for report in reports:
            if "insights" in report and len(report["insights"]) > 0:
                for insight in report["insights"]:
                    if isinstance(insight, dict) and "content" in insight:
                        all_insights.append({
                            "title": report.get("title", ""),
                            "content": insight["content"]
                        })
        return all_insights
    
    def _get_report_title(self, reports: List[Dict[str, Any]]) -> str:
        """从报告中获取标题
        
        Args:
            reports: 报告列表
        
        Returns:
            str: 报告标题
        """
        # 默认标题
        title = "社交媒体分析报告"
        
        # 尝试从第一个报告中获取标题相关信息
        if reports and len(reports) > 0:
            first_report = reports[0]
            if "brand" in first_report:
                brand = first_report["brand"]
                title = f"{brand} 品牌分析报告"
            
            # 也可以从洞察中提取品牌名称
            elif "insights" in first_report and len(first_report["insights"]) > 0:
                content = first_report["insights"][0].get("content", "")
                brand_match = re.search(r'「([^」]+)」|"([^"]+)"|\'([^\']+)\'|(\w+)品牌', content)
                if brand_match:
                    brand = next(group for group in brand_match.groups() if group)
                    title = f"{brand} 品牌分析报告"
        
        return title

    def format_user_quotes(self, quotes: List[Dict[str, str]], limit: int = 5) -> List[Dict[str, str]]:
        """格式化用户原声引用

        Args:
            quotes: 原始用户评论数据
            limit: 限制条数

        Returns:
            List[Dict[str, str]]: 格式化后的用户原声
        """
        if not quotes:
            return []
        
        formatted_quotes = []
        
        for quote in quotes[:limit]:
            formatted_quote = {
                "title": quote.get("title", "无标题")[:30],
                "content": quote.get("content", "")[:100],
                "brands": ", ".join(quote.get("brands", []))
            }
            formatted_quotes.append(formatted_quote)
        
        return formatted_quotes
        
    def _generate_visualizations(self, sub_reports: List[Dict[str, Any]]) -> None:
        """根据子报告生成可视化图表
        
        Args:
            sub_reports: 所有子报告
        """
        for report in sub_reports:
            title = report.get("title", "")
            if not title:
                continue
                
            insights = report.get("insights", [])
            if not insights:
                continue
            
            # 处理所有洞察里的可视化数据
            for insight in insights:
                viz = insight.get("visualization", {})
                if not viz:
                    continue
                    
                chart_type = viz.get("chart_type", "")
                if not chart_type:
                    continue
                
                try:
                    # 根据图表类型生成相应的图表
                    if "网络图" in chart_type and "nodes" in viz and "links" in viz:
                        chart_file = f"network_chart_{title.replace(' ', '_')}.png"
                        chart_path = self.viz_tools.generate_network_chart(
                            viz.get("nodes", []),
                            viz.get("links", []),
                            title,
                            chart_file,
                            self.output_dir
                        )
                        if chart_path:
                            viz["chart_file"] = chart_file
                        
                    elif "雷达图" in chart_type and "dimensions" in viz and "brands" in viz and "scores" in viz:
                        chart_file = f"radar_chart_{title.replace(' ', '_')}.png"
                        chart_path = self.viz_tools.generate_radar_chart(
                            viz.get("dimensions", []),
                            viz.get("brands", []),
                            viz.get("scores", []),
                            title,
                            chart_file,
                            self.output_dir
                        )
                        if chart_path:
                            viz["chart_file"] = chart_file
                    
                    elif "词云图" in chart_type and "words" in viz:
                        sentiment = viz.get("sentiment", "")
                        sentiment_suffix = f"_{sentiment}" if sentiment else ""
                        chart_file = f"wordcloud{sentiment_suffix}_{title.replace(' ', '_')}.png"
                        
                        chart_path = self.viz_tools.generate_word_cloud(
                            viz.get("words", []),
                            f"{title} - {sentiment}评价词云" if sentiment else title,
                            chart_file,
                            self.output_dir
                        )
                        if chart_path:
                            viz["chart_file"] = chart_file
                    
                    elif "柱状图" in chart_type and "brands" in viz and "percentages" in viz:
                        chart_file = f"bar_chart_{title.replace(' ', '_')}.png"
                        chart_path = self.viz_tools.generate_bar_chart(
                            viz.get("brands", []),
                            viz.get("percentages", []),
                            title,
                            chart_file,
                            self.output_dir,
                            y_label="占比(%)"
                        )
                        if chart_path:
                            viz["chart_file"] = chart_file
                    
                    elif "堆叠柱状图" in chart_type and "brands" in viz:
                        chart_file = f"stacked_bar_{title.replace(' ', '_')}.png"
                        # 提取数据系列
                        data_series = []
                        series_names = []
                        
                        if "positive" in viz and "neutral" in viz and "negative" in viz:
                            data_series.extend([
                                viz.get("positive", []),
                                viz.get("neutral", []),
                                viz.get("negative", [])
                            ])
                            series_names.extend(["正面", "中性", "负面"])
                        
                        if data_series and series_names:
                            chart_path = self.viz_tools.generate_stacked_bar_chart(
                                viz.get("brands", []),
                                data_series,
                                series_names,
                                title,
                                chart_file,
                                self.output_dir,
                                y_label="情感分布(%)"
                            )
                            if chart_path:
                                viz["chart_file"] = chart_file
                    
                    elif "热度" in chart_type and "posts" in viz and "heat_values" in viz:
                        chart_file = f"heat_bar_{title.replace(' ', '_')}.png"
                        chart_path = self.viz_tools.generate_heat_bar_chart(
                            viz.get("posts", []),
                            viz.get("heat_values", []),
                            title,
                            chart_file,
                            self.output_dir,
                            y_label="热度值"
                        )
                        if chart_path:
                            viz["chart_file"] = chart_file
                
                except Exception as e:
                    self._log(f"生成图表失败: {chart_type}, 错误: {str(e)}", level="error")
    
    def _log(self, message: str, level: str = "debug"):
        """内部日志记录方法
        
        Args:
            message: 日志消息
            level: 日志级别，可以是"debug", "info", "error"等
        """
        if self.logger:
            if level == "debug":
                self.logger.log_debug(message)
            elif level == "error":
                self.logger.log_error(message)
            else:
                self.logger.log_custom(message)
        elif level == "error":
            # 只有错误级别的日志在没有logger时才打印到控制台
            print(f"ERROR: {message}")
    
    def _generate_html_template(self, title: str, date: str, insights: List[Dict[str, str]], 
                             reports: List[Dict[str, Any]]) -> str:
        """生成HTML模板
        
        Args:
            title: 报告标题
            date: 报告日期
            insights: 关键洞察列表
            reports: 子报告数据
            
        Returns:
            str: HTML内容
        """
        try:
            # 构建洞察HTML
            insights_html = ""
            for insight in insights[:5]:
                insights_html += f"""
                <div class="insight-card">
                    <h3>{insight.get("title", "")}</h3>
                    <p>{insight.get("content", "")}</p>
                </div>
                """
            
            # 构建报告部分HTML
            reports_html = ""
            for report in reports:
                report_title = report.get("title", "")
                content = ""
                if "insights" in report and report["insights"] and "content" in report["insights"][0]:
                    content = report["insights"][0]["content"]
                
                # 检查是否有图表
                chart_html = ""
                for insight in report.get("insights", []):
                    if "visualization" in insight and "chart_file" in insight["visualization"]:
                        chart_file = insight["visualization"]["chart_file"]
                        if isinstance(chart_file, str) and os.path.exists(os.path.join(self.output_dir, chart_file)):
                            chart_html += f'<div class="chart"><img src="{chart_file}" alt="{report_title}图表"></div>'
                
                # 获取用户原声 - 根据不同的报告类型生成不同的用户原声格式
                quotes_html = self._generate_user_quotes_html(report)
                
                reports_html += f"""
                <div class="report-section">
                    <h2>{report_title}</h2>
                    <div class="content">
                        <p>{content}</p>
                        {chart_html}
                        {quotes_html}
                    </div>
                </div>
                """
            
            # 基本HTML模板
            html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', 'SimHei', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        header {{
            background-color: #1e50a2;
            color: white;
            padding: 20px 0;
            text-align: center;
            margin-bottom: 30px;
        }}
        h1, h2, h3 {{
            margin-top: 0;
        }}
        .report-date {{
            font-size: 0.9em;
            color: #ccc;
            margin-top: 5px;
        }}
        .insights-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .insight-card {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 20px;
            flex: 1 0 calc(33.333% - 20px);
            min-width: 300px;
        }}
        .insight-card h3 {{
            color: #1e50a2;
            margin-bottom: 10px;
            font-size: 1.2em;
        }}
        .report-section {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 25px;
            margin-bottom: 30px;
        }}
        .report-section h2 {{
            color: #1e50a2;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
            margin-bottom: 20px;
        }}
        .chart {{
            margin: 20px 0;
            text-align: center;
        }}
        .chart img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .user-quotes {{
            background-color: #f5f5f5;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
        }}
        .user-quotes h4 {{
            margin-top: 0;
            color: #555;
        }}
        .quote {{
            padding: 15px;
            margin-bottom: 15px;
            border-left: 3px solid #1e50a2;
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .quote:last-child {{
            margin-bottom: 0;
        }}
        .quote p {{
            margin: 0 0 10px 0;
            font-style: italic;
        }}
        .quote-meta {{
            display: flex;
            align-items: center;
            font-size: 0.9em;
            color: #666;
        }}
        .quote-meta .source {{
            margin-right: 15px;
        }}
        .quote-meta .stats {{
            display: flex;
            align-items: center;
        }}
        .quote-meta .stats span {{
            margin-right: 15px;
            display: flex;
            align-items: center;
        }}
        .quote-meta .link {{
            color: #1e50a2;
            text-decoration: none;
            margin-left: auto;
        }}
        .quote-meta .link:hover {{
            text-decoration: underline;
        }}
        .quote-emotion {{
            margin-right: 5px;
        }}
        footer {{
            text-align: center;
            padding: 20px;
            color: #777;
            font-size: 0.9em;
        }}
        @media (max-width: 768px) {{
            .insight-card {{
                flex: 1 0 100%;
            }}
            .quote-meta {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .quote-meta .stats {{
                margin-top: 5px;
            }}
            .quote-meta .link {{
                margin-top: 5px;
                margin-left: 0;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>{title}</h1>
            <div class="report-date">生成日期: {date}</div>
        </div>
    </header>
    
    <div class="container">
        <h2>关键洞察</h2>
        <div class="insights-container">
            {insights_html}
        </div>
        
        {reports_html}
    </div>
    
    <footer>
        <div class="container">
            <p>© {date[:4]} 社媒分析报告系统</p>
        </div>
    </footer>
</body>
</html>"""
            
            self._log("HTML内容生成成功")
            return html_content
            
        except Exception as e:
            self._log(f"生成HTML模板失败: {str(e)}", level="error")
            # 返回一个最简单的HTML
            return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1, h2 {{ color: #333; }}
        .section {{ background: #f5f5f5; padding: 15px; margin-bottom: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p>生成日期: {date}</p>
        <div class="section">
            <h2>报告生成失败</h2>
            <p>在生成报告时发生错误: {str(e)}</p>
        </div>
    </div>
</body>
</html>"""

    def _generate_user_quotes_html(self, report: Dict[str, Any]) -> str:
        """根据报告类型生成用户原声HTML
        
        Args:
            report: 报告数据
            
        Returns:
            str: 用户原声HTML代码
        """
        report_title = report.get("title", "").lower()
        quotes_html = ""
        
        user_quotes = []
        for insight in report.get("insights", []):
            if "user_quotes" in insight and insight["user_quotes"]:
                user_quotes = insight["user_quotes"]
                break
        
        if not user_quotes:
            return ""
            
        quotes_html = "<div class='user-quotes'><h4>用户原声</h4>"
        
        # 品牌情感分析模块 - 带有情感图标
        if "情感分析" in report_title:
            for i, quote in enumerate(user_quotes[:3]):
                if not isinstance(quote, dict):
                    continue
                
                content = quote.get("content", "")
                brand = quote.get("brand", "")
                platform = quote.get("url", "").split('/')[2] if quote.get("url", "") else "社交平台"
                likes = quote.get("heat_value", 0) or 0
                reply_count = quote.get("reply_count", 0) or 0
                
                # 根据内容确定是正面还是负面评价 (简单判断，实际应由数据提供)
                is_positive = True
                if i == len(user_quotes) - 1:  # 最后一条假设为负面
                    is_positive = False
                    
                emoji = "😀" if is_positive else "😔"
                
                quotes_html += f"""
                <div class='quote'>
                    <p><span class="quote-emotion">{emoji}</span> "{content}"</p>
                    <div class="quote-meta">
                        <span class="source">来自{platform}</span>
                        <div class="stats">
                            <span>👍 {likes//1000 if likes > 1000 else likes}{"k" if likes > 1000 else ""}</span>
                            <span>💬 {reply_count}条回复</span>
                        </div>
                    </div>
                </div>"""

        # 竞争品牌分析模块
        elif "竞争" in report_title:
            for quote in user_quotes[:3]:
                if not isinstance(quote, dict):
                    continue
                    
                content = quote.get("content", "")
                brands = quote.get("brands", [])
                brands_str = " vs ".join(brands) if brands else quote.get("brand", "")
                platform = quote.get("url", "").split('/')[2] if quote.get("url", "") else "社交平台"
                likes = quote.get("heat_value", 0) or 0
                quote_type = quote.get("type", "")
                
                quotes_html += f"""
                <div class='quote'>
                    <p>"{content}"</p>
                    <div class="quote-meta">
                        <span class="source">来自{platform}</span>
                        <div class="stats">
                            <span>👍 {likes//1000 if likes > 1000 else likes}{"k" if likes > 1000 else ""}</span>
                            <span>涉及品牌: {brands_str}</span>
                            {f'<span>{quote_type}</span>' if quote_type else ''}
                        </div>
                    </div>
                </div>"""
                
        # 产品特征分析模块
        elif "特征" in report_title:
            for quote in user_quotes[:3]:
                if not isinstance(quote, dict):
                    continue
                    
                content = quote.get("content", "")
                brand = quote.get("brand", "")
                dimension = quote.get("dimension", "")
                platform = quote.get("url", "").split('/')[2] if quote.get("url", "") else "社交平台"
                likes = quote.get("heat_value", 0) or 0
                
                quotes_html += f"""
                <div class='quote'>
                    <p>🔍 {dimension if dimension else "特征"}: "{content}"</p>
                    <div class="quote-meta">
                        <span class="source">来自{platform}</span>
                        <div class="stats">
                            <span>👍 {likes//1000 if likes > 1000 else likes}{"k" if likes > 1000 else ""}</span>
                            <span>品牌: {brand}</span>
                        </div>
                    </div>
                </div>"""
                
        # 关键词分析模块
        elif "关键词" in report_title:
            for quote in user_quotes[:3]:
                if not isinstance(quote, dict):
                    continue
                    
                content = quote.get("content", "")
                keyword = quote.get("keyword", "")
                sentiment = quote.get("sentiment", "")
                platform = quote.get("url", "").split('/')[2] if quote.get("url", "") else "社交平台"
                url = quote.get("url", "#")
                
                quotes_html += f"""
                <div class='quote'>
                    <p>关于"{keyword}"的讨论:</p>
                    <p>"{content}"</p>
                    <div class="quote-meta">
                        <span class="source">来自{platform}</span>
                        <div class="stats">
                            <span>{sentiment}评价</span>
                        </div>
                        {f'<a href="{url}" class="link" target="_blank">点击查看原文</a>' if url != "#" else ''}
                    </div>
                </div>"""
                
        # 行业热点分析模块
        elif "热点" in report_title or "趋势" in report_title:
            for quote in user_quotes[:3]:
                if not isinstance(quote, dict):
                    continue
                    
                content = quote.get("content", "")
                title = quote.get("title", "")
                platform = quote.get("url", "").split('/')[2] if quote.get("url", "") else "社交平台"
                url = quote.get("url", "#")
                heat_value = quote.get("heat_value", 0) or 0
                
                quotes_html += f"""
                <div class='quote'>
                    <p>"{content}"</p>
                    <div class="quote-meta">
                        <span class="source">来自{platform}</span>
                        <div class="stats">
                            <span>🔥 热度值: {heat_value}</span>
                            {f'<span>标题: {title}</span>' if title else ''}
                        </div>
                        {f'<a href="{url}" class="link" target="_blank">点击查看原文</a>' if url != "#" else ''}
                    </div>
                </div>"""
                
        # 通用格式 - 品牌声量等其他报告
        else:
            for quote in user_quotes[:3]:
                if not isinstance(quote, dict):
                    continue
                    
                content = quote.get("content", "")
                brand = quote.get("brand", "")
                platform = quote.get("url", "").split('/')[2] if quote.get("url", "") else "社交平台"
                url = quote.get("url", "#")
                likes = quote.get("heat_value", 0) or 0
                
                quotes_html += f"""
                <div class='quote'>
                    <p>"{content}"</p>
                    <div class="quote-meta">
                        <span class="source">来自{platform}</span>
                        <div class="stats">
                            <span>👍 {likes//1000 if likes > 1000 else likes}{"k" if likes > 1000 else ""}</span>
                            {f'<span>品牌: {brand}</span>' if brand else ''}
                        </div>
                        {f'<a href="{url}" class="link" target="_blank">点击查看原文</a>' if url != "#" else ''}
                    </div>
                </div>"""
                
        quotes_html += "</div>"
        return quotes_html