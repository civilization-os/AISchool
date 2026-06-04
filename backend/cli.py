"""
AI School - 主程序（交互式 + 三色大纲 + 持久化存储）
流程：诊断评估 → 三色大纲 + 推荐路径 → 对话循环（/quiz 更新颜色）
"""
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from config.llm_config import LLMConfig
from core.database import init_db
from core import storage
from core.outline_agent import (
    generate_outline, recommend_next, display_outline, update_outline_from_quiz,
    COLOR_ICON, COLOR_LABEL
)


# ──────────────────────────────────────────────
# 工具：单次 LLM 调用（替代旧的 CrewAI Agent 调用）
# ──────────────────────────────────────────────
def ask_agent(agent_role: str, agent_goal: str, backstory: str,
              task_description: str, expected_output: str = "详细的回答",
              verbose: bool = False) -> str:
    from core.llm import get_chat_model
    from langchain_core.messages import SystemMessage, HumanMessage
    system = f"你是一位{agent_role}，目标是{agent_goal}，{backstory}"
    user = f"请{task_description}\n\n要求：{expected_output}"
    llm = get_chat_model(temperature=0.7)
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return resp.content


# ──────────────────────────────────────────────
# 阶段 1：诊断评估（出3题 → 用户答题 → AI评级，返回 level + 诊断摘要）
# ──────────────────────────────────────────────
def assess_level(name: str, topic: str) -> tuple[str, str]:
    """返回 (level, diagnostic_summary)"""
    print(f"\n📋 {name}，我先出 3 道小题了解你的基础～")
    print("─" * 55)

    questions_text = ask_agent(
        agent_role="诊断出题专家",
        agent_goal="生成快速诊断题",
        backstory="你是一位资深教育专家，擅长用简短问题快速判断学生知识水平。",
        task_description=(
            f"为主题「{topic}」生成 3 道诊断题，覆盖从入门到进阶的知识点。\n"
            "格式：每题单独一行，以序号开头（1. 2. 3.），简短清晰。只输出题目，不输出答案。"
        ),
        expected_output="3道诊断题，每题一行",
    )
    print(questions_text)
    print("─" * 55)

    answers = []
    for i in range(1, 4):
        ans = input(f"\n👉 第 {i} 题（不会直接回车跳过）: ").strip()
        answers.append(f"第{i}题答案：{ans or '（未作答）'}")
    answers_text = "\n".join(answers)

    # AI 同时评级 + 生成诊断摘要
    eval_result = ask_agent(
        agent_role="水平评估专家",
        agent_goal="评估学生水平并生成诊断摘要",
        backstory="你是一位专业教育评估师，能准确判断学生知识层次。",
        task_description=(
            f"学生「{name}」在主题「{topic}」的诊断结果：\n\n"
            f"题目：\n{questions_text}\n\n学生回答：\n{answers_text}\n\n"
            "请输出以下两部分：\n"
            "第一行：水平等级（只能是：beginner / intermediate / advanced）\n"
            "第二行起：2-3句话诊断摘要，说明哪些知识点掌握较好/较弱"
        ),
        expected_output="第一行水平等级，其余为诊断摘要",
    )

    lines = eval_result.strip().splitlines()
    level_raw = lines[0].strip().lower() if lines else "beginner"
    diagnostic_summary = "\n".join(lines[1:]).strip() if len(lines) > 1 else eval_result

    level = (
        "advanced" if "advanced" in level_raw
        else "intermediate" if "intermediate" in level_raw
        else "beginner"
    )
    labels = {"beginner": "初学者 🌱", "intermediate": "中级 🌿", "advanced": "高级 🌳"}
    print(f"\n✅ 水平评估：{labels[level]}")
    if diagnostic_summary:
        print(f"📝 {diagnostic_summary}")

    return level, diagnostic_summary


