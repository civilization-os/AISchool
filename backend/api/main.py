"""
FastAPI Web API — AI School 完整教学流程
"""

from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any, AsyncGenerator
import uvicorn, os, base64, traceback
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import json

from db.database import get_db, create_tables
from db import crud
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from core.direct_llm import direct_teach, direct_practice
from core.assessment_llm import generate_assessment_questions_stream
from core.classroom_llm import generate_mini_quiz_stream
from core.exam_llm import generate_exam_stream
from core.learning_crew import LearningEngine
from core.state import SessionStatus

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时自动建表"""
    try:
        create_tables()
        print("[OK] 数据库表已创建/确认")
    except Exception as e:
        print(f"[WARN] 数据库初始化警告: {e}")
    yield

app = FastAPI(
    title="AI School API", 
    description="完整 AI 课堂系统", 
    version="2.0.0",
    lifespan=lifespan
)

# CORS — 允许所有访问（支持小程序迁移与外部部署）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_prefix_middleware(request: Request, call_next):
    # 如果路径以 /api/ 开头，则去掉 /api 前缀以匹配后端路由
    if request.url.path.startswith("/api/"):
        request.scope["path"] = request.url.path[4:]
    return await call_next(request)


# ─── 健康检查 ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0", "service": "AI School"}


# ════════════════════════════════════════════════════════
# 会话管理
# ════════════════════════════════════════════════════════

class CreateSessionRequest(BaseModel):
    subject: str
    student_name: str = "学习者"
    levels: List[int] = [1]       # 课程等级 [1] 或 [1,2] 或 [1,2,3]


class NormalizeCourseRequest(BaseModel):
    query: str                     # 用户输入，如 "微积分" "python"


@app.post("/course/normalize")
def normalize_course(req: NormalizeCourseRequest):
    """规整课程名称，建议等级"""
    from core.llm import get_chat_model
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = get_chat_model(temperature=0.3)
    system = "你是课程规划专家。返回 JSON。"
    user = f"""用户输入了课程「{req.query}」。请：
1. 规整为标准的课程名称
2. 建议合理的学期等级数（1-4）

