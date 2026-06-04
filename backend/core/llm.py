"""
LangChain LLM 统一初始化
支持 DeepSeek / OpenAI 兼容接口
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_chat_model(temperature: float = 0.7, max_tokens: int = 4096):
    """
    获取 LangChain ChatOpenAI 实例（兼容 DeepSeek / 任何 OpenAI 兼容 API）
    优先读取数据库配置，回退到 .env
    """
    # 尝试从 config_utils 读取数据库配置
    try:
        from core.config_utils import get_llm_config
        cfg = get_llm_config()
        base_url = cfg["base_url"]
        api_key = cfg["api_key"]
        model = cfg["model"]
    except Exception:
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    if not api_key:
        raise ValueError("未设置 API Key（DEEPSEEK_API_KEY 或 OPENAI_API_KEY）")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )
