"""
LangGraph 状态机定义 — 学习流程的完整状态转换图
每个 status 值对应一个或一组节点，条件边根据 status 路由
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from core.state import LearningState, SessionStatus, create_initial_state
from core.nodes import (
    start_assessment,
    submit_assessment,
    generate_syllabus,
    start_lesson,
    ask_question,
    start_quiz,
    submit_quiz,
    mark_item_done,
    next_item,
    retry_item,
    start_exam,
    submit_exam,
    _find_next_item_id,
)


# ─── 条件路由函数 ──────────────────────────────────────

def route_after_quiz(state: LearningState) -> Literal["item_done", "retry"]:
    """测验批改后：通过→标记完成，未通过→重学"""
    result = state.get("quiz_result", {})
    return "item_done" if result.get("passed") else "retry"


def route_after_item(state: LearningState) -> Literal["next", "done"]:
    """知识点标记完成后：还有下一个→继续，否则→结束"""
    items = state.get("syllabus_items", [])
    current_id = state.get("current_item_id", "")
    next_id = _find_next_item_id(items, current_id)
    return "next" if next_id else "done"


def check_progress(state: LearningState) -> Literal["exam_ready", "idle"]:
    """检查是否到达考试解锁条件，暂未实现自动跳转"""
    return "idle"


# ─── 构建完整学习图 ────────────────────────────────────

def build_full_graph() -> StateGraph:
    """
    完整状态机图

    状态流：
    ASSESSING → ASSESSED → SYLLABUS_READY → LEARNING
        → QUIZ_ACTIVE → QUIZ_REVIEW → [passed] ITEM_DONE
                                      → [failed] LEARNING (retry)
        → ITEM_DONE → [next] LEARNING
                    → [done] 可解锁 EXAM
    EXAM_ACTIVE → COMPLETED
    """
    builder = StateGraph(LearningState)

    # ── 注册节点 ──
    builder.add_node("start_assessment", start_assessment)
    builder.add_node("submit_assessment", submit_assessment)
    builder.add_node("generate_syllabus", generate_syllabus)
    builder.add_node("start_lesson", start_lesson)
    builder.add_node("ask_question", ask_question)
    builder.add_node("start_quiz", start_quiz)
    builder.add_node("submit_quiz", submit_quiz)
    builder.add_node("mark_item_done", mark_item_done)
    builder.add_node("next_item", next_item)
    builder.add_node("retry_item", retry_item)
    builder.add_node("start_exam", start_exam)
    builder.add_node("submit_exam", submit_exam)

    # ── 入口 ──
    builder.set_entry_point("start_assessment")

    # ── 主线 ──
    builder.add_edge("start_assessment", "submit_assessment")
    builder.add_edge("submit_assessment", "generate_syllabus")
    builder.add_edge("generate_syllabus", "start_lesson")

    # ── 课堂教学 → 测验 ──
    builder.add_edge("start_lesson", "start_quiz")
    builder.add_edge("start_quiz", "submit_quiz")

    # ── 测验结果 → 条件分支 ──
    builder.add_conditional_edges(
        "submit_quiz",
        route_after_quiz,
        {"item_done": "mark_item_done", "retry": "retry_item"},
    )
    builder.add_edge("retry_item", "start_lesson")  # 重学循环

    # ── 标记完成 → 下一个/结束 ──
    builder.add_conditional_edges(
        "mark_item_done",
        route_after_item,
        {"next": "next_item", "done": END},
    )
    builder.add_edge("next_item", "start_lesson")

    # ── 考试 ──
    builder.add_edge("start_exam", "submit_exam")
    builder.add_edge("submit_exam", END)

    return builder.compile(checkpointer=MemorySaver())


# ─── 子图：仅大纲生成 ──────────────────────────────────

def build_syllabus_graph() -> StateGraph:
    builder = StateGraph(LearningState)
    builder.add_node("generate_syllabus", generate_syllabus)
    builder.set_entry_point("generate_syllabus")
    builder.add_edge("generate_syllabus", END)
    return builder.compile()


# ─── 子图：仅教学+测验 ─────────────────────────────────

def build_lesson_graph() -> StateGraph:
    """教学+测验循环，不涉及大纲和考试"""
    builder = StateGraph(LearningState)
    builder.add_node("start_lesson", start_lesson)
    builder.add_node("ask_question", ask_question)
    builder.add_node("start_quiz", start_quiz)
    builder.add_node("submit_quiz", submit_quiz)
    builder.add_node("mark_item_done", mark_item_done)
    builder.add_node("retry_item", retry_item)

    builder.set_entry_point("start_lesson")
    builder.add_edge("start_lesson", "start_quiz")
    builder.add_edge("start_quiz", "submit_quiz")
    builder.add_conditional_edges(
        "submit_quiz", route_after_quiz,
        {"item_done": "mark_item_done", "retry": "retry_item"},
    )
    builder.add_edge("retry_item", "start_lesson")
    builder.add_edge("mark_item_done", END)
    return builder.compile()


# ─── 子图：仅测验 ──────────────────────────────────────

def build_quiz_graph() -> StateGraph:
    builder = StateGraph(LearningState)
    builder.add_node("start_quiz", start_quiz)
    builder.add_node("submit_quiz", submit_quiz)
    builder.set_entry_point("start_quiz")
    builder.add_edge("start_quiz", "submit_quiz")
    builder.add_edge("submit_quiz", END)
    return builder.compile()


# ─── 子图：仅考试 ──────────────────────────────────────

def build_exam_graph() -> StateGraph:
    builder = StateGraph(LearningState)
    builder.add_node("start_exam", start_exam)
    builder.add_node("submit_exam", submit_exam)
    builder.set_entry_point("start_exam")
    builder.add_edge("start_exam", "submit_exam")
    builder.add_edge("submit_exam", END)
    return builder.compile()


# ─── 图实例（单例）────────────────────────────────────

full_graph = build_full_graph()
syllabus_graph = build_syllabus_graph()
lesson_graph = build_lesson_graph()
quiz_graph = build_quiz_graph()
exam_graph = build_exam_graph()
