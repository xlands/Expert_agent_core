# cotex Search API 路由
from fastapi import APIRouter, Request, Response, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import json
import time
from src.agent.chatbot.chatbot import GreetingBot
import logging
import traceback
import os
from datetime import datetime
from src.agent.planning.planner import PlanningAgent
from src.utils.logger import create_logger, create_output_directory
from src.llm import LLM
from src.tools.atomic_insights import atomic_insights
from src.memory.summarizer import summarize_history

router = APIRouter()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 错误码定义
ERROR_CODES = {
    "TIMEOUT_408": {
        "code": "TIMEOUT_408",
        "message": "Processing timeout",
        "retryable": True
    },
    "BAD_REQUEST_400": {
        "code": "BAD_REQUEST_400",
        "message": "Bad request format",
        "retryable": False
    },
    "INTERNAL_ERROR_500": {
        "code": "INTERNAL_ERROR_500",
        "message": "Internal server error",
        "retryable": True
    },
    "INTERRUPT_FAILED_409": {
        "code": "INTERRUPT_FAILED_409",
        "message": "Failed to interrupt the task",
        "retryable": True
    }
}

# 请求模型定义
class Message(BaseModel):
    role: str
    content: str

class StreamingQueryContent(BaseModel):
    messages: Optional[List[Dict[str, Any]]] = None
    collected_data: Optional[List[Dict[str, Any]]] = None
    interrupt_reason: Optional[str] = None
    structured_query: Optional[Dict[str, Any]] = None

class StreamingQueryRequest(BaseModel):
    qa_id: str
    user_id: str
    conversation_id: str
    query_type: str
    content: StreamingQueryContent

class DataProcessingRequest(BaseModel):
    raw_data: List[Dict[str, Any]]

class ConversationSummaryRequest(BaseModel):
    messages: List[Dict[str, Any]]
    conversation_id: Optional[str] = "unknown"
    model_id: Optional[str] = None

# 辅助函数来格式化流输出
def format_stream_response(qa_id, user_id, conversation_id, task_type, content_data):
    """Formats the data into the standard JSON string for streaming."""
    return json.dumps({
        "qa_id": qa_id,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "task_type": task_type,
        "content": content_data
    }, ensure_ascii=False) + '\n'

