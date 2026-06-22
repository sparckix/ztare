"""Standing guard against the recurring SIBLING / split-brain bug class (2026-06-22).

WHY THIS EXISTS: leanmill kept re-introducing the same bug — a capability/decision gate read in two places
with DIFFERENT defaults (the `ZTARE_LEANMILL_PROPOSER_POOL` split-brain: `solver_core` read it default-OFF
while `proposer_pool.pool_enabled` read it default-ON, so the pool silently ran or not depending on which path
hit first). The cure for an INSTANCE is "ONE canonical reader, callers delegate"; the cure for the CLASS is a
mechanical check that FAILS when a boolean on/off flag has more than one default anywhere in the tree — so a
new divergent sibling can't land silently. This is the automatable face of the class; the semantic faces
(duplicated decision LOGIC, deterministic shortcuts in an agency lane) still need the re-runnable Explore audit
+ the Goldilocks/anti-sibling principle in the architecture doc — they are NOT mechanically decidable here.

Run:  python -m ztare.leanmill.flag_audit            # report + exit 1 on any split-brain
      python -m ztare.leanmill.flag_audit --list     # also print the full flag inventory + default-OFF gates
Use as a test:  `from ztare.leanmill.flag_audit import split_brain_flags; assert not split_brain_flags()`
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

# Scan the leanmill tree (where the bug lives); the env-flag convention is ZTARE_*.
_ROOT = Path(__file__).resolve().parent
# A BOOLEAN GATE read: `os.environ.get("ZTARE_X"[, "default"]) (==|!=) "v"`. We require the comparison so that
# a BARE `_sv = os.environ.get("ZTARE_X")` (the save/restore idiom — read current value, override, restore)
# is NOT mistaken for a gate. Capturing (default, op, rhs) lets us compute the EFFECTIVE default (the gate's
# truth value when the env var is UNSET) and compare THAT across readers — two readers that both default-ON
# do not conflict even if one writes the default explicitly and the other relies on `!= "0"`.
_GATE = re.compile(
    r"""os\.environ\.get\(\s*["'](ZTARE_[A-Z0-9_]+)["']\s*(?:,\s*["']([^"']*)["'])?\s*\)\s*(==|!=)\s*["']([^"']*)["']""")
_BOOL = {"0", "1"}


def scan_gates(root: Path | None = None) -> "dict[str, dict[str, list[str]]]":
    """flag -> {default_arg -> [file:line, ...]} over BOOLEAN GATE reads only (a `.get(...) ==/!= 'v'`).
    The KEY is the `.get` DEFAULT ARGUMENT verbatim ('UNSET' if absent) — NOT the comparison's truth value:
    `!= '0'` and `== '0'` on the SAME default are the same gate written two directions (enabled? vs disabled?),
    which is consistent, not a conflict. The split-brain is when the DEFAULT ARG itself diverges (one reader
    `get('F','1')`, another `get('F')` or `get('F','0')`) — exactly the proposer-pool bug."""
    root = root or _ROOT
    out: "dict[str, dict[str, list[str]]]" = defaultdict(lambda: defaultdict(list))
    for p in sorted(root.rglob("*.py")):
        if p.name == "flag_audit.py":
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except Exception:  # noqa: BLE001
            continue
        for i, ln in enumerate(lines, 1):
            for m in _GATE.finditer(ln):
                flag, dflt, rhs = m.group(1), (m.group(2) if m.group(2) is not None else "UNSET"), m.group(4)
                # BOOLEAN gates only: the compared value is "0"/"1". A string-MODE flag (`== "full"`) can
                # legitimately carry different defaults per entry point and checks different values — out of
                # scope for this on/off-capability guard (surface those separately if ever needed).
                if rhs not in _BOOL:
                    continue
                # a boolean gate's default arg should itself be "0"/"1"/UNSET; ignore odd mixed forms
                if dflt not in _BOOL and dflt != "UNSET":
                    continue
                out[flag][dflt].append(f"{p.relative_to(root.parent.parent)}:{i}")
    return {k: dict(v) for k, v in out.items()}


def split_brain_flags(root: Path | None = None) -> "dict[str, dict[str, list[str]]]":
    """The ERROR set: a flag whose BOOLEAN GATES use >1 DISTINCT `.get` default argument — the same gate is
    defaulted one way in one reader and another way elsewhere (the proposer-pool bug exactly). Save/restore
    reads and numeric/string flags are excluded by construction (they have no `==/!=` boolean comparison);
    comparison DIRECTION is ignored (so negative-logic `== '0'` disabled-checks don't false-positive)."""
    return {flag: defs for flag, defs in scan_gates(root).items() if len(defs) > 1}


def default_off_gates(root: Path | None = None) -> "dict[str, list[str]]":
    """Advisory inventory: gate flags whose `.get` default argument is the explicit opt-in '0' (default-OFF).
    Not a bug by itself — many are correct A/B baselines or experimental knobs — but this is the list to
    eyeball for the 'is this a SOUND enhancement that should be DEFAULT-ON at its chokepoint?' review (the
    other half of the anti-sibling principle). A genuinely-sound knob defaulting off is the under-use mode."""
    out: "dict[str, list[str]]" = {}
    for flag, defs in scan_gates(root).items():
        if set(defs) == {"0"}:
            out[flag] = sorted({s for sites in defs.values() for s in sites})
    return out


def main(argv: "list[str] | None" = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    bad = split_brain_flags()
    if bad:
        print("FAIL — SPLIT-BRAIN boolean flag default(s) (a divergent sibling: the same gate is default-ON in "
              "one reader and default-OFF in another). Route every reader through ONE canonical accessor "
              "(e.g. proposer_pool.pool_enabled):")
        for flag, defs in sorted(bad.items()):
            print(f"  ✗ {flag}")
            for d, sites in sorted(defs.items()):
                print(f"       .get default={d!r:7s} at {', '.join(sites)}")
    else:
        print("OK — no split-brain boolean gates (every on/off gate agrees on its effective default).")
    if "--list" in argv:
        off = default_off_gates()
        print(f"\nDefault-OFF boolean gates ({len(off)}) — review for 'sound knob ⇒ should be default-ON?':")
        for flag, sites in sorted(off.items()):
            print(f"  · {flag}  ({sites[0]}{' …' if len(sites) > 1 else ''})")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
