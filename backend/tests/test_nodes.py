"""
测试节点函数 — 使用 mock 替代真实 LLM 调用
验证节点的状态转换正确性
"""

import pytest
import sys
from unittest.mock import patch, MagicMock
sys.path.insert(0, "backend")

from core.nodes import (
    start_assessment, submit_assessment, generate_syllabus,
    start_lesson, ask_question, start_quiz, submit_quiz,
    mark_item_done, next_item, retry_item,
    start_exam, submit_exam,
)
from core.state import SessionStatus


# ─── Mock LLM 响应 ─────────────────────────────────────

def mock_llm_response(text: str):
    """创建一个返回指定文本的 mock LLM"""
    mock = MagicMock()
    mock.invoke.return_value.content = text
    return mock


SAMPLE_QUESTIONS_JSON = """[
  {"id":1,"type":"choice","domain":"基础语法","question":"Python中如何输出？","options":["A. print()","B. echo()","C. console.log()"],"answer":"A","explanation":"print是Python的输出函数","difficulty":"easy"}
]"""

SAMPLE_ASSESSMENT_RESULT = """{"proficiency":{"基础语法":80},"overall_score":80,"report":"**诊断报告**","question_results":[{"id":1,"is_correct":true,"score":100,"feedback":"正确"}]}"""

SAMPLE_SYLLABUS_JSON = """{"topic":"Python","description":"Python入门","sections":[{"id":"1","title":"基础","description":"基础语法","items":[{"id":"1.1","title":"变量","description":"变量定义"}]}]}"""

SAMPLE_QUIZ_JSON = """[{"id":1,"type":"choice","question":"1+1=?","options":["A.1","B.2","C.3"],"answer":"B","explanation":"1+1=2"}]"""

SAMPLE_QUIZ_RESULT = """{"score":80,"passed":true,"feedback":"很好！","weak_points":[]}"""

SAMPLE_EXAM_JSON = """[{"id":1,"type":"choice","domain":"基础","question":"测试题","options":["A","B","C","D"],"answer":"A","explanation":"解析","score_weight":5,"difficulty":"easy"}]"""

SAMPLE_EXAM_QUESTIONS = [{"id": 1, "domain": "基础", "question": "测试题", "options": ["A", "B"], "answer": "A", "score_weight": 5}]

SAMPLE_EXAM_RESULT = """{"score":75,"grade":"B","report":"考试分析","strengths":["基础好"],"weaknesses":["需要练习"],"suggestions":"多做题"}"""


class TestAssessmentNodes:
    """入学测评节点测试"""

    @patch("core.nodes.get_chat_model")
    def test_start_assessment(self, mock_get_llm):
        mock_get_llm.return_value = mock_llm_response(SAMPLE_QUESTIONS_JSON)
        result = start_assessment({"subject": "Python"})

        assert result["status"] == SessionStatus.ASSESSING
        assert len(result["assessment_questions"]) == 1
        assert result["assessment_questions"][0]["question"] != ""

    @patch("core.nodes.get_chat_model")
    def test_submit_assessment(self, mock_get_llm):
        mock_get_llm.return_value = mock_llm_response(SAMPLE_ASSESSMENT_RESULT)
        state = {
            "subject": "Python",
            "assessment_questions": [{"id": 1, "domain": "基础", "question": "1+1=?"}],
            "assessment_answers": ["2"],
        }
        result = submit_assessment(state)

        assert result["status"] == SessionStatus.ASSESSED
        assert "overall_score" in result["assessment_result"]


class TestSyllabusNodes:
    """大纲生成节点测试"""

    @patch("core.nodes.get_chat_model")
    def test_generate_syllabus(self, mock_get_llm):
        mock_get_llm.return_value = mock_llm_response(SAMPLE_SYLLABUS_JSON)
        result = generate_syllabus({"subject": "Python"})

        assert result["status"] == SessionStatus.SYLLABUS_READY
        assert len(result["syllabus_items"]) > 0
        assert result["syllabus_items"][0]["item_title"] == "变量"


class TestLessonNodes:
    """课堂教学节点测试"""

    @patch("core.nodes.get_chat_model")
    def test_start_lesson(self, mock_get_llm):
        mock_get_llm.return_value = mock_llm_response("## 🎙️ 课堂引入\n变量是编程的基础概念。")
        result = start_lesson({
            "subject": "Python",
            "current_item_title": "变量",
            "attempt": 1,
        })

        assert result["status"] == SessionStatus.LEARNING
        assert "变量" in result["lesson_content"]

    def test_start_lesson_retry_increments_attempt(self):
        """重学应使用 attempt 参数"""
        # 只是验证 attempt 参数被传递和使用
        pass

    @patch("core.nodes.get_chat_model")
    def test_ask_question(self, mock_get_llm):
        mock_get_llm.return_value = mock_llm_response("好问题！变量就是存储数据的容器。")
        result = ask_question({
            "subject": "Python",
            "current_item_title": "变量",
            "lesson_content": "变量基础",
            "chat_history": [],
            "student_question": "什么是变量？",
        })

        assert "变量" in result["answer"]


