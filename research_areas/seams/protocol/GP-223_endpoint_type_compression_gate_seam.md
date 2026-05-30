# GP-223 — Endpoint-Type Compression Gate

> **Seam metadata** · `seam_id:` GP-223 · `track:` protocol · `status:` open - opened 2026-05-06 PM · `last_updated:` 2026-05-08


**Status:** open *(inferred 2026-05-08 — needs operator review)*

## Status

open — opened 2026-05-06 PM

## ID

GP-223

## Eigenquestion

When typed_endpoint_pack invokes the LLM to patch a CANNOT-PATCH
endpoint field, can a deterministic pre-check identify cases where
the field is **extensionally equal to a projection of a carried
source receipt** — and discharge it by synthesizing a projection
constructor instead of asking the LLM to write fresh PDE estimate
work?

## Empirical motivation

NS Track B Codex session, 2026-05-06 PM. The operator pushed against
Codex's drift toward over-weighting source-provenance hygiene (because
recent failures were tautology/source-substitution class). The
reframe forced a target-function check that exposed a duplicate:

> capacity_of_macroscopic_clock_sources is extensionally the same
> inequality as P.phase.parabolic_low_high_capacity from the
> carried PhaseLatencyControlGramianReceipt. So the duplicate hard
> field can be discharged by the phase receipt already inside the
> reserve bridge, while the true PDE burden remains instantiating
> that phase receipt honestly.

This is a class of failure: typed_endpoint_pack treats every
top-workmap field as fresh PDE work because it does not check
whether the field's exact type is reachable as a projection of an
already-carried receipt. The rule has been added to the RD mandate
already. This seam scopes the deterministic mechanization.

## Problem Statement

`typed_endpoint_pack.py` runs four patch classes
(TRANSITIVITY_ADAPTER / BRANCH_WISE_FALSIFIER /
SOURCE_PROVENANCE_BRIDGE / INSTANCE_WITH_EVIDENCE) on each
CANNOT-PATCH endpoint. None of them currently run endpoint-type
compression as a pre-check. When the field is extensionally
equivalent (after projection) to a carried source object, the
typed_endpoint_pack:

1. Burns LLM tokens trying to write a fresh proof
2. Either succeeds (LLM finds the projection by coincidence — happy
   case but token-wasteful) or fails with CANNOT-PATCH (
   typed_endpoint_failure_log adds another `unverifiable_other` row)
3. Loses information: the projection structure that COULD have
   discharged the obligation is invisible to the failure analysis

The compression check is a mathematical type-equivalence query.
Lean has the machinery to answer it (`exact?`, `decide`, type-class
unification on the goal). What's missing is the wiring inside
typed_endpoint_pack.

## Proposed Architecture

A new gate in the typed_endpoint_pack flow, executed BEFORE the
four LLM patch classes:

```
typed_endpoint_pack invocation:
  ↓
  for each CANNOT-PATCH endpoint:
    [NEW] EndpointTypeCompressionGate.try_close_by_projection(...)
      ↓ if SUCCESS: synthesize projection constructor; emit
        success record; SKIP LLM patch
      ↓ if FAILURE: proceed to existing 4-class LLM patch flow
  ↓
  log results
```

### Layer 1 — Heuristic pre-check (cheap, deterministic, no Lean call)

For each carried source object `s` in the obligation, check whether
the endpoint field's NAME and TYPE-FRAGMENT match a known projection
pattern:

- Parse the endpoint's declared type (string-level, regex)
- Parse each carried source object's type
- Check structural-name match: does the endpoint's name appear as a
  field accessor of the source's type? (e.g.,
  `capacity_of_macroscopic_clock_sources` matches
  `s.phase.parabolic_low_high_capacity` via a path of accessors)
- Check type-fragment overlap: do the inequality structure
  (`a ≤ b` with same outer shape, same Lean-type for `a` and `b`)
  match after macro substitution?

If both checks pass with high confidence, attempt Layer 2.

### Layer 2 — Lean type-equivalence query (expensive, deterministic)

Run a candidate projection constructor through `lake env lean`:

```lean
-- candidate constructor
noncomputable def {endpoint_name}_by_projection
    (s : {source_type}) : {endpoint_type} :=
  s.{path}
```

If `lake env lean` accepts it: success — emit the projection
constructor as the patch, skip LLM. If `lake env lean` rejects:
the heuristic guess was wrong; fall through to the LLM patch flow.

### Layer 3 — Post-hoc detector (`endpoint_double_invoice` damage signal)

Independent of the gate: after typed_endpoint_pack produces a
verified patch via LLM, an audit step runs the same compression
check retroactively. If the verified patch turns out to be
extensionally equivalent to a projection that the gate could have
synthesized: emit `endpoint_double_invoice` damage signal at INFO
severity. Builds a corpus for "we should have caught this earlier"
events that informs whether to tighten Layer 1's heuristics.

## Scope

**Covers:**
- New gate module `src/ztare/gates/endpoint_type_compression_gate.py`
- Wiring into typed_endpoint_pack.py BEFORE the 4-patch-class flow
- Layer 1 (heuristic) implementation as v0; Layer 2 as v1
- Damage signal kind `endpoint_double_invoice` (already reserved
  in `org/signals/SIGNAL_KINDS.md`)
- F-row recording when projection closes an endpoint (so we can
  measure how often the gate fires)

**Does not cover:**
- Cross-substrate generalization (the projection rule is
  formulated for Lean obligations with carried receipts; not
  obvious how it generalizes to non-Lean substrates)
- Auto-discovery of projection paths beyond direct field accessors
  (deferred to v2 — would require more sophisticated AST analysis)
