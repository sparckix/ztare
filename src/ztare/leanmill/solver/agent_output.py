r"""Agent-output parsing for the leanmill SOLVER — the ONE place to extract structure from the leaf's free-text
response, so the moves stop copy-pasting `re.search(rf"{label}\s*```...")` ad-hoc. That helper (`_fenced`) was
duplicated 6× across the solver (conjecture ×4, reflection, spectral_lift, proof_margin_of_safety); this
consolidates it. Two primitives cover what the moves need:

  • `fenced_block(raw, after, lang=None)` — the first ```fenced``` block following a LABEL
    (e.g. "PROOF:\n```lean\n…```"). Drop-in for every `_fenced`.
  • `labeled_value(raw, label, allowed=None)` — a labeled inline value on one line
    (e.g. "PLAN: FALSIFY — reason"), optionally constrained to an `allowed` set.

Lives in `leanmill/solver/` (NOT `ztare/common/`, which is shared across all of ztare — validator,
research_director, fit, …): this parses the LEANMILL leaf's output specifically. The TYPED kernel-exchange
contracts stay in `leanmill/contracts/`; this is the low-level text extraction the movers share. Migrate the
scattered `_fenced` helpers here (tracked cleanup).

  python -m ztare.leanmill.solver.agent_output --selftest
"""
from __future__ import annotations

import re
from typing import Optional


def fenced_block(raw: str, after: str, lang: "Optional[str]" = None) -> str:
    """The first ```fenced``` code block following the label `after`, stripped (or '' if absent). `lang`
    restricts the fence tag (e.g. 'lean'); None accepts any/none — matching the 6× `_fenced` which used the
    optional `(?:lean)?` tag. Byte-equivalent drop-in for `_fenced(after)`."""
    fence = (rf"(?:{re.escape(lang)})?" if lang else r"[a-zA-Z0-9_+-]*")
    m = re.search(rf"{re.escape(after)}\s*```{fence}\s*\n(.*?)```", raw or "", re.DOTALL)
    return m.group(1).strip() if m else ""


def labeled_value(raw: str, label: str, allowed: "Optional[tuple]" = None,
                  default: str = "") -> "tuple[str, str]":
    """Extract `LABEL: <VALUE> [— <rest>]` from agent output → `(value, rest)`. `value` is upper-cased; if
    `allowed` is given and the parsed value is not in it (or no label is present), returns `(default, "")`.
    The one-line labeled-enum extraction (e.g. a PLAN tag) WITHOUT a per-caller regex; `rest` is trimmed to
    the line and capped."""
    # 2026-06-13 bug-hunt: the label must be a WHOLE WORD and the colon REQUIRED. The old `{label}\s*:?`
    # (optional colon, no boundary) matched INSIDE prose — `…PLANNING…` captured `NING` ⇒ a real
    # `PLAN: SOLVE_DIRECT` election downstream was shadowed and re-coerced to the default (DECOMPOSE),
    # defeating the #133 non-DAG escape. `\bPLAN\b\s*:` won't match `PLANNING` (no boundary after `PLAN`).
    m = re.search(rf"\b{re.escape(label)}\b\s*:\s*([A-Za-z_]+)\s*(?:[—:\-]\s*([^\n]*))?", raw or "")
    if not m:
        return default, ""
    value = (m.group(1) or "").upper()
    if allowed is not None and value not in allowed:
        return default, ""
    return value, (m.group(2) or "").strip()[:240]


def budget_request(raw: str, *, floor: int, cap: int) -> "Optional[int]":
    """#103(1) AGENT-CHOSEN TIME within a deterministic supra-cap (bounded free will): extract the agent's
    `BUDGET: <seconds>` declaration (the PLAN:-style line; `labeled_value` can't carry it — its value class is
    alpha-only) and CLAMP to [floor, cap] — the agent requests, the harness deterministically bounds. `600s`
    suffix tolerated; a degenerate `0` clamps to the floor (never starves a dispatch); absent/garbage ⇒ None
    (caller keeps its calibrated/factory budget — fail-safe, additive)."""
    m = re.search(r"BUDGET\s*:?\s*(\d+)\s*s?\b", raw or "", re.IGNORECASE)
    if not m:
        return None
    # CLAMP ORDER (2026-06-13 audit): `cap` is the hard ceiling, so it must win even if a caller passes
    # floor>cap (little wallclock left). `max(floor, min(cap, v))` would return floor>cap; `min(cap, max(floor, v))`
    # keeps the result ≤ cap always.
    lo = min(floor, cap)
    return int(min(cap, max(lo, int(m.group(1)))))