# ──────────────────────────────────────────────
# Quiz 指令（出题 → 逐题交互 → 批改 → 更新大纲颜色）
# ──────────────────────────────────────────────
def run_quiz(topic: str, level: str, outline_items: list,
             student_id: int, outline_id: int) -> list:
    """执行测验，返回更新后的 outline_items"""
    print("\n📝 生成小测验，稍候...")

    quiz_text = ask_agent(
        agent_role="题目设计专家",
        agent_goal="设计高质量测验题",
        backstory="你是一位专业题目设计师，擅长根据难度设计针对性测验。",
        task_description=(
            f"为主题「{topic}」（学生水平：{level}）生成 3 道测验题。\n"
            "每题以编号开头（1. 2. 3.），简短清晰，只输出题目，不输出答案。"
        ),
        expected_output="3道测验题",
    )
    print("\n" + "─" * 55)
    print(quiz_text)
    print("─" * 55)

    answers = []
    for i in range(1, 4):
        ans = input(f"\n✏️  第 {i} 题（跳过直接回车）: ").strip()
        answers.append(f"第{i}题：{ans or '（未作答）'}")

    print("\n⏳ 批改中...")
    feedback = ask_agent(
        agent_role="学习评估专家",
        agent_goal="批改测验给出详细反馈",
        backstory="你是一位严谨的教育评估专家，给出具体可操作的改进建议。",
        task_description=(
            f"批改「{topic}」测验：\n\n题目：\n{quiz_text}\n\n"
            f"学生答案：\n" + "\n".join(answers) + "\n\n"
            "请给出：1) 每题评分与正确答案 2) 总体评价 3) 后续学习建议"
        ),
        expected_output="完整批改报告",
    )
    print(f"\n📊 批改结果：\n{feedback}")

    # 更新大纲颜色
    print("\n🔄 更新知识点掌握状态...")
    item_dicts = [{"title": it.title, "description": it.description,
                   "color": it.color, "id": it.id} for it in outline_items]
    updated = update_outline_from_quiz(item_dicts, feedback)

    for upd in updated:
        storage.update_item_color(upd["id"], upd["color"])

    # 刷新 outline_items 对象颜色
    for it, upd in zip(outline_items, updated):
        it.color = upd["color"]

    print(display_outline(
        [{"title": it.title, "description": it.description, "color": it.color}
         for it in outline_items],
        title="更新后的学习大纲"
    ))
    return outline_items


# ──────────────────────────────────────────────
# 对话循环（用户主导）
# ──────────────────────────────────────────────
class ChatSession:
    def __init__(self, student_id: int, name: str, topic: str,
                 level: str, outline_items: list):
        self.student_id   = student_id
        self.name         = name
        self.topic        = topic
        self.level        = level
        self.outline_items = outline_items
        self.history: list[dict] = []

    def _build_context(self) -> str:
        if not self.history:
            return "（对话刚开始）"
        lines = []
        for h in self.history[-8:]:
            tag = "学生" if h["role"] == "user" else "AI老师"
            lines.append(f"{tag}：{h['content']}")
        return "\n".join(lines)

    def chat(self, user_input: str) -> str:
        ctx = self._build_context()
        outline_ctx = "、".join(
            f"{COLOR_ICON.get(it.color,'🔴')}{it.title}" for it in self.outline_items
        )
        response = ask_agent(
            agent_role="学科教学专家",
            agent_goal=f"辅导学生学习「{self.topic}」",
            backstory=(
                f"你是一位有10年教学经验的专家，正在辅导「{self.name}」"
                f"（{self.level}水平）学习「{self.topic}」。"
                f"大纲掌握状态：{outline_ctx}。"
                "请根据学生的薄弱点重点讲解，用清晰易懂的语言解答，适当举例，末尾可提引导性问题。"
            ),
            task_description=(
                f"对话历史：\n{ctx}\n\n学生最新输入：{user_input}"
            ),
            expected_output="针对学生输入的教学回应",
        )
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "ai",   "content": response})
        # 持久化
        storage.save_chat(self.student_id, self.topic, "user",  user_input)
        storage.save_chat(self.student_id, self.topic, "ai",    response)
        return response

    def summarize(self) -> str:
        ctx = self._build_context()
        return ask_agent(
            agent_role="学科教学专家",
            agent_goal="整理学习要点",
            backstory=f"你是一位经验丰富的{self.topic}老师。",
            task_description=(
                f"根据以下对话，为「{self.name}」整理「{self.topic}」的学习要点总结：\n{ctx}\n\n"
                "请输出结构化知识点总结（含重点、难点、记忆建议）。"
            ),
            expected_output="结构化知识点总结",
        )

    def run_loop(self, outline_id: int):
        level_cn = {"beginner": "初学者", "intermediate": "中级", "advanced": "高级"}.get(self.level, self.level)
        print(f"\n{'═'*55}")
        print(f"🎓 {self.topic} | {level_cn} | {self.name}")
        print("─" * 55)
        print("💡 指令：/quiz 测验  /练习 练习题  /总结 知识总结  /大纲 查看大纲  /exit 退出")
        print(f"{'═'*55}\n")

        # 开场白
        opening = ask_agent(
            agent_role="学科教学专家",
            agent_goal=f"开始辅导「{self.topic}」",
            backstory=f"你是一位有10年教学经验的专家，正在开始为「{self.name}」（{level_cn}水平）讲解「{self.topic}」。",
            task_description=(
                f"请友好开场，简述今天学习大纲，并针对红色（未掌握）的知识点提出第一个引导性问题。"
            ),
            expected_output="开场白 + 第一个引导性问题",
        )
        print(f"🤖 AI老师：{opening}\n")

        while True:
            try:
                user_input = input("👤 你：").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n👋 再见！")
                break

            if not user_input:
                continue

            cmd = user_input.lower()

            if cmd in ("/exit", "退出", "exit", "quit"):
                print("\n👋 学习结束！数据已保存，下次继续～")
                break

            elif cmd in ("/quiz", "quiz", "测验"):
                self.outline_items = run_quiz(
                    self.topic, self.level, self.outline_items,
                    self.student_id, outline_id
                )

            elif cmd in ("/练习", "练习", "/practice"):
                print("\n⏳ 生成练习题...")
                result = ask_agent(
                    agent_role="题目设计专家",
                    agent_goal="生成针对性练习题",
                    backstory="你是一位专业题目设计师。",
                    task_description=(
                        f"为「{self.name}」（{self.level}水平）生成「{self.topic}」的3道练习题，"
                        "包含参考答案。"
                    ),
                    expected_output="3道练习题 + 参考答案",
                )
                print(f"\n📝 练习题：\n{result}\n")

            elif cmd in ("/总结", "总结", "/summary"):
                print("\n⏳ 整理知识点...")
                result = self.summarize()
                print(f"\n📚 知识点总结：\n{result}\n")

            elif cmd in ("/大纲", "大纲", "/outline"):
                item_dicts = [{"title": it.title, "description": it.description,
                               "color": it.color} for it in self.outline_items]
                print(display_outline(item_dicts, title=f"{self.topic} 学习大纲"))
                print(recommend_next(item_dicts))

            else:
                print("\n⏳ 思考中...\n")
                response = self.chat(user_input)
                print(f"🤖 AI老师：{response}\n")


