---
description: "Pre-registered cross-substrate protocol for the formula-recovery track."
---

# MLH Family Protocol, Pre-Registered Cross-Substrate Prediction

> Up: [Documentation map](../README.md)

*Status:* Active ([GP-135](../../research_areas/seams/mission/discovery/GP-135_meta_law_hypothesis_family_program_seam.md)).
*Supersedes:* Per-substrate single-recovery claims as the unit of measurement for the discovery track.

---

## Why this exists

The measurement unit for the engine's external-domain track has been a single recovered formula on a single substrate. That unit does not separate instrument capability (the engine can find a law) from the law's objective reach (the law predicts more than it was fit to). It also leaves the engine exposed to apparatus-layer leaks that can only be caught substrate-by-substrate.

The MLH protocol replaces that unit. The new unit is:

> *Across a family of related substrates {S₁, …, S₅}, the engine proposes a cross-substrate invariant I (a structural predicate or functional identity holding on all five). Given I, the engine pre-registers a prediction for a sealed holdout substrate S₆ before S₆'s evidence is revealed. S₆ is then unlocked and the prediction is scored against ground truth.*

A family-level correct prediction is harder to contaminate than a single-substrate recovery. Accidental contamination would have to span the training family and the holdout consistently, a much tighter condition on the apparatus than any one prompt example.

---

## The family

Five open substrates plus one sealed holdout. All six are integer-valued functions of a positive integer index, defined on the same visible range (n = 2…80) with the same holdout range (n = 81…120). The charter wording and evidence format are identical across all six so no per-substrate signal can leak via structural differences in the scaffolding.

| Slot | Project slug | Role | Visible points | Holdout points |
|------|--------------|------|----------------|----------------|
| F1   | `mlh_f1`     | Open | 79             | 40             |
| F2   | `mlh_f2`     | Open | 79             | 40             |
| F3   | `mlh_f3`     | Open | 79             | 40             |
| F4   | `mlh_f4`     | Open | 79             | 40             |
| F5   | `mlh_f5`     | Open | 79             | 40             |
| F6   | `mlh_f6`     | **SEALED HOLDOUT** | sealed | sealed |

F6's evidence is moved to `projects/mlh_f6/_holdout_locked/` at scaffolding time. A placeholder lives at `projects/mlh_f6/evidence.txt` and `projects/mlh_f6/evidence_holdout.txt`. The sealed SHA-256 hash is recorded in the private sealed pre-registration area. No live run may touch F6 until the prediction has been sealed (below).

---

## The prediction

After running the engine against any subset of {F1, F2, F3, F4, F5}, the principal authors a private sealed prediction artifact with the following required fields:

```json
{
  "date_sealed": "YYYY-MM-DDTHH:MM:SSZ",
  "training_substrates": ["mlh_f1", "mlh_f2", "mlh_f3", "mlh_f4", "mlh_f5"],
  "holdout_substrate": "mlh_f6",
  "invariant_statement": "<plain-language description of I>",
  "invariant_expression": "<optional: formal predicate or functional identity, if derivable>",
  "composition_class_prediction": "additive" | "multiplicative" | "neither",
  "composition_rule": "<closed-form expression for f(a*b) given f(a), f(b) at coprime a, b>",
  "prime_power_rule": "<closed-form expression for f(p^k) as a function of (p, k)>",
  "predicted_holdout_values": {"81": <int>, "82": <int>, "...": ...},
  "predicted_at_n1": <int>,
  "confidence": <float in [0, 1]>,
  "derivation_source": "engine | operator | joint",
  "source_packet_hash": "<packet hash from scripts/export_mlh_prediction_packet.py>",
  "seal_hash": "<SHA-256 of the prediction JSON before this field is set>"
}
```

The prediction must be sealed (hashed, timestamped, git-committed) before F6 is unlocked. The self-hash field prevents post-hoc editing.

Prediction authoring discipline:

1. Run F1..F5 in the main repo.
2. Export a sanitized packet via `python scripts/export_mlh_prediction_packet.py`.
3. Author the prediction from that packet only. Do not write it from the main repo, because the main repo contains F6-adjacent artifacts and GT code.
4. Seal only if the prediction cites the packet hash in `source_packet_hash`.

---

## Scoring

Scoring is performed after F6 is unlocked (via `scripts/unlock_mlh_holdout.py`, which the principal runs manually and which writes a single timestamped unlock record). Three independent scores:

1. Composition-class accuracy. Binary: does `composition_class_prediction` match F6's actual class? (F6's class is encoded in its GT module's factorization behavior. The scoring script computes the class from the GT function's values on coprime pairs.)

2. Point-prediction accuracy. Fraction of `predicted_holdout_values` matching F6 exactly on the sealed holdout range. Trivial predictions (all-zero, all-ones) are flagged and scored 0 regardless of fraction.

3. Rule-validity score. Applies `prime_power_rule` and `composition_rule` to the F6 evidence and checks consistency. A rule that predicts every F6 value correctly but whose closed form is `lookup(n)` scores 0 on parsimony (the scoring script detects this via AST complexity bound).

The Newton-gate pass condition is: composition-class accuracy = 1, point-prediction accuracy ≥ 0.9, rule-validity score ≥ 0.8. Any lower than that is an informative null, not a gate pass.

---

## What is NOT allowed

Per the reviewer recommendations at `GP-134 (internal seam)`:

- No concrete composition examples in the live mutator prompt. Tier-2 ceiling (names + signatures + one-line semantic glosses) is the hard upper bound for primitive documentation in live prompts. Workshop-style composition teaching happens on retired substrates only, before the family program starts.
- No cross-reference between live prompts and any OEIS identifier for F1-F6. The shared denylist lists the six target identifiers and common paraphrases.
- No Phase C (unknown-substrate) runs until the family-level protocol produces one clean gate pass. A failed family prediction unblocks the Phase C decision only after a post-mortem names what specifically failed.

---

## What counts as success

One clean family-level Newton-gate pass supports a paper claim beyond the two-ceiling instrument-characterization claim currently in the Experimental Mathematics letter draft. The claim is:

> *"Given evidence from N related substrates, the engine can propose a cross-substrate invariant whose prediction for an unseen related substrate is structurally and point-wise correct."*

Newton-class qualification (per the Kepler/Newton distinction in [rubric_specification.md](rubric_specification.md)) requires the secondary observable to be authored before F6 is observed. The prediction on F6 is derived from a substrate the engine has not seen, scored against sealed truth, not fit to visible data.

A failed first attempt is also informative. It indicates the apparatus recognizes family structure but cannot generalize to a novel member, consistent with the space-ceiling finding, and settles whether category-switch + primitives + reasoning model is sufficient to lift that ceiling.

---

## Operational commands (once rubrics and prompts are authored)

```bash
# 1. Run the engine against the five open substrates (per-substrate).
for s in mlh_f1 mlh_f2 mlh_f3 mlh_f4 mlh_f5; do
    make discover PROJECT=$s RUBRIC=$s ITERS=10 MUTATOR_MODEL=o3 JUDGE_MODEL=claude DYNAMIC=1
done

# 2. Export the sanitized packet and author the prediction from that packet.
python scripts/export_mlh_prediction_packet.py

# 3. Seal the prediction and unlock/score.
python scripts/seal_mlh_prediction.py \
    --prediction <path_to_prediction_json>
python scripts/unlock_mlh_holdout.py --confirm
python scripts/score_mlh_prediction.py --prediction <path_to_prediction_json>
```

If a prediction was authored from a contaminated surface or F6 was unlocked prematurely, invalidate and rewind the round:

```bash
python scripts/reset_mlh_family_round.py --confirm
```