JSON: {{"name":"标准课程名","levels":[1,2,3],"description":"简短说明"}}"""

    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    from core.nodes import _parse_json
    result = _parse_json(resp.content, {"name": req.query, "levels": [1], "description": ""})
    # 确保 levels 合法
    if not isinstance(result.get("levels"), list) or not result["levels"]:
        result["levels"] = [1]
    return result


@app.post("/session/create")
def create_session_api(req: CreateSessionRequest, db: Session = Depends(get_db)):
    student = crud.get_or_create_student(db, req.student_name)
    session = crud.create_session(db, student.id, req.subject)
    # 保存课程等级
    session.course_levels = req.levels
    db.commit()
    return {
        "session_id": session.id,
        "student_id": student.id,
        "subject": session.subject,
        "status": session.status,
        "levels": req.levels,
    }


@app.get("/session/{session_id}")
def get_session_api(session_id: int, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    items = crud.get_syllabus_items(db, session_id)
    unlock = crud.get_exam_unlock_status(db, session_id)
    
    # 获取测评记录（无论是否完成）
    assessment_info = None
    record = db.query(crud.AssessmentRecord).filter(crud.AssessmentRecord.session_id == session_id).first()
    if record:
        assessment_info = {
            "id": record.id,
            "completed": record.completed,
            "has_questions": bool(record.questions),
            "answers_count": len(record.answers) if record.answers else 0
        }
        if record.completed:
            assessment_info.update({
                "questions": record.questions,
                "answers": record.answers,
                "proficiency_result": record.proficiency_result,
                "ai_report": record.ai_report,
                "question_results": record.question_results
            })

    return {
        "session_id": session.id,
        "subject": session.subject,
        "status": session.state_status or session.status,
        "progress_pct": session.progress_pct,
        "proficiency_data": session.proficiency_data,
        "course_levels": session.course_levels or [1],
        "completed_item_ids": session.completed_item_ids or [],
        "assessment": assessment_info,
        "syllabus_items": [
            {"id": i.id, "section_id": i.section_id, "section_title": i.section_title,
             "item_id": i.item_id, "item_title": i.item_title, "item_description": i.item_description,
             "status": i.status, "mastery_score": i.mastery_score, "sort_order": i.sort_order,
             "level": i.level}
            for i in items
        ],
        "exam_unlock": unlock,
    }


@app.get("/session/student/{student_name}")
def get_student_sessions_api(student_name: str, db: Session = Depends(get_db)):
    student = crud.get_or_create_student(db, student_name)
    sessions = crud.get_student_sessions(db, student.id)
    return {
        "student_id": student.id,
        "sessions": [
            {"session_id": s.id, "subject": s.subject, "status": s.status,
             "progress_pct": s.progress_pct,
             "created_at": s.created_at.isoformat() if s.created_at else None,
             "updated_at": s.updated_at.isoformat() if s.updated_at else None}
            for s in sessions
        ]
    }


@app.delete("/session/{session_id}")
def delete_session_api(session_id: int, db: Session = Depends(get_db)):
    success = crud.delete_session(db, session_id)
    if not success:
        raise HTTPException(404, "会话不存在或已删除")
    return {"status": "success", "session_id": session_id}


# ════════════════════════════════════════════════════════
# 入学测评
# ════════════════════════════════════════════════════════

@app.post("/assessment/start/{session_id}")
def start_assessment(session_id: int, open_count: int = 3, force_new: bool = False, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
        
    # 如果强制刷新，清空该主题的全局缓存
    if force_new:
        print(f"DEBUG: force_new=True, clearing cache for {session.subject}")
        crud.delete_config(db, f"assess_cache_{session.subject}")
    
    # 检查是否存在已完成或未完成的测评
    existing_record = db.query(crud.AssessmentRecord).filter(crud.AssessmentRecord.session_id == session_id).first()
    if existing_record and existing_record.questions and not force_new:
        print(f"DEBUG: Found existing record for session {session_id}, returning it.")
        if existing_record.completed:
             return {
                "assessment_id": existing_record.id,
                "session_id": session_id,
                "subject": session.subject,
                "questions": existing_record.questions,
                "answers": existing_record.answers or [],
                "completed": True,
                "proficiency_result": existing_record.proficiency_result,
                "ai_report": existing_record.ai_report,
                "question_results": existing_record.question_results
            }
        return {
            "assessment_id": existing_record.id,
            "session_id": session_id,
            "subject": session.subject,
            "questions": existing_record.questions,
            "answers": existing_record.answers or [],
            "total": len(existing_record.questions),
        }
        
    # 增加：检查主题维度的全局缓存
    cached_questions = crud.get_assessment_cache(db, session.subject)
    if cached_questions:
        print(f"DEBUG: Found global cache for {session.subject}, assigning to session {session_id}")
        record = crud.create_assessment(db, session_id, cached_questions)
        return {
            "assessment_id": record.id,
            "session_id": session_id,
            "subject": session.subject,
            "questions": cached_questions,
            "total": len(cached_questions),
            "cached": True
        }

    # 使用 LearningEngine 生成题目
    engine = LearningEngine(session_id, f"student_{session.student_id}")
    result = engine.start_assessment(session.subject)
    questions = result.get("assessment_questions", [])
    if not questions:
        raise HTTPException(500, "生成题目失败，请重试")

    # 更新状态
    session.state_status = SessionStatus.ASSESSING
    db.commit()

    # 存入全局缓存和 DB
    crud.set_assessment_cache(db, session.subject, questions)
    record = crud.create_assessment(db, session_id, questions)
    return {
        "assessment_id": record.id,
        "session_id": session_id,
        "subject": session.subject,
        "questions": questions,
        "total": len(questions),
        "state_status": session.state_status,
    }

@app.post("/assessment/start_stream/{session_id}")
def start_assessment_stream(session_id: int, open_count: int = 3, force_new: bool = False, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    
    if force_new:
        crud.delete_config(db, f"assess_cache_{session.subject}")
        # 如果还要删除旧的 record
        old_record = db.query(crud.AssessmentRecord).filter(crud.AssessmentRecord.session_id == session_id).first()
        if old_record:
            db.delete(old_record)
            db.commit()

    # 断线重连
    existing_record = db.query(crud.AssessmentRecord).filter(crud.AssessmentRecord.session_id == session_id).first()
    if existing_record and existing_record.questions and not force_new:
        # 如果已完成或已有题目，直接返回
        def quick_stream():
            event = {
                "status": "done",
                "questions": existing_record.questions,
                "answers": existing_record.answers or [],
                "assessment_id": existing_record.id,
                "completed": existing_record.completed,
                "total": len(existing_record.questions)
            }
            if existing_record.completed:
                event.update({
                    "proficiency_result": existing_record.proficiency_result,
                    "ai_report": existing_record.ai_report,
                    "question_results": existing_record.question_results
                })
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        return StreamingResponse(quick_stream(), media_type="text/event-stream")
    
    subject = session.subject  # 提前取出，避免在生成器内依赖外部 Session

    def event_stream():
        # 生成器内部自己创建独立的 DB Session，与路由函数的 Depends 完全解耦
        from db.database import SessionLocal
        stream_db = SessionLocal()
        try:
            # 增加：流式也先检查缓存
            cached_qs = crud.get_assessment_cache(stream_db, subject)
            if cached_qs:
                record = crud.create_assessment(stream_db, session_id, cached_qs)
                event = {
                    "status": "done",
                    "questions": cached_qs,
                    "answers": [],
                    "assessment_id": record.id,
                    "total": len(cached_qs),
                    "cached": True
                }
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                return

            for event in generate_assessment_questions_stream(subject, count=10, open_count=open_count):
                if event["status"] == "done":
                    questions = event.get("questions", [])
                    if questions:
                        # 存入全局缓存
                        crud.set_assessment_cache(stream_db, subject, questions)
                        record = crud.create_assessment(stream_db, session_id, questions)
                        event["assessment_id"] = record.id
                        event["total"] = len(questions)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            import json
            traceback.print_exc()
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            stream_db.close()
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")


class SubmitAssessmentRequest(BaseModel):
    answers: List[str]      # 与 questions 等长，每题一个答案字符串


@app.post("/assessment/submit/{session_id}")
def submit_assessment(session_id: int, req: SubmitAssessmentRequest, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    record = db.query(crud.AssessmentRecord).filter_by(session_id=session_id).first()
    if not record:
        raise HTTPException(404, "测评记录不存在，请先调用 /assessment/start")

    # 使用 LearningEngine 批改
    engine = LearningEngine(session_id, f"student_{session.student_id}")
    result = engine.submit_assessment(record.questions, req.answers, session.subject)
    assessment_result = result.get("assessment_result", {})

    proficiency = assessment_result.get("proficiency", {})
    report = assessment_result.get("report", "")
    overall_score = assessment_result.get("overall_score", 0.0)
    question_results = assessment_result.get("question_results", [])

    record = crud.complete_assessment(db, session_id, req.answers, proficiency, report, overall_score, question_results)

    # 更新状态机状态
    session = crud.get_session(db, session_id)
    if session:
        session.state_status = SessionStatus.ASSESSED
        db.commit()

    return {
        "session_id": session_id,
        "proficiency": proficiency,
        "report": report,
        "overall_score": overall_score,
        "question_results": question_results,
        "state_status": SessionStatus.ASSESSED,
    }


# ════════════════════════════════════════════════════════
# 跳过入学测评
# ════════════════════════════════════════════════════════

@app.post("/assessment/skip/{session_id}")
def skip_assessment(session_id: int, db: Session = Depends(get_db)):
    """跳过入学测评，直接进入 ASSESSED 状态"""
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")

    # 检查是否已有测评
    from db.models import AssessmentRecord
    record = db.query(AssessmentRecord).filter(
        AssessmentRecord.session_id == session_id
    ).first()

    if not record:
        # 创建一条空的测评记录
        record = AssessmentRecord(
            session_id=session_id,
            questions=[],
            answers=[],
            completed=True,
            proficiency_result={"__overall__": 0},
            ai_report="",
            question_results=[],
        )
        db.add(record)

    session.state_status = SessionStatus.ASSESSED
    session.status = "assessed"
    db.commit()

    return {
        "session_id": session_id,
        "state_status": SessionStatus.ASSESSED,
        "message": "已跳过入学测评",
    }


# ════════════════════════════════════════════════════════
# 大纲（持久化）
# ════════════════════════════════════════════════════════

class GenerateSyllabusRequest(BaseModel):
    topic: str


@app.post("/syllabus/generate/{session_id}")
def generate_syllabus_for_session(session_id: int, req: GenerateSyllabusRequest,
                                   db: Session = Depends(get_db),
                                   force: bool = False):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")

    # force=True: 清空现有大纲和进度
    if force:
        crud.delete_syllabus_items(db, session_id)
        session.progress_pct = 0.0
        session.proficiency_data = {}

    # 获取课程等级
    levels = session.course_levels or [1]

    # 使用 LearningEngine 生成大纲（支持多等级）
    engine = LearningEngine(session_id, f"student_{session.student_id}")
    syllabus = engine.generate_syllabus(req.topic or session.subject, levels=levels)
    if not syllabus or not syllabus.get("sections"):
        raise HTTPException(500, "大纲生成失败")

    # 持久化到 DB
    crud.bulk_create_syllabus(db, session_id, syllabus)
    items = crud.get_syllabus_items(db, session_id)

    # 更新状态
    session.state_status = SessionStatus.SYLLABUS_READY
    session.status = "learning"
    db.commit()

    return {
        "session_id": session_id,
        "syllabus": syllabus,
        "items_created": len(items),
        "state_status": SessionStatus.SYLLABUS_READY,
        "course_levels": levels,
        "regenerated": force,
    }


class UpdateItemStatusRequest(BaseModel):
    status: str             # none/learning/done
    mastery_score: Optional[float] = None


@app.post("/syllabus/item/{item_db_id}/complete")
def complete_syllabus_item(item_db_id: int, db: Session = Depends(get_db)):
    """标记知识点完成，更新进度"""
    item = db.query(crud.SyllabusItem).filter(crud.SyllabusItem.id == item_db_id).first()
    if not item:
        raise HTTPException(404, "知识点不存在")

    # 更新状态
    item.status = "done"
    item.mastery_score = item.mastery_score or 85.0

    # 更新 session 进度
    session = db.query(crud.LearningSession).filter(crud.LearningSession.id == item.session_id).first()
    if session:
        completed = list(session.completed_item_ids or [])
        if item.item_id not in completed:
            completed.append(item.item_id)
        session.completed_item_ids = completed

        total = db.query(crud.SyllabusItem).filter(crud.SyllabusItem.session_id == session.id).count()
        session.progress_pct = round(len(completed) / total * 100, 1) if total else 0
        session.state_status = SessionStatus.ITEM_DONE

    db.commit()

    return {
        "item_id": item_db_id,
        "status": "done",
        "progress_pct": session.progress_pct if session else 0,
    }


@app.put("/syllabus/item/{item_db_id}")
def update_item_status(item_db_id: int, req: UpdateItemStatusRequest,
                       db: Session = Depends(get_db)):
    item = db.query(crud.SyllabusItem).filter(crud.SyllabusItem.id == item_db_id).first()
    if not item:
        raise HTTPException(404, "条目不存在")
    updated = crud.update_item_status(db, item.session_id, item_db_id, req.status, req.mastery_score)
    progress = crud.update_session_progress(db, item.session_id)
    return {"item_id": item_db_id, "status": updated.status, "progress_pct": progress}


@app.post("/assessment/save_answers/{session_id}")
def save_assessment_answers(session_id: int, req: dict, db: Session = Depends(get_db)):
    """保存测评进度（中间答案）"""
    record = db.query(crud.AssessmentRecord).filter(crud.AssessmentRecord.session_id == session_id).first()
    if not record:
        # 如果记录还没建立（还在生成中或者没点开始），静默返回成功，避免前端 log 报错
        return {"status": "skipped", "message": "record not found yet"}
    if record.completed:
        raise HTTPException(400, "测评已完成，无法修改答案")
    
    # 获取前端传来的 answers 数组
    answers = req.get("answers", [])
    record.answers = answers
    db.commit()
    return {"status": "success", "session_id": session_id}


# ════════════════════════════════════════════════════════
# 课堂
# ════════════════════════════════════════════════════════

class StartLessonRequest(BaseModel):
    item_db_id: int         # SyllabusItem.id
    reteach: bool = False   # 是否重新上课（小测验未过）


@app.post("/classroom/start/{session_id}")
def classroom_start(session_id: int, req: StartLessonRequest, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    item = db.query(crud.SyllabusItem).filter(
        crud.SyllabusItem.id == req.item_db_id,
        crud.SyllabusItem.session_id == session_id
    ).first()
    if not item:
        raise HTTPException(404, "知识点不存在")

    # 获取或创建课堂对话
    convo = db.query(crud.ClassroomConversation).filter_by(
        session_id=session_id, item_id=item.item_id
    ).first()

    attempt = 1
    if convo and req.reteach:
        crud.increment_attempt(db, convo.id)
        convo = db.query(crud.ClassroomConversation).filter_by(id=convo.id).first()
        attempt = convo.attempt_count
    elif convo and not req.reteach:
        # 断线续学：返回已有内容
        lesson_plan = convo.lesson_plan or {}
        if not lesson_plan.get("cards"):
            from core.nodes import _build_lesson_plan

            lesson_plan = _build_lesson_plan(convo.lesson_content or "", session.subject, convo.item_title or item.item_title)
            convo.lesson_plan = lesson_plan
            db.commit()
        elif not lesson_plan.get("objectives"):
            lesson_plan["objectives"] = [f"掌握{convo.item_title or item.item_title}的核心概念"]
            convo.lesson_plan = lesson_plan
            db.commit()

        return {
            "conversation_id": convo.id,
            "item_id": item.item_id,
            "item_title": item.item_title,
            "lesson_content": convo.lesson_content,
            "lesson_plan": lesson_plan,
            "history": convo.messages,
            "attempt": convo.attempt_count,
            "resumed": True,
        }

    # 生成结构化教案
    from core.nodes import start_lesson as start_lesson_node
    plan_result = start_lesson_node({
        "subject": session.subject,
        "current_item_title": item.item_title,
        "attempt": attempt,
    })
    lesson_content = plan_result.get("lesson_content", "")
    lesson_plan = plan_result.get("lesson_plan", {})
    print(f"[DEBUG] lesson_plan cards: {len(lesson_plan.get('cards', []))}", flush=True)

    if convo is None:
        convo = crud.get_or_create_conversation(
            db, session_id, item.item_id, item.item_title, lesson_content)
        convo.lesson_plan = lesson_plan
        db.commit()
    else:
        convo.lesson_content = lesson_content
        convo.lesson_plan = lesson_plan
        convo.messages = []
        db.commit()

    # 标记知识点为"学习中"，更新状态机状态
    crud.update_item_status(db, session_id, req.item_db_id, "learning")
    session.state_status = SessionStatus.LEARNING
    db.commit()

    crud.update_item_status(db, session_id, req.item_db_id, "learning")
    session.state_status = SessionStatus.LEARNING
    db.commit()

    return {
        "conversation_id": convo.id,
        "item_id": item.item_id,
        "item_title": item.item_title,
        "lesson_content": lesson_content,
        "lesson_plan": lesson_plan,
        "history": [],
        "attempt": attempt,
        "resumed": False,
        "state_status": SessionStatus.LEARNING,
    }


class AskQuestionRequest(BaseModel):
    conversation_id: int
    question: str


@app.post("/classroom/ask/{session_id}")
def classroom_ask(session_id: int, req: AskQuestionRequest, db: Session = Depends(get_db)):
    convo = db.query(crud.ClassroomConversation).filter(
        crud.ClassroomConversation.id == req.conversation_id,
        crud.ClassroomConversation.session_id == session_id
    ).first()
    if not convo:
        raise HTTPException(404, "课堂对话不存在")
    session = crud.get_session(db, session_id)

    # 使用 LearningEngine 回答问题
    engine = LearningEngine(session_id, f"student_{session.student_id}")
    answer = engine.ask_question(
        session.subject, convo.item_title,
        convo.lesson_content,
        convo.messages or [],
        req.question
    )
    crud.append_message(db, convo.id, "user", req.question)
    crud.append_message(db, convo.id, "assistant", answer)
    return {"answer": answer, "conversation_id": convo.id}


class StartQuizRequest(BaseModel):
    conversation_id: int
    item_db_id: int


@app.post("/classroom/start-quiz/{session_id}")
def classroom_start_quiz(session_id: int, req: StartQuizRequest, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    item = db.query(crud.SyllabusItem).filter(
        crud.SyllabusItem.id == req.item_db_id,
        crud.SyllabusItem.session_id == session_id
    ).first()
    if not item:
        raise HTTPException(404, "知识点不存在")

    attempt_number = crud.get_item_quiz_count(db, session_id, item.item_id) + 1

    # 使用 LearningEngine 生成测验
    engine = LearningEngine(session_id, f"student_{session.student_id}")
    questions = engine.start_quiz(session.subject, item.item_title)
    if not questions:
        raise HTTPException(500, "生成题目失败，请重试")

    # 更新状态
    session.state_status = SessionStatus.QUIZ_ACTIVE
    db.commit()

    record = crud.create_quiz(db, session_id, item.item_id, item.item_title,
                              questions, attempt_number)
    return {
        "quiz_id": record.id,
        "item_id": item.item_id,
        "item_title": item.item_title,
        "questions": questions,
        "attempt_number": attempt_number,
        "state_status": SessionStatus.QUIZ_ACTIVE,
    }

@app.post("/classroom/start-quiz_stream/{session_id}")
def classroom_start_quiz_stream(session_id: int, req: StartQuizRequest, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    item = db.query(crud.SyllabusItem).filter(
        crud.SyllabusItem.id == req.item_db_id,
        crud.SyllabusItem.session_id == session_id
    ).first()
    if not item:
        raise HTTPException(404, "知识点不存在")

    attempt_number = crud.get_item_quiz_count(db, session_id, item.item_id) + 1

    # 提前记录需要的数据，避免在生成器内依赖外部 Session
    subject = session.subject
    item_id = item.item_id
    item_title = item.item_title

    def event_stream():
        from db.database import SessionLocal
        stream_db = SessionLocal()
        try:
            for event in generate_mini_quiz_stream(subject, item_title, count=4):
                if event["status"] == "done":
                    questions = event.get("questions", [])
                    if questions:
                        record = crud.create_quiz(stream_db, session_id, item_id, item_title,
                                                  questions, attempt_number)
                        event["quiz_id"] = record.id
                        event["item_id"] = item_id
                        event["item_title"] = item_title
                        event["attempt_number"] = attempt_number
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            import json
            traceback.print_exc()
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            stream_db.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/classroom/submit-quiz/{session_id}")
async def classroom_submit_quiz(
    session_id: int,
    quiz_id: int = Form(...),
    item_db_id: int = Form(...),
    answers: str = Form(...),       # JSON 字符串
    images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db)
):
    """提交小测验答案（支持文字+图片）"""
    import json as _json
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    quiz = db.query(crud.QuizRecord).filter(crud.QuizRecord.id == quiz_id).first()
    if not quiz:
        raise HTTPException(404, "测验记录不存在")

    answers_list = _json.loads(answers)

    # 处理图片
    images_b64 = []
    for img in images:
        content = await img.read()
        images_b64.append(base64.b64encode(content).decode())

    # 使用 LearningEngine 批改
    engine = LearningEngine(session_id, f"student_{session.student_id}")
    result = engine.submit_quiz(session.subject, quiz.item_title, quiz.questions, answers_list)
    score = result.get("quiz_result", {}).get("score", 0)
    passed = result.get("quiz_result", {}).get("passed", False)
    feedback = result.get("quiz_result", {}).get("feedback", "")

    crud.complete_quiz(db, quiz_id, answers_list, score, passed, feedback)

    if passed:
        crud.update_item_status(db, session_id, item_db_id, "done", score)
        session.state_status = SessionStatus.QUIZ_REVIEW
    else:
        session.state_status = SessionStatus.QUIZ_REVIEW
    db.commit()

    return {
        "quiz_id": quiz_id,
        "score": score,
        "passed": passed,
        "feedback": feedback,
        "progress_pct": crud.get_exam_unlock_status(db, session_id)["progress"],
        "state_status": session.state_status,
    }


@app.get("/session/{session_id}/quizzes")
def get_session_quizzes(session_id: int, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    
    quizzes = db.query(crud.QuizRecord).filter(
        crud.QuizRecord.session_id == session_id,
        crud.QuizRecord.passed.isnot(None) # completed quizzes
    ).order_by(crud.QuizRecord.created_at.desc()).all()
    
    quiz_list = [
        {
            "id": q.id,
            "type": "quiz",
            "item_id": q.item_id,
            "item_title": q.item_title,
            "questions": q.questions,
            "answers": q.answers,
            "score": q.score,
            "passed": q.passed,
            "ai_feedback": q.ai_feedback,
            "attempt_number": q.attempt_number,
            "created_at": q.created_at.isoformat() if q.created_at else None
        } for q in quizzes
    ]

    # 获取当前学生的所有入学测评记录（全局可见）
    current_session = db.query(crud.LearningSession).filter(crud.LearningSession.id == session_id).first()
    if current_session:
        # 查找该学生的所有已完成测评
        all_assessments = db.query(crud.AssessmentRecord).join(crud.LearningSession).filter(
            crud.LearningSession.student_id == current_session.student_id,
            crud.AssessmentRecord.completed == True
        ).all()

        for assess in all_assessments:
            # 避免重复（如果将来逻辑变了）
            if any(q["id"] == assess.id and q["type"] == "assessment" for q in quiz_list):
                continue
                
            quiz_list.append({
                "id": assess.id,
                "type": "assessment",
                "item_title": f"入学诊断测试 ({assess.session.subject})",
                "questions": assess.questions,
                "answers": assess.answers,
                "score": (assess.proficiency_result or {}).get("__overall__", 0),
                "passed": True,
                "ai_feedback": assess.ai_report,
                "question_results": assess.question_results,
                "attempt_number": 1,
                "created_at": assess.created_at.isoformat() if assess.created_at else None
            })

    # 重新按时间排序，确保入学测试在正确位置或按需排序
    # 这里我们保持倒序，入学测试通常是最后（最早）的一个
    
    return {
        "session_id": session_id,
        "quizzes": quiz_list
    }


# ════════════════════════════════════════════════════════
# 期中/期末考试
# ════════════════════════════════════════════════════════

@app.get("/exam/unlock-check/{session_id}")
def exam_unlock_check(session_id: int, db: Session = Depends(get_db)):
    return crud.get_exam_unlock_status(db, session_id)


class GenerateExamRequest(BaseModel):
    exam_type: str      # "midterm" / "final"


@app.post("/exam/generate/{session_id}")
def exam_generate(session_id: int, req: GenerateExamRequest, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    unlock = crud.get_exam_unlock_status(db, session_id)
    if req.exam_type == "midterm" and not unlock["midterm"]:
        raise HTTPException(403, f"期中考试未解锁（当前进度 {unlock['progress']}%，需 ≥50%）")
    if req.exam_type == "final" and not unlock["final"]:
        raise HTTPException(403, f"期末考试未解锁（当前进度 {unlock['progress']}%，需 ≥90%）")

    items = crud.get_syllabus_items(db, session_id)
    if req.exam_type == "midterm":
        covered = [i.item_title for i in items if i.status == "done"]
    else:
        covered = [i.item_title for i in items]

    questions = generate_exam(session.subject, covered, req.exam_type)
    if not questions:
        raise HTTPException(500, "试卷生成失败，请重试")

    record = crud.create_exam(db, session_id, req.exam_type, covered, questions)
    return {
        "exam_id": record.id,
        "exam_type": req.exam_type,
        "subject": session.subject,
        "covered_count": len(covered),
        "questions": questions,
        "total": len(questions),
    }

@app.post("/exam/generate_stream/{session_id}")
def exam_generate_stream(session_id: int, req: GenerateExamRequest, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    unlock = crud.get_exam_unlock_status(db, session_id)
    if req.exam_type == "midterm" and not unlock["midterm"]:
        raise HTTPException(403, f"期中考试未解锁（当前进度 {unlock['progress']}%，需 ≥50%）")
    if req.exam_type == "final" and not unlock["final"]:
        raise HTTPException(403, f"期末考试未解锁（当前进度 {unlock['progress']}%，需 ≥90%）")

    items = crud.get_syllabus_items(db, session_id)
    if req.exam_type == "midterm":
        covered = [i.item_title for i in items if i.status == "done"]
    else:
        covered = [i.item_title for i in items]

    def event_stream():
        try:
            for event in generate_exam_stream(session.subject, covered, req.exam_type):
                if event["status"] == "done":
                    questions = event.get("questions", [])
                    if questions:
                        record = crud.create_exam(db, session_id, req.exam_type, covered, questions)
                        event["exam_id"] = record.id
                        event["exam_type"] = req.exam_type
                        event["subject"] = session.subject
                        event["covered_count"] = len(covered)
                        event["total"] = len(questions)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as e:
            traceback.print_exc()
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/exam/submit/{session_id}")
async def exam_submit(
    session_id: int,
    exam_id: int = Form(...),
    answers: str = Form(...),
    images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db)
):
    import json as _json
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    exam = db.query(crud.ExamRecord).filter(crud.ExamRecord.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "考试记录不存在")

    answers_list = _json.loads(answers)
    score, report = evaluate_exam(session.subject, exam.exam_type, exam.questions, answers_list)
    crud.complete_exam(db, exam_id, answers_list, score, report)
    return {"exam_id": exam_id, "score": score, "report": report}


# ════════════════════════════════════════════════════════
# 兼容旧接口（快速学习/练习题 直连 LLM）
# ════════════════════════════════════════════════════════

class QuickTeachRequest(BaseModel):
    topic: str
    question: Optional[str] = None


@app.post("/learning/quick-teach")
def quick_teach(req: QuickTeachRequest):
    try:
        content = direct_teach(req.topic, req.question)
        return {"topic": req.topic, "content": content, "type": "quick_teach"}
    except Exception as e:
        raise HTTPException(500, str(e))


class PracticeRequest(BaseModel):
    topic: str
    difficulty: str = "medium"
    count: int = 5


@app.post("/learning/practice")
def practice(req: PracticeRequest):
    try:
        result = direct_practice(req.topic, req.difficulty, req.count)
        return {"topic": req.topic, "content": result, "type": "practice"}
    except Exception as e:
        raise HTTPException(500, str(e))


class SyllabusRequest(BaseModel):
    topic: str


class ConfigSaveRequest(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class AnswersSaveRequest(BaseModel):
    quiz_id: int
    answers: List[str]


class ConfigTestRequest(BaseModel):
    llm_base_url: str
    llm_api_key: str
    llm_model_name: str


@app.get("/config")
def get_configs(db: Session = Depends(get_db)):
    """获取所有配置"""
    configs = crud.get_all_configs(db)
    return {"configs": configs}


@app.post("/config/save")
def save_config(req: ConfigSaveRequest, db: Session = Depends(get_db)):
    """保存或更新配置"""
    crud.set_config(db, req.key, req.value, req.description)
    return {"status": "ok"}


@app.post("/config/test")
def test_llm_config(req: ConfigTestRequest):
    """测试 LLM 配置是否可用 (真实调用)"""
    from openai import OpenAI
    try:
        # 使用传入的参数进行实时测试，验证无误后再保存
        client = OpenAI(
            api_key=req.llm_api_key,
            base_url=req.llm_base_url
        )
        response = client.chat.completions.create(
            model=req.llm_model_name,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5
        )
        content = response.choices[0].message.content
        return {"status": "ok", "message": f"连接成功！模型响应: {content}"}
    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower():
            error_msg = "API Key 错误或无效"
        elif "base_url" in error_msg.lower():
            error_msg = "Base URL 格式错误或无法访问"
        raise HTTPException(status_code=400, detail=f"连接失败: {error_msg}")


@app.post("/classroom/save_quiz_answers/{session_id}")
def save_quiz_answers(session_id: int, req: AnswersSaveRequest, db: Session = Depends(get_db)):
    """暂存小测验答案"""
    crud.save_quiz_answers(db, req.quiz_id, req.answers)
    return {"status": "ok"}


@app.post("/learning/syllabus")
def syllabus_standalone(req: SyllabusRequest):
    try:
        data = generate_syllabus(req.topic)
        return {"topic": req.topic, "syllabus": data}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/analytics/dashboard/{session_id}")
def get_dashboard_analytics(session_id: int, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    
    # 1. 趋势数据 (Trend): 获取所有已通过的测验分数
    quizzes = db.query(crud.QuizRecord).filter(
        crud.QuizRecord.session_id == session_id,
        crud.QuizRecord.passed == True
    ).order_by(crud.QuizRecord.created_at.asc()).all()
    
    trend = [
        {"date": q.created_at.isoformat() if q.created_at else None, "score": q.score, "item": q.item_title}
        for q in quizzes
    ]
    
    # 2. 掌握度分布 (Mastery Distribution): 从 session.proficiency_data 提取
    mastery_dist = session.proficiency_data or {}
    
    # 3. 考分预测 (Projection)
    avg_score = sum([q.score for q in quizzes]) / len(quizzes) if quizzes else 60
    # 加权计算：平均分 * 0.7 + 过程活跃度等
    projected_score = min(100, avg_score * 0.8 + (session.progress_pct or 0) * 0.3)
    
    return {
        "session_id": session_id,
        "subject": session.subject,
        "progress": session.progress_pct,
        "trend": trend,
        "mastery_distribution": mastery_dist,
        "projected_score": round(projected_score, 1)
    }


# ════════════════════════════════════════════════════════
# 静态文件挂载 (仅用于 Standalone 单镜像部署模式)
# ════════════════════════════════════════════════════════

static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/", StaticFiles(directory=static_path, html=True), name="static")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
