import json
import hashlib
from pathlib import Path

from ztare.common.constraint_isomorphism import SurfacedConjecture, SurfacedIsomorphism
from ztare.common.kernel_action_schema import validate_kernel_action_schema
from ztare.research_director.research_isomorphism import (
    ResearchDomain,
    _cand_key,
    build_signed_experiment_verdict,
    closed_champion_fact_adjudicator,
    conjecture_between,
    debug_conjecture_for_seams,
    debug_query_for_seam,
    langlands_sweep,
    prescribe_for_seam,
    record_disposition,
    surface_for_research_ceiling,
)
from ztare.leanmill.formal_verification_provider import generate_keypair


def test_research_isomorphism_compiles_prescription_to_kernel_action_schema() -> None:
    domain = ResearchDomain()
    iso = SurfacedIsomorphism(
        theorem="Max-flow min-cut",
        field="network optimization",
        mechanism="dual certificate names the obstruction",
        mapping_hint="source residual -> target certificate",
    )

    prescription = domain.compile_to_test(iso, None)
    action = prescription.action_schema
    ok, missing = validate_kernel_action_schema(action or {})

    assert ok is True
    assert missing == []
    assert action is not None
    assert action["record_type"] == "kernel_action_schema"
    assert action["source_kind"] == "research_isomorphism"
    assert action["action_family"] == "structural_transfer"


def test_research_isomorphism_ledger_records_kernel_action_schema(tmp_path: Path) -> None:
    ledger = tmp_path / "research_isomorphism_candidates.jsonl"
    iso = SurfacedIsomorphism(
        theorem="Max-flow min-cut",
        field="network optimization",
        mechanism="dual certificate names the obstruction",
        mapping_hint="source residual -> target certificate",
    )

    surface_for_research_ceiling(
        {
            "constraint_class": "stalled residual needs certificate",
            "abstract_form": "target-side obstruction certificate",
            "home_field": "autoresearch",
        },
        query=lambda fp, n: [iso],
        ledger=ledger,
    )

    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    ok, missing = validate_kernel_action_schema(row["action_schema"])

    assert ok is True
    assert missing == []
    assert row["action_schema"]["target_mapping"] == "source residual -> target certificate"


def test_prescribe_for_seam_passes_typed_invariants(monkeypatch) -> None:
    import ztare.common.constraint_isomorphism as ci

    seen = {}

    def fake_query(fp, n, *, provider, model, typed_mapping, mode):
        seen.update(
            {
                "provider": provider,
                "model": model,
                "typed_mapping": typed_mapping,
                "mode": mode,
                "invariants": dict(fp.invariants),
                "n": n,
            }
        )
        return [
            SurfacedIsomorphism(
                theorem="Kruskal tensor uniqueness",
                field="multilinear algebra",
                mechanism="rank condition gives identifiable tensor factors",
                mapping_hint="scalar statistic -> identifiable preimage after rank receipt",
                invariant_map={"projection": "identifiable preimage after rank receipt"},
            )
        ]

    monkeypatch.setattr(ci, "default_llm_query", fake_query)

    rx = prescribe_for_seam(
        "many-to-one scalar projection loses tensor preimage",
        abstract_form="kernel contains distinct tensor states",
        home_field="fluid PDE",
        model="deepseek",
        n=3,
        invariants={"projection": "many_to_one"},
        typed_mapping=True,
    )

    assert rx["candidate_count"] == 1
    assert rx["source_theorem"] == "Kruskal tensor uniqueness"
    assert seen == {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "typed_mapping": True,
        "mode": "solve",
        "invariants": {"projection": "many_to_one"},
        "n": 3,
    }


def test_debug_query_for_seam_reports_parse_status(monkeypatch) -> None:
    import ztare.common.constraint_isomorphism as ci

    response = (
        '[{"theorem":"Whitney extension","field":"differential topology",'
        '"mechanism":"section obstruction","mapping_hint":"preimage selector",'
        '"invariant_map":{"projection":"quotient preimage"}}]'
    )

    dbg = debug_query_for_seam(
        "many-to-one scalar projection loses tensor preimage",
        abstract_form="kernel contains distinct tensor states",
        home_field="fluid PDE",
        model="deepseek",
        n=2,
        invariants={"projection": "many_to_one"},
        typed_mapping=True,
        dispatch=lambda *args, **kwargs: (response, {"transport": "test", "returncode": 0}),
    )

    assert dbg["provider"] == "deepseek"
    assert dbg["model"] == "deepseek-chat"
    assert dbg["parse_status"] == "parsed"
    assert dbg["candidate_count"] == 1
    assert dbg["candidates"][0]["theorem"] == "Whitney extension"
    assert dbg["candidates"][0]["field"] == "differential topology"
    assert dbg["candidates"][0]["transport_validation"]["status"] == "legacy_typed_mapping"


