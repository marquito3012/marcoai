"""
Tests for the ReAct orchestrator and tool registry.
Memory-efficient test suite following TDD patterns.
"""
import pytest
import sqlite3
from unittest.mock import Mock, patch, MagicMock
import json


# =============================================================================
# Tool Registry Tests
# =============================================================================

class TestToolRegistry:
    """Test tool registry singleton and registration."""

    def test_registry_singleton(self):
        """Test that tool registry is a singleton."""
        from app.agent.tools import ToolRegistry

        registry1 = ToolRegistry()
        registry2 = ToolRegistry()

        assert registry1 is registry2, "Registry should be singleton"

    def test_tool_registration(self):
        """Test tool registration and retrieval."""
        from app.agent.tools import tool_registry, ToolDefinition

        # Create a mock tool
        def mock_handler():
            pass

        tool_def = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object"},
            handler=mock_handler
        )

        tool_registry.register(tool_def)

        # Verify registration
        retrieved = tool_registry.get("test_tool")
        assert retrieved is not None
        assert retrieved.name == "test_tool"
        assert retrieved.description == "A test tool"

    def test_tool_has_method(self):
        """Test tool existence check."""
        from app.agent.tools import tool_registry

        assert tool_registry.has("finance_log_transaction") is True
        assert tool_registry.has("nonexistent_tool") is False

    def test_duplicate_registration_warning(self, caplog):
        """Test that duplicate registration logs warning."""
        from app.agent.tools import tool_registry, ToolDefinition

        def handler1():
            pass

        def handler2():
            pass

        # Register twice
        tool_registry.register(ToolDefinition(
            name="dup_tool",
            description="First",
            parameters={},
            handler=handler1
        ))
        tool_registry.register(ToolDefinition(
            name="dup_tool",
            description="Second",
            parameters={},
            handler=handler2
        ))

        # Should have logged warning
        assert "Re-registering" in caplog.text

    def test_list_tools_excludes_handler(self):
        """Test that list_tools doesn't include handler in output."""
        from app.agent.tools import tool_registry

        tools = tool_registry.list_tools()

        for tool in tools:
            assert "handler" not in tool
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool

    def test_list_tools_for_prompt_format(self):
        """Test tools formatting for system prompt."""
        from app.agent.tools import tool_registry

        prompt = tool_registry.list_tools_for_prompt()

        assert isinstance(prompt, str)
        assert "finance_log_transaction" in prompt
        assert "calendar_create_event" in prompt


class TestToolExecution:
    """Test tool execution and validation."""

    def test_execute_unknown_tool_raises(self):
        """Test that executing unknown tool raises error."""
        from app.agent.tools import tool_registry, ToolExecutionError

        with pytest.raises(ToolExecutionError) as exc_info:
            tool_registry.execute("nonexistent_tool")

        assert "Unknown tool" in str(exc_info.value)

    def test_execute_missing_required_param(self):
        """Test that missing required params raises validation error."""
        from app.agent.tools import tool_registry, ToolValidationError

        # finance_log_transaction requires: type, category, amount, date
        with pytest.raises(ToolValidationError) as exc_info:
            tool_registry.execute(
                "finance_log_transaction",
                type="expense"  # Missing other required params
            )

        assert "Missing required parameter" in str(exc_info.value)

    def test_execute_valid_tool(self, mock_db):
        """Test successful tool execution."""
        from app.agent.tools import tool_registry

        # Execute with all required params
        result = tool_registry.execute(
            "finance_log_transaction",
            type="expense",
            category="Food",
            amount=25.50,
            date="2024-01-15",
            description="Test lunch",
            user_id="test-user",
            db=mock_db
        )

        assert result["status"] == "logged"
        assert "id" in result

    def test_usage_tracking(self):
        """Test that tool usage is tracked."""
        from app.agent.tools import tool_registry

        initial_stats = tool_registry.get_usage_stats()
        initial_count = initial_stats.get("finance_log_transaction", 0)

        # Execute tool
        try:
            tool_registry.execute(
                "finance_log_transaction",
                type="expense",
                category="Test",
                amount=10,
                date="2024-01-01",
                user_id="test",
                db=Mock()
            )
        except Exception:
            pass  # Ignore DB errors

        new_stats = tool_registry.get_usage_stats()
        assert new_stats.get("finance_log_transaction", 0) > initial_count


class TestToolDecorator:
    """Test the @tool decorator."""

    def test_decorator_registers_tool(self):
        """Test that @tool decorator auto-registers function."""
        from app.agent.tools import tool_registry, tool

        @tool(
            name="decorated_test_tool",
            description="Test description",
            parameters={"type": "object"}
        )
        def test_func():
            return "test result"

        assert tool_registry.has("decorated_test_tool")
        retrieved = tool_registry.get("decorated_test_tool")
        assert retrieved.description == "Test description"


# =============================================================================
# ReAct Orchestrator Tests
# =============================================================================

