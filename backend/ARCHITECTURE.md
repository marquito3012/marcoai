# Marco AI Backend Architecture

## Overview

Memory-efficient **Single-Agent ReAct Orchestrator** with LLM Tool Calling.

**Key Design Decision:** Instead of a multi-agent swarm, we use a single agent that selects and executes Python functions via tool calling. This saves:
- API calls (no inter-agent communication)
- Memory (no multiple agent contexts)
- Latency (direct function execution)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌─────────────────────────────────────┐  │
│  │   /api/chat  │────▶│   ReAct Orchestrator                │  │
│  │   (POST)     │     │   - Max 3 iterations                │  │
│  │              │     │   - Lazy LLM client                 │  │
│  │              │     │   - API fallback chain              │  │
│  └──────────────┘     └──────────────┬──────────────────────┘  │
│                                      │                          │
│                                      ▼                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Tool Registry                           │  │
│  │  ┌─────────────┬─────────────┬─────────────┬───────────┐  │  │
│  │  │  Calendar   │   Finance   │   Habits    │  Shopping │  │  │
│  │  │  Tools      │   Tools     │   Tools     │  Tools    │  │  │
│  │  └─────────────┴─────────────┴─────────────┴───────────┘  │  │
│  │  ┌─────────────┬─────────────┐                             │  │
│  │  │   RAG       │   Leisure   │                             │  │
│  │  │   Memory    │   Tools     │                             │  │
│  │  └─────────────┴─────────────┘                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                      │                          │
│         ┌────────────────────────────┼──────────────────────┐   │
│         │                            │                      │   │
│         ▼                            ▼                      ▼   │
│  ┌─────────────┐             ┌─────────────┐        ┌──────────┐│
│  │ LLM APIs    │             │   SQLite    │        │  Google  ││
│  │ Groq        │             │   + vec     │        │  OAuth   ││
│  │ OpenRouter  │             │   (local)   │        │  APIs    ││
│  │ Gemini      │             │             │        │          ││
│  └─────────────┘             └─────────────┘        └──────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## ReAct Loop Pattern

```
User Input
    │
    ▼
┌─────────────────────────────────────────────┐
│  Iteration 1 (max 3)                        │
│  1. LLM reasons about tools needed          │
│  2. Parses tool calls: <tool>{json}</tool>  │
│  3. Executes tools via registry             │
│  4. Formats results for LLM                 │
└─────────────────────────────────────────────┘
    │
    ├─► More tools needed? ──► Next iteration
    │
    └─► No tools? ──► Final response
```

## Tool Registration System

### Tool Definition

```python
@tool(
    name="finance_log_transaction",
    description="Log a financial transaction (expense or income)",
    parameters={
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["expense", "income"]},
            "category": {"type": "string"},
            "amount": {"type": "number"},
            "date": {"type": "string"},
        },
        "required": ["type", "category", "amount", "date"],
    },
    examples=[
        {"type": "expense", "category": "Food", "amount": 25.50}
    ]
)
def finance_log_transaction(
    type: str, category: str, amount: float,
    date: str, user_id: str, db
) -> Dict:
    """Implementation here"""
```

### Tool Call Format (XML-style)

```xml
<finance_log_transaction>
{"type": "expense", "category": "Food", "amount": 25.50, "date": "2024-01-15"}
</finance_log_transaction>
```

### Execution Flow

```
1. LLM generates response with tool call XML
2. Orchestrator parses: regex <(\w+)>(\{.*\})</\1>
3. Validates required parameters
4. Executes handler with user_id, db injected
5. Returns structured result:
   {
     "success": true,
     "tool": "finance_log_transaction",
     "result": {"id": "...", "status": "logged"},
     "error": null
   }
```

## Memory Optimizations

| Component | Optimization | Impact |
|-----------|--------------|--------|
| **Settings** | Singleton + `__slots__` | ~50% less memory |
| **Database** | Thread-local connection | No pool overhead |
| **Tool Registry** | Singleton, lazy loading | Tools loaded on-demand |
| **LLM Client** | Lazy initialization | Only created when needed |
| **API Fallback** | Try Groq → OpenRouter → Gemini | Graceful degradation |
| **ReAct Loop** | Max 3 iterations | Prevents infinite loops |
| **SQLite** | WAL mode, 2MB cache | Better concurrency |

## API Fallback Chain

```python
api_order = ["groq", "openrouter", "gemini"]

for api in api_order:
    try:
        client = create_client(api)
        client.models.list()  # Health check
        return client  # Success
    except Exception:
        logger.warning(f"{api} unavailable, trying next")
        continue

raise RuntimeError("All APIs failed")
```

## Module Structure

```
app/
├── agent/
│   ├── orchestrator.py   # ReAct loop, LLM integration
│   └── tools.py          # Tool registry, decorators, implementations
├── modules/              # Domain modules (modular monolith)
│   ├── calendar/         # Google Calendar
│   ├── finance/          # SQLite-based transactions
│   ├── habits/           # Streak tracking
│   ├── food/             # Shopping, meal planning
│   ├── leisure/          # Events, game deals
│   └── rag/              # Memory search
├── services/             # External API clients
│   ├── google_calendar.py
│   └── google_gmail.py
├── rag/                  # RAG engine
│   └── engine.py         # sqlite-vec integration
└── database.py           # SQLite manager
```

## Error Handling

### Tool Execution Errors

```python
try:
    result = tool_registry.execute("tool_name", **params)
    return {"success": True, "result": result}
except ToolValidationError as e:
    return {"success": False, "error": f"Invalid params: {e}"}
except ToolExecutionError as e:
    return {"success": False, "error": str(e)}
```

### LLM Errors

```python
try:
    response = await orchestrator.process(user_input, user_id)
except RuntimeError as e:
    return {"response": "API unavailable, please try again later"}
```

## Testing

```bash
# Run tests
cd backend
./run_tests.sh

# Or with pytest directly
pytest tests/test_orchestrator.py -v
```

### Test Coverage

- `TestToolRegistry` - Singleton, registration, validation
- `TestToolExecution` - Parameter validation, error handling
- `TestReActOrchestrator` - Parsing, loop behavior
- `TestFinanceTools` - End-to-end with mock DB
- `TestHabitsTools` - Streak calculations

## Performance Targets (Raspberry Pi 3)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Idle Memory | < 200MB | `docker stats` |
| Cold Start | < 5s | Time to first request |
| Tool Call Latency | < 500ms | LLM + execution |
| Max Memory | < 512MB | Under load |

## Security Considerations

1. **User Isolation**: All queries include `user_id` filter
2. **SQL Injection**: Parameterized queries only
3. **OAuth Tokens**: Stored encrypted in `user_preferences`
4. **API Keys**: Environment variables only (never committed)

## Future Enhancements

1. **Tool Caching**: Cache expensive tool results (e.g., calendar fetch)
2. **Progressive Tool Loading**: Load tool definitions on-demand
3. **Batch Tool Execution**: Execute independent tools in parallel
4. **Tool Usage Analytics**: Track most-used tools for optimization
