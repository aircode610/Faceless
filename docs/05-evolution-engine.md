# Evolution Engine — FIX / DERIVED / CAPTURED

The evolution engine takes a dispatched `EvolutionSuggestion` and produces a new skill version. All three evolution types share the same inner loop but use different prompts and write different records to SQLite.

All evolved skills land in `status=pending` and require human approval before going live.

---

## Source Files

| File | Role |
|------|------|
| `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/evolver.py` | FIX/DERIVED/CAPTURED logic, inner loop, apply-with-retry — copy/adapt |
| `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py` | Evolution prompts (FIX, DERIVED, CAPTURED) — copy verbatim |
| `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/store.py` | SQLite write patterns — copy/adapt |
| `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/types.py` | SkillRecord, EvolutionSuggestion types — copy/adapt |

---

## Inner Evolution Loop

All three types run this loop:

```
Iteration 1..N-1:
  LLM has tools available (read_file, web_search, shell, etc.)
  LLM investigates the issue, reads skill content, gathers context
  If LLM outputs <EVOLUTION_COMPLETE> → extract content → proceed to apply
  If LLM outputs <EVOLUTION_FAILED> → abort, log reason, return None
  Otherwise → continue iterating

Iteration N (final, forced):
  Tools disabled
  LLM must output final content or declare failure
```

**Limits**:
- `EVOLUTION_MAX_ITERATIONS = 5`
- `EVOLUTION_MAX_APPLY_ATTEMPTS = 3` (apply → validate SKILL.md frontmatter exists and is valid → if error: feed back to LLM for correction)

On `EVOLUTION_FAILED` or parse error at final iteration → evolution is aborted, suggestion status set to `"failed"`, no DB record written.

---

## 7a — FIX Evolution

**Purpose**: Repair a broken, outdated, or incomplete skill in place. The fixed version replaces the parent.

**Prompt** (verbatim from `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py` → `_EVOLUTION_FIX_TEMPLATE`, lines 376-509):

```
Class: SkillEnginePrompts.evolution_fix()
Inputs: current_content, direction, failure_context, tool_issue_summary, metric_summary, constitution
```

The constitution block is injected at the top via `_format_constitution_block()`.

Output format: `CHANGE_SUMMARY: ...` followed by a patch (Format A — preferred) or full rewrite (Format B), ending with `<EVOLUTION_COMPLETE>` or `<EVOLUTION_FAILED>`.

**DB record written on success**:

```
New SkillRecord:
  id:               {name}__v{generation}_{uuid8}
  parent_id:        old skill id
  generation:       parent.generation + 1
  lineage_origin:   "FIXED"
  content_diff:     unified diff vs parent
  content_snapshot: full file contents at this version
  status:           "pending"   ← awaits human approval
```

**Lifecycle on approval**:
- Old skill → `status=superseded`
- New skill → `status=active`
- Old skill's directory on disk is removed; new skill's directory is written

**Lifecycle on rejection**:
- Old skill stays `status=active`
- New skill stays `status=rejected`
- No filesystem changes

---

## 7b — DERIVED Evolution

**Purpose**: Create an enhanced version of a skill in a new directory. The parent skill stays unchanged and active until the derived version is approved.

Use DERIVED when the existing skill is not broken but could be significantly improved — better coverage, restructured steps, merged with another skill.

**Prompt** (verbatim from `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py` → `_EVOLUTION_DERIVED_TEMPLATE`, lines 512-656):

```
Class: SkillEnginePrompts.evolution_derived()
Inputs: parent_content, direction, execution_insights, metric_summary, constitution
```

Output format: `CHANGE_SUMMARY: ...` followed by patch or full rewrite for a **new** skill directory, ending with `<EVOLUTION_COMPLETE>` or `<EVOLUTION_FAILED>`.

**DB record written on success**:

