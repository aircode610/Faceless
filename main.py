"""
"Valar Dohaeris." — All men must serve.

Faceless — Self-Improving Skill-Based Agent Framework
Main entry point with LangSmith tracing.

Usage:
  # Bootstrap a new agent
  python main.py bootstrap --description "Review GitHub PRs for security issues"

  # Run a task
  python main.py run --task "Review PR #42 for SQL injection vulnerabilities"
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# ── LangSmith tracing setup ─────────────────────────
# Load .env before anything else
from dotenv import load_dotenv
load_dotenv()

# Ensure tracing env vars are set
os.environ["LANGSMITH_TRACING"] = os.environ.get("LANGSMITH_TRACING", "true")
os.environ["LANGSMITH_PROJECT"] = os.environ.get("LANGSMITH_PROJECT", "faceless")

from src.meta_agent import bootstrap_agent
from src.orchestrator import run_task


# ── Default MCP catalog (for demo) ──────────────────

DEFAULT_MCPS = [
    {"name": "github", "description": "Read/write GitHub repos, PRs, issues, reviews"},
    {"name": "trello", "description": "Read/write Trello boards and cards"},
    {"name": "search", "description": "Web search via Tavily"},
    {"name": "sqlite", "description": "Query local SQLite databases"},
    {"name": "slack", "description": "Post messages to Slack channels"},
    {"name": "filesystem", "description": "Read/write local files and directories"},
    {"name": "terminal", "description": "Execute shell commands"},
]

FACELESS_BANNER = r"""
    ⚔️  FACELESS — A Man Has No Name  ⚔️
    ╔══════════════════════════════════════╗
    ║  Self-Improving Skill-Based Agent    ║
    ║  "Valar Morghulis"                   ║
    ╚══════════════════════════════════════╝
"""


def cmd_bootstrap(args):
    """Bootstrap a new Faceless agent."""
    print(FACELESS_BANNER)
    print("🏛️  The House of Black and White opens its doors...\n")

    description = args.description
    mcps = DEFAULT_MCPS

    if args.mcps:
        with open(args.mcps) as f:
            mcps = json.load(f)

    print(f"📜 Agent description: {description}")
    print(f"🔧 Available MCPs: {[m['name'] for m in mcps]}")
    print("\n⏳ The ritual begins... (this may take a moment)\n")

    result = bootstrap_agent(
        user_description=description,
        available_mcps=mcps,
    )

    print("✅ Bootstrap complete!\n")
    print(f"  🎭 Agent name: {result.get('agent_name', 'unknown')}")
    print(f"  🔧 Selected MCPs: {result.get('selected_mcps', [])}")
    print(f"  📜 Constitution: agent/constitution.md")
    print(f"  🗡️  Skills created: {len(result.get('skills', []))}")
    print(f"  💾 Config: agent/agent_config.json")
    print(f"  🗄️  Database: agent/db/agent.db")

    for skill in result.get("skills", []):
        print(f"    → {skill['name']} ({skill.get('category', '?')})")

    print("\n🏛️  A new servant of the Many-Faced God is born.")
    print("   Run tasks with: python main.py run --task 'your task here'")


def cmd_run(args):
    """Run a task through the orchestrator."""
    print(FACELESS_BANNER)

    if not os.path.exists("agent/agent_config.json"):
        print("❌ No agent found. Run bootstrap first:")
        print("   python main.py bootstrap --description 'your agent description'")
        sys.exit(1)

    task = args.task
    print(f"🎭 A man receives a task: {task}\n")
    print("⏳ The face is chosen, the skills are gathered...\n")

    result = run_task(task_description=task)

    run_id = result.get("run_id", "unknown")
    analysis = result.get("analysis_result")

    print(f"\n✅ Task complete. Run ID: {run_id}")
    print(f"  📁 Recording: recordings/{run_id}/")

    if analysis:
        completed = analysis.get("task_completed", False)
        note = analysis.get("execution_note", "")
        evolutions = analysis.get("evolution_suggestions", [])
        features = analysis.get("feature_requests", [])

        status_icon = "✅" if completed else "⚠️"
        print(f"  {status_icon} Task completed: {completed}")
        print(f"  📝 {note}")

        if evolutions:
            print(f"\n  🔄 Evolution suggestions ({len(evolutions)}):")
            for evo in evolutions:
                print(f"    → [{evo.get('priority', '?')}] {evo.get('type', '?')}: {evo.get('direction', '')[:80]}")

        if features:
            print(f"\n  💡 Feature requests ({len(features)}):")
            for feat in features:
                print(f"    → {feat.get('capability', '')[:80]}")

    # Evolution results
    evo_results = result.get("evolution_results", [])
    if evo_results:
        succeeded = [e for e in evo_results if e.get("succeeded")]
        failed = [e for e in evo_results if not e.get("succeeded")]
        print(f"\n  🧬 Evolution engine ran ({len(evo_results)} suggestions):")
        for e in succeeded:
            print(f"    ✅ {e['type'].upper()}: {e.get('change_summary', '')[:70]}")
            print(f"       → pending approval: {e.get('resulting_skill_id', '')}")
        for e in failed:
            print(f"    ❌ {e['type'].upper()}: {e.get('error_reason', 'unknown')[:70]}")
        if succeeded:
            print(f"\n  🏛️  {len(succeeded)} evolution(s) await review at /review")

    print("\n🏛️  Valar Dohaeris — the service is rendered.")


def cmd_status(args):
    """Show current agent status."""
    print(FACELESS_BANNER)

    if not os.path.exists("agent/agent_config.json"):
        print("❌ No agent bootstrapped yet.")
        return

    with open("agent/agent_config.json") as f:
        config = json.load(f)

    print(f"🎭 Agent: {config.get('agent_name', 'unknown')}")
    print(f"🔧 MCPs: {config.get('selected_mcps', [])}")
    print(f"📅 Created: {config.get('created_at', '?')}")

    # Count skills
    from src.skill_engine.store import SkillStore
    store = SkillStore("agent/db/agent.db")
    skills = store.get_active_skills()
    run_count = store.get_run_count()
    store.close()

    print(f"🗡️  Active skills: {len(skills)}")
    for s in skills:
        rate = s.total_completions / max(s.total_applied, 1)
        print(f"   → {s.name} (selected {s.total_selections}x, {rate:.0%} success)")

    print(f"📊 Total runs: {run_count}")


def main():
    parser = argparse.ArgumentParser(
        description="Faceless — Self-Improving Skill-Based Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='  "Valar Morghulis" — All men must die.\n  "Valar Dohaeris" — All men must serve.',
    )
    subparsers = parser.add_subparsers(dest="command")

    # bootstrap
    bp = subparsers.add_parser("bootstrap", help="Bootstrap a new agent")
    bp.add_argument("--description", "-d", required=True, help="Agent description")
    bp.add_argument("--mcps", "-m", help="Path to MCPs JSON file (optional)")

    # run
    rp = subparsers.add_parser("run", help="Run a task")
    rp.add_argument("--task", "-t", required=True, help="Task description")

    # status
    subparsers.add_parser("status", help="Show agent status")

    args = parser.parse_args()

    if args.command == "bootstrap":
        cmd_bootstrap(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
