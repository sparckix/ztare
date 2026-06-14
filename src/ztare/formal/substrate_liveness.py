"""Substrate liveness calibration — the forcing function that prevents 'going blind'.

RCA (2026-06-01): a toolchain/ABI mismatch (repl binary built at a different Lean than
the project's Mathlib oleans) made `import Mathlib` SILENTLY return an empty env in ~0.8s.
Every probe then errored, and experiment scripts read the resulting "0 closed" as a real
solver verdict ('talent-bound', 'automation void'). We trusted a NEGATIVE result from an
instrument we never calibrated. Those negatives were non-probative — same class as the
#print-axioms module-incompatible VOID.

The fix is structural, not a point-fix: BEFORE any proof-search run may interpret a
negative, it MUST pass calibration controls run THROUGH THE SAME code path as the real
probes (PersistentLean.check / the same closure gate). A negative from an uncalibrated
substrate is REJECTED, not interpreted.

Three layers, cheapest first:
  1. toolchain_match() — deterministic, no process: read the repl binary's lean-toolchain
     and the project's lean-toolchain and compare. Catches the exact RCA for ~0 cost.
  2. positive controls — known-true goals (incl. Mathlib-dependent) MUST close clean.
     A dead/empty env fails these => substrate is not alive => fail-closed.
  3. negative controls — a known-FALSE goal MUST NOT be reported closed (guards verifier
     false-accept), and a `sorry` proof MUST be caught by the #print-axioms gate (guards
     that our 'kernel-clean' definition actually rejects sorry).

Substrate-agnostic: no NS/APN/Clay specifics. Pass an optional `corpus_probe` (a small
true goal in the real corpus's module shape) to also calibrate in-context, per the lesson
that a positive control must match the real substrate shape.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from ztare.common.timeouts import timeout_s   # central budget factory (stdlib-only; safe for the ztare.formal layer)


class SubstrateDeadError(RuntimeError):
    """Raised when calibration fails — the substrate cannot be trusted to produce an
    interpretable negative. Fail-closed: the caller must ABORT, never report '0 closed'."""


# known-true goals; the Mathlib ones fail on an empty/dead env (the RCA signature)
_POSITIVE = [
    ("env_exists", "example : True := trivial"),
    ("mathlib_nat", "example : (2 : ℕ) + 2 = 4 := by norm_num"),
    ("mathlib_finset", "example : (∅ : Finset ℕ) = ∅ := rfl"),
]
# known-FALSE goal: must NOT be reported closed (guards verifier false-accept)
_NEGATIVE_FALSE = ("false_goal", "example : (1 : ℕ) = 2 := by norm_num")
# a sorry proof whose axioms MUST contain sorryAx (guards the closure gate itself)
_SORRY_GATE = ("sorry_gate",
               "theorem _ztare_sorry_probe : (1 : ℕ) = 1 := by sorry\n"
               "#print axioms _ztare_sorry_probe")


@dataclass
class CalibrationReport:
    project_dir: str
    repl_bin: str
    toolchain_repl: str = ""
    toolchain_project: str = ""
    toolchain_match: bool = False
    import_seconds: float | None = None
    positives: list[dict] = field(default_factory=list)
    false_goal_rejected: bool = False
    sorry_gate_detects: bool = False
    alive: bool = False
    failures: list[str] = field(default_factory=list)

    def banner(self) -> str:
        mark = "GREEN ✅ ALIVE" if self.alive else "RED ❌ DEAD"
        tc = (f"{self.toolchain_repl} vs {self.toolchain_project} "
              f"{'MATCH' if self.toolchain_match else 'MISMATCH'}")
        pos = " ".join(f"{p['name']}={'ok' if p['closed'] else 'FAIL'}"
                       for p in self.positives)
        t = f" import={self.import_seconds:.1f}s" if self.import_seconds else ""
        return (f"[substrate-calibration] {mark} | toolchain {tc}{t} | "
                f"positive: {pos} | false-goal-rejected={self.false_goal_rejected} | "
                f"sorry-gate-detects={self.sorry_gate_detects}"
                + (f" | FAILURES: {'; '.join(self.failures)}" if self.failures else ""))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def toolchain_of(path: Path) -> str:
    """Return the stripped lean-toolchain string for a project dir, or '' if absent."""
    tc = Path(path) / "lean-toolchain"
    try:
        return tc.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def repl_toolchain(repl_bin: str | Path) -> str:
    """The lean-toolchain the repl binary was built under: walk up from
    <lean_repl>/.lake/build/bin/repl to <lean_repl>/lean-toolchain."""
    p = Path(repl_bin).resolve()
    for anc in p.parents:
        cand = anc / "lean-toolchain"
        has_lakefile = (anc / "lakefile.toml").exists() or (anc / "lakefile.lean").exists()
        if cand.exists() and has_lakefile:
            return toolchain_of(anc)
    # fallback: vendor/lean_repl is parents[3] of the binary
    try:
        return toolchain_of(p.parents[3])
    except Exception:
        return ""


def toolchain_match(repl_bin: str | Path, project_dir: str | Path) -> tuple[bool, str, str]:
    """Layer 1 (deterministic, no process): does the repl binary's toolchain match the
    project's Mathlib toolchain? Catches the dead-REPL RCA at ~0 cost."""
    rtc = repl_toolchain(repl_bin)
    ptc = toolchain_of(project_dir)
    return (bool(rtc) and bool(ptc) and rtc == ptc), rtc, ptc


