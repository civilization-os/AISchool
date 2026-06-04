"""
测评专用 LLM — 入学诊断测试
"""

import json, os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

from core.config_utils import get_openai_client
from core.llm_utils import chat_completion, parse_json_response

def _chat(system: str, user: str, temperature: float = 1.0) -> str:
    client, model = get_openai_client()
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": user}],
        temperature=temperature, max_tokens=3000,
    )
    return r.choices[0].message.content or ""


def generate_assessment_questions(subject: str, count: int = 10, open_count: int = 2) -> list:
    """生成入学诊断题，覆盖该主题的各子领域"""
    system = (
        "你是一位专业的中国高级教研员和测评专家。请严格返回 JSON 数组，不要有多余文字。\n"
        "【重要约束】严禁在题目中出现“如图所示”、“见图”、“下方图表”等对外部图片的引用，因为目前系统无法显示图片。请确保所有题目都是文字自洽的。"
    )
    user = f"""为「{subject}」生成 {count} 道【入学摸底诊断题】，覆盖该主题的多个核心考点与子领域。
要求：
- 题型混合：其中必须包含 {open_count} 道简答题（type="open"），其余为单选题（type="choice"）。
- 简答题难度要求：简答题中至少包含 1 道 Medium 和 1 道 Hard 难度。
- 整体难度梯度：整体应包含基础、中档和压轴题。
- 每道题精准标注所属“核心考点/模块”
- JSON 格式：
[
  {{
    "id": 1,
    "type": "choice",
    "domain": "核心考点/模块",
    "question": "题目内容",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "answer": "A",
    "explanation": "详细解析思路",
    "difficulty": "easy"
  }},
  {{
    "id": 2,
    "type": "open",
    "domain": "核心考点/模块",
    "question": "题目内容",
    "answer": "参考答案",
    "explanation": "答题要点与评价标准",
    "difficulty": "medium"
  }}
]"""
    raw = chat_completion(system, user, temperature=1.0)
    return parse_json_response(raw, fallback=[])

def generate_assessment_questions_stream(subject: str, count: int = 10, open_count: int = 2):
    """流式生成入学诊断题，实时 yield 状态和数据"""
    system = (
        "你是一位专业的中国高级教研员和测评专家。请严格返回 JSON 数组，不要有多余文字。\n"
        "【重要约束】严禁在题目中出现“如图所示”、“见图”、“下方图表”等对外部图片的引用，因为目前系统无法显示图片。请确保所有题目都是文字自洽的。"
    )
    user = f"""为「{subject}」生成 {count} 道【入学摸底诊断题】，覆盖该主题的多个核心考点与子领域。
要求：
- 题型混合：其中必须包含 {open_count} 道简答题（type="open"），其余为单选题（type="choice"）。
- 简答题难度要求：简答题中至少包含 1 道 Medium 和 1 道 Hard 难度。
- 整体难度梯度：整体应包含基础、中档和压轴题。
- 每道题精准标注所属“核心考点/模块”
- JSON 格式：
[
  {{
    "id": 1,
    "type": "choice",
    "domain": "核心考点/模块",
    "question": "题目内容",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "answer": "A",
    "explanation": "详细解析思路",
    "difficulty": "easy"
  }},
  {{
    "id": 2,
    "type": "open",
    "domain": "核心考点/模块",
    "question": "题目内容",
    "answer": "参考答案",
    "explanation": "答题要点与评价标准",
    "difficulty": "medium"
  }}
]"""
    try:
        client, model = get_openai_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user}],
            temperature=1.0, max_tokens=3000, stream=True
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


def evaluate_assessment(subject: str, questions: list, answers: list) -> tuple[dict, str, float, list]:
    """批改测评，返回 (熟练度字典, 分析报告文字, 总体评分, 逐题评估结果)"""
    qa_text = ""
    for q, a in zip(questions, answers):
        qa_text += f"\n题{q['id']}（{q['domain']}）: {q['question']}\n学生答案: {a}\n参考答案: {q.get('answer','')}\n"

    system = "你是一位资深教育诊断专家。请根据学生的答题情况，输出一份结构严谨、维度明确、分析深刻的评估报告（Markdown 格式）。"
    user = f"""请针对以下【摸底诊断】生成一份专业评估报告。

{qa_text}

请严格按此 JSON 结构返回（report 部分使用 Markdown）：
{{
  "proficiency": {{ "考点1": 0-100, ... }},
  "overall_score": 0-100,
  "report": "### 1. 核心知识诊断\\n分析学生在各知识点上的深度和广度...\\n### 2. 学科能力多维分析\\n从逻辑思维、应用能力、基础稳固度等维度点评...\\n### 3. 个性化提分规划\\n给出具体的阶段性学习建议...",
  "question_results": [
    {{
      "id": 题目ID,
      "is_correct": true/false,
      "score": 该题得分,
      "feedback": "简短的一句式点评",
      "explanation": "详细的解题思路"
    }}
  ]
}}"""
    raw = chat_completion(system, user, temperature=0.0)
    data = parse_json_response(raw, fallback={})
    return (
        data.get("proficiency", {}), 
        data.get("report", "评估完成（解析生成失败）"), 
        float(data.get("overall_score", 0.0)),
        data.get("question_results", [])
    )
