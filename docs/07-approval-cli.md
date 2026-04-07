# Approval Gate — CLI, Benchmark, Rollback, Audit

The approval gate is the human review layer. All evolved skills land in `status=pending` and require explicit approval before going live. See `11-ui.md` for the web UI that exposes this workflow.

---

## Source Files

| File | Role |
|------|------|
| `/Users/amirali.iranmanesh/JB/OpenSpace/src/approval/queue.py` | Pending queue reader + approval/rejection logic |
| `/Users/amirali.iranmanesh/JB/OpenSpace/src/approval/benchmark.py` | Benchmark regression guard runner |
| `/Users/amirali.iranmanesh/JB/OpenSpace/src/approval/cli.py` | `manage.py` CLI commands |
| `/Users/amirali.iranmanesh/JB/OpenSpace/src/audit/log.py` | Audit log writer |

---

## Skill Lifecycle States

```
bootstrap  → active
evolution  → pending → approved → active
                     → rejected   (preserved forever, never goes active)
rollback   → new active record created from old content (bypasses pending)
```

A skill in `pending` state is not selectable for execution and does not supersede its parent. Parent stays `active` until approval.

---

## CLI Commands (`python manage.py ...`)

```bash
# Evolutions
python manage.py pending                              # list pending queue
python manage.py show {skill_id}                     # show diff + details
python manage.py approve {skill_id}                  # runs benchmark, then approves
python manage.py reject {skill_id} --reason "..."    # reject with reason
python manage.py edit-approve {skill_id}             # open $EDITOR, then approve

# Feature requests
python manage.py feat list
python manage.py feat accept {feat_id}               # triggers CAPTURED evolution
python manage.py feat defer {feat_id}
python manage.py feat dismiss {feat_id} --reason "..."

# History and rollback
python manage.py history {skill_name}                # all versions
python manage.py rollback --skill {skill_name} --to-generation {N}

# Audit
python manage.py audit [--skill {skill_name}] [--last N]

# Constitution
python manage.py constitution edit                   # creates versioned backup first
```

---

## Approval Actions

| Action             | Effect |
|--------------------|--------|
| **approve**        | Benchmark runs → if pass: `status=active`, parent `status=superseded`, audit entry written |
| **reject**         | `status=rejected`, parent stays `active`, audit entry with rejection reason |
| **edit-approve**   | Reviewer edits content → new content snapshot stored → benchmark runs → approved |

## Feature Request Actions

| Action      | Effect |
|-------------|--------|
| **accept**  | Triggers CAPTURED evolution with the capability as `direction` |
| **defer**   | Leaves in queue |
| **dismiss** | Sets `status=wont_fix` |

---

## Benchmark Regression Guard

Runs automatically before any approval (CLI or UI). Lives in `/Users/amirali.iranmanesh/JB/OpenSpace/src/approval/benchmark.py`.

**Benchmark definition** (`agent/benchmark.json`):

```json
[
  {
    "id": "bench_001",
    "task": "Review PR #456 which adds raw SQL string formatting",
    "pr_content": "...",
    "expected_flags": ["sql_injection"],
    "expected_no_flags": ["variable_naming"]
  }
]
```

**Flow**:
1. Temporarily activate the pending skill in a sandboxed DB snapshot
2. Run all benchmark tasks against the candidate skill set
3. Compare outputs against `expected_flags` / `expected_no_flags`
4. If `pass_rate >= BENCHMARK_PASS_THRESHOLD (0.80)` → proceed
5. If below threshold → block approval, surface which cases failed

**Pass function**:

```python
def evaluate_case(output: str, expected_flags: list[str], expected_no_flags: list[str]) -> bool:
    for flag in expected_flags:
        if flag not in output.lower():
            return False   # missed a required finding
    for flag in expected_no_flags:
        if flag in output.lower():
            return False   # made a forbidden finding
    return True
```

---

## Rollback

Creates a **new** DB record from the old content — never mutates history.

```python
def rollback(skill_name: str, to_generation: int):
    target = db.get_skill_version(name=skill_name, generation=to_generation)
    current_active = db.get_active_skill(skill_name)

    db.set_status(current_active.id, "superseded")

    new_id = f"{target.name}__v{current_max_gen + 1}_{uuid8()}"
    db.insert_skill(SkillRecord(
        id=new_id,
        content=target.content,
        parent_id=current_active.id,
        generation=current_max_gen + 1,
        lineage_origin="ROLLBACK",
        status="active",   # bypasses approval gate — explicit human action
    ))

    write_skill_to_disk(new_id, target.content)

    db.write_audit(
        action="rollback",
        skill_id=new_id,
        reviewer=current_user,
        note=f"Rolled back to generation {to_generation}",
        parent_id=current_active.id,
    )
```

---

## Audit Log

Every state-changing action is written to `audit_log`. See `08-database.md` for the full schema.

**Events**:

| Action                | When |
|-----------------------|------|
| `bootstrap`           | Meta-agent creates initial skills |
| `approved`            | Evolution approved |
| `rejected`            | Evolution rejected |
| `edited_and_approved` | Reviewer edited content and approved |
| `rollback`            | Skill rolled back to previous generation |
| `constitution_edited` | Human edits constitution |

**Example entry**:

```json
{
  "event_id": "audit_x1y2z3",
  "skill_id": "check-sql-injection__v3_ab12cd",
  "action": "approved",
  "reviewer": "alice@company.com",
  "timestamp": "2026-04-07T14:45:00Z",
  "parent_id": "check-sql-injection__v2_e5f6g7h8",
  "content_diff": "unified diff string",
  "benchmark_passed": 1,
  "benchmark_details": {"passed": 12, "total": 12},
  "note": ""
}
```

**Useful queries**:

```sql
-- Who approved what, when
SELECT a.action, a.reviewer, a.timestamp, s.name, s.generation
FROM audit_log a JOIN skills s ON a.skill_id = s.id
ORDER BY a.timestamp DESC;

-- All changes to a specific skill
SELECT a.action, a.reviewer, a.timestamp, a.note
FROM audit_log a WHERE a.skill_id LIKE 'check-sql-injection%'
ORDER BY a.timestamp;

-- Rejection reasons
SELECT s.name, a.note, a.timestamp
FROM audit_log a JOIN skills s ON a.skill_id = s.id
WHERE a.action = 'rejected';
```

---

## Constitution Management

The constitution is a flat file at `agent/constitution.md`, never stored in the `skills` table, never touched by the evolution engine.

On any human edit:
1. Back up current file as `constitution_v{N}.md`
2. Write new content to `constitution.md`
3. Write `audit_log` entry with `action="constitution_edited"`
