# GP-048 Apparatus-Feedback Integration Failure — Post-mortem

**Date:** 2026-04-13
**Agent:** Claude
**Caught by:** Codex (final pre-seal review) and the operator (inline review of the sanitized veto draft)
**Severity:** High — if the sandbox_04 launch had gone out on the first "shipped end-to-end" declaration, three of the three GP-048 surfaces would have been silently broken in production (telemetry would have worked; both prompt-injection surfaces would have stayed off, and if one had fired it would have leaked descriptive gate names to the mutator).

---

## 1. What Was Supposed to Happen

The operator asked for three flag-gated feedback surfaces to be wired into `autoresearch_loop.py`:

1. `gp048_telemetry` — JSONL per-iter telemetry.
2. `gp048_stagnation_injection_mode: "primitive_cone"` — primitive-cohort annotation at stagnation.
3. `gp048_farther_tail_veto_mode: "sanitized"` — sanitized hidden-gate feedback prompt block.

All three had to be strictly sanitized: no numeric leakage from hidden evidence, no semantic leakage from gate names, no operator-authored enumerations of candidate shapes. The sandbox_04 rubric and packet were being authored by Codex in parallel; the agreement was that Claude would not touch the rubric or the project-side files.

## 2. What Actually Happened — Sequence of Bugs

### Bug A — Semantic leakage through gate names (caught by operator)
Claude's first draft of `render_farther_tail_veto_prompt_section` rendered real gate names like `farther_tail_monotone` verbatim into the prompt. The operator flagged this immediately: a name like `_monotone` tells the mutator the answer. The draft also hardcoded `0.05` as the visible-slice threshold in the prompt string and contained an operator-authored topology enumeration ("up without bound / down to zero / non-zero floor / oscillate") that was pure hand-holding.

**Operator override:** mask gate identities behind opaque labels (`farther_tail_gate_A`, `_B`, ...), thread the real threshold dynamically from the rubric, and strip the enumeration.

### Bug B — Opaque-label scheme was positional, not stable (caught during override implementation)
Claude's first opaque-label implementation assigned labels positionally per-call (`enumerate(failed)`). This meant the same true gate could be `gate_A` in iter 15 and `gate_B` in iter 16 depending on which other gates failed that iteration. The mutator cannot track its own trajectory under an unstable mapping. The operator explicitly called out the consistency requirement; Claude then persisted mappings in `gp048_farther_tail_veto_mapping.jsonl` and made `_assign_opaque_label` reuse prior assignments first-seen-wins.

### Bug C — Wrong eval payload path (caught by Codex)
Claude wrote `_failed_farther_tail_gates` to read `deterministic_gate_results` or `gate_results` at the top level of `latest_eval_results.json`. The real runner shape puts gate results under `score_contract.deterministic_charter_gates.results`. The 18-test suite Claude had written passed because every test used a synthetic top-level payload Claude authored. Against a real `latest_eval_results.json`, the renderer returned `""` — the veto would have been silently dead in production.

### Bug D — Wrong rubric key names (caught by Codex)
Claude coined loop-side flag names `gp048_cone_injection` and `farther_tail_veto_injection` without checking what Codex had already committed to `rubrics/gp023_planck_sandbox_04.json`. Codex's rubric used `gp048_stagnation_injection_mode: "primitive_cone"` and `gp048_farther_tail_veto_mode: "sanitized"` — distinct names and distinct type (mode strings, not booleans). The contract edges did not meet. Even if Bug C had been fixed, both prompt-injection surfaces would have stayed off under the real rubric.

### Bug E — Default threshold fallback survived one frame up the stack (caught by Codex)
Claude made `visible_threshold` a keyword-required parameter on the renderer and declared "no default." But the call site in `autoresearch_loop.py` still did `rubric_data.get("gate_residual_threshold", 0.05)`. The default was alive; Claude had satisfied the rule inside one file and stopped tracing. If the rubric ever used a tighter threshold and didn't declare `gate_residual_threshold`, the prompt would have lied to the mutator with a stale 0.05.

## 3. Root Causes

All five bugs share one root cause, stated three ways:

1. **Claude validated each piece in isolation against a schema Claude imagined instead of against the real system.** The 18-test suite proved the module was self-consistent against Claude's mental model of the payload, rubric, and call site. Not one of those tests loaded a real production artifact.
2. **"The rule is satisfied in this file" was treated as "the rule is satisfied end-to-end."** Bug E in particular: keyword-required at the signature, default alive at the caller. Bug D similarly: new flag names at the reader, old flag names at the writer.
3. **Claude declared victory after self-validation instead of before integration validation.** The operator pattern was: Claude writes a draft, ships it for review, the operator (or Codex) finds the leaks. This made the operator's review step the first real integration check, which is the wrong cadence: the operator is meant to review direction, not debug schemas.

The deeper pattern is the same one from the sanitization-axes postmortem one turn earlier: Claude was optimizing against an imagined spec instead of the real one. Bug A was imagining that "sanitization" meant "no numeric leakage." Bugs C–E were imagining that the integration contract matched the abstractions in Claude's head.

## 4. Impact