```
New SkillRecord:
  id:               {new_name}__v{max_parent_gen+1}_{uuid8}
  parent_ids:       [parent_id]               ← or [id_a, id_b] for a merge of two skills
  generation:       max(parent.generation) + 1
  lineage_origin:   "DERIVED"
  content_snapshot: full file contents
  status:           "pending"
```

**On approval**: parent skill → `status=superseded`, new skill → `status=active`.

For merges (two parent skills): both parents are superseded upon approval.

---

## 7c — CAPTURED Evolution

**Purpose**: Extract a novel reusable pattern the agent discovered without any skill guidance, or fulfill an accepted feature request.

CAPTURED skills have no parent — they are brand new entries in the skill library. This type is also triggered when a reviewer accepts a feature request from the approval queue.

**Prompt** (verbatim from `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py` → `_EVOLUTION_CAPTURED_TEMPLATE`, lines 659-765):

```
Class: SkillEnginePrompts.evolution_captured()
Inputs: direction, category, execution_highlights, constitution
```

Output format: `CHANGE_SUMMARY: ...` followed by a full new `SKILL.md` content (no patch, since there is no parent), ending with `<EVOLUTION_COMPLETE>` or `<EVOLUTION_FAILED>`.

**DB record written on success**:

```
New SkillRecord:
  id:               {name}__v1_{uuid8}
  parent_ids:       []
  generation:       1
  lineage_origin:   "CAPTURED"
  content_snapshot: full file contents
  status:           "pending"
```

---

## Evolution Principles

These apply to all three evolution types. Inject them into the evolution LLM's system prompt.

**1. Explain the why, not just the what.**
Don't write "ALWAYS check f-strings". Write: "Check f-strings because Python's f-string interpolation bypasses parameterized query protection — the database driver never sees the template, only the final interpolated string." LLMs follow reasoning better than rules, and reasoning generalizes to edge cases.

**2. Keep skills lean.**
Remove steps that aren't pulling their weight. If a step consistently gets skipped in execution logs, the agent has decided it's not useful. Lean skills are faster to inject and easier to follow.

**3. Bundle repeated scripts.**
If execution logs show the agent writing the same helper script (e.g., `check_fstrings.py`) across 2+ independent runs, that script should be moved into `scripts/` in the skill directory. The next evolution should reference it directly rather than re-implementing it.

**4. Re-check the description after any evolution.**
When content changes significantly (FIX or DERIVED), the `description` frontmatter may become stale. The evolution LLM must review and update it to accurately reflect the new trigger conditions. A stale description causes under- or over-selection.

**5. Generalize, don't overfit.**
Suggestions come from a single task run. The fix should address the root pattern, not the specific instance. If the agent missed an f-string in `user_id`, the fix must cover all f-string interpolation in SQL contexts — not just `user_id`.

---

## Skill ID Format

```
{skill-name}__v{generation}_{8-char-uuid}

Examples:
  check-sql-injection__v1_a1b2c3d4   ← generation 0 bootstrap
  check-sql-injection__v2_e5f6g7h8   ← after first FIX
  check-sql-injection__v3_ab12cd34   ← after second FIX
  check-infra-drift__v1_xy99zz00     ← a CAPTURED skill (new)
```

---

## Filesystem Layout After Evolution

When a FIX evolution is approved and activated:

```
agent/skills/
  check-sql-injection/         ← directory updated in place
    SKILL.md                   ← new version content
    .skill_id                  ← updated: "check-sql-injection__v3_ab12cd34"
    scripts/
      check_fstrings.py        ← may be added if evolution bundled a script
```

When a DERIVED evolution is approved:

```
agent/skills/
  check-sql-injection/         ← original, now status=superseded (directory removed)
  check-sql-injection-enhanced/  ← new directory written
    SKILL.md
    .skill_id
```

When a CAPTURED evolution is approved:

```
agent/skills/
  check-infra-drift/           ← new directory written
    SKILL.md
    .skill_id
```
