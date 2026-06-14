"""Claim AUDIT — the legible certificate distilled from the governance organs already run.

For an UNTRUSTED claim (an autoformalized theorem, an AI-generated proof, a compliance rule), the deliverable
is not the raw proof — it is a LEGIBLE AUDIT a human can read to decide whether to trust the result:

    {claim, faithfulness evidence, the discriminating instances decided, the laundering checks survived,
     axioms used, the matched-negative-controls} — distilled from organ outputs that ALREADY ran.

This module is PURE DISTILLATION + RENDERING — it adds NO soundness surface. It does not compile, decide, or
re-run any organ; it READS the structured verdicts the kernel already produced (`LeanProofGateResult` on the
math side, the `formal-verification-provider/v1` payload on the non-math/SMT side) and renders them. So it
cannot make a wrong claim look right — it can only present, faithfully, what governance found. "The proof is
the evidence; the audit is the product."

Substrate-neutral, in `common/` next to `governed_verification.py` + `apparatus_certificate.py` (same rule:
distills already-produced verdicts, NO substrate import — no Lean, no z3). Earns its place by ≥2 real consumers:
  - the math/proof path  — `from_lean_gate_result(LeanProofGateResult.to_dict())`  (gates/lean_proof_gate)
  - the non-math/certify path — `from_provider_payload(payload)`  (leanmill/formal_verification_provider)

  python -m ztare.common.claim_audit --selftest
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

# Same 4-way verdict vocabulary as the formal-verification provider (carried as a string — common/ does NOT
# import leanmill). verified = faithful + checker-closed + ratified; refuted = counterexample to a faithful
# claim; inconclusive = timeout/no-checker/insufficient; invalid = unfaithful OR a laundered/axiom-dirty close.
VERDICTS = ("verified", "refuted", "inconclusive", "invalid")


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256((text or "").encode("utf-8")).hexdigest()


@dataclass
class ClaimAudit:
    """The legible audit of one governed claim. Every field is DISTILLED from an organ output — nothing here
    is re-decided. `laundering_checks_survived` lists the organs that PASSED; `laundering_flags` lists any that
    FIRED (non-empty ⇒ the close is suspect)."""
    verdict: str
    claim_formal: str                                  # the theorem statement / Lean source / SMT rule checked
    claim_sha256: str                                  # binds the audit to the EXACT artifact
    substrate: str                                     # "lean" | "smt" | "isabelle" | ...
    checker: str                                       # the binding that ratified ("lean:lake", "smt:z3")
    claim_nl: str = ""                                 # natural-language claim/rule ("" when the formal IS the claim)
    faithfulness_evidence: list[str] = field(default_factory=list)   # NL↔formal faithfulness legs / receipts
    discriminating_instances: list[str] = field(default_factory=list)  # boundary/labelled cases the checker DECIDED
    laundering_checks_survived: list[str] = field(default_factory=list)
    laundering_flags: list[str] = field(default_factory=list)        # organs that FIRED (empty ⇒ clean)
    axioms: list[str] = field(default_factory=list)                  # axioms beyond the core (empty ⇒ axiom-clean)
    applied_lemmas: list[str] = field(default_factory=list)          # (math) the Mathlib lemmas the proof cited
    robustness: dict = field(default_factory=dict)                   # the proof_margin_of_safety RobustnessReport
    cross_substrate: dict = field(default_factory=dict)              # the cross_substrate_consensus ConsensusVerdict
    caveats: list[str] = field(default_factory=list)
    summary: str = ""

    @property
    def trustworthy(self) -> bool:
        """A consumer's quick gate: verified + no organ fired. NOT a substitute for reading the audit."""
        return self.verdict == "verified" and not self.laundering_flags

    def with_robustness(self, report: "dict[str, Any]") -> "ClaimAudit":
        """Fold a `proof_margin_of_safety` RobustnessReport (the post-closure SEMANTIC-STRENGTH battery — the
        adversarial-faithfulness / matched-negative-control-for-the-STATEMENT primitive) into this audit. The
        deepest faithfulness signal: a DECORATIVE hypothesis (one whose trivialization does NOT break the proof)
        means the statement is over-specified / the proof ignores it. ADVISORY by construction — robustness adds
        faithfulness CAVEATS or strengthens confidence; it NEVER flips a `verified` verdict to `invalid` (that
        would re-gate an advisory battery). Mutates + returns self."""
        if not report:
            return self
        self.robustness = dict(report)
        overall = report.get("overall")
        tests = report.get("tests") or {}
        decorative = ((tests.get("load_bearing") or {}).get("detail") or {}).get("decorative_hypotheses") or []
        if decorative:
            self.caveats.append(
                f"semantic strength: {len(decorative)} DECORATIVE hypothesis(es) — trivializing them did not "
                f"break the proof, so the statement is over-specified / they are unused "
                f"({', '.join(str(d) for d in decorative)[:160]}).")
        if overall == "robust":
            self.laundering_checks_survived.append("margin-of-safety (no decorative hypothesis)")
        elif overall == "fragile_advisory":
            self.caveats.append("semantic strength: margin-of-safety flags this close as FRAGILE (advisory).")
        self.summary = _summarize(self)
        return self

    def with_consensus(self, consensus: "dict[str, Any]") -> "ClaimAudit":
        """Fold a `cross_substrate_consensus` ConsensusVerdict (.to_dict()) into the audit. CORROBORATED across
        ≥2 INDEPENDENT substrates → a trust-lift survived-check; FAITHFULNESS_CONFLICT → a flag (one substrate's
        NL→formal translation is unfaithful — a translation bug localized without a human), which sets
        trustworthy=False. ADVISORY-loud, exactly like `with_robustness`: it re-decides nothing and never flips
        the kernel verdict; a conflict WARNS the consumer, it does not fabricate a verdict. Mutates + returns self."""
        if not consensus:
            return self
        self.cross_substrate = dict(consensus)
        status = consensus.get("status")
        subs = consensus.get("agree_ok") or []
        if status == "corroborated":
            self.laundering_checks_survived.append(
                f"cross-substrate corroboration ({consensus.get('n_substrates', len(subs))} independent "
                f"substrates: {', '.join(subs)})")
        elif status == "faithfulness_conflict":
            self.laundering_flags.append(
                "cross-substrate DISAGREEMENT — " + (consensus.get("reason")
                or "substrates disagree on the same claim; one NL→formal translation is unfaithful"))
            self.caveats.append("a substrate disagreement localizes a translation bug to inspect: "
                                + "; ".join(f"{c.get('a')}↔{c.get('b')}" for c in (consensus.get("conflict") or [])[:4]))
        self.summary = _summarize(self)
        return self

    def to_dict(self) -> "dict[str, Any]":
        return asdict(self)