class TestReActOrchestrator:
    """Test the ReAct orchestrator."""

    def test_orchestrator_initialization(self):
        """Test orchestrator creates with minimal setup."""
        from app.agent.orchestrator import SyncReActOrchestrator

        orchestrator = SyncReActOrchestrator()

        assert orchestrator is not None
        assert orchestrator.MAX_ITERATIONS == 3
        assert orchestrator._settings is not None

    def test_orchestrator_settings_singleton(self):
        """Test that orchestrator uses singleton settings."""
        from app.agent.orchestrator import SyncReActOrchestrator
        from app.config import get_settings

        orchestrator = SyncReActOrchestrator()
        settings = get_settings()

        assert orchestrator._settings is settings

    def test_tool_parsing_single_call(self):
        """Test XML-style tool call parsing."""
        from app.agent.orchestrator import SyncReActOrchestrator

        orchestrator = SyncReActOrchestrator()

        response = '''
        Let me log that expense.
        <finance_log_transaction>{"type": "expense", "category": "Food", "amount": 25.50, "date": "2024-01-15"}</finance_log_transaction>
        '''

        tool_calls = orchestrator._parse_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0].name == "finance_log_transaction"
        assert tool_calls[0].arguments["amount"] == 25.50
        assert tool_calls[0].arguments["type"] == "expense"

    def test_tool_parsing_multiple_calls(self):
        """Test parsing multiple tool calls in one response."""
        from app.agent.orchestrator import SyncReActOrchestrator

        orchestrator = SyncReActOrchestrator()

        response = '''
        <calendar_create_event>{"title": "Meeting", "start_datetime": "2024-01-15T10:00:00", "end_datetime": "2024-01-15T11:00:00"}</calendar_create_event>
        <habits_track>{"habit_name": "Exercise", "date": "2024-01-15"}</habits_track>
        '''

        tool_calls = orchestrator._parse_tool_calls(response)

        assert len(tool_calls) == 2
        assert tool_calls[0].name == "calendar_create_event"
        assert tool_calls[1].name == "habits_track"

    def test_tool_parsing_invalid_json(self):
        """Test parsing handles invalid JSON gracefully."""
        from app.agent.orchestrator import SyncReActOrchestrator

        orchestrator = SyncReActOrchestrator()

        response = '<finance_log_transaction>{invalid json}</finance_log_transaction>'

        tool_calls = orchestrator._parse_tool_calls(response)

        # Should still parse but with empty args
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "finance_log_transaction"

    def test_tool_parsing_no_calls(self):
        """Test parsing returns empty list when no tool calls."""
        from app.agent.orchestrator import SyncReActOrchestrator

        orchestrator = SyncReActOrchestrator()

        response = "Sure, I can help with that! Let me know what you need."

        tool_calls = orchestrator._parse_tool_calls(response)

        assert len(tool_calls) == 0

    def test_format_tool_results_success(self):
        """Test formatting successful tool results."""
        from app.agent.orchestrator import SyncReActOrchestrator

        orchestrator = SyncReActOrchestrator()

        results = [
            {"success": True, "tool": "finance_log", "result": {"id": "123"}, "error": None}
        ]

        formatted = orchestrator._format_tool_results(results)

        assert "SUCCESS" in formatted
        assert "finance_log" in formatted
        assert "123" in formatted

    def test_format_tool_results_error(self):
        """Test formatting failed tool results."""
        from app.agent.orchestrator import SyncReActOrchestrator

        orchestrator = SyncReActOrchestrator()

        results = [
            {"success": False, "tool": "calendar_create", "result": None, "error": "API error"}
        ]

        formatted = orchestrator._format_tool_results(results)

        assert "ERROR" in formatted
        assert "API error" in formatted


class TestReActLoop:
    """Test the ReAct loop behavior."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked LLM."""
        from app.agent.orchestrator import SyncReActOrchestrator
        return SyncReActOrchestrator()

    def test_max_iterations_enforced(self, orchestrator):
        """Test that max iterations prevents infinite loops."""
        # This tests the safeguard - in real usage, LLM would eventually respond
        # without tool calls. Here we verify the limit exists.
        assert orchestrator.MAX_ITERATIONS == 3

    def test_process_returns_response_dict(self, mock_db):
        """Test that process returns structured response."""
        from app.agent.orchestrator import SyncReActOrchestrator

        orchestrator = SyncReActOrchestrator(db=mock_db)

        # Mock the LLM call to return immediate response (no tool calls)
        with patch.object(orchestrator, '_call_llm') as mock_llm:
            mock_llm.return_value = "I'd be happy to help you with that!"

            result = orchestrator.process_sync(
                user_input="Hello!",
                user_id="test-user"
            )

        assert isinstance(result, dict)
        assert "response" in result
        assert "conversation_id" in result
        assert "tool_calls" in result
        assert "iterations" in result
        assert result["response"] == "I'd be happy to help you with that!"

    def test_process_with_tool_call(self, mock_db):
        """Test process with a tool call."""
        from app.agent.orchestrator import SyncReActOrchestrator

        orchestrator = SyncReActOrchestrator(db=mock_db)

        # First call returns tool call, second returns final response
        responses = [
            '<shopping_add_item>{"item": "Milk"}</shopping_add_item>',
            "I've added Milk to your shopping list!"
        ]

        with patch.object(orchestrator, '_call_llm') as mock_llm:
            mock_llm.side_effect = responses

            result = orchestrator.process_sync(
                user_input="Add milk to my shopping list",
                user_id="test-user"
            )

        assert result["tool_calls"] >= 1
        assert result["iterations"] == 2  # Two LLM calls


