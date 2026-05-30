---
id: ANTI-PATTERN-006
name: cross_agent_monoculture
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: ["cross-family validated", "swarm verified", "3 agents agree"]
  structural:
    - validation_claimed_via_n_claude_code_agent_subagents_all_claude
    - convergent_verdict_used_to_promote_claim_without_cross_family_check
    - same_agent_produces_claim_and_audits_it
    - paid_cross_family_swarm_skipped_when_load_bearing_decision_imminent
  problem_classes: [apparatus_self_audit]
detection_protocol:
  primary: PATTERN-011  # swarm_dispatch (named anti-pattern: AGENT-FAMILY-LAUNDERING)
  secondary: PATTERN-002  # darwin_idea_killer (cross-family LLM diagnostic)
  rule:
    - "Claiming 'cross-family validation' using N Claude Code Agent subagents (all Claude family) is AGENT-FAMILY-LAUNDERING. True cross-family requires the PY LLM-based variant of swarm_dispatch (Anthropic + Google + OpenAI)."
    - "When a primitive is being claimed 'novel above the published frontier' OR a central decision turns on the verdict, escalate from agent-based → PY LLM-based swarm per AGENTS.md §6e.0."
    - "DARWIN must run on cross-family LLM, not the same family that produced the claim (PATTERN-002 anti-pattern: SELF-GRADING)."
mitigation:
  - "Escalate to PY LLM-based swarm via existing scripts (scripts/openmath_novel_ideas_swarm.py / surgical_swarm_panel.py / swarm_vitali_to_integral.py) with --budget-estimate-only first, then --allow-paid once authorized."
  - "Re-label the prior agent-based 'cross-family' verdict as 'single-family Claude convergence'."
  - "Per AGENTS.md §6e.1: judge tier MUST be a different provider family than mutator. Apply the same rule to anti-pattern audits."
examples:
  - id: catch_22
    summary: "Mentioned in catch #25 ledger update as already-recorded monoculture catch. Pattern: agent-based swarm (Claude-only) used in places where AGENTS.md §6e.0 would mandate PY LLM-based cross-family swarm. PATTERN-011 swarm_dispatch's anti-pattern section names this AGENT-FAMILY-LAUNDERING."
    file: anti_laundering_catch_25_lean_elaborator_rabbithole_2026_05_08.md
falsifiable_test:
  description: "Inspect the dispatch record for any claim labeled 'cross-family validated'. The anti-pattern fires iff every agent in the swarm was the same provider family (e.g. all Claude Code Agents)."
  binary_check: "len(distinct_provider_families(swarm_agents)) ≥ 2, firing iff False."
  not_trivial: "Returns 'not firing' when scripts/openmath_novel_ideas_swarm.py runs across Claude Opus + GPT-5.5 + Gemini 3.1 Pro (3 distinct families). Returns 'firing' when 5 Claude Code Agent subagents all return convergent verdicts and the verdict is then claimed cross-family. The test discriminates. NOT True := by trivial."
chain_position: pre  # runs BEFORE promoting any claim that depends on cross-family validation
references:
  - "PATTERN-011 swarm_dispatch (AGENT-FAMILY-LAUNDERING anti-pattern section)"
  - "PATTERN-002 darwin_idea_killer (SELF-GRADING anti-pattern section)"
  - "AGENTS.md §6e.0 (cross-family hygiene), §6e.1 (model tier discipline)"
  - "scripts/openmath_novel_ideas_swarm.py"
  - "scripts/surgical_swarm_panel.py"
  - "anti_laundering_catch_25_lean_elaborator_rabbithole_2026_05_08.md"
---

# ANTI-PATTERN-006, Cross-Agent Monoculture

## What it is

Treating N parallel Claude Code Agent subagents as "cross-family
validation" when all subagents are the same provider family. The
PATTERN-011 swarm_dispatch documentation already names this
AGENT-FAMILY-LAUNDERING; the anti-pattern entry formalizes
detection.

## Why it appears

Agent-based swarms are free within session quota; PY LLM-based
swarms have real-dollar cost and require budget approval. The
incentive is to use agent-based for everything and call it
"cross-family". The Claude family has correlated biases that
single-family validation cannot detect (training-data overlap,
RLHF objective overlap).

## Why it matters

Tonight's catch #22 surfaced this in the META-DARWIN-HOFSTADTER
audit. A primitive being claimed "novel above the published
frontier" requires actual cross-family check (Anthropic + Google +
OpenAI agreement), not 3 Claude subagents agreeing. The cost of
not running paid swarm at the central decision points is
overstated novelty claims that won't survive external review.

## Detection protocol

Apply PATTERN-011 swarm_dispatch's own AGENT-FAMILY-LAUNDERING
detection:

1. Inspect dispatch record: list provider family per subagent.
2. If `len(distinct_provider_families) < 2`, the verdict is NOT
   cross-family validated.
3. Cross-check against AGENTS.md §6e.0 trigger conditions:
   primitive claimed "novel above frontier"? central decision
   turns on verdict? → escalate to PY LLM-based swarm.

## Mitigation when detected

- Re-label single-family verdict honestly: "5 Claude Code Agents
  converged" not "cross-family validated".
- Escalate to PY LLM-based swarm via:
  - `scripts/openmath_novel_ideas_swarm.py --budget-estimate-only`
  - present estimate to operator
  - dispatch with `--allow-paid` once authorized
- Per AGENTS.md §6e.1: judge family ≠ mutator family. Same rule
  for anti-pattern audits, use cross-family DARWIN.

## Falsifiable test (catalog-level)

`len(distinct_provider_families(swarm_agents)) ≥ 2`. Firing iff
False.

NOT trivially True: scripts/openmath_novel_ideas_swarm.py
empirically runs across 3 distinct families (test passes,
not-firing). Tonight's morning iteration used 7+ hours of
agent-based swarm (test fails for any audit citing it as
cross-family, firing). The test discriminates.

## Cross-references

- PATTERN-011 (`org/patterns/swarm_dispatch.md`), anti-pattern
  section names AGENT-FAMILY-LAUNDERING.
- PATTERN-002 (`org/patterns/darwin_idea_killer.md`), SELF-GRADING
  anti-pattern (related family-discipline rule).
- AGENTS.md §6e.0 + §6e.1.
- `scripts/openmath_novel_ideas_swarm.py`,
  `scripts/surgical_swarm_panel.py`.
- `projects/ns_millennium_hunt/workspace/research_notes/anti_laundering_catch_25_lean_elaborator_rabbithole_2026_05_08.md`
