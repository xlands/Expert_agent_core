import json
from typing import Generator, List, Dict, Any
import traceback

from src.llm import LLM
from src.agent.query_rewriter import QueryRewriter
from src.utils.logger import create_logger
from src.tools.executor import execute_tool
from src.memory.summarizer import summarize_history
from src.prompt.planning import GREETING_BOT_SYSTEM_PROMPT

class GreetingBot:
    """迎宾机器人
    
    负责与用户进行初始交互，识别用户意图，并在合适时机调用查询改写模块进行深度分析。
    """
    
    def __init__(self):
        """初始化迎宾机器人及所需工具实例"""
        self.llm = LLM(model="deepseek-v3")
        self.query_rewriter = QueryRewriter()
        
        # 创建工具实例的映射，用于传递给 executor
        self.tool_instances = {
            "query_rewriter_instance": self.query_rewriter,
        }

    DEFAULT_SYSTEM_PROMPT = GREETING_BOT_SYSTEM_PROMPT

    def chat(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """处理用户消息列表，使用两阶段方法处理对话和工具调用。

        首先尝试调用工具，如果LLM决定调用工具，则执行并返回JSON结果。
        否则，流式生成文本响应。

        Args:
            messages: 用户的消息列表 (ChatML format)

        Yields:
            str: 响应片段 (普通文本或工具执行结果的JSON字符串)
        """
        last_user_message_content = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message_content = msg.get("content", "")
                break
        logger = create_logger(f"Chat: {last_user_message_content[:50]}...")
        logger.log_step_start("处理用户消息 (两阶段模式)")
        logger.log_custom(f"输入消息列表: {messages}")

        # 准备消息和系统提示词
        system_prompt = self.DEFAULT_SYSTEM_PROMPT
        if messages and messages[0].get("role") == "system":
            system_prompt = messages[0]["content"]
            llm_messages = messages[1:]
        else:
            llm_messages = messages

        # 定义工具 (与之前相同)
        llm_tools_definition = [
             {
                "type": "function",
                "function": {
                    "name": "query_rewrite",
                    "description": "当用户需要进行社交媒体数据分析（如品牌分析、竞品分析、用户评价分析等）时，使用此工具将用户查询或对话历史改写为结构化的分析任务。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "用户的原始查询或相关对话历史摘要",
                            }
                        },
                        "required": ["query"]
                    },
                }
            }
        ]

        try:
            # --- Stage 1: Ask for Tool Call Decision ---
            logger.log_step_start("Stage 1: 请求工具调用决策 (ask_tool)")
            tool_decision_message = self.llm.ask_tool(
                messages=llm_messages,
                system_prompt=system_prompt,
                tools=llm_tools_definition,
                tool_choice="auto" # 让模型决定是否调用工具
            )
            # 记录完整的模型响应内容
            logger.log_custom(f"ask_tool 响应: {tool_decision_message}")
            if tool_decision_message.content:
                logger.log_custom(f"模型回复内容: {tool_decision_message.content}")
            if tool_decision_message.tool_calls:
                logger.log_custom(f"模型工具调用: {tool_decision_message.tool_calls}")

            # --- Stage 2: Execute Tool or Generate Text ---
            if tool_decision_message.tool_calls:
                logger.log_step_start("Stage 2: 检测到工具调用，执行工具")
                # 目前假设只有一个工具调用
                tool_call = tool_decision_message.tool_calls[0]
                tool_name = tool_call.function.name
                arguments_str = tool_call.function.arguments # 这是JSON字符串

                logger.log_custom(f"准备执行工具: '{tool_name}' with args: {arguments_str}")
                tool_result = execute_tool(
                    tool_name=tool_name,
                    tool_arguments_str=arguments_str,
                    tool_instances=self.tool_instances,
                    logger=logger
                )
                
                logger.log_custom(f"工具执行结果: {tool_result}")

                # 构建最终的输出负载
                output_payload = tool_result # 默认为工具结果

                # 将最终负载转换为JSON
                json_result = json.dumps(output_payload, ensure_ascii=False)
                yield json_result # Yield the single formatted JSON result and finish
                logger.log_custom("工具执行完成")
                return # Important: Stop generation after yielding tool result

            else:
                logger.log_step_start("Stage 2: 未检测到工具调用，流式生成文本")
                # 调用流式接口生成文本
                stream_generator = self.llm.generate_stream(
                    messages=llm_messages,
                    system_prompt=system_prompt,
                    # 不需要传递 tools 或 tool_choice 给纯文本生成
                )

                # 流式处理文本响应
                full_response = ""  # 用于收集完整响应
                for chunk in stream_generator:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.content:
                        # 收集完整响应
                        full_response += delta.content
                        # Wrap text chunk in the standard stream format
                        stream_output = {
                            "task_type": "stream",
                            "content": {"content": delta.content}
                        }
                        yield json.dumps(stream_output, ensure_ascii=False) # Yield formatted stream chunk
                
                # 记录完整的生成文本
                logger.log_custom(f"模型完整回复: {full_response}")
                logger.log_custom("文本生成完成")

        except Exception as e:
            logger.log_error(f"Chatbot: 两阶段处理中发生错误: {e}\\n{traceback.format_exc()}")
            # 返回结构化的错误信息，符合新格式
            error_output = {
                "task_type": "error",
                "content": {"error": "Chatbot 处理时发生错误", "details": str(e)}
            }
            yield json.dumps(error_output, ensure_ascii=False)

class RiskControlBot:
    """风控机器人（MVP阶段空实现）
    
    负责检查内容是否符合规范和法规要求。在MVP阶段仅作为空实现。
    """
    
    def __init__(self):
        """初始化风控机器人"""
        pass
        
    def check_content(self, content: str) -> bool:
        """检查内容是否合规
        
        Args:
            content: 需要检查的内容
            
        Returns:
            bool: 内容是否合规
        """
        # MVP阶段返回True，表示所有内容都合规
        return True 