- The dual case: when the endpoint's RHS is the projection target
  (currently scoped only to LHS-projection cases per the
  motivating example)

## Implementation sketch

```python
# src/ztare/gates/endpoint_type_compression_gate.py

@dataclass
class CompressionCandidate:
    source_object: str           # name of carried source receipt
    projection_path: list[str]   # accessor chain (e.g., ["phase", "parabolic_low_high_capacity"])
    confidence: float            # heuristic match score 0..1


def find_compression_candidates(
    endpoint: EndpointSpec,
    carried_receipts: list[ReceiptSpec],
) -> list[CompressionCandidate]:
    """Layer 1: heuristic name + type-fragment matching."""
    ...


def try_close_by_projection(
    endpoint: EndpointSpec,
    carried_receipts: list[ReceiptSpec],
    *,
    project_dir: Path,
    timeout_seconds: int = 30,
) -> CompressionResult:
    """Run Layer 1 + Layer 2. Return (patch_text, source_obj, path)
    if a projection constructor compiles; else None."""
    candidates = find_compression_candidates(endpoint, carried_receipts)
    for cand in sorted(candidates, key=lambda c: -c.confidence):
        constructor_text = synthesize_projection_constructor(endpoint, cand)
        if lake_compiles(constructor_text, project_dir, timeout=timeout_seconds):
            return CompressionResult(
                closed=True,
                patch_text=constructor_text,
                source_object=cand.source_object,
                projection_path=cand.projection_path,
            )
    return CompressionResult(closed=False)
```

## Why this is non-trivial

1. **It applies the Compress leg of ZTARE reflexively to typed_endpoint_pack itself.** The pack was treating each endpoint as a fresh problem; the gate is a Compress operator that asks "is this endpoint already discharged by something we're carrying?"

2. **It captures a class of operator-inception that's mechanizable.** The reframe pattern (operator pushes Codex against drift toward one failure class) is GP-102's territory but happens repeatedly in NS Track B. Mechanizing the result of this specific reframe leaves operator attention free for higher-leverage moves.

3. **Layer 3 (post-hoc detector) provides empirical ROI feedback.** We can measure how often the gate would have fired by running Layer 3 retrospectively on the existing typed_endpoint_failure_log. That gives an honest before-shipping estimate of leverage.

## Connection to other seams

- **GP-217** Act-and-flag scope (Codex/RD authority around closure attempts) — this seam expands what "act" looks like for typed_endpoint_pack.
- **GP-220** Reflexive Primitive ROI Telemetry — once GP-223 ships, its engagement_rate / hit_rate / action_rate flow into the GP-220 scorecard.
- **GP-216 v5 vocabulary** — the rule maps to `core_05 Canonical Form & Invariance` (per GP-216e). Concretely: project to the canonical form (the carried receipt's type) before treating as new.
- **typed_endpoint_failure_log.jsonl** — Layer 3 reads this retrospectively; the live pack run feeds this as before-LLM-attempt enrichment.

## Honest failure modes

1. **Layer 1 false positives.** Heuristic name-matching could flag endpoints that aren't actually projections (e.g., two unrelated capacity fields with similar names). Layer 2's `lake env lean` check is the safety net — if the synthesized constructor doesn't compile, we fall through to LLM.
2. **Layer 2 false negatives.** Some real projections may need non-trivial reasoning that bare `s.path` won't capture (intermediate lemmas, type-class inference details). Won't catch those; they fall through to the LLM patch flow as today. Acceptable for v0.
3. **Compute cost of Layer 2.** Each `lake env lean` invocation is ~2-5 seconds. With ~10 carried receipts and ~3 candidates each, that's ~60-150 seconds per CANNOT-PATCH endpoint. Mitigation: timeout per candidate at 30s; bail after first compile. Layer 1 should rank candidates so we hit the right one early.
4. **The motivating example was 1 substrate (NS Track B).** If the endpoint-projection pattern is rare outside NS, the gate is decorative. Mitigation: ship the post-hoc detector (Layer 3) FIRST; ship Layer 1+2 only when post-hoc shows ≥3 events across ≥2 substrates.

## Future work

- v2: extend to cross-receipt projections (the path crosses multiple carried receipts; e.g., `s.phase.parabolic` then `from_phase(...)` constructor)
- v3: transformer-based projection-path proposer when heuristics + naïve unification fail
- Lean tactic: a `by endpoint_type_compress` tactic that runs the same logic at proof-time, reusable in non-typed_endpoint_pack contexts

## Status of work

- ✅ Rule added to RD mandate (Codex shipped 2026-05-06 PM)
- ✅ Damage signal kind `endpoint_double_invoice` reserved in
  `org/signals/SIGNAL_KINDS.md`
- ✅ This seam authored (architectural commitment + scope)
- ⏸ Layer 3 post-hoc detector — implement first to validate
  empirical leverage
- ⏸ Layer 1 heuristic + Layer 2 lake check — ship after Layer 3
  shows ≥3 events across ≥2 substrates
- ⏸ Reflexive primitive catalog entry — **DEFERRED, possibly NOT
  catalog-worthy** (operator review 2026-05-06 PM). The 8 existing
  catalog entries are all abstract pattern classes (Compress applied
  to a class of thing). Endpoint-Type Compression is a specific
  gate, not a generalizable pattern. Promotion to the catalog
  requires a 2nd cross-substrate instance that proves the
  Carried-Context Compression abstraction generalizes — e.g., a
  non-Lean substrate where some output is extensionally a
  projection of a carried input and the apparatus was treating it
  as fresh work. Until that observation, GP-223 stays a concrete
  gate seam; the catalog stays at 8 primitives.