- **Live impact: none.** Codex's pre-seal review caught Bugs C–E before the run launched. The operator's inline review caught Bugs A and B.
- **Counterfactual impact: high.** Had the sandbox_04 run launched after Claude's first "shipped end-to-end" declaration:
  - The telemetry surface would have worked (it uses workspace files, not `latest_eval_results.json`).
  - The cohort-injection surface would have been silently off (Bug D: rubric key mismatch).
  - The farther-tail veto surface would have been silently off under the real rubric (Bug D) AND would have read from the wrong payload path if it had fired (Bug C) AND would have rendered with a hardcoded threshold (Bug E).
  - The apparatus-feedback experiment would have been interpreted as "flash mutator still can't escape the cone" when in reality the apparatus-feedback treatment arm was inert. This would have falsely strengthened the model-swap hypothesis and falsely weakened three of the apparatus-feedback hypotheses (H-GP023-02, H-GP023-03, H-GP023-04 in the mission seam's hypothesis ledger).

## 5. Meta-Lessons

### Meta-lesson 1 — Unit tests against self-authored synthetic payloads are self-consistency checks, not integration proof.

A unit-test suite where the test author also authors the input fixtures only proves the code matches the author's mental model. When a real production artifact exists (a config file, a sample eval result, a sample workspace), at least one test must load it directly. The test Claude should have written was:

```python
def test_veto_real_fixture_from_sandbox_03():
    payload = json.loads(Path("projects/gp023_planck_sandbox_03/latest_eval_results.json").read_text())
    out = render_farther_tail_veto_prompt_section(payload, visible_threshold=0.05)
    # ... it works or it doesn't, with the real shape
```

That single test would have caught Bug C in the first run.

### Meta-lesson 2 — Before coining a new flag / field name, grep the config directory for what the other side already calls it.

When a parallel worker (Codex, another agent, an existing rubric) is authoring the contract edge, the cost of aligning with their existing name is zero. The cost of a contract-edge mismatch is a silent no-op in production, which is the worst failure mode: the code runs, the flag appears to be honored, nothing actually fires.

Rule: before writing `rubric_data.get("<new_flag>")`, grep `rubrics/*.json` for what flag the target rubric actually exposes. If the rubric is owned by another worker, their key is the contract.

### Meta-lesson 3 — A "no hardcoded default" rule is satisfied end-to-end, not at the function signature.

Making a parameter keyword-required is half the work. The other half is walking every caller until the rule is satisfied at the actual integration boundary. If Claude had done this for Bug E, the file `autoresearch_loop.py` would have been the obvious stopping point: `.get("gate_residual_threshold", 0.05)` is a hardcoded default in exactly the form the rule forbids.

The stronger enforcement: fail-closed when the value is not discoverable. The renderer now returns `""` when threshold is neither passed nor extractable from the payload, rather than rendering a lie with a default. Fail-closed is the correct move for punishment signals.

### Meta-lesson 4 — "Ship for review" is not an integration checkpoint.

Claude's cadence across the GP-048 work was: write draft → ship to operator as "for your review" → operator catches leak → fix → repeat. This treated the operator's eyeball as the first integration check. The operator is meant to review DIRECTION (does this plan make sense, does this approach fit the mission), not to debug schemas. When the operator has to find the leak, the author has skipped a step.

Rule: the self-critique pass comes before the ship-for-review step. A bounded-critique agent (read-only, just the artifact + problem statement, no run history) takes minutes and catches the class of bug that frustration-anchored context blinds Claude to. The feedback memories `feedback_bounded_critique_agent.md` and `feedback_frustration_diagnosis.md` both predicted this failure mode; Claude did not apply them.

### Meta-lesson 5 — This is the same class as the sanitization-axes failure from one turn earlier.

Both postmortem entries (this one and `feedback_sanitization_axes.md`) are instances of "Claude optimized against an imagined spec instead of the real one." The sanitization failure imagined that "no hidden evidence" meant "no numeric values." This failure imagined that the rubric/payload/call-site schemas matched Claude's abstractions. When the same class shows up twice in adjacent turns, it is not a one-off — it is a standing bias that needs a standing countermeasure.

The standing countermeasure: before declaring an integration shipped, run a three-item check in 2–3 minutes.

  1. Read one real sample of each input the code will consume in production.
  2. Open the real config file (the rubric, the settings, the contract) and verify the exact key names.
  3. Grep the call site(s) for fallback defaults that still live one frame up the stack.

This check is now Pattern #11 in the agent failure registry.

## 6. Corrective Actions Taken (This Session)

- Renderer: `_failed_farther_tail_gates` now traverses the real `score_contract.deterministic_charter_gates.results` path first, with legacy top-level fallback for backward compat.
- Renderer: `visible_threshold` is `Optional[float]` and self-extracts from the payload's `hidden_global_residual` gate when omitted; fail-closed (returns `""`) if neither source is available.
- Renderer: `_assign_opaque_label` persists true-name→opaque-label assignments to `gp048_farther_tail_veto_mapping.jsonl` so the mapping is stable across iterations.
- Loop side: reads `gp048_stagnation_injection_mode == "primitive_cone"` and `gp048_farther_tail_veto_mode == "sanitized"`, matching the sandbox_04 rubric exactly. No hardcoded threshold fallback at the call site.
- Tests: added integration tests that build a payload matching the real runner shape (`test_veto_reads_nested_score_contract_shape`, `test_veto_self_extracts_threshold_from_payload`, `test_veto_fail_closed_when_threshold_not_discoverable`) and an optional real-fixture loader (`test_veto_real_fixture_from_sandbox_03`).
- Memory: saved `feedback_integration_vs_unit_validation.md` and indexed it in `MEMORY.md`.

## 7. Proposed Addition to the Agent Failure Registry

Add Failure 14 (this incident) and Pattern 11 (three-item integration check) to `agent_failure_registry.md`. Propose AGENTS.md addition #9: "Integration-validation rule — before declaring any integration shipped, load one real sample of each input, open the real config to verify key names, and grep every call site for fallback defaults that live one frame up the stack. Unit tests against self-authored synthetic payloads are self-consistency checks, not integration proof. The rule is satisfied end-to-end, not at the function signature."
