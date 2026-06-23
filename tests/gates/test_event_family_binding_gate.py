from ztare.gates.event_family_binding_gate import (
    run_event_family_binding_gate,
)


def test_event_family_binding_flags_label_only_transfer() -> None:
    result = run_event_family_binding_gate({
        "target_event_family": "H-prefix events",
        "source_event_family": "suitable LEI event tents",
        "same_label": "local high-interface events",
        "both_finite_prefix": True,
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert "event_identity" in result["missing_fields"]
    assert any(
        v["type"] == "event_family_binding_replaced_by_weak_substitutes"
        for v in result["violations"]
    )


def test_event_family_binding_accepts_pre_payoff_identity_receipt() -> None:
    result = run_event_family_binding_gate({
        "target_event_family": "H-prefix events",
        "source_event_family": "suitable LEI event tents",
        "event_identity": "H_event n = LEI_event n for every n<N",
        "pre_payoff_timing": "event family and index map fixed before payoff",
        "same_carrier": "same local-energy carrier",
        "same_owner_or_source": "same owner-root prefix",
        "index_map": "n maps to n",
        "index_map_total_on_prefix": "all n<N are covered",
        "no_proxy_family": "not a scalar threshold proxy",
        "no_post_payoff_selection": "not selected from final deficit",
    })

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["violations"] == []


def test_event_family_binding_blocks_declared_proxy_confuser() -> None:
    result = run_event_family_binding_gate(
        {
            "target_event_family": "H-prefix events",
            "source_event_family": "suitable LEI event tents",
            "event_identity": "H_event n = LEI_event n for every n<N",
            "pre_payoff_timing": "event family and index map fixed before payoff",
            "same_carrier": "same local-energy carrier",
            "same_owner_or_source": "same owner-root prefix",
            "index_map": "n maps to n",
            "index_map_total_on_prefix": "all n<N are covered",
            "no_proxy_family": "not a scalar threshold proxy",
            "no_post_payoff_selection": "not selected from final deficit",
            "known_proxy_family_confuser": "H lives on a threshold proxy",
        },
        enforce_block=True,
    )

    assert result["passed"] is False
    assert any(
        v["type"] == "event_family_binding_proxy_confuser_declared"
        for v in result["violations"]
    )


def test_event_family_binding_accepts_dominated_injection_receipt() -> None:
    result = run_event_family_binding_gate({
        "relation_type": "dominated_injection",
        "target_event_family": "selected topology events",
        "source_event_family": "fresh-frequency same-tree events",
        "dominating_event_injection": "pre-payoff injection from selected topology events to fresh-frequency events",
        "domination_inequality": "selected prefix cost <= fresh-frequency budget + viscous error",
        "error_or_loss_budget": "viscous reconnection error prefix is budgeted",
        "pre_payoff_timing": "event map fixed before payoff",
        "same_carrier": "same pressure/Duhamel carrier after transfer",
        "same_owner_or_source": "same owner tree",
        "index_map": "selected n maps to fresh event j(n)",
        "index_map_total_on_prefix": "all selected n<K covered",
        "no_proxy_family": "not merely a bad-center shell proxy",
        "no_post_payoff_selection": "not selected after pressure-null failure",
    })

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["relation_type"] == "dominated_injection"
    assert result["violations"] == []


def test_event_family_binding_dominated_injection_requires_loss_budget() -> None:
    result = run_event_family_binding_gate({
        "relation_type": "dominated_injection",
        "target_event_family": "selected topology events",
        "source_event_family": "fresh-frequency same-tree events",
        "dominating_event_injection": "pre-payoff injection",
        "domination_inequality": "selected prefix cost <= fresh-frequency budget + error",
        "pre_payoff_timing": "fixed before payoff",
        "same_carrier": "same carrier",
        "same_owner_or_source": "same owner",
        "index_map": "j",
        "index_map_total_on_prefix": "all covered",
        "no_proxy_family": "not proxy",
        "no_post_payoff_selection": "no post payoff",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert "error_or_loss_budget" in result["missing_fields"]


def test_event_family_binding_treats_missing_strings_as_absent() -> None:
    result = run_event_family_binding_gate({
        "target_event_family": "material windows",
        "source_event_family": "quadratic threshold family",
        "event_identity": "missing: no material-window identity theorem",
        "pre_payoff_timing": "quadratic cap fixed before payoff",
        "same_carrier": "missing: carrier not identified",
        "same_owner_or_source": "missing: owner not identified",
        "index_map": "n maps to n",
        "index_map_total_on_prefix": "missing: no total prefix map",
        "no_proxy_family": "missing: proxy family not excluded",
        "no_post_payoff_selection": "no post payoff selection for the numeric cap",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert "event_identity" in result["missing_fields"]
    assert "same_carrier" in result["missing_fields"]
    assert "index_map_total_on_prefix" in result["missing_fields"]

