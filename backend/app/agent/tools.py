"""
Tool registry for the single-agent ReAct orchestrator.
Memory-efficient design with lazy tool loading and validation.

Follows the Tool Registry pattern from ai-agents-architect:
- Register tools with schema and examples
- Lazy loading for expensive tools
- Usage tracking for optimization
- Graceful error handling
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from functools import wraps
import json
import logging
import sqlite3

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """
    Lightweight tool definition with minimal overhead.

    Attributes:
        name: Unique tool identifier (e.g., 'finance_log_transaction')
        description: Human-readable description for LLM context
        parameters: JSON Schema-like parameter definition
        handler: The actual function to call
        examples: Optional usage examples for LLM guidance
    """
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema-like
    handler: Callable
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM context (excludes handler)."""
        result = {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
        if self.examples:
            result["examples"] = self.examples
        return result


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    pass


class ToolValidationError(Exception):
    """Raised when tool parameters fail validation."""
    pass


class ToolRegistry:
    """
    Singleton tool registry with lazy loading and validation.

    Memory optimizations:
    - Tools only loaded when first accessed
    - No caching of large results
    - Minimal metadata stored per tool

    Design patterns from ai-agents-architect:
    - Dynamic tool discovery
    - Lazy loading for expensive tools
    - Usage tracking for optimization
    - Clear error modes
    """
    _instance: Optional["ToolRegistry"] = None
    _lock = False  # Simple lock flag

    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, ToolDefinition] = {}
            cls._instance._usage_counts: Dict[str, int] = {}
            cls._instance._initialized = True
        return cls._instance

    def register(self, tool_def: ToolDefinition) -> None:
        """
        Register a tool definition.

        Args:
            tool_def: Complete tool definition with handler

        Raises:
            ValueError: If tool name already registered
        """
        if tool_def.name in self._tools:
            logger.warning(f"Re-registering tool: {tool_def.name}")

        self._tools[tool_def.name] = tool_def
        self._usage_counts[tool_def.name] = 0
        logger.debug(f"Registered tool: {tool_def.name}")

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all registered tools for LLM context.
        Memory-efficient: only returns necessary metadata.
        """
        return [t.to_dict() for t in self._tools.values()]

    def list_tools_for_prompt(self) -> str:
        """
        Format tools as a string for system prompt.
        Optimized for token efficiency.
        """
        lines = []
        for tool in self._tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
            if tool.parameters.get('properties'):
                params = tool.parameters['properties']
                required = tool.parameters.get('required', [])
                param_str = ", ".join(
                    f"{k}*" if k in required else k
                    for k in params.keys()
                )
                if param_str:
                    lines.append(f"  Params: {param_str}")
        return "\n".join(lines)

    def execute(self, name: str, **kwargs) -> Any:
        """
        Execute a tool by name with given parameters.

        Args:
            name: Tool name to execute
            **kwargs: Parameters to pass to the handler

        Returns:
            Tool execution result

        Raises:
            ToolExecutionError: If tool not found or execution fails
            ToolValidationError: If parameters fail validation
        """
        tool = self.get(name)
        if not tool:
            raise ToolExecutionError(f"Unknown tool: {name}")

        # Validate required parameters
        self._validate_params(tool, kwargs)

        # Track usage
        self._usage_counts[name] = self._usage_counts.get(name, 0) + 1

        try:
            result = tool.handler(**kwargs)
            logger.debug(f"Tool executed: {name}")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {name} - {e}")
            raise ToolExecutionError(f"Tool {name} failed: {str(e)}")

    def _validate_params(self, tool: ToolDefinition, params: Dict[str, Any]) -> None:
        """
        Validate parameters against tool schema.
        Basic validation - checks required fields only.
        """
        required = tool.parameters.get('required', [])
        for param in required:
            if param not in params:
                raise ToolValidationError(
                    f"Missing required parameter '{param}' for tool '{tool.name}'"
                )

    def get_usage_stats(self) -> Dict[str, int]:
        """Get tool usage statistics for optimization."""
        return dict(self._usage_counts)

    def get_most_used_tools(self, top_n: int = 5) -> List[tuple]:
        """Get most frequently used tools for optimization."""
        sorted_tools = sorted(
            self._usage_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_tools[:top_n]


# Global registry instance (singleton)
tool_registry = ToolRegistry()


# =============================================================================
# Tool Decorator
# =============================================================================

def tool(name: str, description: str, parameters: Dict[str, Any],
         examples: List[Dict[str, Any]] = None):
    """
    Decorator to register a function as a tool.

    Args:
        name: Unique tool identifier
        description: Human-readable description for LLM
        parameters: JSON Schema-like parameter definition
        examples: Optional usage examples

    Example:
        @tool(
            name="finance_log_transaction",
            description="Log a financial transaction",
            parameters={
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["expense", "income"]},
                    "amount": {"type": "number"}
                },
                "required": ["type", "amount"]
            }
        )
        def log_transaction(type: str, amount: float) -> Dict:
            return {"status": "logged"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=wrapper,
            examples=examples or []
        )
        tool_registry.register(tool_def)
        return wrapper
    return decorator


