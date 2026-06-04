# AI School

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/vue-3.4-brightgreen)](https://vuejs.org/)
[![LangGraph](https://img.shields.io/badge/langgraph-0.2%2B-purple)](https://langchain-ai.github.io/langgraph/)
[![Tests](https://img.shields.io/badge/tests-82%20passed-brightgreen)](backend/tests)

An AI-powered learning platform with structured knowledge cards, multi-semester course planning, and adaptive quizzes. Built with LangChain + LangGraph on the backend and Vue 3 + Tailwind on the frontend.

## Architecture

```
frontend/          Vue 3 + Tailwind + Vite
     │  REST
backend/           FastAPI + LangChain + LangGraph
     │
     ├── core/state.py      11-state session machine
     ├── core/nodes.py      LangGraph node functions
     ├── core/graph.py      5 sub-graph definitions
     ├── core/knowledge.py  Knowledge graph + mastery model
     ├── core/lesson.py     Multi-dimension knowledge cards
     └── core/llm.py        Unified LLM (DeepSeek / OpenAI)
```

## Features

- **Multi-semester courses** — Generate 1/2/3 semester syllabi with difficulty progression
- **Knowledge cards** — Each topic presented through definition, geometric, physical, formula, example, and lab cards
- **Browse / Focus modes** — Tiled overview or single-card deep dive
- **Adaptive quizzes** — AI-generated quiz with pass/retry workflow
- **Progress tracking** — Weighted by difficulty and mastery score
- **State machine** — 11-state session management with conditional routing

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- DeepSeek / OpenAI compatible API key

### Backend

```bash
git clone https://github.com/civilization-os/AISchool.git
cd AISchool

cp backend/.env.example backend/.env
# Edit backend/.env — set your DEEPSEEK_API_KEY

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

## Workflow

```
Launchpad
  └─ Type "微积分" → AI normalizes name + suggests difficulty
      └─ Select: 🏁 1-semester / 📗📘 2-semester / 📗📘📕 3-semester
          └─ CourseStudio (syllabus = course itself)
              ├─ Click topic → Classroom
              │     ├─ 📖 Definition (always first)
              │     ├─ 📐 Geometric / ⚡ Physical / 🧮 Formula
              │     ├─ 💡 Examples / 🔬 Lab / 🌍 Application
              │     └─ Browse ↔ Focus mode toggle
              ├─ 📝 Quiz → Pass → Mark done
              └─ 🔄 Regenerate syllabus (with confirmation)
```

## State Machine

```
IDLE → ASSESSING → ASSESSED → SYLLABUS_READY → LEARNING
  → QUIZ_ACTIVE → QUIZ_REVIEW → [passed]  ITEM_DONE
                               → [failed]  LEARNING (retry)
  → ITEM_DONE → [next] LEARNING → [done] complete
```

## Testing

```bash
cd backend
python -m pytest tests/ -v
# 82 passed in 1.8s
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/course/normalize` | Normalize course name, suggest levels |
| POST | `/session/create` | Create learning session |
| GET | `/session/{id}` | Get session with state_status |
| POST | `/assessment/start/{id}` | Generate assessment |
| POST | `/assessment/submit/{id}` | Submit & grade |
| POST | `/assessment/skip/{id}` | Skip assessment |
| POST | `/syllabus/generate/{id}` | Generate syllabus (`?force=true` to reset) |
| POST | `/classroom/start/{id}` | Start lesson → LessonDeck cards |
| POST | `/classroom/ask/{id}` | Follow-up question |
| POST | `/classroom/start-quiz/{id}` | Generate quiz |
| POST | `/classroom/submit-quiz/{id}` | Submit & grade quiz |
| POST | `/syllabus/item/{id}/complete` | Mark item done |

## Configuration

```env
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DATABASE_URL=sqlite:///./database.db
LLM_PROVIDER=deepseek
```

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python, FastAPI, LangChain, LangGraph |
| Frontend | Vue 3, Tailwind CSS, Vite, Lucide Icons |
| Database | SQLite (dev) / PostgreSQL (prod) |
| LLM | DeepSeek / OpenAI compatible |
| Testing | pytest (backend), Vitest (frontend) |

## Project Structure

```
AISchool/
├── backend/
│   ├── api/main.py           FastAPI endpoints
│   ├── core/
│   │   ├── state.py          Session state enum & TypedDict
│   │   ├── nodes.py          LangGraph node functions
│   │   ├── graph.py          Graph definitions (5 sub-graphs)
│   │   ├── knowledge.py      Knowledge graph & mastery model
│   │   ├── lesson.py         LessonDeck knowledge cards
│   │   └── llm.py            Unified LLM init
│   ├── db/                   SQLAlchemy models + CRUD
│   └── tests/                82 tests
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── Launchpad.vue     Course creation hub
│   │   │   └── CourseStudio.vue  Main learning workspace
│   │   ├── components/
│   │   │   └── studio/           Classroom, Assessment, Quiz
│   │   └── layouts/MainLayout.vue
│   └── package.json
└── README.md
```

## License

MIT
