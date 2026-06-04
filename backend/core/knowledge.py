"""
通用知识点架构 — Knowledge Graph + Learning Path + Mastery Model
"""
from __future__ import annotations
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class PointType(str, Enum):
    """知识点类型"""
    CONCEPT = "concept"       # 概念理解
    SKILL = "skill"           # 技能训练
    EXERCISE = "exercise"     # 练习巩固
    PROJECT = "project"       # 项目实践


class Difficulty(int, Enum):
    """难度等级"""
    REMEMBER = 1    # 识记
    UNDERSTAND = 2  # 理解
    APPLY = 3       # 应用
    ANALYZE = 4     # 分析
    EVALUATE = 5    # 评价/创造


# ─── 单个知识点定义 ────────────────────────────────────

@dataclass
class KnowledgePoint:
    """
    知识点的完整定义

    Attributes:
        id: 唯一标识，如 "1.1"
        title: 知识点名称
        description: 简短说明
        point_type: 类型（概念/技能/练习/项目）
        difficulty: 难度 1-5
        estimated_minutes: 预计学习时间（分钟）
        prerequisites: 前置知识点 ID 列表
        tags: 标签，如 ["python", "基础"]
        section_id: 所属章节 ID
        section_title: 所属章节名称
        sort_order: 章内排序
    """
    id: str
    title: str
    description: str = ""
    point_type: PointType = PointType.CONCEPT
    difficulty: Difficulty = Difficulty.REMEMBER
    estimated_minutes: int = 15
    prerequisites: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    section_id: str = ""
    section_title: str = ""
    sort_order: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "point_type": self.point_type.value,
            "difficulty": self.difficulty.value,
            "estimated_minutes": self.estimated_minutes,
            "prerequisites": self.prerequisites,
            "tags": self.tags,
            "section_id": self.section_id,
            "section_title": self.section_title,
            "sort_order": self.sort_order,
        }


# ─── 知识点掌握度 ──────────────────────────────────────

@dataclass
class MasteryRecord:
    """
    学生对某个知识点的掌握记录

    Attributes:
        point_id: 知识点 ID
        mastery_score: 掌握度 0-100
        status: none | learning | done
        attempt_count: 学习次数
        best_quiz_score: 最高测验分
        time_spent_minutes: 累计学习分钟
    """
    point_id: str
    mastery_score: float = 0.0
    status: str = "none"
    attempt_count: int = 0
    best_quiz_score: float = 0.0
    time_spent_minutes: int = 0


# ─── 学习路径 ──────────────────────────────────────────

@dataclass
class LearningPath:
    """
    计算出的最优学习路径

    Attributes:
        point_ids: 按学习顺序排列的知识点 ID 列表
        estimated_total_minutes: 预计总时长
        parallel_groups: 可并行学习的知识点组（同级无依赖）
    """
    point_ids: List[str] = field(default_factory=list)
    estimated_total_minutes: int = 0
    parallel_groups: List[List[str]] = field(default_factory=list)


# ─── 知识点图谱 ────────────────────────────────────────

