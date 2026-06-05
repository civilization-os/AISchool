"""
LangGraph 节点函数 — 每个节点只做一件事
严格遵循状态机：节点执行的前提是 status 正确
"""

import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_chat_model
from core.state import SessionStatus


def _parse_json(raw: str, fallback=None):
    """安全解析 LLM 返回的 JSON"""
    if not raw:
        return fallback
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].strip().startswith("```"):
            text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return fallback


def _build_lesson_plan(raw: str, subject: str, item_title: str) -> dict:
    """Build a lesson deck and fall back to a minimal card when the LLM JSON is malformed."""
    from core.lesson import LessonDeck

    data = _parse_json(raw, {}) or {}

    try:
        deck = LessonDeck.from_llm_json(data, subject=subject, topic=item_title)
        lesson_dict = deck.to_dict()
    except Exception:
        lesson_dict = {}

    if lesson_dict.get("cards"):
        if not lesson_dict.get("objectives"):
            lesson_dict["objectives"] = [f"掌握{item_title}的核心概念"]
        return lesson_dict

    return {
        "topic": item_title,
        "subject": subject,
        "objectives": [f"掌握{item_title}的核心概念"],
        "cards": [
            {
                "type": "definition",
                "title": "核心内容",
                "content": raw or f"本节课围绕「{item_title}」展开。",
                "icon": "📉",
                "label": "定义",
            }
        ],
    }


# ═══════════════════════════════════════════════════════════
# 入学测评
# ═══════════════════════════════════════════════════════════

def start_assessment(state: dict) -> dict:
    """生成入学测评题目，状态 → ASSESSING"""
    subject = state.get("subject", "")
    llm = get_chat_model(temperature=1.0)

    system = (
        "你是一位中国高级教研员。严格返回 JSON 数组。"
        "严禁出现'如图所示'等图片引用。"
    )
    user = f"""为「{subject}」生成 10 道入学摸底诊断题。
要求：8道单选题，2道简答题，覆盖基础/中档/压轴。
JSON格式：
[{{"id":1,"type":"choice","domain":"考点","question":"...","options":["A.","B.","C.","D."],"answer":"A","explanation":"...","difficulty":"easy"}}]"""

    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    questions = _parse_json(resp.content, [])

    return {
        "assessment_questions": questions,
        "status": SessionStatus.ASSESSING,
    }


def submit_assessment(state: dict) -> dict:
    """批改入学测评 → ASSESSED"""
    subject = state.get("subject", "")
    questions = state.get("assessment_questions", [])
    answers = state.get("assessment_answers", [])

    qa_text = ""
    for q, a in zip(questions, answers):
        qa_text += f"\n题{q['id']}（{q.get('domain','')}）: {q['question']}\n学生答案: {a}\n参考: {q.get('answer','')}\n"

    llm = get_chat_model(temperature=0.0)
    system = "你是资深教育诊断专家。返回 JSON。"
    user = f"""批改诊断：{qa_text}
JSON：{{"proficiency":{{"考点":0-100}},"overall_score":0-100,"report":"Markdown报告","question_results":[{{"id":1,"is_correct":true,"score":100,"feedback":"..."}}]}}"""

    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    result = _parse_json(resp.content, {"proficiency": {}, "overall_score": 0, "report": "", "question_results": []})

    return {
        "assessment_result": result,
        "status": SessionStatus.ASSESSED,
    }


# ═══════════════════════════════════════════════════════════
# 大纲
# ═══════════════════════════════════════════════════════════

