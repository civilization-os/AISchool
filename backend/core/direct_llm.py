"""
直连 LLM 工具 - 绕过 crewAI 框架直接调用 DeepSeek API
用于需要快速响应的接口（quick-teach、practice、syllabus）
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

from core.config_utils import get_openai_client
from core.llm_utils import chat_completion, parse_json_response




def direct_teach(topic: str, question: str | None = None) -> str:
    """直连 LLM 进行知识点讲解"""
    system = (
        "你是一位经验丰富的中国金牌教研员和辅导老师，擅长用清晰易懂的语言讲解知识点。"
        "请给出结构化的讲解，包含：教学目标聚焦、重难点剖析、典型例题详解、举一反三(变式)、易错警告。"
        "使用 Markdown 格式，让内容层次分明。"
    )
    if question:
        user = f"请讲解「{topic}」，并特别解答这个问题：{question}"
    else:
        user = f"请详细讲解「{topic}」，让初学者能够快速理解和掌握。"
    return chat_completion(system, user, temperature=1.3)


def direct_practice(topic: str, difficulty: str = "medium", count: int = 5) -> str:
    """直连 LLM 生成练习题"""
    diff_map = {"easy": "基础巩固", "medium": "能力提升", "hard": "培优拓展"}
    diff_cn = diff_map.get(difficulty, "能力提升")
    system = (
        "你是一位专业的中国名校出题专家，能设计高质量的学科练习题。"
        "每道题包含：题目、选项（如适合）、参考答案、详细解析（包含考点分析和解题思路点拨）。"
        "使用 Markdown 格式，标注题号。"
    )
    user = f"请为「{topic}」生成 {count} 道{diff_cn}难度的练习题，紧扣核心考点。"
    return chat_completion(system, user, temperature=1.0)


def generate_syllabus(topic: str) -> dict:
    """直连 LLM 生成结构化学习大纲（返回 JSON）"""
    system = (
        "你是一位中国金牌课程设计专家，能为任意学习主题生成系统化的教学大纲或知识树。"
        "请严格返回 JSON 格式，不要有多余文字。"
    )
    user = f"""请为「{topic}」生成一个系统化的教学大纲。
要求：
- 采用中国教材常见划分方式，分为 4-6 个“模块”
- 每个模块有 3-5 个“考点/单元”，并标注前置知识要求和重难点
- JSON 格式如下：
{{
  "topic": "{topic}",
  "description": "简短描述这个主题的学习目标",
  "sections": [
    {{
      "id": "1",
      "title": "模块名称",
      "description": "模块简述与前置知识要求",
      "items": [
        {{"id": "1.1", "title": "考点名称", "description": "简短说明（标明重点或难点）"}},
        {{"id": "1.2", "title": "考点名称", "description": "简短说明（标明重点或难点）"}}
      ]
    }}
  ]
}}"""
    raw = chat_completion(system, user, temperature=1.0)
    
    fallback = {
        "topic": topic,
        "description": f"{topic} 学习大纲",
        "sections": [
            {
                "id": "1",
                "title": "基础入门",
                "description": "掌握基本概念",
                "items": [
                    {"id": "1.1", "title": f"{topic} 基础概念", "description": "了解核心定义"},
                    {"id": "1.2", "title": "环境搭建", "description": "配置学习环境"},
                ]
            }
        ]
    }
    return parse_json_response(raw, fallback=fallback)