class KnowledgeGraph:
    """
    知识点图谱 — 管理知识点及其前置依赖关系

    用法:
        kg = KnowledgeGraph()
        kg.add_point(KnowledgePoint(id="1.1", title="变量"))
        kg.add_point(KnowledgePoint(id="1.2", title="函数", prerequisites=["1.1"]))
        path = kg.calculate_path()
    """

    def __init__(self):
        self._points: Dict[str, KnowledgePoint] = {}

    # ── 构建 ──────────────────────────────────────────

    def add_point(self, point: KnowledgePoint):
        """添加一个知识点"""
        self._points[point.id] = point

    def add_section(self, section_id: str, section_title: str,
                    items: List[Dict]) -> List[KnowledgePoint]:
        """批量添加一个章节内的知识点"""
        points = []
        for i, item in enumerate(items):
            point = KnowledgePoint(
                id=item.get("id", f"{section_id}.{i+1}"),
                title=item.get("title", ""),
                description=item.get("description", ""),
                section_id=section_id,
                section_title=section_title,
                prerequisites=item.get("prerequisites", []),
                difficulty=Difficulty(item.get("difficulty", 1)),
                point_type=PointType(item.get("point_type", "concept")),
                estimated_minutes=item.get("estimated_minutes", 15),
                tags=item.get("tags", []),
                sort_order=i,
            )
            self.add_point(point)
            points.append(point)
        return points

    def build_from_syllabus(self, syllabus: dict) -> List[KnowledgePoint]:
        """从大纲 dict 批量构建"""
        all_points = []
        for sec in syllabus.get("sections", []):
            items = sec.get("items", [])
            points = self.add_section(
                section_id=sec.get("id", ""),
                section_title=sec.get("title", ""),
                items=items,
            )
            all_points.extend(points)
        return all_points

    @property
    def points(self) -> List[KnowledgePoint]:
        return list(self._points.values())

    @property
    def point_ids(self) -> List[str]:
        return list(self._points.keys())

    def get_point(self, point_id: str) -> Optional[KnowledgePoint]:
        return self._points.get(point_id)

    # ── 前置依赖校验 ──────────────────────────────────

    def validate_prerequisites(self) -> List[str]:
        """
        校验前置依赖是否完整（所有前置知识点都存在）
        返回缺失的前置知识点 ID 列表
        """
        missing = []
        existing = set(self._points.keys())
        for pid, point in self._points.items():
            for prereq in point.prerequisites:
                if prereq not in existing:
                    missing.append(f"{pid} 依赖 {prereq} 但不存在")
        return missing

    def get_unlocked_points(self, completed_ids: Set[str]) -> List[KnowledgePoint]:
        """获取当前已解锁（前置条件全部满足）的知识点"""
        result = []
        for pid, point in self._points.items():
            if pid in completed_ids:
                continue
            prereqs = set(point.prerequisites)
            if prereqs.issubset(completed_ids):
                result.append(point)
        return sorted(result, key=lambda p: p.sort_order)

    # ── 拓扑排序（学习顺序） ──────────────────────────

    def topological_sort(self) -> List[str]:
        """
        拓扑排序 → 学习顺序
        使用 Kahn 算法
        """
        in_degree: Dict[str, int] = {pid: 0 for pid in self._points}
        adj: Dict[str, List[str]] = {pid: [] for pid in self._points}

        for pid, point in self._points.items():
            for prereq in point.prerequisites:
                if prereq in adj:
                    adj[prereq].append(pid)
                    in_degree[pid] = in_degree.get(pid, 0) + 1

        queue = [pid for pid, deg in in_degree.items() if deg == 0]
        sorted_ids = []

        while queue:
            # 按 sort_order 排序同层节点
            queue.sort(key=lambda pid: self._points[pid].sort_order)
            pid = queue.pop(0)
            sorted_ids.append(pid)

            for neighbor in adj[pid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 如果有环，未排序的节点追加到最后
        remaining = [pid for pid in self._points if pid not in sorted_ids]
        return sorted_ids + remaining

    def calculate_path(self, completed_ids: Optional[Set[str]] = None) -> LearningPath:
        """
        计算最优学习路径
        - 拓扑排序保证前置依赖
        - 计算并行组（同级无依赖的可并行学习）
        """
        completed = completed_ids or set()
        all_sorted = self.topological_sort()

        # 过滤已完成
        to_learn = [pid for pid in all_sorted if pid not in completed]

        # 计算并行组
        parallel_groups: List[List[str]] = []
        processed: Set[str] = set()

        for pid in to_learn:
            point = self._points[pid]
            prereq_set = set(point.prerequisites)
            # 这个知识点依赖的所有知识点
            depends_on_processed = prereq_set.issubset(processed)

            if depends_on_processed and parallel_groups:
                # 检查是否能加入当前组
                can_parallel = True
                for existing in parallel_groups[-1]:
                    existing_point = self._points[existing]
                    if pid in existing_point.prerequisites or existing in point.prerequisites:
                        can_parallel = False
                        break
                if can_parallel:
                    parallel_groups[-1].append(pid)
                    processed.add(pid)
                    continue

            parallel_groups.append([pid])
            processed.add(pid)

        total_minutes = sum(
            self._points[pid].estimated_minutes
            for pid in to_learn
            if pid in self._points
        )

        return LearningPath(
            point_ids=to_learn,
            estimated_total_minutes=total_minutes,
            parallel_groups=parallel_groups,
        )

    # ── 序列化 ────────────────────────────────────────

    def to_syllabus_items(self, mastery_records: Dict[str, MasteryRecord] = None) -> List[dict]:
        """导出为 syllabus_items 格式（给 state 和 DB 使用）"""
        records = mastery_records or {}
        items = []
        for pid, point in self._points.items():
            rec = records.get(pid)
            items.append({
                "item_id": point.id,
                "item_title": point.title,
                "item_description": point.description,
                "point_type": point.point_type.value,
                "difficulty": point.difficulty.value,
                "estimated_minutes": point.estimated_minutes,
                "prerequisites": point.prerequisites,
                "tags": point.tags,
                "status": rec.status if rec else "none",
                "mastery_score": rec.mastery_score if rec else 0.0,
                "attempt_count": rec.attempt_count if rec else 0,
                "sort_order": point.sort_order,
            })
        return items

    @classmethod
    def from_syllabus_dict(cls, syllabus: dict) -> "KnowledgeGraph":
        """从大纲 dict 构建完整图谱"""
        kg = cls()
        kg.build_from_syllabus(syllabus)
        return kg


# ─── 掌握度计算 ────────────────────────────────────────

class MasteryModel:
    """
    掌握度计算模型

    综合以下因素计算掌握度：
    - 测验得分 (quiz_weight=0.6)
    - 学习次数 (attempt_weight=0.2)
    - 前置知识掌握度 (prerequisite_weight=0.2)
    """

    QUIZ_WEIGHT = 0.6
    ATTEMPT_WEIGHT = 0.2
    PREREQUISITE_WEIGHT = 0.2
    PASS_THRESHOLD = 70.0

    @classmethod
    def calculate(cls, quiz_score: float, attempt_count: int,
                  prereq_mastery: float = 100.0, max_attempts: int = 5) -> float:
        """
        计算综合掌握度

        Args:
            quiz_score: 最近一次测验得分 (0-100)
            attempt_count: 学习次数
            prereq_mastery: 前置知识平均掌握度 (0-100)
            max_attempts: 学习次数达到此值不再衰减

        Returns:
            综合掌握度 0-100
        """
        # 测验得分
        quiz_part = quiz_score * cls.QUIZ_WEIGHT

        # 学习次数：前几次加分，多次后稳定
        attempt_factor = min(attempt_count / max_attempts, 1.0)
        attempt_part = attempt_factor * 100 * cls.ATTEMPT_WEIGHT

        # 前置知识
        prereq_part = prereq_mastery * cls.PREREQUISITE_WEIGHT

        return round(quiz_part + attempt_part + prereq_part, 1)

    @classmethod
    def is_passed(cls, mastery_score: float) -> bool:
        return mastery_score >= cls.PASS_THRESHOLD

    @classmethod
    def get_prereq_mastery(cls, point: KnowledgePoint,
                           records: Dict[str, MasteryRecord]) -> float:
        """计算某知识点所有前置知识的平均掌握度"""
        prereq_ids = point.prerequisites
        if not prereq_ids:
            return 100.0
        scores = []
        for pid in prereq_ids:
            rec = records.get(pid)
            scores.append(rec.mastery_score if rec else 0.0)
        return sum(scores) / len(scores) if scores else 100.0
