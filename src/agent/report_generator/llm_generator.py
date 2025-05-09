import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import base64
from datetime import datetime
from src.llm import LLM

class ReportLLMGenerator:
    """LLM报告生成器，使用大模型生成HTML报告"""
    
    def __init__(self, model: str = "deepseek-v3", logger=None):
        """初始化LLM报告生成器
        
        Args:
            model: 使用的LLM模型
            logger: 日志记录器实例(可选)
        """
        self.llm = LLM(model=model)
        self.data_dir = None
        self.output_dir = "reports"
        self.report_name = "分析报告"
        self.logger = logger
        
    def set_output_dir(self, output_dir: str):
        """设置输出目录
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def set_data_dir(self, data_dir: str):
        """设置数据目录，用于读取JSON数据
        
        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = data_dir
        
    def set_report_name(self, report_name: str):
        """设置报告名称
        
        Args:
            report_name: 报告名称
        """
        self.report_name = report_name
    
    def load_json_data(self, filename: str) -> Dict:
        """加载JSON数据
        
        Args:
            filename: JSON文件名
            
        Returns:
            Dict: 加载的JSON数据
        """
        try:
            file_path = os.path.join(self.data_dir, filename)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"文件不存在: {file_path}")
                return {}
        except Exception as e:
            print(f"加载JSON数据出错: {str(e)}")
            return {}
    
    def load_all_data(self) -> Dict[str, Dict]:
        """加载所有JSON数据文件
        
        Returns:
            Dict[str, Dict]: 所有JSON数据的字典
        """
        return {
            "brand_mentions": self.load_json_data("brand_mentions_analysis.json"),
            "brand_sentiment": self.load_json_data("brand_sentiment_analysis.json"),
            "competitor": self.load_json_data("competitor_analysis.json"),
            "feature": self.load_json_data("feature_analysis.json"),
            "keyword": self.load_json_data("keyword_analysis.json"),
            "trend": self.load_json_data("trend_analysis.json"),
            "ip_distribution": self.load_json_data("ip_distribution_analysis.json")
        }
    
    def generate_report(self, sub_reports: Optional[List[Dict]] = None, output_path: Optional[str] = None) -> str:
        """生成完整的HTML报告
        
        Args:
            sub_reports: 子报告列表(不使用)
            output_path: 输出文件路径，如果为None则自动生成
            
        Returns:
            str: 生成的报告路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"report_{timestamp}.html")
        
        if self.logger:
            self.logger.log_custom(f"开始生成 {self.report_name}...")
        else:
            print(f"正在生成 {self.report_name}...")
        
        # 加载所有数据
        data = self.load_all_data()
        if not any(data.values()):
            if self.logger:
                self.logger.log_custom("无法加载数据，生成报告失败")
            else:
                print("无法加载数据，生成报告失败")
            return None
            
        # 生成报告各部分内容
        css_styles = self.get_css_styles()
        
        # 开始生成HTML内容
        with open(output_path, 'w', encoding='utf-8') as f:
            # 写入HTML头部
            html_head = f"""
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{self.report_name}</title>
                <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/echarts-wordcloud@2.1.0/dist/echarts-wordcloud.min.js"></script>
                <style>{css_styles}</style>
            </head>
            <body>
                <div class="report-container">
                    <div class="report-header">
                        <h1>{self.report_name}</h1>
                        <p class="report-date">生成日期：{datetime.now().strftime("%Y年%m月%d日")}</p>
                    </div>
            """
            f.write(html_head)
            
            # 生成各个模块
            for module_name, generator_func, module_data in [
                ("执行摘要", self.generate_executive_summary, data),
                ("品牌对比分析", self.generate_brand_comparison, data["brand_mentions"]),
                ("品牌情感分析", self.generate_brand_sentiment, data["brand_sentiment"]),
                ("行业趋势分析", self.generate_trend_analysis, data["trend"]),
                ("竞争分析", self.generate_competitor_analysis, data["competitor"]),
                ("特征分析", self.generate_feature_analysis, data["feature"]),
                ("关键词分析", self.generate_keyword_analysis, data["keyword"]),
                ("用户地理分布分析", self.generate_ip_distribution_analysis, data["ip_distribution"]),
                ("优化建议", self.generate_optimization_suggestions, data)
            ]:
                if self.logger:
                    module_start = self.logger.log_step_start(f"生成{module_name}")
                
                # 获取生成内容的迭代器
                content_iter = generator_func(module_data)
                
                # 对于非生成器函数，直接写入内容
                if not hasattr(content_iter, '__iter__') or hasattr(content_iter, '__len__'):
                    f.write(content_iter)
                    
                    if self.logger:
                        self.logger.log_step_result(module_start, f"{module_name}生成完成")
                    else:
                        print(f"{module_name}生成完成")
                    continue
                
                # 处理生成器函数，逐块写入内容
                for chunk in content_iter:
                    f.write(chunk)
                    f.flush()  # 确保内容立即写入文件
                
                if self.logger:
                    self.logger.log_step_result(module_start, f"{module_name}生成完成")
                else:
                    print(f"{module_name}生成完成")
            
            # 写入HTML尾部
            html_footer = """
                    <div class="report-footer">
                        <p>© """ + str(datetime.now().year) + """ Cotex AI | 数据分析报告</p>
                    </div>
                </div>
                
                <script>
                document.addEventListener('DOMContentLoaded', function() {
                    const chartContainers = document.querySelectorAll('[data-chart]');
                    chartContainers.forEach(container => {
                        const chartId = container.getAttribute('id');
                        const chartConfig = container.getAttribute('data-chart');
                        if (chartConfig && chartId) {
                            try {
                                const config = JSON.parse(chartConfig);
                                const chart = echarts.init(document.getElementById(chartId));
                                chart.setOption(config);
                                window.addEventListener('resize', function() {
                                    chart.resize();
                                });
                            } catch (e) {
                                console.error('初始化图表出错:', e);
                            }
                        }
                    });
                });
                </script>
            </body>
            </html>
            """
            f.write(html_footer)
        
        if self.logger:
            self.logger.log_custom(f"报告已生成: {output_path}")
            self.logger.log_file_output(output_path)
        else:
            print(f"报告已生成: {output_path}")
            
        return output_path
    
    def generate_report_stream(self, output_path: Optional[str] = None):
        """生成完整的HTML报告（流式输出版）
        
        Args:
            output_path: 输出文件路径，如果为None则自动生成
            
        Yields:
            str: 生成的报告片段
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"report_{timestamp}.html")
        
        # 生成HTML头部
        css_styles = self.get_css_styles()
        html_head = f"""<!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{self.report_name}</title>
            <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/echarts-wordcloud@2.1.0/dist/echarts-wordcloud.min.js"></script>
            <style>{css_styles}</style>
        </head>
        <body>
            <div class="report-container">
                <div class="report-header">
                    <h1>{self.report_name}</h1>
                    <p class="report-date">生成日期：{datetime.now().strftime("%Y年%m月%d日")}</p>
                </div>"""
        
        yield html_head
        full_html = html_head
        
        # 生成各个模块
        data = self.load_all_data()
        
        for module_name, generator_func, module_data in [
            ("执行摘要", self.generate_executive_summary, data),
            ("品牌对比分析", self.generate_brand_comparison, data["brand_mentions"]),
            ("品牌情感分析", self.generate_brand_sentiment, data["brand_sentiment"]),
            ("行业趋势分析", self.generate_trend_analysis, data["trend"]),
            ("竞争分析", self.generate_competitor_analysis, data["competitor"]),
            ("特征分析", self.generate_feature_analysis, data["feature"]),
            ("关键词分析", self.generate_keyword_analysis, data["keyword"]),
            ("用户地理分布分析", self.generate_ip_distribution_analysis, data["ip_distribution"]),
            ("优化建议", self.generate_optimization_suggestions, data)
        ]:
            print(f"生成{module_name}...")
            module_content = generator_func(module_data)
            yield module_content
            full_html += module_content
        
        # HTML尾部
        html_footer = """
                <div class="report-footer">
                    <p>© """ + str(datetime.now().year) + """ Cotex AI | 数据分析报告</p>
                </div>
            </div>
            
            <script>
            document.addEventListener('DOMContentLoaded', function() {
                const chartContainers = document.querySelectorAll('[data-chart]');
                chartContainers.forEach(container => {
                    const chartId = container.getAttribute('id');
                    const chartConfig = container.getAttribute('data-chart');
                    if (chartConfig && chartId) {
                        try {
                            const config = JSON.parse(chartConfig);
                            const chart = echarts.init(document.getElementById(chartId));
                            chart.setOption(config);
                            window.addEventListener('resize', function() {
                                chart.resize();
                            });
                        } catch (e) {
                            console.error('初始化图表出错:', e);
                        }
                    }
                });
            });
            </script>
        </body>
        </html>"""
        
        yield html_footer
        full_html += html_footer
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        
        print(f"报告已生成: {output_path}")
    
    def _generate_with_stream(self, prompt: str):
        """辅助方法：根据当前流式状态生成内容
        
        Args:
            prompt: 提示词
            
        Returns:
            str或生成器: 根据流式状态返回字符串或内容生成器
        """
        # 在提示词末尾添加不要使用Markdown格式的指示
        prompt += """

重要：直接返回原始HTML代码，不要使用Markdown格式（如```html），不要使用任何代码块标记。
"""
        
        # 将 prompt 包装成正确的 messages 格式
        llm_messages = [{"role": "user", "content": prompt}]

        # 处理流式生成请求
        try:
            # 直接使用非流式模式，新版API不支持直接设置stream属性
            # 传递包装好的 llm_messages 列表给 messages 参数
            return self.llm.generate(messages=llm_messages)
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"生成内容失败: {str(e)}")
            else:
                print(f"生成内容失败: {str(e)}")
            return f"<div class='error'>生成内容失败: {str(e)}</div>"
    
    def _clean_stream_content(self, content_stream):
        """处理流式生成内容
        
        Args:
            content_stream: 内容生成器
            
        Yields:
            str: 处理后的内容片段
        """
        try:
            for chunk in content_stream:
                delta = chunk.choices[0].delta if hasattr(chunk, 'choices') and chunk.choices else None
                content = delta.content if delta and hasattr(delta, 'content') else ""
                if content:
                    yield content
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"流式处理失败: {str(e)}")
            else:
                print(f"流式处理失败: {str(e)}")
            yield f"<div class='error'>流式处理失败: {str(e)}</div>"
    
    def generate_executive_summary(self, all_data: Dict[str, Dict]) -> str:
        """生成执行摘要模块
        
        Args:
            all_data: 所有数据
            
        Returns:
            str: 执行摘要HTML内容
        """
        prompt = f"""
        请根据以下数据，生成分析报告的执行摘要模块HTML内容：
        
        报告名称：{self.report_name}
        
        数据概览：
        {json.dumps(all_data, ensure_ascii=False, indent=2)}
        
        请遵循以下设计规范：
        1. 模块布局:
        ```
        ┌─────────────────────────────────────────────────────────┐
        │ 执行摘要                                              📋 │
        ├─────────────────────────────────────────────────────────┤
        │                                                         │
        │ 【报告名】在过去【时间段】获得【N】条相关提及，正面评价  │
        │ 占比【X%】，负面评价占比【Y%】；用户最关注【特征】，     │
        │ 主要竞争对手为【竞品名】。                              │
        │                                                         │
        └─────────────────────────────────────────────────────────┘
        ```
        
        2. 样式要求:
        - 使用圆角卡片样式
        - 标题使用18px加粗字体
        - 内容使用14px常规字体
        - 使用适当的内边距和间距
        
        3. 内容要求:
        - 简洁明了地总结报告在市场中的表现
        - 提供关键数据点和核心发现
        - 内容应基于提供的数据，不要编造数据
        - 内容应当包含报告声量、情感分析、关键特征和主要竞争对手等信息
        
        请生成完整的HTML代码片段，不要包含<html>、<head>或<body>标签。
        """
        
        return self._generate_with_stream(prompt)
    
    def generate_brand_comparison(self, brand_mentions_data: Dict) -> str:
        """生成品牌对比分析模块
        
        Args:
            brand_mentions_data: 品牌提及分析数据
            
        Returns:
            str: 品牌对比分析HTML内容
        """
        prompt = f"""
        请根据以下数据，生成品牌对比分析模块的HTML内容：
        
        ```json
        {json.dumps(brand_mentions_data, ensure_ascii=False, indent=2)}
        ```
        
        请遵循以下设计规范：
        1. 模块布局:
        ```
        ┌─────────────────────────────────────────────────────────┐
        │ 品牌对比分析                         🔄 切换指标 📊 TOP10 │
        ├─────────────────────────────────────────────────────────┤
        │                                                         │
        │ 【核心洞察】【品牌名】在所有评论和内容中讨论热度最高，   │
        │ 占比达【X%】，领先第二名品牌【Y%】                      │
        │                                                         │
        │ ╭───────────────────────────────────────────────────╮  │
        │ │                                                   │  │
        │ │              [品牌对比柱状图/气泡图]              │  │
        │ │                                                   │  │
        │ ╰───────────────────────────────────────────────────╯  │
        │                                                         │
        │ 【数据明细】                                            │
        │ ┌──────────┬────────┬─────────┬──────────┬───────────┐ │
        │ │ 品牌     │ 声量   │ 正面率  │ 热度指数 │ 环比增长  │
        │ ├──────────┼────────┼─────────┼──────────┼───────────┤ │
        │ │ 品牌A    │ XXX    │ XX%     │ XX       │ ↑XX%      │
        │ │ 品牌B    │ XXX    │ XX%     │ XX       │ ↓XX%      │
        │ │ 品牌C    │ XXX    │ XX%     │ XX       │ ↑XX%      │
        │ └──────────┴────────┴─────────┴──────────┴───────────┘ │
        │                                                         │
        │ 【用户原声】                                            │
        │ ┌─────────────────────────────────────────────────────┐ │
        │ │ "【原文引用1】" - 来自【平台】                       │ │
        │ │ 👍 XXk · 🔗 点击查看原文                              │ │
        │ └─────────────────────────────────────────────────────┘ │
        │ ┌─────────────────────────────────────────────────────┐ │
        │ │ "【原文引用2】" - 来自【平台】                       │ │
        │ │ 👍 XXk · 🔗 点击查看原文                              │ │
        │ └─────────────────────────────────────────────────────┘ │
        │                                                         │
        └─────────────────────────────────────────────────────────┘
        ```
        
        2. 可视化要求:
        - 使用ECharts.js创建品牌对比柱状图
        - 图表应显示TOP品牌的讨论热度占比
        - 确保图表交互性(悬停显示详情)
        - 使用#3366FF作为主色调，辅助色为#FF6633和#EFEFEF
        
        3. 内容要求:
        - 核心洞察部分需要提炼数据中最重要的发现
        - 数据明细表格应展示主要品牌的关键指标
        - 用户原声部分应展示3-5条真实的用户评论
        - 确保所有数据都来自提供的JSON
        
        请生成完整的HTML代码片段，包含必要的CSS样式和ECharts.js的图表配置。不要包含<html>、<head>或<body>标签。
        """
        
        return self._generate_with_stream(prompt)
    
    def generate_brand_sentiment(self, brand_sentiment_data: Dict) -> str:
        """生成品牌情感分析模块
        
        Args:
            brand_sentiment_data: 品牌情感分析数据
            
        Returns:
            str: 品牌情感分析HTML内容
        """
        prompt = f"""
        请根据以下数据，生成品牌情感分析模块的HTML内容：
        
        ```json
        {json.dumps(brand_sentiment_data, ensure_ascii=False, indent=2)}
        ```
        
        请遵循以下设计规范：
        1. 模块布局:
        ```
        ┌─────────────────────────────────────────────────────────┐
        │ 品牌情感分析                                   🔄 平台筛选 │
        ├─────────────────────────────────────────────────────────┤
        │                                                         │
        │ 【核心洞察】【品牌名】获得了【X%】的正面评价，主要集中在 │
        │ 【某领域】方面                                          │
        │                                                         │
        │ ╭───────────────────────────────────╮ ╭──────────────────╮ │
        │ │                               │ │                  │ │
        │ │      [堆叠柱状图/饼图]         │ │   [情感雷达图]   │ │
        │ │                               │ │                  │ │
        │ ╰───────────────────────────────╯ ╰──────────────────╯ │
        │                                                         │
        │                                                         │
        │ 【用户原声】                                            │
        │ ┌─────────────────────────────────────────────────────┐ │
        │ │ 😀 "【正面评价原声1】" - 来自【平台】                 │ │
        │ │ 👍 XXk · 💬 XX条回复                                  │ │
        │ └─────────────────────────────────────────────────────┘ │
        │                                                         │
        └─────────────────────────────────────────────────────────┘
        ```
        
        2. 可视化要求:
        - 使用ECharts.js创建情感分析饼图
        - 使用合适的颜色标识正面/负面/中性情感
        - 确保图表交互性(悬停显示详情)
        
        3. 内容要求:
        - 核心洞察部分需要提炼数据中最重要的情感分析发现
        - 用户原声部分应分别展示正面和负面评价的真实用户评论
        - 如果数据缺失，请优雅地处理并显示"暂无数据"
        - 确保所有数据都来自提供的JSON
                
        请生成完整的HTML代码片段，包含必要的CSS样式和ECharts.js的图表配置。不要包含<html>、<head>或<body>标签。
        """
        
        return self._generate_with_stream(prompt)
    
    def generate_trend_analysis(self, trend_data: Dict) -> str:
        """生成趋势分析模块
        
        Args:
            trend_data: 趋势分析数据
            
        Returns:
            str: 趋势分析HTML内容
        """
        prompt = f"""
        请根据以下数据，生成行业趋势分析模块的HTML内容：
        
        ```json
        {json.dumps(trend_data, ensure_ascii=False, indent=2)}
        ```
        
        请遵循以下设计规范：
        1. 模块布局:
        ```
        ┌─────────────────────────────────────────────────────────┐
        │ 行业趋势分析                         🔄 切换时间 📊 热点榜 │
        ├─────────────────────────────────────────────────────────┤
        │                                                         │
        │ 【核心洞察】当前行业最热门的讨论主题是【话题名称】，     │
        │ 热度值达到【数值】，主要涉及【品牌列表】                │
        │                                                         │
        │ ╭───────────────────────────────────────────────────╮  │
        │ │                                                   │  │
        │ │              [热度趋势图/热点榜]                  │  │
        │ │                                                   │  │
        │ ╰───────────────────────────────────────────────────╯  │
        │                                                         │
        │ 【热点话题TOP3】                                        │
        │ ┌────────────────┬────────┬─────────────┬────────────┐ │
        │ │ 话题           │ 热度值 │ 发布日期    │ 涉及品牌   │
        │ ├────────────────┼────────┼─────────────┼────────────┤ │
        │ │ 【话题1】      │ XXXXX  │ YYYY-MM-DD  │ A,B,C      │
        │ │ 【话题2】      │ XXXXX  │ YYYY-MM-DD  │ B,D,E      │
        │ │ 【话题3】      │ XXXXX  │ YYYY-MM-DD  │ A,C,F      │
        │ └────────────────┴────────┴─────────────┴────────────┘ │
        │                                                         │
        │ 【用户原声】                                            │
        │ ┌─────────────────────────────────────────────────────┐ │
        │ │ "【原文引用1】" - 来自【平台】                       │ │
        │ │ 👍 XXk · 🔥 热度值: XXXXX                             │ │
        │ └─────────────────────────────────────────────────────┘ │
        │                                                         │
        └─────────────────────────────────────────────────────────┘
        ```
        
        2. 可视化要求:
        - 使用ECharts.js创建热度条形图
        - 横轴为话题名称，纵轴为热度值
        - 使用渐变色显示热度差异
        - 确保图表交互性(悬停显示详情)
        
        3. 内容要求:
        - 核心洞察部分需要提炼数据中最重要的趋势发现
        - 热点话题表格应展示TOP3热门话题的详细信息
        - 用户原声部分应展示与热门话题相关的真实用户评论
        - 确保所有数据都来自提供的JSON
        
        请生成完整的HTML代码片段，包含必要的CSS样式和ECharts.js的图表配置。不要包含<html>、<head>或<body>标签。
        """
        
        return self._generate_with_stream(prompt)
    
    def generate_competitor_analysis(self, competitor_data: Dict) -> str:
        """生成竞争品牌分析模块
        
        Args:
            competitor_data: 竞争品牌分析数据
            
        Returns:
            str: 竞争品牌分析HTML内容
        """
        prompt = f"""
        请根据以下数据，生成竞争品牌分析模块的HTML内容：
        
        ```json
        {json.dumps(competitor_data, ensure_ascii=False, indent=2)}
        ```
        
        请遵循以下设计规范：
        1. 模块布局:
        ```
        ┌─────────────────────────────────────────────────────────┐
        │ 竞争品牌分析                                     📊 TOP5 │
        ├─────────────────────────────────────────────────────────┤
        │                                                         │
        │ 【核心洞察】【品牌名】的主要竞争对手是【竞品名】，两者在 │
        │ 【领域】方面存在直接竞争                               │
        │                                                         │
        │ ╭───────────────────────────────╮ ╭──────────────────╮ │
        │ │                               │ │                  │ │
        │ │    [竞争关系网络图]           │ │ [用户流失趋势图] │ │
        │ │                               │ │                  │ │
        │ ╰───────────────────────────────╯ ╰──────────────────╯ │
        │                                                         │
        │ 【竞争品牌TOP5】                                         │
        │ ┌──────────┬─────────┬───────────┬──────────┬────────┐ │
        │ │ 品牌     │ 提及率  │ 用户流失率 │ 用户摇摆率 │ 竞争度 │ │
        │ ├──────────┼─────────┼───────────┼──────────┼────────┤ │
        │ │ 【竞品1】 │ XX%     │ XX%       │ XX%      │ ★★★★★ │ │
        │ │ 【竞品2】 │ XX%     │ XX%       │ XX%      │ ★★★★☆ │ │
        │ │ 【竞品3】 │ XX%     │ XX%       │ XX%      │ ★★★☆☆ │ │
        │ │ 【竞品4】 │ XX%     │ XX%       │ XX%      │ ★★☆☆☆ │ │
        │ │ 【竞品5】 │ XX%     │ XX%       │ XX%      │ ★☆☆☆☆ │ │
        │ └──────────┴─────────┴───────────┴──────────┴────────┘ │
        │                                                         │
        │ 【用户原声】                                            │
        │ ┌─────────────────────────────────────────────────────┐ │
        │ │ "【原文引用1】" - 来自【平台】                       │ │
        │ │ 👍 XXk · 涉及品牌: 本品牌 vs 【竞品】                 │ │
        │ └─────────────────────────────────────────────────────┘ │
        │                                                         │
        └─────────────────────────────────────────────────────────┘
        ```
        
        2. 可视化要求:
        - 使用ECharts.js创建网络关系图，显示品牌间的竞争关系
        - 节点大小表示品牌提及率
        - 连线粗细表示竞争强度
        - 确保图表交互性(悬停显示详情)
        
        3. 内容要求:
        - 核心洞察部分需要提炼数据中最重要的竞争关系发现
        - 竞争品牌表格应展示TOP5竞争品牌的关键指标
        - 用户原声部分应展示提及多个品牌的真实用户评论
        - 确保所有数据都来自提供的JSON
        
        请生成完整的HTML代码片段，包含必要的CSS样式和ECharts.js的图表配置。不要包含<html>、<head>或<body>标签。
        """
        
        return self._generate_with_stream(prompt)
    
    def generate_feature_analysis(self, feature_data: Dict) -> str:
        """生成产品特征分析模块
        
        Args:
            feature_data: 产品特征分析数据
            
        Returns:
            str: 产品特征分析HTML内容
        """
        prompt = f"""
        请根据以下数据，生成产品特征分析模块的HTML内容：
        
        ```json
        {json.dumps(feature_data, ensure_ascii=False, indent=2)}
        ```
        
        请遵循以下设计规范：
        1. 模块布局:
        ```
        ┌─────────────────────────────────────────────────────────┐
        │ 产品特征分析                            🔄 切换品牌 🔍 详情 │
        ├─────────────────────────────────────────────────────────┤
        │                                                         │
        │ 【核心洞察】用户最关注的产品特征是「【特征名】」，       │
        │ 其中【品牌名】在该维度得分【X】分，表现最佳              │
        │                                                         │
        │ ╭───────────────────────────────────────────────────╮  │
        │ │                                                   │  │
        │ │                 [多维度雷达图]                    │  │
        │ │                                                   │  │
        │ ╰───────────────────────────────────────────────────╯  │
        │                                                         │
        │ 【特征对比明细】                                        │
        │ ┌───────────┬─────────┬─────────┬─────────┬─────────┐  │
        │ │ 特征      │ 品牌A   │ 品牌B   │ 品牌C   │ 品牌D   │  │
        │ ├───────────┼─────────┼─────────┼─────────┼─────────┤  │
        │ │ 外观设计  │ ★★★★★  │ ★★★★☆  │ ★★★☆☆  │ ★★★★☆  │  │
        │ │ 性能表现  │ ★★★★☆  │ ★★★★★  │ ★★★★☆  │ ★★★☆☆  │  │
        │ │ 价格性价比│ ★★★☆☆  │ ★★★★☆  │ ★★★★★  │ ★★★☆☆  │  │
        │ │ 智能驾驶  │ ★★★★☆  │ ★★★☆☆  │ ★★★★☆  │ ★★★★★  │  │
        │ │ 用户体验  │ ★★★★☆  │ ★★★★☆  │ ★★★☆☆  │ ★★★★☆  │  │
        │ └───────────┴─────────┴─────────┴─────────┴─────────┘  │
        │                                                         │
        │ 【用户原声】                                            │
        │ ┌─────────────────────────────────────────────────────┐ │
        │ │ 🔍 【特征名1】: "【原文引用1】" - 来自【平台】        │ │
        │ │ 👍 XXk · 品牌: 【品牌名】                             │ │
        │ └─────────────────────────────────────────────────────┘ │
        │                                                         │
        └─────────────────────────────────────────────────────────┘
        ```
        
        2. 可视化要求:
        - 使用ECharts.js创建多维度雷达图
        - 每个品牌使用不同颜色，形成明显区分
        - 维度应包括所有产品特征
        - 确保图表交互性(悬停显示详情)
        
        3. 内容要求:
        - 核心洞察部分需要提炼数据中最重要的产品特征发现
        - 特征对比明细表格应展示所有品牌在各个特征维度上的表现
        - 用户原声部分应按特征分类展示真实用户评论
        - 确保所有数据都来自提供的JSON
        
        请生成完整的HTML代码片段，包含必要的CSS样式和ECharts.js的图表配置。不要包含<html>、<head>或<body>标签。
        """
        
        return self._generate_with_stream(prompt)
    
    def generate_keyword_analysis(self, keyword_data: Dict) -> str:
        """生成关键词分析模块
        
        Args:
            keyword_data: 关键词分析数据
            
        Returns:
            str: 关键词分析HTML内容
        """
        prompt = """
        请根据以下数据，生成品牌关键词分析模块的HTML内容：
        
        ```json
        """ + json.dumps(keyword_data, ensure_ascii=False, indent=2) + """
        ```
        
        请遵循以下设计规范：
        1. 模块布局:
        ```
        ┌─────────────────────────────────────────────────────────┐
        │ 品牌关键词分析                       🔄 切换品牌 🔍 情感筛选 │
        ├─────────────────────────────────────────────────────────┤
        │                                                         │
        │ 【核心洞察】【品牌名】相关讨论中，「【关键词】」是最热门的│
        │ 正面关键词，权重值达到【数值】                          │
        │                                                         │
        │ ╭───────────────────────────────────╮ ╭──────────────────╮ │
        │ │                               │ │                  │ │
        │ │     [正面关键词词云]          │ │  [负面关键词词云]│ │
        │ │                               │ │                  │ │
        │ ╰───────────────────────────────╯ ╰──────────────────╯ │
        │                                                         │
        │ 【热门关键词TOP10】                                      │
        │ ┌─────────────┬─────────┬───────────┬────────┬────────┐ │
        │ │ 关键词      │ 提及数   │ 情感倾向   │ 热度值  │ 趋势   │
        │ ├─────────────┼─────────┼───────────┼────────┼────────┤ │
        │ │ 【关键词1】  │ XXX     │ 正面       │ XX     │ ↑XX%   │
        │ │ 【关键词2】  │ XXX     │ 负面       │ XX     │ ↓XX%   │
        │ │ ...         │ ...     │ ...       │ ...    │ ...    │
        │ └─────────────┴─────────┴───────────┴────────┴────────┘ │
        │                                                         │
        │ 【关键词关联原声】                                      │
        │ ┌─────────────────────────────────────────────────────┐ │
        │ │ 关于"【关键词】"的讨论:                               │ │
        │ │ "【原文引用1】" - 来自【平台】                       │ │
        │ │ 👍 XXk · 💬 XX条回复                                  │ │
        │ └─────────────────────────────────────────────────────┘ │
        │                                                         │
        └─────────────────────────────────────────────────────────┘
        ```
        
        2. 可视化要求:
           - 使用echarts-wordcloud插件创建词云图
           - 正面词云使用蓝色系(#1890ff)，负面词云使用红色系(#f5222d)
           - 词的大小应与权重成正比
           - 确保图表交互性(悬停显示详情)
        
        3. 内容要求:
        - 核心洞察部分需要提炼数据中最重要的关键词发现
        - 热门关键词表格应展示TOP10关键词的详细信息
        - 关键词关联原声部分应展示与热门关键词相关的真实用户评论
        - 确保所有数据都来自提供的JSON
        
        重要提示：使用echarts-wordcloud插件创建词云，确保创建两个独立的词云容器，分别用于正面和负面关键词。
        
        请直接返回原始HTML代码，不要使用Markdown格式（如```html），不要使用任何代码块标记。只输出HTML代码，不要包含<html>、<head>或<body>标签。
        """
        
        # 将 prompt 包装成正确的 messages 格式
        llm_messages = [{"role": "user", "content": prompt}]
        # 传递包装好的 llm_messages 列表给 messages 参数
        return self.llm.generate(messages=llm_messages)
    
    def generate_optimization_suggestions(self, all_data: Dict[str, Any]) -> str:
        """生成品牌优化建议模块
        
        Args:
            all_data: 所有数据
            
        Returns:
            str: 品牌优化建议HTML内容
        """
        prompt = """
        请根据以下数据，生成品牌优化建议模块的HTML内容：
        
        ```json
        """ + json.dumps(all_data, ensure_ascii=False, indent=2) + """
        ```
        
        请遵循以下设计规范：
        1. 模块布局:
        ```
        ┌─────────────────────────────────────────────────────────┐
        │ 品牌优化建议                                      🌟 重要 │
        ├─────────────────────────────────────────────────────────┤
        │                                                         │
        │ 基于数据分析，我们建议优化以下关键领域：                 │
        │                                                         │
        │ ┌─────────────────────────────────────────────────────┐ │
        │ │ 📈 【建议领域1】                                     │ │
        │ │ • 【具体建议内容】                                   │ │
        │ │ • 【具体建议内容】                                   │ │
        │ │ 📊 数据支撑: 【支持该建议的具体数据点】              │ │
        │ └─────────────────────────────────────────────────────┘ │
        │                                                         │
        │ ┌─────────────────────────────────────────────────────┐ │
        │ │ 🔄 【建议领域2】                                     │ │
        │ │ • 【具体建议内容】                                   │ │
        │ │ • 【具体建议内容】                                   │ │
        │ │ 📊 数据支撑: 【支持该建议的具体数据点】              │ │
        │ └─────────────────────────────────────────────────────┘ │
        │                                                         │
        │ ┌─────────────────────────────────────────────────────┐ │
        │ │ 🛡️ 【建议领域3】                                     │ │
        │ │ • 【具体建议内容】                                   │ │
        │ │ • 【具体建议内容】                                   │ │
        │ │ 📊 数据支撑: 【支持该建议的具体数据点】              │ │
        │ └─────────────────────────────────────────────────────┘ │
        │                                                         │
        └─────────────────────────────────────────────────────────┘
        ```
        
        2. 样式要求:
        - 使用突出的卡片式设计
        - 每个建议卡片使用不同的图标
        - 使用醒目的图标标记重要建议
        - 为不同类型的建议使用不同的边框颜色
        
        3. 内容要求:
        - 基于所有数据分析生成3-5个关键优化建议
        - 每个建议应有明确的领域标题
        - 每个建议应包含2-3个具体的优化内容
        - 每个建议必须有数据支撑，引用JSON数据中的具体数字或事实
        - 确保所有建议都来自提供的数据，不要编造
        
        请直接返回原始HTML代码，不要使用Markdown格式（如```html），不要使用任何代码块标记。只输出HTML代码，不要包含<html>、<head>或<body>标签。
        """
        
        # 将 prompt 包装成正确的 messages 格式
        llm_messages = [{"role": "user", "content": prompt}]
        # 传递包装好的 llm_messages 列表给 messages 参数
        return self.llm.generate(messages=llm_messages)
    
    def generate_ip_distribution_analysis(self, ip_distribution_data: Dict) -> str:
        """生成用户地理分布分析模块
        
        Args:
            ip_distribution_data: 用户地理分布分析数据
            
        Returns:
            str: 用户地理分布分析HTML内容
        """
        prompt = f"""
        请根据以下数据，生成用户地理分布分析模块的HTML内容：
        
        ```json
        {json.dumps(ip_distribution_data, ensure_ascii=False, indent=2)}
        ```
        
        请遵循以下设计规范：
        1. 模块布局:
        ```
        ┌─────────────────────────────────────────────────────────┐
        │ 用户地理分布分析                           🔄 切换视图    │
        ├─────────────────────────────────────────────────────────┤
        │                                                         │
        │ 【核心洞察】【地区名】的用户互动热度最高，热度值达到    │
        │ 【数值】，占总热度的【百分比】                          │
        │                                                         │
        │ ╭───────────────────────────────────────────────────╮  │
        │ │                                                   │  │
        │ │              [地区热度柱状图]                     │  │
        │ │                                                   │  │
        │ ╰───────────────────────────────────────────────────╯  │
        │                                                         │
        │ 【地区分布明细】                                        │
        │ ┌──────────┬───────────┬────────┐                      │
        │ │ 地区     │ 热度值    │ 热度占比 │                      │
        │ ├──────────┼───────────┼────────┤                      │
        │ │ 地区1    │ XXXXX     │ XX.X%  │                      │
        │ │ 地区2    │ XXXXX     │ XX.X%  │                      │
        │ │ 地区3    │ XXXXX     │ XX.X%  │                      │
        │ │ 地区4    │ XXXXX     │ XX.X%  │                      │
        │ │ 地区5    │ XXXXX     │ XX.X%  │                      │
        │ └──────────┴───────────┴────────┘                      │
        │                                                         │
        │ 【品牌地区分布】                                        │
        │ ┌──────────┬────────────┬────────────┬────────────────┐ │
        │ │ 品牌     │ 热门地区1  │ 热门地区2  │ 热门地区3      │
        │ ├──────────┼────────────┼────────────┼────────────────┤ │
        │ │ 品牌A    │ XX%        │ XX%        │ XX%            │
        │ │ 品牌B    │ XX%        │ XX%        │ XX%            │
        │ │ 品牌C    │ XX%        │ XX%        │ XX%            │
        │ └──────────┴────────────┴────────────┴────────────────┘ │
        │                                                         │
        │ 【用户原声】                                            │
        │ ┌─────────────────────────────────────────────────────┐ │
        │ │ "【原文引用1】" - 来自【平台】                       │ │
        │ │ 👍 XXk · 🔗 点击查看原文                              │ │
        │ └─────────────────────────────────────────────────────┘ │
        └─────────────────────────────────────────────────────────┘
        ```
        
        2. 可视化要求:
        - 使用ECharts.js创建地区热度柱状图
        - 横轴为地区名称，纵轴为热度值
        - 使用渐变色显示热度差异
        - 确保图表交互性(悬停显示热度值和占比)
        
        3. 内容要求:
        - 核心洞察部分只关注地区热度分布，提炼最高热度的地区
        - 确保所有数据都来自提供的JSON
        
        请生成完整的HTML代码片段，包含必要的CSS样式和ECharts.js的图表配置。不要包含<html>、<head>或<body>标签。
        """
        
        return self._generate_with_stream(prompt)
    
    def get_css_styles(self) -> str:
        """获取CSS样式
        
        Returns:
            str: CSS样式代码
        """
        return """
        /* 全局样式 */
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
        }
        
        body {
            background-color: #f9f9f9;
            color: #333333;
        }
        
        .report-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
            background-color: #ffffff;
            box-shadow: 0 2px 16px rgba(0, 0, 0, 0.05);
        }
        
        .report-header {
            text-align: center;
            margin-bottom: 32px;
            padding-bottom: 16px;
            border-bottom: 1px solid #EEEEEE;
        }
        
        .report-header h1 {
            font-size: 28px;
            font-weight: bold;
            color: #333333;
            margin-bottom: 8px;
        }
        
        .report-date {
            font-size: 14px;
            color: #999999;
        }
        
        /* 模块通用样式 */
        .module {
            margin-bottom: 32px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            background-color: #ffffff;
        }
        
        .module-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 24px;
            background-color: #3366FF;
            color: white;
        }
        
        .module-title {
            font-size: 18px;
            font-weight: bold;
        }
        
        .module-actions {
            display: flex;
            gap: 8px;
        }
        
        .module-content {
            padding: 24px;
        }
        
        .insight {
            margin-bottom: 24px;
            line-height: 1.6;
        }
        
        /* 图表容器 */
        .chart-container {
            width: 100%;
            height: 400px;
            margin: 24px 0;
            border-radius: 8px;
            overflow: hidden;
            background-color: #FCFCFC;
            border: 1px solid #EEEEEE;
        }
        
        /* 表格样式 */
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 24px 0;
        }
        
        .data-table th,
        .data-table td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #EEEEEE;
        }
        
        .data-table th {
            font-weight: bold;
            background-color: #F7F7F7;
        }
        
        .data-table tr:hover {
            background-color: #F5F9FF;
        }
        
        /* 用户原声样式 */
        .quotes-container {
            margin-top: 24px;
        }
        
        .quote-card {
            padding: 16px;
            margin-bottom: 16px;
            background-color: #F9F9F9;
            border-radius: 8px;
            border-left: 4px solid #3366FF;
        }
        
        .quote-content {
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 8px;
        }
        
        .quote-meta {
            font-size: 12px;
            color: #999999;
            display: flex;
            justify-content: space-between;
        }
        
        /* 响应式设计 */
        @media (max-width: 1199px) {
            .report-container {
                padding: 16px;
            }
            
            .chart-container {
                height: 300px;
            }
        }
        
        @media (max-width: 767px) {
            .module-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
            }
            
            .chart-container {
                height: 250px;
            }
            
            .data-table {
                font-size: 12px;
            }
            
            .data-table th,
            .data-table td {
                padding: 8px;
            }
        }
        
        /* 品牌优化建议样式 */
        .suggestion-card {
            padding: 16px;
            margin-bottom: 16px;
            border-radius: 8px;
            border: 1px solid #EEEEEE;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .suggestion-title {
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 12px;
            color: #3366FF;
        }
        
        .suggestion-content {
            margin-bottom: 12px;
        }
        
        .suggestion-list {
            padding-left: 24px;
            margin-bottom: 12px;
        }
        
        .suggestion-data {
            font-size: 12px;
            padding: 8px;
            background-color: #F5F9FF;
            border-radius: 4px;
        }
        
        /* 页脚样式 */
        .report-footer {
            margin-top: 48px;
            padding-top: 16px;
            border-top: 1px solid #EEEEEE;
            text-align: center;
            font-size: 12px;
            color: #999999;
        }
        """

# 使用示例
if __name__ == "__main__":
    # 创建报告生成器
    generator = ReportLLMGenerator()
    
    # 设置数据目录和输出目录
    generator.set_data_dir("outputs/v0.2.1_帮我做一下小米汽车的竞品分析/data")
    generator.set_output_dir("outputs/report_test")
    
    # 设置报告名称
    generator.set_report_name("用户query分析报告")
    
    # 生成报告
    report_path = generator.generate_report()
    
    print(f"报告已生成: {report_path}")
