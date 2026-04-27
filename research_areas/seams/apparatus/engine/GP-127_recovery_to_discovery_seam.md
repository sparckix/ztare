# GP-127 — Recovery to Discovery: Three Capability Upgrades

**Status:** IMPLEMENTED — backtested on A000009
**Opened:** 2026-04-23
**Category:** Apparatus / Engine / Discovery Capability
**Trigger:** Survey hit rate 0/3 on unknown substrates. Panel verdict: engine is a recovery instrument, not yet a discovery engine.

## The Diagnosis

After GP-126 sky survey (3 unknown substrates, 0 discoveries):
- S1 (abundant density): compressed in-window but fails extrapolation
- S2 (Mertens normalized): correct null (incompressible)
- S3 (prime gaps normalized): correct null (incompressible)

Panel identified three structural gaps between recovery and discovery:
1. Grammar is fixed — engine can't learn from its own successful compressions
2. Representation is limited — only 3 transforms (log, reciprocal, diff)
3. Grammar self-expansion exists (GP-115) but suggestions aren't tried

## The Debate (2026-04-23)

**Panel:** The engine is a recovery instrument, not a discovery engine.
**Operator:** Invert. How do we cross the gap? Kepler to Newton.
**Panel (initial):** Three research directions, estimated weeks to months.
**Operator:** You're strawmanning. These are engineering, not research.
**Panel (corrected):** Yes. All three are implementable today.

Implementation estimates after inversion:
| Improvement | Initial estimate | Actual |
|---|---|---|
| Cross-substrate primitive library | "needs library to grow" | 2 hours |
| Extended representation transforms | "research problem" | 1 day |
| Grammar self-expansion wiring | "buildable now" | Already existed (GP-115) |

## What Was Built

### 1. Cross-Substrate Primitive Library (GP-127)

**File:** `src/ztare/fit/primitive_library.py`
**Config:** `config/primitive_library.json`

- Bootstrapped with 9 primitives from past successful compressions
  (Hardy-Ramanujan, Vaughan, Lucky density, Meinardus, Ulam reciprocal,
  geometric decay, Robin bound, exp-sqrt, inverse-log correction)
- Loaded FIRST in compress_champion before fixed grammar templates
- Auto-saves winning forms after each successful compression
- Backtested: A000009 run loaded 9 library templates, found 7 gate-passing
  forms, auto-saved the winner back to library

### 2. Extended Representation Transforms

**File:** `src/ztare/fit/post_underidentified.py`

Added 5 new transforms to observable rotation:
- `diff(log(z))` — log-differences (catches geometric/multiplicative)
- `cumavg(z)` — running average (smooths fluctuations)
- `z*x` — un-normalizes ratios
- `z^2` — quadratic (variance structure)
- `sqrt(|z|)` — compresses large values

Total transforms: 3 (existing) + 5 (new) = 8

### 3. Grammar Self-Expansion (Stage 4)

**File:** `src/ztare/fit/compress_champion.py`

Wired GP-115 `residual_grammar_expander` as Stage 4 of compression:
- After Stages 1-3 all fail to find gate-passing form
- Compute residuals of best-fitting template
- `suggest_from_residuals()` diagnoses residual shape
- Suggested templates are tried with full gate harness
- If any pass gates, they're added to results

Pipeline is now: Stage 1 (additive) → Stage 2 (compositional) →
Stage 3 (periodicity) → Stage 4 (residual-driven expansion)

## Backtest

A000009 (partitions into distinct parts):
- Library loaded 9 bootstrapped templates
- 41 total templates tried (9 library + 22 stage1 + 13 stage2)
- 7 gate-passing forms found
- Best: `a*sqrt(n) + b*log(n) + c/n + d/n^2 + e` (BIC -29015)
- Winner auto-saved to primitive library
- No regressions vs. prior runs

## What This Enables

The engine now has:
- **Memory across substrates** — forms that worked before are tried first
- **More representations** — 8 transforms instead of 3
- **Self-diagnosing grammar** — when templates fail, residual shape
  generates new candidates mechanically

Whether these cross the recovery-discovery boundary is an empirical
question. The next survey batch tests it.

## Checkbox

- [x] primitive_library.py
- [x] Bootstrap library from 9 past compressions
- [x] Wire library loading into compress_champion
- [x] Wire auto-save of winners
- [x] Add 5 extended transforms to post_underidentified
- [x] Wire Stage 4 grammar self-expansion
- [x] Backtest on A000009 (no regressions)
- [ ] Re-run survey S1/S2/S3 with upgrades
- [ ] Run new GP-126 Tier 2 targets with upgrades