class TestMemoryEfficiency:
    """Test memory-efficient design patterns."""

    def test_settings_singleton(self):
        """Test that settings uses singleton pattern."""
        from app.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_database_singleton(self, mock_db):
        """Test that database manager uses singleton pattern."""
        from app.database import DatabaseManager

        # Note: In tests, we might get different instances due to mocking
        # The singleton is for production use
        db1 = DatabaseManager()
        db2 = DatabaseManager()

        assert db1 is db2

    def test_tool_registry_singleton(self):
        """Test that tool registry uses singleton pattern."""
        from app.agent.tools import ToolRegistry

        registry1 = ToolRegistry()
        registry2 = ToolRegistry()

        assert registry1 is registry2


# =============================================================================
# Integration Tests (with mock DB)
# =============================================================================

class TestFinanceTools:
    """Test finance tools end-to-end."""

    @pytest.fixture
    def mock_db(self):
        """Create in-memory SQLite database with MockDatabaseManager wrapper."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row

        conn.execute("""
            CREATE TABLE finance_transactions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                date TEXT NOT NULL
            )
        """)

        # Wrap in MockDatabaseManager to provide .transaction() and .connection() methods
        from tests.conftest import MockDatabaseManager
        mock_db_manager = MockDatabaseManager(conn)

        yield mock_db_manager
        conn.close()

    def test_log_expense(self, mock_db):
        """Test logging an expense."""
        from app.agent.tools import finance_log_transaction

        result = finance_log_transaction(
            type="expense",
            category="Food",
            amount=25.50,
            description="Lunch",
            date="2024-01-15",
            user_id="test-user",
            db=mock_db
        )

        assert result["status"] == "logged"

        # Verify in database (use _conn to access raw connection for verification)
        cursor = mock_db._conn.execute(
            "SELECT * FROM finance_transactions WHERE id = ?",
            (result["id"],)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["type"] == "expense"
        assert row["amount"] == 25.50

    def test_log_income(self, mock_db):
        """Test logging income."""
        from app.agent.tools import finance_log_transaction

        result = finance_log_transaction(
            type="income",
            category="Salary",
            amount=5000,
            date="2024-01-01",
            user_id="test-user",
            db=mock_db
        )

        assert result["status"] == "logged"

    def test_get_balance(self, mock_db):
        """Test getting monthly balance."""
        from app.agent.tools import finance_log_transaction, finance_get_balance

        # Add transactions
        finance_log_transaction(
            type="income", category="Salary", amount=5000,
            date="2024-01-15", user_id="test-user", db=mock_db
        )
        finance_log_transaction(
            type="expense", category="Food", amount=500,
            date="2024-01-20", user_id="test-user", db=mock_db
        )

        # Get balance
        result = finance_get_balance("2024-01", "test-user", mock_db)

        assert result["month"] == "2024-01"
        assert result["income"] == 5000
        assert result["expense"] == 500
        assert result["balance"] == 4500


class TestHabitsTools:
    """Test habits tools end-to-end."""

    @pytest.fixture
    def mock_db_with_habit(self, mock_db):
        """Create database with a test habit."""
        # Access raw connection for setup
        conn = mock_db._conn

        conn.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                frequency TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS habit_completions (
                id TEXT PRIMARY KEY,
                habit_id TEXT NOT NULL,
                date TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 1,
                UNIQUE(habit_id, date)
            )
        """)

        # Add a test habit
        conn.execute(
            "INSERT INTO habits (id, user_id, name, frequency, active) VALUES (?, ?, ?, ?, ?)",
            ("habit-1", "test-user", "Exercise", '{"type": "daily"}', 1)
        )

        yield mock_db

    def test_track_habit(self, mock_db_with_habit):
        """Test tracking a habit."""
        from app.agent.tools import habits_track

        result = habits_track(
            habit_name="Exercise",
            date="2024-01-15",
            user_id="test-user",
            db=mock_db_with_habit
        )

        assert result["success"] is True
        assert result["status"] == "tracked"

    def test_track_nonexistent_habit(self, mock_db_with_habit):
        """Test tracking a habit that doesn't exist."""
        from app.agent.tools import habits_track

        result = habits_track(
            habit_name="NonExistent",
            date="2024-01-15",
            user_id="test-user",
            db=mock_db_with_habit
        )

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_get_streak(self, mock_db_with_habit):
        """Test getting habit streak."""
        from app.agent.tools import habits_track, habits_get_streak

        # Track habit for 3 consecutive days
        habits_track("Exercise", "2024-01-13", "test-user", mock_db_with_habit)
        habits_track("Exercise", "2024-01-14", "test-user", mock_db_with_habit)
        habits_track("Exercise", "2024-01-15", "test-user", mock_db_with_habit)

        result = habits_get_streak("Exercise", "test-user", mock_db_with_habit)

        assert result["habit"] == "Exercise"
        assert result["streak"] == 3
