"""
学习会话状态机 — 状态枚举 + State TypedDict
前后端状态一一对应，前端根据 status 决定渲染哪个 View
"""

from typing import TypedDict, Optional, Any
from enum import Enum


class SessionStatus(str, Enum):
    """学习会话状态枚举 — 每个值对应前端 CourseStudio 的一个 View"""

    IDLE = "idle"                     # 初始，尚未开始
    ASSESSING = "assessing"           # 入学测评中 → 前端 AssessmentView
    ASSESSED = "assessed"             # 测评完成 → 前端显示大纲（带测评结果）
    SYLLABUS_READY = "syllabus_ready" # 大纲已生成 → 前端 SyllabusView
    LEARNING = "learning"             # 上课中 → 前端 ClassroomView
    QUIZ_ACTIVE = "quiz_active"       # 随堂测验进行中 → 前端弹出 QuizPanel
    QUIZ_REVIEW = "quiz_review"       # 测验结果展示 → 前端显示通过/重学按钮
    ITEM_DONE = "item_done"           # 知识点已完成 → 前端标记绿色打勾
    EXAM_ACTIVE = "exam_active"       # 考试进行中 → 前端 ExamView
    COMPLETED = "completed"           # 课程完成


class LearningState(TypedDict):
    """贯穿整个学习流程的状态 — 每个字段对应一个明确的数据域"""

    # ── 会话基础 ──────────────────────────────────────
    session_id: int
    student_id: str
    subject: str
    status: str                      # SessionStatus 值，前端直接读取
    error: Optional[str]

    # ── 入学测评 ──────────────────────────────────────
    assessment_questions: list       # 题目 [{id, type, question, options, ...}]
    assessment_answers: list         # 学生答案 [str]
    assessment_result: dict          # { proficiency, overall_score, report, question_results }

    # ── 学习大纲 ──────────────────────────────────────
    syllabus: dict                   # { topic, description, sections: [...] }
    syllabus_items: list             # 扁平化大纲条目 [{item_id, section_id, item_title, status, ...}]
    # 当前知识点由 current_item_id 定位，在 syllabus_items 中按 item_id 查找

    # ── 课堂教学 ──────────────────────────────────────
    current_item_id: str             # 当前知识点的 item_id
    current_item_title: str
    attempt: int                     # 第几次学习此知识点（重学+1）
    lesson_content: str              # AI 教学内容（Markdown）
    chat_history: list               # [{role: "user"|"assistant", content: str}]

    # ── 随堂测验 ──────────────────────────────────────
    quiz_questions: list             # [{id, type, question, options, answer, explanation}]
    quiz_answers: list               # 学生答案 [str]
    quiz_result: dict                # { score, passed, feedback, weak_points }

    # ── 期中/期末考试 ─────────────────────────────────
    exam_type: str                   # "midterm" | "final"
    exam_questions: list             # 题目列表
    exam_answers: list               # 学生答案
    exam_result: dict                # { score, grade, report }

    # ── 进度 ──────────────────────────────────────────
    progress_pct: float              # 0-100
    completed_item_ids: list         # 已完成的知识点 item_id 列表


def create_initial_state(session_id: int, student_id: str, subject: str) -> LearningState:
    """创建初始状态"""
    return {
        "session_id": session_id,
        "student_id": student_id,
        "subject": subject,
        "status": SessionStatus.IDLE,
        "error": None,
        "assessment_questions": [],
        "assessment_answers": [],
        "assessment_result": {},
        "syllabus": {},
        "syllabus_items": [],
        "current_item_id": "",
        "current_item_title": "",
        "attempt": 1,
        "lesson_content": "",
        "chat_history": [],
        "quiz_questions": [],
        "quiz_answers": [],
        "quiz_result": {},
        "exam_type": "",
        "exam_questions": [],
        "exam_answers": [],
        "exam_result": {},
        "progress_pct": 0.0,
        "completed_item_ids": [],
    }
