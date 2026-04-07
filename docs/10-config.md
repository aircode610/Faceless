# Configuration & Thresholds

All tuneable parameters in one place. Create `/Users/amirali.iranmanesh/JB/OpenSpace/src/config.py` (or equivalent) and import from there.

---

## Evolution Engine

| Parameter                        | Default | Where Used                                             |
|----------------------------------|---------|--------------------------------------------------------|
| `EVOLUTION_MAX_ITERATIONS`       | 5       | Max inner loop iterations per evolution LLM call       |
| `EVOLUTION_MAX_APPLY_ATTEMPTS`   | 3       | Max patch apply + SKILL.md validate attempts           |
| `EVOLUTION_MAX_CONCURRENT`       | 3       | Max parallel evolution LLM calls (shared semaphore)    |

---

## Trigger 1 — Post-Execution Analysis

| Parameter                    | Default | Where Used                                |
|------------------------------|---------|-------------------------------------------|
| `ANALYSIS_MAX_ITERATIONS`    | 5       | Max analyzer LLM loop iterations          |
| `MAX_CONVERSATION_CHARS`     | 80,000  | Truncation limit for conversation log     |
| `MAX_TOOL_ERROR_CHARS`       | 1,000   | Truncation for tool error messages        |
| `MAX_TOOL_RESULT_CHARS`      | 800     | Truncation for tool success results       |
| `MAX_TOOL_ARGS_CHARS`        | 500     | Truncation for tool arguments             |
| `MAX_TRAJ_SUMMARY_CHARS`     | 1,500   | Truncation for tool timeline summary      |
| `MAX_SKILL_CONTENT_CHARS`    | 8,000   | Truncation per skill content              |

---

## Trigger 2 — Tool Degradation

| Parameter                    | Default | Where Used                                          |
|------------------------------|---------|-----------------------------------------------------|
| `TOOL_DEGRADED_RATE`         | 0.5     | `recent_success_rate` threshold below which a tool is "problematic" |
| `TOOL_MIN_CALLS`             | 5       | Minimum tool calls before degradation check applies |
| `TOOL_ROLLING_WINDOW`        | 100     | Last N tool calls used for success rate calculation |

---

## Trigger 3 — Skill Health Check

| Parameter                           | Default | Where Used                                          |
|-------------------------------------|---------|-----------------------------------------------------|
| `METRIC_CHECK_EVERY_N_EXECUTIONS`   | 5       | Trigger 3 cadence (runs every N task executions)    |
| `METRIC_MIN_SELECTIONS_TO_EVALUATE` | 5       | Minimum selections before health check evaluates a skill |
| `FALLBACK_THRESHOLD`                | 0.40    | `fallback_rate` above this → FIX candidate          |
| `HIGH_APPLIED_FOR_FIX`              | 0.40    | `applied_rate` threshold for FIX combined condition |
| `LOW_COMPLETION_THRESHOLD`          | 0.35    | `completion_rate` below this → FIX candidate (when applied_rate > HIGH_APPLIED_FOR_FIX) |
| `MODERATE_EFFECTIVE_THRESHOLD`      | 0.55    | `effective_rate` below this → DERIVED candidate     |
| `MIN_APPLIED_FOR_DERIVED`           | 0.25    | Minimum `applied_rate` before DERIVED is considered |

---

## Skill Selection

| Parameter                        | Default | Where Used                                          |
|----------------------------------|---------|-----------------------------------------------------|
| `MAX_SKILLS_PER_TASK`            | 3       | Max skills selected per task execution              |
| `QUALITY_FILTER_MIN_SELECTIONS`  | 2       | Min selections before quality filter activates      |

Quality filter rules (applied before LLM selection):
- Exclude if `total_selections >= QUALITY_FILTER_MIN_SELECTIONS` and `total_completions == 0`
- Exclude if `total_applied >= QUALITY_FILTER_MIN_SELECTIONS` and `fallback_rate > 0.5`

---

## Recurrence Tracking

| Parameter                          | Default | Where Used                                              |
|------------------------------------|---------|----------------------------------------------------------|
| `RECURRENCE_PROMOTION_THRESHOLD`   | 3       | Pattern recurrences before priority auto-escalates       |
| `RECURRENCE_MIN_DISTINCT_RUNS`     | 2       | Min distinct runs required for escalation to trigger     |

Priority escalation ladder: `low → medium → high → critical`

---

## Feature Requests

| Parameter                     | Default | Where Used                                      |
|-------------------------------|---------|--------------------------------------------------|
| `FEATURE_REQUEST_AUTO_ACCEPT` | false   | If true, accepted FEATs skip reviewer queue     |

Keep this `false` for all prototype and production deployments. Auto-accepting bypasses the human review step entirely.

---

## Benchmark Regression Guard

| Parameter                    | Default | Where Used                                           |
|------------------------------|---------|------------------------------------------------------|
| `BENCHMARK_PASS_THRESHOLD`   | 0.80    | Minimum pass rate to allow approval                  |

---

## Execution Agent

| Parameter                    | Default | Where Used                                       |
|------------------------------|---------|--------------------------------------------------|
| `MAX_EXECUTION_ITERATIONS`   | 15      | Max agentic loop iterations per task             |

---

## Example `/Users/amirali.iranmanesh/JB/OpenSpace/src/config.py`

```python
# Evolution engine
EVOLUTION_MAX_ITERATIONS = 5
EVOLUTION_MAX_APPLY_ATTEMPTS = 3
EVOLUTION_MAX_CONCURRENT = 3

# Trigger 1 — analysis
ANALYSIS_MAX_ITERATIONS = 5
MAX_CONVERSATION_CHARS = 80_000
MAX_TOOL_ERROR_CHARS = 1_000
MAX_TOOL_RESULT_CHARS = 800
MAX_TOOL_ARGS_CHARS = 500
MAX_TRAJ_SUMMARY_CHARS = 1_500
MAX_SKILL_CONTENT_CHARS = 8_000

# Trigger 2 — tool degradation
TOOL_DEGRADED_RATE = 0.5
TOOL_MIN_CALLS = 5
TOOL_ROLLING_WINDOW = 100

# Trigger 3 — health check
METRIC_CHECK_EVERY_N_EXECUTIONS = 5
METRIC_MIN_SELECTIONS_TO_EVALUATE = 5
FALLBACK_THRESHOLD = 0.40
HIGH_APPLIED_FOR_FIX = 0.40
LOW_COMPLETION_THRESHOLD = 0.35
MODERATE_EFFECTIVE_THRESHOLD = 0.55
MIN_APPLIED_FOR_DERIVED = 0.25

# Skill selection
MAX_SKILLS_PER_TASK = 3
QUALITY_FILTER_MIN_SELECTIONS = 2

# Recurrence
RECURRENCE_PROMOTION_THRESHOLD = 3
RECURRENCE_MIN_DISTINCT_RUNS = 2

# Feature requests
FEATURE_REQUEST_AUTO_ACCEPT = False

# Benchmark
BENCHMARK_PASS_THRESHOLD = 0.80

# Execution
MAX_EXECUTION_ITERATIONS = 15
```
