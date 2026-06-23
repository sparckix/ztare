---
description: "Review packet for narrow fail-closed validator and source-contract preflight checks."
---
# Validator Source Preflight Packet

> **Up:** [Review Packets](README.md)

## Scoped Claim

ZTARE now has additional narrow source-contract checks at the autoresearch
workbench boundary. Context inference will not mark a workbench surface ready
when the rubric source is malformed or when a hidden-holdout rubric lacks the
required project files.

The checked examples are intentionally small:

- weighted rubric `dimensions` must be structurally valid and sum to 100 when
  provided;
- `holdout_hard_gate: true` requires `gate_harness.py` and
  `evidence_holdout.txt`;
- malformed rubric JSON fails before routing.

This extends the existing route JSON validation in
`scripts/public/control/action_intelligence.py`.

## Evidence Level

L1: deterministic preflight implementation with fixed tests. This is boundary
hardening, not a benchmark result.

## Primary Sources

- [autoresearch_workbench_router.py](../../../src/ztare/research_director/autoresearch_workbench_router.py)
- [action_intelligence.py](../../../scripts/public/control/action_intelligence.py)
- [test_autoresearch_workbench_router.py](../../../tests/research_director/test_autoresearch_workbench_router.py)
- [test_action_intelligence.py](../../../tests/scripts/test_action_intelligence.py)
- [rubric specification](../../concepts/rubric_specification.md)

## Runnable Anchor

```bash
PYTHONPATH=src:. ./venv/bin/python -m pytest tests/research_director/test_autoresearch_workbench_router.py tests/scripts/test_action_intelligence.py -q
```

Expected output:

```text
21 passed
```

## What The Test Covers

The router tests verify that malformed weighted dimensions, missing hidden
holdout source files, and malformed rubric JSON do not silently route a task as
ready for autoresearch.

The action-intelligence tests verify that malformed agentic route JSON fails
before row construction, including missing prerequisite booleans and
inconsistent `invoke_autoresearch` decisions.

## Evidence Summary

The added checks live at existing source boundaries. The workbench router now
records source-contract errors instead of inferring a ready workbench from a
malformed rubric or a missing hidden-holdout source. The action-intelligence
route JSON check remains the row-construction boundary for route records.

## Non-Claims

- No claim that all rubric fields are fully schema-validated.
- No claim that a preflight pass proves the downstream research result.
- No claim that the workbench router replaces the full autoresearch loop gates.
- No claim that historical rubrics are all clean.

## Next Falsifier

A new malformed rubric or route row that reaches an `invoke_autoresearch`
decision without source-contract errors would falsify this packet's current
coverage. The next upgrade should add a broader rubric schema gate only after
the existing launcher and router share the same contract vocabulary.

## Missing Upgrade

The missing upgrade is a single shared rubric schema gate used by both the
router and the full autoresearch launcher. The current packet only covers the
highest-risk context-inference failures named in the rubric specification.
