"""
课堂教学模型 — 多维知识卡片
每个知识点从多个维度切入，每张 card 是一个独立维度
"""

from __future__ import annotations
from typing import List, Optional
from dataclasses import dataclass, field


CARD_ICONS = {
    "definition": "📖",
    "geometric": "📐",
    "physical": "⚡",
    "formula": "🧮",
    "example": "💡",
    "lab": "🔬",
    "syntax": "⌨️",
    "code": "💻",
    "pitfall": "⚠️",
    "application": "🌍",
    "history": "📜",
    "analogy": "🔄",
    "summary": "📝",
    "practice": "✏️",
    "visual": "👁️",
}

CARD_LABELS = {
    "definition": "定义",
    "geometric": "几何意义",
    "physical": "物理意义",
    "formula": "公式",
    "example": "典型例题",
    "lab": "实验室",
    "syntax": "语法",
    "code": "代码示例",
    "pitfall": "常见错误",
    "application": "实际应用",
    "history": "发展历史",
    "analogy": "类比理解",
    "summary": "要点总结",
    "practice": "动手练习",
    "visual": "可视化",
}


@dataclass
class Card:
    """一张知识卡片 = 一个维度"""
    type: str                           # card type key
    title: str                          # 卡片标题
    content: str                        # Markdown 内容
    icon: str = "📄"                    # emoji
    core: bool = True                   # 必看 or 拓展
    next_hint: str = ""                 # 下一张的引导提示
    checkpoint: Optional[dict] = None   # 快问快答

    def __post_init__(self):
        self.icon = CARD_ICONS.get(self.type, "📄")

    @property
    def label(self) -> str:
        return CARD_LABELS.get(self.type, self.title)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "icon": self.icon,
            "label": self.label,
            "core": self.core,
            "next_hint": self.next_hint,
            "checkpoint": self.checkpoint,
        }


@dataclass
class LessonDeck:
    """
    一节课 = 一组知识卡片
    每张卡片是一个独立维度，用户自由翻阅
    """
    topic: str
    subject: str
    objectives: List[str] = field(default_factory=list)
    cards: List[Card] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "subject": self.subject,
            "objectives": self.objectives,
            "cards": [c.to_dict() for c in self.cards],
        }

    @classmethod
    def from_llm_json(cls, data: dict, subject: str = "", topic: str = "") -> "LessonDeck":
        cards_data = data.get("cards", [])
        cards = []
        for cd in cards_data:
            card_type = cd.get("type", "definition")
            cp = cd.get("checkpoint")
            cards.append(Card(
                type=card_type,
                title=cd.get("title", CARD_LABELS.get(card_type, "")),
                content=cd.get("content", ""),
                core=cd.get("core", True),
                next_hint=cd.get("next_hint", ""),
                checkpoint=cp if cp and cp.get("question") else None,
            ))
        # 确保 definition 卡排在最前
        def_sort_key = lambda c: (0 if c.type == "definition" else 1)
        cards.sort(key=def_sort_key)
        return cls(
            topic=topic or data.get("topic", ""),
            subject=subject,
            objectives=data.get("objectives", []),
            cards=cards,
        )