def _selftest() -> int:
    fails = []

    def ok(n, c):
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
        if not c:
            fails.append(n)

    # fenced_block: PARITY with the 6× inline `_fenced` regex (so migration is a safe drop-in)
    raw = "preamble\nLEMMA:\n```lean\ntheorem t : True := trivial\n```\nPROOF:\n```\nby trivial\n```\n"

    def _legacy_fenced(after):  # the exact body copied across the solver
        m = re.search(rf"{after}\s*```(?:lean)?\s*\n(.*?)```", raw, re.DOTALL)
        return m.group(1).strip() if m else ""

    ok("fenced_block == legacy _fenced (LEMMA, lean tag)", fenced_block(raw, "LEMMA:") == _legacy_fenced("LEMMA:"))
    ok("fenced_block == legacy _fenced (PROOF, no tag)", fenced_block(raw, "PROOF:") == _legacy_fenced("PROOF:"))
    ok("fenced_block extracts the lean block", "theorem t" in fenced_block(raw, "LEMMA:"))
    ok("fenced_block lang-restricted matches the lean fence", fenced_block(raw, "LEMMA:", lang="lean").startswith("theorem"))
    ok("fenced_block absent label ⇒ ''", fenced_block(raw, "NOPE:") == "")

    # labeled_value: the PLAN-tag style extraction
    P = ("DECOMPOSE", "SOLVE_DIRECT", "SPECIALIZE", "FALSIFY", "ABDUCE", "TRANSPORT", "GENERALIZE")
    ok("labeled_value: action + em-dash reason",
       labeled_value("PLAN: FALSIFY — looks false\nDECOMP:", "PLAN", P) == ("FALSIFY", "looks false"))
    ok("labeled_value: colon reason + case-insensitive",
       labeled_value("PLAN: specialize: tighten the bound", "PLAN", P) == ("SPECIALIZE", "tighten the bound"))
    ok("labeled_value: hyphen reason", labeled_value("PLAN: DECOMPOSE - split it", "PLAN", P)[0] == "DECOMPOSE")
    ok("labeled_value: no label ⇒ default", labeled_value("just prose", "PLAN", P, default="DECOMPOSE") == ("DECOMPOSE", ""))
    ok("labeled_value: unrecognized ⇒ default", labeled_value("PLAN: NONSENSE", "PLAN", P, default="DECOMPOSE")[0] == "DECOMPOSE")
    ok("labeled_value: no allowed-set ⇒ takes any token", labeled_value("MODE: fast", "MODE")[0] == "FAST")
    # 2026-06-13 bug-hunt regression: prose containing the label as a SUBSTRING must NOT shadow the real
    # election (the `\bLABEL\b\s*:` fix). `PLANNING` no longer captures `NING` and masks `PLAN: SOLVE_DIRECT`.
    ok("labeled_value: prose 'PLANNING' does NOT shadow the real PLAN line",
       labeled_value("I am now PLANNING my approach.\nPLAN: SOLVE_DIRECT — one rfl", "PLAN", P) == ("SOLVE_DIRECT", "one rfl"))
    ok("labeled_value: bare label without a colon ⇒ default (colon now required; discriminating default)",
       labeled_value("PLAN DECOMPOSE", "PLAN", P, default="FALSIFY")[0] == "FALSIFY")

    # budget_request (#103(1)): agent-declared seconds, deterministically clamped
    ok("budget: plain", budget_request("PLAN: DECOMPOSE\nBUDGET: 600 — long compile", floor=30, cap=1800) == 600)
    ok("budget: s-suffix + case", budget_request("budget: 90s", floor=30, cap=1800) == 90)
    ok("budget: clamps to cap", budget_request("BUDGET: 99999", floor=30, cap=1800) == 1800)
    ok("budget: 0 clamps to floor (never starves)", budget_request("BUDGET: 0", floor=30, cap=1800) == 30)
    ok("budget: absent ⇒ None (caller keeps factory)", budget_request("just prose", floor=30, cap=1800) is None)
    ok("budget: garbage ⇒ None", budget_request("BUDGET: soon", floor=30, cap=1800) is None)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    raise SystemExit(_selftest() if "--selftest" in sys.argv else (print(__doc__) or 0))
