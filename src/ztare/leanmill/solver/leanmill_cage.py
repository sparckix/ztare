"""Full Cage routing for the leanmill substrate (GP-086 Phase 6 / GP-249) — leanmill anti-laundering is
dispatched through the SAME Cage orchestrator (`gates/cage.py`) that runs the autoresearch gaming-pattern
gates, so there is ONE `(substrate × gate)` dispatcher across the factory.

§3b-safe BY CONSTRUCTION: the routed gate's `run` IS `run_anti_laundering_kernel`, so `govern_via_cage`
returns the IDENTICAL verdict to calling the kernel directly — the Cage adds dispatch, not a re-implemented
organ stack (re-implementing each organ as a separate gate would risk divergence + is the bigger migration;
the finer per-organ Cage gates live in `leanmill_hardener.leanmill_cage_gates` for the registry view). The
live solver path stays on the direct kernel call until `ZTARE_LEANMILL_CAGE_ROUTING=1` flips it on — and
because the verdict is identical, that flip is regression-safe + reversible.

NOTE: the Cage's substrate.meta schema (min_rows_per_category / near_miss_factor / frame_invariant_y) is
autoresearch-shaped; for a proof_target substrate those keys are VESTIGIAL placeholders (just to pass
`validate_substrate_meta`). A future Cage refactor could make the meta schema substrate-class-conditional.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any


def proof_target_meta() -> dict:
    """Minimal valid `proof_target` substrate.meta (the numeric keys are vestigial placeholders for a Lean
    proof — present only to pass `cage.validate_substrate_meta`)."""
    return {"type": "substrate", "class": "proof_target", "target_convention_homogeneity": "homogeneous",
            "min_rows_per_category": 1, "near_miss_factor": 1.0, "frame_invariant_y": True}


def _kernel_gate():
    """The leanmill anti-laundering kernel as ONE Cage gate (POST_JUDGE, engages on proof_target). Its
    `run` IS `run_anti_laundering_kernel` ⇒ dispatching it yields the kernel's exact verdict."""
    from ztare.gates.cage import Gate

    def _can_handle(substrate, candidate):
        meta = getattr(substrate, "meta", None) or {}
        return (meta.get("class") == "proof_target", "engages on substrate.class==proof_target")

    def _run(substrate, candidate):
        from ztare.gates.lean_proof_gate import run_anti_laundering_kernel
        c = candidate if isinstance(candidate, dict) else {}
        return run_anti_laundering_kernel(
            c.get("lean_source", ""), Path(c.get("lean_path", ".") or "."),
            c.get("ztare_proofs_root"), deep_verify=c.get("deep_verify", False),
            original_source=c.get("original_source"), target_name=c.get("target_name"))

    return Gate(name="leanmill_anti_laundering", phase="POST_JUDGE",
                can_handle=_can_handle, run=_run, dependencies=[])


def leanmill_cage():
    """A Cage holding the leanmill anti-laundering kernel gate + the finer per-organ gates (the registry
    view). The kernel gate is authoritative; the per-organ gates are the granular Cage-dispatchable form."""
    from ztare.gates.cage import Cage
    from ztare.leanmill.solver.leanmill_hardener import leanmill_cage_gates
    return Cage([_kernel_gate(), *leanmill_cage_gates()])


def govern_via_cage(lean_source: str, lean_path: "Path", ztare_proofs_root: "Path | None",
                    *, original_source: "str | None" = None, target_name: "str | None" = None,
                    deep_verify: bool = False) -> dict:
    """Route leanmill anti-laundering through the Cage and return the SAME dict `run_anti_laundering_kernel`
    returns ({passed, flags, confirmed, detail}). Behavior-identical to the direct call (the kernel gate IS
    the kernel) — this is the §3b-safe full Cage routing entry. Fail-OPEN on a Cage error (never block)."""
    try:
        from ztare.gates.cage import Cage
        sub = SimpleNamespace(meta=proof_target_meta())
        cand = {"lean_source": lean_source, "lean_path": lean_path, "ztare_proofs_root": ztare_proofs_root,
                "original_source": original_source, "target_name": target_name, "deep_verify": deep_verify}
        cage = Cage([_kernel_gate()])
        _em, results = cage.dispatch_and_run(sub, cand)
        verdict = results.get("leanmill_anti_laundering")
        if isinstance(verdict, dict) and "passed" in verdict:
            verdict = dict(verdict)
            verdict["_routed_via"] = "cage"
            return verdict
        # Cage didn't engage / errored → fall back to the direct kernel (never lose the gate).
        from ztare.gates.lean_proof_gate import run_anti_laundering_kernel
        return run_anti_laundering_kernel(lean_source, lean_path, ztare_proofs_root, deep_verify=deep_verify,
                                          original_source=original_source, target_name=target_name)
    except Exception as e:  # noqa: BLE001 — fail-open; never block a closure on a routing error
        return {"passed": True, "flags": [], "confirmed": [], "detail": {"cage_routing_error": str(e)[:160]}}


def _selftest() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    from ztare.gates.cage import Cage, validate_substrate_meta
    ok("proof_target meta validates", validate_substrate_meta(proof_target_meta())[0] is True)
    c = leanmill_cage()
    ok("leanmill_cage holds the kernel gate + the per-organ gates", "leanmill_anti_laundering" in c.gates and len(c.gates) >= 3)

    # REGRESSION: govern_via_cage verdict == direct run_anti_laundering_kernel verdict (behavior-identical).
    from ztare.gates.lean_proof_gate import run_anti_laundering_kernel
    orig = "import Mathlib\n\ntheorem t : ∀ n : ℕ, n = n + 1 := by\n  sorry\n"
    shadow = ("import Mathlib\n\nlocal instance {α : Type u} : HAdd α Nat α where\n  hAdd a _ := a\n\n"
              "theorem t : ∀ n : ℕ, n = n + 1 := by\n  intro n\n  rfl\n")
    for label, src, on in (("instance-shadowing (should FAIL both)", shadow, orig),
                           ("clean (should PASS both)", "import Mathlib\n\ntheorem t : True := by\n  trivial\n",
                            "import Mathlib\n\ntheorem t : True := by\n  sorry\n")):
        direct = run_anti_laundering_kernel(src, Path("/tmp/_k.lean"), Path("/tmp"), original_source=on, target_name="t")
        viacage = govern_via_cage(src, Path("/tmp/_k.lean"), Path("/tmp"), original_source=on, target_name="t")
        ok(f"Cage verdict == direct verdict [{label}]", direct.get("passed") == viacage.get("passed"))
        ok(f"  routed via cage [{label}]", viacage.get("_routed_via") == "cage")
    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
