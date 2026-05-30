import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "public"
    / "lean"
    / "gap_typed_prompter.py"
)


def _load_script():
    spec = importlib.util.spec_from_file_location("gap_typed_prompter", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_field_evidence_beats_source_target_packaging():
    mod = _load_script()

    result = mod.heuristic_gap_type(
        "fixed_topology -> reserve_bound -> ∀ j, reach j * kNorm j <= C",
        "MacroscopicFlatTorusClockSource",
        "capacity_of_macroscopic_clock_sources",
    )

    assert result["gap_type"] == "COERCIVITY"


def test_embedding_field_is_not_auxiliary_from_source_target_name():
    mod = _load_script()

    result = mod.heuristic_gap_type(
        "∀ n, controlBudget n <= generatedLedger.lipschitzCost n",
        "PhaseLatencyProfileLipschitzReserveSource",
        "phase_control_embeds_in_generated_lipschitz_ledger",
    )

    assert result["gap_type"] == "PROPAGATION"


def test_section_prefix_identity_routes_to_auxiliary_construction():
    from src.ztare.research_director.gap_typing import heuristic_gap_type

    result = heuristic_gap_type(
        "Prop",
        "PostPayoffSectionRepairPacket",
        "selectedSectionIdentityFixedBeforePayoffMissing",
    )

    assert result["gap_type"] == "AUXILIARY"


def test_extensional_measure_missing_routes_to_auxiliary_construction():
    from src.ztare.research_director.gap_typing import heuristic_gap_type

    result = heuristic_gap_type(
        "Prop",
        "SectionLabelOnlyInterfaceVariationOracleAmbiguityPacket",
        "extensionalInterfaceVariationMeasureMissing",
    )

    assert result["gap_type"] == "AUXILIARY"


def test_loss_projection_missing_routes_to_auxiliary_construction():
    from src.ztare.research_director.gap_typing import heuristic_gap_type

    result = heuristic_gap_type(
        "Prop",
        "RawPositiveEigenconeLossUnpaidPacket",
        "coneLossPaidBeforeProjectionMissing",
    )

    assert result["gap_type"] == "AUXILIARY"


def test_eigenframe_cone_inclusion_missing_routes_to_auxiliary_construction():
    from src.ztare.research_director.gap_typing import heuristic_gap_type

    result = heuristic_gap_type(
        "Prop",
        "EigenframeLabelWithoutSelectedConeInclusionPacket",
        "selectedConeInclusionMissing",
    )

    assert result["gap_type"] == "AUXILIARY"


def test_sparse_carleson_pair_to_owner_routes_to_packing():
    from src.ztare.research_director.gap_typing import heuristic_gap_type

    result = heuristic_gap_type(
        "Prop",
        "KernelRelationNotOwnerPreimagePacket",
        "pairToOwnerSparseDominationMissing",
    )

    assert result["gap_type"] == "PACKING"

def test_second_moment_anticoncentration_routes_to_coercivity():
    from src.ztare.research_director.gap_typing import heuristic_gap_type

    result = heuristic_gap_type(
        "Prop",
        "InterfaceSecondMomentConcentrationSpikePacket",
        "thresholdSpikeSecondMomentDebt",
    )

    assert result["gap_type"] == "COERCIVITY"



def test_amplitude_cap_missing_routes_to_coercivity():
    from src.ztare.research_director.gap_typing import heuristic_gap_type

    result = heuristic_gap_type(
        "Prop",
        "FixedProfileWeightOnlyNoAmplitudeCapPacket",
        "pointwiseThresholdInterfacePaymentCapMissing",
    )

    assert result["gap_type"] == "COERCIVITY"

def test_m2_over_q_size_sum_surplus_routes_to_coercivity():
    from src.ztare.research_director.gap_typing import heuristic_gap_type

    result = heuristic_gap_type(
        "Prop",
        "QuadraticRatioSizeSumSurplusCertificate",
        "m2OverQSizeSumSurplus",
    )

    assert result["gap_type"] == "COERCIVITY"

