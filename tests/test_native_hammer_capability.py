from __future__ import annotations

from pathlib import Path

from ztare.leanmill.solver import governed_dag_search as gds
from ztare.leanmill.solver import solver_core as sc
from ztare.leanmill.solver.deterministic import NativeHammerProbeResult


def _synthetic_row() -> dict:
    return {
        "row_id": "native-test",
        "target_theorem_name": "native_test",
        "goal": "theorem native_test : (0 : Nat) = 0 := by sorry",
    }


def test_native_probe_distinguishes_exhaustion_from_checker_unavailability(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("ZTARE_LEANMILL_PERMOVE_CAPS", "0")
    monkeypatch.setenv("ZTARE_LEANMILL_NATIVE_DEDUP", "0")
    monkeypatch.setattr(sc, "_native_campaign_context", lambda source, _name: source)

    monkeypatch.setattr(
        sc, "_verify_compile", lambda *_args, **_kwargs: (False, "tactic failed")
    )
    exhausted = sc._native_hammer_probe(
        _synthetic_row(), tmp_path, 30, tactics=("rfl",)
    )
    assert exhausted.disposition == "exhausted"
    assert exhausted.admissible_negative is True

    monkeypatch.setattr(
        sc,
        "_verify_compile",
        lambda *_args, **_kwargs: (False, "verify_compile_timeout"),
    )
    unavailable = sc._native_hammer_probe(
        _synthetic_row(), tmp_path, 30, tactics=("rfl",)
    )
    assert unavailable.disposition == "unavailable"
    assert unavailable.admissible_negative is False


def test_cap_clipped_native_probe_is_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    import ztare.leanmill.cold_calibration as cold

    monkeypatch.setenv("ZTARE_LEANMILL_PERMOVE_CAPS", "1")
    monkeypatch.setenv("ZTARE_LEANMILL_NATIVE_DEDUP", "0")
    monkeypatch.setattr(cold, "cold_safe_timeout", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(sc, "_native_campaign_context", lambda source, _name: source)
    monkeypatch.setattr(
        sc,
        "_verify_compile",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("a zero-cap probe must not invoke the checker")
        ),
    )

    result = sc._native_hammer_probe(
        _synthetic_row(), tmp_path, 0, tactics=("rfl",)
    )
    assert result.disposition == "unavailable"


def test_native_self_test_uses_isolated_rfl_control(tmp_path: Path, monkeypatch) -> None:
    seen = {}

    def probe(row, _root, _timeout, *, tactics=None):
        seen["row"] = dict(row)
        seen["tactics"] = tactics
        return NativeHammerProbeResult("closed", "rfl", "compiled")

    monkeypatch.setattr(sc, "_native_hammer_probe", probe)
    monkeypatch.setattr(
        "ztare.formal.repl_compile.get_campaign_substrate", lambda: None
    )

    ok, _detail = sc._native_hammer_self_test(tmp_path, 10)
    assert ok is True
    assert seen["tactics"] == ("rfl",)
    assert seen["row"]["target_theorem_name"] == "nh_smoke"
    assert seen["row"]["goal"] == ": (0 : Nat) = 0"


def test_preflight_cache_key_carries_checker_roster_campaign_and_toolchain(
    tmp_path: Path, monkeypatch
) -> None:
    toolchain = tmp_path / "lean-toolchain"
    toolchain.write_text("leanprover/lean4:v4.19.0\n", encoding="utf-8")
    campaign = tmp_path / "Campaign.lean"
    campaign.write_text("def Campaign : Prop := True\n", encoding="utf-8")
    monkeypatch.setattr(sc, "active_proof_checker_name", lambda: "checker-a")
    monkeypatch.setattr(
        "ztare.formal.repl_compile.get_campaign_substrate", lambda: str(campaign)
    )

    first = sc._preflight_cache_key(tmp_path, False)
    campaign.write_text("def Campaign : Prop := False\n", encoding="utf-8")
    second = sc._preflight_cache_key(tmp_path, False)
    monkeypatch.setattr(sc, "active_proof_checker_name", lambda: "checker-b")
    third = sc._preflight_cache_key(tmp_path, False)

    assert first != second
    assert second != third


def test_spike_uses_disposable_target_and_never_governs_root(
    tmp_path: Path, monkeypatch
) -> None:
    root = {
        "row_id": "root-row",
        "target_theorem_name": "root_target",
        "goal": "theorem root_target : False := by sorry",
    }
    seen = {}

    def probe(row, _root, _timeout, *, tactics=None):
        seen["row"] = dict(row)
        seen["tactics"] = tactics
        return NativeHammerProbeResult("closed", "rfl", "control compiled")

    monkeypatch.setattr(sc, "_native_hammer_probe", probe)
    monkeypatch.setattr(
        sc,
        "_record_attempt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("calibration must not enter theorem attempt telemetry")
        ),
    )
    runner = sc._build_dag_move_runner(
        r=root,
        contract={},
        enriched_goal=root["goal"],
        verify_timeout=30,
        provider="codex",
        fallbacks=[],
        invoke_with_routing=lambda *_args, **_kwargs: None,
        providers_tried=[],
        lean_root=tmp_path,
    )

    result = runner(gds.spike_probe(), gds.MOVE_NATIVE_HAMMER, 20.0)

    assert seen["row"]["row_id"] == "native_hammer::spike"
    assert seen["row"]["target_theorem_name"] == "_spike_internal_standard"
    assert seen["row"]["goal"] == gds.SPIKE_GOAL_TEXT
    assert seen["tactics"] == ("rfl",)
    assert result.calibration_available is True
    assert result.ratified_close is False
    assert gds.spike_closed(result) is True


def test_ratification_only_does_not_run_search_carrier_preflight(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        sc,
        "preflight_moves_alive",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("ratification must not depend on search-carrier preflight")
        ),
    )
    seen = {}

    def bounded_ratifier(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return {
            "ratification_only": True,
            "results": [{
                "name": "adhoc::target",
                "target_name": "target",
                "outcome": "failed_compile",
                "tail": "carried artifact rejected",
            }],
            "closure_candidates": 0,
        }

    monkeypatch.setattr(
        "ztare.leanmill.carried_theorem_ratification.ratify_carried_theorem",
        bounded_ratifier,
    )

    result = sc.solve_adhoc(
        "target",
        "import Mathlib\n\ntheorem target : True := by sorry\n",
        ": True",
        substrate=tmp_path,
        preverified_proof="by trivial",
        preverified_provider="existing_artifact",
        preverified_only=True,
    )

    assert result["ratification_only"] is True
    assert result["results"][0]["outcome"] == "failed_compile"
    assert seen["args"][:4] == (
        "target",
        "import Mathlib\n\ntheorem target : True := by sorry\n",
        "by trivial",
        ": True",
    )
    assert seen["kwargs"]["provider_label"] == "existing_artifact"
