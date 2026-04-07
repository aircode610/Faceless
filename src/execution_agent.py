"""
"Valar Morghulis." — All men must serve.
The execution agent: performs the actual task using its tools and skills.
It knows nothing about evolution, approval, or the skill engine.
It simply does its job, wearing the face it was given.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Annotated, Any, TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, START, MessagesState, StateGraph

from src.config import LLM_MODEL, LLM_TEMPERATURE, MAX_EXECUTION_ITERATIONS


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


def build_execution_agent(tools: list | None = None):
    """
    Build a LangGraph execution agent.

    The agent runs an LLM loop with optional tools, terminating when:
      - The LLM outputs content containing <COMPLETE>
      - Max iterations reached
      - No tool calls and no completion signal (natural end)
    """
    tools = tools or []
    tools_by_name = {t.name: t for t in tools}

    llm = init_chat_model(LLM_MODEL, temperature=LLM_TEMPERATURE)
    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm

    def call_llm(state: ExecutionState) -> dict:
        """LLM decides what to do next."""
        iteration = state.get("iteration", 0) + 1
        system = SystemMessage(content=state["system_prompt"])

        response = llm_with_tools.invoke([system] + state["messages"])

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

    def call_tools(state: ExecutionState) -> dict:
        """Execute tool calls from the last LLM message."""
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
                tool = tools_by_name[tool_name]
                observation = tool.invoke(tool_call["args"])
                content = str(observation)
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

    Returns dict with: messages, conversation_log, tool_trace, tools_used,
                       iteration, task_complete
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

    final_state = agent.invoke(initial_state)
    return final_state
