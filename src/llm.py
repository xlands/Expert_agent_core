from openai import OpenAI, RateLimitError, APIError, AuthenticationError
from openai.types.chat import ChatCompletionMessage, ChatCompletionChunk
from typing import Optional, Dict, Any, List, Union, Generator
import json
import concurrent.futures
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type

class LLM:
    def __init__(self, model: str = "deepseek-v3", api_key: Optional[str] = None):
        """初始化LLM类
        
        Args:
            model: 调用的模型别名 (e.g., "deepseek-v3", "deepseek-v3-online")
            api_key: API Key (当前硬编码)
        """
        self.model_map = {
            "deepseek-v3": "deepseek-v3-250324",
            "deepseek-v3-online": "bot-20250321210824-76l48",
            "doubao-lite": "doubao-1-5-lite-32k-250115"
        }
        self.model = self.model_map[model] # Store the resolved default model ID
        self.api_key = "" # Store the API key (using hardcoded for now)

    def _get_client_for_model(self, model_id: str) -> OpenAI:
        """Creates an OpenAI client with the correct base_url for the given model_id."""
        if model_id == 'bot-20250321210824-76l48':
            base_url = "https://ark.cn-beijing.volces.com/api/v3/bots"
        else:
            base_url = "https://ark.cn-beijing.volces.com/api/v3"
            
        return OpenAI(
            base_url=base_url,
            api_key=self.api_key
        )

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3),
           retry=retry_if_exception_type((RateLimitError, APIError)))
    def ask_tool(self,
                 messages: List[Dict[str, str]],
                 system_prompt: Optional[str] = None,
                 model: Optional[str] = None, # Accepts alias
                 tools: Optional[List[Dict]] = None,
                 tool_choice: Optional[str] = "auto",
                 json_output: bool = False,
                 **kwargs: Any) -> ChatCompletionMessage:
        """(非流式) 向 LLM 请求决策，可能包含工具调用。
        Args:
            messages: 消息列表
            system_prompt: 系统提示词
            model: 模型覆盖
            tools: 可用工具定义列表
            tool_choice: 工具选择模式 ("none", "auto", {"type": "function", ...})
            json_output: 是否强制要求 JSON 输出 (如果为 True，tools 应为 None)
            **kwargs: 其他传递给 API 的参数
        Returns:
            ChatCompletionMessage 对象，包含 content 和 tool_calls
        Raises:
            Exception: API 调用失败或其他错误
        """
        final_messages = list(messages)
        if system_prompt:
            if not final_messages or final_messages[0].get("role") != "system":
                final_messages.insert(0, {"role": "system", "content": system_prompt})
            elif final_messages[0].get("role") == "system":
                final_messages[0]["content"] = system_prompt

        resolved_model_id = self.model_map.get(model, self.model) if model else self.model
        # Get a client configured for this specific model_id
        client = self._get_client_for_model(resolved_model_id)

        request_params = {
            "model": resolved_model_id,
            "messages": final_messages,
            "stream": False,
            **kwargs
        }

        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = tool_choice
        elif json_output:
            request_params["response_format"] = {"type": "json_object"}
        
        # Use the dynamically created client
        completion = client.chat.completions.create(**request_params)
        if not completion.choices:
            raise ValueError("LLM response missing 'choices'")
        return completion.choices[0].message

    def generate(self, 
                 messages: List[Dict[str, str]],
                 system_prompt: Optional[str] = None,
                 model: Optional[str] = None, # Accepts alias
                 return_content_only: bool = True,
                 json_output: bool = False,
                 **kwargs: Any) -> Union[str, Any, Dict]:
        """生成响应 (基于消息列表)
        
        Args:
            messages: 消息列表 (ChatML format)
            system_prompt: 可选的系统提示词。如果提供，且 messages[0]['role'] 不是 'system'，
                         则会被添加到 messages 列表的开头。
            model: 可选的模型别名或 ID 进行覆盖
            return_content_only: 是否只返回内容而非完整消息对象
            json_output: 是否输出JSON格式的响应
            **kwargs: 其他参数
            
        Returns:
            根据参数返回字符串、消息对象或JSON对象
        """
        final_messages = list(messages)
        if system_prompt:
            if not final_messages or final_messages[0].get("role") != "system":
                final_messages.insert(0, {"role": "system", "content": system_prompt})
            elif final_messages[0].get("role") == "system":
                final_messages[0]["content"] = system_prompt

        resolved_model_id = self.model_map.get(model, self.model) if model else self.model
        # Get a client configured for this specific model_id
        client = self._get_client_for_model(resolved_model_id)

        request_params = {
            "model": resolved_model_id,
            "messages": final_messages,
            "stream": False,
            **kwargs
        }
            
        if json_output:
            request_params["response_format"] = {"type": "json_object"}
            
        # Use the dynamically created client
        completion = client.chat.completions.create(**request_params)
        
        message_obj = completion.choices[0].message
        content = message_obj.content
        
        if json_output:
            try:
                # 直接尝试解析JSON
                return json.loads(content)
            except json.JSONDecodeError:
                # 导入抽取工具并使用它处理内容
                from src.utils.extract_markdown import extract_json_from_markdown
                extracted_json = extract_json_from_markdown(content)
                if extracted_json is not None:
                    return extracted_json
                # 如果仍然无法解析，提供友好的错误信息
                raise ValueError(f"无法从LLM响应提取JSON结构。响应内容:\n{content[:500]}...")
        
        if return_content_only:
            return content
        else:
            return message_obj
            
    def batch_generate(self,
                       message_lists: List[List[Dict[str, str]]],
                       system_prompt: Optional[str] = None,
                       model: Optional[str] = None, # Accepts alias
                       batch_size: int = 10, # Note: batch_size is not currently used for parallel execution
                       json_output: bool = False,
                       **kwargs: Any) -> List[Union[str, Dict]]:
        results = []
        # Simple sequential execution
        for i, messages in enumerate(message_lists):
            result = self.generate(
                messages=messages,
                system_prompt=system_prompt,
                model=model, # Pass alias down
                json_output=json_output,
                **kwargs
            )
            results.append(result)
        return results

    def generate_stream(self, 
                        messages: List[Dict[str, str]],
                        system_prompt: Optional[str] = None,
                        model: Optional[str] = None, # Accepts alias
                        **kwargs: Any) -> Generator[ChatCompletionChunk, None, None]:
        """(流式) 生成文本响应。
        Args:
            messages: 消息列表
            system_prompt: 系统提示词
            model: 可选的模型别名或 ID 进行覆盖
            **kwargs: 其他 API 参数
        Yields:
            ChatCompletionChunk: 流式响应块
        Raises:
            Exception: API 调用或流处理错误
        """
        final_messages = list(messages)
        if system_prompt:
            if not final_messages or final_messages[0].get("role") != "system":
                final_messages.insert(0, {"role": "system", "content": system_prompt})
            elif final_messages[0].get("role") == "system":
                 final_messages[0]["content"] = system_prompt
        
        resolved_model_id = self.model_map.get(model, self.model) if model else self.model
        # Get a client configured for this specific model_id
        client = self._get_client_for_model(resolved_model_id)
        
        request_params = {
            "model": resolved_model_id,
            "messages": final_messages,
            "stream": True,
            **kwargs 
        }

        # Use the dynamically created client
        completion_stream = client.chat.completions.create(**request_params)
        for chunk in completion_stream:
            yield chunk 