def generate_syllabus(state: dict) -> dict:
    """生成学习大纲 → SYLLABUS_READY
    支持等级: levels=[1,2,3] 表示生成多学期内容"""
    from core.knowledge import KnowledgeGraph

    subject = state.get("subject", "")
    levels = state.get("levels", [1])

    level_prompt = ""
    if len(levels) > 1:
        parts = []
        for lv in levels:
            descs = {1: "基础入门", 2: "进阶提高", 3: "高级深化", 4: "专题拓展"}
            parts.append(f"第{lv}学期（{descs.get(lv, '进阶')}）")
        level_prompt = "按多学期分层生成，每学期独立成章：\n" + "\n".join(parts) + "\n"
        level_prompt += "每个考点标注所属学期：在 items 中添加 \"level\": 1/2/3/4 字段。"

    llm = get_chat_model(temperature=0.7)
    system = "你是中国金牌课程设计专家。返回 JSON。"
    user = f"""为「{subject}」生成系统化教学大纲。
{level_prompt}
每个学期4-6个模块，每模块3-5个考点。
标注前置依赖（prerequisites字段，空数组表示无前置）。
JSON:
{{"topic":"{subject}","description":"...","sections":[{{"id":"1","title":"模块名","description":"...","items":[{{"id":"1.1","title":"考点名称","description":"说明","level":1,"prerequisites":[],"difficulty":2,"estimated_minutes":15}}]}}]}}"""

    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    syllabus = _parse_json(resp.content, {"topic": subject, "description": "", "sections": []})

    # 使用 KnowledgeGraph 构建
    kg = KnowledgeGraph.from_syllabus_dict(syllabus)
    items = kg.to_syllabus_items()

    # 给 items 补上 level（从原始 section 数据获取）
    level_map = {}
    for sec in syllabus.get("sections", []):
        for item in sec.get("items", []):
            level_map[item.get("id", "")] = item.get("level", 1)
    for item in items:
        item["level"] = level_map.get(item["item_id"], 1)

    # ── 自校验 ──────────────────────────────────────
    syllabus, items = _review_syllabus(subject, syllabus, items)

    first_id = items[0]["item_id"] if items else ""

    return {
        "syllabus": syllabus,
        "syllabus_items": items,
        "status": SessionStatus.SYLLABUS_READY,
        "current_item_id": first_id,
    }


def _review_syllabus(subject: str, syllabus: dict, items: list) -> tuple:
    """大纲自校验：检查质量问题，自动修正"""
    sections = syllabus.get("sections", [])
    issues = []

    # 1. 空章节检查
    for sec in sections:
        if not sec.get("items"):
            issues.append(f"章节「{sec.get('title','')}」为空")

    # 2. 重复标题检查
    titles = [item.get("item_title", "") for item in items]
    if len(titles) != len(set(titles)):
        dupes = [t for t in titles if titles.count(t) > 1]
        issues.append(f"存在重复知识点标题: {list(set(dupes))}")

    # 3. 前置依赖检查
    all_ids = {item["item_id"] for item in items if "item_id" in item}
    for item in items:
        for prereq in item.get("prerequisites", []):
            if prereq and prereq not in all_ids:
                issues.append(f"「{item.get('item_title','')}」前置依赖 {prereq} 不存在")

    # 4. level 合法性检查
    if items:
        levels_found = {item.get("level", 0) for item in items}
        if len(levels_found) < 1:
            issues.append("缺少 level 标签")

    # 5. 总分章数过少检查
    if len(items) < 6:
        issues.append(f"知识点过少（仅{len(items)}个），应至少6个")

    # 如果有问题，用 LLM 修正
    if issues:
        print(f"[Review] 大纲发现 {len(issues)} 个问题，正在修正...")
        for issue in issues:
            print(f"  - {issue}")

        llm = get_chat_model(temperature=0.5)
        system = "你是一位课程质量审查专家。修正以下大纲问题，返回完整的修正后 JSON。"
        user = f"""原始课程：「{subject}」
原始大纲 JSON：
{json.dumps(syllabus, ensure_ascii=False, indent=2)}

发现以下问题：
{chr(10).join(f'- {i}' for i in issues)}

请修正这些问题，返回完整的修正后 JSON（保持相同结构）。
如果某个章节无内容，补充合理知识点。
如果有重复标题，重命名。
如果前置依赖不存在，移除或修正该依赖。
如果知识点过少，补充到至少 6 个。"""

        try:
            resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
            fixed = _parse_json(resp.content, None)
            if fixed and fixed.get("sections"):
                syllabus = fixed
                # 重新扁平化 items
                from core.knowledge import KnowledgeGraph
                kg = KnowledgeGraph.from_syllabus_dict(syllabus)
                items = kg.to_syllabus_items()
                # 重新补 level
                level_map = {}
                for sec in syllabus.get("sections", []):
                    for item in sec.get("items", []):
                        level_map[item.get("id", "")] = item.get("level", 1)
                for item in items:
                    item["level"] = level_map.get(item["item_id"], 1)
        except Exception as e:
            print(f"[Review] 修正失败: {e}，使用原始大纲")

    return syllabus, items


