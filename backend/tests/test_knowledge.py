"""
测试通用知识点架构 — KnowledgeGraph, LearningPath, MasteryModel
"""

import pytest
import sys
sys.path.insert(0, "backend")

from core.knowledge import (
    KnowledgePoint, KnowledgeGraph, MasteryRecord, MasteryModel,
    LearningPath, PointType, Difficulty,
)


class TestKnowledgePoint:
    """单个知识点定义测试"""

    def test_create_point(self):
        pt = KnowledgePoint(id="1.1", title="变量", description="变量定义与赋值")
        assert pt.id == "1.1"
        assert pt.title == "变量"
        assert pt.point_type == PointType.CONCEPT
        assert pt.difficulty == Difficulty.REMEMBER

    def test_to_dict(self):
        pt = KnowledgePoint(id="1.1", title="函数", prerequisites=["1.0"])
        d = pt.to_dict()
        assert d["id"] == "1.1"
        assert d["prerequisites"] == ["1.0"]

    def test_custom_type_and_difficulty(self):
        pt = KnowledgePoint(
            id="2.3", title="排序算法实现",
            point_type=PointType.SKILL,
            difficulty=Difficulty.APPLY,
            estimated_minutes=30,
        )
        assert pt.point_type == PointType.SKILL
        assert pt.difficulty == Difficulty.APPLY
        assert pt.estimated_minutes == 30


class TestKnowledgeGraph:
    """知识点图谱测试"""

    @pytest.fixture
    def graph(self):
        kg = KnowledgeGraph()

        kg.add_point(KnowledgePoint(id="1.1", title="变量", section_id="1", section_title="基础"))
        kg.add_point(KnowledgePoint(id="1.2", title="字符串", section_id="1", section_title="基础", prerequisites=["1.1"]))
        kg.add_point(KnowledgePoint(id="1.3", title="列表", section_id="1", section_title="基础", prerequisites=["1.1"]))
        kg.add_point(KnowledgePoint(id="2.1", title="函数定义", section_id="2", section_title="进阶", prerequisites=["1.2", "1.3"]))
        kg.add_point(KnowledgePoint(id="2.2", title="递归", section_id="2", section_title="进阶", prerequisites=["2.1"]))
        return kg

    def test_add_and_get(self, graph):
        assert len(graph.points) == 5
        pt = graph.get_point("1.1")
        assert pt is not None
        assert pt.title == "变量"

    def test_get_nonexistent(self, graph):
        pt = graph.get_point("99.9")
        assert pt is None

    # ── 前置依赖校验 ──────────────────────────────────

    def test_validate_all_valid(self, graph):
        missing = graph.validate_prerequisites()
        assert len(missing) == 0

    def test_validate_missing_prerequisite(self):
        kg = KnowledgeGraph()
        kg.add_point(KnowledgePoint(id="2.1", title="函数", prerequisites=["1.0"]))
        missing = kg.validate_prerequisites()
        assert len(missing) == 1
        assert "2.1" in missing[0]

    # ── 拓扑排序 ──────────────────────────────────────

    def test_topological_order(self, graph):
        sorted_ids = graph.topological_sort()
        # 1.1 应在 1.2 和 1.3 之前
        assert sorted_ids.index("1.1") < sorted_ids.index("1.2")
        assert sorted_ids.index("1.1") < sorted_ids.index("1.3")
        # 1.2 和 1.3 应在 2.1 之前
        assert sorted_ids.index("1.2") < sorted_ids.index("2.1")
        assert sorted_ids.index("1.3") < sorted_ids.index("2.1")
        # 2.1 应在 2.2 之前
        assert sorted_ids.index("2.1") < sorted_ids.index("2.2")

    def test_topological_all_nodes_included(self, graph):
        sorted_ids = graph.topological_sort()
        assert set(sorted_ids) == {"1.1", "1.2", "1.3", "2.1", "2.2"}

    def test_topological_no_prerequisites(self):
        """无前置依赖时按 sort_order 排序"""
        kg = KnowledgeGraph()
        kg.add_point(KnowledgePoint(id="b", title="B", sort_order=1))
        kg.add_point(KnowledgePoint(id="a", title="A", sort_order=0))
        sorted_ids = kg.topological_sort()
        assert sorted_ids == ["a", "b"]

    # ── 学习路径计算 ──────────────────────────────────

    def test_calculate_path_order(self, graph):
        path = graph.calculate_path()
        assert len(path.point_ids) == 5
        assert path.point_ids[0] == "1.1"  # 无前置，第一个

    def test_calculate_path_with_completed(self, graph):
        """已完成的知识点应被跳过"""
        path = graph.calculate_path(completed_ids={"1.1", "1.2"})
        assert "1.1" not in path.point_ids
        assert "1.2" not in path.point_ids
        assert "1.3" in path.point_ids  # 还没学

    def test_parallel_groups(self, graph):
        """同级无依赖的知识点应能并行"""
        path = graph.calculate_path()
        # 1.2 和 1.3 都依赖 1.1，互不依赖，应可并行
        parallel_found = any("1.2" in g and "1.3" in g for g in path.parallel_groups)
        assert parallel_found

    def test_estimated_time(self, graph):
        path = graph.calculate_path()
        assert path.estimated_total_minutes > 0

    # ── 已解锁知识点 ──────────────────────────────────

    def test_get_unlocked_initially(self, graph):
        """初始时应只有无前置依赖的知识点"""
        unlocked = graph.get_unlocked_points(set())
        ids = {p.id for p in unlocked}
        assert "1.1" in ids
        assert "1.2" not in ids  # 依赖 1.1

    def test_get_unlocked_after_progress(self, graph):
        """完成 1.1 后，1.2 和 1.3 应解锁"""
        unlocked = graph.get_unlocked_points({"1.1"})
        ids = {p.id for p in unlocked}
        assert "1.2" in ids
        assert "1.3" in ids
        assert "2.1" not in ids  # 依赖 1.2 和 1.3

    def test_get_unlocked_all_done(self, graph):
        """全部完成后应无解锁知识点"""
        unlocked = graph.get_unlocked_points({"1.1", "1.2", "1.3", "2.1", "2.2"})
        assert len(unlocked) == 0

    # ── 序列化 ────────────────────────────────────────

    def test_to_syllabus_items(self, graph):
        items = graph.to_syllabus_items()
        assert len(items) == 5
        # to_syllabus_items 使用 item_id（不是 id）作为主键
        first = next(i for i in items if i["item_id"] == "1.1")
        assert first["item_title"] == "变量"
        assert first["status"] == "none"
        # 不应有冗余的 id 字段
        assert "id" not in first or first["id"] == first["item_id"]

    def test_to_syllabus_items_with_records(self, graph):
        records = {
            "1.1": MasteryRecord(point_id="1.1", mastery_score=90.0, status="done"),
        }
        items = graph.to_syllabus_items(records)
        item_1_1 = next(i for i in items if i["item_id"] == "1.1")
        assert item_1_1["status"] == "done"
        assert item_1_1["mastery_score"] == 90.0


