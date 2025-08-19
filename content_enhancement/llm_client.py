from __future__ import annotations

"""
LLMClient - 统一的大语言模型调用封装
------------------------------------------------
本模块提供一个轻量级的客户端，用于向大语言模型发送提示词（prompt），并解析结构化返回结果。
目标：
1. 屏蔽底层 API 差异（OpenAI / Azure / 其他）
2. 提供简单的缓存与重试机制，降低请求成本并提升稳定性
3. 暴露领域相关的辅助方法，如获取实体属性模板、逻辑规则、关键词列表等

使用示例：
>>> client = LLMClient(api_key="sk-...", model="gpt-3.5-turbo")
>>> tmpl = client.get_attribute_template("Person")
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
import json
import logging
import os
import time
import re  # 导入正则表达式模块
from functools import lru_cache
import asyncio # 引入 asyncio

try:
    import openai
    from openai import OpenAI, AsyncOpenAI # 导入 AsyncOpenAI
except ImportError:
    openai = None
    OpenAI = None
    AsyncOpenAI = None

logger = logging.getLogger(__name__)


@dataclass
class LLMClientConfig:
    api_key: Optional[str] = None
    model: str = "Qwen/QwQ-32B"
    base_url: Optional[str] = None
    timeout: int = 180  # 延长超时至180秒
    max_retries: int = 3
    cache_enabled: bool = True


class LLMClient:
    """简单的 LLM 客户端封装"""

    def __init__(self, config: LLMClientConfig | None = None):
        self.config = config or LLMClientConfig()
        self.is_operational = False

        # 1. 从标准环境变量名读取配置
        self.config.api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
        self.config.base_url = self.config.base_url or os.getenv("BASE_URL")
        self.config.model = os.getenv("OPENAI_MODEL", self.config.model)  

        # 2. 判断客户端是否可以正常工作
        if not OpenAI:
            logger.warning("openai 库未安装或版本过旧，LLMClient 将处于降级模式。")
        elif not self.config.api_key:
            logger.warning("未在环境变量中找到 OPENAI_API_KEY，LLMClient 将处于降级模式。")
        else:
            self.is_operational = True
            try:
                self.async_client = AsyncOpenAI( # 初始化异步客户端
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    timeout=self.config.timeout,
                )
            except TypeError:
                 self.async_client = None # 兼容旧版本
                 logger.warning("无法初始化 AsyncOpenAI，异步功能将不可用。请检查 openai 库版本。")

            logger.info(f"LLMClient 已配置。模型: {self.config.model}, Base URL: {self.config.base_url or '默认'}")

    def _chat_completion(self, prompt: str, temperature: float = 0.2, **kwargs) -> str:
        """与大语言模型交互（底层封装），使用新版 openai>1.0.0 接口。"""
        if not self.is_operational:
            return ""  # 降级：返回空字符串

        client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout,
        )

        for retry in range(self.config.max_retries):
            try:
                response = client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": "你是一个知识图谱专家，回答需 JSON"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                )
                return response.choices[0].message.content.strip()
            except Exception as exc:
                sleep_time = 2 ** retry
                logger.warning("LLM 请求失败 (第 %s 次), %s秒后重试. 错误: %s", retry + 1, sleep_time, exc)
                time.sleep(sleep_time)
        logger.error("LLM 请求多次失败后放弃。")
        return ""

    async def _achat_completion(self, prompt: str, temperature: float = 0.2, **kwargs) -> str:
        """异步与大语言模型交互。"""
        if not self.is_operational or not self.async_client:
            return ""

        for retry in range(self.config.max_retries):
            try:
                response = await self.async_client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": "你是一个知识图谱专家，回答需 JSON"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                )
                return response.choices[0].message.content.strip()
            except Exception as exc:
                sleep_time = 2 ** retry
                logger.warning("异步 LLM 请求失败 (第 %s 次), %s秒后重试. 错误: %s", retry + 1, sleep_time, exc)
                await asyncio.sleep(sleep_time)
        logger.error("异步 LLM 请求多次失败后放弃。")
        return ""

    def _clean_and_parse_json(self, response_text: str, context: str = "") -> Any:
        """
        清理LLM返回的Markdown代码块并解析JSON。
        """
        # 正则表达式查找被 ```json ... ``` 或 ``` ... ``` 包围的内容
        match = re.search(r"```(json)?\s*([\s\S]*?)\s*```", response_text, re.DOTALL)
        if match:
            # 如果匹配成功，提取第二个捕获组的内容
            clean_text = match.group(2).strip()
        else:
            # 如果没有匹配，假定整个字符串就是JSON
            clean_text = response_text

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            logger.error(f"在 {context} 中解析JSON失败。原始文本 (前100字符): '{response_text[:100]}...'")
            return None

    # ------------------------ 领域辅助方法 (已更新) ------------------------------
    @lru_cache(maxsize=128)
    def get_attribute_template(self, entity_type: str) -> Dict[str, Any]:
        """获取指定实体类型的属性模板，结构同 AttributeTemplate。"""
        prompt = (
            "请为知识图谱中的实体类型 '{entity_type}' 生成属性模板，\n"
            "返回严格的 JSON，包含字段：required_attributes (list)，optional_attributes (list)，\n"
            "attribute_patterns (dict: attribute -> 正则表达式)。"
        ).format(entity_type=entity_type)

        response_text = self._chat_completion(prompt)
        if not response_text:
            logger.warning("LLM 未返回内容，get_attribute_template 使用空结果。")
            return {}
        
        parsed_data = self._clean_and_parse_json(response_text, context=f"get_attribute_template({entity_type})")
        return parsed_data if isinstance(parsed_data, dict) else {}

    @lru_cache(maxsize=128)
    def get_logical_rules(self, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取逻辑校验规则，按需可指定实体类型。"""
        prompt = (
            "请为知识图谱生成逻辑一致性校验规则{suffix}，\n"
            "输出 JSON 数组，每个元素包含 rule_name, condition (自然语言描述)，check (自然语言描述)。"
        ).format(suffix=f" (实体类型: {entity_type})" if entity_type else "")
        
        response_text = self._chat_completion(prompt)
        if not response_text:
            return []
            
        parsed_data = self._clean_and_parse_json(response_text, context=f"get_logical_rules({entity_type})")
        return parsed_data if isinstance(parsed_data, list) else []

    @lru_cache(maxsize=64)
    def get_keywords(self, category: str) -> List[str]:
        """获取指定类别（如 verb / causal 等）的关键词列表"""
        prompt = f"列出知识图谱分析中类别 '{category}' 的中文关键词，返回 JSON 数组。"
        
        response_text = self._chat_completion(prompt)
        if not response_text:
            return []
            
        parsed_data = self._clean_and_parse_json(response_text, context=f"get_keywords({category})")
        return parsed_data if isinstance(parsed_data, list) else []

    # --------------------- 自定义钩子/扩展 ------------------------------
    def custom_query(self, prompt: str, **kwargs) -> str:
        """向 LLM 发送自定义 prompt，返回文本。"""
        return self._chat_completion(prompt, **kwargs) 

    async def acustom_query(self, prompt: str, **kwargs) -> str:
        """异步向 LLM 发送自定义 prompt，返回文本。"""
        return await self._achat_completion(prompt, **kwargs) 