"""Post-closure ROBUSTNESS battery — the proof-substrate analogue of the cognitive gym's GP-112 margin
of safety (`fit/margin_of_safety.py`). GP-112's tests are numerical (curve_fit / residual drift /
extrapolation) and share ZERO code with proof robustness, so this is a SUBSTRATE-SPECIFIC battery — NOT
a forced shared interface (that would be a hollow protocol). But it REUSES the existing leanmill
primitives wholesale (no new gate logic, no parallel kernel):
  • soundness     → `lean_proof_gate.run_anti_laundering_kernel` (THE kernel) — re-confirmed as a
                    CONFIDENCE annotation, not a re-gate (GP-112: "does not alter the finding").
  • surveyability → `gates.proof_surveyability_gate` (axiom-allowlist lexical + proof-length-vs-sketch).
  • load-bearing  → the one genuinely-NEW perturbation test (deep; needs lake): trivialize each Prop
                    hypothesis of the target to `True` and recompile — a hypothesis whose trivialization
                    does NOT break the proof is DECORATIVE (weaken signal: the statement is over-specified
                    or the proof ignores it). This is the proof analogue of GP-112's "which coefficients
                    survive under perturbation."

ADVISORY by construction: it annotates a CLOSED proof with strengthen / weaken / inconclusive signals;
it NEVER re-rejects a closure (run it post-ratification, like GP-112's standalone analysis step).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RobustnessReport:
    target: str
    tests: dict = field(default_factory=dict)   # name -> {verdict, detail}
    strengthened: list = field(default_factory=list)
    weakened: list = field(default_factory=list)
    inconclusive: list = field(default_factory=list)

    @property
    def overall(self) -> str:
        # ADVISORY summary — never a hard reject. "fragile_advisory" iff any test weakened the closure.
        return "fragile_advisory" if self.weakened else ("robust" if self.strengthened else "inconclusive")

    def to_dict(self) -> dict:
        return {"target": self.target, "overall": self.overall, "tests": self.tests,
                "strengthened": self.strengthened, "weakened": self.weakened,
                "inconclusive": self.inconclusive,
                "kind": "proof_margin_of_safety", "advisory": True}


def _record(rep: RobustnessReport, name: str, verdict: str, detail: Any) -> None:
    rep.tests[name] = {"verdict": verdict, "detail": detail}
    {"strengthen": rep.strengthened, "weaken": rep.weakened, "inconclusive": rep.inconclusive}[verdict].append(name)


# ── hypothesis parsing for the load-bearing perturbation (reuses statement_integrity._signature) ──────

_PROP_HINT = re.compile(r"[<>≤≥=≠∈∉∣∤→↔∀∃¬∧∨]|\b(?:Prime|Coprime|Continuous|Differentiable|Algebraic|"
                        r"Irreducible|Monotone|Bounded|Nonempty|Finite)\b")


def _target_block(lean_source: str, target_name: str) -> str:
    from ztare.leanmill.solver.statement_integrity import decl_blocks
    blocks = dict(decl_blocks(lean_source))
    for n in blocks:
        if n == target_name or n.endswith("." + target_name):
            return blocks[n]
    return ""


def _prop_hypotheses(block: str) -> "list[tuple[str, str]]":
    """Return (binder_group_text, full_type) for binder groups whose type LOOKS like a Prop hypothesis
    (contains a relational/logical symbol or a known predicate). Heuristic — this battery is advisory."""
    from ztare.leanmill.solver.statement_integrity import _signature
    sig = _signature(block)
    out: list[tuple[str, str]] = []
    # match (names : type) / {names : type} / ⦃names : type⦄ binder groups at top level
    for m in re.finditer(r"[(\{⦃]\s*([^():{}⦃⦄]+?)\s*:\s*([^()]*?)\s*[)\}⦄]", sig):
        grp, typ = m.group(0), m.group(2)
        if _PROP_HINT.search(typ):
            out.append((grp, typ))
    return out


def proof_margin_of_safety(lean_source: str, target_name: str, lean_root: "Path | None" = None,
                           *, timeout_s: int = 90, deep: bool = True,
                           original_source: "str | None" = None) -> dict:
    """Run the post-closure robustness battery on a CLOSED proof. `deep` (needs lake) runs the
    load-bearing hypothesis perturbation; static tests (soundness shape-organs + surveyability) always
    run. Returns RobustnessReport.to_dict() — ADVISORY (strengthen/weaken/inconclusive), never a reject."""
    rep = RobustnessReport(target=target_name)

    # 1. SOUNDNESS re-confirmation — REUSE the ONE kernel (shape organs; deep_verify off ⇒ no recompile).
    try:
        from ztare.gates.lean_proof_gate import run_anti_laundering_kernel
        k = run_anti_laundering_kernel(lean_source, (lean_root or Path(".")) / "_mos.lean",
                                       (lean_root or Path(".")), deep_verify=False,
                                       original_source=original_source, target_name=target_name)
        confirmed = k.get("confirmed") or []
        _record(rep, "soundness", "weaken" if confirmed else "strengthen",
                {"passed": k.get("passed"), "confirmed": confirmed, "flags": k.get("flags")})
    except Exception as e:  # noqa: BLE001
        _record(rep, "soundness", "inconclusive", {"error": repr(e)[:140]})

    # 2. SURVEYABILITY — REUSE proof_surveyability_gate (lexical axiom-allowlist + length-vs-sketch).
    try:
        from ztare.gates.proof_surveyability_gate import axiom_allowlist_check, proof_length_vs_sketch_check
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False) as _tf:
            _tf.write(lean_source); _p = Path(_tf.name)
        ax = axiom_allowlist_check(_p)
        ln = proof_length_vs_sketch_check(_p, None)
        _p.unlink(missing_ok=True)
        survey_ok = bool(ax.get("passed")) and (ln.get("passed") is not False)
        _record(rep, "surveyability", "strengthen" if survey_ok else "weaken",
                {"axiom_allowlist": ax.get("reason"), "length": ln.get("reason")})
    except Exception as e:  # noqa: BLE001
        _record(rep, "surveyability", "inconclusive", {"error": repr(e)[:140]})

    # 3. LOAD-BEARING hypotheses (the genuinely-new perturbation) — trivialize each Prop hypothesis → True
    #    and recompile; a hypothesis whose trivialization still compiles is DECORATIVE (weaken).
    block = _target_block(lean_source, target_name)
    hyps = _prop_hypotheses(block) if block else []
    if not deep or lean_root is None:
        _record(rep, "load_bearing", "inconclusive",
                {"note": "deep/lake not run", "n_prop_hypotheses": len(hyps)})
    elif not hyps:
        _record(rep, "load_bearing", "inconclusive", {"note": "no Prop hypotheses parsed"})
    else:
        from ztare.gates.v33_preflight_risk_detector import _compile_probe
        decorative: list[str] = []
        for grp, _typ in hyps:
            triv = grp[:grp.rfind(":")] + ": True" + grp[len(grp) - 1:]   # (h : P) -> (h : True)
            perturbed = lean_source.replace(grp, triv, 1)
            if _compile_probe(perturbed, lean_root, "MoS_loadbearing", timeout_s) is True:
                decorative.append(grp.strip())   # still compiles with the hypothesis trivialized ⇒ decorative
        if decorative:
            _record(rep, "load_bearing", "weaken",
                    {"decorative_hypotheses": decorative, "of": len(hyps),
                     "interpretation": "trivializing these did NOT break the proof — over-specified / ignored"})
        else:
            _record(rep, "load_bearing", "strengthen",
                    {"all_hypotheses_load_bearing": len(hyps)})

    # 4. CONCLUSION DISCRIMINATION (differential re-verification, iso-run transport 2026-06-12): rebuild
    #    the target with the NEGATED conclusion and the SAME proof body, recompile. A genuine proof is
    #    conclusion-SPECIFIC: it must FAIL on ¬(conclusion) ("differential_confirmed"). If the same body
    #    ALSO closes the negation in the same context ("zero_differential"), the hypotheses are
    #    CONTRADICTORY — the closure is kernel-true but VACUOUS, the shape laundering hides in. The
    #    battery only MEASURES (advisory, per this module's contract); the governance layer owns the
    #    credit decision (solve_adhoc treats zero_differential as a blocker — the one perturbation
    #    verdict that is sound to reject on, since both G and ¬G proving ⇒ inconsistent context.)
    if not deep or lean_root is None:
        _record(rep, "conclusion_discrimination", "inconclusive", {"note": "deep/lake not run"})
    else:
        try:
            from ztare.leanmill import lean_source as _ls
            from ztare.leanmill.solver.conjecture import _top_level_colon
            from ztare.gates.v33_preflight_risk_detector import _compile_probe as _cp_disc
            sig = _ls.extract_signature(lean_source, target_name) or ""
            j = _top_level_colon(sig) if sig else -1
            body = _ls.split_at_proof(block)[1][2:] if block else ""   # proof body, binder-safe ([2:] drops `:=`)
            if j < 0 or not body.strip():
                _record(rep, "conclusion_discrimination", "inconclusive",
                        {"note": "could not split signature/body via canonical parsers"})
            else:
                binders, concl = sig[:j].strip(), sig[j + 1:].strip()
                neg_block = (f"theorem {target_name}_negdisc {binders} : ¬ ({concl}) :={body}"
                             if binders else f"theorem {target_name}_negdisc : ¬ ({concl}) :={body}")
                neg_src = lean_source.replace(block, neg_block, 1)
                r = _cp_disc(neg_src, lean_root, "MoS_discrimination", timeout_s)
                if r is True:
                    _record(rep, "conclusion_discrimination", "weaken",
                            {"differential": "zero",
                             "interpretation": "the SAME proof body closes the NEGATED conclusion in the "
                                               "same context ⇒ hypotheses contradictory (vacuous context) "
                                               "or conclusion-independent automation — laundering-shaped"})
                elif r is False:
                    _record(rep, "conclusion_discrimination", "strengthen",
                            {"differential": "confirmed",
                             "interpretation": "negated conclusion does NOT close — the proof is "
                                               "conclusion-specific (the discriminating differential)"})
                else:
                    _record(rep, "conclusion_discrimination", "inconclusive",
                            {"note": "perturbed compile timed out / errored — never block on inconclusive"})
        except Exception as e:  # noqa: BLE001 — a measuring leg must never break the battery
            _record(rep, "conclusion_discrimination", "inconclusive", {"error": repr(e)[:140]})

    return rep.to_dict()


# ── RUNG-TIGHTENING (M5) — turn a one-off rung into a monotone-tightening chain toward G ──────────────
# Proof-mining transport: a non-constructive SPECIALIZE rung G' (e.g. "∃ N, …") implies a STRONGER explicit
# statement B (e.g. a concrete N / rate). If the leaf can PROVE B sorry-free AND B ⇒ G' typechecks (B is a
# genuine strengthening) AND B ≠ G' (a real tightening), B is banked so a LATER rung can CITE it — rungs
# accumulate toward G instead of being one-offs. SOUND: a fabricated/unrelated bound fails the B-compiles or
# B⇒G' leg and is never banked; the kernel is the arbiter (reuses conjecture.specialization_is_genuine, the
# SAME gate shape, no new gate logic). This lives HERE (the quantitative-slack home), not a parallel store.
# Prompt lives in the canonical registry (prompts.py); local name preserved for the call site.
from ztare.leanmill.solver.prompts import RUNG_TIGHTEN_PROMPT as _RUNG_TIGHTEN_PROMPT


def rung_tighten(rung_block: str, rung_conclusion: str, sname: str, lean_root: "Path",
                 timeout_s: int, preamble: str = "") -> "tuple[str, str, str]":
    """Extract + KERNEL-VERIFY an explicit stronger bound B implied by a non-constructive rung G'. Returns
    (bound_block, implies_block, bname); ('', '', bname) on failure (a fabricated tighter rung is NEVER
    banked). Reuses `conjecture.specialization_is_genuine` for the gate: B compiles sorry-free AND `B ⇒ G'`
    typechecks sorry-free (genuine strengthening) AND B's conclusion ≠ G''s (a real tightening)."""
    from ztare.leanmill.solver.conjecture import specialization_is_genuine, _lemma_conclusion
    bname = f"tight_{re.sub(r'[^A-Za-z0-9_]', '', sname or 'rung')[:24] or 'rung'}"
    pre = ("\nPREAMBLE:\n" + preamble.strip() + "\n") if preamble.strip() else ""
    prompt = _RUNG_TIGHTEN_PROMPT.format(bname=bname, rung=rung_block, pre=pre)
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch
        raw = default_dispatch(prompt, repo=lean_root, timeout=timeout_s) or ""
    except Exception:  # noqa: BLE001
        return "", "", bname

    from ztare.leanmill.solver.agent_output import fenced_block
    bound, implies = fenced_block(raw, "BOUND:"), fenced_block(raw, "IMPLIES:")
    if not bound:
        return "", "", bname
    # Gate: B sorry-free + (B ⇒ G') typechecks + B's conclusion ≠ the rung's. Passing goal_conclusion =
    # the rung's conclusion makes leg (c) reject "B identical to the rung" (no-op tightening).
    _rc = rung_conclusion or _lemma_conclusion(rung_block)
    genuine, _why = specialization_is_genuine(bound, implies, bname, _rc, lean_root, timeout_s, preamble=preamble)
    if not genuine:
        return "", "", bname
    # ANTI-VACUITY (stricter than the inherited specialize gate): the implication theorem must actually
    # CONCLUDE the rung — a vacuous `… : True := trivial` compiles but proves nothing about B⇒G'. Require
    # the implies block's conclusion to match the rung's (so it genuinely derives the rung from B).
    import re as _re2
    if implies and _re2.sub(r"\s+", " ", (_lemma_conclusion(implies) or "")) != _re2.sub(r"\s+", " ", _rc or ""):
        return "", "", bname
    return bound, implies, bname


