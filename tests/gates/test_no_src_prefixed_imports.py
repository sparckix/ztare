"""Mechanized prevention for the dual-module-identity RCA.

ROOT CAUSE (logged in GP-241_forward_spec_promotion_contracts.md):
`rd_tick_brief` puts BOTH repo-root and repo/src on sys.path, so
`from src.ztare.X import …` inside an importable module loads a
SECOND, distinct module object from the same file (sys.modules key
`src.ztare.X` ≠ `ztare.X`). Security-critical gates then operate on a
different module instance than the daemon/brief use — failing
launcher-dependently and NON-reproducibly in isolation (it cost a
multi-turn debugging spiral exactly because every isolated repro
passed).

INVARIANT (deterministic, grep-able, one canonical identity):
no importable module under src/ztare may import itself via the
`src.ztare.…` spelling. The canonical importable root is `ztare.…`
(repo/src on sys.path). `src.`-prefixed imports are permitted ONLY in
non-importable entrypoints (scripts/, tests/, deploy/) where a single
process controls sys.path.

This test fails CI/`pytest` (and runs as a plain script) if the
invariant is violated — so the RCA cannot silently recur.

Run: python3 tests/gates/test_no_src_prefixed_imports.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "src" / "ztare"
_BAD = re.compile(r"^\s*(from|import)\s+src\.ztare(\.|\s|$)")


def _is_runtime_module(p: Path) -> bool:
    # The RCA vector is a RUNTIME importable module imported under
    # mixed spellings within ONE process. Test files / test dirs are
    # controlled single-process entrypoints that set their own
    # sys.path — not the vector. Scope the invariant to runtime code
    # so the guard is actionable, not permanently-red noise.
    parts = p.parts
    if any(seg in ("tests", "test", "_tests", "testing")
           for seg in parts):
        return False
    if p.name.startswith("test_") or p.name.endswith("_test.py"):
        return False
    return True


def _offenders() -> list[str]:
    bad: list[str] = []
    for p in PKG.rglob("*.py"):
        if not _is_runtime_module(p):
            continue
        try:
            for i, line in enumerate(
                    p.read_text(encoding="utf-8",
                                errors="ignore").splitlines(), 1):
                if _BAD.match(line):
                    bad.append(f"{p.relative_to(ROOT)}:{i}: "
                               f"{line.strip()}")
        except Exception:
            continue
    return bad


def test_no_src_prefixed_imports_in_importable_pkg():
    bad = _offenders()
    assert not bad, (
        "dual-module-identity RCA guard: importable src/ztare modules "
        "MUST import via canonical `ztare.…`, never `src.ztare.…` "
        "(the second spelling loads a distinct module object under a "
        "different sys.modules key when repo-root is also on path — "
        "the launcher-dependent gate failure this prevents). "
        "Offenders:\n  " + "\n  ".join(bad))


if __name__ == "__main__":
    _b = _offenders()
    if _b:
        print("FAIL — src.ztare-prefixed imports in importable pkg:")
        for x in _b:
            print("  " + x)
        raise SystemExit(1)
    print("PASS — no src.ztare-prefixed imports in importable "
          "src/ztare (dual-identity RCA cannot recur via this path)")
