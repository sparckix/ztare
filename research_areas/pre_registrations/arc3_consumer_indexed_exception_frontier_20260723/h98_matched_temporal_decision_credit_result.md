# H98 matched temporal-decision credit result

Date: 2026-08-04

Verdict: supported offline

H98 compiled delayed task credit from two anonymous, exact-source matched
chain pairs. Every first decision was immediately `open`. In both pairs the
`advance` arm reached external attainment one decision later and the matched
`detour` arm remained externally open.

The compiler assigned:

- `advance-family`: `task_credited`, enable support `2`, preference `+1`;
- `detour-family`: `task_hazard`, hazard support `2`, preference `-1`.

Those preferences flipped the existing guarded-protocol selector from the
higher predicted-yield `detour-family` to `advance-family`. Primitive,
readout, control, and total costs were byte-for-byte unchanged between the
baseline and reranked price receipts.

Predicted-versus-observed information yield remained a separate authority.
For the shared source state, `advance` predicted `0.8` and observed mean
`0.5`; `detour` predicted `1.2` and observed mean `0.125`. The calibration
receipts explicitly set `task_credit_authorized=false`. Two high-information
open/open pairs produced no task judgment.

Negative controls refused controller-context drift, complete-choice-set drift,
and eligibility traces longer than the registered one-step lifetime. All ten
registered checks passed. The focused module plus surrounding continual-memory
and guarded-protocol suites passed `18/18`.

Evidence:

- machine result:
  `h98_matched_temporal_decision_credit_result.json`
  (`f0e12878ec48b33f37a74006aa8f4e21d835a2f3b7610bb104852fe8f522c096`);
- compiler:
  `src/ztare/common/temporal_decision_credit.py`;
- test:
  `tests/common/test_temporal_decision_credit.py`.

This establishes an anonymous synthetic one-step credit compiler and
yield-error receipt. ARC persistence, planner integration, cross-context
transport, H97 support, and benchmark improvement remain open.
