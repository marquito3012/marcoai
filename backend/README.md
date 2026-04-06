# Marco AI Backend

Memory-efficient modular monolith backend for Raspberry Pi 3 (1GB RAM).

## Quick Start

### Option 1: Run with Docker (Recommended)

```bash
# From project root
cp backend/.env.example backend/.env
# Edit .env and add your API keys

docker compose up -d --build

# View logs
docker compose logs -f

# Run tests inside container
docker compose exec marcoai ./run_tests.sh
```

### Option 2: Run Locally

```bash
cd backend

# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run tests
./run_tests.sh
# or: python -m pytest tests/ -v

# 4. Run server
uvicorn app.main:app --reload --port 8000
```

## Running Tests

```bash
# With Docker
docker compose exec marcoai ./run_tests.sh

# Local (after installing dependencies)
./run_tests.sh

# Direct pytest
python -m pytest tests/ -v --tb=short
```

## Project Structure

```
backend/
├── app/
│   ├── agent/
│   │   ├── orchestrator.py   # ReAct loop with tool calling
│   │   └── tools.py          # 12 registered tools
│   ├── modules/              # Domain routers
│   │   ├── calendar/
│   │   ├── finance/
│   │   ├── habits/
│   │   ├── food/
│   │   ├── leisure/
│   │   └── rag/
│   ├── services/             # Google API clients
│   ├── rag/                  # RAG engine
│   ├── config.py             # Settings (singleton)
│   ├── database.py           # SQLite manager
│   └── main.py               # FastAPI app
├── tests/
├── requirements.txt
├── Dockerfile
└── ARCHITECTURE.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/chat` | POST | Main chat with tool calling |
| `/api/calendar/events` | GET/POST | Calendar operations |
| `/api/finance/balance` | GET | Monthly balance |
| `/api/finance/transaction` | POST | Log transaction |
| `/api/habits/track` | POST | Track habit |
| `/api/habits/{name}/streak` | GET | Get streak |
| `/api/food/shopping` | GET | Shopping list |
| `/api/memory/search` | GET | Search memory |

## Environment Variables

```bash
# LLM APIs (at least one required)
GROQ_API_KEY=
OPENROUTER_API_KEY=
GEMINI_API_KEY=

# Google OAuth (for Calendar/Gmail)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Memory limits
MAX_MEMORY_MB=512
```

See `.env.example` for full list.

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system design.

**Key Pattern:** Single-Agent ReAct with Tool Calling
- Not a multi-agent swarm
- LLM selects Python functions via XML-style tool calls
- Saves API calls and memory vs multi-agent approaches