# ═══════════════════════════════════════════════════════════
# 课堂教学
# ═══════════════════════════════════════════════════════════

def start_lesson(state: dict) -> dict:
    """开始上课 → LEARNING
    生成多维知识卡片（LessonDeck），每张 card 是一个独立维度"""

    subject = state.get("subject", "")
    item_title = state.get("current_item_title", "")
    attempt = state.get("attempt", 1)

    prompt_extra = f"\n（第{attempt}次讲解，换种方式）" if attempt > 1 else ""

    llm = get_chat_model(temperature=1.3)
    system = (
        "你是一位中国金牌辅导老师。"
        "数学公式使用 LaTeX：行内$公式$，独立$$公式$$。"
        "返回 JSON，不要有多余文字。"
    )
    user = f"""为「{subject}」中的知识点「{item_title}」生成一组知识卡片{prompt_extra}。

卡片按推荐顺序排列，形成完整的学习叙事。每张卡片标注 `core: true`（必看）或 `core: false`（拓展）。
必看卡片（2-3张）覆盖核心概念，拓展卡片（2-3张）提供深度补充。

必看卡片应包含：
- definition: 严格定义，必须是知识点的数学/学科定义
- example: 代表性例题，含逐步解答
- 一张你选择的必看维度（根据学科特点）

拓展卡片从以下选择（根据知识点关联性）：
- geometric, physical, formula, lab, application, analogy, history, pitfall

每张卡片还要带：
- next_hint: 一句话预告下一张卡片的内容（最后一张写空字符串）
- checkpoint: 一个小检测题（可选，只在必看卡片上出现）

JSON 格式：
{{
  "topic": "{item_title}",
  "objectives": ["理解...", "掌握..."],
  "cards": [
    {{
      "type": "definition",
      "core": true,
      "title": "定义",
      "content": "严格定义与说明...",
      "next_hint": "接下来用图像直观理解这个概念",
      "checkpoint": {{"question": "快速检测题", "options": ["A","B","C","D"], "correct_index": 0, "explanation": "解析"}}
    }},
    {{
      "type": "example",
      "core": true,
      "title": "典型例题",
      "content": "例题与解答...",
      "next_hint": "然后看看在实际场景中的应用",
      "checkpoint": null
    }},
    {{
      "type": "geometric",
      "core": false,
      "title": "几何意义",
      "content": "几何直观解释...",
      "next_hint": ""
    }}
  ]
}}"""

    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])

    try:
        lesson_dict = _build_lesson_plan(resp.content, subject, item_title)
    except Exception as e:
        print(f"[start_lesson] 卡片生成失败: {e}，降级")
        lesson_dict = {
            "topic": item_title,
            "subject": subject,
            "objectives": [f"掌握{item_title}的核心概念"],
            "cards": [{"type": "definition", "title": "核心内容", "content": resp.content, "icon": "📖", "label": "定义"}],
        }

    return {
        "lesson_content": resp.content,
        "lesson_plan": lesson_dict,
        "status": SessionStatus.LEARNING,
    }


def ask_question(state: dict) -> dict:
    """学生追问（状态不变，仍 LEARNING）"""
    subject = state.get("subject", "")
    item_title = state.get("current_item_title", "")
    lesson_content = state.get("lesson_content", "")
    chat_history = state.get("chat_history", [])
    student_question = state.get("student_question", "")

    llm = get_chat_model(temperature=1.3)
    system = (
        f"你是「{subject}」金牌教师，正在讲解「{item_title}」。"
        "回答亲切自然，LaTeX格式数学公式。"
    )

    messages = [SystemMessage(content=system)]
    messages.append(HumanMessage(content=f"已讲内容：\n{lesson_content}"))
    for msg in chat_history[-6:]:
        messages.append(
            HumanMessage(content=msg["content"]) if msg["role"] == "user"
            else SystemMessage(content=msg["content"])
        )
    messages.append(HumanMessage(content=student_question))

    resp = llm.invoke(messages)

    return {"answer": resp.content}


# ═══════════════════════════════════════════════════════════
# 随堂测验
# ═══════════════════════════════════════════════════════════

