# The plain-sight 10x — it was never the portal (2026-07-20)

## The finding, in one line

The champion cannot model **energy-bar refill**, that single missing operator accounts for **83% of the entire residual** (510 of 617 wrong rows; 495 are specifically a missed refill), the system **already proposed the operator 15 times**, and **all 106 operator proposals in this project's history have an adoption rate of 0%.** The bottleneck was never the portal, never exploration, never the science — it is a dead operator-adoption pipeline.

## The measurement (against the current 16,378-row bank)

- Champion (`test_model.py`) wrong on **617 rows**. (The "14,707/14,707 exact" from earlier receipts was on *law-scored* rows with env-frames excluded; the real per-transition picture is far worse once level-3 evidence is banked.)
- **510 / 617 (83%)** have an energy-bar (rows 61-62) miss. **495** are specifically the champion predicting the bar *empty* (color 3) where the environment shows it *charged* (color 11).
- Missed-cell distribution by row-band: band 56 (contains the bar) = **47,983 missed cells**, vs 8,636 for the next-largest band. The bar dominates the error mass ~4:1.
- Refill events in-bank: **497**, across all four actions — a real, heavily-witnessed mechanic, not a rare edge case.
- The exotic **portal transport** that has been the loop's "frontier residual" since 2026-07-12, and that I chased in file 10, is **27-30 rows** — an order of magnitude smaller than the refill everyone walked past.

## Why nobody saw it

Two compounding causes, both now understood:
1. **The loop wasn't banking these transitions.** The acquisition bug (fixed this session: play-under-unresolved-identification + witness-gap steering) meant the loop only ever played where its model was already right. Refill events happen in regions/times the champion mispredicts, so they were under-witnessed — the dominant residual was statistically invisible.
2. **Fixation on novelty.** The portal produced a dramatic 1,421-cell relayout and a "transport" label; it captured attention (mine included). The refill is boring — a strip of cells flipping 3→11 — so it was never characterized, even though it is 16× more of the error mass.

## The actual bottleneck (confirmed)

The system is not failing to *find* the fix. It found it 15 times:

```
region_rewrite(region=[35,3,62,63], colors=[3,5,8,9,11,12]) ... disp: rejected
region_rewrite(region=[20,3,62,63], ...)                     ... disp: rejected
local_recolor(region=[61,13,62,63], mapping over [3,8,11])   ... disp: open
```

15 energy-bar-region operator proposals exist in `operator_proposals.jsonl`. Dispositions: 8 rejected, 7 open. **Adopted: 0. Across all 106 proposals in the ledger: adopted 0.**

This is the "row 3 gap" named in the very first review (`02_meta_governance_review.md`): the build→register→wire→first-fire pipeline for operator/grammar proposals has no owner, so the system can diagnose its own dominant residual, propose the exact operator, and never adopt it. **A general-purpose skill-acquisition engine that cannot extend its own grammar is pattern-matching inside a frozen vocabulary, not acquiring skills.**

## What this reframes

The week of "stuck on level 3" was not a hard-science wall. It was: (a) an acquisition bug that hid the dominant residual (fixed this session), plus (b) a dead adoption pipeline that prevents the trivially-proposed fix from entering the model (open). Both are harness defects, not intelligence limits. The portal is real and will need its own operator eventually — but it was a red herring for the week's stall.

## The one decisive move (not more apparatus)

Own the adoption pipeline for **one** operator, end-to-end, and watch 83% of the residual close. Two admissible routes, in order of cleanliness:

1. **Let the codex leaf close it, now that it can.** The mutator writes arbitrary Python (`step(state,action,t)`) — it does not need a grammar operator; it needs the refill *counterexample* in its briefing (leaf-computable evidence, not a mechanism hint). With acquisition fixed, the refill rows are now banked and are the dominant residual; the in-flight grind is the honest test of whether the leaf induces the recharge. Watch the next few cycles' `visible_replay_exact` and wrong-row count.
2. **If the leaf still doesn't close it**, the operator-implement leg (`operator_implement.py`) must be given a caller that builds one `open` card into a candidate, runs the planted-synthetic acceptance test + strict-improvement gate, and promotes on pass. That is the single highest-leverage harness change left — it converts the 0% proposal-adoption rate into a live self-extension loop, which is the actual general-purpose claim.

The trigger for the refill (what causes 3→11) is deliberately left uncharacterized here: 490/497 refills occur over generic floor, so it is a genuine induction problem — the leaf's job, not the conductor's. Hand-authoring it would be exactly the forbidden conductor-authored law.
