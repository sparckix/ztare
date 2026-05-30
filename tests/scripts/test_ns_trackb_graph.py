import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts" / "public" / "projects" / "ns" / "archive" / "graph_stack" / "ns_trackb_graph.py"
)


def _load_script():
    spec = importlib.util.spec_from_file_location("ns_trackb_graph", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_core02_detects_recurrence_reserve_and_potential_language():
    mod = _load_script()
    text = """
    structure EventRecurrencePricePDEObligation where
      reservePrice : Nat -> Real
      monotone_potential_declared_before_payoff : Prop
    """

    ops = mod.classify_ops(text, tags=[])

    assert "core_02" in ops


def test_core02_detects_declaration_name_reserve_without_literal_potential_function():
    mod = _load_script()
    text = "theorem LowFrequencyLipschitzReservePrefixClosure : Prop := True"

    ops = mod.classify_ops(text, tags=[])

    assert "core_02" in ops


def test_obligation_returning_constructor_def_is_not_open_obligation():
    mod = _load_script()
    block = """
    def trackB_profile_lipschitz_control_of_source
        (source : Source) :
        TrackBProfileLipschitzControlObligation :=
      existing_constructor source
    """

    status = mod.classify_status(
        "def",
        "trackB_profile_lipschitz_control_of_source",
        ["obligation", "trackb"],
        block,
    )

    assert status == "declaration"


def test_prop_valued_def_surface_remains_open_obligation():
    mod = _load_script()
    block = """
    def route1OpenObligation
        (transportDefect commutatorResidual : Real) : Prop :=
      route1KillerTheoremSearchFrontier transportDefect commutatorResidual
    """

    status = mod.classify_status(
        "def",
        "route1OpenObligation",
        ["obligation"],
        block,
    )

    assert status == "open_obligation"
