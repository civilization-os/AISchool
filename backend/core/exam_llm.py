"""
考试专用 LLM — 期中/期末考试出题和批改
"""

import json, os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


from core.config_utils import get_openai_client
from core.llm_utils import chat_completion, parse_json_response


def generate_exam(subject: str, covered_items: list, exam_type: str) -> list:
    """生成期中/期末试卷"""
    count = 15 if exam_type == "midterm" else 20
    scope = "已学习的章节" if exam_type == "midterm" else "全部章节"
    items_text = "、".join(covered_items[:20])

    system = "你是一位资深中国公立学校命题组长，请严格返回 JSON 数组，不要有多余文字。"
    user = f"""为「{subject}」出一份极具区分度的{"期中" if exam_type == "midterm" else "期末"}考试试卷。
考察范围：{scope}，具体考点：{items_text}

要求：
- 共 {count} 道题
- 题型：单选题（{count//2}道）、填空/简答题（{count//4}道）、压轴综合大题（{count//4}道）
- 难度分布符合国内考试核心标准：30%基础送分、50%中档拉开差距、20%压轴选拔
- 题目新颖贴近国情，考察深度理解和推导，杜绝死记硬背
- 压轴大题要求综合运用多个考点，设置层层递进的小问
- JSON 格式与小测验相同，增加 "score_weight": 分值（选择题分低，综合大题分高）

[
  {{
    "id": 1,
    "type": "choice",
    "domain": "具体考点",
    "question": "...",
    "options": ["A...", "B...", "C...", "D..."],
    "answer": "B",
    "explanation": "...",
    "score_weight": 3,
    "difficulty": "easy"
  }}
]"""

    raw = chat_completion(system, user, temperature=1.0, max_tokens=4000)
    return parse_json_response(raw, fallback=[])

def generate_exam_stream(subject: str, covered_items: list, exam_type: str):
    """流式生成期中/期末试卷，实时 yield 状态和数据"""
    count = 15 if exam_type == "midterm" else 20
    scope = "已学习的章节" if exam_type == "midterm" else "全部章节"
    items_text = "、".join(covered_items[:20])

    system = "你是一位资深中国公立学校命题组长，请严格返回 JSON 数组，不要有多余文字。"
    user = f"""为「{subject}」出一份极具区分度的{"期中" if exam_type == "midterm" else "期末"}考试试卷。
考察范围：{scope}，具体考点：{items_text}

要求：
- 共 {count} 道题
- 题型：单选题（{count//2}道）、填空/简答题（{count//4}道）、压轴综合大题（{count//4}道）
- 难度分布符合国内考试核心标准：30%基础送分、50%中档拉开差距、20%压轴选拔
- 题目新颖贴近国情，考察深度理解和推导，杜绝死记硬背
- 压轴大题要求综合运用多个考点，设置层层递进的小问
- JSON 格式与小测验相同，增加 "score_weight": 分值（选择题分低，综合大题分高）

[
  {{
    "id": 1,
    "type": "choice",
    "domain": "具体考点",
    "question": "...",
    "options": ["A...", "B...", "C...", "D..."],
    "answer": "B",
    "explanation": "...",
    "score_weight": 3,
    "difficulty": "easy"
  }}
]"""

    try:
        client, model = get_openai_client()
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user}],
            temperature=1.0, max_tokens=4000, stream=True
        )
        buffer = ""
        for chunk in r:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                buffer += delta
                yield {"status": "streaming", "chunk": delta}
                
        raw = buffer.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.split("\n")[:-1])
        questions = json.loads(raw.strip())
        yield {"status": "done", "questions": questions}
    except Exception as e:
        yield {"status": "error", "message": str(e)}


def evaluate_exam(subject: str, exam_type: str, questions: list, answers: list) -> tuple[float, str]:
    """批改考试，返回 (score 0-100, report)"""
    qa_text = ""
    for q, a in zip(questions, answers):
        qa_text += f"\n题{q['id']}（{q.get('domain','')}）[{q.get('score_weight',5)}分]：{q['question']}\n学生：{a}\n参考：{q.get('answer','')}\n"

    exam_name = "期中考试" if exam_type == "midterm" else "期末考试"
    raw = chat_completion(
        system_prompt="你是资深的中国考卷阅卷组长，按百分制严格评分，并给出学情分析。返回 JSON 不要有多余文字。",
        user_prompt=(
            f"批改「{subject}」{exam_name}：\n{qa_text}\n\n"
            "返回JSON格式：\n"
            "{\"score\": 82, \"grade\": \"B\", \"report\": \"...\", \"strengths\": [], \"weaknesses\": [], \"suggestions\": \"...\"}"
        ),
        temperature=0.0,
        max_tokens=2000
    )
    
    data = parse_json_response(raw, fallback={})
    score = float(data.get("score", 0))
    parts = [f"## 成绩：{score}分（{data.get('grade','')})\n\n{data.get('report','')}"]
    if data.get("strengths"):
        parts.append("\n\n**✅ 优势**\n" + "\n".join(f"- {s}" for s in data["strengths"]))
    if data.get("weaknesses"):
        parts.append("\n\n**❌ 薄弱点**\n" + "\n".join(f"- {w}" for w in data["weaknesses"]))
    if data.get("suggestions"):
        parts.append(f"\n\n**💡 建议**\n{data['suggestions']}")
    return score, "".join(parts)