# 使用示例
if __name__ == "__main__":
    # 初始化LLM
    llm = LLM(model="deepseek-v3")
    # llm = LLM(model="deepseek-r1-online", stream=True)
    
    # # 示例提示词
    # prompt = "帮我总结一下小米汽车用户舆情"
    # # prompt = "我的品牌是帕特，帮我做一下品牌的诊断和衡量"
    # system_prompt = ""
    
    # # 调用模型
    # response = llm.generate(prompt, system_prompt)
    # print(f"模型响应:\n{response}")
    
    # 测试batch_generate
    batch_message_lists = [
        [{"role": "user", "content": "分析小米SU7的优缺点"}],
        [{"role": "user", "content": "比较小米汽车和特斯拉的智能驾驶功能"}],
        [{"role": "user", "content": "总结小米汽车的续航表现"}],
        [{"role": "user", "content": "分析小米汽车的用户评价"}],
        [{"role": "user", "content": "预测小米汽车的未来市场表现"}]
    ]
    
    print("\n测试batch_generate:")
    for batch_size in [4, 5]:
        print(f"\n使用batch_size={batch_size}:")
        import time
        start_time = time.time()
        responses = llm.batch_generate(batch_message_lists, batch_size=batch_size)
        elapsed = time.time() - start_time
        
        for i, (prompt, response) in enumerate(zip(batch_message_lists, responses)):
            print(f"{i+1}. Prompt: {prompt}")
            print(f"Response: {response[:100]}...")
            print()
        print(f"总耗时: {elapsed:.2f}秒")

    # 示例消息列表
    example_messages = [
        {"role": "user", "content": "你好，请介绍一下你自己"}
    ]
    # 调用 generate
    response = llm.generate(example_messages)
    print(f"\nGenerate Response:\n{response}")

    # 调用 generate_stream
    print("\nGenerate Stream Response:")
    for chunk in llm.generate_stream(example_messages):
        content = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else ""
        print(content, end="", flush=True)
    print()

    # 测试带 system_prompt
    system = "你是一个乐于助人的助手。"
    response_with_system = llm.generate(example_messages, system_prompt=system)
    print(f"\nGenerate with System Prompt:\n{response_with_system}")

    # 测试 JSON 输出 (如果模型支持)
    json_messages = [
        {"role": "user", "content": "请用JSON格式返回三个城市的名字和它们的人口。 Key 应该是 name 和 population."}
    ]
    json_response = llm.generate(json_messages, json_output=True, model="deepseek-v3") # Test JSON with alias
    print(f"\nJSON Output Response:\n{json.dumps(json_response, indent=2, ensure_ascii=False)}")
