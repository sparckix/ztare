"""Anytime-valid (peeking-safe) A/B gate — Borrow C (#40), from the #36 ATP borrow-mining.

leanmill's lift tests are run-as-you-go with the operator inspecting them mid-run and deciding whether
to flip a default (ZTARE_AGENTIC_LEAF, cascade-vs-DAG, #28 calibration). That is OPTIONAL STOPPING WITH
PEEKING — the exact setting that inflates type-I error in a fixed-horizon test, and the live cause of the
REVERTED Barrington invent-mode lever ("P1 invent lost = variance at n=1") and the SVD single-attempt
0.375 that was pure variance. This module is the machine-checkable form of the project's own discipline
("a negative is inadmissible without calibration / n=1 is non-probative"): a confidence SEQUENCE on the
paired A−B closure difference that is valid at EVERY n SIMULTANEOUSLY (Ville's inequality on a betting
martingale, Waudby-Smith & Ramdas). The gate FLIPS a default only when the sequence excludes 0; otherwise
the honest verdict is "not_yet — keep running". Self-calibrated: the false-flip rate under the null is
Monte-Carlo-verified ≤ α (run `python -m ztare.leanmill.sequential_ab`).
"""
from __future__ import annotations


class SequentialABGate:
    """Paired anytime-valid A/B gate. Feed `(a_i, b_i)` ∈ {0,1} per target (did arm A close, did arm B
    close, on the SAME target); `verdict()` ∈ {"A>B","B>A","not_yet"} is valid at every n by Ville.

    Mechanism: shift the paired difference d_i=a_i−b_i to y_i=(d_i+1)/2 ∈ {0,0.5,1}; A=B ⟺ E[y]=0.5.
    For each candidate mean m on a grid, run a two-sided MIXTURE betting martingale K_n(m)=avg_λ Π(1±λ(y−m));
    by Ville, P(sup_n K > 2/α) ≤ α/2 per side ⇒ rejecting m when K>2/α gives a (1−α) confidence sequence
    {m not rejected}. The gate fires only when that whole interval lies strictly on one side of 0.5."""

    def __init__(self, alpha: float = 0.05, grid: int = 101, lams: "tuple[float, ...]" = (0.25, 0.5, 0.9)):
        self.alpha = alpha
        self.thr = 2.0 / alpha                       # two-sided: α/2 per side via Ville
        self.grid = [i / (grid - 1) for i in range(grid)]
        self.lams = lams
        self.cap = {m: {1: [1.0] * len(lams), -1: [1.0] * len(lams)} for m in self.grid}
        self.rejected = {m: False for m in self.grid}
        self.n = 0

    def update(self, a: int, b: int) -> None:
        y = ((a - b) + 1) / 2.0                       # {0, 0.5, 1}
        self.n += 1
        for m in self.grid:
            if self.rejected[m]:
                continue
            for sgn in (1, -1):
                caps = self.cap[m][sgn]
                for j, lam in enumerate(self.lams):
                    caps[j] *= (1.0 + sgn * lam * (y - m))   # |λ|<1, |y−m|≤1 ⇒ factor>0
                if sum(caps) / len(caps) > self.thr:
                    self.rejected[m] = True
                    break

    def cs(self) -> "tuple[float, float]":
        surv = [m for m in self.grid if not self.rejected[m]]
        if not surv:
            return (0.5, 0.5)
        return (min(surv), max(surv))

    def verdict(self) -> str:
        lo, hi = self.cs()
        if lo > 0.5:
            return "A>B"
        if hi < 0.5:
            return "B>A"
        return "not_yet"


def ab_gate(a_outcomes: "list[int]", b_outcomes: "list[int]", alpha: float = 0.05) -> dict:
    """Batch convenience: feed two aligned closure lists (paired by target), return the verdict + CS.
    `not_yet` ⇒ NOT enough evidence to flip a default (the honest answer under peeking)."""
    g = SequentialABGate(alpha=alpha)
    for a, b in zip(a_outcomes, b_outcomes):
        g.update(int(a), int(b))
    lo, hi = g.cs()
    return {"verdict": g.verdict(), "n": g.n, "cs_lo": round(lo, 3), "cs_hi": round(hi, 3),
            "a_rate": round(sum(a_outcomes) / max(1, len(a_outcomes)), 3),
            "b_rate": round(sum(b_outcomes) / max(1, len(b_outcomes)), 3)}


def _mc_calibrate(trials: int = 600, N: int = 120, alpha: float = 0.05) -> dict:
    """Monte-Carlo calibration (the instrument is inadmissible until this passes): under the NULL
    (A,B same rate) the gate must FALSE-FLIP (ever say A>B or B>A while peeking at every n) at rate ≤ α;
    under a real gap it must eventually flip the right way (power). Uses random — Python only."""
    import random
    rng = random.Random(20260605)
    # NULL: both arms p=0.5, peek every n, count trials that EVER flip
    false_flips = 0
    for _ in range(trials):
        g = SequentialABGate(alpha=alpha)
        flipped = False
        for _i in range(N):
            g.update(1 if rng.random() < 0.5 else 0, 1 if rng.random() < 0.5 else 0)
            if g.verdict() != "not_yet":
                flipped = True
                break
        false_flips += int(flipped)
    null_rate = false_flips / trials
    # POWER: A=0.65, B=0.35, count trials that flip to A>B by N
    pwr = wrong = 0
    for _ in range(trials):
        g = SequentialABGate(alpha=alpha)
        for _i in range(N):
            g.update(1 if rng.random() < 0.65 else 0, 1 if rng.random() < 0.35 else 0)
            v = g.verdict()
            if v == "A>B":
                pwr += 1
                break
            if v == "B>A":
                wrong += 1
                break
    return {"alpha": alpha, "null_false_flip_rate": round(null_rate, 4), "must_be_leq_alpha": null_rate <= alpha,
            "power_A>B": round(pwr / trials, 3), "wrong_direction": round(wrong / trials, 4)}


if __name__ == "__main__":
    import json
    r = _mc_calibrate()
    print(json.dumps(r, indent=2))
    print("CALIBRATION", "PASS — anytime-valid (false-flip ≤ α under peeking)" if r["must_be_leq_alpha"]
          else "FAIL — false-flip exceeds α; tune thr/lams")
