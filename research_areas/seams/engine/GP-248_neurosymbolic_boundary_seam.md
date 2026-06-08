# GP-248 — Neurosymbolic Boundary: neural in the PROPOSER (yes, gated) vs neural in the GATES (never)

Status: decided (factory-wide boundary; one gated follow-up implemented for leanmill, one identified for law discovery)
Opened: 2026-06-06
Track: kernel
Related: GP-246 (move-algebra seam), GP-103 (compression primitive), GP-144 (new-science-claim discipline),
         leanmill_architecture.md, common/inversion.py, common/cognitive_gym.py, the 2026-06-05 not-behind verdict

## Trigger

2026-06-06 — Recurring external pushes to "make ZTARE neurosymbolic" (≥2nd time): neural-guided symbolic
regression in `compress`, a learned move-policy/value net + neurosymbolic conjecture/specialize in
leanmill, differentiable gates, and learned symbolic invariants, claiming 3–10× and that the repo is
"already tagged neurosymbolic." This applies factory-WIDE — to the in-loop autoresearch law-discovery
kernel (`make discover → compress → prove`) AND to leanmill (one instantiation), AND to out-of-loop tools.
This seam records the durable boundary so it is not relitigated each time it resurfaces.

## Eigenquestion

> Across the WHOLE factory (autoresearch law discovery + leanmill + out-of-loop), where does tighter
> neural↔symbolic coupling add capability — vs (a) proposer/search strength we can add safely but is not a
> new boundary, or (b) a fusion that collapses the four hard boundaries and the zero-trust moat?

## Verdict — one boundary, two directions, applied to every substrate

The factory is a socio-symbolic scaffold: neural PROPOSERS (the LLM mutator in `discover`; the symbolic-
regression search in `compress`; the LLM leaves + conjecture/specialize/generalize/falsify in leanmill)
are STRICTLY SEPARATED from deterministic VERIFIERS + GATES + LEDGERS (the compress fitter, holdout tests,
the Lean kernel, `run_anti_laundering_kernel`/MNC/statement_integrity, the role-separated judge, the
append-only ledgers). The boundary is between those two columns.

**Direction A — neural in the PROPOSER / SEARCH column, loosely coupled + gated. The factory ALREADY is
this; upgrades here are SAFE but are proposer/search strength, not a new boundary.**
 - LAW DISCOVERY (highest-leverage instance): `compress` is deterministic symbolic regression today, which
   combinatorially explodes on hard substrates (Navier–Stokes). A neural-guided symbolic-regression engine
   (PySR + neural prior, or a FunSearch/AlphaEvolve-style learned prior over expression trees, trained
   OFFLINE on the discover/compress/prove ledgers) guides the search toward compressible forms WITHOUT
   touching the gates — the symbolic fitter + holdout + Lean prover stay the final arbiters. This is the
   single most useful neural add in the whole factory, precisely because the search there is hardest.
 - LEANMILL: a learned move-SELECTION prior / a better leaf (fine-tuned tactic predictor under the
   unprovisioned `deepseek-prover`/`leancopilot` slots). Leaf/search strength under existing slots.
 - Every such upgrade is "train a better proposer/search heuristic on our own ledgers." Sound to add
   (gated, version-pinned, arbiters unchanged), but it is the LEAF/SEARCH axis, not a missing boundary.

**Direction B — neural in the GATE / VERIFIER column: differentiable gates, learned symbolic invariants
replacing static rules, a fused core with internal gradient flow. HARD NO, factory-wide.** It collapses
the four boundaries (proposal/verification, evidence/memory, role separation, zero-trust) and makes the
gate a new self-certification / specification-gaming surface — the exact laundering vector the moat closes
(in leanmill: mollifier_rate def-edit, sorry-shell, warm-path statement-alteration; in law discovery: a
learned "is this a real law" judge would be gameable by the mutator it judges). A gate that becomes
learned/differentiable is no longer deterministic, external, or human-inspectable. The static gate IS the
moat.

**Net: nothing proposed is a new boundary.** It is proposer/search strength (sound, gated, add it where
the search is hardest = `compress`) + a moat-destroying fusion (rejected). We are not leaving BOUNDARY
capability on the table; we deliberately leave proposer talent on the table and invest in the environment
that makes any proposer reliable.

## Gated follow-ups (proposer-column only; arbiters untouched)

1. **Law discovery — neural-guided symbolic regression in `compress`** (IDENTIFIED, not yet built): a
   learned prior over expression trees guiding the compressor's search, trained offline on the
   discover/compress/prove ledgers; gated + version-pinned; the symbolic fitter + holdout + Lean prover
   remain arbiters. Highest-leverage, attacks the real NS combinatorial explosion. Queued.
2. **Leanmill — context-aware learned move PRIOR** (IMPLEMENTED 2026-06-06): extends the existing Arc-H
   calibration (`set_move_priors`/`_CALIBRATED_PRIORS`/`move_calibration.py`) from a context-FREE per-move
   rate to a per-(move, goal-feature) STRATIFIED empirical prior learned offline from the
   `solver_lane_attempts.db` + frontier_triage features. Only changes move ORDERING — the kernel still
   ratifies, so a bad prior wastes budget but can NEVER launder a closure. Gated, default-OFF, A/B-able
   against the flat Beta-prior. See `solver/move_prior_context.py`.

## Falsifier

A learned proposer/search prior beats the current heuristic on the substrate's DISCRIMINATING metric
(compress: compression ratio / discovery rate; leanmill: `closed_or_rung@budget`) — A=B-style, base-rate
> 0, pos/neg controls through one code path — AND no gate is EVER made differentiable/learned (the
verifiers/gates/ledgers stay static, external, deterministic). No lift over the existing calibration ⇒
even the safe follow-ups are dead. Any move toward a learned gate ⇒ moat breach, revert.

## Decision

Build NO fusion engine and NO learned/differentiable gate, anywhere in the factory. Add neural ONLY in the
proposer/search column, offline-trained on our own ledgers, gated + version-pinned, arbiters unchanged —
prioritizing `compress` (where search is hardest). The leanmill context-aware move-prior ships now as the
first instance (default-OFF, A/B-gated); neural-guided symbolic regression in `compress` is queued behind
the unmeasured-lift backlog. Not a multiplier — a calibrated efficiency gain that preserves the moat.
