"""
数据库 CRUD 操作
"""

from sqlalchemy.orm import Session
from typing import Optional, List
from db.models import (
    Student, LearningSession, SyllabusItem,
    AssessmentRecord, ClassroomConversation, QuizRecord, ExamRecord,
    SystemConfig
)


# ─── Student ─────────────────────────────────────────────

def get_or_create_student(db: Session, name: str = "学习者") -> Student:
    student = db.query(Student).filter(Student.name == name).first()
    if not student:
        student = Student(name=name)
        db.add(student)
        db.commit()
        db.refresh(student)
    return student


# ─── LearningSession ─────────────────────────────────────

def create_session(db: Session, student_id: int, subject: str) -> LearningSession:
    session = LearningSession(
        student_id=student_id,
        subject=subject,
        status="assessing",
        state_status="assessing",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: int) -> Optional[LearningSession]:
    return db.query(LearningSession).filter(LearningSession.id == session_id).first()


def get_student_sessions(db: Session, student_id: int) -> List[LearningSession]:
    return db.query(LearningSession).filter(
        LearningSession.student_id == student_id
    ).order_by(LearningSession.updated_at.desc()).all()


def update_session_status(db: Session, session_id: int, status: str) -> LearningSession:
    session = get_session(db, session_id)
    if session:
        session.status = status
        db.commit()
        db.refresh(session)
    return session


def update_session_progress(db: Session, session_id: int) -> float:
    """重新计算并保存进度百分比"""
    items = db.query(SyllabusItem).filter(SyllabusItem.session_id == session_id).all()
    if not items:
        return 0.0
    done = sum(1 for i in items if i.status == "done")
    pct = round(done / len(items) * 100, 1)
    session = get_session(db, session_id)
    if session:
        session.progress_pct = pct
        db.commit()
    return pct


def delete_session(db: Session, session_id: int) -> bool:
    """级联删除会话，并清空该主题的评测缓存"""
    session = get_session(db, session_id)
    if not session:
        return False
    # 清空评测缓存，确保下次进入同一主题时是新题目
    cache_key = f"assess_cache_{session.subject}"
    print(f"DEBUG: Deleting assessment cache for subject: {session.subject} (key: {cache_key})")
    delete_config(db, cache_key)

    # 手动删除关联的 AssessmentRecord，避免外键约束冲突
    assessment = db.query(AssessmentRecord).filter(AssessmentRecord.session_id == session_id).first()
    if assessment:
        db.delete(assessment)
    db.delete(session)
    db.commit()
    return True


# ─── SyllabusItem ─────────────────────────────────────────

def bulk_create_syllabus(db: Session, session_id: int, syllabus_data: dict):
    """从 AI 生成的大纲数据批量创建条目"""
    sort = 0
    for section in syllabus_data.get("sections", []):
        for item in section.get("items", []):
            db_item = SyllabusItem(
                session_id=session_id,
                section_id=section["id"],
                section_title=section["title"],
                item_id=item["id"],
                item_title=item["title"],
                item_description=item.get("description", ""),
                level=item.get("level", 1),
                sort_order=sort
            )
            db.add(db_item)
            sort += 1
    db.commit()


def delete_syllabus_items(db: Session, session_id: int):
    """删除会话的所有大纲条目"""
    db.query(SyllabusItem).filter(
        SyllabusItem.session_id == session_id
    ).delete(synchronize_session=False)
    db.commit()


def get_syllabus_items(db: Session, session_id: int) -> List[SyllabusItem]:
    return db.query(SyllabusItem).filter(
        SyllabusItem.session_id == session_id
    ).order_by(SyllabusItem.sort_order).all()


def update_item_status(db: Session, session_id: int, item_db_id: int,
                       status: str, score: float = None) -> SyllabusItem:
    item = db.query(SyllabusItem).filter(
        SyllabusItem.id == item_db_id,
        SyllabusItem.session_id == session_id
    ).first()
    if item:
        item.status = status
        if score is not None:
            item.mastery_score = score
        db.commit()
        db.refresh(item)
        update_session_progress(db, session_id)
    return item


# ─── AssessmentRecord ──────────────────────────────────────

def create_assessment(db: Session, session_id: int, questions: list) -> AssessmentRecord:
    existing = db.query(AssessmentRecord).filter(AssessmentRecord.session_id == session_id).first()
    if existing:
        existing.questions = questions
        existing.completed = False
        db.commit()
        db.refresh(existing)
        return existing
    record = AssessmentRecord(session_id=session_id, questions=questions)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_assessment_cache(db: Session, subject: str) -> Optional[list]:
    """获取主题维度的评测题目缓存"""
    key = f"assess_cache_{subject}"
    val = get_config(db, key)
    if val:
        try:
            import json
            return json.loads(val)
        except:
            return None
    return None


def set_assessment_cache(db: Session, subject: str, questions: list):
    """设置主题维度的评测题目缓存"""
    key = f"assess_cache_{subject}"
    import json
    val = json.dumps(questions, ensure_ascii=False)
    set_config(db, key, val, description=f"Assessment questions cache for {subject}")