# Human-epistemic gap that NO checker closes — kept as a standing caveat on every audit (epistemic P16): a
# kernel proves the FORMAL statement; whether that statement faithfully captures the INFORMAL claim is human.
_P16_CAVEAT = ("Semantic equivalence of the formal statement to the informal claim is a human judgment the "
               "checker does not certify (epistemic P16).")


def _summarize(a: "ClaimAudit") -> str:
    if a.verdict == "verified":
        bits = []
        if a.discriminating_instances:
            bits.append(f"{len(a.discriminating_instances)} discriminating instance(s) decided")
        if "matched-negative-control" in a.laundering_checks_survived:
            bits.append("negation does not close (not vacuous)")
        if not a.axioms:
            bits.append("axiom-clean")
        tail = "; ".join(bits) if bits else "checker-ratified"
        return f"VERIFIED by {a.checker} — {tail}."
    if a.verdict == "invalid":
        why = "; ".join(a.laundering_flags) or "faithfulness/governance check failed"
        return f"INVALID — {why} (the close cannot be trusted)."
    if a.verdict == "refuted":
        return f"REFUTED by {a.checker} — a counterexample to the claim was found."
    return f"INCONCLUSIVE — {a.checker} could not decide (timeout / unavailable / insufficient evidence)."


def from_lean_gate_result(result: "dict[str, Any]", *, claim_nl: str = "", claim_formal: str = "",
                          mnc_passed: Optional[bool] = None, checker: str = "lean:lake") -> "ClaimAudit":
    """Distill a math/proof audit from a `LeanProofGateResult` (as a dict — `.to_dict()`). Reads the gate's
    OWN verdict fields (compiled / gate_passed / axiom_audit_passed / anti_laundering_passed / v33_organ_flags /
    extra_axioms / applied_lemmas / theorem_statement_hashes). `mnc_passed` is the matched-negative-control
    verdict the solver gate runs alongside (the gate result itself may not carry it); pass it when known."""
    r = result or {}
    compiled = bool(r.get("compiled"))
    gate_passed = bool(r.get("gate_passed"))
    axiom_ok = bool(r.get("axiom_audit_passed"))
    al_ok = bool(r.get("anti_laundering_passed", True))
    flags = list(r.get("v33_organ_flags") or [])
    axioms = list(r.get("extra_axioms") or [])
    applied = list(r.get("applied_lemmas") or [])
    hashes = r.get("theorem_statement_hashes") or []

    formal = claim_formal or (hashes[0].get("name", "") if hashes and isinstance(hashes[0], dict) else "")
    csha = ""
    if hashes and isinstance(hashes[0], dict) and hashes[0].get("statement_sha256"):
        csha = "sha256:" + str(hashes[0]["statement_sha256"]).removeprefix("sha256:")
    else:
        csha = _sha256(formal)

    # verdict from the organ verdicts (NO re-decision): unfaithful/laundered/axiom-dirty ⇒ invalid, checked
    # before the pass read so a laundered-but-compiled close is never surfaced as verified.
    if not compiled:
        verdict = "inconclusive"
    elif flags or (not al_ok) or (not axiom_ok) or (mnc_passed is False):
        verdict = "invalid"
    elif gate_passed:
        verdict = "verified"
    else:
        verdict = "inconclusive"

    survived: "list[str]" = []
    if axiom_ok:
        survived.append("axiom-allowlist")
    if al_ok and not flags:
        survived.append("anti-laundering-kernel")
    if mnc_passed is True:
        survived.append("matched-negative-control")
    if hashes:
        survived.append("statement-hash-bind")

    caveats = [_P16_CAVEAT]
    if mnc_passed is None:
        caveats.append("matched-negative-control not asserted on this path (vacuity not ruled out here).")
    if flags:
        caveats.append("anti-laundering organ(s) fired: " + ", ".join(flags))

    a = ClaimAudit(
        verdict=verdict, claim_formal=formal, claim_sha256=csha, substrate="lean", checker=checker,
        claim_nl=claim_nl,
        faithfulness_evidence=([f"theorem statement bound by {csha}"] if hashes else []),
        discriminating_instances=[],                  # proof-side discrimination IS the matched-negative-control
        laundering_checks_survived=survived, laundering_flags=flags,
        axioms=axioms, applied_lemmas=applied, caveats=caveats,
    )
    a.summary = _summarize(a)
    return a


