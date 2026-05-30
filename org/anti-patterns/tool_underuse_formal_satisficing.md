---
id: ANTI-PATTERN-018
name: tool_underuse_formal_satisficing
version: 1
status: active
discovered: 2026-05-20
cluster_size: 3
discovered_reason: |
  Multiple hard residual sessions had a domain workbench, graph surface, or
  reusable ZTARE primitive available, but the agent moved from pencil sketch
  to formal/code edits and then toward close before using those tools.  When
  the tools were finally used, they caught weak surfaces: declaration-only
  spend partitions, missing typed nonnegativity, and event-prefix/payment
  distinctions.
triggers:
  lexical:
    - "I'll patch Lean"
    - "compile passed"
    - "close the tick"
    - "workbench later"
    - "tool not needed"
  structural:
    - hard_residual_with_available_domain_tools
    - formal_edit_after_single_pencil_pass
    - compile_or_close_attempt_before_tool_stress_pass
    - reusable_primitive_gap_not_promoted
    - skipped_tool_without_why_not
  problem_classes:
    - hard_mathematical_residual
    - hard_research_residual
    - proof_frontier
    - formal_frontier
detection_protocol:
  primary: PATTERN-028
  secondary: PATTERN-025
  rule:
    - "Before any formal/code edit on a hard residual, verify that a pencil artifact exists and that class-matched tools/primitives were run or explicitly marked why_not."
    - "Before close, verify that the patched artifact was stressed by a tool/adversarial pass, not just compiled."
    - "If a missing discriminator would be reusable, require a promotion decision: promote now, defer with reason, or reject."
mitigation:
  - "Run PATTERN-028 recursive_tool_depth_loop."
  - "Add a research_done loop entry with orientation, tool pass, artifact pass, and stress pass."
  - "Move substrate-specific vocabulary to caller/profile layers; keep reusable primitives substrate-neutral."
  - "If the tool catches a weak surface, fix the artifact rather than weakening the tool."
falsifiable_test:
  description: "For a hard residual tick with a formal/code artifact, inspect the tick receipt and artifacts."
  binary_check: "fires iff there is no pre-edit tool/primitives pass or no post-edit stress pass, and no explicit why_not for available class-matched tools."
  not_trivial: "Does not fire on ticks that run pencil -> workbench/primitive -> artifact -> rerun/stress, even if the mathematical result is negative."
chain_position: in_tick
references:
  - org/patterns/recursive_tool_depth_loop.md
  - org/patterns/gowers_first_formalize_second.md
  - AGENTS.md §0a2 2d1/2e1/2e2/2e3
  - org/mandates/research_director_mandate.md v1.66/v1.69
---

# ANTI-PATTERN-018 — Tool-Underuse Formal Satisficing

## What It Is

A hard residual has available domain tools, graph surfaces, deterministic
checks, or reusable primitives, but the agent moves from a pencil sketch to a
formal/code patch and treats compilation or a single stress pass as enough.

The result can look disciplined because it has a checked artifact, while the
best available falsifiers and discriminators were left idle.

## Why It Appears

Compilation, close gates, and judge feedback are executable and immediate.
Research depth is often a taste judgment unless it is mechanized.  Agents
therefore optimize toward the executable feedback and stop before the domain
tooling has shaped the statement.

## Detection Signatures

- A hard residual tick has a formal/code diff but no pre-edit tool/workbench
  receipt.
- A tool is mentioned as existing, but no command output or artifact is cited.
- A reusable primitive gap is described in prose but not promoted, deferred
  with reason, or rejected.
- The post-edit check is only compile/build, with no adversarial or tool pass.
- Substrate vocabulary leaks into a general-purpose helper instead of living
  in a caller/profile.

## Mitigation

Run PATTERN-028.  The minimum acceptable sequence is:

```text
pencil/orientation -> tool or primitive pass -> artifact edit -> stress pass
```

If a class-matched tool is skipped, write a one-line `why_not`.  If the tool
is too weak and the gap is reusable, improve the primitive with structured
inputs/outputs and a small test; otherwise record the limitation and keep the
tick verdict bounded.