def complete_assessment(db: Session, session_id: int, answers: list,
                        proficiency: dict, report: str, overall_score: float = 0.0,
                        question_results: list = None) -> AssessmentRecord:
    record = db.query(AssessmentRecord).filter(AssessmentRecord.session_id == session_id).first()
    if record:
        record.answers = answers
        # 将总体评分也存入熟练度结果中，方便前端读取
        proficiency["__overall__"] = overall_score
        record.proficiency_result = proficiency
        record.ai_report = report
        record.question_results = question_results
        record.completed = True
        db.commit()
        db.refresh(record)
    # 同步更新 session 的熟练度数据
    session = get_session(db, session_id)
    if session:
        session.proficiency_data = proficiency
        session.status = "learning"
        db.commit()
    return record


# ─── ClassroomConversation ──────────────────────────────────

def get_or_create_conversation(db: Session, session_id: int,
                                item_id: str, item_title: str,
                                lesson_content: str) -> ClassroomConversation:
    existing = db.query(ClassroomConversation).filter(
        ClassroomConversation.session_id == session_id,
        ClassroomConversation.item_id == item_id
    ).first()
    if existing:
        return existing
    convo = ClassroomConversation(
        session_id=session_id,
        item_id=item_id,
        item_title=item_title,
        lesson_content=lesson_content,
        messages=[]
    )
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


def append_message(db: Session, convo_id: int, role: str, content: str):
    import datetime
    convo = db.query(ClassroomConversation).filter(ClassroomConversation.id == convo_id).first()
    if convo:
        msgs = list(convo.messages or [])
        msgs.append({"role": role, "content": content,
                     "ts": datetime.datetime.utcnow().isoformat()})
        convo.messages = msgs
        db.commit()


def increment_attempt(db: Session, convo_id: int):
    """重学时增加尝试次数，清空消息"""
    convo = db.query(ClassroomConversation).filter(ClassroomConversation.id == convo_id).first()
    if convo:
        convo.attempt_count += 1
        convo.messages = []
        db.commit()
        db.refresh(convo)
    return convo


# ─── QuizRecord ───────────────────────────────────────────

def create_quiz(db: Session, session_id: int, item_id: str, item_title: str,
                questions: list, attempt_number: int = 1) -> QuizRecord:
    record = QuizRecord(
        session_id=session_id,
        item_id=item_id,
        item_title=item_title,
        questions=questions,
        attempt_number=attempt_number
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def complete_quiz(db: Session, quiz_id: int, answers: list,
                  score: float, passed: bool, feedback: str) -> QuizRecord:
    record = db.query(QuizRecord).filter(QuizRecord.id == quiz_id).first()
    if record:
        record.answers = answers
        record.score = score
        record.passed = passed
        record.ai_feedback = feedback
        db.commit()
        db.refresh(record)
    return record


def save_quiz_answers(db: Session, quiz_id: int, answers: list) -> Optional[QuizRecord]:
    """暂存测验答案"""
    record = db.query(QuizRecord).filter(QuizRecord.id == quiz_id).first()
    if record:
        record.answers = answers
        db.commit()
        db.refresh(record)
    return record


def get_item_quiz_count(db: Session, session_id: int, item_id: str) -> int:
    return db.query(QuizRecord).filter(
        QuizRecord.session_id == session_id,
        QuizRecord.item_id == item_id
    ).count()


# ─── ExamRecord ───────────────────────────────────────────

def get_exam_unlock_status(db: Session, session_id: int) -> dict:
    """检查期中/期末考试解锁状态"""
    items = get_syllabus_items(db, session_id)
    if not items:
        return {"midterm": False, "final": False, "progress": 0}

    total = len(items)
    done = sum(1 for i in items if i.status == "done")
    pct = done / total * 100

    # 查是否已有对应考试
    exams = db.query(ExamRecord).filter(ExamRecord.session_id == session_id).all()
    has_midterm = any(e.exam_type == "midterm" for e in exams)
    has_final = any(e.exam_type == "final" for e in exams)

    return {
        "midterm": pct >= 50 and not has_midterm,
        "final": pct >= 90 and not has_final,
        "progress": round(pct, 1),
        "done_count": done,
        "total_count": total,
        "has_midterm": has_midterm,
        "has_final": has_final
    }


def create_exam(db: Session, session_id: int, exam_type: str,
                covered_items: list, questions: list) -> ExamRecord:
    record = ExamRecord(
        session_id=session_id,
        exam_type=exam_type,
        covered_items=covered_items,
        questions=questions
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def complete_exam(db: Session, exam_id: int, answers: list,
                  score: float, report: str) -> ExamRecord:
    record = db.query(ExamRecord).filter(ExamRecord.id == exam_id).first()
    if record:
        record.answers = answers
        record.score = score
        record.ai_report = report
        record.completed = True
        db.commit()
        db.refresh(record)
    return record


# ─── SystemConfig ──────────────────────────────────────────

def get_config(db: Session, key: str) -> Optional[str]:
    cfg = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return cfg.value if cfg else None


def set_config(db: Session, key: str, value: str, description: str = None):
    cfg = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if cfg:
        cfg.value = value
        if description:
            cfg.description = description
    else:
        cfg = SystemConfig(key=key, value=value, description=description)
        db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


def get_all_configs(db: Session) -> List[SystemConfig]:
    return db.query(SystemConfig).all()


def delete_config(db: Session, key: str):
    db.query(SystemConfig).filter(SystemConfig.key == key).delete(synchronize_session=False)
    db.commit()
