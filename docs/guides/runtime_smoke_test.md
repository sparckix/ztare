---
description: "Sub-five-second runtime sanity check that spends no API credits."
---
# Runtime Smoke Test

> **Up:** [Documentation map](../README.md)

**Purpose.** Prove the org runtime is structurally sound on your machine in
under five seconds, without spending API credits.

```bash
python scripts/public/control/runtime_smoke_test.py
```

A green run looks like this:

```text
PASS  runtime smoke test  stamp=test_runtime_smoke_<timestamp>
  ok  research_problem
  ok  preference_profile (taste axes: 4)
  ok  role_loop (5 roles)
  ok  approval_channel
  ok  audit_trail
  cleanup: removed 4 artifact(s)
```

If you see five `ok` rows and a clean cleanup, the runtime is sound. The
script exercises the five irreducible elements of the runtime, all in one
pass, with no LLM dependency.

---

## What it actually does

| Step | Element | What the script does | What it proves |
|---|---|---|---|
| 1 | task | Drops one synthetic task into `org/tasks/active/` | The task schema is writable and the task directory is in the right place |
| 2 | preference profile | Loads `org/preferences/principal.yaml` and counts the priority axes | Preferences parse and contain the priority vector that role daemons consume each tick |
| 3 | role loop | Calls `scripts/public/control/org_role_preflight.py --json` for every role yaml | All roles match `schemas/role.v1.schema.json`, mandates resolve, and the bootstrap chain is intact |
| 4 | approval channel | Drops a synthetic approval, runs the same atomic-write resolution Orbit's API uses, renames the pending file to `.handled`, appends one `transitions.jsonl` row | The pending → resolved → audit pipeline is wired and atomic |
| 5 | audit trail | Reads the last 50 lines of `transitions.jsonl` and confirms exactly one row matches the synthetic approval | The audit log is append-only, parseable, and replayable |

The script does **not**:

- Invoke any agent CLI (no LLM calls, no spend).
- Test a live tenant notification provider (would need real provider
  credentials).
- Test the Orbit dashboard (would need git-sync server up + browser).
- Test multi-host coordination, RBAC, or signed audit (those are
  enterprise-axis features, out of scope until the relevant trigger fires).

The script **does** clean up after itself unless you pass `--keep`.

---

## When to run it

- After cloning the repo, before doing anything else.
- After editing any role yaml, the role-loop step catches schema drift the
  fastest of any check.
- In CI on every commit that touches `org/`, `ztare_workspace/`,
  `schemas/`, or `scripts/public/control/org_role_preflight.py`.
- After an upgrade, if the smoke test fails on a commit that previously
  passed, the regression is structural, not subtle.

---

## When it fails

The script prints which step failed and surfaces the underlying error.
Common diagnoses:

| Failure | Likely cause | Fix |
|---|---|---|
| `research_problem` red | `org/tasks/active/` is not writable | Check filesystem permissions, or that you ran from the repo root |
| `preference_profile` red, `axes_count: 0` | `org/preferences/principal.yaml` is missing or malformed | Restore from git or rerun `scripts/public/control/org_first_run_setup.py` |
| `preference_profile` red, "PyYAML not installed" | Python deps missing | `pip install -r requirements.txt` |
| `role_loop` red | A role yaml diverged from `schemas/role.v1.schema.json` | Run `python scripts/public/control/org_role_preflight.py --role <name>` to see the exact field that broke |
| `approval_channel` red | `ztare_workspace/gates/` is not writable | Check filesystem permissions |
| `audit_trail` red, `matches_found: 0` | `transitions.jsonl` write was lost | Investigate disk / volume / mount issues; rerun |
| `audit_trail` red, `matches_found: >1` | A previous run left rows behind | Run with `--keep` then inspect `transitions.jsonl` for stale rows manually |

---

## Output flags

| Flag | Effect |
|---|---|
| (none) | Pretty-print one line per step. Exit 0 on green, 1 on red. |
| `--json` | Print full machine-readable JSON report with timestamps and per-step detail. Useful for CI artifact upload or downstream tooling. |
| `--keep` | Skip cleanup. Leaves the synthetic task, approval (pending + resolved), and audit row in place under the `test_runtime_smoke_<timestamp>` stamp so you can inspect them. **Remember to clean up manually** if you use this on a long-lived deployment. |

---

## What "smoke test" means here

This is not a stress test, a benchmark, a fuzzer, or a security audit. It is
the smallest possible runnable proof that the runtime is alive and the
contracts hold. If it passes, your runtime is in a sound starting state. If
it fails, the runtime itself is broken, fix it before doing anything else
with the org.

A passing smoke test is a necessary, not sufficient, condition for shipping
work through the runtime. The next layer up is the rail-specific verification
in the Orbit dashboard and tenant notification setup guides (those exercise
the human-facing rails the smoke test deliberately skips).

---

## Cross-references

- `scripts/public/control/runtime_smoke_test.py`, the script itself
- `scripts/public/control/org_first_run_setup.py`, the broader first-run preflight (covers
  more configuration; takes longer; does not exercise the approval flow)
- `scripts/public/control/org_role_preflight.py`, the per-role validator the smoke test
  delegates to
- `schemas/role.v1.schema.json`, the role contract the smoke test enforces
- `docs/guides/org_runtime_quickstart.md`, what to do once the smoke test
  is green