def start_quiz(state: dict) -> dict:
    """生成测验题目 → QUIZ_ACTIVE"""
    subject = state.get("subject", "")
    item_title = state.get("current_item_title", "")

    llm = get_chat_model(temperature=1.0)
    system = "你是一位中国名校出卷专家。返回 JSON 数组。禁止图片引用。"
    user = f"""为「{subject} - {item_title}」出 4 道随堂测验题。
混合选择题和简答题。
JSON：[{{"id":1,"type":"choice","question":"...","options":["A.","B.","C.","D."],"answer":"B","explanation":"..."}}]"""

    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    questions = _parse_json(resp.content, [])

    return {
        "quiz_questions": questions,
        "quiz_answers": [""] * len(questions),
        "status": SessionStatus.QUIZ_ACTIVE,
    }


def submit_quiz(state: dict) -> dict:
    """批改测验 → QUIZ_REVIEW"""
    subject = state.get("subject", "")
    item_title = state.get("current_item_title", "")
    questions = state.get("quiz_questions", [])
    answers = state.get("quiz_answers", [])

    qa_text = ""
    for q, a in zip(questions, answers):
        qa_text += f"\n题{q['id']}：{q['question']}\n学生：{a}\n参考：{q.get('answer','')}\n"

    llm = get_chat_model(temperature=0.0)
    system = "你是严格公正的中国阅卷老师。返回 JSON。"
    user = f"""批改「{subject} - {item_title}」测验：
{qa_text}
JSON：{{"score":85,"passed":true,"feedback":"...","weak_points":["..."]}}"""

    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    result = _parse_json(resp.content, {"score": 0, "passed": False, "feedback": "", "weak_points": []})
    result["score"] = float(result.get("score", 0))
    result["passed"] = bool(result.get("passed", result["score"] >= 70))

    return {
        "quiz_result": result,
        "status": SessionStatus.QUIZ_REVIEW,
    }


# ═══════════════════════════════════════════════════════════
# 学习进度
# ═══════════════════════════════════════════════════════════

def _find_item(items: list, item_id: str) -> tuple:
    """根据 item_id 查找知识点，返回 (index, item_dict) 或 (-1, None)"""
    for i, item in enumerate(items):
        if item.get("item_id") == item_id:
            return i, item
    return -1, None


def _find_next_item_id(items: list, current_id: str) -> str:
    """查找当前知识点之后第一个未完成的知识点"""
    _, current = _find_item(items, current_id)
    if current is None:
        # 当前找不到，返回第一个未完成的
        for item in items:
            if item.get("status") != "done":
                return item.get("item_id", "")
        return ""

    current_sort = current.get("sort_order", 0)
    # 找 sort_order 大于当前且未完成的
    candidates = [
        item for item in items
        if item.get("sort_order", 0) > current_sort
        and item.get("status") != "done"
    ]
    candidates.sort(key=lambda x: x.get("sort_order", 0))
    return candidates[0].get("item_id", "") if candidates else ""


def mark_item_done(state: dict) -> dict:
    """标记知识点完成 → ITEM_DONE，更新进度（加权）"""
    from core.knowledge import KnowledgePoint, MasteryModel, MasteryRecord

    items = list(state.get("syllabus_items", []))
    current_id = state.get("current_item_id", "")
    completed_ids = list(state.get("completed_item_ids", []))
    quiz_score = state.get("quiz_result", {}).get("score", 0)

    # 更新当前 item 状态（用 MasteryModel 计算掌握度）
    for item in items:
        if item.get("item_id") == current_id:
            attempt = state.get("attempt", 1)
            # 计算前置知识掌握度
            prereq_ids = item.get("prerequisites", [])
            prereq_scores = []
            for pid in prereq_ids:
                for done_item in items:
                    if done_item.get("item_id") == pid:
                        prereq_scores.append(done_item.get("mastery_score", 0))
            prereq_mastery = sum(prereq_scores) / len(prereq_scores) if prereq_scores else 100.0

            mastery = MasteryModel.calculate(
                quiz_score=quiz_score,
                attempt_count=attempt,
                prereq_mastery=prereq_mastery,
            )
            item["status"] = "done"
            item["mastery_score"] = mastery

    if current_id and current_id not in completed_ids:
        completed_ids.append(current_id)

    # 加权进度：按难度加权
    total_weight = 0.0
    completed_weight = 0.0
    for item in items:
        diff = item.get("difficulty", 1)
        weight = float(diff)  # 难度越高权重越大
        total_weight += weight
        if item.get("item_id") in completed_ids:
            # 已完成的按掌握度再加权
            score = item.get("mastery_score", 0)
            completed_weight += weight * (score / 100.0)

    progress = round(completed_weight / total_weight * 100, 1) if total_weight > 0 else 0.0

    return {
        "syllabus_items": items,
        "completed_item_ids": completed_ids,
        "progress_pct": progress,
        "status": SessionStatus.ITEM_DONE,
    }


