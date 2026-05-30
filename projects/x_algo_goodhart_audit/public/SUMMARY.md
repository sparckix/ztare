# X ranking: a structural Goodhart audit

Public digest of the `x_algo_goodhart_audit` substrate probe. The
iteration logs and debate transcripts stay internal; this is the
honest result.

## The claim

The open-sourced X ranking has a structural asymmetry in
`offset_score()` (in `ranking_scorer.rs`): every candidate with a
zero-or-positive combined engagement score receives the same fixed
positive additive boost (`NEGATIVE_SCORES_OFFSET`), applied after the
transformer prediction and weighting layer. Because candidates are
scored in isolation (during inference each candidate attends only to
the user context, never to other candidates, with no cross-candidate
normalization), no learned "quality" prediction or continued
retraining can counteract a systematic additive bias added downstream
of the model.

## What this is and is not

- A code-grounded structural argument about the published algorithm,
  traced to the specific function and the no-cross-normalization
  design.
- Not an empirical measurement of live feed outcomes. The harm chain
  is argued from the code path, not from production telemetry that is
  not available.

## Status

A completed substrate probe with a falsifiable, mechanism-anchored
thesis. Single operator, no privileged access; the value is the
located mechanism and the explicit boundary of what the code can and
cannot show.