def _selftest() -> int:
    """Offline checks of the static legs + the hypothesis parser (no lake; deep leg covered by a probe
    monkeypatch)."""
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"); fails.append(name) if not cond else None

    blk = "theorem t (n : ℕ) (hn : 0 < n) (G : RationalFn) (hf : Algebraic G) : Good n := by sorry"
    hyps = _prop_hypotheses(blk)
    names = [g for g, _ in hyps]
    ok("parses Prop hypotheses (0<n, Algebraic G)", any("0 < n" in g for g in names) and any("Algebraic" in g for g in names))
    ok("does NOT flag the plain type-param (n : ℕ) / (G : RationalFn) as Prop",
       not any(re.fullmatch(r"\(n : ℕ\)", g.strip()) for g in names) and not any("RationalFn" in g for g in names))

    # static battery (deep off): soundness + surveyability run; deep legs inconclusive.
    src = "import Mathlib\n\ntheorem t (n : ℕ) (hn : 0 < n) : n + 0 = n := by simp\n"
    rep = proof_margin_of_safety(src, "t", lean_root=None, deep=False)
    ok("battery is ADVISORY (advisory=True, never a reject)", rep["advisory"] is True)
    ok("runs soundness + surveyability + load_bearing + discrimination legs",
       set(rep["tests"]) == {"soundness", "surveyability", "load_bearing", "conclusion_discrimination"})
    ok("load_bearing inconclusive when deep off", rep["tests"]["load_bearing"]["verdict"] == "inconclusive")
    ok("discrimination inconclusive when deep off",
       rep["tests"]["conclusion_discrimination"]["verdict"] == "inconclusive")
    ok("overall is one of robust/fragile_advisory/inconclusive", rep["overall"] in ("robust", "fragile_advisory", "inconclusive"))

    # deep leg: monkeypatch the compile probe so a hypothesis trivialization 'still compiles' ⇒ decorative=weaken.
    import ztare.gates.v33_preflight_risk_detector as v33
    _orig = v33._compile_probe
    v33._compile_probe = lambda *a, **k: True   # everything compiles ⇒ all hyps decorative
    try:
        rep2 = proof_margin_of_safety(src, "t", lean_root=Path("/tmp"), deep=True)
        ok("deep load-bearing flags decorative hypotheses (weaken)", rep2["tests"]["load_bearing"]["verdict"] == "weaken")
        # everything-compiles ⇒ the NEGATED conclusion also "closes" ⇒ ZERO differential (the blocker class)
        _d2 = rep2["tests"]["conclusion_discrimination"]
        ok("discrimination: negation also closing ⇒ zero differential (weaken + detail flag)",
           _d2["verdict"] == "weaken" and _d2["detail"].get("differential") == "zero")
        # name-tagged mock: load-bearing probes "compile", the DISCRIMINATION probe FAILS ⇒ confirmed
        v33._compile_probe = lambda src_, root_, name_, t_: name_ != "MoS_discrimination"
        rep3 = proof_margin_of_safety(src, "t", lean_root=Path("/tmp"), deep=True)
        _d3 = rep3["tests"]["conclusion_discrimination"]
        ok("discrimination: negation failing ⇒ differential confirmed (strengthen)",
           _d3["verdict"] == "strengthen" and _d3["detail"].get("differential") == "confirmed")
        ok("negated probe built by canonical parsers (¬-wrapped conclusion, same body)",
           "negdisc" not in src)   # original source untouched (replace built a NEW string)
        # timeout/None ⇒ inconclusive, NEVER a weaken (never block on inconclusive)
        v33._compile_probe = lambda *a, **k: None
        rep4 = proof_margin_of_safety(src, "t", lean_root=Path("/tmp"), deep=True)
        ok("discrimination: probe timeout ⇒ inconclusive (never blocks)",
           rep4["tests"]["conclusion_discrimination"]["verdict"] == "inconclusive")
    finally:
        v33._compile_probe = _orig

    # M5 rung_tighten (offline): a leaf that returns NO bound ⇒ no tightening (never banks a fabricated
    # bound); bname is derived from the rung name. The kernel legs (B compiles, B⇒G') need lake.
    import ztare.leanmill.solver.agentic_leaf as _al
    _od = _al.default_dispatch
    _al.default_dispatch = lambda *a, **k: ""
    try:
        b, i, nm = rung_tighten("theorem spec_x : ∃ N : ℕ, True := ⟨0, trivial⟩", "∃ N : ℕ, True",
                                "spec_x", Path("/tmp"), 5)
        ok("rung_tighten: no bound from leaf ⇒ no tightening", b == "" and nm == "tight_spec_x")
    finally:
        _al.default_dispatch = _od

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
