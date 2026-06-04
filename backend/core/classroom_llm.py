"""
课堂专用 LLM — 知识点讲解、对话、小测验
"""

import json, os, base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


from core.config_utils import get_openai_client
from core.llm_utils import chat_completion, parse_json_response


def _chat_messages(messages: list, temperature: float = 1.3) -> str:
    client, model = get_openai_client()
    r = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=3000,
    )
    return r.choices[0].message.content or ""


def start_lesson(subject: str, item_title: str, attempt: int = 1) -> str:
    """开始上课：提供知识点定义 + 例题"""
    prompt_extra = ""
    if attempt > 1:
        prompt_extra = f"\n（这是第{attempt}次讲解，请换一种方式、增加新的例子来解释）"

    messages = [
        {
            "role": "system",
            "content": (
                "你是一位耐心的中国金牌辅导老师，用「深入浅出」的方式教学。"
                "所有数学公式必须使用 LaTeX 格式：行内公式使用 $公式$，独占一行的公式使用 $$公式$$。"
                "请按以下结构讲解：\n"
                "## 🎙️ 课堂引入\n"
                "## 📖 核心知识讲解\n"
                "## 💡 典型例题剖析\n（给出2-3个从简单到复杂的例题，包含详细解答过程）\n"
                "## ⚠️ 易错点提示\n"
                "## 📝 板书总结\n"
                "## 💬 欢迎提问"
            )
        },
        {
            "role": "user",
            "content": f"请讲解「{subject}」课程中的知识点：「{item_title}」{prompt_extra}"
        }
    ]
    return _chat_messages(messages)


def ask_question(subject: str, item_title: str, lesson_content: str,
                 history: list, student_question: str) -> str:
    """学生自由提问，AI 即时解答"""
    messages = [
        {
            "role": "system",
            "content": (
                f"你是「{subject}」的中国金牌辅导教师，正在给学生讲解「{item_title}」。"
                "回答要富有启发性，比如用“这位同学问得好”、“我们来回顾一下”等话术引导。"
                "可以补充新例子，但不要照搬已讲过的长篇内容。语言要亲切自然。"
                "所有数学公式必须使用 LaTeX 格式：行内公式用 $公式$，独立公式用 $$公式$$，不要直接输出裸式LaTeX。"
            )
        },
        {
            "role": "assistant",
            "content": lesson_content
        }
    ]
    # 加入历史对话
    for msg in history[-6:]:  # 最多保留最近6条
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": student_question})
    return _chat_messages(messages)


def generate_mini_quiz(subject: str, item_title: str, count: int = 4) -> list:
    """生成小测验题目（联网+变形题，保证新颖性）"""
    system = (
        "你是一位中国名校出卷专家，请严格返回 JSON 数组，不要有多余文字。\n"
        "【重要约束】严禁在题目中出现“如图所示”、“见图”、“下方图表”等对外部图表的引用，因为目前系统无法显示图片。请确保所有题目都是文字自洽的。"
    )
    user = f"""请为「{subject} - {item_title}」出一份精简版的【当堂达标检测（随堂测验）】。共 {count} 道题目。
要求：
- 不要出教科书上的原题，出一些变式题或应用设误题
- 题型混合：单项选择题、填空题和简答题
- 贴近国内应试风格，考察理解与变通，有一定思考量
- JSON 格式：
[
  {{
    "id": 1,
    "type": "choice",
    "question": "题目（变式或应用设误）",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "answer": "B",
    "explanation": "详细解析路线"
  }},
  {{
    "id": 2,
    "type": "open",
    "question": "填空题或简答题目",
    "answer": "参考答案要点",
    "explanation": "踩分点及考点说明"
  }}
]"""
    raw = chat_completion(system, user, temperature=1.0, max_tokens=2000)
    return parse_json_response(raw, fallback=[])

def generate_mini_quiz_stream(subject: str, item_title: str, count: int = 4):
    """流式生成小测验题目，实时 yield 状态和数据"""
    system = (
        "你是一位中国名校出卷专家，请严格返回 JSON 数组，不要有多余文字。\n"
        "【重要约束】严禁在题目中出现“如图所示”、“见图”、“下方图表”等对外部图表的引用，因为目前系统无法显示图片。请确保所有题目都是文字自洽的。"
    )
    user = f"""请为「{subject} - {item_title}」出一份精简版的【当堂达标检测（随堂测验）】。共 {count} 道题目。
要求：
- 不要出教科书上的原题，出一些变式题或应用设误题
- 题型混合：单项选择题、填空题和简答题
- 贴近国内应试风格，考察理解与变通，有一定思考量
- JSON 格式：
[
  {{
    "id": 1,
    "type": "choice",
    "question": "题目（变式或应用设误）",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "answer": "B",
    "explanation": "详细解析路线"
  }},
  {{
    "id": 2,
    "type": "open",
    "question": "填空题或简答题目",
    "answer": "参考答案要点",
    "explanation": "踩分点及考点说明"
  }}
]"""
    try:
        client, model = get_openai_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user}],
            temperature=1.0, max_tokens=2000, stream=True
        )
        buffer = ""
        for chunk in response:
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


def evaluate_quiz(subject: str, item_title: str, questions: list,
                  answers: list, images: list = None) -> tuple[float, bool, str]:
    """批改小测验 (score 0-100, passed, feedback)"""
    qa_text = ""
    for q, a in zip(questions, answers):
        qa_text += f"\n题{q['id']}：{q['question']}\n学生答案：{a}\n参考答案：{q.get('answer','')}\n"

    # 如果有图片（base64），追加到内容
    content_parts = []
    if images:
        for img_b64 in images:
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            })
    content_parts.append({
        "type": "text",
        "text": f"请批改「{subject} - {item_title}」的小测验：\n{qa_text}\n\n请返回JSON：{{\"score\": 85, \"passed\": true, \"feedback\": \"具体的典型错误分析与复习建议...\", \"weak_points\": [\"...\"]}}",
    })

    raw = ""
    try:
        client, model = get_openai_client()
        r = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是严格公正的中国阅卷老师，注意按踩分点给分，请返回 JSON 不要有多余文字。"},
                {"role": "user", "content": content_parts if images else content_parts[0]["text"]}
            ],
            temperature=0.0, max_tokens=1500,
        )
        raw = r.choices[0].message.content or ""
    except Exception as e:
        print(f"Vision 批改失败，尝试回退: {e}")
        raw = chat_completion(
            system_prompt="你是严格公正的中国阅卷老师，注意按踩分点给分，请返回 JSON 不要有多余文字。",
            user_prompt=f"批改「{subject} - {item_title}」小测验：\n{qa_text}\n返回JSON：{{\"score\": 85, \"passed\": true, \"feedback\": \"...\"}}",
            temperature=0.0
        )

    data = parse_json_response(raw, fallback={})
    score = float(data.get("score", 0))
    passed = bool(data.get("passed", score >= 70))
    feedback = data.get("feedback", "批改出现问题，请重试")
    weak = data.get("weak_points", [])
    if weak:
        feedback += "\n\n**薄弱点：**\n" + "\n".join(f"- {w}" for w in weak)
    return score, passed, feedback
