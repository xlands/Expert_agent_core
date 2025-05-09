import os
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
from wordcloud import WordCloud
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from typing import List, Dict, Any, Optional, Tuple, Union
import matplotlib.font_manager as fm
from pathlib import Path

class VisualizationTools:
    """可视化工具类，用于生成各种图表"""
    
    def __init__(self):
        """初始化可视化工具"""
        # 查找系统中可用的中文字体
        self._setup_chinese_font()
        
        # 设置正确显示负号
        plt.rcParams['axes.unicode_minus'] = False
        
        self.color_map = ['#3366FF', '#FF6633', '#33CC66', '#FF9933', '#9966FF', 
                          '#FF3366', '#66CCFF', '#FFCC33', '#99CC33', '#FF6699']
    
    def _setup_chinese_font(self):
        """设置支持中文显示的字体"""
        # 常见中文字体列表
        chinese_fonts = [
            'SimHei', 'Microsoft YaHei', 'STSong', 'SimSun', 'FangSong', 
            'STFangsong', 'STKaiti', 'DFKai-SB', 'PingFang SC', 'Hiragino Sans GB',
            'WenQuanYi Zen Hei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC', 
            'Source Han Sans CN', 'Source Han Serif CN'
        ]
        
        # 自定义字体路径
        custom_font_paths = [
            '/System/Library/Fonts',  # macOS系统字体路径
            '/Library/Fonts',         # macOS用户字体路径
            '/usr/share/fonts',       # Linux字体路径
            'C:\\Windows\\Fonts',     # Windows字体路径
            str(Path.home() / '.fonts'),  # 用户主目录下的字体
            str(Path(__file__).parent.parent.parent / 'fonts')  # 项目字体目录
        ]
        
        # 添加自定义字体 - 修复目录处理
        for font_dir in custom_font_paths:
            if os.path.exists(font_dir) and os.path.isdir(font_dir):
                # 遍历目录中的字体文件
                font_extensions = ['.ttf', '.ttc', '.otf']
                for root, dirs, files in os.walk(font_dir):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in font_extensions):
                            try:
                                font_path = os.path.join(root, file)
                                fm.fontManager.addfont(font_path)
                            except Exception as e:
                                # 忽略添加失败的字体
                                pass
        
        # 查找可用的中文字体
        available_fonts = []
        font_found = False
        
        for font in chinese_fonts:
            try:
                test_font = fm.findfont(fm.FontProperties(family=font), fallback=False)
                if test_font is not None and ('ttf' in test_font or 'ttc' in test_font or 'otf' in test_font):
                    available_fonts.append(font)
                    font_found = True
                    # 成功找到字体时不打印，避免过多输出
            except:
                continue
        
        # 如果找到可用字体，设置字体
        if font_found:
            plt.rcParams['font.sans-serif'] = available_fonts + ['Arial']
            self.chinese_font = available_fonts[0]
        else:
            # 如果没有找到，使用系统默认字体，并不打印警告
            self.chinese_font = None

    def _save_figure(self, title: str, filename: str, output_dir: str) -> str:
        """保存图表到文件
        
        Args:
            title: 图表标题
            filename: 文件名
            output_dir: 输出目录
            
        Returns:
            str: 保存的文件路径
        """
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
        plt.title(title, fontproperties=self.chinese_font)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        return output_path
    
    def generate_bar_chart(self, 
                           categories: List[str], 
                           values: List[float], 
                           title: str, 
                           filename: str, 
                           output_dir: str,
                           y_label: str = "百分比") -> str:
        """生成柱状图
        
        Args:
            categories: 类别列表（X轴）
            values: 数值列表（Y轴）
            title: 图表标题
            filename: 输出文件名
            output_dir: 输出目录
            y_label: Y轴标签
            
        Returns:
            str: 保存的文件路径
        """
        plt.figure(figsize=(10, 6))
        bars = plt.bar(categories, values, color=self.color_map[:len(categories)])
        
        # 在柱状图上添加数值标签
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom')
        
        # 使用FontProperties来设置中文字体
        font_prop = fm.FontProperties(family=self.chinese_font) if self.chinese_font else None
        
        plt.xticks(rotation=45, ha='right', fontproperties=font_prop)
        plt.ylabel(y_label, fontproperties=font_prop)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        return self._save_figure(title, filename, output_dir)
    
    def generate_stacked_bar_chart(self,
                                  categories: List[str],
                                  data_series: List[List[float]],
                                  series_names: List[str],
                                  title: str,
                                  filename: str,
                                  output_dir: str,
                                  y_label: str = "比例") -> str:
        """生成堆叠柱状图
        
        Args:
            categories: 类别列表（X轴）
            data_series: 多个数据系列
            series_names: 数据系列名称
            title: 图表标题
            filename: 输出文件名
            output_dir: 输出目录
            y_label: Y轴标签
            
        Returns:
            str: 保存的文件路径
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 使用FontProperties来设置中文字体
        font_prop = fm.FontProperties(family=self.chinese_font) if self.chinese_font else None
        
        # 使用不同的颜色来区分不同的数据系列
        bottom = np.zeros(len(categories))
        for i, data in enumerate(data_series):
            p = ax.bar(categories, data, bottom=bottom, label=series_names[i], 
                    color=self.color_map[i % len(self.color_map)])
            bottom += np.array(data)
            
            # 在每个柱子上添加数值标签
            for j, rect in enumerate(p):
                height = rect.get_height()
                if height > 0:  # 只有当值大于0时才添加标签
                    ax.text(rect.get_x() + rect.get_width()/2.,
                           bottom[j] - height/2.,
                           f'{height:.0f}',
                           ha='center', va='center',
                           color='white', fontweight='bold')
        
        ax.set_ylabel(y_label, fontproperties=font_prop)
        ax.set_title(title, fontproperties=font_prop)
        ax.legend(loc='upper right', prop=font_prop)
        
        # 设置坐标轴格式
        plt.xticks(rotation=45, ha='right', fontproperties=font_prop)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        return self._save_figure(title, filename, output_dir)
    
    def generate_radar_chart(self,
                            dimensions: List[str],
                            brands: List[str],
                            scores: List[List[float]],
                            title: str,
                            filename: str,
                            output_dir: str) -> str:
        """生成雷达图
        
        Args:
            dimensions: 维度列表
            brands: 品牌列表
            scores: 分数列表
            title: 图表标题
            filename: 输出文件名
            output_dir: 输出目录
            
        Returns:
            str: 保存的文件路径
        """
        # 计算角度
        N = len(dimensions)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # 闭合雷达图
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(polar=True))
        
        # 使用FontProperties来设置中文字体
        font_prop = fm.FontProperties(family=self.chinese_font) if self.chinese_font else None
        
        # 遍历每个品牌
        for i, brand in enumerate(brands):
            # 为每个品牌的分数添加第一个值，以闭合雷达图
            values = scores[i].copy()  # 复制列表以避免修改原始数据
            values += values[:1]
            
            # 绘制线条
            ax.plot(angles, values, linewidth=2, label=brand, 
                   color=self.color_map[i % len(self.color_map)])
            
            # 填充区域
            ax.fill(angles, values, alpha=0.1, 
                   color=self.color_map[i % len(self.color_map)])
        
        # 设置角度标签
        plt.xticks(angles[:-1], dimensions, fontproperties=font_prop)
        
        # 设置y轴的范围
        ax.set_rlabel_position(0)
        max_score = max([max(brand_scores) for brand_scores in scores])
        plt.yticks(range(1, max_score + 1), color="grey", size=8)
        plt.ylim(0, max_score)
        
        # 添加图例
        plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1), prop=font_prop)
        
        return self._save_figure(title, filename, output_dir)
    
    def generate_network_chart(self,
                              nodes: List[Dict[str, Any]],
                              links: List[Dict[str, Any]],
                              title: str,
                              filename: str,
                              output_dir: str) -> str:
        """生成网络图
        
        Args:
            nodes: 节点列表，包含id和group
            links: 连接列表，包含source, target, type, value
            title: 图表标题
            filename: 输出文件名
            output_dir: 输出目录
            
        Returns:
            str: 保存的文件路径
        """
        # 创建图
        G = nx.Graph()
        
        # 添加节点
        for node in nodes:
            G.add_node(node['id'], group=node.get('group', 1))
        
        # 添加边
        edge_types = {}
        for link in links:
            source = link['source']
            target = link['target']
            link_type = link.get('type', 'default')
            value = link.get('value', 1)
            
            # 如果已经有边，则更新权重
            if G.has_edge(source, target):
                G[source][target]['weight'] += value
            else:
                G.add_edge(source, target, weight=value, type=link_type)
            
            # 收集边的类型
            if link_type not in edge_types:
                edge_types[link_type] = []
            edge_types[link_type].append((source, target))
        
        # 设置布局
        pos = nx.spring_layout(G, k=0.3, iterations=50, seed=42)
        
        # 创建图形
        plt.figure(figsize=(12, 10))
        
        # 使用FontProperties来设置中文字体
        font_prop = fm.FontProperties(family=self.chinese_font) if self.chinese_font else None
        
        # 绘制节点，按组设置颜色
        node_groups = {}
        for node in nodes:
            group = node.get('group', 1)
            if group not in node_groups:
                node_groups[group] = []
            node_groups[group].append(node['id'])
        
        for group, nodes_in_group in node_groups.items():
            nx.draw_networkx_nodes(G, pos, nodelist=nodes_in_group, 
                                 node_size=500, node_color=self.color_map[(group-1) % len(self.color_map)], 
                                 alpha=0.8)
        
        # 绘制边，每种类型一种颜色
        edge_colors = cm.tab10(np.linspace(0, 1, len(edge_types)))
        
        for i, (edge_type, edges) in enumerate(edge_types.items()):
            # 过滤出当前类型的边
            edge_list = [(u, v) for u, v in G.edges() if (u, v) in edges or (v, u) in edges]
            if edge_list:
                # 获取边的权重
                edge_weights = [G[u][v]['weight'] * 2 for u, v in edge_list]
                
                nx.draw_networkx_edges(G, pos, edgelist=edge_list, width=edge_weights,
                                     edge_color=[edge_colors[i]] * len(edge_list), alpha=0.7, 
                                     label=edge_type)
        
        # 绘制标签
        nx.draw_networkx_labels(G, pos, font_size=12, font_family=self.chinese_font if self.chinese_font else 'sans-serif', 
                              font_weight='bold')
        
        # 添加图例
        plt.legend(prop=font_prop)
        plt.axis('off')
        
        return self._save_figure(title, filename, output_dir)
    
    def generate_word_cloud(self,
                           words: List[Dict[str, Any]],
                           title: str,
                           filename: str,
                           output_dir: str) -> str:
        """生成词云图
        
        Args:
            words: 词汇列表，包含text和weight
            title: 图表标题
            filename: 输出文件名
            output_dir: 输出目录
            
        Returns:
            str: 保存的文件路径
        """
        # 将词汇列表转换为词频字典
        word_freq = {word['text']: word['weight'] for word in words}
        
        # 根据情感选择颜色映射
        sentiment = None
        if any(word.get('sentiment') for word in words if isinstance(word, dict)):
            sentiment_word = next((word for word in words if isinstance(word, dict) and word.get('sentiment')), None)
            if sentiment_word:
                sentiment = sentiment_word.get('sentiment')
        
        # 根据情感选择颜色
        if sentiment == "正面":
            colormap = "YlGn"  # 黄绿色调，积极色彩
        elif sentiment == "负面":
            colormap = "OrRd"  # 橙红色调，消极色彩
        else:
            colormap = "Blues"  # 蓝色调，中性色彩
            
        # 查找中文字体文件
        font_path = None
        if self.chinese_font:
            # 先尝试直接从字体管理器获取字体路径
            try:
                font_path = fm.findfont(fm.FontProperties(family=self.chinese_font))
            except:
                pass
                
        # 如果无法找到字体，尝试在常见位置查找
        if not font_path or 'ttf' not in font_path:
            common_font_files = [
                '/System/Library/Fonts/PingFang.ttc',  # macOS
                '/System/Library/Fonts/STHeiti Light.ttc',  # macOS
                '/Library/Fonts/Microsoft/SimHei.ttf',  # macOS
                '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # Linux
                'C:\\Windows\\Fonts\\simhei.ttf',  # Windows
                'C:\\Windows\\Fonts\\msyh.ttc'  # Windows
            ]
            
            for f in common_font_files:
                if os.path.exists(f):
                    font_path = f
                    break
        
        # 生成词云
        wc = WordCloud(
            font_path=font_path,
            background_color='white',
            max_words=100,
            width=800,
            height=500,
            colormap=colormap,
            prefer_horizontal=0.9
        ).generate_from_frequencies(word_freq)
        
        # 创建图表
        plt.figure(figsize=(10, 6))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        
        return self._save_figure(title, filename, output_dir)
    
    def generate_heat_bar_chart(self,
                               categories: List[str],
                               values: List[float],
                               title: str,
                               filename: str,
                               output_dir: str,
                               y_label: str = "热度值") -> str:
        """生成热度条形图
        
        Args:
            categories: 类别列表（Y轴）
            values: 数值列表（X轴）
            title: 图表标题
            filename: 输出文件名
            output_dir: 输出目录
            y_label: X轴标签
            
        Returns:
            str: 保存的文件路径
        """
        # 创建水平条形图
        plt.figure(figsize=(12, 8))
        
        # 使用FontProperties来设置中文字体
        font_prop = fm.FontProperties(family=self.chinese_font) if self.chinese_font else None
        
        # 反转类别和值，使最大值在顶部
        reversed_categories = categories.copy()
        reversed_categories.reverse()
        reversed_values = values.copy()
        reversed_values.reverse()
        
        # 使用热力渐变色
        norm = plt.Normalize(min(values), max(values))
        colors = cm.hot(norm(reversed_values))
        
        # 创建水平条形图
        bars = plt.barh(range(len(reversed_categories)), reversed_values, color=colors)
        
        # 添加数值标签
        for i, bar in enumerate(bars):
            width = bar.get_width()
            plt.text(width + width*0.01, bar.get_y() + bar.get_height()/2.,
                   f'{width:,.0f}', ha='left', va='center')
        
        # 设置Y轴标签
        plt.yticks(range(len(reversed_categories)), reversed_categories, fontproperties=font_prop)
        plt.xlabel(y_label, fontproperties=font_prop)
        plt.grid(axis='x', linestyle='--', alpha=0.7)
        
        return self._save_figure(title, filename, output_dir)
    
    def generate_visualization(self, 
                              chart_type: str, 
                              title: str, 
                              filename: str, 
                              output_dir: str, 
                              **kwargs) -> str:
        """根据指定的图表类型生成可视化图表
        
        Args:
            chart_type: 图表类型，支持 'bar'(柱状图), 'stacked_bar'(堆叠柱状图), 
                       'radar'(雷达图), 'network'(网络图), 'word_cloud'(词云图), 
                       'heat_bar'(热度条形图)
            title: 图表标题
            filename: 输出文件名
            output_dir: 输出目录
            **kwargs: 根据图表类型传入的不同参数
                
                'bar': 
                    - categories: List[str] 类别列表（X轴）
                    - values: List[float] 数值列表（Y轴）
                    - y_label: str 可选，Y轴标签，默认为"百分比"
                
                'stacked_bar': 
                    - categories: List[str] 类别列表（X轴）
                    - data_series: List[List[float]] 多个数据系列
                    - series_names: List[str] 数据系列名称
                    - y_label: str 可选，Y轴标签，默认为"比例"
                
                'radar': 
                    - dimensions: List[str] 维度列表
                    - brands: List[str] 品牌列表
                    - scores: List[List[float]] 分数列表
                
                'network': 
                    - nodes: List[Dict[str, Any]] 节点列表，包含id和group
                    - links: List[Dict[str, Any]] 连接列表，包含source, target, type, value
                
                'word_cloud': 
                    - words: List[Dict[str, Any]] 词汇列表，包含text和weight
                
                'heat_bar': 
                    - categories: List[str] 类别列表（Y轴）
                    - values: List[float] 数值列表（X轴）
                    - y_label: str 可选，X轴标签，默认为"热度值"
            
        Returns:
            str: 保存的文件路径
            
        Raises:
            ValueError: 如果chart_type不被支持或缺少必要参数
        """
        # 验证图表类型
        supported_chart_types = ['bar', 'stacked_bar', 'radar', 'network', 'word_cloud', 'heat_bar']
        if chart_type not in supported_chart_types:
            raise ValueError(f"不支持的图表类型: {chart_type}。支持的类型: {', '.join(supported_chart_types)}")
        
        # 根据图表类型调用相应的生成方法
        if chart_type == 'bar':
            required_params = ['categories', 'values']
            for param in required_params:
                if param not in kwargs:
                    raise ValueError(f"生成柱状图缺少必要参数: {param}")
            
            return self.generate_bar_chart(
                categories=kwargs['categories'],
                values=kwargs['values'],
                title=title,
                filename=filename,
                output_dir=output_dir,
                y_label=kwargs.get('y_label', "百分比")
            )
            
        elif chart_type == 'stacked_bar':
            required_params = ['categories', 'data_series', 'series_names']
            for param in required_params:
                if param not in kwargs:
                    raise ValueError(f"生成堆叠柱状图缺少必要参数: {param}")
                    
            return self.generate_stacked_bar_chart(
                categories=kwargs['categories'],
                data_series=kwargs['data_series'],
                series_names=kwargs['series_names'],
                title=title,
                filename=filename,
                output_dir=output_dir,
                y_label=kwargs.get('y_label', "比例")
            )
            
        elif chart_type == 'radar':
            required_params = ['dimensions', 'brands', 'scores']
            for param in required_params:
                if param not in kwargs:
                    raise ValueError(f"生成雷达图缺少必要参数: {param}")
                    
            return self.generate_radar_chart(
                dimensions=kwargs['dimensions'],
                brands=kwargs['brands'],
                scores=kwargs['scores'],
                title=title,
                filename=filename,
                output_dir=output_dir
            )
            
        elif chart_type == 'network':
            required_params = ['nodes', 'links']
            for param in required_params:
                if param not in kwargs:
                    raise ValueError(f"生成网络图缺少必要参数: {param}")
                    
            return self.generate_network_chart(
                nodes=kwargs['nodes'],
                links=kwargs['links'],
                title=title,
                filename=filename,
                output_dir=output_dir
            )
            
        elif chart_type == 'word_cloud':
            required_params = ['words']
            for param in required_params:
                if param not in kwargs:
                    raise ValueError(f"生成词云图缺少必要参数: {param}")
                    
            return self.generate_word_cloud(
                words=kwargs['words'],
                title=title,
                filename=filename,
                output_dir=output_dir
            )
            
        elif chart_type == 'heat_bar':
            required_params = ['categories', 'values']
            for param in required_params:
                if param not in kwargs:
                    raise ValueError(f"生成热度条形图缺少必要参数: {param}")
                    
            return self.generate_heat_bar_chart(
                categories=kwargs['categories'],
                values=kwargs['values'],
                title=title,
                filename=filename,
                output_dir=output_dir,
                y_label=kwargs.get('y_label', "热度值")
            )
