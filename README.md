# Marco AI - Backend

Memory-efficient modular monolith backend for Raspberry Pi 3 (1GB RAM).

## Architecture

```
backend/
├── app/
│   ├── agent/              # Single-agent ReAct orchestrator
│   │   ├── __init__.py
│   │   ├── orchestrator.py # Tool-calling engine with API fallback
│   │   └── tools.py        # Tool registry and implementations
│   ├── auth/               # Google OAuth 2.0
│   ├── modules/            # Domain modules (modular monolith)
│   │   ├── finance/        # Expenses, income, balance
│   │   ├── habits/         # Binary habit tracking with streaks
│   │   ├── food/           # Shopping list, meal planning
│   │   ├── leisure/        # Events, game deals
│   │   └── rag/            # Semantic memory search
│   ├── rag/                # RAG engine with sqlite-vec
│   ├── services/           # External API clients (Google)
│   ├── config.py           # Memory-efficient settings
│   ├── database.py         # SQLite manager with optimizations
│   └── main.py             # FastAPI application
├── data/                   # SQLite database (persisted volume)
├── tests/                  # Unit tests
├── requirements.txt        # Minimal dependencies
├── Dockerfile              # Memory-optimized image
└── .env.example            # Environment template
```

## Key Design Decisions

### Memory Optimizations

1. **Singleton Pattern**: Settings, database connections, tool registry use singletons
2. **Lazy Loading**: LLM clients, OAuth credentials loaded only when first used
3. **Thread-local Storage**: One connection per thread, no connection pooling overhead
4. **__slots__**: Config class uses `__slots__` to prevent dynamic attribute allocation
5. **Minimal Middleware**: Only essential FastAPI middleware
6. **Single Worker**: Uvicorn runs with 1 worker to minimize memory footprint

### SQLite Optimizations

```sql
PRAGMA journal_mode=WAL;           -- Better concurrency
PRAGMA cache_size=-2000;           -- 2MB page cache
PRAGMA temp_store=MEMORY;          -- Temp tables in RAM
PRAGMA synchronous=NORMAL;         -- Balance safety/speed
```

### API Fallback Chain

```
Groq (primary) → OpenRouter (fallback) → Gemini (last resort)
```

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Fill in API keys
# - GROQ_API_KEY (required, fastest)
# - OPENROUTER_API_KEY (optional fallback)
# - GEMINI_API_KEY (optional fallback)
# - Google OAuth credentials (for Calendar/Gmail)

# 3. Run with Docker
docker compose up -d --build

# 4. Access the application
# - API: http://localhost:8000
# - Health: http://localhost:8000/health
# - Chat: POST http://localhost:8000/api/chat
```

## API Endpoints

### Core
- `POST /api/chat` - Main chat with tool-calling
- `GET /health` - Health check

### Finance
- `GET /api/finance/balance?month=YYYY-MM&user_id=X`
- `POST /api/finance/transaction`

### Habits
- `POST /api/habits/track`
- `GET /api/habits/{name}/streak`

### Food
- `GET /api/food/shopping`
- `POST /api/food/shopping/add`

### Leisure
- `GET /api/leisure/events`
- `GET /api/leisure/deals`

### Memory
- `GET /api/memory/search?q=query&user_id=X`

## Tool-Calling Format

The orchestrator uses XML-style tool calls in LLM responses:

```xml
<finance_log_transaction>{"type": "expense", "category": "Food", "amount": 25.50, "date": "2024-01-15"}</finance_log_transaction>
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --port 8000

# Run tests
pytest
```

## Raspberry Pi 3 Performance

| Metric | Target |
|--------|--------|
| Idle Memory | < 200MB |
| Peak Memory | < 512MB |
| Cold Start | < 5s |
| Tool Call Latency | < 500ms |

## License

MIT
