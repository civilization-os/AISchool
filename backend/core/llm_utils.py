import json
import traceback
from typing import Any, Optional
from core.config_utils import get_openai_client

def chat_completion(system_prompt: str, user_prompt: str, temperature: float = 1.0, max_tokens: int = 3000) -> str:
    """统一的聊天接口，包含基础错误处理"""
    try:
        client, model = get_openai_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"❌ LLM 调用失败: {str(e)}")
        traceback.print_exc()
        return ""

def parse_json_response(raw_text: str, fallback: Any = None) -> Any:
    """统一的 JSON 提取与解析逻辑"""
    if not raw_text:
        return fallback
    
    raw = raw_text.strip()
    # 移除 Markdown 代码块标记回退
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines[0].strip().startswith("```json") or lines[0].strip() == "```":
            raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3]
    
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {str(e)}")
        print(f"📄 原始输出片段: {raw[:200]}...")
        return fallback
