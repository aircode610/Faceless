"""
The House of Black and White keeps its ledgers precise.
All thresholds and constants live here.
"""

# ── LLM ──────────────────────────────────────────────
LLM_MODEL = "claude-sonnet-4-20250514"
LLM_TEMPERATURE = 0

# ── Evolution engine ─────────────────────────────────
EVOLUTION_MAX_ITERATIONS = 5
EVOLUTION_MAX_APPLY_ATTEMPTS = 3
EVOLUTION_MAX_CONCURRENT = 3

# ── Trigger 1 — analysis ────────────────────────────
ANALYSIS_MAX_ITERATIONS = 5
MAX_CONVERSATION_CHARS = 80_000
MAX_TOOL_ERROR_CHARS = 1_000
MAX_TOOL_RESULT_CHARS = 800
MAX_TOOL_ARGS_CHARS = 500
MAX_TRAJ_SUMMARY_CHARS = 1_500
MAX_SKILL_CONTENT_CHARS = 8_000

# ── Trigger 2 — tool degradation ────────────────────
TOOL_DEGRADED_RATE = 0.5
TOOL_MIN_CALLS = 5
TOOL_ROLLING_WINDOW = 100

# ── Trigger 3 — health check ────────────────────────
METRIC_CHECK_EVERY_N_EXECUTIONS = 5
METRIC_MIN_SELECTIONS_TO_EVALUATE = 5
FALLBACK_THRESHOLD = 0.40
HIGH_APPLIED_FOR_FIX = 0.40
LOW_COMPLETION_THRESHOLD = 0.35
MODERATE_EFFECTIVE_THRESHOLD = 0.55
MIN_APPLIED_FOR_DERIVED = 0.25

# ── Skill selection ──────────────────────────────────
MAX_SKILLS_PER_TASK = 3
QUALITY_FILTER_MIN_SELECTIONS = 2

# ── Recurrence ───────────────────────────────────────
RECURRENCE_PROMOTION_THRESHOLD = 3
RECURRENCE_MIN_DISTINCT_RUNS = 2

# ── Feature requests ────────────────────────────────
FEATURE_REQUEST_AUTO_ACCEPT = False

# ── Benchmark ────────────────────────────────────────
BENCHMARK_PASS_THRESHOLD = 0.80

# ── Execution ────────────────────────────────────────
MAX_EXECUTION_ITERATIONS = 15

# ── Bootstrap ────────────────────────────────────────
DEFAULT_INITIAL_SKILLS_COUNT = 5

# ── Paths ────────────────────────────────────────────
AGENT_DIR = "agent"
DB_PATH = "agent/db/agent.db"
RECORDINGS_DIR = "recordings"
SKILLS_DIR = "agent/skills"
CONSTITUTION_PATH = "agent/constitution.md"
AGENT_CONFIG_PATH = "agent/agent_config.json"