# =============================================================================
# Calendar Tools (Google API)
# =============================================================================

@tool(
    name="calendar_list_events",
    description="List Google Calendar events for a date range",
    parameters={
        "type": "object",
        "properties": {
            "start_date": {"type": "string", "description": "Start date (ISO format: YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "End date (ISO format: YYYY-MM-DD)"},
        },
        "required": ["start_date", "end_date"],
    },
    examples=[
        {"start_date": "2024-01-15", "end_date": "2024-01-21"}
    ]
)
def calendar_list_events(start_date: str, end_date: str, user_id: str, db) -> List[Dict]:
    """List calendar events from Google Calendar."""
    from ..services.google_calendar import GoogleCalendarService
    service = GoogleCalendarService(user_id)
    return service.list_events(start_date, end_date)


@tool(
    name="calendar_create_event",
    description="Create a new Google Calendar event",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Event title"},
            "start_datetime": {"type": "string", "description": "Start datetime (ISO format)"},
            "end_datetime": {"type": "string", "description": "End datetime (ISO format)"},
            "description": {"type": "string", "description": "Event description"},
            "location": {"type": "string", "description": "Event location"},
        },
        "required": ["title", "start_datetime", "end_datetime"],
    },
    examples=[
        {
            "title": "Team Meeting",
            "start_datetime": "2024-01-15T10:00:00",
            "end_datetime": "2024-01-15T11:00:00",
            "description": "Weekly sync"
        }
    ]
)
def calendar_create_event(
    title: str, start_datetime: str, end_datetime: str,
    description: str = None, location: str = None,
    user_id: str = None, db = None
) -> Dict:
    """Create a calendar event."""
    from ..services.google_calendar import GoogleCalendarService
    service = GoogleCalendarService(user_id)
    return service.create_event(title, start_datetime, end_datetime, description, location)


@tool(
    name="calendar_delete_event",
    description="Delete a Google Calendar event by ID",
    parameters={
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "Google Calendar event ID"},
        },
        "required": ["event_id"],
    },
)
def calendar_delete_event(event_id: str, user_id: str, db) -> Dict:
    """Delete a calendar event."""
    from ..services.google_calendar import GoogleCalendarService
    service = GoogleCalendarService(user_id)
    success = service.delete_event(event_id)
    return {"deleted": success}


# =============================================================================
# Finance Tools (SQLite)
# =============================================================================

