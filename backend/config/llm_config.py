"""
LLM 配置读取 — 仅保留配置读取，不再持有 CrewAI 引用
实际 LLM 实例化交给 core/llm.py 的 get_chat_model()
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


def get_deepseek_config() -> Dict[str, str]:
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    return {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "api_key": api_key,
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    }


def get_provider() -> str:
    return os.getenv("LLM_PROVIDER", "deepseek").lower()


def check_config() -> Dict[str, Any]:
    provider = get_provider()
    try:
        cfg = get_deepseek_config()
        return {
            "status": "ready",
            "provider": provider,
            "model": cfg["model"],
            "base_url": cfg.get("base_url", "default"),
            "message": f"{provider.upper()} 配置正常",
        }
    except Exception as e:
        return {"status": "error", "provider": provider, "error": str(e), "message": f"配置错误: {e}"}
