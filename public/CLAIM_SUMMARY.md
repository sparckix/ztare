# Reasoning-Compiler / Research-Agent Contracts — Public Claim Summary

> Public-evidence surface for the H31-H55 pattern/action, orchestration-menu,
> anti-pattern, and PDE/RD contract work. Detailed artifacts remain in
> `epistemic-generation/experiments/`.

## Claim

LLM research agents benefit from a runtime contract layer that turns source
facts into inspectable obligations: residual/evidence carrier, nearest
confuser, action program, deterministic gate, and later outcome trace.

This is a **reasoning-compiler discipline** claim, not a claim that creativity
or theory generation has been automated.

## Evidence

Controlled synthetic/replay experiments support four highlights:

- Labels and catalogue prose were weak; executable contract fields changed
  downstream behavior more reliably.
- Free-form compilation was unsafe; typed classing needed source-cue checks,
  deterministic lowering, and program invariants.
- Wrong contracts actively misrouted action until invariant gates caught wrong
  order, stop condition, outside handoff, or lowering.
- Boundary-card and PDE/RD tests showed the same pattern: validate the typed
  work unit or repair trace, rather than trusting prose that says the work was
  done.

## Boundaries

Production uplift is not established. Existing production-like traces had zero
complete rows for the orchestration shadow schema, so outside-menu expansion and
known-first refusal remain instrumentation-only until shadow rows with later
outcomes exist.

## Retest Tag

*Methodology / framework claim; synthetic/replay positive with production-shadow
gap.* Axis A is closed as scoped-positive; Axis B needs production shadow rows;
Axis C needs live repair-loop traces; PDE/RD needs continued work-unit checks on
live payloads.

## Cross-Reference

- Public claim register: `docs/public_claim_register.md`, section *Epistemic
  Generation as Mechanization Placement*.
- Research log: `epistemic-generation/research_log.md`, H31-H55
  and "Reasoning-compiler synthesis after H31-H51".
- Key code: `orchestration_contract_gate.py`, `orchestration_shadow_log.py`,
  `boundary_card_gate.py`, `boundary_card_repair_trace.py`,
  `pde_work_unit_gate.py`.
