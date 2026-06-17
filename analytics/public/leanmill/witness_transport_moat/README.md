# The exogenous-compute edge — bare model vs leanmill, kernel-confirmed (only-N integer factoring)

Goal item 1: the single undeniable demonstration that leanmill does something a bare frontier model cannot, and
the kernel independently confirms it. **This writeup includes the honest correction that got us here** — the
first version of the test was flawed; the corrected version below is the real result.

## The result (clean, matched, identical instances)

Goal form: `∃ x y : ℤ, x * y = N ∧ 1 < x ∧ x < N` — given *only* the product N (a semiprime), find a non-trivial
factor. Receipt: `factoring_moat_run.json`.

| arm | closed | note |
|---|---|---|
| native cascade (deterministic Lean tactics) | **0/4** | can't construct a witness |
| **bare deepseek-chat** (pure text, no tools, no fallback) | **1/4** | closed *only* the 6-digit control; failed 16/22/26-digit |
| **leanmill `factorization` path + kernel** | **4/4** | SymPy `factorint` → `⟨p,q,…⟩` → kernel re-verifies `x·y=N ∧ 1<x<N` |

**Separation +3** — the three hard rows (16, 22, 26 digits) are *witness-only*: bare fails, leanmill factors and
the kernel confirms, on the **same** N. The 6-digit positive control (deepseek factored `225413 = 431×523`)
proves the model is live and capable of the task — so the failures are a real capability wall, not a dead
instrument. A separate probe: deepseek-**reasoner** also fails (it exhausts its entire reasoning budget,
`finish_reason=length`, returning nothing); gpt/claude APIs were down, so deepseek is the live bare baseline.

**Why this is a structural cliff, not a budget gap:** factoring a large semiprime by generating tokens is
infeasible at any model scale (there is no factoring algorithm in next-token prediction; the answer is not
pattern-derivable). More sampling / a bigger model does not close it — the Rice / one-way-function shape.

## The honest correction (kept — this is how we got the clean result)

The first attempt used the existing Pell/Kronecker/witness corpus and **overclaimed**. Measured against the
deterministic native cascade it was a clean 20/20 vs 0/20 — but native is a weak baseline. Measured against a
**strong reasoning model** (gemini-3.1-pro, no tools), that corpus is **subsumed: bare 10/11, witness 11/11,
separation +1** (`witness_vs_bare_run.json`). Two design flaws, proven:

1. **The Kronecker "factoring" rows leaked the answer.** They give *both* `x·y=N` and `x+y=S`, which is a
   quadratic (`S²−4N=(p−q)²`, a perfect square), **not** factoring. The sum hands over the solution.
2. **The fresh Pell instances had small fundamental solutions** (D=392→(99,5), etc.), and the famous large ones
   (D=61's 10-digit `(1766319049,226153980)`) are textbook-memorized.

Removing the leak (give *only* N) restores the real separation — the +3 above. The earlier
"witness-transport 12/12, an LLM cannot do this" was vs native only and is **corrected**.

## What's claimed, and what's not

- **Claimed:** on only-N integer factorization, a bare pure-text model cannot factor a 16+ digit semiprime
  (measured, with a passing control), while leanmill's exogenous-compute `factorization` path does and the
  **kernel re-verifies** the result. Verified **axiom-clean** (not merely compile-clean): leanmill's own
  `audit_axioms_subset` gate reports the 16- and 26-digit closures depend on exactly
  `{propext, Classical.choice, Quot.sound}` — no `native_decide`/`ofReduceBool`, no `sorryAx`. A wrong factor
  cannot mint a closure (the kernel rejects it).
- **Not claimed:** a general solving advantage, a benchmark SOTA, or that *no* AI system can factor — a
  *tool/code-execution-enabled* agent can run its own factorizer (architecture §line 31). The edge is that the
  **model's weights cannot**, leanmill supplies the computation, and an **independent kernel governs** it.
- **Honest scope:** small N (4 matched instances + probes); the robust findings are the **0-or-control vs
  kernel-verified** pattern and the structural argument, not a tight interval. Wider panel (gpt/claude when
  their APIs return; deepseek-reasoner already concurs) is the open follow-up.

## Reproduce
```
# leanmill arm (free) + bare arm (one API model):
WVB_OUT=factoring_moat_run.json ZTARE_LEANMILL_KRONECKER=1 PYTHONPATH=src ./venv/bin/python \
  projects/leanmill_experiments/public/witness_vs_bare_controlled.py \
  --no-fixed --factoring --bare-models deepseek-chat --bare-rows all
```
Engine path: `src/ztare/leanmill/solver/witness_transport.py` (`is_factoring_existential` + `solve_factor`,
selftest `python -m ztare.leanmill.solver.witness_transport`).
