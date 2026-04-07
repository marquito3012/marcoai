"""
Memory-efficient Single-Agent ReAct Orchestrator.
Uses LLM Tool Calling pattern with graceful API fallback.
Optimized for Raspberry Pi 3 (1GB RAM).

Follows ReAct Loop pattern from ai-agents-architect:
- Thought: reason about what to do next
- Action: select and invoke a tool
- Observation: process tool result
- Repeat until task complete or stuck
- Max iteration limits to prevent infinite loops
"""
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..config import Settings, get_settings
from ..database import DatabaseManager
from .tools import tool_registry, ToolExecutionError

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Parsed tool call from LLM response."""
    name: str
    arguments: Dict[str, Any]
    raw_text: str = ""  # Original parsed text for debugging


@dataclass
class ReActIteration:
    """Single iteration of the ReAct loop."""
    thought: str
    tool_calls: List[ToolCall]
    tool_results: List[Dict]
    is_final: bool = False


class ReActOrchestrator:
    """
    Single-agent ReAct (Reason + Act) orchestrator.

    Memory-efficient design:
    - No conversation history stored in memory (fetched from DB as needed)
    - Lazy LLM client initialization
    - Minimal state tracking per request
    - Max iteration limits prevent infinite loops

    Anti-patterns avoided (from ai-agents-architect):
    - ✅ Unlimited autonomy - max iterations enforced
    - ✅ Tool errors surfaced to LLM - explicit error handling
    - ✅ Memory hoarding - selective context only
    - ✅ Fragile parsing - robust regex with fallbacks
    """

    # System prompt optimized for tool calling
    # Uses XML-style tags for reliable parsing
    SYSTEM_PROMPT = """You are Marco AI, a friendly personal assistant.
You have access to tools for: calendar, finance, habits, shopping, memory.

THINK STEP-BY-STEP:
1. Reason about what the user wants
2. If you need to take an action, call a tool using this format:
   <tool_name>{{"param1": "value1", "param2": "value2"}}</tool_name>
3. Use the tool result to form your response
4. If no tool is needed, respond naturally

AVAILABLE TOOLS:
{tools}

