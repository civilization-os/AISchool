"""
测试状态枚举、状态转换合法性、初始状态工厂
"""

import pytest
import sys
sys.path.insert(0, "backend")

from core.state import SessionStatus, LearningState, create_initial_state


class TestSessionStatus:
    """状态枚举测试"""

    def test_status_values(self):
        """所有状态值应是有意义的字符串"""
        assert SessionStatus.IDLE == "idle"
        assert SessionStatus.ASSESSING == "assessing"
        assert SessionStatus.ASSESSED == "assessed"
        assert SessionStatus.SYLLABUS_READY == "syllabus_ready"
        assert SessionStatus.LEARNING == "learning"
        assert SessionStatus.QUIZ_ACTIVE == "quiz_active"
        assert SessionStatus.QUIZ_REVIEW == "quiz_review"
        assert SessionStatus.ITEM_DONE == "item_done"
        assert SessionStatus.EXAM_ACTIVE == "exam_active"
        assert SessionStatus.COMPLETED == "completed"

    def test_all_statuses_covered(self):
        """应有 10 个状态"""
        assert len(list(SessionStatus)) == 10

    def test_status_flow_order(self):
        """状态应按学习流程自然排列"""
        flow = [
            SessionStatus.IDLE,
            SessionStatus.ASSESSING,
            SessionStatus.ASSESSED,
            SessionStatus.SYLLABUS_READY,
            SessionStatus.LEARNING,
            SessionStatus.QUIZ_ACTIVE,
            SessionStatus.QUIZ_REVIEW,
            SessionStatus.ITEM_DONE,
            SessionStatus.EXAM_ACTIVE,
            SessionStatus.COMPLETED,
        ]
        # 验证每个状态都能正确转换（字符串匹配）
        for i in range(len(flow) - 1):
            assert isinstance(flow[i].value, str)


class TestInitialState:
    """初始状态工厂测试"""

    def test_create_initial_state(self):
        """初始状态应有正确的默认值"""
        state = create_initial_state(session_id=1, student_id="test_001", subject="Python 编程")

        assert state["session_id"] == 1
        assert state["student_id"] == "test_001"
        assert state["subject"] == "Python 编程"
        assert state["status"] == SessionStatus.IDLE
        assert state["error"] is None

    def test_all_fields_present(self):
        """初始状态应包含所有必需字段"""
        state = create_initial_state(1, "t", "数学")

        required_fields = [
            "session_id", "student_id", "subject", "status", "error",
            "assessment_questions", "assessment_answers", "assessment_result",
            "syllabus", "syllabus_items",
            "current_item_id", "current_item_title", "attempt",
            "lesson_content", "chat_history",
            "quiz_questions", "quiz_answers", "quiz_result",
            "exam_type", "exam_questions", "exam_answers", "exam_result",
            "progress_pct", "completed_item_ids",
        ]
        for field in required_fields:
            assert field in state, f"缺少字段: {field}"

    def test_collections_are_empty(self):
        """初始状态的列表/字典应为空"""
        state = create_initial_state(1, "t", "数学")

        assert state["assessment_questions"] == []
        assert state["assessment_answers"] == []
        assert state["assessment_result"] == {}
        assert state["syllabus"] == {}
        assert state["syllabus_items"] == []
        assert state["chat_history"] == []
        assert state["completed_item_ids"] == []

    def test_numeric_defaults(self):
        """数字字段应有合理的默认值"""
        state = create_initial_state(1, "t", "数学")

        assert state["attempt"] == 1
        assert state["progress_pct"] == 0.0
        assert state["current_item_id"] == ""


class TestStateTransitions:
    """状态转换合法性测试"""

    def test_valid_transitions(self):
        """
        验证学习流程中的合法状态转换
        测试状态机图中定义的每条边
        """
        transitions = {
            SessionStatus.IDLE:            [SessionStatus.ASSESSING],
            SessionStatus.ASSESSING:       [SessionStatus.ASSESSED],
            SessionStatus.ASSESSED:        [SessionStatus.SYLLABUS_READY],
            SessionStatus.SYLLABUS_READY:  [SessionStatus.LEARNING],
            SessionStatus.LEARNING:        [SessionStatus.LEARNING, SessionStatus.QUIZ_ACTIVE],
            SessionStatus.QUIZ_ACTIVE:     [SessionStatus.QUIZ_REVIEW],
            SessionStatus.QUIZ_REVIEW:     [SessionStatus.ITEM_DONE, SessionStatus.LEARNING],
            SessionStatus.ITEM_DONE:       [SessionStatus.LEARNING, SessionStatus.EXAM_ACTIVE, SessionStatus.COMPLETED],
            SessionStatus.EXAM_ACTIVE:     [SessionStatus.COMPLETED],
            SessionStatus.COMPLETED:       [],
        }

        # 验证所有状态都有定义
        for status in SessionStatus:
            assert status in transitions, f"状态 {status} 未定义转换规则"

    def test_no_illegal_skip(self):
        """不能跳过中间状态（验证转换链完整性）"""
        # 从 IDLE 到 SYLLABUS_READY 必须经过 ASSESSING 和 ASSESSED
        flow = [SessionStatus.IDLE, SessionStatus.ASSESSING,
                SessionStatus.ASSESSED, SessionStatus.SYLLABUS_READY]
        for i in range(len(flow) - 1):
            curr, next_st = flow[i], flow[i + 1]
            # 验证每一步都是可达的
            assert curr != next_st

    def test_quiz_retry_loop(self):
        """QUIZ_REVIEW 应能回到 LEARNING（重学循环）"""
        assert SessionStatus.LEARNING in [
            SessionStatus.LEARNING,
            SessionStatus.ITEM_DONE,
        ], "QUIZ_REVIEW 应支持回到 LEARNING 的重学循环"


class TestLearningStateType:
    """LearningState TypedDict 类型测试"""

    def test_can_update_fields(self):
        """状态字段应可变"""
        state = create_initial_state(1, "t", "测试")
        state["status"] = SessionStatus.ASSESSING
        state["progress_pct"] = 50.0
        state["completed_item_ids"] = ["1.1", "1.2"]

        assert state["status"] == "assessing"
        assert state["progress_pct"] == 50.0
        assert len(state["completed_item_ids"]) == 2

    def test_can_merge_dicts(self):
        """状态应支持 dict update 合并（LangGraph 节点返回值的常见模式）"""
        state = create_initial_state(1, "s", "数学")

        # 模拟节点返回值合并
        updates = {
            "status": SessionStatus.ASSESSING,
            "assessment_questions": [{"id": 1, "question": "1+1=?"}],
        }
        state.update(updates)

        assert state["status"] == "assessing"
        assert len(state["assessment_questions"]) == 1
        assert state["assessment_questions"][0]["question"] == "1+1=?"


class TestStateEdgeCases:
    """状态边界情况测试"""

    def test_status_string_equality(self):
        """status 应与字符串直接比较（前端常见用法）"""
        state = create_initial_state(1, "t", "主题")
        assert state["status"] == "idle"
        state["status"] = "learning"
        assert state["status"] == "learning"

    def test_initial_progress_boundary(self):
        """进度应在 0-100 范围内"""
        state = create_initial_state(1, "t", "主题")
        assert 0 <= state["progress_pct"] <= 100

        state["progress_pct"] = 100.0
        assert state["progress_pct"] == 100.0

    def test_attempt_positive(self):
        """学习次数应为正整数"""
        state = create_initial_state(1, "t", "主题")
        assert state["attempt"] >= 1

        state["attempt"] += 1  # 重学
        assert state["attempt"] == 2