# ──────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────
def main():
    print("🎓 AI School - 智能学习辅导系统")
    print("=" * 55)

    # 初始化数据库
    try:
        init_db()
    except Exception as e:
        print(f"⚠️  数据库连接失败（{e}）")
        print("💡 请先执行：docker-compose up -d")
        return

    # 检查模型配置
    cfg = LLMConfig.check_config()
    print(f"模型：{cfg['provider'].upper()} / {cfg['model']} — {cfg['message']}")
    if cfg["status"] == "error":
        print(f"❌ {cfg['error']}")
        return

    print("\n📌 模式选择：")
    print("  1. 完整学习会话（诊断 → 三色大纲 → 对话辅导）")
    print("  2. 快速对话（直接进入辅导）")
    print("  3. 退出")

    choice = input("\n请选择 (1/2/3): ").strip()

    if choice == "1":
        name  = input("\n你的名字（默认: 同学）: ").strip() or "同学"
        topic = input("学习主题（例如: Python基础、微积分）: ").strip() or "Python编程基础"

        # 存储学生
        student = storage.get_or_create_student(name)

        # 阶段1：诊断评估
        level, diagnostic_summary = assess_level(name, topic)

        # 阶段2：生成三色大纲
        print("\n⏳ 根据诊断结果生成学习大纲，稍候...")
        item_dicts = generate_outline(topic, level, diagnostic_summary)

        # 展示大纲
        print(display_outline(item_dicts, title=f"{topic} 学习大纲"))
        print(recommend_next(item_dicts))

        # 存入数据库
        outline = storage.save_outline(student.id, topic, level, item_dicts)
        outline_items = storage.get_outline_items(outline.id)

        input("\n按 Enter 开始学习对话...")

        # 阶段3：对话循环
        session = ChatSession(student.id, name, topic, level, outline_items)
        session.run_loop(outline.id)

    elif choice == "2":
        name  = input("\n你的名字（默认: 同学）: ").strip() or "同学"
        topic = input("学习主题: ").strip() or "Python编程基础"
        level = "beginner"
        student = storage.get_or_create_student(name)

        # 查找已有大纲
        outline = storage.get_outline(student.id, topic)
        if outline:
            outline_items = storage.get_outline_items(outline.id)
            item_dicts = [{"title": it.title, "description": it.description,
                          "color": it.color} for it in outline_items]
            print(display_outline(item_dicts, title=f"上次的 {topic} 学习大纲"))
            level = outline.level
        else:
            outline_items = []
            outline = type("Outline", (), {"id": None})()  # dummy

        session = ChatSession(student.id, name, topic, level, outline_items)
        session.run_loop(outline.id)

    elif choice == "3":
        print("👋 再见！")


if __name__ == "__main__":
    main()