def test_conjecture_between_requires_both_lowerings_predictions_and_logs_schema(tmp_path: Path) -> None:
    ledger = tmp_path / "research_isomorphism_candidates.jsonl"
    good = SurfacedConjecture(
        mother_structure="budgeted motion object",
        lowerings={
            "left": {"pause_signal": "budget stall", "mover": "motion leg"},
            "right": {"clock_rate": "budget decrement", "counter": "motion leg"},
        },
        novel_predictions={
            "left": ["within 20 actions a clock-rate perturbation changes the pause state"],
            "right": ["within 20 actions a transit-pause analogue appears before counter depletion"],
        },
        kill_conditions={
            "left": ["refute if the pause state is unchanged after 20 actions under the perturbation"],
            "right": ["refute if no pre-depletion pause-like state appears in 20 actions"],
        },
    )
    bad = SurfacedConjecture(
        mother_structure="decorative bridge",
        lowerings={"left": {"pause_signal": "x"}},
        novel_predictions={"left": ["something may happen"]},
        kill_conditions={"left": ["unclear"]},
    )

    out = conjecture_between(
        {
            "constraint_class": "transit pause with budgeted mover",
            "home_field": "arc",
            "pause_signal": "state_dependent_pause",
            "mover": "translation",
        },
        {
            "constraint_class": "clocked counter controls motion rate",
            "home_field": "arc",
            "clock_rate": "p/q",
            "counter": "monotone",
        },
        query=lambda left, right, n: [good, bad],
        ledger=ledger,
    )

    assert [c.mother_structure for c in out["conjectures"]] == ["budgeted motion object"]
    assert [c.mother_structure for c in out["rejected"]] == ["decorative bridge"]
    assert out["conjectures"][0].specificity and out["conjectures"][0].specificity > 0

    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert row["record_type"] == "conjectural_correspondence"
    assert row["mother_structure"] == "budgeted motion object"
    assert row["offline_adjudication"]["status"] == "not_run"
    ok, missing = validate_kernel_action_schema(row["action_schema"])
    assert ok is True
    assert missing == []
    assert row["action_schema"]["action_name"] == "conjectural_correspondence"


def test_conjecture_between_preserves_typed_prediction_cards(tmp_path: Path) -> None:
    ledger = tmp_path / "research_isomorphism_candidates.jsonl"
    conj = SurfacedConjecture(
        mother_structure="counterexample quotient transducer",
        lowerings={"left": {"residual": "counterexample class"}, "right": {"route": "quotient state"}},
        novel_predictions={
            "left": [{
                "prediction": "one quotient class explains the next failure",
                "measurement": "residual class hash after replay",
                "intervention": "rerun the same policy from the boundary state",
                "horizon": "within 3 transitions",
                "expected_observation": "same quotient id recurs",
                "novelty_reason": "raw coordinates vary while quotient id stays fixed",
            }],
            "right": [{
                "prediction": "strategy changes only after quotient id changes",
                "measurement": "selected action family",
                "intervention": "swap representative within same quotient class",
                "horizon": "one decision",
                "expected_observation": "same action family is selected",
                "novelty_reason": "local state alone would not force action invariance",
            }],
        },
        kill_conditions={
            "left": [{
                "refuter": "different quotient ids appear for equivalent failures",
                "gate": "frozen replay quotient audit",
                "receipt": "quotient_counterexample_receipt",
            }],
            "right": [{
                "refuter": "same quotient id selects different action families",
                "gate": "representative-swap policy audit",
                "receipt": "strategy_quotient_receipt",
            }],
        },
    )

    out = conjecture_between(
        {"constraint_class": "terminal residual quotient", "residual": "class"},
        {"constraint_class": "strategy routing quotient", "route": "class"},
        query=lambda left, right, n: [conj],
        ledger=ledger,
    )

    assert out["conjectures"][0].specificity == 1.0
    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    cards = row["prediction_cards"]
    assert cards[0]["measurement"] == "residual class hash after replay"
    assert cards[0]["gate"] == "frozen replay quotient audit"
    assert row["action_schema"]["payload"]["prediction_cards"][1]["receipt"] == "strategy_quotient_receipt"