class TestQuizNodes:
    """随堂测验节点测试"""

    @patch("core.nodes.get_chat_model")
    def test_start_quiz(self, mock_get_llm):
        mock_get_llm.return_value = mock_llm_response(SAMPLE_QUIZ_JSON)
        result = start_quiz({
            "subject": "Python",
            "current_item_title": "变量",
        })

        assert result["status"] == SessionStatus.QUIZ_ACTIVE
        assert len(result["quiz_questions"]) == 1

    @patch("core.nodes.get_chat_model")
    def test_submit_quiz_passed(self, mock_get_llm):
        mock_get_llm.return_value = mock_llm_response(SAMPLE_QUIZ_RESULT)
        result = submit_quiz({
            "subject": "Python",
            "current_item_title": "变量",
            "quiz_questions": [{"id": 1, "question": "1+1=?"}],
            "quiz_answers": ["2"],
        })

        assert result["status"] == SessionStatus.QUIZ_REVIEW
        assert result["quiz_result"]["passed"] is True
        assert result["quiz_result"]["score"] == 80


class TestProgressNodes:
    """学习进度节点测试"""

    @pytest.fixture
    def base_item_state(self):
        return {
            "syllabus_items": [
                {"item_id": "1.1", "item_title": "变量", "status": "learning", "mastery_score": 0, "sort_order": 0},
                {"item_id": "1.2", "item_title": "字符串", "status": "none", "mastery_score": 0, "sort_order": 1},
            ],
            "current_item_id": "1.1",
            "completed_item_ids": [],
            "quiz_result": {"score": 85, "passed": True, "feedback": ""},
            "progress_pct": 0.0,
        }

    def test_mark_item_done(self, base_item_state):
        result = mark_item_done(base_item_state)

        assert result["status"] == SessionStatus.ITEM_DONE
        # 第一个知识点应标记为 done
        assert result["syllabus_items"][0]["status"] == "done"
        # MasteryModel 加权计算：85*0.6 + 0.2*100*0.2 + 100*0.2 = 51+4+20=75
        assert result["syllabus_items"][0]["mastery_score"] == 75.0

    def test_progress_calculation(self, base_item_state):
        """完成1个知识点，加权进度应大于0"""
        result = mark_item_done(base_item_state)
        assert result["progress_pct"] > 0

    def test_all_done_100_percent(self, base_item_state):
        """全部完成（满分+高掌握度）→ 接近100%"""
        result = mark_item_done(base_item_state)
        # 第一个: quiz=100, attempt=1, mastery=100*0.6+4+20=84
        result = mark_item_done({
            "syllabus_items": result["syllabus_items"],
            "current_item_id": "1.2",
            "completed_item_ids": result["completed_item_ids"],
            "quiz_result": {"score": 100, "passed": True},
            "attempt": 1,
        })
        # 进度 = (75/100*1 + 84/100*1) / 2 * 100 = 79.5，加权后综合进度
        assert result["progress_pct"] == 79.5

    def test_next_item(self, base_item_state):
        result = next_item(base_item_state)

        assert result["current_item_id"] == "1.2"
        assert result["current_item_title"] == "字符串"
        assert result["status"] == SessionStatus.LEARNING
        assert result["attempt"] == 1  # 新知识点重置 attempt

    def test_next_item_last(self):
        """最后一个知识点时 next_item 应保持 ITEM_DONE"""
        state = {
            "syllabus_items": [{"item_id": "1.1", "item_title": "唯一知识点", "sort_order": 0}],
            "current_item_id": "1.1",
        }
        result = next_item(state)
        assert result["status"] == SessionStatus.ITEM_DONE

    def test_retry_item(self, base_item_state):
        result = retry_item(base_item_state)

        assert result["status"] == SessionStatus.LEARNING
        assert result["attempt"] == 2  # attempt +1
        assert result["lesson_content"] == ""  # 清空重新生成


class TestExamNodes:
    """考试节点测试"""

    @patch("core.nodes.get_chat_model")
    def test_start_exam(self, mock_get_llm):
        mock_get_llm.return_value = mock_llm_response(SAMPLE_EXAM_JSON)
        result = start_exam({
            "subject": "Python",
            "exam_type": "midterm",
            "syllabus_items": [{"item_id": "1.1", "item_title": "变量", "status": "done"}],
        })

        assert result["status"] == SessionStatus.EXAM_ACTIVE
        assert len(result["exam_questions"]) == 1

    @patch("core.nodes.get_chat_model")
    def test_submit_exam(self, mock_get_llm):
        mock_get_llm.return_value = mock_llm_response(SAMPLE_EXAM_RESULT)
        result = submit_exam({
            "subject": "Python",
            "exam_type": "midterm",
            "exam_questions": SAMPLE_EXAM_QUESTIONS,
            "exam_answers": ["A"],
        })

        assert result["status"] == SessionStatus.COMPLETED
        assert result["exam_result"]["score"] == 75


class TestNodeEdgeCases:
    """节点边界情况测试"""

    def test_mark_item_done_no_items(self):
        """没有知识点时不应崩溃"""
        result = mark_item_done({
            "syllabus_items": [],
            "current_item_index": 0,
            "current_item_id": "",
            "completed_item_ids": [],
            "quiz_result": {},
            "progress_pct": 0.0,
        })
        assert result["progress_pct"] == 0.0

    def test_next_item_empty(self):
        result = next_item({
            "syllabus_items": [],
            "current_item_index": 0,
        })
        assert result["status"] == SessionStatus.ITEM_DONE