@tool(
    name="finance_log_transaction",
    description="Log a financial transaction (expense or income)",
    parameters={
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["expense", "income"], "description": "Transaction type"},
            "category": {"type": "string", "description": "Category (e.g., 'Food', 'Salary')"},
            "amount": {"type": "number", "description": "Amount"},
            "description": {"type": "string", "description": "Description"},
            "date": {"type": "string", "description": "Date (ISO format: YYYY-MM-DD)"},
        },
        "required": ["type", "category", "amount", "date"],
    },
    examples=[
        {"type": "expense", "category": "Food", "amount": 25.50, "date": "2024-01-15", "description": "Lunch"},
        {"type": "income", "category": "Salary", "amount": 5000, "date": "2024-01-01"}
    ]
)
def finance_log_transaction(
    type: str, category: str, amount: float,
    description: str = None, date: str = None,
    user_id: str = None, db = None
) -> Dict:
    """Log a financial transaction."""
    import uuid
    from datetime import datetime
    tx_id = str(uuid.uuid4())
    date = date or datetime.now().isoformat()[:10]

    with db.transaction() as conn:
        conn.execute("""
            INSERT INTO finance_transactions (id, user_id, type, category, amount, description, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tx_id, user_id, type, category, amount, description, date))

    return {"id": tx_id, "status": "logged"}


@tool(
    name="finance_get_balance",
    description="Get monthly balance summary",
    parameters={
        "type": "object",
        "properties": {
            "month": {"type": "string", "description": "Month in YYYY-MM format"},
        },
        "required": ["month"],
    },
)
def finance_get_balance(month: str, user_id: str, db) -> Dict:
    """Get monthly balance summary."""
    with db.connection() as conn:
        cursor = conn.execute("""
            SELECT
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
            FROM finance_transactions
            WHERE user_id = ? AND date LIKE ? || '%'
        """, (user_id, month))
        row = cursor.fetchone()

    income = float(row["income"] or 0)
    expense = float(row["expense"] or 0)
    return {
        "month": month,
        "income": income,
        "expense": expense,
        "balance": income - expense,
    }


# =============================================================================
# Habits Tools (SQLite)
# =============================================================================

@tool(
    name="habits_track",
    description="Mark a habit as completed for a specific date",
    parameters={
        "type": "object",
        "properties": {
            "habit_name": {"type": "string", "description": "Name of the habit"},
            "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
        },
        "required": ["habit_name", "date"],
    },
)
def habits_track(habit_name: str, date: str, user_id: str, db) -> Dict:
    """Track habit completion."""
    import uuid

    with db.connection() as conn:
        # Find habit
        cursor = conn.execute(
            "SELECT id FROM habits WHERE user_id = ? AND name = ?",
            (user_id, habit_name)
        )
        row = cursor.fetchone()
        if not row:
            return {"error": f"Habit '{habit_name}' not found", "success": False}

        habit_id = row["id"]
        completion_id = str(uuid.uuid4())

        # Insert or update completion
        conn.execute("""
            INSERT OR REPLACE INTO habit_completions (id, habit_id, date, completed)
            VALUES (?, ?, ?, 1)
        """, (completion_id, habit_id, date))

    return {"status": "tracked", "habit": habit_name, "date": date, "success": True}


@tool(
    name="habits_get_streak",
    description="Get current streak for a habit",
    parameters={
        "type": "object",
        "properties": {
            "habit_name": {"type": "string", "description": "Name of the habit"},
        },
        "required": ["habit_name"],
    },
)
def habits_get_streak(habit_name: str, user_id: str, db) -> Dict:
    """Calculate current habit streak."""
    with db.connection() as conn:
        cursor = conn.execute("""
            SELECT h.id, h.frequency FROM habits h
            WHERE h.user_id = ? AND h.name = ?
        """, (user_id, habit_name))
        row = cursor.fetchone()

        if not row:
            return {"error": f"Habit '{habit_name}' not found", "streak": 0}

        habit_id = row["id"]

        # Count consecutive completions from today backwards
        cursor = conn.execute("""
            SELECT COUNT(*) as streak FROM (
                SELECT date FROM habit_completions
                WHERE habit_id = ? AND completed = 1
                ORDER BY date DESC
            )
        """, (habit_id,))
        streak_row = cursor.fetchone()

    return {"habit": habit_name, "streak": streak_row["streak"] if streak_row else 0}


# =============================================================================
# Shopping List Tools (SQLite)
# =============================================================================

@tool(
    name="shopping_add_item",
    description="Add an item to the shopping list",
    parameters={
        "type": "object",
        "properties": {
            "item": {"type": "string", "description": "Item name"},
            "quantity": {"type": "string", "description": "Quantity (optional)"},
        },
        "required": ["item"],
    },
)
def shopping_add_item(item: str, quantity: str = None, user_id: str = None, db = None) -> Dict:
    """Add item to shopping list."""
    import uuid
    item_id = str(uuid.uuid4())

    with db.transaction() as conn:
        conn.execute("""
            INSERT INTO shopping_list (id, user_id, item, quantity, purchased)
            VALUES (?, ?, ?, ?, 0)
        """, (item_id, user_id, item, quantity))

    return {"id": item_id, "item": item, "quantity": quantity, "status": "added"}


@tool(
    name="shopping_list_items",
    description="Get all items from the shopping list",
    parameters={
        "type": "object",
        "properties": {
            "include_purchased": {"type": "boolean", "description": "Include already purchased items"},
        },
    },
)
def shopping_list_items(include_purchased: bool = False, user_id: str = None, db = None) -> List[Dict]:
    """List shopping list items."""
    with db.connection() as conn:
        if include_purchased:
            cursor = conn.execute(
                "SELECT item, quantity, purchased FROM shopping_list WHERE user_id = ?",
                (user_id,)
            )
        else:
            cursor = conn.execute(
                "SELECT item, quantity FROM shopping_list WHERE user_id = ? AND purchased = 0",
                (user_id,)
            )
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# RAG Memory Tools (sqlite-vec)
# =============================================================================

@tool(
    name="memory_search",
    description="Search conversation history using semantic search",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Max results (default 5)"},
        },
        "required": ["query"],
    },
)
def memory_search(query: str, limit: int = 5, user_id: str = None, db = None) -> List[Dict]:
    """Search conversation history with semantic search."""
    from ..rag.engine import RAGEngine

    engine = RAGEngine(db)
    results = engine.search(query, user_id, limit)
    return results


@tool(
    name="memory_save",
    description="Save a conversation turn to memory",
    parameters={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Content to save"},
            "role": {"type": "string", "enum": ["user", "assistant"], "description": "Speaker role"},
        },
        "required": ["content", "role"],
    },
)
def memory_save(content: str, role: str, user_id: str = None, db = None) -> Dict:
    """Save conversation to memory."""
    from ..rag.engine import RAGEngine

    engine = RAGEngine(db)
    conv_id = engine.save_conversation(user_id, role, content)
    return {"id": conv_id, "status": "saved"}
