"""Metrology — does the firewall actually DISCRIMINATE?

ZTARE's gates (`provenance_firewall`, `reingest_gate`, the argument-kernel `verdict`) are deterministic and
already exercised by their own module selftests — but a selftest only proves "this input passes / that input
fails" for the inputs its author picked. It never asks the harder question: against a labeled adversarial
corpus of KNOWN-sound and KNOWN-laundered cases, what is the gate's confusion matrix? Most "AI governance"
frameworks never measure this at all — they assert a gate works, they don't compute its precision/recall
against ground truth. That is what this module is for: a domain-neutral, no-LLM harness that runs the seed
corpus through each gate and reports the confusion matrix (+ MCC / Youden's J) so a discrimination failure
(a laundering case that slips through) is a visible number, not a vibe.

The seed corpus doubles as a POSITIVE-CONTROL battery: every `should_pass=False` case is a known-should-fail
input the gate must fail (the "run the gold control before trusting a metric" discipline) — `_selftest` asserts
zero misses and MCC==1.0 on it, i.e. the gates perfectly separate this labeled set.

The one genuinely novel piece: `formal_oracle_label` is the LeanMill hook for GROWING the corpus past hand-
labeled cases — kernel verification as a ground-truth label source for the formal substrate, instead of a
human eyeballing "should this pass?". It is opt-in and inert by default (see its docstring): the real
attack path dispatches an LLM to search for a proof, which this module's no-LLM charter forbids running
implicitly, and this environment happens to have a live Lean toolchain on PATH — so the only safe default is
off, never invoked by `_selftest`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from ztare.scenarios.argument_kernel import verdict
from ztare.scenarios.artifacts import (
    Deliverable, GovernedEdge, GovernedElement, GovernedState, Relation, Slot,
    decision_memo, provenance_firewall, reingest_gate, render,
)

FAMILIES = ("sound", "orphan", "drift", "unlicensed", "bullet", "qualifier_drop", "unsupported")


@dataclass(frozen=True)
class LabeledCase:
    """One adversarial-corpus entry: a gate to run, its input, and the GROUND-TRUTH label.

    `should_pass` is the ground truth, not the gate's opinion: True = a genuinely governed/sound input the
    gate MUST pass; False = a laundered/unsound input the gate MUST catch (reject). `payload` is gate-specific
    (see `run_gate`): firewall → (deliverables, governed, declared); reingest → (polished_text, governed);
    verdict → governed."""
    name: str
    kind: str          # "firewall" | "reingest" | "verdict"
    payload: object
    should_pass: bool
    family: str        # one of FAMILIES


def run_gate(case: LabeledCase) -> bool:
    """Run the gate `case` names and return PREDICTED-PASS (True = the gate calls this input sound). For a
    verdict case, 'pass' means the grounded verdict is SUPPORTED — the only status a sound, fully-evidenced
    claim graph should reach; BLOCKED/REFUTED both count as 'the gate did not wave this through'."""
    if case.kind == "firewall":
        deliverables, governed, declared = case.payload
        return provenance_firewall(deliverables, governed, declared).ok
    if case.kind == "reingest":
        polished, governed = case.payload
        return reingest_gate(polished, governed).ok
    if case.kind == "verdict":
        return verdict(case.payload) == "SUPPORTED"
    raise ValueError(f"unknown case kind: {case.kind!r}")


def seed_corpus() -> "list[LabeledCase]":
    """Balanced adversarial set: >=2 sound cases per gate, one case per named laundering family. Sound cases
    are genuinely governed (real evidence, verbatim slots, edge-licensed relations); unsound cases are minimal
    and pointed — one failure mode each, nothing else wrong, so a miss localizes to exactly one family."""
    gs = GovernedState([
        GovernedElement("c1", "claim", "Feature X lifts activation by 3-5% under bounded evidence E."),
        GovernedElement("e1", "evidence", "Interview cohort n=12; 9 cited the missing step."),
        GovernedElement("f1", "falsifier", "If the A/B shows <1% lift at n=2000, the claim is dead."),
    ])
    cases: "list[LabeledCase]" = []

    # --- firewall (total-provenance + verbatim + set-completeness + edge-licensing) ---
    cases.append(LabeledCase("firewall_governed_memo", "firewall",
                             ([decision_memo(gs)], gs, ["decision_memo"]), True, "sound"))
    reuse = Deliverable("spec", [Slot("A", "c1", gs.by_id("c1").text), Slot("B", "c1", gs.by_id("c1").text)])
    cases.append(LabeledCase("firewall_many_to_one_reuse", "firewall", ([reuse], gs, ["spec"]), True, "sound"))
    orphan = Deliverable("spec", [Slot("Claim", "ghost", "Feature X definitely 10x's retention.")])
    cases.append(LabeledCase("firewall_orphan_element", "firewall", ([orphan], gs, ["spec"]), False, "orphan"))
    drift = Deliverable("spec", [Slot("Claim", "c1", "Feature X lifts activation by 3-5%.")])  # dropped 'under E'
    cases.append(LabeledCase("firewall_paraphrase_drift", "firewall", ([drift], gs, ["spec"]), False, "drift"))
    unlicensed = Deliverable("spec", [Slot("Claim", "c1", gs.by_id("c1").text)],
                             relations=[Relation("e1", "SUPPORTS", "c1")])  # gs has no edges
    cases.append(LabeledCase("firewall_unlicensed_relation", "firewall",
                             ([unlicensed], gs, ["spec"]), False, "unlicensed"))

    # --- reingest (downstream-polish re-ingest gate) ---
    cases.append(LabeledCase("reingest_governed_sentence", "reingest",
                             ("# Memo\n" + gs.by_id("c1").text, gs), True, "sound"))
    cases.append(LabeledCase("reingest_rendered_memo", "reingest", (render(decision_memo(gs)), gs), True, "sound"))
    cases.append(LabeledCase("reingest_bullet_laundering", "reingest",
                             ("- We will 10x revenue next quarter.", gs), False, "bullet"))
    cases.append(LabeledCase("reingest_qualifier_drop", "reingest",
                             ("Feature X lifts activation by 3-5%.", gs), False, "qualifier_drop"))

    # --- verdict (grounded ABA acceptance) ---
    supported = GovernedState([GovernedElement("c1", "claim", "C1"), GovernedElement("e1", "evidence", "E1")],
                              [GovernedEdge("e1", "SUPPORTS", "c1")])
    cases.append(LabeledCase("verdict_direct_support", "verdict", supported, True, "sound"))
    chain = GovernedState(
        [GovernedElement("t", "thesis", "T"), GovernedElement("c", "claim", "C"),
         GovernedElement("e", "evidence", "E")],
        [GovernedEdge("e", "SUPPORTS", "c"), GovernedEdge("c", "SUPPORTS", "t")])
    cases.append(LabeledCase("verdict_evidence_chain_to_thesis", "verdict", chain, True, "sound"))
    circular = GovernedState(
        [GovernedElement("c1", "claim", "C1"), GovernedElement("c2", "claim", "C2")],
        [GovernedEdge("c1", "SUPPORTS", "c2"), GovernedEdge("c2", "SUPPORTS", "c1")])  # no evidence anchor
    cases.append(LabeledCase("verdict_circular_unsupported", "verdict", circular, False, "unsupported"))

    return cases


def discriminate(corpus: "list[LabeledCase]") -> dict:
    """The confusion matrix + derived metrics, computed by hand (no numpy/sklearn — this is ~12 cases).
    POSITIVE class = 'the gate flags this case as unsound' (predicted_pass is False). Ground-truth positive
    = should_pass is False (a laundered case). So: TP = laundering correctly caught; FN = a MISS — the
    dangerous case, an unsound input the gate waved through; FP = a sound case wrongly rejected; TN = a sound
    case correctly passed. All ratios guard div-by-zero (an empty or one-sided corpus returns 0.0, not NaN)."""
    tp = fp = tn = fn = 0
    per_family: "dict[str, dict]" = {}
    misses: "list[str]" = []
    for case in corpus:
        predicted_pass = run_gate(case)
        correct = predicted_pass == case.should_pass
        fam = per_family.setdefault(case.family, {"n": 0, "correct": 0, "cases": []})
        fam["n"] += 1
        fam["correct"] += int(correct)
        fam["cases"].append({"name": case.name, "should_pass": case.should_pass,
                             "predicted_pass": predicted_pass, "correct": correct})
        if case.should_pass:      # ground truth SOUND
            if predicted_pass:
                tn += 1
            else:
                fp += 1
        else:                      # ground truth UNSOUND (laundered)
            if predicted_pass:
                fn += 1
                misses.append(case.name)
            else:
                tp += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0             # a.k.a. sensitivity: unsound cases caught
    specificity = tn / (tn + fp) if (tn + fp) else 0.0        # sound cases correctly passed
    denom = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
    mcc = ((tp * tn) - (fp * fn)) / denom if denom else 0.0
    youden_j = recall + specificity - 1.0
    return {
        "n": len(corpus), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision, "recall": recall, "specificity": specificity,
        "mcc": mcc, "youden_j": youden_j,
        "per_family": per_family, "misses": misses,
    }


def formal_oracle_label(claim_text: str) -> "bool | None":
    """LeanMill oracle HOOK — the path to grow the corpus past hand-labeled cases: kernel-verified truth as
    the label source instead of a human eyeballing 'should this pass?'. Attempts to formalize `claim_text` as
    a campaign target and kernel-check it; True = kernel-verified (closed), False = kernel-refuted
    (target_false_as_stated), None = unavailable/inconclusive (open gap, deferred, or any error).

    Opt-in only (`ZTARE_METROLOGY_LIVE_ORACLE=1`): the real attack path (`autoformalize_and_solve`'s default
    `formalize_fn`/`solve_fn`) dispatches an LLM to search for a proof, and this module is domain-neutral/
    no-LLM by charter — so importing this function must never be enough to fire a live campaign. This is also
    why `_selftest` never sets the env var: growing the corpus this way is a deliberate, out-of-band run, not
    part of the deterministic gate check. Guarded end-to-end regardless — any import/timeout/parse/proof
    error degrades to None, never a crash and never a fabricated label."""
    if os.environ.get("ZTARE_METROLOGY_LIVE_ORACLE") != "1":
        return None  # inert by default — see docstring
    try:
        from ztare.leanmill.solver.autoformalize_notes import autoformalize_from_notes
        result = autoformalize_from_notes(f"## Target\n{claim_text}\n", lemma_timeout_s=30, target_timeout_s=120)
        target = result.get("target") or {}
        if target.get("solved"):
            return True
        if target.get("outcome") == "target_false_as_stated":
            return False
        return None  # open / deferred / gap — inconclusive, not a label
    except Exception:  # noqa: BLE001 — any failure is inconclusive, never a false label
        return None


# ── Reuse the ecosystem's labeled corpora for the SEMANTIC layer (don't hand-build one). ────────────────────
# The structural gates above are ZTARE-specific (provenance / set-completeness) — no public corpus tests them.
# But the SEMANTIC edge question — "does this evidence support / refute this claim?" — is exactly claim
# verification, and there ARE established labeled corpora: SciFact (allenai/scifact, ~1.4k, SUPPORT/CONTRADICT/
# NOINFO), FEVER (185k, SUPPORTED/REFUTED/NEI), VitaminC (~400k contrastive), SNLI/MNLI (entail/neutral/contra).
# Measuring an edge-proposer against these is the honest number for "how much to trust a W3 (LLM-proposed) edge"
# — i.e. it quantifies the warrant ladder, not the deterministic structural gates.
_LABEL_TO_STATUS = {  # dataset verdict label → ZTARE grounded status (NEI/NOINFO ⇒ BLOCKED)
    "SUPPORT": "SUPPORTED", "SUPPORTS": "SUPPORTED", "SUPPORTED": "SUPPORTED", "entailment": "SUPPORTED",
    "CONTRADICT": "REFUTED", "REFUTES": "REFUTED", "REFUTED": "REFUTED", "contradiction": "REFUTED",
    "NOT ENOUGH INFO": "BLOCKED", "NOTENOUGHINFO": "BLOCKED", "NEI": "BLOCKED", "neutral": "BLOCKED",
}


def edge_triples_from_jsonl(rows: "list[dict]") -> "list[dict]":
    """Normalize a claim-verification dataset (SciFact / FEVER / VitaminC / NLI, already read to dict rows) into
    `{claim, evidence, gold}` triples where `gold` ∈ {SUPPORTED, REFUTED, BLOCKED}. Tolerant of each dataset's
    field names. This is a LOADER, not a downloader — point it at a corpus you have (e.g. allenai/scifact)."""
    out: "list[dict]" = []
    for r in rows:
        claim = str(r.get("claim") or r.get("hypothesis") or r.get("sentence2") or "").strip()
        evidence = str(r.get("evidence") or r.get("premise") or r.get("sentence1")
                       or r.get("abstract") or r.get("evidence_text") or "").strip()
        label = r.get("label") or r.get("gold_label") or r.get("verdict")
        gold = _LABEL_TO_STATUS.get(str(label).strip()) if label is not None else None
        if claim and gold:
            out.append({"claim": claim, "evidence": evidence, "gold": gold})
    return out


def measure_edge_proposer(triples: "list[dict]", classify) -> dict:
    """Measure a SEMANTIC edge-proposer `classify(claim, evidence) -> 'SUPPORTED'|'REFUTED'|'BLOCKED'` against a
    labeled claim-verification corpus (the `edge_triples_from_jsonl` output) — the honest 'how good is a W3
    edge?' number. `classify` is the boundary (an NLI model, an LLM, or a rule) — INJECTED, so this harness
    stays deterministic. Returns accuracy + a 3×3 confusion by gold status. No classifier ⇒ a clear note (the
    measurement needs a proposer; the deterministic structural gates do not)."""
    if classify is None:
        return {"ok": False, "note": "inject an edge-classifier (NLI/LLM) to measure the semantic W3 layer"}
    n = correct = 0
    confusion: "dict[str, dict[str, int]]" = {}
    for t in triples:
        pred = str(classify(t["claim"], t["evidence"]) or "BLOCKED")
        confusion.setdefault(t["gold"], {}).setdefault(pred, 0)
        confusion[t["gold"]][pred] += 1
        n += 1
        correct += int(pred == t["gold"])
    return {"ok": True, "n": n, "accuracy": round(correct / n, 3) if n else 0.0, "confusion": confusion}


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    corpus = seed_corpus()
    families = {c.family for c in corpus}
    ok("corpus covers every named laundering family",
       {"orphan", "drift", "unlicensed", "bullet", "qualifier_drop", "unsupported"} <= families)
    ok("corpus has >=2 SOUND cases for every gate kind",
       all(sum(1 for c in corpus if c.kind == k and c.should_pass) >= 2
           for k in ("firewall", "reingest", "verdict")))

    result = discriminate(corpus)
    ok("zero MISSES — every unsound (laundered) case is caught", result["fn"] == 0 and not result["misses"])
    ok("zero false-rejects — every sound case passes", result["fp"] == 0)
    ok("MCC == 1.0 (the gates perfectly discriminate the seed corpus)", result["mcc"] == 1.0)
    ok("Youden's J == 1.0 (perfect separation)", result["youden_j"] == 1.0)
    ok("precision/recall/specificity all 1.0 on a perfectly-discriminating seed",
       result["precision"] == 1.0 and result["recall"] == 1.0 and result["specificity"] == 1.0)

    # div-by-zero guard: a one-sided (all-sound) corpus must not raise or return NaN.
    guard = discriminate([c for c in corpus if c.should_pass])
    ok("discriminate guards div-by-zero on a degenerate all-sound corpus",
       guard["tp"] == 0 and guard["fn"] == 0 and guard["mcc"] == 0.0 and guard["precision"] == 0.0)

    label = formal_oracle_label("Feature X lifts activation by 3-5% under bounded evidence E.")
    ok("formal_oracle_label returns None-or-bool without crashing (inert unless opted in)",
       label is None or isinstance(label, bool))
    ok("formal_oracle_label is inert by default (no live LeanMill campaign from the selftest)", label is None)

    print("--- discrimination report ---")
    print(f"  n={result['n']}  tp={result['tp']} fp={result['fp']} tn={result['tn']} fn={result['fn']}")
    print(f"  precision={result['precision']:.3f} recall={result['recall']:.3f} "
          f"specificity={result['specificity']:.3f} MCC={result['mcc']:.3f} J={result['youden_j']:.3f}")
    for fam in sorted(result["per_family"]):
        stats = result["per_family"][fam]
        print(f"  [{fam}] {stats['correct']}/{stats['n']} correct")
    if result["misses"]:
        print(f"  MISSES (dangerous — unsound case NOT caught): {result['misses']}")

    # Semantic-layer corpus loader (reuse SciFact/FEVER/NLI — don't hand-build). Inline SciFact-shaped sample.
    triples = edge_triples_from_jsonl([
        {"claim": "Drug X lowers LDL", "evidence": "In the RCT, drug X reduced LDL by 20%.", "label": "SUPPORT"},
        {"claim": "Drug X raises LDL", "evidence": "In the RCT, drug X reduced LDL by 20%.", "label": "CONTRADICT"},
        {"claim": "Drug X cures cancer", "evidence": "The RCT measured LDL only.", "label": "NOT ENOUGH INFO"}])
    ok("corpus loader maps a claim-verification dataset to {claim,evidence,gold} triples",
       len(triples) == 3 and {t["gold"] for t in triples} == {"SUPPORTED", "REFUTED", "BLOCKED"})
    ok("edge-proposer measurement needs an injected classifier (no silent fabrication)",
       measure_edge_proposer(triples, None)["ok"] is False)
    perfect = measure_edge_proposer(triples, lambda c, e: {t["claim"]: t["gold"] for t in triples}[c])
    ok("a perfect classifier scores accuracy 1.0 on the sample (measurement wired)",
       perfect["ok"] and perfect["accuracy"] == 1.0)

    print("METROLOGY SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