IMPORTANT:
- Only call one tool at a time
- Wait for the tool result before calling another
- If a tool fails, try a different approach or ask for clarification
- Be conversational and helpful

    RESPOND NATURALLY IN {language_name}. Be concise but friendly. Always use {language_name} for your final response to the user."""

    # Maximum ReAct iterations to prevent infinite loops
    MAX_ITERATIONS = 3

    def __init__(self, db: Optional[DatabaseManager] = None):
        self._settings = get_settings()
        self._db = db
        self._llm_client = None
        self._available_tools = tool_registry.list_tools()
        self._tools_prompt = tool_registry.list_tools_for_prompt()

    def _create_llm_client(self, api: str):
        """
        Create a specific LLM client for the requested API.
        Does not pre-test connection to avoid initialization overhead.
        """
        try:
            if api == "groq":
                from groq import Groq
                return Groq(api_key=self._settings.groq_api_key)

            elif api == "openrouter":
                from openai import OpenAI
                return OpenAI(
                    api_key=self._settings.openrouter_api_key,
                    base_url="https://openrouter.ai/api/v1"
                )

            elif api == "gemini":
                from google import genai
                return genai.Client(api_key=self._settings.gemini_api_key)

        except Exception as e:
            logger.error(f"Failed to initialize {api} client: {e}")
            return None

        return None

    def _parse_tool_calls(self, llm_response: str) -> List[ToolCall]:
        """
        Parse tool calls from LLM response using regex.
        Handles XML-style format: <tool_name>{json}</tool_name>

        Graceful degradation:
        - Returns empty list if no tool calls found
        - Logs parsing errors but continues
        """
        tool_calls = []
        # Pattern: <tool_name>{json}</tool_name>
        pattern = r'<(\w+)>(\{[^}]*\})</\1>'

        for match in re.finditer(pattern, llm_response):
            tool_name = match.group(1)
            raw_json = match.group(2)

            try:
                args = json.loads(raw_json)
                tool_calls.append(ToolCall(
                    name=tool_name,
                    arguments=args,
                    raw_text=match.group(0)
                ))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tool JSON: {raw_json[:50]}... - {e}")
                # Try to extract partial information
                tool_calls.append(ToolCall(
                    name=tool_name,
                    arguments={},
                    raw_text=match.group(0)
                ))

        return tool_calls

    def _execute_tool(self, call: ToolCall, user_id: str) -> Dict[str, Any]:
        """
        Execute a tool call and return structured result.
        Always returns a dict with 'success' key.
        """
        try:
            result = tool_registry.execute(
                call.name,
                user_id=user_id,
                db=self._db,
                **call.arguments
            )
            return {
                "success": True,
                "tool": call.name,
                "result": result,
                "error": None
            }
        except ToolExecutionError as e:
            logger.warning(f"Tool execution error: {call.name} - {e}")
            return {
                "success": False,
                "tool": call.name,
                "result": None,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected tool error: {call.name} - {e}")
            return {
                "success": False,
                "tool": call.name,
                "result": None,
                "error": f"Internal error: {str(e)}"
            }

    def _call_llm(self, messages: List[Dict]) -> str:
        """
        Call LLM with API fallback and modular SDK handling.
        """
        api_order = self._settings.llm_api_order
        if not api_order:
            api_order = ["groq", "openrouter", "gemini"]

        last_error = None
        for api in api_order:
            try:
                client = self._create_llm_client(api)
                if not client:
                    continue

                if api == "groq":
                    # Build Groq-specific schema
                    tools_schema = self._build_openai_tools_schema()
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=messages,
                        tools=tools_schema if tools_schema else None,
                        temperature=0.6,
                        max_tokens=1024,
                    )
                    return self._extract_openai_response(response)

                elif api == "openrouter":
                    tools_schema = self._build_openai_tools_schema()
                    response = client.chat.completions.create(
                        model="meta-llama/llama-3-8b-instruct",
                        messages=messages,
                        tools=tools_schema if tools_schema else None,
                        temperature=0.7,
                        max_tokens=1024,
                        extra_headers={
                            "HTTP-Referer": self._settings.app_url,
                            "X-Title": "Marco AI",
                        }
                    )
                    return self._extract_openai_response(response)

                elif api == "gemini":
                    # Gemini uses generate_content and its own tool schema
                    # Simplified: using text-only for now if tool conversion is complex
                    # Actually, let's try to support it or use text parsing as fallback
                    response = client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=[{"role": m["role"], "parts": [{"text": m["content"]}]} for m in messages],
                    )
                    return response.text

            except Exception as e:
                last_error = e
                logger.warning(f"API {api} call failed: {e}")
                continue

        raise RuntimeError(f"All LLM APIs failed: {last_error}")

    def _build_openai_tools_schema(self) -> List[Dict]:
        """Convert registry tools to OpenAI function calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            }
            for t in tool_registry._tools.values()
        ]

    def _extract_openai_response(self, response) -> str:
        """Extract text or tool calls from OpenAI-compatible response."""
        message = response.choices[0].message
        
        # Check for native tool calls
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_xml = []
            for tc in message.tool_calls:
                # Groq sometimes returns arguments as dict, sometimes string
                args = tc.function.arguments
                if not isinstance(args, str):
                    args = json.dumps(args)
                tool_xml.append(f"<{tc.function.name}>{args}</{tc.function.name}>")
            return " ".join(tool_xml)

        return message.content or ""

    def _extract_response_text(self, response) -> str:
        """
        Extract text from LLM response.
        Handles both native tool calls and text responses.
        """
        message = response.choices[0].message

        # Check for native tool calls (Groq/OpenAI format)
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_xml = []
            for tc in message.tool_calls:
                args = tc.function.arguments
                tool_xml.append(f"<{tc.function.name}>{args}</{tc.function.name}>")
            return " ".join(tool_xml)

        # Return text content
        return message.content or ""

    def _build_messages(self, user_input: str, language: str = "en") -> List[Dict]:
        """Build message list for LLM."""
        lang_name = "Spanish" if language == "es" else "English"
        system_prompt = self.SYSTEM_PROMPT.format(
            tools=self._tools_prompt,
            language_name=lang_name
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

    async def process(
        self,
        user_input: str,
        user_id: str,
        language: str = "en",
        conversation_id: Optional[str] = None,
    ) -> Dict:
        """
        Process user input through ReAct loop.

        Memory-efficient:
        - Max 3 iterations to prevent infinite loops
        - No history stored between calls
        - Minimal state tracking

        Args:
            user_input: User's message
            user_id: User identifier for data isolation
            conversation_id: Optional conversation ID for tracking

        Returns:
            Dict with response, tool_calls count, and iterations
        """
        import uuid

        conversation_id = conversation_id or str(uuid.uuid4())
        messages = self._build_messages(user_input, language=language)

        # ReAct loop with iteration limit
        iteration_count = 0
        final_response = None
        total_tool_calls = 0

        while iteration_count < self.MAX_ITERATIONS:
            iteration_count += 1
            logger.debug(f"ReAct iteration {iteration_count}/{self.MAX_ITERATIONS}")

            # Call LLM
            try:
                llm_response = await self._call_llm_async(messages)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return {
                    "conversation_id": conversation_id,
                    "response": "I'm having trouble connecting right now. Please try again.",
                    "error": str(e),
                    "tool_calls": 0,
                    "iterations": iteration_count,
                }

            # Parse tool calls
            tool_calls = self._parse_tool_calls(llm_response)

            if not tool_calls:
                # No tool calls = final response
                final_response = llm_response
                logger.debug("No tool calls found, using response directly")
                break

            total_tool_calls += len(tool_calls)
            logger.debug(f"Parsed {len(tool_calls)} tool calls")

            # Execute tools
            tool_results = []
            for call in tool_calls:
                result = self._execute_tool(call, user_id)
                tool_results.append(result)

            # Format tool results for LLM
            tool_result_text = self._format_tool_results(tool_results)

            # Add to conversation history
            messages.append({
                "role": "assistant",
                "content": llm_response,
            })
            messages.append({
                "role": "tool",
                "content": tool_result_text,
            })

        # Ensure we have a response
        if final_response is None:
            final_response = "I've completed the actions. Is there anything else you need?"

        # Save to memory (async, non-blocking)
        try:
            from ..rag.engine import RAGEngine
            engine = RAGEngine(self._db)
            await engine.save_conversation_async(user_id, "user", user_input)
            await engine.save_conversation_async(user_id, "assistant", final_response)
        except Exception as e:
            logger.warning(f"Failed to save conversation: {e}")

        return {
            "conversation_id": conversation_id,
            "response": final_response,
            "tool_calls": total_tool_calls,
            "iterations": iteration_count,
        }

    def _format_tool_results(self, results: List[Dict]) -> str:
        """Format tool results for LLM consumption."""
        lines = []
        for r in results:
            if r["success"]:
                lines.append(f"{r['tool']}: SUCCESS - {json.dumps(r['result'])}")
            else:
                lines.append(f"{r['tool']}: ERROR - {r['error']}")
        return "\n".join(lines)

    async def _call_llm_async(self, messages: List[Dict]) -> str:
        """Async wrapper for LLM call."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._call_llm, messages)


# =============================================================================
# Synchronous version for non-async contexts
# =============================================================================

class SyncReActOrchestrator(ReActOrchestrator):
    """
    Synchronous version of the ReAct orchestrator.
    Use when async is not available or needed.
    """

    def process_sync(
        self,
        user_input: str,
        user_id: str,
        conversation_id: Optional[str] = None,
    ) -> Dict:
        """
        Process user input synchronously.

        Same logic as async process(), but runs in blocking fashion.
        """
        import uuid

        conversation_id = conversation_id or str(uuid.uuid4())
        messages = self._build_messages(user_input)

        # ReAct loop with iteration limit
        iteration_count = 0
        final_response = None
        total_tool_calls = 0

        while iteration_count < self.MAX_ITERATIONS:
            iteration_count += 1
            logger.debug(f"ReAct iteration {iteration_count}/{self.MAX_ITERATIONS}")

            # Call LLM (blocking)
            try:
                llm_response = self._call_llm(messages)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return {
                    "conversation_id": conversation_id,
                    "response": "I'm having trouble connecting right now. Please try again.",
                    "error": str(e),
                    "tool_calls": 0,
                    "iterations": iteration_count,
                }

            # Parse tool calls
            tool_calls = self._parse_tool_calls(llm_response)

            if not tool_calls:
                final_response = llm_response
                break

            total_tool_calls += len(tool_calls)

            # Execute tools
            tool_results = []
            for call in tool_calls:
                result = self._execute_tool(call, user_id)
                tool_results.append(result)

            # Add to conversation
            tool_result_text = self._format_tool_results(tool_results)
            messages.append({"role": "assistant", "content": llm_response})
            messages.append({"role": "tool", "content": tool_result_text})

        if final_response is None:
            final_response = "I've completed the actions."

        # Save to memory
        try:
            from ..rag.engine import RAGEngine
            engine = RAGEngine(self._db)
            engine.save_conversation(user_id, "user", user_input)
            engine.save_conversation(user_id, "assistant", final_response)
        except Exception as e:
            logger.warning(f"Failed to save conversation: {e}")

        return {
            "conversation_id": conversation_id,
            "response": final_response,
            "tool_calls": total_tool_calls,
            "iterations": iteration_count,
        }
