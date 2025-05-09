import json
from typing import List, Dict, Any, Optional, Generator, Union

from src.llm import LLM
from src.utils.logger import create_logger # Assuming create_logger can be reused or passed
from src.agent.analyzer.analyzers import (
    BrandAnalyzer,
    CompetitorAnalyzer,
    FeatureAnalyzer,
    KeywordAnalyzer,
    TrendAnalyzer,
    IPAnalyzer,
)
from src.agent.report_generator import ReportLLMGenerator
from src.prompt.planning import PLANNING_SYSTEM_PROMPT
import os # Needed for path joining
import traceback # For error logging
from src.tools.executor import execute_tool

class PlanningAgent:
    """
    规划代理，使用 LLM 进行任务规划，并协调执行分析任务和生成报告。
    """

    def __init__(self, output_dir: str, logger=None):
        """初始化规划代理。

        Args:
            output_dir: 所有分析结果和报告的输出根目录。
            logger: 用于记录日志的 logger 实例。如果为 None，将创建一个新的。
        """
        self.llm = LLM(model="deepseek-v3") # Or choose another appropriate model
        self.output_dir = output_dir
        self.data_dir = os.path.join(output_dir, "data")
        self.reports_dir = os.path.join(output_dir, "reports")
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

        self.logger = logger if logger else create_logger("PlanningAgent", log_dir=os.path.join(output_dir, "logs"))

        # 初始化所有分析器实例
        self.analyzers: Dict[str, Any] = {
            "analyze_brand_mentions": BrandAnalyzer(output_dir=self.data_dir),
            "analyze_brand_sentiment": BrandAnalyzer(output_dir=self.data_dir), # Note: Same instance handles both
            "analyze_competitor_relationships": CompetitorAnalyzer(output_dir=self.data_dir),
            "analyze_product_features": FeatureAnalyzer(output_dir=self.data_dir),
            "analyze_keywords": KeywordAnalyzer(output_dir=self.data_dir),
            "analyze_trends": TrendAnalyzer(output_dir=self.data_dir),
            "analyze_ip_distribution": IPAnalyzer(output_dir=self.data_dir),
        }
        # Separate instance for report generation
        self.report_generator = ReportLLMGenerator(logger=self.logger)
        self.report_generator.set_output_dir(self.reports_dir)
        self.report_generator.set_data_dir(self.data_dir)

        # 定义LLM可用的工具schema
        self.tools = self._get_analyzer_tools_schema()

    def _get_analyzer_tools_schema(self) -> List[Dict[str, Any]]:
        """生成LLM可用的工具定义列表。"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "analyze_brand_mentions",
                    "description": "分析品牌提及频次和占比，生成品牌声量分析报告。用于了解哪些品牌最受关注。",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "data": {
                                "type": "array",
                                "description": "待分析的数据集，包含内容文本、评论等信息"
                            }
                        },
                        "required": ["data"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_brand_sentiment",
                    "description": "分析用户对各品牌的情感倾向（正面、中性、负面）。用于了解品牌口碑。",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "data": {
                                "type": "array",
                                "description": "待分析的数据集，包含品牌情感信息"
                            }
                        },
                        "required": ["data"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_competitor_relationships",
                    "description": "分析主要品牌与其竞争对手的关系，识别用户在不同品牌间的讨论提及情况。",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "data": {
                                "type": "array",
                                "description": "待分析的数据集，包含多个品牌的提及和对比信息"
                            }
                        },
                        "required": ["data"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_product_features",
                    "description": "分析用户讨论中涉及的产品特征/维度，并评估各品牌在这些维度上的表现。",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "data": {
                                "type": "array",
                                "description": "待分析的数据集，包含产品特征和用户评价"
                            }
                        },
                        "required": ["data"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_keywords",
                    "description": "提取用户讨论中的高频关键词，识别正面和负面讨论焦点。",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "data": {
                                "type": "array",
                                "description": "待分析的数据集，包含文本内容和评论"
                            }
                        },
                        "required": ["data"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_trends",
                    "description": "分析讨论热点和趋势，提取热门话题和相关用户原声。",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "data": {
                                "type": "array",
                                "description": "待分析的数据集，包含时间序列信息和热度"
                            }
                        },
                        "required": ["data"]
                    }
                }
            },
             {
                "type": "function",
                "function": {
                    "name": "analyze_ip_distribution",
                    "description": "分析发帖和评论用户的地理位置分布，了解用户地域特征。",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "data": {
                                "type": "array",
                                "description": "待分析的数据集，包含用户位置信息"
                            }
                        },
                        "required": ["data"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_final_report",
                    "description": "在完成所有选定的分析任务后，调用此工具来整合结果并生成最终的综合分析报告。",
                    "parameters": {
                        "type": "object", 
                        "properties": {}
                    }
                }
            }
        ]

    def plan_tasks(self, structured_query: Dict[str, Any]) -> Dict[str, Any]:
        """使用 LLM 根据结构化查询规划分析任务并决定是否生成报告。

        Args:
            structured_query: 结构化的查询字典。

        Returns:
            一个字典，包含:
            - "analysis_tasks": List[str], 需要执行的分析任务名称列表。
            - "generate_report": bool, 是否需要生成最终报告。
            - "error": Optional[str], 如果规划失败，则包含错误信息。
        """
        query_str = json.dumps(structured_query, ensure_ascii=False, indent=2)
        self.logger.log_step_start(f"Planning for query: {query_str[:100]}...")
        self.logger.log_custom(f"结构化查询输入:\n{query_str}")

        system_prompt = PLANNING_SYSTEM_PROMPT

        messages = [
            {"role": "user", "content": f"请根据以下结构化查询规划分析任务:\n```json\n{query_str}\n```"}
        ]

        self.logger.log_custom("调用 LLM 进行任务规划...")
        # Use ask_tool to get tool calls decision from LLM
        response_message = self.llm.ask_tool(
            messages=messages,
            system_prompt=system_prompt,
            tools=self.tools,
            tool_choice="auto", # Let the LLM decide which tools to call
            temperature=0.0 # For deterministic planning
        )
        self.logger.log_custom(f"LLM 响应: {response_message}")

        selected_tasks = []
        generate_report_flag = False

        if response_message.tool_calls:
            self.logger.log_custom(f"LLM 决定调用 {len(response_message.tool_calls)} 个工具:")
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name
                if tool_name == "generate_final_report":
                    generate_report_flag = True
                    self.logger.log_custom(f"- {tool_name} (将生成最终报告)")
                elif tool_name in self.analyzers:
                    selected_tasks.append(tool_name)
                    self.logger.log_custom(f"- {tool_name}")
                else:
                    self.logger.log_error(f"LLM 尝试调用未知工具: {tool_name}")
        else:
            self.logger.log_error("LLM 没有选择任何分析任务。可能需要澄清用户查询。")
            return [] # Return empty list if no tasks

        plan = {
            "analysis_tasks": selected_tasks,
            "generate_report": generate_report_flag
        }
        planning_start = self.logger.log_step_start("任务规划")
        self.logger.log_step_result(planning_start, f"规划完成，选定 {len(selected_tasks)} 个分析任务，生成报告: {generate_report_flag}", plan)
        return plan

    def run_analysis(self, result_data: List[Dict[str, Any]], structured_query: Optional[Dict[str, Any]] = None) -> Generator[Union[str, Dict], None, None]:
        """
        执行分析流程。如果提供structured_query则进行规划，否则执行所有分析。
        
        Args:
            result_data: 待分析的数据集合，包含内容文本、品牌提及和其他分析所需信息
            structured_query: 可选的结构化查询，用于规划分析任务
            
        Yields:
            分析过程中的日志信息或最终结果字典
        """
        overall_start_time = self.logger.log_step_start("完整分析流程")
        yield "[STATUS] 开始执行完整分析流程"

        # 在run_analysis开始处添加
        if not result_data:
            self.logger.log_warning("传入的数据集为空")
            yield "[WARNING] 输入数据为空，分析结果可能不准确"

        # 确定要执行的任务
        if structured_query:
            plan = self.plan_tasks(structured_query)
            if plan.get("error"):
                yield {"status": "failure", "error": plan["error"]}
                return
            selected_tasks = plan["analysis_tasks"]
            generate_report_flag = plan["generate_report"]
        else:
            # 如果没有查询，执行所有分析任务并生成报告
            selected_tasks = list(self.analyzers.keys())
            generate_report_flag = True

        # 执行分析任务
        for task_name in selected_tasks:
            yield f"[TASK_START] {task_name}"
            result = execute_tool(
                tool_name=task_name,
                tool_arguments_str=json.dumps({"data": result_data}),  # 使用正确的参数名data
                tool_instances=self.analyzers,
                logger=self.logger
            )
            if result["task_type"] == "error":
                error_details = result['content'].get('details', '')
                yield f"[TASK_ERROR] {task_name}: {result['content']['error']} - {error_details}"
            else:
                yield f"[TASK_SUCCESS] {task_name}"

        # 生成报告
        final_report_path = None # 初始化报告路径
        if generate_report_flag:
            yield "[REPORT_START] 生成最终报告"
            final_report_path = os.path.join(self.reports_dir, "final_report.html")
            # 恢复：传递空列表，让报告生成器自己加载文件
            self.report_generator.generate_report([], final_report_path)
            yield f"[REPORT_DONE] {final_report_path}"

        yield {
            "status": "success",
            "message": "分析完成",
            "final_report_path": final_report_path if generate_report_flag else None
        }


# 示例用法 (需要调整以提供 result_data 和有效的 output_dir)
if __name__ == '__main__':
    # 创建临时输出目录用于测试
    temp_output_dir = "./temp_planner_output"
    os.makedirs(temp_output_dir, exist_ok=True)
    print(f"测试输出将保存在: {temp_output_dir}")

    # 模拟结构化查询
    sample_query = {
        "background": "用户对小米SU7感兴趣，想了解其市场表现和用户反馈。",
        "task": "进行详细的竞品分析，包括品牌声量、用户情感、产品特点、关键词和讨论趋势。",
        "output_format": "需要一份包含图表的综合分析报告"
    }

    # !!! 重要: 需要提供真实的 result_data 用于测试 !!!
    # 这里我们用一个空列表模拟，实际使用时需要加载真实数据
    # 例如:
    # with open('path/to/your/竞品分析结果.json', 'r') as f:
    #     mock_result_data = json.load(f)
    mock_result_data = [
        {"content": "小米汽车确实不错，特别是雷总发布会后热度很高，但还是要看交付和质量。", "brand_mentions": ["小米汽车"], "sentiment": {"小米汽车": "positive"}, "features": {"小米汽车": ["热度", "交付", "质量"]}, "keywords": ["小米汽车", "不错", "热度", "交付", "质量"], "ip_location": "北京"},
        {"content": "特斯拉的自动驾驶还是领先一步，不过价格劝退。", "brand_mentions": ["特斯拉"], "sentiment": {"特斯拉": "neutral"}, "features": {"特斯拉": ["自动驾驶", "价格"]}, "keywords": ["特斯拉", "自动驾驶", "领先", "价格"], "ip_location": "上海"},
        {"content": "蔚来的换电很方便，服务也好，就是有点贵。", "brand_mentions": ["蔚来"], "sentiment": {"蔚来": "positive"}, "features": {"蔚来": ["换电", "服务", "价格"]}, "keywords": ["蔚来", "换电", "方便", "服务", "贵"], "ip_location": "广东"},
         {"content": "小米SU7的外观挺好看，有点像保时捷，不知道实际开起来怎么样。", "brand_mentions": ["小米SU7", "保时捷"], "sentiment": {"小米SU7": "positive", "保时捷": "neutral"}, "features": {"小米SU7": ["外观"]}, "keywords": ["小米SU7", "外观", "好看", "保时捷"], "ip_location": "北京"}
        # ... 更多数据
    ]
    print(f"使用 {len(mock_result_data)} 条模拟数据进行测试。")


    # 初始化 PlanningAgent
    planner = PlanningAgent(output_dir=temp_output_dir)

    # 运行完整的分析流程
    print("\n=== 开始运行分析流程 ===")
    analysis_result = planner.run_analysis(mock_result_data, sample_query)
    print("\n=== 分析流程结束 ===")

    # 打印结果摘要
    print("\n分析结果:")
    print(f"  状态: {analysis_result.get('status')}")
    print(f"  消息: {analysis_result.get('message')}")
    if analysis_result.get('final_report_path'):
        print(f"  最终报告路径: {analysis_result.get('final_report_path')}")
    if analysis_result.get('error'):
        print(f"  错误: {analysis_result.get('error')}")

    print(f"\n详细日志和输出文件可在 '{temp_output_dir}' 目录下查看。")

    # 可以添加第二个测试用例
    sample_query_2 = {
         "background": "用户想了解最近露营装备的讨论热点。",
         "task": "分析相关讨论，提取关键词和热门趋势，不需要完整的品牌对比和报告。",
         "output_format": "趋势简报和关键词列表"
    }
    mock_result_data_2 = [
         {"content": "最近好多人去露营，挪客的帐篷好像挺火的。", "brand_mentions": ["挪客"], "sentiment": {"挪客": "positive"}, "keywords": ["露营", "挪客", "帐篷", "火"], "ip_location": "浙江"},
         {"content": "周末去山里露营，空气真好，但是蚊子也多。", "keywords": ["露营", "山里", "空气好", "蚊子多"], "ip_location": "四川"},
    ]
    print("\n=== 开始运行第二个分析流程 (露营) ===")
    analysis_result_2 = planner.run_analysis(mock_result_data_2, sample_query_2)
    print("\n=== 第二个分析流程结束 ===")
    print("\n分析结果2:")
    print(f"  状态: {analysis_result_2.get('status')}")
    print(f"  消息: {analysis_result_2.get('message')}")