class TestKnowledgeGraphBuilding:
    """从大纲 dict 构建图谱测试"""

    def test_build_from_syllabus(self):
        syllabus = {
            "topic": "Python",
            "sections": [
                {
                    "id": "1", "title": "基础",
                    "items": [
                        {"id": "1.1", "title": "变量", "description": "变量定义"},
                        {"id": "1.2", "title": "类型", "description": "数据类型"},
                    ],
                },
                {
                    "id": "2", "title": "进阶",
                    "items": [
                        {"id": "2.1", "title": "函数", "description": "函数定义"},
                    ],
                },
            ],
        }
        kg = KnowledgeGraph.from_syllabus_dict(syllabus)
        assert len(kg.points) == 3
        assert kg.get_point("1.1") is not None
        assert kg.get_point("2.1") is not None
        assert kg.get_point("1.1").section_title == "基础"
        assert kg.get_point("2.1").section_title == "进阶"


class TestMasteryModel:
    """掌握度计算模型测试"""

    def test_perfect_score(self):
        """满分测验 + 1次学习 = 高掌握度"""
        score = MasteryModel.calculate(quiz_score=100, attempt_count=1)
        assert score > 70

    def test_low_score(self):
        """低分测验 = 低掌握度"""
        score = MasteryModel.calculate(quiz_score=30, attempt_count=1)
        assert score < 50

    def test_attempt_improvement(self):
        """多次学习应提高掌握度"""
        s1 = MasteryModel.calculate(quiz_score=60, attempt_count=1)
        s2 = MasteryModel.calculate(quiz_score=60, attempt_count=3)
        assert s2 > s1

    def test_prerequisite_impact(self):
        """前置知识掌握度低应拉低总分"""
        s1 = MasteryModel.calculate(quiz_score=80, attempt_count=1, prereq_mastery=100)
        s2 = MasteryModel.calculate(quiz_score=80, attempt_count=1, prereq_mastery=50)
        assert s2 < s1

    def test_pass_threshold(self):
        """70分以上为通过"""
        assert MasteryModel.is_passed(75.0) is True
        assert MasteryModel.is_passed(70.0) is True
        assert MasteryModel.is_passed(69.9) is False
        assert MasteryModel.is_passed(0.0) is False

    def test_prereq_mastery_none(self):
        """无前置知识点时返回 100"""
        point = KnowledgePoint(id="1.1", title="独立知识点")
        score = MasteryModel.get_prereq_mastery(point, {})
        assert score == 100.0

    def test_prereq_mastery_calculation(self):
        """有前置知识点时计算平均分"""
        point = KnowledgePoint(id="2.1", title="函数", prerequisites=["1.1", "1.2"])
        records = {
            "1.1": MasteryRecord(point_id="1.1", mastery_score=80),
            "1.2": MasteryRecord(point_id="1.2", mastery_score=60),
        }
        score = MasteryModel.get_prereq_mastery(point, records)
        assert score == 70.0  # (80 + 60) / 2