def _closed_clean(pl, code: str) -> bool:
    r = pl.check(code, timeout=timeout_s("substrate_liveness"))
    return bool(r.get("success")) and not (r.get("errors") or []) and not (r.get("sorries") or [])


def calibrate(pl, corpus_probe: str | None = None,
              import_seconds: float | None = None,
              require_toolchain_match: bool = True) -> CalibrationReport:
    """Run the full calibration through the SAME code path as real probes. Returns a
    CalibrationReport and RAISES SubstrateDeadError if the substrate cannot be trusted.

    `pl` is a live PersistentLean. `corpus_probe` is an optional small KNOWN-TRUE goal in
    the real corpus's module shape (e.g. one using the corpus's own defs) — calibrating
    in-context, since a positive control must match the real substrate shape.
    """
    rep = CalibrationReport(project_dir=pl.project_dir, repl_bin=pl.repl_bin,
                            import_seconds=import_seconds)
    m, rtc, ptc = toolchain_match(pl.repl_bin, pl.project_dir)
    rep.toolchain_match, rep.toolchain_repl, rep.toolchain_project = m, rtc, ptc
    if require_toolchain_match and not m:
        rep.failures.append(
            f"toolchain mismatch (repl {rtc!r} != project {ptc!r}) — repl binary and "
            f"Mathlib oleans built at different Lean versions")

    positives = list(_POSITIVE)
    if corpus_probe:
        positives.append(("corpus_context", corpus_probe))
    for name, code in positives:
        ok = _closed_clean(pl, code)
        rep.positives.append({"name": name, "closed": ok})
        if not ok:
            rep.failures.append(f"positive control {name!r} did NOT close "
                                f"(substrate not alive / Mathlib not loaded)")

    # negative control: a false goal must NOT be reported closed
    rf = pl.check(_NEGATIVE_FALSE[1], timeout=timeout_s("substrate_liveness"))
    rep.false_goal_rejected = not (rf.get("success") and not (rf.get("errors") or []))
    if not rep.false_goal_rejected:
        rep.failures.append("verifier FALSE-ACCEPT: a known-false goal was reported closed")

    # sorry-gate control: a sorry proof's axioms MUST contain sorryAx (gate detects sorry)
    rs = pl.check(_SORRY_GATE[1], timeout=timeout_s("substrate_liveness"))
    rep.sorry_gate_detects = "sorryAx" in (rs.get("output") or "")
    if not rep.sorry_gate_detects:
        rep.failures.append("closure gate BLIND: #print axioms did not surface sorryAx "
                            "for a sorry proof (kernel-clean check would not reject sorry)")

    rep.alive = not rep.failures
    if not rep.alive:
        raise SubstrateDeadError(rep.banner())
    return rep