# 流式任务接口
@router.post('/v1/streaming/query')
async def streaming_query(request: StreamingQueryRequest):
    request_start_time = time.time()
    try:
        # 处理中断请求
        if request.query_type == 'interrupt':
            # 模拟中断处理
            interrupt_reason = request.content.interrupt_reason
            if not interrupt_reason:
                logger.warning("Interrupt request missing 'interrupt_reason'")
                raise HTTPException(status_code=400, detail=ERROR_CODES["BAD_REQUEST_400"])
                
            # 这里应该实现实际的中断逻辑
            # ...
            
            return {"status": "interrupted", "reason": interrupt_reason}
        
        # 处理用户查询或服务器查询
        qa_id = request.qa_id
        user_id = request.user_id
        conversation_id = request.conversation_id
        content = request.content
        
        # 设置超时时间
        timeout = 60 if request.query_type == 'user' else 600  # 用户查询60秒，服务器查询600秒
        
        # 创建流式响应
        async def generate():
            nonlocal request_start_time # Allow modification for accurate timing if needed
            try:
                if request.query_type == 'user':
                    # 获取消息列表，如果不存在或为空则返回错误
                    messages = content.messages
                    if not messages:
                        logger.error(f"Request content missing 'messages' for query_type=user, qa={qa_id}, conv={conversation_id}")
                        yield format_stream_response(qa_id, user_id, conversation_id, "error", {"error": "Missing 'messages' in content"})
                        return

                    greeting_bot = GreetingBot()
                    logger.info(f"Starting GreetingBot.chat for user query, qa={qa_id}, conv={conversation_id}")
                    generator = greeting_bot.chat(messages)

                    for response_chunk_str in generator:
                        try:
                            # Assuming chatbot yields JSON strings like {"task_type": "...", "content": ...}
                            parsed_data = json.loads(response_chunk_str)
                            task_type = parsed_data.get("task_type", "error") # Default to error if missing
                            content_data = parsed_data.get("content", {"error": "Missing content from chatbot"})
                            yield format_stream_response(qa_id, user_id, conversation_id, task_type, content_data)
                        except json.JSONDecodeError:
                             logger.warning(f"Chatbot yielded non-JSON string: {response_chunk_str[:100]}...", exc_info=True)
                             # Yield as simple stream message? Or error?
                             yield format_stream_response(qa_id, user_id, conversation_id, "stream", {"content": f"[Chatbot Raw]: {response_chunk_str}"})
                        except Exception as inner_e:
                             logger.error(f"Error processing chatbot response chunk: {inner_e}", exc_info=True)
                             yield format_stream_response(qa_id, user_id, conversation_id, "error", {"error": f"Error processing chatbot response: {inner_e}"})
                    logger.info(f"GreetingBot.chat finished for user query, qa={qa_id}, conv={conversation_id}")
                elif request.query_type == 'server':
                    # 处理服务器收集的数据
                    collected_data = content.collected_data
                    
                    if not collected_data:
                        logger.error(f"Request content missing or empty 'collected_data' for query_type=server, qa={qa_id}, conv={conversation_id}")
                        yield format_stream_response(qa_id, user_id, conversation_id, "error", {"error": "Missing or empty 'collected_data' in content"})
                        return

                    # 从请求content中获取structured_query
                    structured_query = getattr(content, 'structured_query', None)
                    if structured_query:
                        logger.info(f"Using structured_query from request for planning, qa={qa_id}, conv={conversation_id}")
                    else:
                        logger.info(f"No structured_query provided, will use default plan, qa={qa_id}, conv={conversation_id}")

                    # Create output directory and logger for this specific analysis run
                    # Use conversation_id and timestamp for uniqueness
                    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    base_output_dir = os.path.join("data", "server_runs") # Store server runs separately
                    run_output_dir = os.path.join(base_output_dir, f"conv_{conversation_id}_qa_{qa_id}_{run_timestamp}")
                    try:
                        os.makedirs(run_output_dir, exist_ok=True)
                    except OSError as e:
                         logger.error(f"Failed to create output directory '{run_output_dir}': {e}", exc_info=True)
                         yield format_stream_response(qa_id, user_id, conversation_id, "error", {"error": "Failed to create output directory"})
                         return

                    run_logger = create_logger(f"ServerRun_{conversation_id}_{qa_id}", log_dir=os.path.join(run_output_dir, "logs"))
                    run_logger.log_custom(f"Starting server analysis run. Output Dir: {run_output_dir}")
                    yield format_stream_response(qa_id, user_id, conversation_id, "stream", {"content": f"[SETUP] Analysis setup complete. Output Dir: {run_output_dir}. Starting analysis..."}) # Keep one setup message

                    planner = PlanningAgent(output_dir=run_output_dir, logger=run_logger)
                    logger.info(f"Starting PlanningAgent.run_analysis for server query, qa={qa_id}, conv={conversation_id}") # Log to app log

                    final_summary = None
                    analysis_generator = planner.run_analysis(result_data=collected_data, structured_query=structured_query) # 传递structured_query

                    # 1. Stream Logs from the analysis generator
                    logger.info(f"Executing analysis generator for qa={qa_id}, conv={conversation_id}...") # Changed log message
                    for output in analysis_generator:
                        if isinstance(output, str):
                            # It's a log message
                             yield format_stream_response(qa_id, user_id, conversation_id, "stream", {"content": output}) # Correctly place string in content.content
                        elif isinstance(output, dict):
                            # It's the final summary object
                            final_summary = output
                            # No break here, let generator finish naturally
                        else:
                             logger.warning(f"Planner yielded unexpected type: {type(output)}")
                             yield format_stream_response(qa_id, user_id, conversation_id, "stream", {"content": f"[WARN] Unexpected output from planner: {str(output)[:100]}"}) # Place warning in content.content
                    logger.info(f"Analysis generator finished for qa={qa_id}, conv={conversation_id}.")


                    # Ensure generator finished and we got the summary
                    if final_summary is None:
                        logger.error(f"PlanningAgent generator finished but did not yield a final summary dict, qa={qa_id}, conv={conversation_id}")
                        yield format_stream_response(qa_id, user_id, conversation_id, "error", {"error": "Internal error: Analysis completed without summary"}) # Error content
                        return

                    # 2. Stream Report (if available in summary)
                    report_path = final_summary.get("final_report_path")
                    if report_path and os.path.exists(report_path):
                        logger.info(f"Streaming report file: {report_path}")
                        yield format_stream_response(qa_id, user_id, conversation_id, "stream", {"content": f"[REPORT] Starting report transmission from {os.path.basename(report_path)}..."})
                        try:
                            with open(report_path, 'r', encoding='utf-8') as f_report:
                                for line in f_report:
                                    # Send report line by line
                                    yield format_stream_response(qa_id, user_id, conversation_id, "report", {"content": line})
                            yield format_stream_response(qa_id, user_id, conversation_id, "stream", {"content": "[REPORT] Report transmission complete."})
                        except FileNotFoundError:
                            logger.error(f"Report file path found in summary but file not found: {report_path}")
                            yield format_stream_response(qa_id, user_id, conversation_id, "stream", {"content": f"[ERROR] Report file not found at path: {report_path}"})
                        except Exception as report_e:
                            logger.error(f"Error reading or streaming report file {report_path}: {report_e}", exc_info=True)
                            yield format_stream_response(qa_id, user_id, conversation_id, "stream", {"content": f"[ERROR] Failed to stream report file: {report_e}"})
                    elif report_path:
                         logger.warning(f"Report path '{report_path}' in summary, but file does not exist.")
                         yield format_stream_response(qa_id, user_id, conversation_id, "stream", {"content": f"[WARN] Report path exists in summary but file not found: {report_path}"})


                    # 3. Stream Final Summary/Done message
                    logger.info(f"Sending final 'done' message with summary, qa={qa_id}, conv={conversation_id}")
                    yield format_stream_response(qa_id, user_id, conversation_id, "done", final_summary) # Use the final_summary dict as content

                    logger.info(f"PlanningAgent.run_analysis finished for server query, qa={qa_id}, conv={conversation_id}")
                else:
                    logger.error(f"Invalid query_type '{request.query_type}', qa={qa_id}, conv={conversation_id}")
                    yield format_stream_response(qa_id, user_id, conversation_id, "error", {"error": f"Invalid query_type: {request.query_type}"})
            except Exception as e:
                # 处理generate内部异常，记录详细错误信息
                logger.error(f"Error during streaming generation (qa={qa_id}, conv={conversation_id}): {e}", exc_info=True)
                # Yield a final error message to the client
                try:
                    yield format_stream_response(qa_id, user_id, conversation_id, "error", ERROR_CODES["INTERNAL_ERROR_500"])
                except Exception as final_e:
                    # If even yielding the error fails, log it. Client might disconnect.
                    logger.error(f"Failed to yield final error message: {final_e}", exc_info=True)
        
        # 返回流式响应
        return StreamingResponse(generate(), media_type='application/json')
        
    except Exception as e:
        # 处理streaming_query函数本身的异常
        request_duration = time.time() - request_start_time
        logger.error(f"Error in streaming_query endpoint after {request_duration:.2f}s: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_CODES["INTERNAL_ERROR_500"])

# 数据原子化接口
@router.post('/v1/data/processing')
async def data_processing(request: DataProcessingRequest):
    request_start_time = time.time() # Start timer
    try:
        raw_data = request.raw_data

        # Call atomic_insights directly with the raw_data
        processed_data = []
        try:
            logger.info(f"Starting atomic insights analysis for {len(raw_data)} items.")
            # Pass the raw_data directly to atomic_insights
            # atomic_insights handles the internal LLM calls and processing
            # Consider specifying model_id if not default
            processed_data = atomic_insights(parsed_data=raw_data)
            logger.info(f"Finished atomic insights analysis.")

            # 创建新的结果列表以保留所有原始字段
            final_processed_data = []
            
            # 遍历处理后的数据和对应的原始数据
            for i, item in enumerate(processed_data):
                if i < len(raw_data):  # 确保索引在范围内
                    # 创建一个新字典，首先包含所有原始字段
                    final_item = dict(raw_data[i])
                    
                    # 然后添加/覆盖处理后的字段
                    for key, value in item.items():
                        final_item[key] = value
                    
                    final_processed_data.append(final_item)
                else:
                    # 如果没有对应的原始数据，直接添加处理后的数据
                    final_processed_data.append(item)

            
            # 使用合并后的最终数据替换原始处理数据
            processed_data = final_processed_data

        except Exception as analysis_e:
             logger.error(f"Error during atomic_insights analysis in data_processing: {analysis_e}", exc_info=True)
             raise HTTPException(status_code=500, detail={"error": ERROR_CODES["INTERNAL_ERROR_500"], "message": f"Failed during data analysis: {analysis_e}"})

        # 返回处理结果 (atomic_insights return value is the content)
        processing_duration = time.time() - request_start_time
        logger.info(f"Data processing completed in {processing_duration:.2f}s for {len(processed_data)} items.")
        return {"content": processed_data}

    except Exception as e:
        # 超时或其他错误处理
        request_duration = time.time() - request_start_time
        logger.error(f"Error in data_processing endpoint after {request_duration:.2f}s: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_CODES["INTERNAL_ERROR_500"])

# 对话摘要接口
@router.post('/v1/conversation/summary')
async def conversation_summary(request: ConversationSummaryRequest):
    request_start_time = time.time()
    try:
        # 获取必要参数
        messages = request.messages
        conversation_id = request.conversation_id
        model_id = request.model_id  # 可选参数
        
        try:
            # 创建LLM实例，可选指定模型
            llm_kwargs = {}
            if model_id:
                llm_kwargs['model'] = model_id
                
            llm = LLM(**llm_kwargs)
            
            # 调用摘要函数
            logger.info(f"开始为会话{conversation_id}生成摘要，消息数量: {len(messages)}")
            summary_text = summarize_history(history=messages, llm=llm)
            
            # 返回摘要结果
            processing_duration = time.time() - request_start_time
            logger.info(f"摘要生成完成，耗时: {processing_duration:.2f}s, conv={conversation_id}")
            return {
                "summary": summary_text,
                "conversation_id": conversation_id
            }
            
        except Exception as analysis_e:
            logger.error(f"摘要生成过程中出错: {analysis_e}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": ERROR_CODES["INTERNAL_ERROR_500"], 
                          "message": f"摘要生成失败: {analysis_e}"})
            
    except Exception as e:
        # 一般错误处理
        request_duration = time.time() - request_start_time
        logger.error(f"摘要接口出错，耗时 {request_duration:.2f}s: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_CODES["INTERNAL_ERROR_500"])