def from_provider_payload(payload: "dict[str, Any]") -> "ClaimAudit":
    """Distill a non-math/certify audit from a `formal-verification-provider/v1` payload (a dict). Reads the
    payload's verdict + `metadata.anti_laundering` + `metadata.provider_artifacts` (the battery cases, the SMT
    boundary, the laundered-control verdict) — all already produced by the firewall."""
    p = payload or {}
    md = p.get("metadata") or {}
    artifacts = md.get("provider_artifacts") or {}
    anti = md.get("anti_laundering") or {}
    faith = artifacts.get("faithfulness") or {}
    cert = artifacts.get("certificate") or {}

    formal = cert.get("lean_src") or p.get("certificate_ref", "")
    csha = cert.get("sha256") or p.get("certificate_digest") or _sha256(formal)
    substrate = p.get("formal_system", "smt")
    checker = f"{substrate}:{p.get('verifier_ref', '')}".rstrip(":")

    cases = faith.get("labelled_cases") or []
    instances = [f"{c[0]} → {'true' if c[1] else 'false'}" for c in cases if isinstance(c, (list, tuple)) and len(c) == 2]
    boundary = (faith.get("smt_boundary") or {}).get("boundary")
    if boundary is not None:
        instances = [f"SMT boundary @ {boundary} (the off-by-one a reviewer misses)"] + instances

    survived: "list[str]" = []
    flags: "list[str]" = []
    if str(anti.get("statement_integrity")) == "pass":
        survived.append("statement-integrity")
    mnc = anti.get("matched_negative_control")
    if mnc == "rejected":
        survived.append("matched-negative-control")
    elif mnc == "admitted":
        flags.append("matched-negative-control ADMITTED — the laundered twin was NOT rejected (the battery cannot separate it)")

    faithfulness = list(p.get("faithfulness_refs") or [])
    if faith.get("faithful_battery_pass") is True:
        faithfulness = ["faithful formalization decided every labelled case"] + faithfulness

    caveats = [_P16_CAVEAT]
    cer = p.get("counterexample_ref")
    if cer:
        caveats.append(f"counterexample: {cer}")

    a = ClaimAudit(
        verdict=p.get("verdict", "inconclusive"),
        claim_formal=formal, claim_sha256=csha, substrate=substrate, checker=checker,
        claim_nl=faith.get("rule_nl", "") or p.get("subject_ref", ""),
        faithfulness_evidence=faithfulness, discriminating_instances=instances,
        laundering_checks_survived=survived, laundering_flags=flags,
        axioms=[], applied_lemmas=[], caveats=caveats,
    )
    a.summary = _summarize(a)
    return a


