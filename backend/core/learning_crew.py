"""
学习引擎 — LangGraph 状态机的薄封装
API 层只需调用这些方法，无需理解图结构
"""

from typing import Optional
from core.state import LearningState, SessionStatus, create_initial_state
from core.graph import full_graph, syllabus_graph, lesson_graph, quiz_graph, exam_graph


class LearningEngine:
    """学习引擎 — 对 LangGraph 状态机的业务封装"""

    def __init__(self, session_id: int = 0, student_id: str = "default"):
        self.session_id = session_id
        self.student_id = student_id

    def _thread_id(self, suffix: str = "") -> dict:
        tid = f"session_{self.session_id}{suffix}"
        return {"configurable": {"thread_id": tid}}

    def _run_graph(self, graph, state: dict, suffix: str = "") -> dict:
        """运行图并返回结果 state"""
        return graph.invoke(state, config=self._thread_id(suffix))

    # ── 完整流程 ──────────────────────────────────────

    def run_full_session(self, topic: str) -> dict:
        """完整学习流程（测评→大纲→教学→测验→完成）"""
        state = create_initial_state(self.session_id, self.student_id, topic)
        return self._run_graph(full_graph, state)

    # ── 分步操作 ──────────────────────────────────────

    def start_assessment(self, topic: str) -> dict:
        """生成测评题目"""
        from core.nodes import start_assessment as fn
        return fn({"subject": topic, "session_id": self.session_id})

    def submit_assessment(self, questions: list, answers: list, subject: str) -> dict:
        """提交测评答案"""
        from core.nodes import submit_assessment as fn
        return fn({
            "assessment_questions": questions,
            "assessment_answers": answers,
            "subject": subject,
        })

    def generate_syllabus(self, topic: str, levels: list = None) -> dict:
        """生成大纲 — 返回 syllabus dict ({topic, description, sections})
           levels: [1] 单学期, [1,2,3] 多学期"""
        from core.nodes import generate_syllabus as fn
        result = fn({"subject": topic, "levels": levels or [1]})
        return result.get("syllabus", {})

    def start_lesson(self, subject: str, item_title: str, attempt: int = 1) -> str:
        """开始上课"""
        from core.nodes import start_lesson as fn
        result = fn({
            "subject": subject,
            "current_item_title": item_title,
            "attempt": attempt,
        })
        return result.get("lesson_content", "")

    def ask_question(self, subject: str, item_title: str, lesson_content: str,
                     chat_history: list, question: str) -> str:
        """学生追问"""
        from core.nodes import ask_question as fn
        result = fn({
            "subject": subject,
            "current_item_title": item_title,
            "lesson_content": lesson_content,
            "chat_history": chat_history or [],
            "student_question": question,
        })
        return result.get("answer", "")

    def start_quiz(self, subject: str, item_title: str) -> list:
        """生成随堂测验题目"""
        from core.nodes import start_quiz as fn
        result = fn({"subject": subject, "current_item_title": item_title})
        return result.get("quiz_questions", [])

    def submit_quiz(self, subject: str, item_title: str,
                    questions: list, answers: list) -> dict:
        """提交测验"""
        from core.nodes import submit_quiz as fn
        return fn({
            "subject": subject,
            "current_item_title": item_title,
            "quiz_questions": questions,
            "quiz_answers": answers,
        })

    def start_exam(self, subject: str, exam_type: str,
                   syllabus_items: list) -> tuple:
        """生成考试题目"""
        from core.nodes import start_exam as fn
        result = fn({
            "subject": subject,
            "exam_type": exam_type,
            "syllabus_items": syllabus_items,
        })
        return result.get("exam_type", exam_type), result.get("exam_questions", [])

    def submit_exam(self, subject: str, exam_type: str,
                    questions: list, answers: list) -> dict:
        """提交考试"""
        from core.nodes import submit_exam as fn
        return fn({
            "subject": subject,
            "exam_type": exam_type,
            "exam_questions": questions,
            "exam_answers": answers,
        })

    # ── 快速模式（独立工具页面）────────────────────────

    def quick_teach(self, topic: str, question: Optional[str] = None) -> str:
        """快速教学 — 不经过状态机，直接调用 LLM"""
        from core.nodes import start_lesson as teach_fn
        from core.nodes import ask_question as ask_fn

        if question:
            lesson = teach_fn({"subject": topic, "current_item_title": topic, "attempt": 1})
            ans = ask_fn({
                "subject": topic, "current_item_title": topic,
                "lesson_content": lesson.get("lesson_content", ""),
                "chat_history": [], "student_question": question,
            })
            return ans.get("answer", "")
        else:
            result = teach_fn({"subject": topic, "current_item_title": topic, "attempt": 1})
            return result.get("lesson_content", "")

    def generate_practice(self, topic: str, difficulty: str = "medium", count: int = 5) -> str:
        """生成练习题 — 直连 LLM"""
        from core.llm import get_chat_model
        from langchain_core.messages import SystemMessage, HumanMessage

        diff_map = {"easy": "基础巩固", "medium": "能力提升", "hard": "培优拓展"}
        llm = get_chat_model(temperature=1.0)
        resp = llm.invoke([
            SystemMessage(content="你是一位中国名校出题专家。使用 Markdown。"),
            HumanMessage(content=f"为「{topic}」生成{count}道{diff_map.get(difficulty,'能力提升')}难度的练习题，含参考答案和解析。"),
        ])
        return resp.content
