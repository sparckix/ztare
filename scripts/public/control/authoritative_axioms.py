#!/usr/bin/env python3
"""authoritative_axioms.py — THE single authoritative closure verifier
(false-positive-protocol #1: exactly one gate; no caller defines its
own "closed"). Both coherent_rung1.govern_edited and
governance_in_context.govern_in_context delegate here.

ROOT CAUSE THIS FIXES (2026-05-18): the leak-tight corpus files carry a
Lean 4 `module` header; `#print axioms` is forbidden inside a module,
so the prior gate (which appended `#print axioms` into the module file)
returned `open` for 100% of real rows ⇒ every prior authoritative run
was VOID. See memory gate-print-axioms-module-incompatible-runs-void.

ONE-PASS design (VPS scale-validated 20/20 on 2026-05-19): insert an
in-module `Lean.collectAxioms` audit immediately after the exact target
declaration, then open that generated file in a fresh REPL. This avoids
de-module term divergence and the stale-message artifact seen when two
module variants are opened in one persistent REPL.

  generated file open not ok                  -> unverified
  hard errors before audit                    -> open
  hard errors in audit command                -> unverified
  sorry within ±3 of target line              -> open
  no recognizable audit output                -> unverified
  sorryAx present                             -> axiom_smuggled
  explicit local axiom/constant/opaque        -> axiom_smuggled
  target short-name appears in its proof      -> axiom_smuggled
  else                                        -> closure (persisted)

Note: in `module` context, `collectAxioms` reports a broad dependency
frontier rather than the normalized `#print axioms` set. The frontier is
persisted for audit, but arbitrary non-STD names are not closure blockers;
`sorryAx` and explicit local axiom-like declarations are the hard guards.

Fail-closed everywhere: any unknown/odd state is `unverified`, never a
false `closure` and never a false `open`. Result self-carries
provenance (FP #5): {verdict, axioms_deps, persisted, verified_by,
reason}.

KNOWN RESIDUALS (out of scope for this module-fix; do NOT silently
fold in — flagged for separate work): (1) statement-weakening FP — a
`workspace-write` agent could restate the target weaker; no
statement-fidelity check here yet. (2) self-name check is a weak
heuristic (misses fully-qualified-name transcription; can FN a valid
self-referential proof) — kept at parity, reason made auditable.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path

STD = {"propext", "Classical.choice", "Classical.em", "Quot.sound"}
PERSIST = Path("/tmp/rung1/ratified_proofs")

# --- 0-information-asymmetry debug ledger -------------------------------
# EVERY gate attempt (any verdict) persists: the exact proof text +
# Phase-A/Phase-B decisive evidence + verdict + reason. So "why was
# row X open/unverified/smuggled?" is answerable from the ledger with
# ZERO re-running. Fail-safe: logging never raises / never changes a
# verdict. Override dir via ZTARE_GATE_DEBUG_DIR.
_DBG_LEDGER = "gate_attempts.jsonl"
_DBG_LOCK = threading.Lock()


def _dbg_dir() -> Path:
    # resolved at CALL time (not import) so _self_test can isolate its
    # own throwaway ledger and never pollute a real run.
    return Path(os.environ.get("ZTARE_GATE_DEBUG_DIR",
                               "/tmp/rung1/gate_debug"))


def isolate_selftest_ledger() -> None:
    """Call FIRST in EVERY self-test/mock entrypoint (this module's
    and every caller's) so mock govern() calls write to a throwaway
    ledger, never the real run ledger. Clean-by-construction: no
    downstream consumer must remember to filter."""
    os.environ["ZTARE_GATE_DEBUG_DIR"] = tempfile.mkdtemp(
        prefix="selftest_gate_")
    os.environ["ZTARE_GATE_SOURCE"] = "selftest"
    os.environ["ZTARE_GATE_RUN_ID"] = "selftest"


def _log_attempt(prov: dict, target_name: str, target_line: int,
                 full_text: str, ev: dict) -> None:
    """Append one complete, self-describing attempt record. Wrapped so
    a logging failure can NEVER affect the gate verdict."""
    try:
        dbg = _dbg_dir()
        pdir = dbg / "proofs"
        pdir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%dT%H%M%S")
        uid = uuid.uuid4().hex[:8]
        nm = re.sub(r"[^A-Za-z0-9_]", "_", target_name.split(".")[-1])[:48]
        pf = pdir / f"{nm}_{ts}_{uid}.lean"
        pf.write_text(full_text)
        rec = {
            "ts": ts, "uid": uid,
            "run_id": os.environ.get("ZTARE_GATE_RUN_ID", "adhoc"),
            "source": os.environ.get("ZTARE_GATE_SOURCE", "run"),
            "target_name": target_name, "target_line": target_line,
            "verdict": prov.get("verdict"),
            "reason": prov.get("reason"),
            "axioms_deps": prov.get("axioms_deps"),
            "persisted": prov.get("persisted"),
            "verified_by": prov.get("verified_by"),
            "proof_file": str(pf),
            "proof_sha_len": len(full_text),
            "evidence": ev,
        }
        with _DBG_LOCK:
            with (dbg / _DBG_LEDGER).open("a") as f:
                f.write(json.dumps(rec) + "\n")
    except Exception:
        pass
_DEPENDS = re.compile(r"depends on axioms:\s*\[([^\]]*)\]", re.S)
_AXIOMS = re.compile(r"AXIOMS\s*\[([^\]]*)\]", re.S)
_NOAX = "does not depend on any axioms"
_VERIFIER = ("authoritative_axioms.govern "
             "(in-module injected collectAxioms; no de-module)")

_DECL_START = re.compile(
    r"(?m)^(?:(?:public\s+|private\s+|protected\s+)?"
    r"(?:theorem|lemma|def|abbrev|instance|structure|class|inductive|"
    r"namespace|end|section|noncomputable|open|variable|attribute)\b"
    r"|@\[|/--|/-)")
_DECL_NAME = re.compile(
    r"(?m)^(?:public\s+|private\s+|protected\s+)?"
    r"(?:theorem|lemma)\s+([^\s(:]+)")


def t1_demodule(src: str) -> str:
    """Drop the FIRST standalone `module` header line (validated
    minimal, error-equivalent transform). Nothing else changed."""
    out, done = [], False
    for ln in src.splitlines(keepends=True):
        if not done and ln.strip() == "module":
            done = True
            continue
        out.append(ln)
    return "".join(out)


def _line_of(src: str, idx: int) -> int:
    return src.count("\n", 0, idx) + 1


def _decl_name_for_target(src: str, target_line: int,
                          target_name: str) -> str:
    """Find the exact declaration name to audit. Corpus hints can be
    prefixes or miss prime suffixes; target_line is the stronger bind."""
    matches = list(_DECL_NAME.finditer(src))
    spans = []
    for i, m in enumerate(matches):
        cut = matches[i + 1].start() if i + 1 < len(matches) else len(src)
        spans.append((m.group(1), _line_of(src, m.start()),
                      _line_of(src, cut), m.start()))
    # Prefer the declaration that starts at or immediately before the target
    # line. Adjacent declaration spans share a boundary line; treating the
    # previous span as end-inclusive audits the theorem above the target.
    containing = [(start, name) for name, start, _end, _ in spans
                  if start <= target_line]
    if containing:
        return max(containing, key=lambda x: x[0])[1]
    short = target_name.split(".")[-1]
    for name, _, _, _ in spans:
        if name == target_name or name.split(".")[-1] == short:
            return name
    return target_name


def _inject_axiom_audit(src: str, decl_name: str) -> tuple[str, int]:
    audit_cmd = (
        f"\n#check {decl_name}\n"
        "open Lean Elab Command in\n#eval show CommandElabM Unit from do\n"
        f"  let ax ← liftCoreM (Lean.collectAxioms ``{decl_name})\n"
        "  logInfo m!\"AXIOMS "
        "{ax.qsort Name.lt |>.map MessageData.ofConstName |>.toList}\"\n")
    m = re.search(
        rf"(?m)^(?:public\s+|private\s+|protected\s+)?"
        rf"(theorem|lemma)\s+{re.escape(decl_name)}(?=\s|[:(\[{{]|$)",
        src)
    if not m:
        line = src.count("\n") + 1
        return src.rstrip() + "\n" + audit_cmd + "\n", line
    nxt = _DECL_START.search(src, m.end())
    cut = nxt.start() if nxt else len(src)
    line = _line_of(src, cut)
    return (src[:cut].rstrip() + "\n" + audit_cmd + "\n"
            + src[cut:].lstrip("\n")), line


def _err_set(of: dict) -> set:
    return {str(m.get("data", ""))[:120]
            for m in (of.get("errors") or [])}


def _proof_region(body: str, short: str) -> str:
    """Self-name tell region — BYTE-FAITHFUL to the proven gate: use
    `codex_proofstate_pilot._target_block` (the proven, block-scoped
    extractor the prior govern_edited used) then the SAME slicing.
    Lazy import with a local fallback only if _PP is unavailable, so
    the live run path keeps proven parity and the module stays
    importable for the machine-safe self-test."""
    try:
        from codex_proofstate_pilot import _target_block  # proven
        blk = _target_block(body, short)
    except Exception:
        i = body.find(short)
        blk = body[i:] if i >= 0 else ""
    if ":= by" in blk:
        return blk.split(":= by", 1)[1]
    if ":=" in blk:
        return blk.split(":=", 1)[1]
    return ""


def govern(L, full_text: str, target_line: int, target_name: str,
           timeout: int = 160, persist: bool = True) -> dict:
    """L: PersistentLean. `full_text` = the COMPLETE file content that
    should contain a finished proof of `target_name` (codex-edited file
    for govern_edited; sorry-substituted source for govern_in_context).
    Returns {verdict, axioms_deps, persisted, verified_by, reason}."""
    short = target_name.split(".")[-1]
    prov = {"verdict": None, "axioms_deps": None, "persisted": None,
            "verified_by": _VERIFIER, "reason": None}

    # evidence accumulator — captured at every decisive point so the
    # ledger answers "why this verdict?" with zero re-running.
    ev: dict = {"textual_earlyout": False, "phaseA_errors": None,
                "phaseA_sorry_lines": None, "sorry_near_target": None,
                "phaseB_new_errs": None, "phaseB_axioms_raw": None,
                "phaseB_depends_found": None,
                "phaseB_no_axioms_str": None}
    td = Path(tempfile.mkdtemp(prefix="authax_"))
    try:
        # cheap textual early-outs — BYTE-FAITHFUL to the proven gate's
        # pre-check (parity-control: no unrequested behavior change).
        # Old: native_decide / :=\s*by\s*\n\s*sorry / "admit" -> open
        if ("native_decide" in full_text
                or re.search(r":=\s*by\s*\n\s*sorry", full_text)
                or "admit" in full_text):
            ev["textual_earlyout"] = True
            prov.update(verdict="open",
                        reason="textual_sorry_admit_or_nd")
            return prov
        if re.search(r"(?m)^\s*(axiom|constant|opaque)\b", full_text):
            ev["textual_earlyout"] = True
            prov.update(verdict="axiom_smuggled",
                        reason="textual_axiom_constant_or_opaque")
            return prov

        # ---- One-pass true-module validation + axiom audit.
        # `#print axioms` is forbidden in a module, but Lean.collectAxioms
        # is not. Inject the collector immediately after the target decl,
        # so the proof is checked in its real module context and the audit
        # runs in the namespace/section where the name resolves.
        audit_name = _decl_name_for_target(full_text, target_line,
                                           target_name)
        short = audit_name.split(".")[-1]
        injected, audit_line = _inject_axiom_audit(full_text, audit_name)
        fb = td / "B.lean"
        fb.write_text(injected)
        # Real-module generated files showed stale/order-dependent REPL
        # behavior across consecutive opens. Phase-B validated this audit
        # under fresh-REPL isolation, so the authoritative gate matches
        # that condition even though it repays the import cost per verdict.
        try:
            L.close()
        except Exception:
            pass
        ofb = L.open_file(str(fb), timeout)
        ev["phaseB_audit_name"] = audit_name
        ev["phaseB_audit_line"] = audit_line
        if not ofb.get("ok"):
            prov.update(verdict="unverified",
                        reason="injected_open_not_ok")
            return prov
        errors = ofb.get("errors") or []
        ev["phaseA_errors"] = sorted(str(e)[:300] for e in errors)
        ev["phaseB_new_errs"] = sorted(_err_set(ofb))[:5]
        audit_errors = []
        for e in errors:
            pos = e.get("pos") or {}
            if (pos.get("line") or 0) >= audit_line:
                audit_errors.append(e)
        if errors:
            if audit_errors:
                prov.update(verdict="unverified",
                            reason="injected_audit_errors",
                            axioms_deps=sorted(_err_set(ofb))[:3])
            else:
                prov.update(verdict="open", reason="phaseA_errors")
            return prov
        sorry_near = [s for s in (ofb.get("sorries") or [])
                      if s.get("line") is not None
                      and abs(s["line"] - target_line) <= 3]
        ev["phaseA_sorry_lines"] = [s.get("line")
                                    for s in (ofb.get("sorries") or [])]
        ev["sorry_near_target"] = bool(sorry_near)
        if sorry_near:
            prov.update(verdict="open",
                        reason="phaseA_sorry_near_target")
            return prov
        raw = "\n".join(str(m.get("data", "")) for m in
                        (ofb.get("messages") or []))
        rlow = raw.lower()
        depends = list(_DEPENDS.finditer(raw))
        injected_axioms = list(_AXIOMS.finditer(raw))
        ev["phaseB_axioms_raw"] = raw[:1500]
        ev["phaseB_depends_found"] = bool(depends or injected_axioms)
        ev["phaseB_no_axioms_str"] = (_NOAX in rlow)
        if (not depends) and (not injected_axioms) and (_NOAX not in rlow):
            # no recognizable #print-axioms output -> never read
            # silence as clean.
            prov.update(verdict="unverified",
                        reason="no_axioms_output")
            return prov
        deps: set = set()
        for m in depends + injected_axioms:
            deps |= {x.strip() for x in re.split(r"[,\s]+", m.group(1))
                     if x.strip()}
        prov["axioms_deps"] = sorted(deps)
        if "sorryax" in rlow:
            prov.update(verdict="axiom_smuggled",
                        reason="sorryAx")
            return prov
        # self-name transcription tell (PROVEN extractor; auditable)
        pp = _proof_region(full_text, short)
        if short and re.search(rf"\b{re.escape(short)}\b", pp):
            prov.update(verdict="axiom_smuggled",
                        reason="self_name_in_proof_region")
            return prov
        # ---- ratified closure -> persist (FP #3)
        if persist:
            try:
                PERSIST.mkdir(parents=True, exist_ok=True)
                ts = time.strftime("%Y%m%dT%H%M%S")
                nm = re.sub(r"[^A-Za-z0-9_]", "_", short)[:48]
                pf = PERSIST / f"{nm}_{ts}.lean"
                pf.write_text(full_text)
                with (PERSIST / "ratified_manifest.jsonl").open("a") as f:
                    f.write(json.dumps({
                        "name": target_name, "verdict": "closure",
                        "axioms_deps": sorted(deps), "ts": ts}) + "\n")
                prov["persisted"] = str(pf)
            except Exception:
                pass
        prov.update(verdict="closure", reason="axioms_subset_STD")
        return prov
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
        # single 0-asymmetry chokepoint — logs EVERY verdict path.
        _log_attempt(prov, target_name, target_line, full_text, ev)


# ---- machine-safe self-test (mock REPL; NO Lean) -----------------------
def _self_test() -> int:
    isolate_selftest_ledger()   # never pollute the real run ledger
    GOOD = ("module\nimport Mathlib\n\npublic theorem foo : True := "
            "by trivial\n")

    class _Mk:
        def __init__(self, ok=True, msgs=None, err=None, sorries=None):
            self.k = dict(ok=ok, msgs=msgs or [], err=err or [],
                          sorries=sorries or [])

        def open_file(self, path, timeout=160):
            return {"ok": self.k["ok"], "errors": self.k["err"],
                    "sorries": self.k["sorries"],
                    "messages": self.k["msgs"]}

    def m(data):
        return {"severity": "info", "data": data}

    # clean STD -> closure
    r = govern(_Mk(msgs=[m("'foo' depends on axioms: [propext, "
                            "Classical.choice, Quot.sound]")]),
               GOOD, 4, "foo", persist=False)
    assert r["verdict"] == "closure", r
    adjacent = (
        "module\nimport Mathlib\n\n"
        "theorem previous : True := by trivial\n"
        "theorem target : True := by trivial\n"
    )
    assert _decl_name_for_target(adjacent, 5, "target") == "target"
    assert _decl_name_for_target(adjacent, 4, "previous") == "previous"
    # no axioms at all -> closure (subset of STD trivially)
    r = govern(_Mk(msgs=[m("'foo' does not depend on any axioms")]),
               GOOD, 4, "foo", persist=False)
    assert r["verdict"] == "closure", r
    # sorryAx -> axiom_smuggled HARD
    r = govern(_Mk(msgs=[m("'foo' depends on axioms: [sorryAx]")]),
               GOOD, 4, "foo", persist=False)
    assert r["verdict"] == "axiom_smuggled" and r["reason"] == "sorryAx", r
    # injected collector in module mode reports dependency frontiers,
    # not normalized #print-axioms sets; non-STD names are recorded but
    # not a closure blocker unless sorryAx or textual axiom smuggling.
    r = govern(_Mk(msgs=[m("'foo' depends on axioms: [propext, "
                            "Lean.ofReduceBool]")]),
               GOOD, 4, "foo", persist=False)
    assert r["verdict"] == "closure", r
    # explicit local axiom/constant/opaque declarations are smuggling.
    r = govern(_Mk(), "module\nimport Mathlib\n\naxiom bad : True\n"
                      "theorem foo : True := bad\n", 5, "foo",
               persist=False)
    assert r["verdict"] == "axiom_smuggled" and \
        r["reason"] == "textual_axiom_constant_or_opaque", r
    # phase A error -> open
    r = govern(_Mk(err=[{"data": "type mismatch"}]),
               GOOD, 4, "foo", persist=False)
    assert r["verdict"] == "open" and r["reason"] == "phaseA_errors", r
    # phase A sorry near target -> open
    r = govern(_Mk(sorries=[{"line": 4}]), GOOD, 4, "foo",
               persist=False)
    assert r["verdict"] == "open", r
    # injected audit introduced an error -> unverified (fail-closed)
    r = govern(_Mk(err=[{"data": "unknown identifier 'Foo.bar'",
                         "pos": {"line": 99}}]),
               GOOD, 4, "foo", persist=False)
    assert r["verdict"] == "unverified" and \
        r["reason"] == "injected_audit_errors", r
    # no axioms output at all -> unverified (never silence==clean)
    r = govern(_Mk(msgs=[m("some unrelated info")]),
               GOOD, 4, "foo", persist=False)
    assert r["verdict"] == "unverified" and \
        r["reason"] == "no_axioms_output", r
    # textual sorry early-out
    r = govern(_Mk(), "theorem foo : True := by\n  sorry\n", 1, "foo",
               persist=False)
    assert r["verdict"] == "open" and \
        r["reason"] == "textual_sorry_admit_or_nd", r
    # de-module helper: drops only the standalone `module` line
    assert t1_demodule("module\nimport X\nmodule\n") == \
        "import X\nmodule\n"
    print("[self-test] authoritative_axioms: closure / no-axioms / "
          "sorryAx-HARD / textual-axiom-HARD / phaseA-open / sorry-near / "
          "injected-audit-error->unverified / no-output->unverified / "
          "textual-sorry / t1 all PASS. NO Lean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())