_VERDICT_ICON = {"verified": "✅ VERIFIED", "refuted": "❌ REFUTED",
                 "inconclusive": "⚠️ INCONCLUSIVE", "invalid": "❌ INVALID"}


def render_markdown(a: "ClaimAudit") -> str:
    """The legible audit document — the PRODUCT a consumer reads to decide whether to trust the claim."""
    L: "list[str]" = []
    L.append(f"# Claim audit — {_VERDICT_ICON.get(a.verdict, a.verdict.upper())}")
    L.append("")
    L.append(f"_{a.summary}_")
    L.append("")
    if a.claim_nl:
        L.append(f"- **Claim (natural language):** {a.claim_nl}")
    fshort = (a.claim_formal or "").strip().replace("\n", " ⏎ ")
    if len(fshort) > 200:
        fshort = fshort[:200] + " …"
    L.append(f"- **Formal artifact:** `{fshort}`")
    L.append(f"- **Digest:** `{a.claim_sha256}`")
    L.append(f"- **Substrate / checker:** {a.substrate} ({a.checker})")
    L.append("")

    def _section(title: str, items: "list[str]", empty: str) -> None:
        L.append(f"## {title}")
        if items:
            L.extend(f"- {it}" for it in items)
        else:
            L.append(f"- _{empty}_")
        L.append("")

    _section("Faithfulness evidence", a.faithfulness_evidence,
             "none recorded (for a pure-math target, faithfulness is the statement-hash bind + human review)")
    _section("Discriminating instances decided", a.discriminating_instances,
             "n/a on this substrate (proof-side discrimination is the matched-negative-control below)")
    survived = [f"✅ {s}" for s in a.laundering_checks_survived] + [f"❌ {f}" for f in a.laundering_flags]
    _section("Laundering checks", survived, "none run")
    _section("Axioms used", (a.axioms or []), "none beyond the checker's trusted core (axiom-clean)")
    if a.applied_lemmas:
        _section("Library lemmas cited", a.applied_lemmas, "")
    if a.robustness:
        _label = {"load_bearing": "hypothesis-necessity", "soundness": "soundness",
                  "surveyability": "surveyability"}
        L.append("## Robustness — semantic strength (advisory)")
        L.append(f"- margin-of-safety verdict: **{a.robustness.get('overall', '?')}**")
        for tname, t in (a.robustness.get("tests") or {}).items():
            L.append(f"  - {_label.get(tname, tname)}: {t.get('verdict', '?')}")
        L.append("")
    if a.cross_substrate:
        cs = a.cross_substrate
        L.append("## Cross-substrate consensus")
        L.append(f"- status: **{cs.get('status', '?')}** across {cs.get('n_substrates', '?')} substrate(s)")
        if cs.get("agree_ok"):
            L.append(f"  - ratified by: {', '.join(cs['agree_ok'])}")
        if cs.get("agree_reject"):
            L.append(f"  - refused by: {', '.join(cs['agree_reject'])}")
        if cs.get("status") == "faithfulness_conflict":
            L.append("  - ⚠️ disagreement → exactly one NL→formal translation is unfaithful (inspect the renderings)")
        L.append("")
    _section("Caveats", a.caveats, "none")

    L.append("---")
    L.append("_The proof/certificate is the evidence; this audit is its legible distillation. Distilled from "
             "governance organs that already ran — it adds no verification, it reports what governance found._")
    return "\n".join(L)


