"""
"Valar Morghulis." — All men must serve.
The execution agent: performs the actual task using its tools and skills.
It knows nothing about evolution, approval, or the skill engine.
It simply does its job, wearing the face it was given.

Nodes are async so that MCP-backed tools (which are async-only via
langchain-mcp-adapters) can be awaited directly.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, START, MessagesState, StateGraph

from src.config import MAX_EXECUTION_ITERATIONS
from src.llm import get_llm


class ExecutionState(MessagesState):
    """State for the execution agent graph."""
    system_prompt: str
    iteration: int
    max_iterations: int
    task_complete: bool
    # Recording buffers
    conversation_log: list[dict]
    tool_trace: list[dict]
    tools_used: set


def _safe_str(value: Any, limit: int = 4000) -> str:
    try:
        s = str(value)
    except Exception:
        s = repr(value)
    if len(s) > limit:
        return s[:limit] + f"\n... [truncated, full length {len(s)}]"
    return s


def build_execution_agent(tools: list | None = None):
    """
    Build a LangGraph execution agent.

    The agent runs an async LLM loop with optional tools, terminating when:
      - The LLM outputs content containing <COMPLETE>
      - Max iterations reached
      - No tool calls and no completion signal (natural end)
    """
    tools = tools or []
    tools_by_name = {t.name: t for t in tools}

    llm = get_llm()
    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm

    async def call_llm(state: ExecutionState) -> dict:
        """LLM decides what to do next."""
        iteration = state.get("iteration", 0) + 1
        system = SystemMessage(content=state["system_prompt"])

        response = await llm_with_tools.ainvoke([system] + state["messages"])

        # Record conversation
        conv_log = list(state.get("conversation_log", []))
        conv_log.append({
            "role": "assistant",
            "content": response.content if isinstance(response.content, str) else str(response.content),
            "iter": iteration,
        })

        # Check for completion signal
        task_complete = False
        if isinstance(response.content, str) and "<COMPLETE>" in response.content:
            task_complete = True

        return {
            "messages": [response],
            "iteration": iteration,
            "task_complete": task_complete,
            "conversation_log": conv_log,
        }

    async def call_tools(state: ExecutionState) -> dict:
        """Execute tool calls from the last LLM message.

        Uses `ainvoke` so it works for both sync tools and async-only tools
        (e.g. those produced by langchain-mcp-adapters).
        """
        last_message = state["messages"][-1]
        results = []
        tool_trace = list(state.get("tool_trace", []))
        tools_used = set(state.get("tools_used", set()))
        conv_log = list(state.get("conversation_log", []))
        iteration = state.get("iteration", 0)

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tools_used.add(tool_name)
            start = time.time()
            success = True
            error_msg = None

            try:
                tool = tools_by_name.get(tool_name)
                if tool is None:
                    raise RuntimeError(f"Unknown tool: {tool_name}")
                observation = await tool.ainvoke(tool_call["args"])
                content = _safe_str(observation)
            except Exception as e:
                content = f"Error: {e}"
                success = False
                error_msg = str(e)

            duration_ms = int((time.time() - start) * 1000)
            results.append(
                ToolMessage(content=content, tool_call_id=tool_call["id"])
            )

            # Record
            tool_trace.append({
                "iter": iteration,
                "tool": tool_name,
                "args": tool_call["args"],
                "success": success,
                "duration_ms": duration_ms,
                "error_message": error_msg,
            })
            conv_log.append({
                "role": "tool_call",
                "name": tool_name,
                "args": tool_call["args"],
                "iter": iteration,
            })
            conv_log.append({
                "role": "tool_result",
                "name": tool_name,
                "content": content[:500],
                "success": success,
                "iter": iteration,
            })

        return {
            "messages": results,
            "tool_trace": tool_trace,
            "tools_used": tools_used,
            "conversation_log": conv_log,
        }

    def should_continue(state: ExecutionState) -> str:
        """Decide: continue with tools, or end."""
        if state.get("task_complete", False):
            return END

        if state.get("iteration", 0) >= state.get("max_iterations", MAX_EXECUTION_ITERATIONS):
            return END

        last = state["messages"][-1] if state["messages"] else None
        if last and hasattr(last, "tool_calls") and last.tool_calls:
            return "call_tools"

        return END

    # Build graph
    graph = StateGraph(ExecutionState)
    graph.add_node("call_llm", call_llm)
    graph.add_node("call_tools", call_tools)

    graph.add_edge(START, "call_llm")
    graph.add_conditional_edges("call_llm", should_continue, ["call_tools", END])
    graph.add_edge("call_tools", "call_llm")

    return graph.compile()


def run_execution_agent(
    task_description: str,
    system_prompt: str,
    tools: list | None = None,
    max_iterations: int = MAX_EXECUTION_ITERATIONS,
) -> dict:
    """
    Run the execution agent and return its final state.

    The agent's nodes are async, so we dispatch via `ainvoke` wrapped in a
    fresh asyncio event loop. Callers don't need to care about async/sync.
    """
    agent = build_execution_agent(tools=tools)

    initial_state = {
        "messages": [HumanMessage(content=task_description)],
        "system_prompt": system_prompt,
        "iteration": 0,
        "max_iterations": max_iterations,
        "task_complete": False,
        "conversation_log": [
            {"role": "user", "content": task_description, "iter": 0}
        ],
        "tool_trace": [],
        "tools_used": set(),
    }

    try:
        final_state = asyncio.run(agent.ainvoke(initial_state))
    except RuntimeError:
        # Already inside an event loop — run in a dedicated thread.
        import threading
        result: dict = {}

        def _runner():
            nonlocal result
            result = asyncio.run(agent.ainvoke(initial_state))

        t = threading.Thread(target=_runner)
        t.start()
        t.join()
        final_state = result

    return final_state
