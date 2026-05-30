from pathlib import Path
import importlib.util


SCRIPT_PATH = Path("projects/ns_millennium_hunt/scripts/ns_discovery_preflight.py").resolve()


def _load_module():
    spec = importlib.util.spec_from_file_location("ns_discovery_preflight", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_emits_kernel_rerank_consumable_labels() -> None:
    module = _load_module()
    preflight = module.build_preflight(
        "unshadowed positive Duhamel source with signed average and "
        "quadratic reserve claims q > 5/2 weak-Lq tail"
    )

    labels = preflight["machine_labels"]
    assert labels["normal_form_classification"] == "COUNTERMODEL_HIT"
    assert labels["best_normal_form_id"] == "DuhamelPositiveTailUpgrade"
    assert "DuhamelPositiveTailUpgrade" in labels["normal_form_candidate_ids"]
    assert "two_packet_positive_tail_concentration" in labels["packet_countermodel_hits"]
    assert "positive_tail_vs_quadratic_reserve" in labels["currency_rule_hits"]

    consumable = preflight["future_kernel_rerank_consumption"]
    assert consumable["residual_class_label"] == "DuhamelPositiveTailUpgrade"
    assert "DuhamelPositiveTailUpgrade" in consumable["residual_candidate_labels"]
    assert "two_packet_positive_tail_concentration" in consumable["hard_negative_labels"]


def test_theorem_applicability_partial_for_one_component_missing_ckn() -> None:
    module = _load_module()
    preflight = module.build_preflight(
        "near-2D one-component route with u_3 small on a local cylinder, "
        "but only amplitude ratio and local lower badness are available"
    )

    theorem_rows = {
        row["template_id"]: row
        for row in preflight["theorem_applicability"]["rows"]
    }
    krz = theorem_rows["krz_one_component_regular"]
    assert krz["verdict"] == "PARTIAL"
    assert "uniform_ckn_upper_bound" in krz["missing_fields"]
    assert "amplitude ratio" in krz["not_enough_hits"]


def test_same_region_reuse_maps_to_nested_reuse_without_duhamel_tail_noise() -> None:
    module = _load_module()
    preflight = module.build_preflight(
        "same-region reuse guard where each active tail is paid by a reused unit "
        "charge from the same packet lineage, despite a claimed fresh annular "
        "charge or monotone reserve drop"
    )

    labels = preflight["machine_labels"]
    assert labels["normal_form_classification"] == "COUNTERMODEL_HIT"
    assert labels["best_normal_form_id"] == "ScaleFreshCriticalDebit"
    assert "nested_dirac_reuse" in labels["packet_countermodel_hits"]
    assert "positive_flux_nested_reuse" in labels["packet_countermodel_hits"]
    assert "two_packet_positive_tail_concentration" not in labels["packet_countermodel_hits"]
    assert "fresh_charge_vs_scalar_measure" in labels["currency_rule_hits"]


def test_semantic_normalizer_hints_feed_gates_without_becoming_authority(monkeypatch) -> None:
    module = _load_module()

    def fake_semantic_normalize(*_args, **_kwargs):
        return {
            "enabled": True,
            "status": "ok",
            "provider": "openai",
            "feature_hits": [
                {"feature": "positive_carrier", "hits": ["billed over and over"]},
                {"feature": "freshness", "hits": ["no new reserve"]},
                {"feature": "nested_reuse", "hits": ["billed over and over"]},
                {"feature": "local_same_carrier", "hits": ["single local certificate"]},
            ],
            "candidate_normal_forms": [
                {"normal_form_id": "ScaleFreshCriticalDebit", "confidence": "high"}
            ],
        }

    monkeypatch.setattr(module, "semantic_normalize_with_openai", fake_semantic_normalize)
    preflight = module.build_preflight(
        "A single local certificate is billed over and over, with no new reserve.",
        semantic_normalize=True,
    )

    labels = preflight["machine_labels"]
    assert labels["semantic_status"] == "ok"
    assert labels["normal_form_classification"] == "COUNTERMODEL_HIT"
    assert labels["best_normal_form_id"] == "ScaleFreshCriticalDebit"
    assert "positive_flux_nested_reuse" in labels["packet_countermodel_hits"]
    assert "positive_carrier" in labels["semantic_feature_ids"]


def test_semantic_falsifier_hints_are_not_consumed_as_proposal_features(monkeypatch) -> None:
    module = _load_module()

    def fake_semantic_normalize(*_args, **_kwargs):
        return {
            "enabled": True,
            "status": "ok",
            "provider": "openai",
            "feature_hits": [
                {"feature": "positive_carrier", "hits": ["activeTail demand"]},
                {"feature": "freshness", "hits": ["fresh same-carrier reserve"]},
                {"feature": "local_same_carrier", "hits": ["same-carrier reserve"]},
            ],
            "falsifier_feature_hits": [
                {"feature": "nested_reuse", "hits": ["killed by nested reuse"]},
            ],
            "negated_feature_hits": [],
            "candidate_normal_forms": [
                {"normal_form_id": "ScaleFreshCriticalDebit", "confidence": "high"}
            ],
        }

    monkeypatch.setattr(module, "semantic_normalize_with_openai", fake_semantic_normalize)
    preflight = module.build_preflight(
        "fresh same-carrier reserve theorem paying activeTail demand",
        semantic_normalize=True,
    )

    labels = preflight["machine_labels"]
    assert labels["normal_form_classification"] == "STRICTLY_NARROWER"
    assert labels["packet_countermodel_hits"] == []
    assert "nested_reuse" in labels["semantic_falsifier_feature_ids"]
    assert "nested_reuse" not in labels["semantic_feature_ids"]


def test_semantic_defeat_language_is_not_consumed_as_packet_feature(monkeypatch) -> None:
    module = _load_module()

    def fake_semantic_normalize(*_args, **_kwargs):
        return {
            "enabled": True,
            "status": "ok",
            "provider": "openai",
            "feature_hits": [
                {"feature": "positive_carrier", "hits": ["activeTail demand"]},
                {"feature": "freshness", "hits": ["fresh same-carrier reserve"]},
                {"feature": "local_same_carrier", "hits": ["same-carrier reserve"]},
                {"feature": "nested_reuse", "hits": ["defeats nested Dirac reuse"]},
            ],
            "falsifier_feature_hits": [],
            "negated_feature_hits": [],
            "candidate_normal_forms": [
                {"normal_form_id": "ScaleFreshCriticalDebit", "confidence": "high"}
            ],
        }

    monkeypatch.setattr(module, "semantic_normalize_with_openai", fake_semantic_normalize)
    preflight = module.build_preflight(
        "fresh same-carrier reserve theorem paying activeTail demand and "
        "defeats nested Dirac reuse",
        semantic_normalize=True,
    )

    labels = preflight["machine_labels"]
    assert labels["normal_form_classification"] == "STRICTLY_NARROWER"
    assert labels["packet_countermodel_hits"] == []
    assert labels["currency_rule_hits"] == []


def test_deterministic_negated_reuse_terms_do_not_trigger_packet_hits() -> None:
    module = _load_module()
    preflight = module.build_preflight(
        "fresh same-carrier finite-prefix matching source with active tail "
        "payment, no descendant capacity reuse, no same-capacity descendant "
        "rebilling, and not a scalar ledger"
    )

    labels = preflight["machine_labels"]
    assert labels["normal_form_classification"] == "STRICTLY_NARROWER"
    assert labels["packet_countermodel_hits"] == []


def test_owner_atom_rebilling_countermodel_hits_nested_reuse() -> None:
    module = _load_module()
    preflight = module.build_preflight(
        "Owner-map rebilling guard: a pointwise event-to-owner assignment plus "
        "a finite atom budget is still not a prefix budget. One owner atom can "
        "own every selected event; each event is paid pointwise, the atom-charge "
        "prefix is bounded, and the event prefix exceeds any finite target."
    )

    labels = preflight["machine_labels"]
    assert labels["normal_form_classification"] == "COUNTERMODEL_HIT"
    assert "nested_dirac_reuse" in labels["packet_countermodel_hits"]
    assert "positive_flux_nested_reuse" not in labels["packet_countermodel_hits"]


def test_leray_budget_does_not_pay_critical_source_square() -> None:
    module = _load_module()
    preflight = module.build_preflight(
        "C7 annular renewal budget from finite Leray energy dissipation only: "
        "the critical source square for P_N div(u tensor u) or the localized "
        "paraproduct source Carleson demand can diverge while the energy-level "
        "Leray budget remains finite."
    )

    labels = preflight["machine_labels"]
    assert labels["normal_form_classification"] == "COUNTERMODEL_HIT"
    assert "leray_energy_vs_critical_source_square" in labels["packet_countermodel_hits"]
    assert "critical_source_square_vs_leray_energy" in labels["currency_rule_hits"]


def test_energy_skew_cancellation_does_not_pay_positive_source_square() -> None:
    module = _load_module()
    preflight = module.build_preflight(
        "Use divergence-free energy skew-symmetry or Leray projection "
        "cancellation to control the positive source square of P_N div(u_N "
        "tensor u_N) on selected C7 tents. The proposal relies on testing "
        "against velocity, not on a packetwise null-form source theorem."
    )

    labels = preflight["machine_labels"]
    assert labels["normal_form_classification"] == "COUNTERMODEL_HIT"
    assert "energy_skew_vs_positive_source_square" in labels["packet_countermodel_hits"]
    assert "positive_source_square_vs_energy_skew" in labels["currency_rule_hits"]


def test_supplied_source_square_escape_blocks_leray_packet_hit() -> None:
    module = _load_module()
    preflight = module.build_preflight(
        "Type-I envelope critical source-square source with an amplitude "
        "frequency ratio bound: the critical source square for P_N div(u "
        "tensor u) is paid by dissipation only after this source-square "
        "theorem is supplied, not from bare Leray energy."
    )

    labels = preflight["machine_labels"]
    assert "leray_energy_vs_critical_source_square" not in labels["packet_countermodel_hits"]
    packet_rows = {
        row["packet_id"]: row
        for row in preflight["packet_suite"]["packets"]
    }
    assert packet_rows["leray_energy_vs_critical_source_square"]["status"] == "BLOCKED_BY_ESCAPE"
