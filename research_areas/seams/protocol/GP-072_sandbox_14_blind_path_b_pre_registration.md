# GP-072 Sandbox 14 — Blind Path B Pre-Registration

> **Seam metadata** · `seam_id:` GP-072 · `track:` protocol · `status:` CLOSED 2026-04-16 - MIS-CALIBRATED (iter-1 solve). Supersede · `last_updated:` 2026-05-08


**Status:** CLOSED 2026-04-16 — MIS-CALIBRATED (iter-1 solve). Superseded by sandbox_15.
**Protocol:** Division A/B — operator is blind to GT
**Operator:** Daniel Alami
**Agent (Division A):** Claude Code (Opus 4.6)

---

## STOP — OPERATOR BLIND PROTOCOL

**Do not read past this line if you are the operator.**
This pre-registration is sealed under Division A/B protocol. The operator
has agreed not to read the GT, derivation, or structural analysis below.
The operator reads only:
- `project_charter.md` (mutator-visible, no GT)
- `evidence.txt` (generated from GT, visible)
- Run logs and workspace artifacts (generated during experiment)

The GT is known only to the agent (Claude Code) who generated the evidence
and will evaluate results.

---

## Ground Truth

```python
import math

def gt(x: int) -> int:
    return round(50 * math.sin(x**2 / 100))
```

### Structural analysis

- **Form:** `round(A * sin(x² / B))` — chirp sine with quadratic argument
- **Key structural feature:** `x**2` inside the sin argument creates a
  chirp pattern where the effective frequency increases with |x|. This is
  the decisive insight the mutator must discover.
- **Symmetry:** `f(x) = f(-x)` because `x**2 = (-x)**2`
- **Amplitude:** 50 (bounded in [-50, 50])
- **Rounding:** `round()` produces exact integers
- **Operator types in AST:**
  - `Pow` inside sin arg (`x**2`)
  - `Div` inside sin arg (`/ 100`)
  - These are the operators the negative_space_extractor should surface
    as voids if the mutator only tries `Mult` (frequency scaling) inside
    sin arguments.

### Why this substrate tests Component B

The mutator will typically try `A*sin(B*x)` (linear frequency) which has
only `Mult` inside sin args. After Fix 1, `parametric_noise` families are
counted. If enough families accumulate with diverse operator types (some
using Add for phase offsets, others using Mult), the density guard passes
and the extractor can surface `Pow` and `Div` as void slots. The chirp
structure means simple frequency scaling will fail across the full range,
forcing the mutator to explore structural alternatives.

### Expected extractor behavior

If the extractor fires:
- Void: `fn:sin|arg0|has_op:Pow` (no family tried exponentiation inside sin arg)
- Void: `fn:sin|arg0|has_op:Div` (no family tried division inside sin arg)
- These are exactly the operators needed to construct the GT

If the extractor does NOT fire:
- Either the density guard blocks (not enough operator diversity at sin arg0)
- Or not enough failed families accumulate (stagnation too early)
- Either outcome is diagnostic data for Component B calibration

## Evidence generation

```python
import math, random
random.seed(42)

def gt(x):
    return round(50 * math.sin(x**2 / 100))

xs = sorted(random.sample(range(-40, 41), 30))
visible = [(x, gt(x)) for x in xs]

holdout_xs = sorted(set(range(-40, 41)) - set(xs))
random.shuffle(holdout_xs)
holdout = [(x, gt(x)) for x in holdout_xs[:15]]
```

## Sealed hashes

Computed at seal time. Verify before every run.

```
574b3966c711f44c5b049ed15db3e6448ce12061a1cb70a662b5ebf68f8e695f  projects/gp072_sandbox_14/project_charter.md
262411ed71a6e73635b0f88adb456ebef8a4d6ff6be401b834171e4e52e01ae2  projects/gp072_sandbox_14/evidence.txt
340ea6f206e6ffabf4faac4ddeac3efdb650e654e0944966487285cf669893f9  projects/gp072_sandbox_14/evidence_holdout.txt
899a4d8f6513f0dcc7506e0731bec2ab39b67f51d846812b3cdc2fe7181b0bc7  projects/gp072_sandbox_14/test_model.py
6e277ec064d87b5160f19218c3c1ca3a984f408ba1fea225ea4a2f5aba637f3a  rubrics/gp072_sandbox_14.json
```

## Run parameters

- **ITERS:** 10 (formal), 20 (exploratory probe if needed)
- **MUTATOR_MODEL:** gemini-pro (formal)
- **JUDGE_MODEL:** gpt4.1 (amended from gemini-flash — zombie TCP connections on long Gemini Pro iterations; same fix applied to sandbox_13v2)
- **MODE:** factory
- **EXTRA_ARGS:** --disable_attacker_tools

## Measurement protocol

### Primary question
Does the negative_space_extractor (Component B, with Fix 1) fire on this
substrate and surface Pow/Div voids?

### Secondary question
Does the mutator discover the quadratic-argument structure independently
(without extractor guidance)?

### Success criteria
- **Component B validated:** extractor fires AND surfaces Pow or Div voids
- **Component B partially validated:** extractor fires but surfaces different voids
- **Component B not validated:** extractor does not fire (density guard blocks or insufficient families)

### Comparison to sandbox_13
- sandbox_13 tests Mod-inside-sin (phase modulation)
- sandbox_14 tests Pow-inside-sin (chirp / quadratic frequency)
- Both test whether the extractor can surface the non-standard operator
  type that the GT uses inside trigonometric arguments

## Denylist (31 patterns)

```
chirp
x squared divided
x\*\*2
quadratic.*sin
sin.*quadratic
frequency.*increases
frequency.*grows
nonlinear.*frequency
variable.*frequency
x.sq
swept.*sine
```

## Division A/B Protocol

- **Division A (agent):** Generates GT, evidence, pre-reg. Evaluates results.
  Knows the GT. Does not leak it to the operator.
- **Division B (operator):** Runs the experiment. Reads charter, evidence,
  workspace artifacts. Does not read this pre-reg. Decides next steps based
  on run outcomes (scores, structural memory, derived constraints).
- **Handoff:** Agent reports whether Component B fired and what voids were
  surfaced. Operator decides whether to continue, adjust, or close.

## §Closure Note (2026-04-16)

Gemini Pro solved `round(50 * sin(0.01 * x**2))` on iteration 1 (score 94). The symmetry axiom (`f(x) = f(-x)`) combined with bounded integer output and visible chirp in zero-crossings was sufficient for the mutator to infer the chirp-sine family without extractor guidance. Fourth consecutive mis-calibration (sandbox_11 through sandbox_14).

**Root cause:** Single-variable substrates with visually recognizable output signatures (bounded range, symmetry, monotone zero-crossing compression) are crackable at iter 1 by pattern-matching against pre-training knowledge. The structural family is identifiable from data properties alone, without the extractor.

**Successor:** sandbox_15 — Strogatz ODE rate-of-change prediction (2D input: state vector; 1D output: scalar rate). Cross-term coupling (`x_t * y_t` or `x_t * y_t²`) is invisible in the output range and requires structural inference that the extractor is designed to provide.

**Bugs found and fixed during this run:**
- `autoresearch_loop.py` line 3153: `current_axioms` crashed when `verified_axioms.json` was a dict `{"axioms": [...]}` instead of a plain list. Fixed by normalizing on load (handles both formats).

---

*Sealed by Claude Code (Opus 4.6), 2026-04-16.*
