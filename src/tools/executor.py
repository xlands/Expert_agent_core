import json
import traceback
import inspect
from typing import Dict, Any, Optional

def execute_tool(tool_name: str, 
                   tool_arguments_str: Optional[str],
                   tool_instances: Dict[str, Any], 
                   logger) -> Dict[str, Any]:
    """通用工具执行器，查找方法、解析参数、执行并返回结构化结果。
    返回格式: {"task_type": "crawl_task"|"error", "content": ...}
    """
    logger.log_custom(f"Executor: Attempting tool '{tool_name}' with args string: \'{tool_arguments_str[:100]}\'")

    # 1. 查找工具方法
    tool_method = None
    instance_name = "unknown_instance"
    for name, instance in tool_instances.items():
        if hasattr(instance, tool_name) and callable(getattr(instance, tool_name)):
            tool_method = getattr(instance, tool_name)
            instance_name = name
            logger.log_custom(f"Executor: Found method '{tool_name}' in instance '{instance_name}'.")
            break
    
    if not tool_method:
        error_msg = f"Tool method '{tool_name}' not found in provided instances."
        logger.log_warning(error_msg)
        # Return structured error
        return {"task_type": "error", "content": {"error": error_msg}}

    # 2. 解析参数 (暴露错误)
    arguments: Dict[str, Any] = {}
    if tool_arguments_str:
        arguments = json.loads(tool_arguments_str)
        
        # 参数名称适配: 检查方法签名并适配参数名
        if tool_method:
            # 获取方法签名
            sig = inspect.signature(tool_method)
            
            # 参数映射规则
            param_mappings = {
                "result_data": "data",  # 从 result_data 映射到 data
            }
            
            # 执行参数映射
            for old_param, new_param in param_mappings.items():
                if (old_param in arguments and 
                    old_param not in sig.parameters and 
                    new_param in sig.parameters):
                    arguments[new_param] = arguments.pop(old_param)
                    logger.log_custom(f"Executor: Parameter mapped from '{old_param}' to '{new_param}' for tool '{tool_name}'")

    # 3. 执行工具方法
    logger.log_step_start(f"Executor: Executing '{instance_name}.{tool_name}'")
    result = tool_method(**arguments)
    logger.log_custom(f"Executor: Tool '{tool_name}' executed successfully.")
    # 结构化成功返回，带有 task_type
    return {"task_type": "crawl_task", "content": result} 