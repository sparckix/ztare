"""Self-measured cold-Mathlib compile baseline — the ONE source of truth for Lean-compile timeouts.

WHY THIS EXISTS (the recurring bug class): every `lake env lean` on a box without a persistent REPL pays a COLD
Mathlib reload whose wall-time is a PROPERTY OF THE BOX + its page-cache state (~60-90s on the local box, less on
a beefier VPS, more under contention). Timeouts were hand-GUESSED at ~20 scattered sites; any one set below the
cold baseline becomes an INTERMITTENT false-negative — it passes when the page cache is warm and false-fails when
it is cold (e.g. after heavy compiles evict the oleans). That is the dead-instrument bug that keeps recurring,
including on the dead-instrument GUARD itself (`preflight_moves_alive` defaulted to 60s < the ~90s reload). A
hand-coded constant CANNOT be right across boxes/states; the baseline must be MEASURED.

THE FIX: measure the baseline ONCE (a single timed trivial `import Mathlib` compile — the preflight already pays
this), cache + persist it per lean_root, and route EVERY Lean-compile timeout through `cold_safe_timeout(desired)`
= `max(desired, baseline * margin)`. No site can then be set below the measured floor — the memory's "budget
cold-Mathlib timeouts" rule, mechanized + self-adapting per box instead of re-guessed.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

_REPO = Path(__file__).resolve().parents[3]
_BASELINE_FILE = _REPO / "analytics/public/queries/cold_mathlib_baseline.json"

# Conservative fallback used UNTIL a real measurement exists for a root (the memory's safe-side value; better to
# over-budget a fresh box than false-fail). Once measured, the measured value supersedes it.
FALLBACK_BASELINE_S = 120.0
# A measurement above this is treated as contention/glitch, not the true baseline (don't let one bad sample pin
# every timeout to 10 min). Below this we trust it.
SANE_MAX_BASELINE_S = 360.0
DEFAULT_MARGIN = 2.0   # cold reload varies with page-cache/contention; 2x the clean baseline absorbs that.

_MEM_CACHE: "dict[str, float]" = {}


def _load_persisted() -> dict:
    try:
        return json.loads(_BASELINE_FILE.read_text(encoding="utf-8")) if _BASELINE_FILE.exists() else {}
    except Exception:  # noqa: BLE001 — a corrupt cache must never break the solver; re-measure instead
        return {}


def _persist(root_key: str, baseline_s: float) -> None:
    try:
        data = _load_persisted()
        data[root_key] = {"baseline_s": round(baseline_s, 1), "measured_at": int(time.time())}
        _BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _BASELINE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001 — persistence is best-effort (read-only FS / race); the in-mem cache still holds
        pass


def measure_cold_baseline(lean_root, *, ceiling_s: int = 600, force: bool = False) -> Optional[float]:
    """Measure the box's cold-Mathlib compile baseline for `lean_root`: time a single `lake env lean` on a
    trivial `import Mathlib` file, with a GENEROUS ceiling so the MEASUREMENT itself never false-fails. Cached
    in-process + persisted (measured once per box, reused across runs). Returns wall-seconds, or None on error.
    `ZTARE_COLD_BASELINE_S=<secs>` pins it (CI / a known box); `force=True` re-measures."""
    root_key = str(Path(lean_root).resolve())
    env_pin = os.environ.get("ZTARE_COLD_BASELINE_S")
    if env_pin and env_pin.replace(".", "", 1).isdigit():
        return float(env_pin)
    if not force:
        if root_key in _MEM_CACHE:
            return _MEM_CACHE[root_key]
        persisted = _load_persisted().get(root_key, {})
        if isinstance(persisted, dict) and isinstance(persisted.get("baseline_s"), (int, float)):
            _MEM_CACHE[root_key] = float(persisted["baseline_s"])
            return _MEM_CACHE[root_key]
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        probe = Path(td) / "ColdBaselineProbe.lean"
        probe.write_text("import Mathlib\n\ntheorem _cold_baseline_probe : True := trivial\n", encoding="utf-8")
        t0 = time.monotonic()
        try:
            # The probe lives in a TemporaryDirectory, not in ``lean_root``.  Passing only
            # ``probe.name`` makes Lean look for the file under ``cwd`` and turns every
            # measurement into a false toolchain failure.  Keep the project root as cwd
            # (Lake needs it), while identifying the existing probe by its absolute path.
            r = subprocess.run(["lake", "env", "lean", str(probe.resolve())], cwd=str(lean_root),
                               capture_output=True, text=True, timeout=ceiling_s)
        except subprocess.TimeoutExpired:
            return None   # even a trivial compile exceeded the generous ceiling — a real toolchain problem
        except Exception:  # noqa: BLE001
            return None
        dt = time.monotonic() - t0
    if r.returncode != 0:
        return None       # trivial probe didn't even compile — toolchain broken, NOT a baseline
    baseline = min(dt, SANE_MAX_BASELINE_S)
    _MEM_CACHE[root_key] = baseline
    _persist(root_key, baseline)
    return baseline


def cold_safe_timeout(desired_s: int, lean_root=None, *, margin: float = DEFAULT_MARGIN) -> int:
    """The FLOOR every Lean-compile timeout should route through: `max(desired_s, baseline * margin)`, so no
    site is ever budgeted below the box's MEASURED cold-Mathlib reload. With no measurement yet (or no root)
    the conservative `FALLBACK_BASELINE_S` is used — over-budget, never under. This is what kills the bug class:
    a hand value of 60s on a 90s-reload box is silently lifted to the safe floor instead of false-failing."""
    baseline = None
    if lean_root is not None:
        try:
            baseline = measure_cold_baseline(lean_root)
        except Exception:  # noqa: BLE001 — measurement failure must never harden into a too-short timeout
            baseline = None
    if baseline is None:
        baseline = FALLBACK_BASELINE_S
    return int(max(int(desired_s), round(baseline * margin)))


def _selftest() -> int:
    fails = []

    def ok(n, c):
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
        if not c:
            fails.append(n)

    # the FLOOR logic (no Lean): a too-short hand value is lifted to baseline*margin; a generous one is kept.
    global _MEM_CACHE
    _MEM_CACHE = {"/fake/root": 90.0}
    ok("too-short hand value (60s) lifted to the measured floor (90*2=180)",
       cold_safe_timeout(60, "/fake/root", margin=2.0) == 180)
    ok("generous hand value (300s) kept (above the floor)",
       cold_safe_timeout(300, "/fake/root", margin=2.0) == 300)
    ok("no root ⇒ conservative fallback floor (never under-budget)",
       cold_safe_timeout(60, None, margin=2.0) == int(FALLBACK_BASELINE_S * 2))
    ok("env pin overrides measurement", (os.environ.__setitem__("ZTARE_COLD_BASELINE_S", "45")
        or measure_cold_baseline("/fake/root") == 45.0))
    os.environ.pop("ZTARE_COLD_BASELINE_S", None)
    _MEM_CACHE = {}
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    raise SystemExit(_selftest() if "--selftest" in sys.argv else (print(__doc__) or 0))
