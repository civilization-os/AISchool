"""
数据库模型 - SQLAlchemy ORM
AI School 完整教学流程持久化
"""

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Student(Base):
    """学生表"""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), default="学习者")
    created_at = Column(DateTime, server_default=func.now())

    sessions = relationship("LearningSession", back_populates="student")


class LearningSession(Base):
    """学习会话 - 一个主题的完整学习过程"""
    __tablename__ = "learning_sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject = Column(String(200), nullable=False)           # 学习主题
    status = Column(String(20), default="idle")             # 兼容旧字段
    state_status = Column(String(20), default="idle")       # SessionStatus 枚举值
    course_levels = Column(JSON, default=list)               # 课程等级 [1,2,3]
    completed_item_ids = Column(JSON, default=list)          # 已完成知识点 item_id 列表
    proficiency_data = Column(JSON, default=dict)           # 各子领域熟练度 {domain: score}
    progress_pct = Column(Float, default=0.0)               # 总进度百分比
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    student = relationship("Student", back_populates="sessions")
    syllabus_items = relationship("SyllabusItem", back_populates="session", cascade="all, delete-orphan")
    assessment = relationship("AssessmentRecord", back_populates="session", uselist=False)
    classroom_convos = relationship("ClassroomConversation", back_populates="session", cascade="all, delete-orphan")
    quiz_records = relationship("QuizRecord", back_populates="session", cascade="all, delete-orphan")
    exam_records = relationship("ExamRecord", back_populates="session", cascade="all, delete-orphan")


class SyllabusItem(Base):
    """大纲条目 - 每个知识点的学习状态"""
    __tablename__ = "syllabus_items"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id"), nullable=False)
    section_id = Column(String(10))                         # "1", "2", etc.
    section_title = Column(String(200))                     # 章节名称
    item_id = Column(String(20))                            # "1.1", "1.2", etc.
    level = Column(Integer, default=1)                      # 所属学期等级 1/2/3/4
    item_title = Column(String(200), nullable=False)        # 知识点名称
    item_description = Column(Text)
    status = Column(String(20), default="none")             # none/learning/done
    mastery_score = Column(Float, default=0.0)              # 0-100 掌握度
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    session = relationship("LearningSession", back_populates="syllabus_items")


class AssessmentRecord(Base):
    """入学测评记录"""
    __tablename__ = "assessment_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id"), nullable=False, unique=True)
    questions = Column(JSON)                                # 题目列表
    answers = Column(JSON)                                  # 学生答案
    proficiency_result = Column(JSON)                       # {domain: score, ...}
    question_results = Column(JSON)                         # 详细对错与解析列表
    ai_report = Column(Text)                                # AI 生成的分析报告
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    session = relationship("LearningSession", back_populates="assessment")


class ClassroomConversation(Base):
    """课堂对话记录（支持断线续学）"""
    __tablename__ = "classroom_conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id"), nullable=False)
    item_id = Column(String(20), nullable=False)            # 对应的知识点 id
    item_title = Column(String(200))
    messages = Column(JSON, default=list)                   # [{role, content, timestamp}, ...]
    lesson_content = Column(Text)                           # AI 初始讲解内容
    lesson_plan = Column(JSON, default=dict)                # 结构化教案卡片
    attempt_count = Column(Integer, default=1)              # 上课次数（重学+1）
    started_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    session = relationship("LearningSession", back_populates="classroom_convos")


class QuizRecord(Base):
    """小测验记录"""
    __tablename__ = "quiz_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id"), nullable=False)
    item_id = Column(String(20), nullable=False)
    item_title = Column(String(200))
    questions = Column(JSON)                                # 题目
    answers = Column(JSON)                                  # 学生答案（含图片base64）
    score = Column(Float, default=0.0)                      # 0-100
    passed = Column(Boolean, default=False)                 # 是否通过
    ai_feedback = Column(Text)                              # AI 评语 + 薄弱点分析
    attempt_number = Column(Integer, default=1)             # 第几次尝试
    created_at = Column(DateTime, server_default=func.now())

    session = relationship("LearningSession", back_populates="quiz_records")


class ExamRecord(Base):
    """考试记录（期中/期末）"""
    __tablename__ = "exam_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id"), nullable=False)
    exam_type = Column(String(20), nullable=False)          # "midterm" / "final"
    covered_items = Column(JSON)                            # 覆盖的知识点列表
    questions = Column(JSON)                                # 试卷题目
    answers = Column(JSON)                                  # 学生答案
    score = Column(Float, default=0.0)                      # 总分
    ai_report = Column(Text)                                # AI 批改报告
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    session = relationship("LearningSession", back_populates="exam_records")

class SystemConfig(Base):
    """系统全局配置表 (OpenAI 兼容接口等)"""
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text)
    description = Column(String(200))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