def _selftest() -> int:
    fails = []

    def ok(n, c):
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
        if not c:
            fails.append(n)

    # math/proof path: a clean verified close
    gate_ok = {
        "compiled": True, "gate_passed": True, "axiom_audit_passed": True, "anti_laundering_passed": True,
        "v33_organ_flags": [], "extra_axioms": [], "applied_lemmas": ["Nat.add_comm"],
        "theorem_statement_hashes": [{"name": "my_thm", "statement_sha256": "abc123"}],
    }
    a = from_lean_gate_result(gate_ok, claim_nl="n+m = m+n", mnc_passed=True)
    ok("math verified", a.verdict == "verified" and a.trustworthy)
    ok("math binds statement hash", a.claim_sha256 == "sha256:abc123")
    ok("math axiom-clean + MNC survived",
       not a.axioms and "matched-negative-control" in a.laundering_checks_survived)

    # math/proof path: an organ fired ⇒ invalid (laundered), NEVER verified
    gate_bad = {**gate_ok, "v33_organ_flags": ["gold_name_verbatim"], "anti_laundering_passed": False}
    b = from_lean_gate_result(gate_bad, mnc_passed=True)
    ok("math laundered ⇒ invalid (not verified)", b.verdict == "invalid" and not b.trustworthy)
    ok("math invalid surfaces the organ flag", "gold_name_verbatim" in b.laundering_flags)

    # math/proof path: not compiled ⇒ inconclusive
    c = from_lean_gate_result({"compiled": False, "gate_passed": False})
    ok("math not-compiled ⇒ inconclusive", c.verdict == "inconclusive")
    # MNC not asserted ⇒ caveat present
    d = from_lean_gate_result(gate_ok)  # mnc_passed=None
    ok("math un-asserted MNC ⇒ vacuity caveat", any("vacuity" in cv for cv in d.caveats))

    # non-math/certify path: distill from a provider payload (the certify-demo shape)
    payload = {
        "verdict": "verified", "formal_system": "lean", "verifier_ref": "leanmill:certify-demo@v1",
        "certificate_ref": "leanmill://certificates/basel", "certificate_digest": "sha256:deadbeef",
        "subject_ref": "rule://basel/cet1", "faithfulness_refs": ["leanmill://faithfulness/basel"],
        "metadata": {
            "anti_laundering": {"statement_integrity": "pass", "matched_negative_control": "rejected",
                                "smt_boundary_case": 449},
            "provider_artifacts": {
                "certificate": {"sha256": "sha256:deadbeef", "lean_src": "abbrev adequate ... := 450 ≤ b.cet1Bp"},
                "faithfulness": {"rule_nl": "CET1 ≥ 450bp", "faithful_battery_pass": True,
                                 "labelled_cases": [["⟨449⟩", False], ["⟨450⟩", True]],
                                 "smt_boundary": {"boundary": 449}},
            },
        },
    }
    e = from_provider_payload(payload)
    ok("certify verified", e.verdict == "verified" and e.trustworthy)
    ok("certify pulls the NL rule", e.claim_nl == "CET1 ≥ 450bp")
    ok("certify lists the SMT boundary as a discriminating instance",
       any("boundary @ 449" in i for i in e.discriminating_instances))
    ok("certify records MNC + statement-integrity survived",
       "matched-negative-control" in e.laundering_checks_survived
       and "statement-integrity" in e.laundering_checks_survived)

    # certify path: an admitted laundered control ⇒ a flag (even if payload says invalid)
    bad_payload = json.loads(json.dumps(payload))
    bad_payload["verdict"] = "invalid"
    bad_payload["metadata"]["anti_laundering"]["matched_negative_control"] = "admitted"
    f = from_provider_payload(bad_payload)
    ok("certify admitted-launder ⇒ flag + not trustworthy",
       f.laundering_flags and not f.trustworthy)

    # robustness fold (proof_margin_of_safety RobustnessReport): advisory — never flips verified→invalid
    robust = {"overall": "robust", "advisory": True,
              "tests": {"load_bearing": {"verdict": "strengthen", "detail": {"all_hypotheses_load_bearing": 2}}}}
    g = from_lean_gate_result(gate_ok, mnc_passed=True).with_robustness(robust)
    ok("robustness robust ⇒ still verified + survived-check added",
       g.verdict == "verified" and any("margin-of-safety" in s for s in g.laundering_checks_survived))
    fragile = {"overall": "fragile_advisory", "advisory": True,
               "tests": {"load_bearing": {"verdict": "weaken",
                                          "detail": {"decorative_hypotheses": ["(hx : 0 < n)"], "of": 2}}}}
    h = from_lean_gate_result(gate_ok, mnc_passed=True).with_robustness(fragile)
    ok("robustness fragile is ADVISORY (verified NOT flipped to invalid)", h.verdict == "verified")
    ok("robustness surfaces decorative hypotheses as a caveat",
       any("DECORATIVE" in cv for cv in h.caveats) and h.robustness.get("overall") == "fragile_advisory")
    ok("render shows the Robustness section", "## Robustness — semantic strength" in render_markdown(h))

    # cross-substrate consensus fold: corroboration = survived-check; conflict = flag (advisory, not verdict-flip)
    corro = {"status": "corroborated", "n_substrates": 2, "agree_ok": ["lean", "smt_z3"], "agree_reject": [],
             "conflict": [], "reason": "corroborated by 2 independent substrates"}
    cc = from_lean_gate_result(gate_ok, mnc_passed=True).with_consensus(corro)
    ok("consensus corroborated ⇒ survived-check + still verified",
       cc.verdict == "verified" and any("cross-substrate corroboration" in s for s in cc.laundering_checks_survived))
    conflict = {"status": "faithfulness_conflict", "n_substrates": 2, "agree_ok": ["lean"], "agree_reject": ["smt_z3"],
                "conflict": [{"a": "lean", "b": "smt_z3"}], "reason": "substrates disagree; a translation is unfaithful"}
    ce = from_lean_gate_result(gate_ok, mnc_passed=True).with_consensus(conflict)
    ok("consensus conflict ⇒ flag + NOT trustworthy (advisory, verdict NOT flipped)",
       ce.verdict == "verified" and not ce.trustworthy
       and any("DISAGREEMENT" in f for f in ce.laundering_flags))
    ok("render shows the Cross-substrate section",
       "## Cross-substrate consensus" in render_markdown(ce) and "faithfulness_conflict" in render_markdown(ce))

    # render: markdown contains the core sections + the P16 caveat
    md = render_markdown(a)
    ok("render has verdict header", md.startswith("# Claim audit — ✅ VERIFIED"))
    ok("render has all sections",
       all(s in md for s in ("## Faithfulness evidence", "## Discriminating instances decided",
                             "## Laundering checks", "## Axioms used", "## Caveats")))
    ok("render carries the P16 human-equivalence caveat", "epistemic P16" in md)
    ok("render of a verified certify audit shows the boundary",
       "boundary @ 449" in render_markdown(e))

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    print(__doc__)
