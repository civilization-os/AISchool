# AI School — 智能学习辅导系统

基于 LangChain + LangGraph 的 AI 教学系统。支持多学期难度分级、结构化知识卡片、随堂测验。

## Architecture

```
frontend/  (Vue 3 + Tailwind + Vite)
     │  REST + SSE
backend/   (FastAPI + LangChain + LangGraph)
     │
     ├── core/state.py      ← 11-state session state machine
     ├── core/nodes.py      ← LangGraph node functions
     ├── core/graph.py      ← Graph definitions (5 sub-graphs)
     ├── core/knowledge.py  ← Knowledge graph + mastery model
     ├── core/lesson.py     ← LessonDeck knowledge cards
     └── core/llm.py        ← Unified ChatOpenAI (DeepSeek)
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- DeepSeek API key (or any OpenAI-compatible API)

### Backend

```bash
# 1. Clone & enter
git clone https://github.com/civilization-os/AISchool.git
cd AISchool

# 2. Setup config
cp backend/.env.example backend/.env
# Edit backend/.env — set your DEEPSEEK_API_KEY

# 3. Install & run
pip install -r backend/requirements.txt
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

### Verify

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"2.0.0","service":"AI School"}
```

## Feature Overview

### Course Creation
```
Launchpad → Type "微积分" → AI normalizes name + suggests levels
  → Select difficulty: 🏁单学期 / 📗📘双学期 / 📗📘📕三学期
  → Create → CourseStudio
```

### Learning Flow
```
CourseStudio (syllabus = course itself)
  ├── Knowledge points grouped by chapters
  ├── Click → Classroom (knowledge cards)
  │     ├── 📖 Definition (always first)
  │     ├── 📐 Geometric meaning
  │     ├── ⚡ Physical meaning
  │     ├── 🧮 Formula
  │     ├── 💡 Examples
  │     └── 🔬 Lab
  │     └── Browse mode / Focus mode toggle
  ├── 📝 Quiz → Pass → Mark done → Progress saved
  └── 🔄 Regenerate syllabus (with confirmation modal)
```

### State Machine (11 states)

```
IDLE → ASSESSING → ASSESSED → SYLLABUS_READY → LEARNING
  → QUIZ_ACTIVE → QUIZ_REVIEW → [passed] ITEM_DONE
                               → [failed] LEARNING (retry)
  → ITEM_DONE → [next] LEARNING → [done] complete
```

## Testing

```bash
cd backend
python -m pytest tests/ -v
# 82 passed
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/course/normalize` | Normalize course name, suggest levels |
| POST | `/session/create` | Create learning session |
| GET | `/session/{id}` | Get session detail with state_status |
| POST | `/assessment/start/{id}` | Generate assessment questions |
| POST | `/assessment/submit/{id}` | Submit & grade assessment |
| POST | `/assessment/skip/{id}` | Skip assessment |
| POST | `/syllabus/generate/{id}` | Generate syllabus (supports `?force=true`) |
| POST | `/classroom/start/{id}` | Start lesson, returns LessonDeck |
| POST | `/classroom/ask/{id}` | Ask follow-up question |
| POST | `/classroom/start-quiz/{id}` | Generate quiz questions |
| POST | `/classroom/submit-quiz/{id}` | Submit & grade quiz |
| POST | `/syllabus/item/{id}/complete` | Mark item done, update progress |

## Configuration

Edit `backend/.env`:

```env
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DATABASE_URL=sqlite:///./database.db
LLM_PROVIDER=deepseek
```
