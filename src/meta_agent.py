"""
"A girl is Arya Stark of Winterfell. And I'm going home."
But first, the Faceless Men must be born.

Meta-Agent: Runs ONCE at bootstrap to create the agent's identity.
  Step 1 — Select MCPs
  Step 2 — Generate constitution + initial skills
  Step 3 — Persist everything to disk + SQLite
"""

from __future__ import annotations

import json
import os
from typing import Annotated, TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from src.config import (
    AGENT_CONFIG_PATH,
    AGENT_DIR,
    CONSTITUTION_PATH,
    DB_PATH,
    DEFAULT_INITIAL_SKILLS_COUNT,
    LLM_MODEL,
    LLM_TEMPERATURE,
    SKILLS_DIR,
)
from src.prompts.meta_agent_prompts import BOOTSTRAP_TEMPLATE, MCP_SELECTION_TEMPLATE
from src.skill_engine.store import SkillStore
from src.skill_engine.types import (
    BootstrapResult,
    MCPDefinition,
    MCPSelectionResult,
    SkillRecord,
)


# ── State ────────────────────────────────────────────

class MetaAgentState(TypedDict):
    user_description: str
    available_mcps: list[dict]
    selected_mcps: list[str]
    mcp_reasoning: str
    constitution: str
    skills: list[dict]
    agent_name: str
    error: str | None


# ── Nodes ────────────────────────────────────────────

def select_mcps(state: MetaAgentState) -> dict:
    """Step 1: LLM selects which MCPs the agent needs."""
    llm = init_chat_model(LLM_MODEL, temperature=LLM_TEMPERATURE)
    structured_llm = llm.with_structured_output(MCPSelectionResult)

    mcp_list_str = "\n".join(
        f"- **{m['name']}**: {m['description']}" for m in state["available_mcps"]
    )

    prompt = MCP_SELECTION_TEMPLATE.format(
        user_description=state["user_description"],
        mcp_list=mcp_list_str,
    )

    result: MCPSelectionResult = structured_llm.invoke(
        [HumanMessage(content=prompt)]
    )

    # Derive agent name from description (first few words, slugified)
    words = state["user_description"].lower().split()[:4]
    agent_name = "-".join(w for w in words if w.isalnum())[:30] or "faceless-agent"

    return {
        "selected_mcps": result.selected_mcps,
        "mcp_reasoning": result.reasoning,
        "agent_name": agent_name,
    }


def generate_bootstrap(state: MetaAgentState) -> dict:
    """Step 2: LLM generates constitution + initial skills."""
    llm = init_chat_model(LLM_MODEL, temperature=LLM_TEMPERATURE)
    structured_llm = llm.with_structured_output(BootstrapResult)

    # Build MCP descriptions for selected only
    available = {m["name"]: m["description"] for m in state["available_mcps"]}
    selected_descriptions = "\n".join(
        f"- **{name}**: {available.get(name, 'No description')}"
        for name in state["selected_mcps"]
    )

    prompt = BOOTSTRAP_TEMPLATE.format(
        user_description=state["user_description"],
        selected_mcps_with_descriptions=selected_descriptions,
        num_skills=DEFAULT_INITIAL_SKILLS_COUNT,
    )

    result: BootstrapResult = structured_llm.invoke(
        [HumanMessage(content=prompt)]
    )

    return {
        "constitution": result.constitution,
        "skills": [s.model_dump() for s in result.skills],
    }


def persist_artifacts(state: MetaAgentState) -> dict:
    """Step 3: Write everything to disk and SQLite."""
    # Ensure directories
    os.makedirs(os.path.dirname(AGENT_CONFIG_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(SKILLS_DIR, exist_ok=True)

    # Write agent_config.json
    config = {
        "agent_name": state["agent_name"],
        "selected_mcps": state["selected_mcps"],
        "mcp_reasoning": state["mcp_reasoning"],
        "created_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }
    with open(AGENT_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    # Write constitution.md
    with open(CONSTITUTION_PATH, "w") as f:
        f.write(state["constitution"])

    # Initialize store and write skills
    store = SkillStore(DB_PATH)

    for skill_data in state["skills"]:
        skill_name = skill_data["name"]
        skill_id = store.make_skill_id(skill_name, generation=0)

        # Extract description from SKILL.md frontmatter (best effort)
        content = skill_data["content"]
        description = _extract_description(content)

        record = SkillRecord(
            id=skill_id,
            name=skill_name,
            description=description,
            category=skill_data.get("category", "workflow"),
            content=content,
            status="active",
            generation=0,
            lineage_origin="BOOTSTRAP",
        )
        store.insert_skill(record)
        store.insert_audit(skill_id, "bootstrap", reviewer="meta-agent")

        # Write skill directory
        skill_dir = os.path.join(SKILLS_DIR, skill_name)
        os.makedirs(skill_dir, exist_ok=True)

        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write(content)

        with open(os.path.join(skill_dir, ".skill_id"), "w") as f:
            f.write(skill_id)

        # Write scripts
        for script in skill_data.get("scripts", []):
            script_path = os.path.join(skill_dir, script["filename"])
            os.makedirs(os.path.dirname(script_path), exist_ok=True)
            with open(script_path, "w") as f:
                f.write(script["content"])

        # Write references
        for ref in skill_data.get("references", []):
            ref_path = os.path.join(skill_dir, ref["filename"])
            os.makedirs(os.path.dirname(ref_path), exist_ok=True)
            with open(ref_path, "w") as f:
                f.write(ref["content"])

    store.close()
    return {}


def _extract_description(content: str) -> str:
    """Best-effort extraction of description from SKILL.md frontmatter."""
    lines = content.split("\n")
    in_frontmatter = False
    desc_lines = []
    capturing = False

    for line in lines:
        if line.strip() == "---":
            if in_frontmatter:
                break
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line.startswith("description:"):
                text = line.split("description:", 1)[1].strip()
                if text and text != ">":
                    desc_lines.append(text)
                capturing = True
            elif capturing and line.startswith("  "):
                desc_lines.append(line.strip())
            elif capturing:
                break

    return " ".join(desc_lines) if desc_lines else ""


# ── Graph ────────────────────────────────────────────

def build_meta_agent_graph() -> StateGraph:
    """
    The ritual of becoming No One:
      select_mcps → generate_bootstrap → persist_artifacts
    """
    graph = StateGraph(MetaAgentState)

    graph.add_node("select_mcps", select_mcps)
    graph.add_node("generate_bootstrap", generate_bootstrap)
    graph.add_node("persist_artifacts", persist_artifacts)

    graph.add_edge(START, "select_mcps")
    graph.add_edge("select_mcps", "generate_bootstrap")
    graph.add_edge("generate_bootstrap", "persist_artifacts")
    graph.add_edge("persist_artifacts", END)

    return graph


def create_meta_agent():
    """Compile and return the meta-agent graph."""
    graph = build_meta_agent_graph()
    return graph.compile()


# ── Public API ───────────────────────────────────────

def bootstrap_agent(
    user_description: str,
    available_mcps: list[dict],
) -> dict:
    """
    Run the full bootstrap ritual.

    Args:
        user_description: What the agent should do.
        available_mcps: List of {"name": ..., "description": ...} MCPs.

    Returns:
        Final state dict with all bootstrap results.
    """
    agent = create_meta_agent()
    result = agent.invoke({
        "user_description": user_description,
        "available_mcps": available_mcps,
        "selected_mcps": [],
        "mcp_reasoning": "",
        "constitution": "",
        "skills": [],
        "agent_name": "",
        "error": None,
    })
    return result
