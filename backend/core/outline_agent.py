"""
大纲生成 — 使用 LangChain 直连 LLM
替代旧的 CrewAI Agent+Task+Crew 方案
"""

import json
import re
from typing import List, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_chat_model

COLOR_ICON = {"red": "🔴", "yellow": "🟡", "green": "🟢"}
COLOR_LABEL = {"red": "未掌握", "yellow": "部分掌握", "green": "已掌握"}


def generate_outline(topic: str, level: str, diagnostic_result: str) -> List[Dict]:
    """根据话题、水平和诊断结果生成三色学习大纲"""
    llm = get_chat_model(temperature=0.7)

    system = "你是一位课程设计专家。请严格返回 JSON 数组，不要有任何多余文字。"
    user = f"""
主题：「{topic}」（学生水平：{level}）
诊断结果：{diagnostic_result}

请生成 6-10 个知识点，标注初始掌握状态：
- green（已掌握）：诊断中表现良好的
- yellow（部分掌握）：诊断中有偏差的
- red（未掌握）：诊断中答错或未涉及的

JSON 数组格式：
[{{"title": "知识点名称", "description": "简短说明", "color": "red/yellow/green"}}]
"""
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    raw = resp.content.strip()

    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        try:
            items = json.loads(match.group())
            result = []
            for i, item in enumerate(items):
                color = item.get("color", "red")
                if color not in ("red", "yellow", "green"):
                    color = "red"
                result.append({
                    "title": item.get("title", f"知识点 {i+1}"),
                    "description": item.get("description", ""),
                    "color": color,
                })
            return result
        except json.JSONDecodeError:
            pass

    print("⚠️ 大纲解析失败，使用默认大纲")
    return [{"title": f"{topic} 基础概念 {i+1}", "description": "", "color": "red"} for i in range(5)]


def recommend_next(items: List[Dict]) -> str:
    """根据三色状态推荐下一步学习顺序"""
    reds = [it for it in items if it.get("color") == "red"]
    yellows = [it for it in items if it.get("color") == "yellow"]
    greens = [it for it in items if it.get("color") == "green"]

    lines = ["", "📌 **推荐学习顺序**："]
    if reds:
        lines.append(f"  🔴 优先学习（未掌握）：{', '.join(r['title'] for r in reds)}")
    if yellows:
        lines.append(f"  🟡 巩固提升（部分掌握）：{', '.join(y['title'] for y in yellows)}")
    if greens:
        lines.append(f"  🟢 复习回顾（已掌握）：{', '.join(g['title'] for g in greens)}")
    if not reds and not yellows:
        lines.append("  🎉 恭喜！所有知识点已掌握！")
    return "\n".join(lines)


def display_outline(items: List[Dict], title: str = "学习大纲") -> str:
    """格式化显示大纲"""
    lines = [f"\n📚 **{title}**", "─" * 55]
    for i, item in enumerate(items, 1):
        icon = COLOR_ICON.get(item.get("color", "red"), "🔴")
        label = COLOR_LABEL.get(item.get("color", "red"), "")
        desc = f"  → {item['description']}" if item.get("description") else ""
        lines.append(f"  {i:2}. {icon} {item['title']}  [{label}]{desc}")
    lines.append("─" * 55)
    return "\n".join(lines)


def update_outline_from_quiz(items: List[Dict], quiz_result: str) -> List[Dict]:
    """根据测验批改结果更新大纲颜色"""
    llm = get_chat_model(temperature=0.3)
    titles = [it["title"] for it in items]

    system = "你是一位课程评估专家。请严格返回 JSON 对象。"
    user = f"""
根据以下测验反馈，判断这些知识点各应更新为什么颜色。

知识点列表：{titles}
测验反馈：{quiz_result}

颜色规则：
- green：回答正确、完整
- yellow：回答有偏差或不完整
- red：明显答错或未掌握

JSON 格式：{{"知识点名称": "green/yellow/red", ...}}
"""
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    raw = resp.content.strip()
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            mapping = json.loads(match.group())
            for item in items:
                new_color = mapping.get(item["title"])
                if new_color in ("red", "yellow", "green"):
                    item["color"] = new_color
        except json.JSONDecodeError:
            pass
    return items