def test_debug_conjecture_reports_parse_and_schema(monkeypatch) -> None:
    import json as _json
    import ztare.common.constraint_isomorphism as ci

    raw = [{
        "mother_structure": "typed probe scheduler",
        "lowerings": {"left": {"a": "probe"}, "right": {"b": "route"}},
        "novel_predictions": {
            "left": [{
                "prediction": "probe use changes the next gate outcome",
                "measurement": "gate outcome",
                "intervention": "toggle one probe before edit",
                "horizon": "within 4 attempts",
                "expected_observation": "outcome distribution changes",
                "novelty_reason": "surface evidence alone does not force this",
            }],
            "right": [{
                "prediction": "typed route lowers cycle count",
                "measurement": "routing cycles",
                "intervention": "assign typed next instrument",
                "horizon": "within 5 cards",
                "expected_observation": "fewer cycles",
                "novelty_reason": "local routing does not force this",
            }],
        },
        "kill_conditions": {
            "left": [{"refuter": "no outcome difference", "gate": "gate audit", "receipt": "left_receipt"}],
            "right": [{"refuter": "no cycle reduction", "gate": "routing audit", "receipt": "right_receipt"}],
        },
    }]

    dbg = debug_conjecture_for_seams(
        {"constraint_class": "left", "a": "1"},
        {"constraint_class": "right", "b": "2"},
        model="gemini",
        n=1,
        dispatch=lambda *args, **kwargs: (_json.dumps(raw), {"transport": "test", "returncode": 0}),
    )

    assert dbg["parse_status"] == "parsed"
    assert dbg["raw_candidate_count"] == 1
    assert dbg["candidate_count"] == 1
    assert dbg["candidates"][0]["prediction_cards"][0]["receipt"] == "left_receipt"


def test_langlands_sweep_pairs_fingerprints_under_budget(tmp_path: Path) -> None:
    calls = []
    conj = SurfacedConjecture(
        mother_structure="shared object",
        lowerings={"left": {"a": "x"}, "right": {"b": "y"}},
        novel_predictions={
            "left": ["state 2 must change within 3 actions"],
            "right": ["state 4 must fail before 5 actions"],
        },
        kill_conditions={
            "left": ["refute if state 2 remains fixed for 3 actions"],
            "right": ["refute if state 4 survives 5 actions"],
        },
    )

    def query(left, right, n):
        calls.append((left.constraint_class, right.constraint_class))
        return [conj]

    out = langlands_sweep(
        [
            {"constraint_class": "A", "a": "1"},
            {"constraint_class": "B", "b": "2"},
            {"constraint_class": "C", "c": "3"},
        ],
        budget=1,
        query=query,
        ledger=tmp_path / "cands.jsonl",
    )

    assert out["pairs_tested"] == 1
    assert calls == [("A", "B")]
    assert len(out["results"]) == 1


def test_conjecture_between_dedupes_by_prediction_behavior(tmp_path: Path) -> None:
    ledger = tmp_path / "research_isomorphism_candidates.jsonl"
    first = SurfacedConjecture(
        mother_structure="clocked hold-resource transducer",
        lowerings={"left": {"pause": "hold phase"}, "right": {"clock": "release phase"}},
        novel_predictions={
            "left": ["within 20 actions pause onsets fall into q-phase residues"],
            "right": ["within 20 actions non-gate phases are path-active holds"],
        },
        kill_conditions={
            "left": ["refute if no q-phase residue class predicts pause onsets"],
            "right": ["refute if non-gate phases reset or terminate the path"],
        },
    )
    twin = SurfacedConjecture(
        mother_structure="monotone escrow automaton",
        lowerings={"left": {"pause": "escrow phase"}, "right": {"clock": "release schedule"}},
        novel_predictions={
            "left": ["within 20 actions pause history is explained by an escrow release phase"],
            "right": ["within 20 actions idle ticks outside release boundaries preserve the path"],
        },
        kill_conditions={
            "left": ["refute if pause timing has no bounded phase explanation"],
            "right": ["refute if idle non-release ticks reset the path"],
        },
    )

    out = conjecture_between(
        {"constraint_class": "pause structure", "pause": "state"},
        {"constraint_class": "clock structure", "clock": "p/q"},
        query=lambda left, right, n: [first, twin],
        ledger=ledger,
    )

    assert [c.mother_structure for c in out["conjectures"]] == ["clocked hold-resource transducer"]
    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert row["duplicates"][0]["mother_structure"] == "monotone escrow automaton"
    assert row["behavior_key"]


