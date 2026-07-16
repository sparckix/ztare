"""Governed artifacts — the **provenance firewall** for post-run deliverables.

A Scenario may emit domain deliverables after a run (a decision-memo, risk-register, spec). The governance
invariant (operator-driven, Fable-advised): a deliverable must contain NOTHING that wasn't governed. Precisely:

  * The map (artifact element → governed element) is **TOTAL** — every element has a governed pre-image. It is
    NOT injective: many artifact elements may cite one governed element (reuse is what deliverables are). The
    one forbidden thing is an **orphan** — an element with no governed source.
  * The codomain is the run's **GOVERNED FINAL STATE** — the HARDENED claims + bound evidence + falsifiers —
    NOT the pre-test thesis inputs. Citing the pre-registered claim instead of its hardened form would launder
    the un-tested version.
  * Enforcement is **SYNTACTIC**: referential integrity (every slot resolves to a governed id) + text that is
    **verbatim / normalized-equal** to the governed text. Never a "semantically equivalent" judge — that is the
    flaky-judge class the faithfulness firewall already fights, and it lets paraphrase drift silently strengthen
    a claim (dropping a scope qualifier), making the firewall decorative.
  * **Set-completeness** (anti-cherry-pick): every deliverable the charter pre-registered must be emitted OR
    emit a stub with a reason. You cannot silently drop the deliverable that didn't survive.

v1 is **template-composition**: deliverable slots are typed refs into the governed state, filled verbatim.
Free-prose generation is a later, riskier layer that would need a claim-extraction judge — deliberately not v1.
"""
from __future__ import annotations