def next_item(state: dict) -> dict:
    """移动到下一个知识点 → LEARNING 或保持 ITEM_DONE"""
    items = state.get("syllabus_items", [])
    current_id = state.get("current_item_id", "")

    next_id = _find_next_item_id(items, current_id)
    if not next_id:
        return {"status": SessionStatus.ITEM_DONE}

    _, next_item = _find_item(items, next_id)
    return {
        "current_item_id": next_id,
        "current_item_title": next_item.get("item_title", "") if next_item else "",
        "attempt": 1,
        "lesson_content": "",
        "chat_history": [],
        "quiz_questions": [],
        "quiz_answers": [],
        "quiz_result": {},
        "status": SessionStatus.LEARNING,
    }


def retry_item(state: dict) -> dict:
    """重学当前知识点 → LEARNING"""
    return {
        "attempt": state.get("attempt", 1) + 1,
        "lesson_content": "",
        "chat_history": [],
        "quiz_questions": [],
        "quiz_answers": [],
        "quiz_result": {},
        "status": SessionStatus.LEARNING,
    }


# ═══════════════════════════════════════════════════════════
# 考试
# ═══════════════════════════════════════════════════════════

def start_exam(state: dict) -> dict:
    """生成试卷 → EXAM_ACTIVE"""
    subject = state.get("subject", "")
    exam_type = state.get("exam_type", "midterm")
    items = state.get("syllabus_items", [])
    count = 15 if exam_type == "midterm" else 20

    covered = [i.get("item_title", "") for i in items if i.get("status") == "done"]
    if exam_type == "final":
        covered = [i.get("item_title", "") for i in items]

    scope = "已学章节" if exam_type == "midterm" else "全部章节"
    items_text = "、".join(covered[:20])

    llm = get_chat_model(temperature=1.0)
    system = "你是资深中国命题组长。返回 JSON 数组。"
    user = f"""为「{subject}」出{count}道{"期中" if exam_type=="midterm" else "期末"}考试题。
范围：{scope}，考点：{items_text}
题型：{count//2}道选择，{count//4}道填空，{count//4}道综合大题。
JSON：[{{"id":1,"type":"choice","domain":"考点","question":"...","options":["A.","B.","C.","D."],"answer":"B","explanation":"...","score_weight":3,"difficulty":"easy"}}]"""

    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    questions = _parse_json(resp.content, [])

    return {
        "exam_questions": questions,
        "exam_answers": [""] * len(questions),
        "status": SessionStatus.EXAM_ACTIVE,
    }


def submit_exam(state: dict) -> dict:
    """批改考试 → COMPLETED"""
    subject = state.get("subject", "")
    exam_type = state.get("exam_type", "midterm")
    questions = state.get("exam_questions", [])
    answers = state.get("exam_answers", [])

    qa_text = ""
    for q, a in zip(questions, answers):
        qa_text += f"\n题{q['id']}（{q.get('domain','')}）[{q.get('score_weight',5)}分]：{q['question']}\n学生：{a}\n参考：{q.get('answer','')}\n"

    exam_name = "期中" if exam_type == "midterm" else "期末"
    llm = get_chat_model(temperature=0.0)
    system = "你是阅卷组长。返回 JSON。"
    user = f"""批改「{subject}」{exam_name}考试：
{qa_text}
JSON: {{"score":82,"grade":"B","report":"Markdown分析","strengths":[],"weaknesses":[],"suggestions":"..."}}"""

    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    result = _parse_json(resp.content, {"score": 0, "grade": "", "report": ""})
    result["score"] = float(result.get("score", 0))

    return {
        "exam_result": result,
        "status": SessionStatus.COMPLETED,
    }