def test_conjecture_between_blocks_offline_refuted_and_records_covered_side(tmp_path: Path) -> None:
    ledger = tmp_path / "research_isomorphism_candidates.jsonl"
    refuted = SurfacedConjecture(
        mother_structure="bad shared object",
        lowerings={"left": {"a": "x"}, "right": {"b": "y"}},
        novel_predictions={"left": ["unbounded phase drift appears within 3 actions"], "right": ["state 4 changes within 3 actions"]},
        kill_conditions={"left": ["refute if state 2 stays fixed"], "right": ["refute if state 4 stays fixed"]},
    )
    kept = SurfacedConjecture(
        mother_structure="partly covered object",
        lowerings={"left": {"a": "x"}, "right": {"b": "y"}},
        novel_predictions={"left": ["state 2 changes within 3 actions"], "right": ["state 4 changes within 3 actions"]},
        kill_conditions={"left": ["refute if state 2 stays fixed"], "right": ["refute if state 4 stays fixed"]},
    )

    out = conjecture_between(
        {"constraint_class": "left", "a": "1"},
        {"constraint_class": "right", "b": "2"},
        query=lambda left, right, n: [refuted, kept],
        offline_adjudicator=closed_champion_fact_adjudicator({
            "left": {"covered": ["state 2 changes"], "refuted": ["unbounded phase"]},
            "right": {},
        }),
        ledger=ledger,
    )

    # The first candidate is not blocked by name; it is blocked because its left-side
    # prediction/kill text matches a champion-derived refutation pattern.
    assert [c.mother_structure for c in out["conjectures"]] == ["partly covered object"]
    assert [c.mother_structure for c in out["rejected"]] == ["bad shared object"]
    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert row["offline_adjudication"]["status"] == "partially_covered"
    assert row["offline_adjudication"]["source"] == "closed_champion_facts"
    assert row["offline_adjudication"]["sides"]["right"]["status"] == "needs_live"


def test_survived_conjecture_disposition_registers_dictionary_entry(tmp_path: Path, monkeypatch) -> None:
    import ztare.common.constraint_isomorphism as ci

    ledger = tmp_path / "research_isomorphism_candidates.jsonl"
    dictionary = tmp_path / "research_isomorphism_dictionary.jsonl"
    conj = SurfacedConjecture(
        mother_structure="budgeted motion object",
        lowerings={"left": {"a": "x"}, "right": {"b": "y"}},
        novel_predictions={"left": ["state 2 changes within 3 actions"], "right": ["state 4 changes within 3 actions"]},
        kill_conditions={"left": ["refute if state 2 stays fixed"], "right": ["refute if state 4 stays fixed"]},
    )
    conjecture_between(
        {"constraint_class": "left", "a": "1"},
        {"constraint_class": "right", "b": "2"},
        query=lambda left, right, n: [conj],
        ledger=ledger,
    )
    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    evidence = tmp_path / "bounded_replay_1.json"
    evidence.write_text(json.dumps({"outcome": "survived", "candidate_hash": row["candidate_hash"]}))
    experiment_receipt = {
        "receipt_id": "bounded-replay-receipt-1",
        "experiment_id": "bounded-replay-1",
        "intervention_id": "bounded-replay-policy-v1",
        "evidence_ref": str(evidence),
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        "candidate_hash": row["candidate_hash"],
        "status": "verified",
        "outcome": "survived",
    }
    private_key, public_key = generate_keypair()
    experiment_receipt["experiment_verdict"] = build_signed_experiment_verdict(
        row,
        experiment_receipt,
        private_key_pem=private_key,
        verifier_ref="bounded-replay-verifier",
    )
    rec = record_disposition(
        _cand_key(row),
        "survived",
        "prediction survived bounded replay",
        ledger=ledger,
        dictionary=dictionary,
        experiment_receipt=experiment_receipt,
        trusted_public_key_pem=public_key,
    )

    assert rec["dictionary_entry"]["mother_structure"] == "budgeted motion object"
    dict_row = json.loads(dictionary.read_text(encoding="utf-8").splitlines()[0])
    assert dict_row["record_type"] == "learned_correspondence_dictionary_entry"
    assert dict_row["candidate_hash"] == row["candidate_hash"]
    assert dict_row["experiment_receipt"]["experiment_id"] == "bounded-replay-1"

    monkeypatch.setenv("ZTARE_RESEARCH_ISOMORPHISM_DICTIONARY", str(dictionary))
    prompt = ci._build_query_prompt(  # noqa: SLF001
        ResearchDomain().abstract_failure({"constraint_class": "new seam"}),
        2,
        mode="correspondence",
    )
    assert "budgeted motion object" in prompt
