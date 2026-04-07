"""
Memory-efficient Single-Agent ReAct Orchestrator.
Uses LLM Tool Calling pattern with graceful API fallback.
Optimized for Raspberry Pi 3 (1GB RAM).
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
    raw_text: str = ""


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
    """

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

    MAX_ITERATIONS = 3

    def __init__(self, db: Optional[DatabaseManager] = None):
        self._settings = get_settings()
        self._db = db
        self._llm_client = None
        self._available_tools = tool_registry.list_tools()
        self._tools_prompt = tool_registry.list_tools_for_prompt()

    def _create_llm_client(self, api: str):
        try:
            if api == "groq":
                from groq import Groq
                return Groq(api_key=self._settings.groq_api_key)
            elif api == "openrouter":
                from openai import OpenAI
                return OpenAI(api_key=self._settings.openrouter_api_key, base_url="https://openrouter.ai/api/v1")
            elif api == "gemini":
                import google.generativeai as genai
                genai.configure(api_key=self._settings.gemini_api_key)
                return genai
        except Exception as e:
            logger.error(f"Failed to initialize {api} client: {e}")
            return None
        return None

    def _parse_tool_calls(self, llm_response: str) -> List[ToolCall]:
        tool_calls = []
        pattern = r'<(\w+)>(\{[^}]*\})</\1>'
        for match in re.finditer(pattern, llm_response):
            tool_name = match.group(1)
            raw_json = match.group(2)
            try:
                args = json.loads(raw_json)
                tool_calls.append(ToolCall(name=tool_name, arguments=args, raw_text=match.group(0)))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tool JSON: {raw_json[:50]}... - {e}")
                tool_calls.append(ToolCall(name=tool_name, arguments={}, raw_text=match.group(0)))
        return tool_calls

    def _execute_tool(self, call: ToolCall, user_id: str) -> Dict[str, Any]:
        try:
            result = tool_registry.execute(call.name, user_id=user_id, db=self._db, **call.arguments)
            return {"success": True, "tool": call.name, "result": result, "error": None}
        except ToolExecutionError as e:
            logger.warning(f"Tool execution error: {call.name} - {e}")
            return {"success": False, "tool": call.name, "result": None, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected tool error: {call.name} - {e}")
            return {"success": False, "tool": call.name, "result": None, "error": f"Internal error: {str(e)}"}

    def _call_llm(self, messages: List[Dict]) -> str:
        api_order = self._settings.llm_api_order
        if not api_order: api_order = ["groq", "openrouter", "gemini"]

        error_log = []
        for api in api_order:
            try:
                client = self._create_llm_client(api)
                if not client: 
                    error_log.append(f"{api}: Client initialization failed")
                    continue

                if api == "groq":
                    # Try models stable for v0.4.x SDK
                    for model in ["llama-3.3-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768"]:
                        try:
                            tools_schema = self._build_openai_tools_schema()
                            response = client.chat.completions.create(
                                model=model, messages=messages, tools=tools_schema if tools_schema else None,
                                temperature=0.6, max_tokens=1024,
                            )
                            return self._extract_openai_response(response)
                        except Exception as e:
                            logger.warning(f"Groq model {model} failed: {e}")
                            error_log.append(f"Groq ({model}): {str(e)}")
                            continue

                elif api == "openrouter":
                    tools_schema = self._build_openai_tools_schema()
                    try:
                        response = client.chat.completions.create(
                            model="meta-llama/llama-3-8b-instruct:free", messages=messages,
                            tools=tools_schema if tools_schema else None,
                            temperature=0.7, max_tokens=1024,
                            extra_headers={"HTTP-Referer": self._settings.app_url, "X-Title": "Marco AI"}
                        )
                        return self._extract_openai_response(response)
                    except Exception as e:
                        error_log.append(f"OpenRouter: {str(e)}")

                elif api == "gemini":
                    try:
                        # Use legacy gemini-pro for v0.3.x compatibility
                        model = client.GenerativeModel('gemini-3.1-flash-lite-preview')
                        response = model.generate_content(messages[-1]["content"])
                        return response.text
                    except Exception as e:
                        error_log.append(f"Gemini (pro): {str(e)}")

            except Exception as e:
                error_log.append(f"{api} (fatal): {str(e)}")
                continue

        # Show ALL errors if all providers fail
        raise RuntimeError(" | ".join(error_log))

    def _build_openai_tools_schema(self) -> List[Dict]:
        return [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}} for t in tool_registry._tools.values()]

    def _extract_openai_response(self, response) -> str:
        message = response.choices[0].message
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_xml = []
            for tc in message.tool_calls:
                args = tc.function.arguments
                if not isinstance(args, str): args = json.dumps(args)
                tool_xml.append(f"<{tc.function.name}>{args}</{tc.function.name}>")
            return " ".join(tool_xml)
        return message.content or ""

    def _build_messages(self, user_input: str, language: str = "en") -> List[Dict]:
        lang_name = "Spanish" if language == "es" else "English"
        system_prompt = self.SYSTEM_PROMPT.format(tools=self._tools_prompt, language_name=lang_name)
        return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}]

    async def process(self, user_input: str, user_id: str, language: str = "en", conversation_id: Optional[str] = None) -> Dict:
        import uuid
        conversation_id = conversation_id or str(uuid.uuid4())
        messages = self._build_messages(user_input, language=language)
        iteration_count = 0
        final_response = None
        total_tool_calls = 0

        while iteration_count < self.MAX_ITERATIONS:
            iteration_count += 1
            try:
                llm_response = await self._call_llm_async(messages)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                err_str = str(e) or "Unknown Error"
                return {"conversation_id": conversation_id, "response": f"I'm having trouble connecting right now. [{err_str}]", "error": err_str, "tool_calls": 0, "iterations": iteration_count}

            tool_calls = self._parse_tool_calls(llm_response)
            if not tool_calls:
                final_response = llm_response
                break

            total_tool_calls += len(tool_calls)
            tool_results = [self._execute_tool(call, user_id) for call in tool_calls]
            tool_result_text = "\n".join([f"{r['tool']}: SUCCESS - {json.dumps(r['result'])}" if r["success"] else f"{r['tool']}: ERROR - {r['error']}" for r in tool_results])
            messages.append({"role": "assistant", "content": llm_response})
            messages.append({"role": "tool", "content": tool_result_text})

        if final_response is None: final_response = "I've completed the actions."
        return {"conversation_id": conversation_id, "response": final_response, "tool_calls": total_tool_calls, "iterations": iteration_count}

    async def _call_llm_async(self, messages: List[Dict]) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._call_llm, messages)