from ztare.scenarios.governed_types import *  # noqa: F401,F403 — facade re-export (base types)
from ztare.scenarios.verdict import *  # noqa: F401,F403 — facade re-export (verdict)
from ztare.scenarios.verdict import _coverage
from ztare.scenarios.roundtrip import *  # noqa: F401,F403 — facade re-export (roundtrip)
from ztare.scenarios.adapters import *  # noqa: F401,F403 — facade re-export (adapters)
from ztare.scenarios.firewall import *  # noqa: F401,F403 — facade re-export (firewall)
from ztare.scenarios.production import *  # noqa: F401,F403 — facade re-export (production)


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    gs = GovernedState([
        GovernedElement("c1", "claim", "Feature X lifts activation by 3-5% under bounded evidence E."),
        GovernedElement("e1", "evidence", "Interview cohort n=12; 9 cited the missing step."),
        GovernedElement("f1", "falsifier", "If the A/B shows <1% lift at n=2000, the claim is dead."),
    ])

    # 1. governed composition passes the firewall by construction.
    memo = decision_memo(gs)
    v = provenance_firewall([memo], gs, declared=["decision_memo"])
    ok("governed decision_memo passes the firewall", v.ok)
    ok("render carries provenance ids", "← governed:c1" in render(memo))

    # 2. ORPHAN (a slot with no governed pre-image) is REJECTED — the core invariant.
    orphan = Deliverable("spec", [Slot("Claim", "ghost", "Feature X definitely 10x's retention.")])
    v = provenance_firewall([orphan], gs, declared=["spec"])
    ok("orphan element (no governed source) is REJECTED", (not v.ok) and any("ORPHAN" in m for m in v.violations))

    # 3. PARAPHRASE DRIFT (dropping the scope qualifier) is REJECTED — the thing we'd most likely botch.
    drift = Deliverable("spec", [Slot("Claim", "c1", "Feature X lifts activation by 3-5%.")])  # dropped 'under E'
    v = provenance_firewall([drift], gs, declared=["spec"])
    ok("paraphrase drift (dropped qualifier) is REJECTED", (not v.ok) and any("DRIFT" in m for m in v.violations))

    # 4. REUSE (two slots cite one governed element) is ALLOWED — total, not injective.
    reuse = Deliverable("spec", [Slot("A", "c1", gs.by_id("c1").text), Slot("B", "c1", gs.by_id("c1").text)])
    ok("reuse (many-to-one) is ALLOWED", provenance_firewall([reuse], gs, ["spec"]).ok)

    # 4b. ARGUMENT GRAPH: a relation ("evidence supports claim") is licensed ONLY by a governed edge — the
    #     anti-strawman core (connective tissue is a claim about relations, so it must be governed too).
    gs_e = GovernedState(list(gs.elements), edges=[GovernedEdge("e1", "SUPPORTS", "c1")])
    licensed = Deliverable("spec", [Slot("Claim", "c1", gs.by_id("c1").text), Slot("Ev", "e1", gs.by_id("e1").text)],
                           relations=[Relation("e1", "SUPPORTS", "c1")])
    ok("a governed edge LICENSES the relation", provenance_firewall([licensed], gs_e, ["spec"]).ok)
    unlicensed = Deliverable("spec", [Slot("Claim", "c1", gs.by_id("c1").text)],
                             relations=[Relation("e1", "SUPPORTS", "c1")])  # gs has no edges
    v = provenance_firewall([unlicensed], gs, ["spec"])
    ok("an UNLICENSED relation (no governed edge) is REJECTED — no laundered rhetoric",
       (not v.ok) and any("UNLICENSED RELATION" in m for m in v.violations))
    ok("render stamps the licensing edge on the argument",
       "governed-edge:e1-SUPPORTS-c1" in render(licensed, gs_e))

    # 4c. UNIFICATION: a research-map carrier adapts straight into a GovernedState (same object).
    carrier = {"nodes": [{"id": "t1", "type": "thesis", "label": "T", "detail": "Thesis T (hardened)."},
                         {"id": "g1", "type": "gap", "label": "G", "detail": "Evidence gap G."}],
               "edges": [{"from": "g1", "to": "t1", "relation": "CHALLENGES"}]}
    g_from_map = governed_state_from_carrier(carrier)
    ok("research-map carrier adapts to a GovernedState", {"t1", "g1"} <= g_from_map.ids()
       and g_from_map.has_edge("g1", "CHALLENGES", "t1"))
    ok("map's gap becomes a decision-memo finding (research map == governed graph)",
       any(s.label == "Adversarial finding" for s in decision_memo(g_from_map).slots))

    # 5. CHERRY-PICK: a declared deliverable silently dropped is REJECTED; a stub-with-reason is ACCEPTED.
    v = provenance_firewall([memo], gs, declared=["decision_memo", "risk_register"])
    ok("silently dropping a declared deliverable is REJECTED", (not v.ok)
       and any("cherry-pick" in m for m in v.violations))
    stub = Deliverable("risk_register", stub_reason="claim refuted at n=2000; no risk surface to report")
    ok("an accounted stub satisfies set-completeness",
       provenance_firewall([memo, stub], gs, ["decision_memo", "risk_register"]).ok)

    # 6. verbatim-modulo-whitespace only (normalizer is NOT semantic).
    ok("normalizer collapses whitespace, nothing more", normalize("a   b\n c") == "a b c")

    # 7. governed_state_from_run + produce_scenario_artifacts end-to-end (writes governed files, stubs the rest).
    import tempfile
    from pathlib import Path as _P

    gs2 = governed_state_from_run(
        claim="Feature X lifts activation by 3-5% under bounded evidence E.",
        evidence="Interview cohort n=12; 9 cited the missing step.",
        falsifiers=["If the A/B shows <1% lift at n=2000, the claim is dead."])
    ok("governed_state_from_run builds hardened elements", {"claim.hardened", "evidence.bound", "falsifier.0"} <= gs2.ids())
    out = tempfile.mkdtemp()
    report = produce_scenario_artifacts(declared=["decision_memo", "gantt_chart"], governed=gs2, out_dir=out)
    ok("produce writes the governed decision_memo", "decision_memo" in report["written"]
       and _P(out, "decision_memo.md").exists())
    ok("an untemplated declared deliverable is an accounted stub, not fabricated",
       _P(out, "gantt_chart.md").exists() and "Omitted" in _P(out, "gantt_chart.md").read_text()
       and "gantt_chart" not in report["written"])
    ok("provenance_report is emitted", _P(out, "provenance_report.md").exists())
    ok("a run emits the interim governed artifact + a verdict", _P(out, "governed_artifact.json").exists()
       and "verdict" in report)
    # deliverable renders the ARGUMENT (edge-licensed relations), not just a list, when the graph has edges.
    gs_arg = GovernedState([GovernedElement("c1", "claim", "C"), GovernedElement("e1", "evidence", "E")],
                           [GovernedEdge("e1", "SUPPORTS", "c1")])
    ok("deliverable carries the governed argument (edge-licensed relations)",
       len(decision_memo(gs_arg).relations) == 1
       and provenance_firewall([decision_memo(gs_arg)], gs_arg, ["decision_memo"]).ok)
    ok("decision_memo.md cites hardened claim verbatim + provenance id",
       "under bounded evidence E" in _P(out, "decision_memo.md").read_text()
       and "← governed:claim.hardened" in _P(out, "decision_memo.md").read_text())

    # 8. COMPOUNDER — the GROUNDED verdict (argument kernel). Support must be EVIDENCE-ROOTED; an attacker only
    #    refutes if IT is accepted (a declared falsifier is a watch-condition, not an active refutation — grounded
    #    ABA semantics, strictly more correct than the old any-in-edge fold).
    ok("verdict SUPPORTED when a claim is grounded (evidence → claim), no open findings",
       assemble_verdict(GovernedState([GovernedElement("c1", "claim", "C"), GovernedElement("e1", "evidence", "E")],
                                      [GovernedEdge("e1", "SUPPORTS", "c1")])).status == "SUPPORTED")
    ok("verdict BLOCKED on an unresolved gap (honest, not forced)",
       assemble_verdict(GovernedState([GovernedElement("c1", "claim", "C"), GovernedElement("e1", "evidence", "E"),
                                       GovernedElement("g1", "gap", "open")],
                                      [GovernedEdge("e1", "SUPPORTS", "c1")])).status == "BLOCKED")
    ok("verdict REFUTED when an ACCEPTED (evidence) node attacks the claim",
       assemble_verdict(GovernedState([GovernedElement("c1", "claim", "C"), GovernedElement("obs", "evidence", "R")],
                                      [GovernedEdge("obs", "FALSIFIES", "c1")])).status == "REFUTED")
    ok("a DECLARED falsifier (not evidence-backed) does NOT refute — it's a watch-condition (grounded ABA)",
       assemble_verdict(GovernedState(
           [GovernedElement("c1", "claim", "C"), GovernedElement("e1", "evidence", "E"),
            GovernedElement("f1", "falsifier", "F")],
           [GovernedEdge("e1", "SUPPORTS", "c1"), GovernedEdge("f1", "FALSIFIES", "c1")])).status == "SUPPORTED")
    # 8b. multi-claim: one ungrounded claim ⇒ BLOCKED; all grounded ⇒ SUPPORTED.
    multi = GovernedState([GovernedElement("c1", "claim", "C1"), GovernedElement("c2", "claim", "C2"),
                           GovernedElement("e1", "evidence", "E1")],
                          [GovernedEdge("e1", "SUPPORTS", "c1")])   # c2 is ungrounded
    ok("multi-claim graph with one ungrounded claim is BLOCKED, not SUPPORTED",
       assemble_verdict(multi).status == "BLOCKED")
    ok("all-claims-grounded is SUPPORTED",
       assemble_verdict(GovernedState(list(multi.elements) + [GovernedElement("e2", "evidence", "E2")],
                        [GovernedEdge("e1", "SUPPORTS", "c1"), GovernedEdge("e2", "SUPPORTS", "c2")])).status
       == "SUPPORTED")

    # 8c. SUBSUMED (#36): load-bearing is the assumption in the most MINIMAL CORES (ATMS) — subsumes the old
    #     single-toggle sensitivity AND catches jointly-pivotal sets it could not see.
    from ztare.scenarios.argument_kernel import minimal_cores as _mc
    piv = GovernedState(
        [GovernedElement("t", "thesis", "T"), GovernedElement("c", "claim", "C"),
         GovernedElement("e", "evidence", "E")],
        [GovernedEdge("e", "SUPPORTS", "c"), GovernedEdge("c", "SUPPORTS", "t")])
    ok("load-bearing is a pivotal assumption (a minimal core), not graph degree",
       assemble_verdict(piv).load_bearing == "c" and frozenset({"c"}) in _mc(piv))
    ok("load-bearing '' when there are no claims", assemble_verdict(GovernedState()).load_bearing == "")
    ok("coverage is the grounded-accepted claim fraction",
       assemble_verdict(piv).coverage == 1.0 and _coverage(GovernedState()) == 0.0)
    ser = serialize_governed(piv, verdict=assemble_verdict(piv))
    ok("serialize carries the authoritative argument analysis (cores/agenda), not a kernel template",
       "argument" in ser and any("c" in core for core in ser["argument"]["minimal_cores"]))

    # 8d. LIFECYCLE FSM (feedback #1): the four statuses are the states of a canonical transition chart.
    ok("claim-lifecycle chart has the four statuses as states + evidence/counter transitions",
       CLAIM_LIFECYCLE.next_state("UNTESTED", "bind_evidence") == "BACKED"
       and CLAIM_LIFECYCLE.next_state("UNTESTED", "counter_evidence") == "CONTRADICTED"
       and CLAIM_LIFECYCLE.next_state("BACKED", "counter_evidence") == "CONTRADICTED")

    # 9. deliverable boundary (Fable): interim artifact is emittable; re-ingest gate catches ungoverned polish.
    ser = serialize_governed(gs, verdict=assemble_verdict(gs))
    ok("interim governed artifact serializes with schema + polish warning",
       ser["schema"] == "ztare-governed-artifact-v1" and "UNGOVERNED" in ser["downstream_polish"])
    good = reingest_gate("# Memo\n" + gs.by_id("c1").text, gs)
    ok("re-ingest passes a governed sentence", good.ok)
    bad = reingest_gate("Therefore we should ship immediately and it definitely 10x's retention.", gs)
    ok("re-ingest FLAGS an ungoverned polished sentence (credential-transfer guard)",
       (not bad.ok) and any("UNGOVERNED" in m for m in bad.violations))
    # 9b. HOLE (1a) CLOSED: a laundered claim written as a BULLET / quote / table cell is gated, not skipped.
    ok("re-ingest FLAGS an unsupported claim hidden in a markdown bullet",
       not reingest_gate("- We will 10x revenue next quarter.", gs).ok)
    ok("re-ingest FLAGS an unsupported claim in a block-quote", not reingest_gate("> Guaranteed 10x.", gs).ok)
    ok("re-ingest FLAGS an unsupported claim in a table cell",
       not reingest_gate("| Metric | We will 10x revenue |", gs).ok)
    # 9c. HOLE (1b) CLOSED: dropping a scope qualifier from a governed claim no longer passes (containment gap).
    dropped = reingest_gate("Feature X lifts activation by 3-5%.", gs)   # dropped 'under bounded evidence E'
    ok("re-ingest FLAGS a governed claim with its scope qualifier dropped (no substring pass)",
       (not dropped.ok) and any("UNGOVERNED" in m for m in dropped.violations))
    ok("re-ingest still passes a governed deliverable rendered with headings + provenance stamps",
       reingest_gate(render(decision_memo(gs)), gs).ok)
    # terminal-punctuation robustness: a governed claim stored WITHOUT end punctuation still matches its
    # rendered sentence WITH a period — but this must NOT reopen the qualifier-drop hole.
    gsx = GovernedState([GovernedElement("cx", "claim", "Latency drops 30% under load L")])  # no end period
    ok("re-ingest matches a governed claim + a rendered trailing period",
       reingest_gate("Latency drops 30% under load L.", gsx).ok)
    ok("terminal-punctuation robustness does NOT reopen qualifier-drop",
       not reingest_gate("Latency drops 30%.", gsx).ok)
    # 9d. reingest UPDATE PATH (feedback #2): session → diff → promote-only-if-traces + base-hash binding.
    import tempfile as _tf
    from pathlib import Path as _PP
    clean = gs.by_id("c1").text + "\n\n" + gs.by_id("e1").text
    sess = open_reingest_session("proj", clean, gs)
    ok("a fully-governed polish opens a promotable session", sess.promotable and not sess.diff.ungoverned)
    dirty = open_reingest_session("proj", clean + "\nTherefore we should 10x ship.", gs)
    ok("an ungoverned sentence makes the session NON-promotable", not dirty.promotable and dirty.diff.ungoverned)
    _out = str(_PP(_tf.mkdtemp(), "promoted.md"))
    res = promote_reingest(sess, clean, gs, _out, at="2026-07-09")
    ok("promote writes the artifact + a .reingest.json audit record when governed",
       res["promoted"] and _PP(_out).exists() and _PP(_out).with_suffix(".reingest.json").exists())
    ok("promote REFUSES an ungoverned polish", not promote_reingest(dirty, clean, gs, _out)["promoted"])
    stale = ReingestSession("proj", "deadbeefdeadbeef", sess.diff, True)   # wrong base hash
    ok("promote REFUSES when the base governed state shifted (hash mismatch)",
       not promote_reingest(stale, clean, gs, _out)["promoted"])

    # 10. ANNOTATE — the annotated-PRD round-trip (inverse firewall). Statuses are claim LIFECYCLE, doc is INPUT.
    ann_gs = GovernedState(
        [GovernedElement("c1", "claim", "Feature X lifts activation by 3-5% under bounded evidence E."),
         GovernedElement("e1", "evidence", "Interview cohort n=12; 9 cited the missing step."),
         GovernedElement("c2", "claim", "The migration is a two-way door."),
         GovernedElement("f9", "evidence", "The migration cannot be rolled back after conversion.")],
        [GovernedEdge("e1", "SUPPORTS", "c1"), GovernedEdge("f9", "CONTRADICTS", "c2")])
    prd = ("Feature X lifts activation by 3-5% under bounded evidence E. "  # aligns c1, SUPPORTS ⇒ BACKED
           "The migration is a two-way door. "                             # aligns c2, CONTRADICTS in-edge ⇒ CONTRADICTED
           "Users will obviously love the new flow. "                      # a surfaced (untested) assumption
           "This quarter has 13 weeks.")                                   # inert — nothing surfaced, no match
    anns = annotate(prd, ann_gs, surfaced_spans=["Users will obviously love the new flow"])
    by_status = {a.status for a in anns}
    ok("annotate BACKS a sentence aligned to a SUPPORTS'd claim",
       any(a.status == "BACKED" and a.element_id == "c1" for a in anns))
    ok("annotate marks a CONTRADICTED claim (FALSIFIES/CONTRADICTS in-edge)",
       any(a.status == "CONTRADICTED" and a.element_id == "c2" for a in anns))
    ok("annotate surfaces an UNTESTED load-bearing assumption (the hero state)",
       any(a.status == "UNTESTED" and a.element_id == "" for a in anns))
    ok("annotate leaves a plain sentence INERT (not a violation — doc is INPUT)",
       any(a.status == "INERT" for a in anns))
    ok("annotate covers all four lifecycle states on this PRD", by_status == set(ANNOTATION_STATUSES))
    _chart_states = ({r["state"] for r in CLAIM_LIFECYCLE.transition_table()}
                     | {r["next"] for r in CLAIM_LIFECYCLE.transition_table()})
    ok("the four annotation statuses are exactly the lifecycle-chart states",
       set(ANNOTATION_STATUSES) == _chart_states)
    # pre-run (empty governed state) cannot emit BACKED — but surfacing still works (the pre-run product).
    pre = annotate("Users will obviously love the new flow. Unrelated line.", GovernedState(),
                   surfaced_spans=["Users will obviously love the new flow"])
    ok("pre-run: no BACKED (empty graph), assumptions still surface (no mode switch)",
       not any(a.status == "BACKED" for a in pre) and any(a.status == "UNTESTED" for a in pre))
    rendered = render_annotated("prd.md", anns, rejected=["some anchor the surfacer could not verify"])
    ok("render_annotated leads with the assumption COUNT, not pass/fail",
       "load-bearing assumption(s)" in rendered and "FAIL" not in rendered and "PASS" not in rendered)
    ok("render_annotated footers the dropped surfacer anchors (coverage is inspectable)",
       "Dropped anchors" in rendered)

    print("ARTIFACTS SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
