"""
日志记录工具模块，提供执行过程的日志记录功能
"""
import json
import time
import datetime
import os
from pathlib import Path
from typing import Dict, List, Any, Optional


def create_output_directory(query: str) -> str:
    """创建输出目录
    
    Args:
        query: 用户查询内容
    
    Returns:
        str: 输出目录路径
    """
    # 创建基础输出目录
    base_dir = "outputs"
    
    # 生成时间戳和简化的查询文本作为目录名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    query_text = "".join(x for x in query[:20] if x.isalnum())  # 取查询前20个字符的字母数字部分
    
    # 组合目录名
    output_dir = os.path.join(base_dir, f"{timestamp}_{query}")
    
    # 创建必要的子目录
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "reports"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "visualizations"), exist_ok=True)
    
    return output_dir


class ExecutionLogger:
    """执行日志记录类，用于记录各步骤执行时间和结果"""
    
    def __init__(self, query: str, base_dir: str = 'data/example'):
        """
        初始化日志记录器
        
        Args:
            query: 用户查询内容
            base_dir: 日志保存的基础目录
        """
        # 创建日志目录
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = Path(base_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化日志内容列表和文件
        self.logs = []
        self.log_file_path = self.log_dir / f"{query[:20].replace(' ', '_')}_log.md"
        self.log_file = open(self.log_file_path, 'w', encoding='utf-8')
        
        # 记录查询和开始时间
        self.query = query
        self.start_time = time.time()
        self._write_log(f"# Cotex搜索执行日志\n\n## 开始时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self._write_log(f"\n## 查询内容\n```\n{query}\n```\n")
    
    def _write_log(self, content: str) -> None:
        """
        内部方法：将日志内容写入内存列表和文件，并输出到控制台
        
        Args:
            content: 日志内容
        """
        self.logs.append(content)
        self.log_file.write(content + "\n")
        self.log_file.flush()  # 即时刷新文件缓冲区
        print(content)
    
    def log_step_start(self, step_name: str) -> float:
        """
        记录步骤开始执行
        
        Args:
            step_name: 步骤名称
            
        Returns:
            float: 步骤开始时间戳
        """
        step_start = time.time()
        log_content = f"\n## {step_name}\n### 开始时间: {datetime.datetime.fromtimestamp(step_start).strftime('%Y-%m-%d %H:%M:%S')}\n"
        self._write_log(log_content)
        return step_start
    
    def log_step_result(self, start_time: float, result: Any, result_detail: Optional[Dict] = None) -> float:
        """
        记录步骤执行结果及耗时
        
        Args:
            start_time: 步骤开始时间戳
            result: 执行结果说明
            result_detail: 可选的详细结果数据，将以JSON格式记录
            
        Returns:
            float: 执行耗时
        """
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 记录结果
        self._write_log(f"### 执行结果\n{result}\n")
        
        # 如果有详细数据，以JSON格式记录
        if result_detail:
            self._write_log(f"### 详细数据\n```json\n{json.dumps(result_detail, ensure_ascii=False, indent=2)}\n```\n")
        
        # 记录耗时
        self._write_log(f"### 耗时: {execution_time:.2f}秒\n")
        
        return execution_time
    
    def log_file_input(self, file_path: str) -> None:
        """
        记录输入文件
        
        Args:
            file_path: 文件路径
        """
        self._write_log(f"### 输入文件: {file_path}\n")
    
    def log_file_output(self, file_path: str) -> None:
        """
        记录输出文件
        
        Args:
            file_path: 文件路径
        """
        self._write_log(f"### 输出文件: {file_path}\n")
    
    def log_data_sample(self, data: Any) -> None:
        """
        记录数据样例
        
        Args:
            data: 数据样例
        """
        if data:
            sample = data[0] if isinstance(data, list) and data else data
            self._write_log(f"### 数据样例\n```json\n{json.dumps(sample, ensure_ascii=False, indent=2)}\n```\n")
    
    def log_data_count(self, data: List) -> None:
        """
        记录数据条数
        
        Args:
            data: 数据列表
        """
        if data:
            self._write_log(f"### 数据条数: {len(data)}\n")
    
    def log_custom(self, content: str) -> None:
        """
        记录自定义内容
        
        Args:
            content: 要记录的内容
        """
        self._write_log(content)
    
    def log_error(self, error_message: str) -> None:
        """
        记录错误信息
        
        Args:
            error_message: 错误信息内容
        """
        self._write_log(f"\n### 错误\n```\n{error_message}\n```\n")
    
    def log_debug(self, debug_message: str) -> None:
        """
        记录调试信息
        
        Args:
            debug_message: 调试信息内容
        """
        self._write_log(f"[DEBUG] {debug_message}")
    
    def finalize(self) -> tuple:
        """
        完成日志记录，写入文件
        
        Returns:
            tuple: (日志文件路径, 总耗时)
        """
        # 记录总耗时
        total_time = time.time() - self.start_time
        self._write_log(f"\n## 总计\n### 总耗时: {total_time:.2f}秒\n")
        self._write_log(f"### 结束时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 关闭日志文件
        self.log_file.close()
        
        return str(self.log_file_path), total_time
    
    def get_report_path(self) -> Path:
        """
        获取报告文件路径
        
        Returns:
            Path: 报告文件路径
        """
        return self.log_dir / f"{self.query[:20].replace(' ', '_')}_report.md"
    
    def __del__(self):
        """析构函数，确保文件被关闭"""
        if hasattr(self, 'log_file') and self.log_file and not self.log_file.closed:
            self.log_file.close()


def create_logger(query: str, log_dir: str = None) -> ExecutionLogger:
    """
    创建日志记录器的便捷函数
    
    Args:
        query: 用户查询内容
        log_dir: 日志保存目录，如果为None则自动创建目录
        
    Returns:
        ExecutionLogger: 日志记录器实例
    """
    if log_dir is None:
        # 如果没有提供log_dir，则创建新的输出目录
        output_dir = create_output_directory(query)
        log_dir = os.path.join(output_dir, "logs")
    
    return ExecutionLogger(query, base_dir=log_dir) 