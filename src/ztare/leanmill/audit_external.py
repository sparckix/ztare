#!/usr/bin/env python3
"""External-artifact audit (#109) — run a Lean proof leanmill did NOT produce through the governance organs.

WHY this is leanmill SOURCE (not a script): auditing an external prover's output is GENERAL apparatus — the
checker-agnostic, leaf-agnostic trust boundary, sibling of `formal_verification_provider` (the other product
surface). Experiment corpora that feed it are the script/project-side inputs.

Pipeline (existing organs only; adds NO soundness surface):
  1. COMPILE     — the artifact must stand alone (warm REPL via repl_compile, cold `lake env lean` fallback)
  2. AXIOM AUDIT — `#print axioms <decl>` per declaration, allowlist {propext, Classical.choice, Quot.sound}
                   (catches native_decide/ofReduceBool + sorryAx credit — the same F1/F2 discipline the
                   solver's own closures pass)
  3. LEXICAL BAN — sorry/admit/new `axiom` declarations in the source (defense-in-depth)
  4. CERTIFICATE — `common.claim_audit.from_lean_gate_result` → the legible markdown audit

Faithfulness-vs-NL (the firewall judge) is deliberately NOT in v1 — it needs an LLM dispatch; wire the
autoformalize firewall leg behind `--faithfulness` as the follow-up.

Usage:
  python -m ztare.leanmill.audit_external --lean FILE [--nl "claim"] [--project ztare_proofs]
  python -m ztare.leanmill.audit_external --selftest
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
_BANNED = re.compile(r"(?m)\b(sorry|admit)\b|^\s*axiom\s+")


def _default_compile(src: str, project: str) -> dict:
    """Compile `src` standalone over `project` (warm REPL preferred, cold lake fallback). Returns
    {success, output}. Import-header-robust (the warm-vs-verify asymmetry lesson)."""
    try:
        # WARM path: RAW source (the REPL pre-loads Mathlib; a mid-session `import` is rejected)
        from ztare.formal.repl_compile import _get_repl
        pl = _get_repl(project)
        if pl is not None:
            r = pl.check(src, timeout=240)
            ok = bool(r.get("success")) if isinstance(r, dict) else bool(getattr(r, "ok", False))
            out = (r.get("output") or "") if isinstance(r, dict) else str(r)
            return {"success": ok, "output": out}
    except Exception:  # noqa: BLE001 — fall through to cold lake
        pass
    import subprocess
    import tempfile
    from ztare.leanmill.solver.agentic_leaf import ensure_import_header
    with tempfile.NamedTemporaryFile("w", suffix=".lean", dir=Path(project) / ".solver_scratch",
                                     delete=False) as f:
        f.write(ensure_import_header(src))
        tmp = f.name
    r = subprocess.run(["lake", "env", "lean", tmp], cwd=project, capture_output=True, text=True, timeout=600)
    return {"success": r.returncode == 0, "output": (r.stdout or "") + (r.stderr or "")}


def audit_external(lean_path: "Path | None", *, claim_nl: str = "", project: str = "ztare_proofs",
                   source: "str | None" = None, compile_fn=None) -> "tuple[bool, str]":
    """Audit an external Lean artifact. Returns (trustworthy, rendered_markdown). `source`/`compile_fn`
    injectable so the pipeline is hermetically testable without Lean."""
    from ztare.common.claim_audit import from_lean_gate_result, render_markdown
    from ztare.leanmill.solver.statement_integrity import decl_blocks
    from ztare.formal.lean_axiom_audit import parse_axioms
    src = source if source is not None else Path(lean_path).read_text(encoding="utf-8")
    compile_fn = compile_fn or _default_compile
    decls = [n for n, _ in decl_blocks(src)]
    lexical_flags = sorted({m.group(0).strip() for m in _BANNED.finditer(src)})
    # 1. standalone compile
    c = compile_fn(src, project)
    compiled = bool(c.get("success"))
    # 2. axiom audit per decl (appended #print axioms — the same channel the kernel's F1/F2 audit reads)
    extra_axioms: "list[str]" = []
    axiom_ok = compiled
    if compiled and decls:
        probe = src + "\n" + "\n".join(f"#print axioms {d}" for d in decls)
        a = compile_fn(probe, project)
        if a.get("success"):
            extra_axioms = sorted(set(parse_axioms(a.get("output") or "")) - ALLOWED_AXIOMS)
            axiom_ok = not extra_axioms
        else:
            axiom_ok = False   # fail-closed: an unauditable artifact is not a trusted artifact
    gate_shaped = {"compiled": compiled,
                   "gate_passed": compiled and axiom_ok and not lexical_flags,
                   "axiom_audit_passed": axiom_ok,
                   "anti_laundering_passed": not lexical_flags,
                   "v33_organ_flags": [f"lexical_ban:{f}" for f in lexical_flags],
                   "extra_axioms": extra_axioms,
                   "theorem_statement_hashes": [{"name": d} for d in decls]}
    audit = from_lean_gate_result(gate_shaped, claim_nl=claim_nl, checker="lean:external-audit")
    md = render_markdown(audit)
    md += ("\n\n> EXTERNAL-ARTIFACT AUDIT: leanmill did NOT produce this proof; the verdict above is the "
           "governance layer's independent re-verification. Faithfulness-vs-NL judge not run (v1 — the "
           "firewall leg is the follow-up).")
    return bool(gate_shaped["gate_passed"]), md


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    GOOD = "theorem ext_good : 1 + 1 = 2 := by norm_num\n"
    LAUNDERED = "theorem ext_bad : 1 + 1 = 2 := by native_decide\n"
    SORRIED = "theorem ext_sry : False := by sorry\n"

    def mock_compile_clean(src, project):
        if "#print axioms" in src:
            return {"success": True, "output": "'ext_good' depends on axioms: [propext, Classical.choice]"}
        return {"success": True, "output": ""}

    def mock_compile_native(src, project):
        if "#print axioms" in src:
            return {"success": True, "output": "'ext_bad' depends on axioms: [propext, Lean.ofReduceBool]"}
        return {"success": True, "output": ""}

    t, md = audit_external(None, source=GOOD, compile_fn=mock_compile_clean)
    ok("clean external proof ⇒ trustworthy + renders", t is True and "ext_good" in md)
    t, md = audit_external(None, source=LAUNDERED, compile_fn=mock_compile_native)
    ok("native_decide credit ⇒ NOT trustworthy (extra axiom caught)", t is False and "ofReduceBool" in md)
    t, md = audit_external(None, source=SORRIED, compile_fn=mock_compile_clean)
    ok("sorry ⇒ lexical ban trips regardless of compile", t is False and "lexical_ban" in md)
    t, _ = audit_external(None, source=GOOD, compile_fn=lambda s, p: {"success": False, "output": "err"})
    ok("non-compiling artifact ⇒ NOT trustworthy", t is False)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lean", default=None)
    ap.add_argument("--nl", default="")
    ap.add_argument("--project", default="ztare_proofs")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not a.lean:
        print("usage: python -m ztare.leanmill.audit_external --lean FILE [--nl claim] [--project DIR] | --selftest")
        return 2
    trustworthy, md = audit_external(Path(a.lean), claim_nl=a.nl, project=a.project)
    print(md)
    return 0 if trustworthy else 1


if __name__ == "__main__":
    sys.exit(main())
