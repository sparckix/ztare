#!/usr/bin/env python3
"""Measure exact formal coverage of the critical Puiseux terminal.

The adapter replays the existing Puiseux certificates and the governed
arithmetic theorem receipt.  Remaining mathematical propositions retain
adapter-semantic identity, so this script cannot promote the terminal to
formal-kernel authority.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SRC_ROOT = REPO / "src"
JACOBIAN = REPO / (
    "research_areas/pre_registrations/"
    "axiompack_jacobian_field_parametric_20260720"
)
for path in (str(SRC_ROOT), str(JACOBIAN)):
    if path not in sys.path:
        sys.path.insert(0, path)

from gauge_pure_contact_zero_witt_puiseux_obstruction import (  # noqa: E402
    run as puiseux_run,
)
from gauge_critical_monodromy_residue import (  # noqa: E402
    build_certificate as monodromy_residue_run,
)
from gauge_polynomial_flow_finite_monodromy_countermodels import (  # noqa: E402
    build_certificate as finite_monodromy_countermodels_run,
)
from gauge_coupled_julia_projection_fallacy import (  # noqa: E402
    build_certificate as projection_fallacy_run,
)
from ztare.common.content_identity import content_sha256  # noqa: E402
from ztare.leanmill.filtered_evidence_authority import (  # noqa: E402
    make_content_bound_evidence_from_governed_ratification,
)
from ztare.leanmill.formal_claim_coverage import (  # noqa: E402
    FormalClaimCoverageProblem,
    FormalClaimNode,
    FormalPropositionIdentityKind,
    GovernedFormalPropositionIdentity,
    GovernedFormalSupport,
    compile_formal_claim_coverage,
    governed_formal_proposition_identity_from_receipt,
    make_formal_claim_decomposition,
    replay_formal_claim_coverage_certificate,
)
from ztare.leanmill.governed_ratification import (  # noqa: E402
    normalized_target_signature,
)
from ztare.leanmill.lean_source import (  # noqa: E402
    open_decl_for_ratification,
)
from ztare.leanmill.solver.closed_artifact import (  # noqa: E402
    closure_toolchain_identity,
)


LEAN_ROOT = REPO / "ztare_proofs"
CERTIFICATE_LEDGER = (
    REPO / "analytics/public/queries/adhoc_closure_certificates.jsonl"
)
PARITY_LEDGER = REPO / "analytics/public/queries/kernel_parity.jsonl"
ARITHMETIC_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxArithmetic."
    "critical_puiseux_arithmetic_terminal_certificate"
)
ARITHMETIC_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxArithmetic.lean"
)
ARITHMETIC_RECORD_SHA256 = (
    "6caf168f5d071956f6f0d8a3567296c7984bcae13b3b682afb62381fa8c12699"
)
EXPECTED_ARITHMETIC_RECEIPT_SHA256 = (
    "dc3c205e70124f469a5fd5421873568c0dce822e4b4233fdddc0a3db55e0eeb0"
)
MECHANISM_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxMechanism.lean"
)
COEFFICIENT_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxMechanism."
    "fractional_coefficient_forces_nonintegral_multiplicity"
)
COEFFICIENT_RECORD_SHA256 = (
    "a634915d075e94c0428889f33dc07ee73ee96270afd065d7cd2831dbc287dd6c"
)
EXPECTED_COEFFICIENT_RECEIPT_SHA256 = (
    "87382db51f823468f0c46d85d83d5bffdef24b0cf3fa372b6197ce066e63b9fb"
)
TWO_FLOW_INTERVAL_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxMechanism."
    "two_flow_transition_exponent_interval"
)
TWO_FLOW_INTERVAL_RECORD_SHA256 = (
    "fe4c2bc04778c7e8a6b1dec1a64f16b619293ff87dfb224e9981ef121c87384f"
)
EXPECTED_TWO_FLOW_INTERVAL_RECEIPT_SHA256 = (
    "a81b12695b53f9d367404b945e04bf6d378ff07311b1f33e6a7555049fdf648a"
)
GERM_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxGermArithmetic.lean"
)
GERM_SUPPORT_SPECS = (
    (
        "discriminant_factorization",
        (
            "AxiomPackJacobianCriticalPuiseuxGermArithmetic."
            "discriminant_factorization"
        ),
        "3a53defd2a04afb350284a42f1b546555052016fd4278c22d2892b3967b88a27",
        "3ded1d209f499225a8efbfc7b6ea06cc6c52847f16530f6a89a658f2f1b6bb23",
    ),
    (
        "radical_numerator_simple_zero",
        (
            "AxiomPackJacobianCriticalPuiseuxGermArithmetic."
            "radical_numerator_simple_zero"
        ),
        "80013b6ea38fc8dd4c6065bc8a29b503b583509d5d8123b7f73c36e5d50e3883",
        "4466cbbe4df7e108cb00538752061d43c612a9ff035a8e6c37b44394d04569a7",
    ),
    (
        "radical_denominator_at_branch_nonzero",
        (
            "AxiomPackJacobianCriticalPuiseuxGermArithmetic."
            "radical_denominator_at_branch_nonzero"
        ),
        "200a02cc74d82fc9249d024167647df4b92ff10e18bacfb980c372e787364c1d",
        "7805bfcdc3d7eab508aca839aee6fc157080b2c10c0952af42e9c3ff8ae03a07",
    ),
    (
        "radical_simple_zero_scale_exact",
        (
            "AxiomPackJacobianCriticalPuiseuxGermArithmetic."
            "radical_simple_zero_scale_exact"
        ),
        "35dfc7a5250f950269181742170b3e6e404b7ffc63dede4a93eed64604cbb136",
        "291a64cb3be111b370fe13d3176306e992e2d7bc786ad66f71ebd9b822f4a6b9",
    ),
)
SERIES_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxSeries.lean"
)
SERIES_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxSeries."
    "selected_algebraic_germ_series_passage"
)
SERIES_RECORD_SHA256 = (
    "c28469696e1b6781f0ae48fad1edce6482775b801bc373c70f57274ef6e21628"
)
EXPECTED_SERIES_RECEIPT_SHA256 = (
    "92933bad30852103901ca87d489ea0dcc3adb4bbf0209f9419214acaf64bc772"
)
JULIA_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalAutonomousFlow.lean"
)
JULIA_TARGET = "FormalAutonomousFlow.polynomial_julia_identity"
JULIA_RECORD_SHA256 = (
    "833c8cb1b1435b0708de062ac2a0089cd6a364755f536f1d27af55ef1caf81b6"
)
EXPECTED_JULIA_RECEIPT_SHA256 = (
    "a18f5ed1f9cc8b6d3f486a25f6eb256861cbe275272e331bfd176aa730d1e803"
)
INFINITY_CHART_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalPolynomialFlowAtInfinity.lean"
)
INFINITY_CHART_TARGET = (
    "FormalPolynomialFlowAtInfinity."
    "polynomial_infinity_chart_terminal_certificate"
)
INFINITY_CHART_RECORD_SHA256 = (
    "2e5afd27b80bcedfba58a9bde22cd1537de072b1122ef4891c36b602396fed02"
)
EXPECTED_INFINITY_CHART_RECEIPT_SHA256 = (
    "b1c1014c175aae418728477e3760493d9ca130a588c16b5e074c1f03d88f6a16"
)
PROPORTIONAL_SEMIGROUP_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalSubstitutionFlow.lean"
)
PROPORTIONAL_SEMIGROUP_TARGET = (
    "FormalSubstitutionFlow."
    "proportional_substitution_flow_terminal_certificate"
)
PROPORTIONAL_SEMIGROUP_RECORD_SHA256 = (
    "eed5fe2eeab3b40808ba60f4b25ccfd0ee89fc45ea6b4ddca8574f307fbbcad9"
)
EXPECTED_PROPORTIONAL_SEMIGROUP_RECEIPT_SHA256 = (
    "b099911dc1ae41740737f041e996ed0172750fcb2f2c7409493536b6ce7f5a79"
)
PROPORTIONAL_TRAJECTORY_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalAnalyticAutonomousTrajectory.lean"
)
PROPORTIONAL_TRAJECTORY_TARGET = (
    "FormalAnalyticAutonomousTrajectory."
    "proportional_analytic_trajectory_terminal_certificate"
)
PROPORTIONAL_TRAJECTORY_RECORD_SHA256 = (
    "f54e8bc0527b678cf7c905b8ef2693c4c5a8c0d1eaad849d90ae9d69e8e94994"
)
EXPECTED_PROPORTIONAL_TRAJECTORY_RECEIPT_SHA256 = (
    "6885b9dde00d00a9ae4b07f89af396bb54dbd93676746ef7ee1c9e5688231cf3"
)
PROPORTIONAL_REDUCTION_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalProportionalFlowReduction.lean"
)
PROPORTIONAL_REDUCTION_TARGET = (
    "FormalProportionalFlowReduction."
    "proportional_flow_reduction_terminal_certificate"
)
PROPORTIONAL_REDUCTION_RECORD_SHA256 = (
    "5b665dc06f8f3db033aaf7ff3fe5a15699c7d592d3e7b01dbabcbf1b50d1ee93"
)
EXPECTED_PROPORTIONAL_REDUCTION_RECEIPT_SHA256 = (
    "fafcfc3b650ac723e68cb95dbe138c326c825e8ef9fffa152fda8f253d68a79b"
)
FINITE_ANALYTIC_ROUTE_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalAnalyticFiniteRoute.lean"
)
FINITE_ANALYTIC_ROUTE_TARGET = (
    "FormalAnalyticFiniteRoute."
    "finite_analytic_route_terminal_certificate"
)
FINITE_ANALYTIC_ROUTE_RECORD_SHA256 = (
    "490e518ddd0364be3a8bb4ab1a94488f51ad4c4bba2b20acef2c2e71c807ee67"
)
EXPECTED_FINITE_ANALYTIC_ROUTE_RECEIPT_SHA256 = (
    "f228ec497d5953f9462488095d5aa730992391034df191850a4162959f8e7c0e"
)
FINITE_ROUTE_INFERENCE_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalAnalyticFiniteRouteInference.lean"
)
FINITE_ROUTE_INFERENCE_TARGET = (
    "FormalAnalyticFiniteRouteInference."
    "finite_or_classified_escape_inference_terminal_certificate"
)
FINITE_ROUTE_INFERENCE_RECORD_SHA256 = (
    "7697c2587412160caf0b79e9e52d94189bacf1de3f69ee742e1c12faf4d1b6f8"
)
EXPECTED_FINITE_ROUTE_INFERENCE_RECEIPT_SHA256 = (
    "7961e3e74335ebe52666e46d7ac448ecdda025d2d965f6ea0edbc51156263c4a"
)
PUNCTURED_EXTENSION_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalAnalyticPuncturedExtension.lean"
)
PUNCTURED_EXTENSION_TARGET = (
    "FormalAnalyticPuncturedExtension."
    "punctured_extension_terminal_certificate"
)
PUNCTURED_EXTENSION_RECORD_SHA256 = (
    "5ffa05d514ccf350abfc46b1596e18dac3ed5d2582736cc1cb01bb4954a64e8b"
)
EXPECTED_PUNCTURED_EXTENSION_RECEIPT_SHA256 = (
    "9980aedfeb0003c1fddfc74668b3a7af178a4b9f725e00e1e8e124974ea8fe77"
)
PUNCTURED_ESCAPE_INFERENCE_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalAnalyticPuncturedEscapeInference.lean"
)
PUNCTURED_ESCAPE_INFERENCE_TARGET = (
    "FormalAnalyticPuncturedEscapeInference."
    "punctured_unbounded_escape_inference_terminal_certificate"
)
PUNCTURED_ESCAPE_INFERENCE_RECORD_SHA256 = (
    "3efae91512433e91ac0e7e7cb9102f5df423f4fd6da6b317b2d7943f318e0bf3"
)
EXPECTED_PUNCTURED_ESCAPE_INFERENCE_RECEIPT_SHA256 = (
    "828f6280616321d4a26f0fe934cb785fa4503f39ae996f3abf32bc4b8067c778"
)
MEROMORPHIC_INFINITY_CHART_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalMeromorphicInfinityChart.lean"
)
MEROMORPHIC_INFINITY_CHART_TARGET = (
    "FormalMeromorphicInfinityChart."
    "meromorphic_infinity_chart_terminal_certificate"
)
MEROMORPHIC_INFINITY_CHART_RECORD_SHA256 = (
    "39b2c709e1e59c8d101f12fb008e02525fe9a1dcc0c43faea1867c7dccf48afa"
)
EXPECTED_MEROMORPHIC_INFINITY_CHART_RECEIPT_SHA256 = (
    "5b05bc2eb87ad3b07216ad1a09e377fdff4fb04249b80869428811a0c81f13fd"
)
MEROMORPHIC_ESCAPE_INFERENCE_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalMeromorphicInfinityChartInference.lean"
)
MEROMORPHIC_ESCAPE_INFERENCE_TARGET = (
    "FormalMeromorphicInfinityChartInference."
    "meromorphic_reciprocal_escape_inference_terminal_certificate"
)
MEROMORPHIC_ESCAPE_INFERENCE_RECORD_SHA256 = (
    "e36a6b45e868298b9e7d835889372bda8b5733b656a0db73d64373bef792f678"
)
EXPECTED_MEROMORPHIC_ESCAPE_INFERENCE_RECEIPT_SHA256 = (
    "1c12bc4cdd6b948dee20e7c53663c13cb312a36c2edee23d67e774e940488e21"
)
POLYNOMIAL_INFINITY_RAMIFICATION_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalPolynomialInfinityRamification.lean"
)
POLYNOMIAL_INFINITY_RAMIFICATION_TARGET = (
    "FormalPolynomialInfinityRamification."
    "polynomial_infinity_ramification_terminal_certificate"
)
POLYNOMIAL_INFINITY_RAMIFICATION_RECORD_SHA256 = (
    "edc25f102cad56bca1de37a2a066964d0286ca32bd945fcde8edf67a0a02048e"
)
EXPECTED_POLYNOMIAL_INFINITY_RAMIFICATION_RECEIPT_SHA256 = (
    "2572c66cd2a9125b94563e4aef833d44f85b1bfab3c88ebf638595c22e113071"
)
POLYNOMIAL_INFINITY_RAMIFICATION_INFERENCE_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalPolynomialInfinityRamificationInference.lean"
)
POLYNOMIAL_INFINITY_RAMIFICATION_INFERENCE_TARGET = (
    "FormalPolynomialInfinityRamificationInference."
    "polynomial_infinity_ramification_inference_terminal_certificate"
)
POLYNOMIAL_INFINITY_RAMIFICATION_INFERENCE_RECORD_SHA256 = (
    "0b4f53d6f70a621e4e1ace1d8a1a433bd06e6959f80999ac773b22c44ac03000"
)
EXPECTED_POLYNOMIAL_INFINITY_RAMIFICATION_INFERENCE_RECEIPT_SHA256 = (
    "28daf47b17b21f29c5b1fa80f776e3be9d8961643b9ef6b49b52131e1b1317a1"
)
POLYNOMIAL_TIME_SEPARATION_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalPolynomialTimeSeparation.lean"
)
POLYNOMIAL_TIME_SEPARATION_TARGET = (
    "FormalPolynomialTimeSeparation."
    "polynomial_time_separation_terminal_certificate"
)
POLYNOMIAL_TIME_SEPARATION_RECORD_SHA256 = (
    "af57b242aab2a248a2afb6274b1fe95020a6cc694038b6f6f92f61bbeb13dc2f"
)
EXPECTED_POLYNOMIAL_TIME_SEPARATION_RECEIPT_SHA256 = (
    "72077fdcbb8e42bed5042216f754b85f6f958ac357b136840191fc007197bd55"
)
SELECTED_RAMIFIED_INVERSE_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalSelectedRamifiedInverse.lean"
)
SELECTED_RAMIFIED_INVERSE_TARGET = (
    "FormalSelectedRamifiedInverse."
    "selected_reparam_eq_inverse_of_separatedTime"
)
SELECTED_RAMIFIED_INVERSE_RECORD_SHA256 = (
    "4e3decbd1ca980ae8fc930c25f77ffa5548a107820fe0b01d425515ddcec4db2"
)
EXPECTED_SELECTED_RAMIFIED_INVERSE_RECEIPT_SHA256 = (
    "e82c4577bb329892db2548c2fd79a76036b49ce2363a58cc42593b215d4a4027"
)
SELECTED_TRAJECTORY_ASSEMBLY_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalPolynomialSelectedTrajectoryAssembly.lean"
)
SELECTED_TRAJECTORY_ASSEMBLY_TARGET = (
    "FormalPolynomialSelectedTrajectoryAssembly."
    "selected_trajectory_assembly_terminal_certificate"
)
SELECTED_TRAJECTORY_ASSEMBLY_RECORD_SHA256 = (
    "dbcb8d4ddb10634d00d5e8652b02e5969f180664a0fd6950ad835df9ce0ff38d"
)
EXPECTED_SELECTED_TRAJECTORY_ASSEMBLY_RECEIPT_SHA256 = (
    "b0ba0959fc94c0d7057f584ff302eb56f84b70d958800dd7184382d3e893769f"
)
TWO_FLOW_STRUCTURAL_ASSEMBLY_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalTwoFlowStructuralAlternative.lean"
)
TWO_FLOW_STRUCTURAL_ASSEMBLY_TARGET = (
    "FormalTwoFlowStructuralAlternative."
    "two_flow_structural_alternative_terminal_certificate"
)
TWO_FLOW_STRUCTURAL_ASSEMBLY_RECORD_SHA256 = (
    "e2c3320e812a9e94aa37ee9e16f9b2eaf7ffce75966f931975431f6318f98ee9"
)
EXPECTED_TWO_FLOW_STRUCTURAL_ASSEMBLY_RECEIPT_SHA256 = (
    "a2ed2a0fe2219acc62403d45edf96acdb84a1dd2b8f8efd9121cb990a40ebbb5"
)
RAMIFIED_TRAJECTORY_SHEET_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalPolynomialRamifiedTrajectorySheet.lean"
)
RAMIFIED_TRAJECTORY_SHEET_TARGET = (
    "FormalPolynomialRamifiedTrajectorySheet."
    "polynomial_ramified_trajectory_sheet_terminal_certificate"
)
RAMIFIED_TRAJECTORY_SHEET_RECORD_SHA256 = (
    "bce203456aa40bc052a2852a42598a06a2c6e84067e2e68b6b997f98d33f5c7b"
)
EXPECTED_RAMIFIED_TRAJECTORY_SHEET_RECEIPT_SHA256 = (
    "e982a3cd8fc852cc2f920a820dc0ea69b5f8a65f4fe8d560cf1eb31dd387ce1a"
)
LOCAL_SHEET_EXISTENCE_TARGET = (
    "FormalPolynomialRamifiedTrajectorySheet."
    "polynomial_infinity_local_sheet_exists_terminal_certificate"
)
LOCAL_SHEET_EXISTENCE_RECORD_SHA256 = (
    "13808788efd15c93eb26f3faaf7d90bb6d85c3b457f2711a2744caed169298cc"
)
EXPECTED_LOCAL_SHEET_EXISTENCE_RECEIPT_SHA256 = (
    "b93a861d227891a539dfa5fa79e0ea66e7079a6586e71441266c7750a08e0d42"
)
FINITE_SHEET_OVERLAP_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalAnalyticSheetOverlap.lean"
)
FINITE_SHEET_OVERLAP_TARGET = (
    "FormalAnalyticSheetOverlap."
    "polynomial_finite_to_ramified_sheet_overlap_terminal_certificate"
)
FINITE_SHEET_OVERLAP_RECORD_SHA256 = (
    "37c9168d1cebf6e905fe5cd47070ad9e32329cf92f2d88973dc7273b21d8d3a4"
)
EXPECTED_FINITE_SHEET_OVERLAP_RECEIPT_SHA256 = (
    "b87a4cc156177b335309ffd1e6c30c96c35884c0ae7f322d01b0214e295ff7a7"
)
POLYNOMIAL_MEROMORPHIC_END_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalPolynomialMeromorphicEnd.lean"
)
POLYNOMIAL_MEROMORPHIC_END_TARGET = (
    "FormalPolynomialMeromorphicEnd."
    "polynomial_meromorphic_end_sheet_entry_terminal_certificate"
)
POLYNOMIAL_MEROMORPHIC_END_RECORD_SHA256 = (
    "db32abf8430d5dac4a4c8be158ac0ee2ea7070297f8d4e0d207cc364cc48fa5e"
)
EXPECTED_POLYNOMIAL_MEROMORPHIC_END_RECEIPT_SHA256 = (
    "d934b28ba22eb6b8f06ee126c31b5ae10a522f0b7d81a080b876b07df4e02576"
)
RAMIFIED_FIBER_PRODUCT_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalAnalyticRamifiedFiberProduct.lean"
)
RAMIFIED_FIBER_PRODUCT_TARGET = (
    "FormalAnalyticRamifiedFiberProduct."
    "analytic_ramified_fiber_product_terminal_certificate"
)
RAMIFIED_FIBER_PRODUCT_RECORD_SHA256 = (
    "0a606d3206ceffa6efc2a3ba46b1382f4a62c6605bf3214fdfcfe2e7451d558c"
)
EXPECTED_RAMIFIED_FIBER_PRODUCT_RECEIPT_SHA256 = (
    "cf2806d565ebffc42fc4901489eff1519b8329eb7e5a6a3a862dcc96469710ef"
)
REGULAR_INFINITY_FIBER_PRODUCT_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalPolynomialRegularInfinityFiberProduct.lean"
)
REGULAR_INFINITY_FIBER_PRODUCT_TARGET = (
    "FormalPolynomialRegularInfinityFiberProduct."
    "polynomial_regular_infinity_fiber_product_terminal_certificate"
)
REGULAR_INFINITY_FIBER_PRODUCT_RECORD_SHA256 = (
    "647fd11fbf9dd854c52a7f03813bb3eb89c966fe2509d4e083016eb3b716ad97"
)
EXPECTED_REGULAR_INFINITY_FIBER_PRODUCT_RECEIPT_SHA256 = (
    "be8da58f9f128bb482f8c14eaa20cb3d294ee76241aeec550718a96ee43c4367"
)
EQUILIBRIUM_TRAJECTORY_RIGIDITY_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalPolynomialEquilibriumTrajectoryRigidity.lean"
)
EQUILIBRIUM_TRAJECTORY_RIGIDITY_TARGET = (
    "FormalPolynomialEquilibriumTrajectoryRigidity."
    "polynomial_equilibrium_trajectory_rigidity_terminal_certificate"
)
EQUILIBRIUM_TRAJECTORY_RIGIDITY_RECORD_SHA256 = (
    "00e7ff23cc70ccf8c1f6f72cb1d97633e3fdc5a9c2fa748be672fbd44fb2f813"
)
EXPECTED_EQUILIBRIUM_TRAJECTORY_RIGIDITY_RECEIPT_SHA256 = (
    "8faa5aece4139f534a623f48b857d838e708c91b155b499714d3b550da6f3e60"
)
RAMIFIED_FIBER_PRODUCT_OVERLAP_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalAnalyticRamifiedFiberProductOverlap.lean"
)
RAMIFIED_FIBER_PRODUCT_OVERLAP_TARGET = (
    "FormalAnalyticRamifiedFiberProductOverlap."
    "analytic_ramified_fiber_product_overlap_terminal_certificate"
)
RAMIFIED_FIBER_PRODUCT_OVERLAP_RECORD_SHA256 = (
    "37424c27130cf1922595e395dda34c2cc9e73bd29697ff90ac9cb2c2cf5dd7bc"
)
EXPECTED_RAMIFIED_FIBER_PRODUCT_OVERLAP_RECEIPT_SHA256 = (
    "60222f9c3e8841c68dce94a2e984c137ac639d013309e34ccfd5fb7b11de6aaf"
)
FINITE_INFINITY_ABEL_SEPARATION_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalPolynomialFiniteInfinityAbelSeparation.lean"
)
FINITE_INFINITY_ABEL_SEPARATION_TARGET = (
    "FormalPolynomialFiniteInfinityAbelSeparation."
    "polynomial_finite_infinity_abel_separation_terminal_certificate"
)
FINITE_INFINITY_ABEL_SEPARATION_RECORD_SHA256 = (
    "e9bddb93d370f32da8bc4c03450b2920ec7c17c115d168a904ace06a3d723a34"
)
EXPECTED_FINITE_INFINITY_ABEL_SEPARATION_RECEIPT_SHA256 = (
    "704f6e84025af2ecb581114b33226d1ab875ec76c67da96bf88dece58d87fec8"
)
REGULAR_JULIA_FIBER_PRODUCT_END_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalPolynomialRegularJuliaFiberProductEnd.lean"
)
REGULAR_JULIA_FIBER_PRODUCT_END_TARGET = (
    "FormalPolynomialRegularJuliaFiberProductEnd."
    "polynomial_regular_julia_fiber_product_end_terminal_certificate"
)
REGULAR_JULIA_FIBER_PRODUCT_END_RECORD_SHA256 = (
    "e2e4f8a8b95f7341529b349d061d833609bdd3bd83390fb0399a2a80bc5717a6"
)
EXPECTED_REGULAR_JULIA_FIBER_PRODUCT_END_RECEIPT_SHA256 = (
    "2caf92b6206076acf6a93775a4506f201b197c56c4cd2bbdcec72dea7f6aef70"
)
SELECTED_GERM_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxSelectedGerm.lean"
)
SELECTED_GERM_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxSelectedGerm."
    "selected_algebraic_germ_expansion_terminal_certificate"
)
SELECTED_GERM_RECORD_SHA256 = (
    "00f9d1d26b2c4af9fe790111d2c2ab0acdb8f58bdc039212ee30add65ebeb5b8"
)
EXPECTED_SELECTED_GERM_RECEIPT_SHA256 = (
    "905e6dbb6c699a5105e7f52b0cff5855d98a930774d79865137b07742d85d79e"
)
SINGLE_FLOW_OBSTRUCTION_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxSingleFlow.lean"
)
SINGLE_FLOW_OBSTRUCTION_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxSingleFlow."
    "selected_single_polynomial_flow_obstruction_terminal_certificate"
)
SINGLE_FLOW_OBSTRUCTION_RECORD_SHA256 = (
    "531465d6c26957f985d2bcb76d2be59ecf4494762410e9e27261220b0e06161f"
)
EXPECTED_SINGLE_FLOW_OBSTRUCTION_RECEIPT_SHA256 = (
    "f56528d61c46a071a3879b6c07ea3b285a13d32b83dc25a83cbb475b715b773d"
)
ANALYTIC_CONTINUATION_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalAnalyticContinuation.lean"
)
ANALYTIC_CONTINUATION_TARGET = (
    "FormalAnalyticContinuation."
    "analytic_continuation_julia_terminal_certificate"
)
ANALYTIC_CONTINUATION_RECORD_SHA256 = (
    "708a647d3c512ce41fd5e36ccb5b459fbbe0cfac02e496281f89bbc02481cd91"
)
EXPECTED_ANALYTIC_CONTINUATION_RECEIPT_SHA256 = (
    "1a291c037e7627f6bbc010573b1bb3c0776c620f6f1474eef8beb3dfbb9b84b4"
)
ANALYTIC_TAYLOR_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalAnalyticTaylorTransport.lean"
)
ANALYTIC_TAYLOR_TARGET = (
    "FormalAnalyticTaylorTransport."
    "analytic_germ_to_powerSeries_terminal_certificate"
)
ANALYTIC_TAYLOR_RECORD_SHA256 = (
    "af3f5c753d57eb6827224bd26d437757e82c65276ac62788f3214781f4a18011"
)
EXPECTED_ANALYTIC_TAYLOR_RECEIPT_SHA256 = (
    "36505230a9421a4314983992a700d48a0d962ea975039895317309fe6b16f2cb"
)
FORMAL_LINEAR_ODE_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalPowerSeriesLinearODE.lean"
)
FORMAL_LINEAR_ODE_TARGET = (
    "FormalPowerSeriesLinearODE."
    "normalized_formal_linear_ode_terminal_certificate"
)
FORMAL_LINEAR_ODE_RECORD_SHA256 = (
    "ae3a493f04765fb6607b15d92a7eea6c51eeb3d186baa5588c5ea023bd45acac"
)
EXPECTED_FORMAL_LINEAR_ODE_RECEIPT_SHA256 = (
    "59bb187afc80e677c02c70fce3cb8edd2f98f5ff27529381af0ba9c7bbcf6eb6"
)
CONSTRUCTED_ENDPOINT_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxConstructedEndpoint.lean"
)
CONSTRUCTED_ENDPOINT_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxConstructedEndpoint."
    "selected_constructed_endpoint_terminal_certificate"
)
CONSTRUCTED_ENDPOINT_RECORD_SHA256 = (
    "40b552a20dee066e33aab7fa5288d43ede936b1e1a75e2aef87d3c4950abfe31"
)
EXPECTED_CONSTRUCTED_ENDPOINT_RECEIPT_SHA256 = (
    "3c10933666ff5917a16d31c6d67c2e7e45d72267114732e61b58017f42b74421"
)
CONSTRUCTED_SINGLE_FLOW_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxConstructedSingleFlow.lean"
)
CONSTRUCTED_SINGLE_FLOW_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxConstructedSingleFlow."
    "selected_constructed_single_flow_terminal_certificate"
)
CONSTRUCTED_SINGLE_FLOW_RECORD_SHA256 = (
    "61f013d3ef4ae0c02d3442b4daeda203f273c117e7385fc89cadb881ce59502a"
)
EXPECTED_CONSTRUCTED_SINGLE_FLOW_RECEIPT_SHA256 = (
    "ad2004926cb2d30ef53b315a2f2cf47a3d63bdc8d3c72487c4f9274e381b0d18"
)
SELECTED_CHART_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxAnalyticRealization.lean"
)
SELECTED_CHART_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxAnalyticRealization."
    "selected_chart_realization_terminal_certificate"
)
SELECTED_CHART_RECORD_SHA256 = (
    "1c26f90121e4f2c8f419fb7626a1d07c50bb664f06b129b8ea4a9d758c93c73f"
)
EXPECTED_SELECTED_CHART_RECEIPT_SHA256 = (
    "94958ee0bc81e8f32ef507e168e823e2a828ec839f333a3abd3eafc245a40bd6"
)
JULIA_ASSEMBLY_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxJuliaAssembly.lean"
)
JULIA_ASSEMBLY_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxJuliaAssembly."
    "selected_terminal_julia_shifted_powerSeries"
)
JULIA_ASSEMBLY_RECORD_SHA256 = (
    "a80f4c32123043d334b8906d00189e06bf55d139a317166780fc638adcfbb8ff"
)
EXPECTED_JULIA_ASSEMBLY_RECEIPT_SHA256 = (
    "974244e37239d81b0f796511f1af2b762ca6173d1fc7d157ae2a43a1dc4141ce"
)
SINGLE_FLOW_ANALYTIC_OBSTRUCTION_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxJuliaAssembly."
    "selected_single_flow_analytic_obstruction_terminal_certificate"
)
SINGLE_FLOW_ANALYTIC_OBSTRUCTION_RECORD_SHA256 = (
    "fed72e353cb01ef1a55bb6348806de55c47d3e290464f7e1c2edc2247463b2d9"
)
EXPECTED_SINGLE_FLOW_ANALYTIC_OBSTRUCTION_RECEIPT_SHA256 = (
    "c66a5e23496ca4d018bc53b7250c636a037175196287bc64dda940731bbcd281"
)
COMPLEX_SINGLE_FLOW_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxComplexSingleFlow.lean"
)
COMPLEX_SINGLE_FLOW_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxComplexSingleFlow."
    "selected_complex_single_flow_terminal_certificate"
)
COMPLEX_SINGLE_FLOW_RECORD_SHA256 = (
    "f75284788656df7ed413b14fb1925cb865556b3ca4b8ff41d435ae544fa7b584"
)
EXPECTED_COMPLEX_SINGLE_FLOW_RECEIPT_SHA256 = (
    "3c7262c9ebd02fd19b5fd35eb54ca657a120d267987145174b0e913a5a2803de"
)
COMPLEX_SINGLE_FLOW_ANALYTIC_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxComplexJuliaAssembly.lean"
)
COMPLEX_SINGLE_FLOW_ANALYTIC_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxComplexJuliaAssembly."
    "selected_complex_single_flow_analytic_terminal_certificate"
)
COMPLEX_SINGLE_FLOW_ANALYTIC_RECORD_SHA256 = (
    "5da9f3d68e13f3b0a246ec6bc999da0e02ccdc3acd97c463cb75ce537739cacb"
)
EXPECTED_COMPLEX_SINGLE_FLOW_ANALYTIC_RECEIPT_SHA256 = (
    "6f5423d7ef8846f6f8956cecb22fa981922ab21b02e09417fe690fa7c693a725"
)
COMPLEX_JULIA_TRANSPORT_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxComplexJuliaAssembly."
    "selected_terminal_complex_julia_shifted_powerSeries"
)
COMPLEX_JULIA_TRANSPORT_RECORD_SHA256 = (
    "ae3106160d40d1364bb4c6c408f8184e8db7320ce661de486447b3d682b04821"
)
EXPECTED_COMPLEX_JULIA_TRANSPORT_RECEIPT_SHA256 = (
    "44fb3f5138997739844362dc7412275b4ce2d2f61bb18f18b426fd33c47ee032"
)
FINITE_JULIA_CLASSIFICATION_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalFiniteJuliaValuationClassification.lean"
)
FINITE_JULIA_CLASSIFICATION_TARGET = (
    "FormalFiniteJuliaValuationClassification."
    "finite_julia_valuation_classification_terminal_certificate"
)
FINITE_JULIA_CLASSIFICATION_RECORD_SHA256 = (
    "9efb4cd93a18afdc9e54b5789291f15266069cd104f09875609096fa1e47557a"
)
EXPECTED_FINITE_JULIA_CLASSIFICATION_RECEIPT_SHA256 = (
    "8cfcb6faaf31f9c55d8ce24762d678de0ba65ff74d47e3bf94e502b34a2806af"
)
TWO_FLOW_ABEL_ASSEMBLY_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalAnalyticTwoFlowAbelCarrierAssembly.lean"
)
TWO_FLOW_ABEL_ASSEMBLY_TARGET = (
    "FormalAnalyticTwoFlowAbelCarrierAssembly."
    "analytic_two_flow_abel_carrier_assembly_terminal_certificate"
)
TWO_FLOW_ABEL_ASSEMBLY_RECORD_SHA256 = (
    "65e1fffc99cee4b6c047d28cecf00dc3d92b85b6b2e995136f1530fe26a9a420"
)
EXPECTED_TWO_FLOW_ABEL_ASSEMBLY_RECEIPT_SHA256 = (
    "ca4282408094f3f24e9187e140abc1dbd990317e28ab87bdaafb550a8152b349"
)
CRITICAL_TWO_JULIA_EXCLUSION_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalAnalyticCriticalTwoJuliaExclusion.lean"
)
CRITICAL_TWO_JULIA_EXCLUSION_TARGET = (
    "FormalAnalyticCriticalTwoJuliaExclusion."
    "analytic_critical_two_julia_intrinsic_exclusion_terminal_certificate"
)
CRITICAL_TWO_JULIA_EXCLUSION_RECORD_SHA256 = (
    "2bb37deefb1baa60371a943578d353399d87e53f9dc857aa834a5d493985e33a"
)
EXPECTED_CRITICAL_TWO_JULIA_EXCLUSION_RECEIPT_SHA256 = (
    "812dbb0ed57e2310a5311e20a38ef769c18980306fc53975a7cca82f3aa1afbb"
)
MONODROMY_NON_TORSION_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalComplexMonodromyNonTorsion.lean"
)
MONODROMY_NON_TORSION_TARGET = (
    "FormalComplexMonodromyNonTorsion."
    "complex_monodromy_non_torsion_terminal_certificate"
)
MONODROMY_NON_TORSION_RECORD_SHA256 = (
    "f8193cc250d2cea255d1107e63c0397107749cde71a64b15a3ec02e0618780c1"
)
EXPECTED_MONODROMY_NON_TORSION_RECEIPT_SHA256 = (
    "a72e9f7832783458aa3e4df5bd52d3057d00e3e3ba08103b54bd8800fda5adbd"
)
CRITICAL_RESIDUE_IRRATIONALITY_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalCriticalResidueIrrationality.lean"
)
CRITICAL_RESIDUE_IRRATIONALITY_TARGET = (
    "FormalCriticalResidueIrrationality."
    "critical_residue_irrationality_terminal_certificate"
)
CRITICAL_RESIDUE_IRRATIONALITY_RECORD_SHA256 = (
    "b9ac4e8a487f757cde1870bbe795b92b122a502d288802bdd8731490b15a9cf7"
)
EXPECTED_CRITICAL_RESIDUE_IRRATIONALITY_RECEIPT_SHA256 = (
    "56e8457b58314944ac3ef2021891b2ca6f95841a88453786b5e90fe3b966db27"
)
CRITICAL_MONODROMY_BINDING_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalCriticalMonodromyResidueBinding.lean"
)
CRITICAL_MONODROMY_BINDING_TARGET = (
    "FormalCriticalMonodromyResidueBinding."
    "critical_monodromy_residue_binding_terminal_certificate"
)
CRITICAL_MONODROMY_BINDING_RECORD_SHA256 = (
    "25727111271dbc731e3d0c4cdc9688e64bad8a97d28daffa2895d29896b501a7"
)
EXPECTED_CRITICAL_MONODROMY_BINDING_RECEIPT_SHA256 = (
    "c78401d1f0a722b0c9a4d7499b7a9f12565a7bba0b90a8784d8b8ef443676ef2"
)
CRITICAL_CONNECTION_RATIONALIZATION_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalCriticalConnectionRationalization.lean"
)
CRITICAL_CONNECTION_RATIONALIZATION_TARGET = (
    "FormalCriticalConnectionRationalization."
    "critical_connection_rationalization_terminal_certificate"
)
CRITICAL_CONNECTION_RATIONALIZATION_RECORD_SHA256 = (
    "dbc90efc8066be9b0897f097a114dd2c276c8431c8cd990b3a175e5f1e0517ac"
)
EXPECTED_CRITICAL_CONNECTION_RATIONALIZATION_RECEIPT_SHA256 = (
    "ff3dacb701f8fc0bf97db0770ae54a88641fdc9f320968659ccfba9a7716c4c7"
)
CRITICAL_HOLONOMY_LOOP_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalCriticalHolonomyLoop.lean"
)
CRITICAL_HOLONOMY_LOOP_TARGET = (
    "FormalCriticalHolonomyLoop."
    "critical_connection_holonomy_loop_terminal_certificate"
)
CRITICAL_HOLONOMY_LOOP_RECORD_SHA256 = (
    "54198f8b2fe5854ec115f6195de2383b17816cdb257a24d1294d7b3b47f24c33"
)
EXPECTED_CRITICAL_HOLONOMY_LOOP_RECEIPT_SHA256 = (
    "5cc3011d1ab52aee73ad217317c387e1de695a9888c4c5b0e7cd4f057cda0a72"
)
COUPLED_JULIA_ELIMINATION_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalCoupledJuliaElimination.lean"
)
COUPLED_JULIA_ELIMINATION_TARGET = (
    "FormalCoupledJuliaElimination."
    "coupled_julia_elimination_terminal_certificate"
)
COUPLED_JULIA_ELIMINATION_RECORD_SHA256 = (
    "9a0b93843527fc75cb9c0121b79d9c89f726f2de29caaf341485bc56610785c2"
)
EXPECTED_COUPLED_JULIA_ELIMINATION_RECEIPT_SHA256 = (
    "2453126559905d5f8b469193075b5d99f67b6964842edc421710e352acfd4945"
)
FINITE_STATE_TRAJECTORY_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalAnalyticPolynomialControlledTrajectory.lean"
)
FINITE_STATE_TRAJECTORY_TARGET = (
    "FormalAnalyticPolynomialControlledTrajectory."
    "analytic_polynomial_controlled_trajectory_terminal_certificate"
)
FINITE_STATE_TRAJECTORY_RECORD_SHA256 = (
    "f42f0fb155a84be0eb978de3db8a564de7b8927158fc6407f0685aa2e2375faf"
)
EXPECTED_FINITE_STATE_TRAJECTORY_RECEIPT_SHA256 = (
    "59d0d951a2477708b24a7bada5ffeeb1e401fb18f65767ea66bcaf4bd078bc6b"
)
COUPLED_JULIA_DIFFERENTIAL_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalCoupledJuliaDifferentialProlongation.lean"
)
COUPLED_JULIA_DIFFERENTIAL_TARGET = (
    "FormalCoupledJuliaDifferentialProlongation."
    "coupled_julia_differential_prolongation_terminal_certificate"
)
COUPLED_JULIA_DIFFERENTIAL_RECORD_SHA256 = (
    "b4ea295e602ace391568b57fcae9ddda7527f64d84efb48153ae54e03e77c6d7"
)
EXPECTED_COUPLED_JULIA_DIFFERENTIAL_RECEIPT_SHA256 = (
    "3f5feb56c71de3cce1b2c1bb1336ba89189802ac56c6fffe9807e429fa1fe332"
)
VECTOR_FIELD_MULTIPLICITY_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalPolynomialVectorFieldMultiplicity.lean"
)
VECTOR_FIELD_MULTIPLICITY_TARGET = (
    "FormalPolynomialVectorFieldMultiplicity."
    "polynomial_vector_field_multiplicity_terminal_certificate"
)
VECTOR_FIELD_MULTIPLICITY_RECORD_SHA256 = (
    "e17e20a66f02bcebdcd2eb69f3caf15511099ee6a932e8e52c06cf0f3958d125"
)
EXPECTED_VECTOR_FIELD_MULTIPLICITY_RECEIPT_SHA256 = (
    "fef005fce45a01b7fee33fc76b3b392bc135fe1169295266eb0584b388258908"
)
TRIANGULAR_PROLONGATION_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalPolynomialVectorFieldTriangularProlongation.lean"
)
TRIANGULAR_PROLONGATION_TARGET = (
    "FormalPolynomialVectorFieldTriangularProlongation."
    "polynomial_vector_field_triangular_prolongation_terminal_certificate"
)
TRIANGULAR_PROLONGATION_RECORD_SHA256 = (
    "49ec02a1439d2681231c6db5770ab0f7f78ecbcfea3c286544d4aa0de11f526c"
)
EXPECTED_TRIANGULAR_PROLONGATION_RECEIPT_SHA256 = (
    "6d15b972e73314b044088a52ba894fea3cc1f0d571b085af1a70dd098f7efccf"
)
FINITE_PROLONGATION_ESCAPE_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalPolynomialVectorFieldFiniteProlongationEscape.lean"
)
FINITE_PROLONGATION_ESCAPE_TARGET = (
    "FormalPolynomialVectorFieldFiniteProlongationEscape."
    "polynomial_vector_field_finite_prolongation_escape_terminal_certificate"
)
FINITE_PROLONGATION_ESCAPE_RECORD_SHA256 = (
    "9089ac550986408cc211cf0e842673975df09f71be7e260363e7fbdc124c7be4"
)
EXPECTED_FINITE_PROLONGATION_ESCAPE_RECEIPT_SHA256 = (
    "f977b263e8f70f9f0e098f079e44788bca94061024e0167f96d1ac914fe9f76d"
)
DIFFERENTIAL_INVARIANT_SPECIALIZATION_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalDifferentialPolynomialInvariantSpecialization.lean"
)
DIFFERENTIAL_INVARIANT_SPECIALIZATION_TARGET = (
    "FormalDifferentialPolynomialInvariantSpecialization."
    "differential_polynomial_invariant_specialization_terminal_certificate"
)
DIFFERENTIAL_INVARIANT_SPECIALIZATION_RECORD_SHA256 = (
    "ac5df55300c07830f6fe1695cb3cb2bd178e9c104d05c27596efeebd8f2c69b4"
)
EXPECTED_DIFFERENTIAL_INVARIANT_SPECIALIZATION_RECEIPT_SHA256 = (
    "c87bc1088d9a7820c05c1c631ff472e289fda2989850f6a14fb604ee933dc4fc"
)
DERIVATION_ITERATED_LEIBNIZ_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalDerivationIteratedLeibniz.lean"
)
DERIVATION_ITERATED_LEIBNIZ_TARGET = (
    "FormalDerivationIteratedLeibniz."
    "derivation_iterated_leibniz_terminal_certificate"
)
DERIVATION_ITERATED_LEIBNIZ_RECORD_SHA256 = (
    "b8942ecd8796511053655f85b068a5ab8394e3350630e5008d2d637f1f16cdbc"
)
EXPECTED_DERIVATION_ITERATED_LEIBNIZ_RECEIPT_SHA256 = (
    "407a5a98863a3f98771b69758ed130e7dd9290209cddc5298073b226602583b2"
)
COUPLED_JULIA_ALL_ORDER_SPECIALIZATION_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalCoupledJuliaAllOrderSpecializationUnconditional.lean"
)
COUPLED_JULIA_ALL_ORDER_SPECIALIZATION_TARGET = (
    "FormalCoupledJuliaAllOrderSpecializationUnconditional."
    "coupled_julia_all_order_specialization_without_scalar_nonzero_"
    "terminal_certificate"
)
COUPLED_JULIA_ALL_ORDER_SPECIALIZATION_RECORD_SHA256 = (
    "1fd61139d56282c44089c43943960ba28990fe7c4ca626718d4bf17e92139b26"
)
EXPECTED_COUPLED_JULIA_ALL_ORDER_SPECIALIZATION_RECEIPT_SHA256 = (
    "a31da2183e7d0dc6be267051697204e6ab36f943fb7f7f83f28d078a13a61d6b"
)
ANALYTIC_KUMMER_LIFT_SOURCE = (
    LEAN_ROOT / "ZtareProofs" / "FormalAnalyticKummerLift.lean"
)
ANALYTIC_KUMMER_LIFT_TARGET = (
    "FormalAnalyticKummerLift."
    "analytic_kummer_lift_terminal_certificate"
)
ANALYTIC_KUMMER_LIFT_RECORD_SHA256 = (
    "b2c0303e108228cdabb399f493680c942e5309fec8b68dc0ff3d08ef380c1a53"
)
EXPECTED_ANALYTIC_KUMMER_LIFT_RECEIPT_SHA256 = (
    "28a3c3f934810f093e2fc0fbbd8231095e23e40d56919ba43ad3354dc4f04552"
)
SEPARATED_BRANCH_VALUATION_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalSeparatedPolynomialBranchValuation.lean"
)
SEPARATED_BRANCH_VALUATION_TARGET = (
    "FormalSeparatedPolynomialBranchValuation."
    "separated_polynomial_branch_valuation_terminal_certificate"
)
SEPARATED_BRANCH_VALUATION_RECORD_SHA256 = (
    "e95beaa9fd0fad531eff65148617cdd474cc79f385e8d08dda9273389dcd431a"
)
EXPECTED_SEPARATED_BRANCH_VALUATION_RECEIPT_SHA256 = (
    "e5e299636988d347285de47fa53d50ad0b58669e4a7e7721109b5cc9a3ee67f7"
)
ANALYTIC_ALGEBRAIC_BRANCH_BOUNDARY_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalAnalyticAlgebraicBranchBoundary.lean"
)
ANALYTIC_ALGEBRAIC_BRANCH_BOUNDARY_TARGET = (
    "FormalAnalyticAlgebraicBranchBoundary."
    "analytic_algebraic_branch_boundary_terminal_certificate"
)
ANALYTIC_ALGEBRAIC_BRANCH_BOUNDARY_RECORD_SHA256 = (
    "2dba25c7e49e10d69fd7079b255909a3b14949f1cd161c08032898e5354960d9"
)
EXPECTED_ANALYTIC_ALGEBRAIC_BRANCH_BOUNDARY_RECEIPT_SHA256 = (
    "e0972768c378472a259c30b7e8f0819df70802344dfba0e3fb17047e932479be"
)
SEPARATED_ANALYTIC_BRANCH_ASSEMBLY_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalSeparatedAnalyticBranchAssembly.lean"
)
SEPARATED_ANALYTIC_BRANCH_ASSEMBLY_TARGET = (
    "FormalSeparatedAnalyticBranchAssembly."
    "separated_analytic_branch_assembly_terminal_certificate"
)
SEPARATED_ANALYTIC_BRANCH_ASSEMBLY_RECORD_SHA256 = (
    "c41ea283911e4d1c4dfe7e6abb8ebcd7cdd79e129ecb7ba626da94c1566d0757"
)
EXPECTED_SEPARATED_ANALYTIC_BRANCH_ASSEMBLY_RECEIPT_SHA256 = (
    "cfd0c2aa47ee55f71e52c2db9a82d964d9a9a387cd4286a84d2c959736b3e832"
)
FINITE_ENDPOINT_ODE_CONTINUATION_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalAnalyticFiniteEndpointODEContinuation.lean"
)
FINITE_ENDPOINT_ODE_CONTINUATION_TARGET = (
    "FormalAnalyticFiniteEndpointODEContinuation."
    "analytic_finite_endpoint_ode_continuation_terminal_certificate"
)
FINITE_ENDPOINT_ODE_CONTINUATION_RECORD_SHA256 = (
    "59606a1a955c9c7de78db4abb65a374b4c485ca1984b199b18be661045fe67fa"
)
EXPECTED_FINITE_ENDPOINT_ODE_CONTINUATION_RECEIPT_SHA256 = (
    "4a49afa18c8bd78e47cf080e3ffd8121bd3a1b44b851a97c156e5f2b4dffaff6"
)
BOUNDED_DERIVATIVE_ENDPOINT_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalBoundedDerivativeEndpointLimit.lean"
)
BOUNDED_DERIVATIVE_ENDPOINT_TARGET = (
    "FormalBoundedDerivativeEndpointLimit."
    "bounded_derivative_endpoint_limit_terminal_certificate"
)
BOUNDED_DERIVATIVE_ENDPOINT_RECORD_SHA256 = (
    "9bcdf8d78a402b45c78d2570e29386625f4aa855e840d8e863b4c73661abb421"
)
EXPECTED_BOUNDED_DERIVATIVE_ENDPOINT_RECEIPT_SHA256 = (
    "af1b0f0210f871aa32ff741e1baa5ce23d0ea186b5188d5925ad5357051e12ed"
)
BOUNDED_DERIVATIVE_ENDPOINT_GOAL = (
    "Construct a finite left-endpoint limit for every complete-real-normed-"
    "space trajectory on a finite half-open interval from only "
    "differentiability and a uniform derivative bound."
)
BOUNDED_CONTROLLED_POLYNOMIAL_ENDPOINT_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalBoundedControlledPolynomialEndpoint.lean"
)
BOUNDED_CONTROLLED_POLYNOMIAL_ENDPOINT_TARGET = (
    "FormalBoundedControlledPolynomialEndpoint."
    "bounded_controlled_polynomial_endpoint_terminal_certificate"
)
BOUNDED_CONTROLLED_POLYNOMIAL_ENDPOINT_RECORD_SHA256 = (
    "01b18c94801a24c0cbef421dda8c279e8168e14d94d9c751aee46daf6ed737db"
)
EXPECTED_BOUNDED_CONTROLLED_POLYNOMIAL_ENDPOINT_RECEIPT_SHA256 = (
    "55bb145bb04cc6f05ed8b301054c1f44189da4f628cdd488f6a169ea2b47f1a5"
)
BOUNDED_CONTROLLED_POLYNOMIAL_ENDPOINT_GOAL = (
    "Derive the explicit uniform speed bound and a finite left-endpoint "
    "limit for a complex controlled-polynomial trajectory from only the "
    "ODE and uniform driver/state bounds on a finite half-open interval."
)
NORM_ESCAPE_RECIPROCAL_LIMIT_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalNormEscapeReciprocalLimit.lean"
)
NORM_ESCAPE_RECIPROCAL_LIMIT_TARGET = (
    "FormalNormEscapeReciprocalLimit."
    "norm_escape_reciprocal_limit_terminal_certificate"
)
NORM_ESCAPE_RECIPROCAL_LIMIT_RECORD_SHA256 = (
    "67e0c54d559d3425a3156e43f04dd5cd41c91abc54b4daaee8460c8f93ea8af7"
)
EXPECTED_NORM_ESCAPE_RECIPROCAL_LIMIT_RECEIPT_SHA256 = (
    "4ce398507c2ed80e4f370afa548a06f742f87376a5ed8de61d3ad8d652acf934"
)
NORM_ESCAPE_RECIPROCAL_LIMIT_GOAL = (
    "Construct eventual nonvanishing and reciprocal convergence to zero "
    "for every trajectory into a nontrivially normed field from only "
    "convergence of its norm to infinity along an arbitrary source filter."
)
UNIFORM_RESTART_ENDPOINT_ESCAPE_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalUniformRestartEndpointEscape.lean"
)
UNIFORM_RESTART_ENDPOINT_ESCAPE_TARGET = (
    "FormalUniformRestartEndpointEscape."
    "uniform_restart_endpoint_escape_terminal_certificate"
)
UNIFORM_RESTART_ENDPOINT_ESCAPE_RECORD_SHA256 = (
    "1c7573b2d50b3d7e3de72d9c0c9a2aa1dfb91c2ee67dfa782d179e93d1577391"
)
EXPECTED_UNIFORM_RESTART_ENDPOINT_ESCAPE_RECEIPT_SHA256 = (
    "ca90dc44704eae98a224ba6c95fe69289c89b2cc241021c795f1b14e5fda1c07"
)
UNIFORM_RESTART_ENDPOINT_ESCAPE_GOAL = (
    "Prove for every restriction-stable locally unique trajectory category "
    "with restart time uniform on each bounded state ball that a finite-"
    "endpoint trajectory either extends through the endpoint or has norm "
    "tending to infinity, and derive norm escape from absence of extension."
)
CONTROLLED_POLYNOMIAL_UNIFORM_RESTART_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalControlledPolynomialUniformRestart.lean"
)
CONTROLLED_POLYNOMIAL_UNIFORM_RESTART_TARGET = (
    "FormalControlledPolynomialUniformRestart."
    "controlled_polynomial_uniform_restart_terminal_certificate"
)
CONTROLLED_POLYNOMIAL_UNIFORM_RESTART_RECORD_SHA256 = (
    "39f57f7f8537e0dcfe07130160bb26c3f00f1685a74d29d6e7b4de5adfd62251"
)
EXPECTED_CONTROLLED_POLYNOMIAL_UNIFORM_RESTART_RECEIPT_SHA256 = (
    "eea30edabd7b12f683d878baf193f806cd4ba9db05d2be38c52941d11db68da9"
)
CONTROLLED_POLYNOMIAL_UNIFORM_RESTART_GOAL = (
    "Construct one positive restart time uniform over all real restart "
    "times and all complex initial states in a fixed norm ball for "
    "y'=driver(t)*p(y), from continuity and a global driver bound, with "
    "no supplied local solution or Picard witness."
)
CONTROLLED_POLYNOMIAL_OVERLAP_UNIQUENESS_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalControlledPolynomialOverlapUniqueness.lean"
)
CONTROLLED_POLYNOMIAL_OVERLAP_UNIQUENESS_TARGET = (
    "FormalControlledPolynomialOverlapUniqueness."
    "controlled_polynomial_overlap_uniqueness_terminal_certificate"
)
CONTROLLED_POLYNOMIAL_OVERLAP_UNIQUENESS_RECORD_SHA256 = (
    "9f35200f054a5351365e5b287f9868fd031343dc7eca98ba425527a8efc79da6"
)
EXPECTED_CONTROLLED_POLYNOMIAL_OVERLAP_UNIQUENESS_RECEIPT_SHA256 = (
    "419f63bac8ac57b8c6c1ba880f8d34709e372ff26bc7006f012210bbed8c68ed"
)
CONTROLLED_POLYNOMIAL_OVERLAP_UNIQUENESS_GOAL = (
    ": ∀ (p : ℂ[X]) (driver : ℝ → ℂ) (driverBound : ℝ≥0), "
    "(∀ t, ‖driver t‖₊ ≤ driverBound) → ∀ (domain : Set ℝ) "
    "(left right : ℝ → ℂ) (anchor : ℝ), IsPreconnected domain → "
    "anchor ∈ domain → (∀ t ∈ domain, HasDerivAt left "
    "(driver t * p.eval (left t)) t) → (∀ t ∈ domain, "
    "HasDerivAt right (driver t * p.eval (right t)) t) → "
    "left anchor = right anchor → EqOn left right domain"
)
CONTROLLED_POLYNOMIAL_MAXIMAL_TRAJECTORY_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "FormalControlledPolynomialMaximalTrajectory.lean"
)
CONTROLLED_POLYNOMIAL_MAXIMAL_TRAJECTORY_TARGET = (
    "FormalControlledPolynomialMaximalTrajectory."
    "controlled_polynomial_maximal_trajectory_terminal_certificate"
)
CONTROLLED_POLYNOMIAL_MAXIMAL_TRAJECTORY_RECORD_SHA256 = (
    "1d2d23b6ea0c9044f07e3b2b985b7585fc3b770c846fa2ffdd79d647063daa46"
)
EXPECTED_CONTROLLED_POLYNOMIAL_MAXIMAL_TRAJECTORY_RECEIPT_SHA256 = (
    "0d8d07ef473d85f13f71a3d56a235e14b338849dfb391f807726db9b02c693db"
)
CONTROLLED_POLYNOMIAL_MAXIMAL_TRAJECTORY_GOAL = (
    ": ∀ (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier) "
    "(anchor : ℝ) (state : ℂ), "
    "ControlledPolynomialMaximalTrajectoryOutcome p carrier anchor state"
)
EXPECTED_MONODROMY_RESIDUE_SHA256 = (
    "c27c46c0e1d4d83a93714ebe4fafe3dae4994320ceac592b2cfd273a5bce898d"
)
EXPECTED_EQUILIBRIUM_TRANSITION_SHA256 = (
    "7858bb75adf8f7199b894d35a41b2a9211330a40cc534aee3acbe7aefbdc3210"
)
EXPECTED_FINITE_MONODROMY_COUNTERMODELS_SHA256 = (
    "013cafdb99d8de33106059b9a6afe6475991a5e095221166c4a52549d19ec22a"
)
EXPECTED_PROJECTION_FALLACY_SHA256 = (
    "9693925138efb8db07be2afee0d65d7aba8d5b3d5864bfa976ad510eeea5b90e"
)
EXPECTED_SINGLE_FLOW_SHA256 = (
    "6c3a97ebae223d4c0dbf6762d1399d242ea951459d3e7ae44255be2575931926"
)
EXPECTED_TWO_FLOW_SHA256 = (
    "190c7ff996246b663dc6ab94435aaea81fa8f8e4c009188badac06ec88bc963c"
)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _semantic_identity(
    *,
    role: str,
    statement: str,
    evidence_sha256s: tuple[str, ...],
) -> str:
    return content_sha256({
        "schema": "axiompack.formal_residual_semantic_proposition.v1",
        "role": role,
        "statement": statement,
        "evidence_sha256s": list(evidence_sha256s),
    })


def _governed_support(
    *,
    source_path: Path,
    target: str,
    record_sha256: str,
    expected_receipt_sha256: str,
    goal: str | None = None,
) -> tuple[GovernedFormalSupport, GovernedFormalPropositionIdentity]:
    source = source_path.read_text(encoding="utf-8")
    posed, proof = open_decl_for_ratification(source, target)
    signature = normalized_target_signature(source, target)
    ratification_goal = signature if goal is None else goal
    arguments: dict[str, Any] = {
        "certificate_ledger": CERTIFICATE_LEDGER,
        "governed_record_sha256": record_sha256,
        "parity_ledger": PARITY_LEDGER,
        "target": target,
        "expected_signature": signature,
        "posed_source": posed,
        "proof_text": proof,
        "goal": ratification_goal,
        "lean_root": LEAN_ROOT,
        "expected_provider": "existing_artifact",
    }
    receipt = make_content_bound_evidence_from_governed_ratification(
        **arguments
    )
    assert receipt.receipt_sha256 == expected_receipt_sha256
    support = GovernedFormalSupport(
        receipt=receipt,
        certificate_ledger=CERTIFICATE_LEDGER,
        governed_record_sha256=record_sha256,
        parity_ledger=PARITY_LEDGER,
        target=target,
        expected_signature=signature,
        posed_source=posed,
        proof_text=proof,
        goal=ratification_goal,
        lean_root=LEAN_ROOT,
        expected_provider="existing_artifact",
    )
    formal_identity = governed_formal_proposition_identity_from_receipt(
        receipt
    )
    return support, formal_identity


def run(verification_rows: int = 8) -> dict[str, object]:
    """Compile the exact formalization residual of the Puiseux terminal."""

    # Resolve and cache the authority environment before the symbolic replay.
    # The replay is CPU-heavy but cannot mutate the Lean toolchain identity.
    toolchain = closure_toolchain_identity(LEAN_ROOT)
    if toolchain.get("complete") is not True:
        raise RuntimeError("current Lean toolchain identity is incomplete")
    puiseux = puiseux_run(verification_rows)
    single = puiseux["filtered_obstruction_compiler"]
    two_flow = puiseux["conditional_two_flow_obstruction_compiler"]
    single_digest = str(single["puiseux_flow_certificate_sha256"])
    two_flow_digest = str(two_flow["two_flow_puiseux_certificate_sha256"])
    assert single_digest == EXPECTED_SINGLE_FLOW_SHA256
    assert two_flow_digest == EXPECTED_TWO_FLOW_SHA256
    assert (
        puiseux["equilibrium_transition_countermodel"]["certificate_sha256"]
        == EXPECTED_EQUILIBRIUM_TRANSITION_SHA256
    )
    monodromy_residue = monodromy_residue_run()
    assert (
        monodromy_residue["certificate_sha256"]
        == EXPECTED_MONODROMY_RESIDUE_SHA256
    )
    finite_monodromy_countermodels = finite_monodromy_countermodels_run()
    assert finite_monodromy_countermodels["certificate_sha256"] == (
        EXPECTED_FINITE_MONODROMY_COUNTERMODELS_SHA256
    )
    projection_fallacy = projection_fallacy_run()
    assert projection_fallacy["certificate_sha256"] == (
        EXPECTED_PROJECTION_FALLACY_SHA256
    )

    adapter_sha256 = content_sha256({
        "puiseux": puiseux,
        "monodromy_residue": monodromy_residue,
        "finite_monodromy_countermodels": finite_monodromy_countermodels,
        "projection_fallacy": projection_fallacy,
    })
    script_sha256 = _file_sha256(
        JACOBIAN / "gauge_pure_contact_zero_witt_puiseux_obstruction.py"
    )
    monodromy_script_sha256 = _file_sha256(
        JACOBIAN / "gauge_critical_monodromy_residue.py"
    )
    arithmetic_support, arithmetic_identity = _governed_support(
        source_path=ARITHMETIC_SOURCE,
        target=ARITHMETIC_TARGET,
        record_sha256=ARITHMETIC_RECORD_SHA256,
        expected_receipt_sha256=EXPECTED_ARITHMETIC_RECEIPT_SHA256,
    )
    coefficient_support, coefficient_identity = _governed_support(
        source_path=MECHANISM_SOURCE,
        target=COEFFICIENT_TARGET,
        record_sha256=COEFFICIENT_RECORD_SHA256,
        expected_receipt_sha256=EXPECTED_COEFFICIENT_RECEIPT_SHA256,
    )
    interval_support, interval_identity = _governed_support(
        source_path=MECHANISM_SOURCE,
        target=TWO_FLOW_INTERVAL_TARGET,
        record_sha256=TWO_FLOW_INTERVAL_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_TWO_FLOW_INTERVAL_RECEIPT_SHA256
        ),
    )
    germ_support_rows = tuple(
        (
            role,
            *_governed_support(
                source_path=GERM_SOURCE,
                target=target,
                record_sha256=record_sha256,
                expected_receipt_sha256=receipt_sha256,
            ),
        )
        for role, target, record_sha256, receipt_sha256 in GERM_SUPPORT_SPECS
    )
    germ_identities = {
        role: identity
        for role, _support, identity in germ_support_rows
    }
    series_support, series_identity = _governed_support(
        source_path=SERIES_SOURCE,
        target=SERIES_TARGET,
        record_sha256=SERIES_RECORD_SHA256,
        expected_receipt_sha256=EXPECTED_SERIES_RECEIPT_SHA256,
    )
    julia_support, julia_formal_identity = _governed_support(
        source_path=JULIA_SOURCE,
        target=JULIA_TARGET,
        record_sha256=JULIA_RECORD_SHA256,
        expected_receipt_sha256=EXPECTED_JULIA_RECEIPT_SHA256,
    )
    proportional_semigroup_support, proportional_semigroup_identity = (
        _governed_support(
            source_path=PROPORTIONAL_SEMIGROUP_SOURCE,
            target=PROPORTIONAL_SEMIGROUP_TARGET,
            record_sha256=PROPORTIONAL_SEMIGROUP_RECORD_SHA256,
            expected_receipt_sha256=(
                EXPECTED_PROPORTIONAL_SEMIGROUP_RECEIPT_SHA256
            ),
        )
    )
    proportional_trajectory_support, proportional_trajectory_identity = (
        _governed_support(
            source_path=PROPORTIONAL_TRAJECTORY_SOURCE,
            target=PROPORTIONAL_TRAJECTORY_TARGET,
            record_sha256=PROPORTIONAL_TRAJECTORY_RECORD_SHA256,
            expected_receipt_sha256=(
                EXPECTED_PROPORTIONAL_TRAJECTORY_RECEIPT_SHA256
            ),
        )
    )
    proportional_reduction_support, proportional_reduction_identity = (
        _governed_support(
            source_path=PROPORTIONAL_REDUCTION_SOURCE,
            target=PROPORTIONAL_REDUCTION_TARGET,
            record_sha256=PROPORTIONAL_REDUCTION_RECORD_SHA256,
            expected_receipt_sha256=(
                EXPECTED_PROPORTIONAL_REDUCTION_RECEIPT_SHA256
            ),
        )
    )
    selected_germ_support, selected_germ_formal_inference = (
        _governed_support(
            source_path=SELECTED_GERM_SOURCE,
            target=SELECTED_GERM_TARGET,
            record_sha256=SELECTED_GERM_RECORD_SHA256,
            expected_receipt_sha256=(
                EXPECTED_SELECTED_GERM_RECEIPT_SHA256
            ),
        )
    )
    single_flow_obstruction_support, single_flow_obstruction_identity = (
        _governed_support(
            source_path=COMPLEX_SINGLE_FLOW_SOURCE,
            target=COMPLEX_SINGLE_FLOW_TARGET,
            record_sha256=COMPLEX_SINGLE_FLOW_RECORD_SHA256,
            expected_receipt_sha256=(
                EXPECTED_COMPLEX_SINGLE_FLOW_RECEIPT_SHA256
            ),
            goal="",
        )
    )
    analytic_continuation_support, analytic_continuation_identity = (
        _governed_support(
            source_path=ANALYTIC_CONTINUATION_SOURCE,
            target=ANALYTIC_CONTINUATION_TARGET,
            record_sha256=ANALYTIC_CONTINUATION_RECORD_SHA256,
            expected_receipt_sha256=(
                EXPECTED_ANALYTIC_CONTINUATION_RECEIPT_SHA256
            ),
        )
    )
    analytic_taylor_support, analytic_taylor_identity = _governed_support(
        source_path=ANALYTIC_TAYLOR_SOURCE,
        target=ANALYTIC_TAYLOR_TARGET,
        record_sha256=ANALYTIC_TAYLOR_RECORD_SHA256,
        expected_receipt_sha256=EXPECTED_ANALYTIC_TAYLOR_RECEIPT_SHA256,
    )
    formal_linear_ode_support, formal_linear_ode_identity = (
        _governed_support(
            source_path=FORMAL_LINEAR_ODE_SOURCE,
            target=FORMAL_LINEAR_ODE_TARGET,
            record_sha256=FORMAL_LINEAR_ODE_RECORD_SHA256,
            expected_receipt_sha256=(
                EXPECTED_FORMAL_LINEAR_ODE_RECEIPT_SHA256
            ),
        )
    )
    constructed_endpoint_support, constructed_endpoint_identity = (
        _governed_support(
            source_path=CONSTRUCTED_ENDPOINT_SOURCE,
            target=CONSTRUCTED_ENDPOINT_TARGET,
            record_sha256=CONSTRUCTED_ENDPOINT_RECORD_SHA256,
            expected_receipt_sha256=(
                EXPECTED_CONSTRUCTED_ENDPOINT_RECEIPT_SHA256
            ),
        )
    )
    constructed_single_flow_support, constructed_single_flow_identity = (
        _governed_support(
            source_path=CONSTRUCTED_SINGLE_FLOW_SOURCE,
            target=CONSTRUCTED_SINGLE_FLOW_TARGET,
            record_sha256=CONSTRUCTED_SINGLE_FLOW_RECORD_SHA256,
            expected_receipt_sha256=(
                EXPECTED_CONSTRUCTED_SINGLE_FLOW_RECEIPT_SHA256
            ),
        )
    )
    selected_chart_support, selected_chart_identity = _governed_support(
        source_path=SELECTED_CHART_SOURCE,
        target=SELECTED_CHART_TARGET,
        record_sha256=SELECTED_CHART_RECORD_SHA256,
        expected_receipt_sha256=EXPECTED_SELECTED_CHART_RECEIPT_SHA256,
    )
    julia_assembly_support, julia_assembly_identity = _governed_support(
        source_path=COMPLEX_SINGLE_FLOW_ANALYTIC_SOURCE,
        target=COMPLEX_JULIA_TRANSPORT_TARGET,
        record_sha256=COMPLEX_JULIA_TRANSPORT_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_COMPLEX_JULIA_TRANSPORT_RECEIPT_SHA256
        ),
        goal="",
    )
    (single_flow_analytic_obstruction_support,
        single_flow_analytic_obstruction_identity) = _governed_support(
        source_path=COMPLEX_SINGLE_FLOW_ANALYTIC_SOURCE,
        target=COMPLEX_SINGLE_FLOW_ANALYTIC_TARGET,
        record_sha256=COMPLEX_SINGLE_FLOW_ANALYTIC_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_COMPLEX_SINGLE_FLOW_ANALYTIC_RECEIPT_SHA256
        ),
        goal="",
    )
    (finite_julia_classification_support,
        finite_julia_classification_identity) = _governed_support(
        source_path=FINITE_JULIA_CLASSIFICATION_SOURCE,
        target=FINITE_JULIA_CLASSIFICATION_TARGET,
        record_sha256=FINITE_JULIA_CLASSIFICATION_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_FINITE_JULIA_CLASSIFICATION_RECEIPT_SHA256
        ),
        goal="",
    )
    (two_flow_abel_assembly_support,
        two_flow_abel_assembly_identity) = _governed_support(
        source_path=TWO_FLOW_ABEL_ASSEMBLY_SOURCE,
        target=TWO_FLOW_ABEL_ASSEMBLY_TARGET,
        record_sha256=TWO_FLOW_ABEL_ASSEMBLY_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_TWO_FLOW_ABEL_ASSEMBLY_RECEIPT_SHA256
        ),
        goal="",
    )
    (critical_two_julia_exclusion_support,
        critical_two_julia_exclusion_identity) = _governed_support(
        source_path=CRITICAL_TWO_JULIA_EXCLUSION_SOURCE,
        target=CRITICAL_TWO_JULIA_EXCLUSION_TARGET,
        record_sha256=CRITICAL_TWO_JULIA_EXCLUSION_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_CRITICAL_TWO_JULIA_EXCLUSION_RECEIPT_SHA256
        ),
        goal="",
    )
    (monodromy_non_torsion_support,
        monodromy_non_torsion_identity) = _governed_support(
        source_path=MONODROMY_NON_TORSION_SOURCE,
        target=MONODROMY_NON_TORSION_TARGET,
        record_sha256=MONODROMY_NON_TORSION_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_MONODROMY_NON_TORSION_RECEIPT_SHA256
        ),
        goal="",
    )
    (critical_residue_irrationality_support,
        critical_residue_irrationality_identity) = _governed_support(
        source_path=CRITICAL_RESIDUE_IRRATIONALITY_SOURCE,
        target=CRITICAL_RESIDUE_IRRATIONALITY_TARGET,
        record_sha256=CRITICAL_RESIDUE_IRRATIONALITY_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_CRITICAL_RESIDUE_IRRATIONALITY_RECEIPT_SHA256
        ),
        goal="",
    )
    (critical_monodromy_binding_support,
        critical_monodromy_binding_identity) = _governed_support(
        source_path=CRITICAL_MONODROMY_BINDING_SOURCE,
        target=CRITICAL_MONODROMY_BINDING_TARGET,
        record_sha256=CRITICAL_MONODROMY_BINDING_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_CRITICAL_MONODROMY_BINDING_RECEIPT_SHA256
        ),
        goal="",
    )
    (critical_connection_rationalization_support,
        critical_connection_rationalization_identity) = _governed_support(
        source_path=CRITICAL_CONNECTION_RATIONALIZATION_SOURCE,
        target=CRITICAL_CONNECTION_RATIONALIZATION_TARGET,
        record_sha256=CRITICAL_CONNECTION_RATIONALIZATION_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_CRITICAL_CONNECTION_RATIONALIZATION_RECEIPT_SHA256
        ),
        goal="",
    )
    (critical_holonomy_loop_support,
        critical_holonomy_loop_identity) = _governed_support(
        source_path=CRITICAL_HOLONOMY_LOOP_SOURCE,
        target=CRITICAL_HOLONOMY_LOOP_TARGET,
        record_sha256=CRITICAL_HOLONOMY_LOOP_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_CRITICAL_HOLONOMY_LOOP_RECEIPT_SHA256
        ),
        goal="",
    )
    (coupled_julia_elimination_support,
        coupled_julia_elimination_identity) = _governed_support(
        source_path=COUPLED_JULIA_ELIMINATION_SOURCE,
        target=COUPLED_JULIA_ELIMINATION_TARGET,
        record_sha256=COUPLED_JULIA_ELIMINATION_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_COUPLED_JULIA_ELIMINATION_RECEIPT_SHA256
        ),
        goal="",
    )
    (finite_state_trajectory_support,
        finite_state_trajectory_identity) = _governed_support(
        source_path=FINITE_STATE_TRAJECTORY_SOURCE,
        target=FINITE_STATE_TRAJECTORY_TARGET,
        record_sha256=FINITE_STATE_TRAJECTORY_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_FINITE_STATE_TRAJECTORY_RECEIPT_SHA256
        ),
        goal="",
    )
    (coupled_julia_differential_support,
        coupled_julia_differential_identity) = _governed_support(
        source_path=COUPLED_JULIA_DIFFERENTIAL_SOURCE,
        target=COUPLED_JULIA_DIFFERENTIAL_TARGET,
        record_sha256=COUPLED_JULIA_DIFFERENTIAL_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_COUPLED_JULIA_DIFFERENTIAL_RECEIPT_SHA256
        ),
        goal="",
    )
    (vector_field_multiplicity_support,
        vector_field_multiplicity_identity) = _governed_support(
        source_path=VECTOR_FIELD_MULTIPLICITY_SOURCE,
        target=VECTOR_FIELD_MULTIPLICITY_TARGET,
        record_sha256=VECTOR_FIELD_MULTIPLICITY_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_VECTOR_FIELD_MULTIPLICITY_RECEIPT_SHA256
        ),
        goal="",
    )
    (triangular_prolongation_support,
        triangular_prolongation_identity) = _governed_support(
        source_path=TRIANGULAR_PROLONGATION_SOURCE,
        target=TRIANGULAR_PROLONGATION_TARGET,
        record_sha256=TRIANGULAR_PROLONGATION_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_TRIANGULAR_PROLONGATION_RECEIPT_SHA256
        ),
        goal="",
    )
    (finite_prolongation_escape_support,
        finite_prolongation_escape_identity) = _governed_support(
        source_path=FINITE_PROLONGATION_ESCAPE_SOURCE,
        target=FINITE_PROLONGATION_ESCAPE_TARGET,
        record_sha256=FINITE_PROLONGATION_ESCAPE_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_FINITE_PROLONGATION_ESCAPE_RECEIPT_SHA256
        ),
        goal="",
    )
    (differential_invariant_specialization_support,
        differential_invariant_specialization_identity) = _governed_support(
        source_path=DIFFERENTIAL_INVARIANT_SPECIALIZATION_SOURCE,
        target=DIFFERENTIAL_INVARIANT_SPECIALIZATION_TARGET,
        record_sha256=(
            DIFFERENTIAL_INVARIANT_SPECIALIZATION_RECORD_SHA256
        ),
        expected_receipt_sha256=(
            EXPECTED_DIFFERENTIAL_INVARIANT_SPECIALIZATION_RECEIPT_SHA256
        ),
        goal="",
    )
    (derivation_iterated_leibniz_support,
        derivation_iterated_leibniz_identity) = _governed_support(
        source_path=DERIVATION_ITERATED_LEIBNIZ_SOURCE,
        target=DERIVATION_ITERATED_LEIBNIZ_TARGET,
        record_sha256=DERIVATION_ITERATED_LEIBNIZ_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_DERIVATION_ITERATED_LEIBNIZ_RECEIPT_SHA256
        ),
        goal="",
    )
    (coupled_julia_all_order_specialization_support,
        coupled_julia_all_order_specialization_identity) = _governed_support(
        source_path=COUPLED_JULIA_ALL_ORDER_SPECIALIZATION_SOURCE,
        target=COUPLED_JULIA_ALL_ORDER_SPECIALIZATION_TARGET,
        record_sha256=(
            COUPLED_JULIA_ALL_ORDER_SPECIALIZATION_RECORD_SHA256
        ),
        expected_receipt_sha256=(
            EXPECTED_COUPLED_JULIA_ALL_ORDER_SPECIALIZATION_RECEIPT_SHA256
        ),
        goal="",
    )
    (analytic_kummer_lift_support,
        analytic_kummer_lift_identity) = _governed_support(
        source_path=ANALYTIC_KUMMER_LIFT_SOURCE,
        target=ANALYTIC_KUMMER_LIFT_TARGET,
        record_sha256=ANALYTIC_KUMMER_LIFT_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_ANALYTIC_KUMMER_LIFT_RECEIPT_SHA256
        ),
        goal="",
    )
    (separated_branch_valuation_support,
        separated_branch_valuation_identity) = _governed_support(
        source_path=SEPARATED_BRANCH_VALUATION_SOURCE,
        target=SEPARATED_BRANCH_VALUATION_TARGET,
        record_sha256=SEPARATED_BRANCH_VALUATION_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_SEPARATED_BRANCH_VALUATION_RECEIPT_SHA256
        ),
        goal="",
    )
    (analytic_algebraic_branch_boundary_support,
        analytic_algebraic_branch_boundary_identity) = _governed_support(
        source_path=ANALYTIC_ALGEBRAIC_BRANCH_BOUNDARY_SOURCE,
        target=ANALYTIC_ALGEBRAIC_BRANCH_BOUNDARY_TARGET,
        record_sha256=ANALYTIC_ALGEBRAIC_BRANCH_BOUNDARY_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_ANALYTIC_ALGEBRAIC_BRANCH_BOUNDARY_RECEIPT_SHA256
        ),
        goal="",
    )
    (separated_analytic_branch_assembly_support,
        separated_analytic_branch_assembly_identity) = _governed_support(
        source_path=SEPARATED_ANALYTIC_BRANCH_ASSEMBLY_SOURCE,
        target=SEPARATED_ANALYTIC_BRANCH_ASSEMBLY_TARGET,
        record_sha256=SEPARATED_ANALYTIC_BRANCH_ASSEMBLY_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_SEPARATED_ANALYTIC_BRANCH_ASSEMBLY_RECEIPT_SHA256
        ),
        goal="",
    )
    (finite_endpoint_ode_continuation_support,
        finite_endpoint_ode_continuation_identity) = _governed_support(
        source_path=FINITE_ENDPOINT_ODE_CONTINUATION_SOURCE,
        target=FINITE_ENDPOINT_ODE_CONTINUATION_TARGET,
        record_sha256=FINITE_ENDPOINT_ODE_CONTINUATION_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_FINITE_ENDPOINT_ODE_CONTINUATION_RECEIPT_SHA256
        ),
        goal="",
    )
    (bounded_derivative_endpoint_support,
        bounded_derivative_endpoint_identity) = _governed_support(
        source_path=BOUNDED_DERIVATIVE_ENDPOINT_SOURCE,
        target=BOUNDED_DERIVATIVE_ENDPOINT_TARGET,
        record_sha256=BOUNDED_DERIVATIVE_ENDPOINT_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_BOUNDED_DERIVATIVE_ENDPOINT_RECEIPT_SHA256
        ),
        goal=BOUNDED_DERIVATIVE_ENDPOINT_GOAL,
    )
    (bounded_controlled_polynomial_endpoint_support,
        bounded_controlled_polynomial_endpoint_identity) = _governed_support(
        source_path=BOUNDED_CONTROLLED_POLYNOMIAL_ENDPOINT_SOURCE,
        target=BOUNDED_CONTROLLED_POLYNOMIAL_ENDPOINT_TARGET,
        record_sha256=(
            BOUNDED_CONTROLLED_POLYNOMIAL_ENDPOINT_RECORD_SHA256
        ),
        expected_receipt_sha256=(
            EXPECTED_BOUNDED_CONTROLLED_POLYNOMIAL_ENDPOINT_RECEIPT_SHA256
        ),
        goal=BOUNDED_CONTROLLED_POLYNOMIAL_ENDPOINT_GOAL,
    )
    (norm_escape_reciprocal_limit_support,
        norm_escape_reciprocal_limit_identity) = _governed_support(
        source_path=NORM_ESCAPE_RECIPROCAL_LIMIT_SOURCE,
        target=NORM_ESCAPE_RECIPROCAL_LIMIT_TARGET,
        record_sha256=NORM_ESCAPE_RECIPROCAL_LIMIT_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_NORM_ESCAPE_RECIPROCAL_LIMIT_RECEIPT_SHA256
        ),
        goal=NORM_ESCAPE_RECIPROCAL_LIMIT_GOAL,
    )
    (uniform_restart_endpoint_escape_support,
        uniform_restart_endpoint_escape_identity) = _governed_support(
        source_path=UNIFORM_RESTART_ENDPOINT_ESCAPE_SOURCE,
        target=UNIFORM_RESTART_ENDPOINT_ESCAPE_TARGET,
        record_sha256=UNIFORM_RESTART_ENDPOINT_ESCAPE_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_UNIFORM_RESTART_ENDPOINT_ESCAPE_RECEIPT_SHA256
        ),
        goal=UNIFORM_RESTART_ENDPOINT_ESCAPE_GOAL,
    )
    (controlled_polynomial_uniform_restart_support,
        controlled_polynomial_uniform_restart_identity) = _governed_support(
        source_path=CONTROLLED_POLYNOMIAL_UNIFORM_RESTART_SOURCE,
        target=CONTROLLED_POLYNOMIAL_UNIFORM_RESTART_TARGET,
        record_sha256=CONTROLLED_POLYNOMIAL_UNIFORM_RESTART_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_CONTROLLED_POLYNOMIAL_UNIFORM_RESTART_RECEIPT_SHA256
        ),
        goal=CONTROLLED_POLYNOMIAL_UNIFORM_RESTART_GOAL,
    )
    (controlled_polynomial_overlap_uniqueness_support,
        controlled_polynomial_overlap_uniqueness_identity) = (
        _governed_support(
            source_path=CONTROLLED_POLYNOMIAL_OVERLAP_UNIQUENESS_SOURCE,
            target=CONTROLLED_POLYNOMIAL_OVERLAP_UNIQUENESS_TARGET,
            record_sha256=(
                CONTROLLED_POLYNOMIAL_OVERLAP_UNIQUENESS_RECORD_SHA256
            ),
            expected_receipt_sha256=(
                EXPECTED_CONTROLLED_POLYNOMIAL_OVERLAP_UNIQUENESS_RECEIPT_SHA256
            ),
            goal=CONTROLLED_POLYNOMIAL_OVERLAP_UNIQUENESS_GOAL,
        )
    )
    (controlled_polynomial_maximal_trajectory_support,
        controlled_polynomial_maximal_trajectory_identity) = (
        _governed_support(
            source_path=CONTROLLED_POLYNOMIAL_MAXIMAL_TRAJECTORY_SOURCE,
            target=CONTROLLED_POLYNOMIAL_MAXIMAL_TRAJECTORY_TARGET,
            record_sha256=(
                CONTROLLED_POLYNOMIAL_MAXIMAL_TRAJECTORY_RECORD_SHA256
            ),
            expected_receipt_sha256=(
                EXPECTED_CONTROLLED_POLYNOMIAL_MAXIMAL_TRAJECTORY_RECEIPT_SHA256
            ),
            goal=CONTROLLED_POLYNOMIAL_MAXIMAL_TRAJECTORY_GOAL,
        )
    )
    active_support_rows = (
        (
            "critical_arithmetic",
            arithmetic_support,
            arithmetic_identity,
        ),
        (
            "coefficient_cancellation_mechanism",
            coefficient_support,
            coefficient_identity,
        ),
        (
            "two_flow_exponent_interval",
            interval_support,
            interval_identity,
        ),
        (
            "selected_algebraic_germ_series_passage",
            series_support,
            series_identity,
        ),
        (
            "julia_formal_flow_identity",
            julia_support,
            julia_formal_identity,
        ),
        (
            "two_flow_proportional_semigroup_reduction",
            proportional_semigroup_support,
            proportional_semigroup_identity,
        ),
        (
            "two_flow_proportional_same_flow_identification",
            proportional_trajectory_support,
            proportional_trajectory_identity,
        ),
        (
            "two_flow_proportional_autonomous_inference",
            proportional_reduction_support,
            proportional_reduction_identity,
        ),
        (
            "selected_algebraic_germ_inference",
            selected_germ_support,
            selected_germ_formal_inference,
        ),
        (
            "single_flow_ramified_root_factor_obstruction",
            single_flow_obstruction_support,
            single_flow_obstruction_identity,
        ),
        (
            "analytic_continuation_julia_transport",
            analytic_continuation_support,
            analytic_continuation_identity,
        ),
        (
            "analytic_germ_to_powerSeries_transport",
            analytic_taylor_support,
            analytic_taylor_identity,
        ),
        (
            "normalized_formal_linear_ode_constructor",
            formal_linear_ode_support,
            formal_linear_ode_identity,
        ),
        (
            "selected_constructed_endpoint",
            constructed_endpoint_support,
            constructed_endpoint_identity,
        ),
        (
            "selected_constructed_single_flow_obstruction",
            constructed_single_flow_support,
            constructed_single_flow_identity,
        ),
        (
            "single_flow_selected_chart_realization",
            selected_chart_support,
            selected_chart_identity,
        ),
        (
            "single_flow_julia_selected_branch_transport_inference",
            julia_assembly_support,
            julia_assembly_identity,
        ),
        (
            "single_polynomial_flow_inference",
            single_flow_analytic_obstruction_support,
            single_flow_analytic_obstruction_identity,
        ),
        (
            "two_flow_finite_julia_valuation_classification",
            finite_julia_classification_support,
            finite_julia_classification_identity,
        ),
        (
            "two_flow_ramified_cross_carrier_abel_assembly",
            two_flow_abel_assembly_support,
            two_flow_abel_assembly_identity,
        ),
        (
            "two_flow_critical_abel_carrier_exclusion",
            critical_two_julia_exclusion_support,
            critical_two_julia_exclusion_identity,
        ),
        (
            "critical_monodromy_multiplier_non_torsion",
            monodromy_non_torsion_support,
            monodromy_non_torsion_identity,
        ),
        (
            "critical_residue_polynomial_root_irrationality",
            critical_residue_irrationality_support,
            critical_residue_irrationality_identity,
        ),
        (
            "critical_rational_differential_infinite_monodromy_inference",
            critical_monodromy_binding_support,
            critical_monodromy_binding_identity,
        ),
        (
            "critical_connection_rational_differential_identification",
            critical_connection_rationalization_support,
            critical_connection_rationalization_identity,
        ),
        (
            "critical_scalar_holonomy_infinite_monodromy_inference",
            critical_holonomy_loop_support,
            critical_holonomy_loop_identity,
        ),
        (
            "two_flow_coupled_julia_elimination",
            coupled_julia_elimination_support,
            coupled_julia_elimination_identity,
        ),
        (
            "two_flow_finite_state_analytic_trajectory",
            finite_state_trajectory_support,
            finite_state_trajectory_identity,
        ),
        (
            "two_flow_coupled_julia_differential_prolongation",
            coupled_julia_differential_support,
            coupled_julia_differential_identity,
        ),
        (
            "two_flow_polynomial_vector_field_multiplicity",
            vector_field_multiplicity_support,
            vector_field_multiplicity_identity,
        ),
        (
            "two_flow_polynomial_vector_field_triangular_prolongation",
            triangular_prolongation_support,
            triangular_prolongation_identity,
        ),
        (
            "two_flow_polynomial_vector_field_finite_prolongation_escape",
            finite_prolongation_escape_support,
            finite_prolongation_escape_identity,
        ),
        (
            "two_flow_differential_polynomial_invariant_specialization",
            differential_invariant_specialization_support,
            differential_invariant_specialization_identity,
        ),
        (
            "two_flow_derivation_iterated_leibniz",
            derivation_iterated_leibniz_support,
            derivation_iterated_leibniz_identity,
        ),
        (
            "two_flow_actual_prolongation_specialization_inference",
            coupled_julia_all_order_specialization_support,
            coupled_julia_all_order_specialization_identity,
        ),
        (
            "two_flow_analytic_kummer_lift_classification",
            analytic_kummer_lift_support,
            analytic_kummer_lift_identity,
        ),
        (
            "two_flow_analytic_algebraic_branch_boundary_trichotomy",
            analytic_algebraic_branch_boundary_support,
            analytic_algebraic_branch_boundary_identity,
        ),
        (
            "two_flow_separated_polynomial_branch_valuation",
            separated_branch_valuation_support,
            separated_branch_valuation_identity,
        ),
        (
            "two_flow_separated_analytic_branch_assembly",
            separated_analytic_branch_assembly_support,
            separated_analytic_branch_assembly_identity,
        ),
        (
            "two_flow_finite_endpoint_ode_continuation",
            finite_endpoint_ode_continuation_support,
            finite_endpoint_ode_continuation_identity,
        ),
        (
            "two_flow_bounded_derivative_endpoint_limit",
            bounded_derivative_endpoint_support,
            bounded_derivative_endpoint_identity,
        ),
        (
            "two_flow_bounded_controlled_polynomial_endpoint_limit",
            bounded_controlled_polynomial_endpoint_support,
            bounded_controlled_polynomial_endpoint_identity,
        ),
        (
            "two_flow_norm_escape_reciprocal_endpoint_limit",
            norm_escape_reciprocal_limit_support,
            norm_escape_reciprocal_limit_identity,
        ),
        (
            "two_flow_uniform_restart_endpoint_escape_alternative",
            uniform_restart_endpoint_escape_support,
            uniform_restart_endpoint_escape_identity,
        ),
        (
            "two_flow_controlled_polynomial_uniform_restart",
            controlled_polynomial_uniform_restart_support,
            controlled_polynomial_uniform_restart_identity,
        ),
        (
            "two_flow_controlled_polynomial_overlap_uniqueness",
            controlled_polynomial_overlap_uniqueness_support,
            controlled_polynomial_overlap_uniqueness_identity,
        ),
        (
            "two_flow_controlled_polynomial_maximal_trajectory",
            controlled_polynomial_maximal_trajectory_support,
            controlled_polynomial_maximal_trajectory_identity,
        ),
        *germ_support_rows,
    )
    selected_germ = _semantic_identity(
        role="selected_algebraic_germ_expansion",
        statement=(
            "On the selected branch u=x+2 at x=-2, the inverse radial "
            "holonomy has nonzero regular coefficient and first nonintegral "
            "term (1120*sqrt(6)/34347)*u^(5/2)."
        ),
        evidence_sha256s=(adapter_sha256, script_sha256),
    )
    two_flow_proportional_reduction = _semantic_identity(
        role="two_flow_proportional_autonomous_reduction",
        statement=(
            "If the two normalized polynomial generators are equal, hence "
            "the original generators are proportional, the composition of "
            "their time-one autonomous flows is a single polynomial "
            "autonomous flow."
        ),
        evidence_sha256s=(
            adapter_sha256,
            str(two_flow["proof_contract_sha256"]),
        ),
    )
    single_flow_statement = _semantic_identity(
        role="single_polynomial_flow_obstruction",
        statement=(
            "The selected critical inverse radial holonomy is not the "
            "time-one germ of a polynomial autonomous generator."
        ),
        evidence_sha256s=(single_digest,),
    )
    single_flow_julia_transport = _semantic_identity(
        role="single_flow_julia_selected_branch_transport",
        statement=(
            "Analytic continuation and translation along the selected "
            "finite branch carry the universal Julia identity to the exact "
            "shifted power-series equality at input center -2 and the "
            "selected nonzero output center."
        ),
        evidence_sha256s=(single_digest,),
    )
    root_statement = _semantic_identity(
        role="critical_two_sided_puiseux_terminal",
        statement=(
            "The selected critical inverse radial holonomy is neither one "
            "polynomial autonomous flow nor a composition of two polynomial "
            "autonomous flows tangent to the identity."
        ),
        evidence_sha256s=(single_digest, two_flow_digest),
    )
    terminal_inference = _semantic_identity(
        role="critical_puiseux_terminal_inference",
        statement=(
            "The selected germ expansion, nonzero-coefficient arithmetic, "
            "Julia identity, and exhaustive two-flow alternative imply the "
            "critical two-sided terminal exclusion."
        ),
        evidence_sha256s=(single_digest, two_flow_digest),
    )
    two_flow_selected_route_evidence = _semantic_identity(
        role="two_flow_selected_route_evidence_exhaustion",
        statement=(
            "Every selected factorization of the critical holonomy by two "
            "complex polynomial autonomous flows constructs compatible route "
            "evidence for exactly the endpoint-eliminant, dominant "
            "equilibrium-boundary, nonfinite ramified-cross, or proportional "
            "branch. A dominant component is normalized and routed rather "
            "than promoted to an endpoint eliminant."
        ),
        evidence_sha256s=(
            adapter_sha256,
            str(two_flow["proof_contract_sha256"]),
            EXPECTED_PROJECTION_FALLACY_SHA256,
        ),
    )
    two_flow_selected_route_evidence_inference = _semantic_identity(
        role="two_flow_selected_route_evidence_exhaustion_inference",
        statement=(
            "The actual prolongation dichotomy, compatible selected "
            "factor-continuation carrier, and normalization of every dominant "
            "component imply exhaustive selected route evidence."
        ),
        evidence_sha256s=(
            adapter_sha256,
            str(two_flow["proof_contract_sha256"]),
            EXPECTED_PROJECTION_FALLACY_SHA256,
        ),
    )
    two_flow_selected_dominant_component_routing = _semantic_identity(
        role="two_flow_selected_dominant_component_normalization_and_routing",
        statement=(
            "Every dominant irreducible component of the selected saturated "
            "coupled differential ideal admits a finite ramified "
            "normalization over F=0. The lifted scalar action is a Kummer "
            "multiplier, and its selected boundary is routed compatibly to "
            "the equilibrium, infinity-cross, or proportional carrier, "
            "including overlap with the original factor branches."
        ),
        evidence_sha256s=(
            adapter_sha256,
            EXPECTED_PROJECTION_FALLACY_SHA256,
            analytic_kummer_lift_identity.identity_sha256,
            separated_branch_valuation_identity.identity_sha256,
            analytic_algebraic_branch_boundary_identity.identity_sha256,
            separated_analytic_branch_assembly_identity.identity_sha256,
        ),
    )
    two_flow_selected_dominant_component_routing_inference = (
        _semantic_identity(
            role=(
                "two_flow_selected_dominant_component_"
                "normalization_and_routing_inference"
            ),
            statement=(
                "A finite normalized dominant-component carrier with a "
                "selected raw separated analytic branch, lifted "
                "power-equivariant scalar action, and compatible factor "
                "overlap, together with governed raw-branch assembly, "
                "analytic Kummer, and algebraic-boundary theorems, implies "
                "the normalized "
                "Kummer action and the exhaustive constant-equilibrium, "
                "finite multiplicity, or pole-degree route."
            ),
            evidence_sha256s=(
                adapter_sha256,
                EXPECTED_PROJECTION_FALLACY_SHA256,
                analytic_kummer_lift_identity.identity_sha256,
                separated_branch_valuation_identity.identity_sha256,
                analytic_algebraic_branch_boundary_identity.identity_sha256,
                separated_analytic_branch_assembly_identity.identity_sha256,
            ),
        )
    )
    two_flow_selected_dominant_component_carrier = _semantic_identity(
        role=(
            "two_flow_selected_dominant_component_normalization_"
            "lift_and_relation_carrier"
        ),
        statement=(
            "Every selected dominant component admits a finite ramified "
            "normalization over F=0, a local analytic automorphism lifting "
            "the scalar monodromy and satisfying the exact power identity, "
            "a selected single-valued punctured analytic branch satisfying "
            "the exact raw separated relation, and overlap with the original "
            "selected factor branches."
        ),
        evidence_sha256s=(
            adapter_sha256,
            EXPECTED_PROJECTION_FALLACY_SHA256,
        ),
    )
    two_flow_selected_nonfinite_cross_carrier = _semantic_identity(
        role="two_flow_selected_nonfinite_cross_carrier_realization",
        statement=(
            "Every selected nonfinite branch of an arbitrary critical "
            "two-polynomial-flow factorization constructs a centered "
            "TwoFlowRamifiedCrossCarrier with the selected source, endpoint, "
            "inner Julia row, and endpoint derivative bindings."
        ),
        evidence_sha256s=(adapter_sha256, two_flow_digest),
    )
    two_flow_nonfinite_cross_exclusion = _semantic_identity(
        role="two_flow_nonfinite_cross_carrier_exclusion",
        statement=(
            "Selected critical bindings, governed Abel-carrier assembly, and "
            "the governed intrinsic two-Julia contradiction exclude every "
            "nonfinite ramified-cross branch."
        ),
        evidence_sha256s=(adapter_sha256, two_flow_digest),
    )
    two_flow_nonfinite_cross_exclusion_inference = _semantic_identity(
        role="two_flow_nonfinite_cross_carrier_exclusion_inference",
        statement=(
            "Selected cross-carrier realization, governed Abel assembly, and "
            "the governed critical carrier contradiction imply exclusion of "
            "the nonfinite branch."
        ),
        evidence_sha256s=(adapter_sha256, two_flow_digest),
    )
    critical_rational_differential_monodromy = _semantic_identity(
        role="critical_rational_differential_infinite_monodromy",
        statement=(
            "The explicit rational differential N(t) / ((t-1)Q(t)) has a "
            "noncancelling real pole with irrational residue and an "
            "infinite-order exponential monodromy multiplier."
        ),
        evidence_sha256s=(
            str(monodromy_residue["certificate_sha256"]),
            monodromy_script_sha256,
        ),
    )
    critical_infinite_monodromy = _semantic_identity(
        role="critical_scalar_holonomy_infinite_monodromy",
        statement=(
            "Identification of the original critical connection with the "
            "governed rational differential transfers its infinite-order "
            "scalar monodromy to an infinite orbit of critical endpoint values."
        ),
        evidence_sha256s=(
            str(monodromy_residue["certificate_sha256"]),
            monodromy_non_torsion_identity.identity_sha256,
        ),
    )
    two_flow_selected_factorization_continuation = _semantic_identity(
        role="two_flow_selected_factorization_continuation_carrier",
        statement=(
            "A selected maximal-path/escape carrier and the governed finite-"
            "endpoint ODE continuation theorem construct compatible inner "
            "and outer analytic continuations along every iterate of the "
            "governed scalar loop, retaining both Julia rows and the visible "
            "logarithmic differential equation wherever the hidden branch "
            "remains finite."
        ),
        evidence_sha256s=(
            adapter_sha256,
            two_flow_digest,
            finite_endpoint_ode_continuation_identity.identity_sha256,
            bounded_derivative_endpoint_identity.identity_sha256,
        ),
    )
    two_flow_selected_factorization_continuation_inference = (
        _semantic_identity(
            role=(
                "two_flow_selected_factorization_"
                "continuation_carrier_inference"
            ),
            statement=(
                "Maximal selected-path construction with the exact finite-"
                "limit versus reciprocal-infinity alternative, together "
                "with governed finite-endpoint ODE continuation, implies the "
                "selected factorization continuation carrier."
            ),
            evidence_sha256s=(
                adapter_sha256,
                two_flow_digest,
                finite_endpoint_ode_continuation_identity.identity_sha256,
                bounded_derivative_endpoint_identity.identity_sha256,
            ),
        )
    )
    two_flow_selected_factorization_maximal_path_escape = _semantic_identity(
        role=(
            "two_flow_selected_factorization_"
            "maximal_path_or_escape_carrier"
        ),
        statement=(
            "A selected maximal lift with a bounded-speed versus reciprocal-"
            "infinity alternative, together with governed endpoint "
            "compactness, produces either a finite state limit or a "
            "compatible reciprocal-infinity escape chart at every finite-"
            "time obstruction."
        ),
        evidence_sha256s=(
            adapter_sha256,
            two_flow_digest,
            bounded_derivative_endpoint_identity.identity_sha256,
        ),
    )
    two_flow_selected_factorization_maximal_path_escape_inference = (
        _semantic_identity(
            role=(
                "two_flow_selected_factorization_"
                "maximal_path_or_escape_carrier_inference"
            ),
            statement=(
                "Maximal selected-path construction with the exact bounded-"
                "speed versus reciprocal-infinity alternative, together "
                "with governed bounded-derivative endpoint compactness, "
                "implies the finite-limit versus reciprocal-infinity "
                "maximal-path carrier."
            ),
            evidence_sha256s=(
                adapter_sha256,
                two_flow_digest,
                bounded_derivative_endpoint_identity.identity_sha256,
            ),
        )
    )
    two_flow_selected_factorization_maximal_lift_speed_escape = (
        _semantic_identity(
            role=(
                "two_flow_selected_factorization_maximal_lift_"
                "bounded_speed_or_reciprocal_escape_carrier"
            ),
            statement=(
                "A selected maximal lift with a bounded-state versus "
                "reciprocal-infinity alternative, together with governed "
                "controlled-polynomial endpoint compactness, produces "
                "either a uniform derivative bound on a terminal interval "
                "or a compatible reciprocal-infinity escape chart."
            ),
            evidence_sha256s=(
                adapter_sha256,
                two_flow_digest,
                bounded_controlled_polynomial_endpoint_identity.identity_sha256,
            ),
        )
    )
    two_flow_selected_factorization_maximal_lift_speed_escape_inference = (
        _semantic_identity(
            role=(
                "two_flow_selected_factorization_maximal_lift_"
                "bounded_speed_or_reciprocal_escape_carrier_inference"
            ),
            statement=(
                "Maximal selected-path construction with a uniformly bounded "
                "loop driver and the exact bounded-state versus reciprocal-"
                "infinity alternative, together with governed controlled-"
                "polynomial endpoint compactness, implies the bounded-speed "
                "versus reciprocal-infinity maximal-lift carrier."
            ),
            evidence_sha256s=(
                adapter_sha256,
                two_flow_digest,
                bounded_controlled_polynomial_endpoint_identity.identity_sha256,
            ),
        )
    )
    two_flow_selected_factorization_maximal_lift_state_escape = (
        _semantic_identity(
            role=(
                "two_flow_selected_factorization_maximal_lift_"
                "bounded_state_or_reciprocal_escape_carrier"
            ),
            statement=(
                "A selected maximal lift with the exact bounded-state versus "
                "norm-escape alternative and the selected algebraic "
                "reciprocal-germ upgrade, together with the governed "
                "norm-escape reciprocal endpoint theorem, produces either a "
                "uniform state bound on a terminal interval or a compatible "
                "reciprocal-infinity escape chart."
            ),
            evidence_sha256s=(
                adapter_sha256,
                two_flow_digest,
                norm_escape_reciprocal_limit_identity.identity_sha256,
            ),
        )
    )
    two_flow_selected_factorization_maximal_lift_state_escape_inference = (
        _semantic_identity(
            role=(
                "two_flow_selected_factorization_maximal_lift_"
                "bounded_state_or_reciprocal_escape_carrier_inference"
            ),
            statement=(
                "The maximal-lift bounded-state versus norm-escape carrier, "
                "the selected algebraic reciprocal-germ upgrade, and the "
                "governed norm-escape chart change imply the exact bounded-"
                "state versus compatible reciprocal-infinity carrier."
            ),
            evidence_sha256s=(
                adapter_sha256,
                two_flow_digest,
                norm_escape_reciprocal_limit_identity.identity_sha256,
            ),
        )
    )
    two_flow_selected_factorization_maximal_lift_state_norm_escape = (
        _semantic_identity(
            role=(
                "two_flow_selected_factorization_maximal_lift_"
                "bounded_state_or_norm_escape_carrier"
            ),
            statement=(
                "A selected maximal lift realized as a restriction-stable, "
                "locally unique, uniformly restartable trajectory with no "
                "finite endpoint extension, together with the governed "
                "uniform-restart endpoint theorem, produces norm escape at "
                "every finite-time obstruction; the complementary bounded "
                "terminal state case is retained explicitly."
            ),
            evidence_sha256s=(
                adapter_sha256,
                two_flow_digest,
                uniform_restart_endpoint_escape_identity.identity_sha256,
            ),
        )
    )
    two_flow_selected_factorization_maximal_lift_state_norm_escape_inference = (
        _semantic_identity(
            role=(
                "two_flow_selected_factorization_maximal_lift_"
                "bounded_state_or_norm_escape_carrier_inference"
            ),
            statement=(
                "The selected uniformly restartable maximal-lift carrier and "
                "the governed endpoint escape alternative imply bounded "
                "terminal state or norm convergence to infinity."
            ),
            evidence_sha256s=(
                adapter_sha256,
                two_flow_digest,
                uniform_restart_endpoint_escape_identity.identity_sha256,
            ),
        )
    )
    two_flow_selected_uniform_restart_maximal_lift = (
        _semantic_identity(
            role=(
                "two_flow_selected_uniformly_restartable_"
                "maximal_lift_carrier"
            ),
            statement=(
                "Every selected two-flow factor germ constructs along each "
                "compact critical loop iterate a maximal controlled-"
                "polynomial lift whose solution predicate restricts, is "
                "locally unique on open preconnected overlaps, has restart "
                "time uniform on each bounded state ball, admits no finite "
                "endpoint extension, and retains the bounded loop driver and "
                "endpoint derivative bindings."
            ),
            evidence_sha256s=(
                adapter_sha256,
                two_flow_digest,
                controlled_polynomial_uniform_restart_identity.identity_sha256,
            ),
        )
    )
    two_flow_selected_uniform_restart_maximal_lift_inference = (
        _semantic_identity(
            role=(
                "two_flow_selected_uniformly_restartable_"
                "maximal_lift_carrier_inference"
            ),
            statement=(
                "The selected maximal controlled-polynomial lift with a "
                "globally continuous bounded loop driver and local overlap "
                "uniqueness, together with the governed bounded-state "
                "uniform-restart theorem, constructs the uniformly "
                "restartable maximal-lift carrier."
            ),
            evidence_sha256s=(
                adapter_sha256,
                two_flow_digest,
                controlled_polynomial_uniform_restart_identity.identity_sha256,
            ),
        )
    )
    two_flow_selected_maximal_lift_driver_uniqueness = (
        _semantic_identity(
            role=(
                "two_flow_selected_maximal_lift_bounded_driver_"
                "local_uniqueness_carrier"
            ),
            statement=(
                "Every selected two-flow factor germ constructs along each "
                "compact critical loop iterate a maximal controlled-"
                "polynomial lift whose solution predicate restricts and is "
                "locally unique on open preconnected overlaps, whose loop "
                "driver is globally continuous and bounded in the real path "
                "parameter, which admits no finite endpoint extension, and "
                "which retains the endpoint derivative bindings."
            ),
            evidence_sha256s=(
                adapter_sha256,
                two_flow_digest,
                controlled_polynomial_overlap_uniqueness_identity.identity_sha256,
            ),
        )
    )
    two_flow_selected_maximal_lift_driver_uniqueness_inference = (
        _semantic_identity(
            role=(
                "two_flow_selected_maximal_lift_bounded_driver_"
                "local_uniqueness_carrier_inference"
            ),
            statement=(
                "The selected maximal controlled-polynomial lift with a "
                "globally bounded loop driver, exact ODE bindings, and no "
                "finite endpoint extension, together with the governed "
                "complete overlap-uniqueness theorem, constructs the "
                "restriction-stable locally unique solution carrier."
            ),
            evidence_sha256s=(
                adapter_sha256,
                two_flow_digest,
                controlled_polynomial_overlap_uniqueness_identity.identity_sha256,
            ),
        )
    )
    two_flow_selected_maximal_lift_driver = _semantic_identity(
        role="two_flow_selected_maximal_lift_bounded_driver_carrier",
        statement=(
            "Every selected two-flow factor germ constructs along each "
            "compact critical loop iterate a maximal controlled-polynomial "
            "lift whose loop driver is globally continuous and bounded in "
            "the real path parameter, which admits no finite endpoint "
            "extension, and which retains the exact ODE and endpoint "
            "derivative bindings."
        ),
        evidence_sha256s=(
            adapter_sha256,
            two_flow_digest,
            controlled_polynomial_maximal_trajectory_identity.identity_sha256,
        ),
    )
    two_flow_selected_maximal_lift_driver_inference = _semantic_identity(
        role=(
            "two_flow_selected_maximal_lift_bounded_driver_"
            "carrier_inference"
        ),
        statement=(
            "Selected factor-loop polynomial, bounded-driver, anchor, and "
            "initial-state data, together with the governed canonical "
            "maximal controlled-polynomial trajectory, selected-branch "
            "identification, and finite-endpoint gluing, construct the "
            "maximal selected lift with exact nonextension and endpoint "
            "bindings."
        ),
        evidence_sha256s=(
            adapter_sha256,
            two_flow_digest,
            controlled_polynomial_maximal_trajectory_identity.identity_sha256,
        ),
    )
    two_flow_selected_factor_loop_driver_endpoint_adapter = _semantic_identity(
        role=(
            "two_flow_selected_factor_loop_driver_initial_data_"
            "and_endpoint_gluing_carrier"
        ),
        statement=(
            "Every selected two-flow factor germ constructs the exact "
            "controlled polynomial, globally continuous bounded loop "
            "driver, anchor, and initial state; identifies the governed "
            "canonical maximal trajectory with the selected branch along "
            "every critical-loop iterate; converts any finite endpoint "
            "extension into a larger anchor-based candidate; and retains "
            "the endpoint derivative bindings."
        ),
        evidence_sha256s=(adapter_sha256, two_flow_digest),
    )
    two_flow_selected_norm_escape_reciprocal_germ_upgrade = (
        _semantic_identity(
            role=(
                "two_flow_selected_norm_escape_"
                "holomorphic_reciprocal_germ_upgrade"
            ),
            statement=(
                "For the selected algebraic continuation, pathwise norm "
                "escape and its reciprocal zero limit construct a "
                "holomorphic reciprocal germ at the endpoint, nonzero on a "
                "punctured neighborhood and compatible with the selected "
                "infinity sheet."
            ),
            evidence_sha256s=(adapter_sha256, two_flow_digest),
        )
    )
    two_flow_loop_continuation_transfer = _semantic_identity(
        role="two_flow_factorization_loop_continuation_transfer",
        statement=(
            "The selected continuation carrier and division-free coupled "
            "Julia kernel make every finite lifted hidden endpoint a root of "
            "q(F)p(Y)-A(x)F p(x)q(Y) along every critical loop iterate."
        ),
        evidence_sha256s=(
            adapter_sha256,
            two_flow_digest,
            EXPECTED_FINITE_MONODROMY_COUNTERMODELS_SHA256,
        ),
    )
    two_flow_actual_normalized_relation_hypotheses = _semantic_identity(
        role="two_flow_actual_normalized_relation_hypotheses",
        statement=(
            "The selected critical factorization embeds in a differential "
            "coefficient field where the outer generator has vanishing "
            "constant and linear coefficients, both generator coefficient "
            "sets are derivation-constant, and the source scalar binding is "
            "a0=A(x)p(x)."
        ),
        evidence_sha256s=(
            adapter_sha256,
            coupled_julia_differential_identity.identity_sha256,
        ),
    )
    two_flow_actual_prolongation_specialization = _semantic_identity(
        role="two_flow_actual_prolongation_specialization",
        statement=(
            "The concrete normalized coupled-Julia relation and the governed "
            "all-order specialization theorem identify every actual "
            "prolongation on F=0 with the governed triangular family after "
            "constructing the quadratic tangent tail and visible factor."
        ),
        evidence_sha256s=(
            adapter_sha256,
            coupled_julia_all_order_specialization_identity.identity_sha256,
        ),
    )
    two_flow_actual_prolongation_dichotomy = _semantic_identity(
        role="two_flow_actual_prolongation_eliminant_or_dominant_component",
        statement=(
            "Actual total-prolongation specialization, finite-state analytic "
            "uniqueness, and the governed multiplicity-triangular escape "
            "kernel imply the correct algebraic alternative: either the "
            "saturated differential ideal contains a nonzero endpoint "
            "eliminant, or an irreducible component dominates the F-line. A "
            "dominant component has no finite regular point over F=0; its "
            "boundary lies in p(Y)=0 or at hidden infinity."
        ),
        evidence_sha256s=(
            adapter_sha256,
            finite_state_trajectory_identity.identity_sha256,
            vector_field_multiplicity_identity.identity_sha256,
            triangular_prolongation_identity.identity_sha256,
            finite_prolongation_escape_identity.identity_sha256,
        ),
    )
    two_flow_actual_prolongation_dichotomy_inference = (
        _semantic_identity(
            role=(
                "two_flow_actual_prolongation_"
                "eliminant_or_dominant_component_inference"
            ),
            statement=(
                "The actual normalized prolongation-specialization theorem and "
                "the governed analytic, differential, multiplicity, "
                "triangular, and finite-escape kernels imply the endpoint-"
                "eliminant versus dominant-component alternative without the "
                "invalid empty-fiber projection step."
            ),
            evidence_sha256s=(
                adapter_sha256,
                coupled_julia_differential_identity.identity_sha256,
                finite_prolongation_escape_identity.identity_sha256,
            ),
        )
    )
    two_flow_finite_coupled_exclusion = _semantic_identity(
        role="two_flow_finite_coupled_monodromy_exclusion",
        statement=(
            "A selected branch assigned a nonzero endpoint eliminant is "
            "incompatible with the non-torsion critical scalar endpoint orbit. "
            "Finite Julia valuation classification prevents a mixed regular-"
            "equilibrium interpretation; dominant Lambert-type and boundary "
            "components belong to the separate normalization route."
        ),
        evidence_sha256s=(
            adapter_sha256,
            EXPECTED_EQUILIBRIUM_TRANSITION_SHA256,
            str(monodromy_residue["certificate_sha256"]),
        ),
    )
    two_flow_finite_coupled_exclusion_inference = _semantic_identity(
        role="two_flow_finite_coupled_monodromy_exclusion_inference",
        statement=(
            "For the endpoint-eliminant alternative, finite Julia "
            "classification, the infinite critical endpoint orbit, and the "
            "coupled factor-continuation identity exclude the selected lifted "
            "branch."
        ),
        evidence_sha256s=(
            adapter_sha256,
            EXPECTED_EQUILIBRIUM_TRANSITION_SHA256,
            str(monodromy_residue["certificate_sha256"]),
        ),
    )
    two_flow_global_exclusion = _semantic_identity(
        role="two_polynomial_flow_factorization_excluded",
        statement=(
            "Exhaustive selected-route evidence, the nonfinite cross-carrier "
            "contradiction, exclusion of finite coupled monodromy, and "
            "the proportional one-flow reduction exclude every composition "
            "of two complex polynomial autonomous flows."
        ),
        evidence_sha256s=(single_digest, two_flow_digest),
    )
    two_flow_global_exclusion_inference = _semantic_identity(
        role="two_polynomial_flow_factorization_exclusion_inference",
        statement=(
            "The route-exhaustion, nonfinite, finite-coupled, and "
            "proportional branch certificates jointly imply the arbitrary "
            "two-flow exclusion."
        ),
        evidence_sha256s=(single_digest, two_flow_digest),
    )
    semantic = FormalPropositionIdentityKind.ADAPTER_SEMANTIC
    lean = FormalPropositionIdentityKind.GOVERNED_LEAN_PROPOSITION
    # v53 retains the v41 projection correction and the governed local
    # normalization/boundary kernels, then isolates maximal selected-path
    # construction and its bounded-state/escape alternative from governed
    # polynomial speed bounds, endpoint compactness, finite-limit
    # continuation, and pathwise reciprocal chart change. The remaining
    # escape obligation is split between construction of a uniformly
    # restartable maximal lift and holomorphic germ upgrade.
    # A saturated
    # family can have an empty regular fiber at F=0 and still project densely.
    # The active DAG therefore requires an eliminant-or-dominant-component
    # dichotomy followed by normalization and routing of the dominant branch.
    decomposition = make_formal_claim_decomposition(
        name="axiompack-jacobian-critical-puiseux-terminal-v53",
        root_node_id="critical_terminal_excluded",
        nodes=(
            FormalClaimNode(
                node_id="critical_terminal_excluded",
                proposition_sha256=root_statement,
                identity_kind=semantic,
                children=(
                    "selected_algebraic_germ_expansion",
                    "single_polynomial_flow_obstruction",
                    "two_polynomial_flow_factorization_excluded",
                ),
                inference_proposition_sha256=terminal_inference,
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id="selected_algebraic_germ_expansion",
                proposition_sha256=selected_germ,
                identity_kind=semantic,
                children=(
                    "discriminant_factorization",
                    "radical_numerator_simple_zero",
                    "radical_denominator_at_branch_nonzero",
                    "radical_simple_zero_scale_exact",
                    "selected_algebraic_germ_series_passage",
                ),
                inference_proposition_sha256=(
                    selected_germ_formal_inference.identity_sha256
                ),
                inference_identity_kind=lean,
                inference_lean_identity=selected_germ_formal_inference,
            ),
            *tuple(
                FormalClaimNode(
                    node_id=role,
                    proposition_sha256=identity.identity_sha256,
                    identity_kind=lean,
                    lean_identity=identity,
                )
                for role, identity in sorted(germ_identities.items())
            ),
            FormalClaimNode(
                node_id="selected_algebraic_germ_series_passage",
                proposition_sha256=series_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=series_identity,
            ),
            FormalClaimNode(
                node_id="critical_arithmetic",
                proposition_sha256=arithmetic_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=arithmetic_identity,
            ),
            FormalClaimNode(
                node_id="coefficient_cancellation_mechanism",
                proposition_sha256=coefficient_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=coefficient_identity,
            ),
            FormalClaimNode(
                node_id="julia_formal_flow_identity",
                proposition_sha256=julia_formal_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=julia_formal_identity,
            ),
            FormalClaimNode(
                node_id="single_polynomial_flow_obstruction",
                proposition_sha256=single_flow_statement,
                identity_kind=semantic,
                children=(
                    "selected_algebraic_germ_expansion",
                    "critical_arithmetic",
                    "coefficient_cancellation_mechanism",
                    "julia_formal_flow_identity",
                    "single_flow_julia_selected_branch_transport",
                    "single_flow_ramified_root_factor_obstruction",
                    "normalized_formal_linear_ode_constructor",
                    "selected_constructed_endpoint",
                    "selected_constructed_single_flow_obstruction",
                ),
                inference_proposition_sha256=(
                    single_flow_analytic_obstruction_identity.identity_sha256
                ),
                inference_identity_kind=lean,
                inference_lean_identity=(
                    single_flow_analytic_obstruction_identity
                ),
            ),
            FormalClaimNode(
                node_id="single_flow_julia_selected_branch_transport",
                proposition_sha256=single_flow_julia_transport,
                identity_kind=semantic,
                children=(
                    "single_flow_selected_chart_realization",
                    "analytic_continuation_julia_transport",
                    "analytic_germ_to_powerSeries_transport",
                ),
                inference_proposition_sha256=(
                    julia_assembly_identity.identity_sha256
                ),
                inference_identity_kind=lean,
                inference_lean_identity=julia_assembly_identity,
            ),
            FormalClaimNode(
                node_id="single_flow_selected_chart_realization",
                proposition_sha256=selected_chart_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=selected_chart_identity,
            ),
            FormalClaimNode(
                node_id="analytic_continuation_julia_transport",
                proposition_sha256=analytic_continuation_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=analytic_continuation_identity,
            ),
            FormalClaimNode(
                node_id="analytic_germ_to_powerSeries_transport",
                proposition_sha256=analytic_taylor_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=analytic_taylor_identity,
            ),
            FormalClaimNode(
                node_id="single_flow_ramified_root_factor_obstruction",
                proposition_sha256=(
                    single_flow_obstruction_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=single_flow_obstruction_identity,
            ),
            FormalClaimNode(
                node_id="normalized_formal_linear_ode_constructor",
                proposition_sha256=formal_linear_ode_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=formal_linear_ode_identity,
            ),
            FormalClaimNode(
                node_id="selected_constructed_endpoint",
                proposition_sha256=constructed_endpoint_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=constructed_endpoint_identity,
            ),
            FormalClaimNode(
                node_id="selected_constructed_single_flow_obstruction",
                proposition_sha256=(
                    constructed_single_flow_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=constructed_single_flow_identity,
            ),
            FormalClaimNode(
                node_id="two_polynomial_flow_factorization_excluded",
                proposition_sha256=two_flow_global_exclusion,
                identity_kind=semantic,
                children=(
                    "two_flow_selected_route_evidence_exhaustion",
                    "two_flow_nonfinite_cross_carrier_exclusion",
                    "two_flow_finite_coupled_monodromy_exclusion",
                    "two_flow_proportional_autonomous_reduction",
                    "two_flow_exponent_interval",
                ),
                inference_proposition_sha256=(
                    two_flow_global_exclusion_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id="two_flow_selected_route_evidence_exhaustion",
                proposition_sha256=two_flow_selected_route_evidence,
                identity_kind=semantic,
                children=(
                    (
                        "two_flow_actual_prolongation_"
                        "eliminant_or_dominant_component"
                    ),
                    (
                        "two_flow_selected_dominant_component_"
                        "normalization_and_routing"
                    ),
                    "two_flow_selected_factorization_continuation_carrier",
                ),
                inference_proposition_sha256=(
                    two_flow_selected_route_evidence_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id="two_flow_nonfinite_cross_carrier_exclusion",
                proposition_sha256=two_flow_nonfinite_cross_exclusion,
                identity_kind=semantic,
                children=(
                    "two_flow_selected_nonfinite_cross_carrier_realization",
                    "two_flow_ramified_cross_carrier_abel_assembly",
                    "two_flow_critical_abel_carrier_exclusion",
                ),
                inference_proposition_sha256=(
                    two_flow_nonfinite_cross_exclusion_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id="two_flow_selected_nonfinite_cross_carrier_realization",
                proposition_sha256=two_flow_selected_nonfinite_cross_carrier,
                identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id="two_flow_ramified_cross_carrier_abel_assembly",
                proposition_sha256=two_flow_abel_assembly_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=two_flow_abel_assembly_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_critical_abel_carrier_exclusion",
                proposition_sha256=(
                    critical_two_julia_exclusion_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=critical_two_julia_exclusion_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_finite_coupled_monodromy_exclusion",
                proposition_sha256=two_flow_finite_coupled_exclusion,
                identity_kind=semantic,
                children=(
                    "two_flow_finite_julia_valuation_classification",
                    "critical_scalar_holonomy_infinite_monodromy",
                    "two_flow_factorization_loop_continuation_transfer",
                ),
                inference_proposition_sha256=(
                    two_flow_finite_coupled_exclusion_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_actual_prolongation_"
                    "eliminant_or_dominant_component"
                ),
                proposition_sha256=(
                    two_flow_actual_prolongation_dichotomy
                ),
                identity_kind=semantic,
                children=(
                    "two_flow_actual_prolongation_specialization",
                    "two_flow_finite_state_analytic_trajectory",
                    "two_flow_coupled_julia_differential_prolongation",
                    "two_flow_polynomial_vector_field_multiplicity",
                    (
                        "two_flow_polynomial_vector_field_"
                        "triangular_prolongation"
                    ),
                    (
                        "two_flow_polynomial_vector_field_"
                        "finite_prolongation_escape"
                    ),
                ),
                inference_proposition_sha256=(
                    two_flow_actual_prolongation_dichotomy_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id="two_flow_actual_prolongation_specialization",
                proposition_sha256=(
                    two_flow_actual_prolongation_specialization
                ),
                identity_kind=semantic,
                children=(
                    (
                        "two_flow_differential_polynomial_"
                        "invariant_specialization"
                    ),
                    "two_flow_derivation_iterated_leibniz",
                    "two_flow_actual_normalized_relation_hypotheses",
                    (
                        "two_flow_polynomial_vector_field_"
                        "triangular_prolongation"
                    ),
                ),
                inference_proposition_sha256=(
                    coupled_julia_all_order_specialization_identity.identity_sha256
                ),
                inference_identity_kind=lean,
                inference_lean_identity=(
                    coupled_julia_all_order_specialization_identity
                ),
            ),
            FormalClaimNode(
                node_id="two_flow_actual_normalized_relation_hypotheses",
                proposition_sha256=(
                    two_flow_actual_normalized_relation_hypotheses
                ),
                identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id="two_flow_derivation_iterated_leibniz",
                proposition_sha256=(
                    derivation_iterated_leibniz_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=derivation_iterated_leibniz_identity,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_differential_polynomial_"
                    "invariant_specialization"
                ),
                proposition_sha256=(
                    differential_invariant_specialization_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=differential_invariant_specialization_identity,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_selected_dominant_component_"
                    "normalization_and_routing"
                ),
                proposition_sha256=(
                    two_flow_selected_dominant_component_routing
                ),
                identity_kind=semantic,
                children=(
                    (
                        "two_flow_selected_dominant_component_"
                        "normalization_lift_and_relation_carrier"
                    ),
                    "two_flow_analytic_kummer_lift_classification",
                    (
                        "two_flow_analytic_algebraic_branch_"
                        "boundary_trichotomy"
                    ),
                    "two_flow_separated_polynomial_branch_valuation",
                    "two_flow_separated_analytic_branch_assembly",
                ),
                inference_proposition_sha256=(
                    two_flow_selected_dominant_component_routing_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_selected_dominant_component_"
                    "normalization_lift_and_relation_carrier"
                ),
                proposition_sha256=(
                    two_flow_selected_dominant_component_carrier
                ),
                identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id="two_flow_analytic_kummer_lift_classification",
                proposition_sha256=(
                    analytic_kummer_lift_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=analytic_kummer_lift_identity,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_analytic_algebraic_branch_"
                    "boundary_trichotomy"
                ),
                proposition_sha256=(
                    analytic_algebraic_branch_boundary_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=analytic_algebraic_branch_boundary_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_separated_polynomial_branch_valuation",
                proposition_sha256=(
                    separated_branch_valuation_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=separated_branch_valuation_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_separated_analytic_branch_assembly",
                proposition_sha256=(
                    separated_analytic_branch_assembly_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=separated_analytic_branch_assembly_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_finite_state_analytic_trajectory",
                proposition_sha256=(
                    finite_state_trajectory_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=finite_state_trajectory_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_finite_endpoint_ode_continuation",
                proposition_sha256=(
                    finite_endpoint_ode_continuation_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=finite_endpoint_ode_continuation_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_coupled_julia_differential_prolongation",
                proposition_sha256=(
                    coupled_julia_differential_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=coupled_julia_differential_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_polynomial_vector_field_multiplicity",
                proposition_sha256=(
                    vector_field_multiplicity_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=vector_field_multiplicity_identity,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_polynomial_vector_field_"
                    "triangular_prolongation"
                ),
                proposition_sha256=(
                    triangular_prolongation_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=triangular_prolongation_identity,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_polynomial_vector_field_"
                    "finite_prolongation_escape"
                ),
                proposition_sha256=(
                    finite_prolongation_escape_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=finite_prolongation_escape_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_finite_julia_valuation_classification",
                proposition_sha256=(
                    finite_julia_classification_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=finite_julia_classification_identity,
            ),
            FormalClaimNode(
                node_id="critical_scalar_holonomy_infinite_monodromy",
                proposition_sha256=critical_infinite_monodromy,
                identity_kind=semantic,
                children=(
                    "critical_connection_rational_differential_identification",
                    "critical_rational_differential_infinite_monodromy",
                ),
                inference_proposition_sha256=(
                    critical_holonomy_loop_identity.identity_sha256
                ),
                inference_identity_kind=lean,
                inference_lean_identity=critical_holonomy_loop_identity,
            ),
            FormalClaimNode(
                node_id=(
                    "critical_connection_rational_differential_identification"
                ),
                proposition_sha256=(
                    critical_connection_rationalization_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=critical_connection_rationalization_identity,
            ),
            FormalClaimNode(
                node_id="critical_rational_differential_infinite_monodromy",
                proposition_sha256=critical_rational_differential_monodromy,
                identity_kind=semantic,
                children=(
                    "critical_residue_polynomial_root_irrationality",
                    "critical_monodromy_multiplier_non_torsion",
                ),
                inference_proposition_sha256=(
                    critical_monodromy_binding_identity.identity_sha256
                ),
                inference_identity_kind=lean,
                inference_lean_identity=(
                    critical_monodromy_binding_identity
                ),
            ),
            FormalClaimNode(
                node_id="critical_residue_polynomial_root_irrationality",
                proposition_sha256=(
                    critical_residue_irrationality_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=critical_residue_irrationality_identity,
            ),
            FormalClaimNode(
                node_id="critical_monodromy_multiplier_non_torsion",
                proposition_sha256=monodromy_non_torsion_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=monodromy_non_torsion_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_factorization_loop_continuation_transfer",
                proposition_sha256=two_flow_loop_continuation_transfer,
                identity_kind=semantic,
                children=(
                    "two_flow_selected_factorization_continuation_carrier",
                ),
                inference_proposition_sha256=(
                    coupled_julia_elimination_identity.identity_sha256
                ),
                inference_identity_kind=lean,
                inference_lean_identity=coupled_julia_elimination_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_selected_factorization_continuation_carrier",
                proposition_sha256=(
                    two_flow_selected_factorization_continuation
                ),
                identity_kind=semantic,
                children=(
                    (
                        "two_flow_selected_factorization_"
                        "maximal_path_or_escape_carrier"
                    ),
                    "two_flow_finite_endpoint_ode_continuation",
                ),
                inference_proposition_sha256=(
                    two_flow_selected_factorization_continuation_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_selected_factorization_"
                    "maximal_path_or_escape_carrier"
                ),
                proposition_sha256=(
                    two_flow_selected_factorization_maximal_path_escape
                ),
                identity_kind=semantic,
                children=(
                    (
                        "two_flow_selected_factorization_maximal_lift_"
                        "bounded_speed_or_reciprocal_escape_carrier"
                    ),
                    "two_flow_bounded_derivative_endpoint_limit",
                ),
                inference_proposition_sha256=(
                    two_flow_selected_factorization_maximal_path_escape_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_selected_factorization_maximal_lift_"
                    "bounded_speed_or_reciprocal_escape_carrier"
                ),
                proposition_sha256=(
                    two_flow_selected_factorization_maximal_lift_speed_escape
                ),
                identity_kind=semantic,
                children=(
                    (
                        "two_flow_selected_factorization_maximal_lift_"
                        "bounded_state_or_reciprocal_escape_carrier"
                    ),
                    (
                        "two_flow_bounded_controlled_polynomial_"
                        "endpoint_limit"
                    ),
                ),
                inference_proposition_sha256=(
                    two_flow_selected_factorization_maximal_lift_speed_escape_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_selected_factorization_maximal_lift_"
                    "bounded_state_or_reciprocal_escape_carrier"
                ),
                proposition_sha256=(
                    two_flow_selected_factorization_maximal_lift_state_escape
                ),
                identity_kind=semantic,
                children=(
                    (
                        "two_flow_selected_factorization_maximal_lift_"
                        "bounded_state_or_norm_escape_carrier"
                    ),
                    (
                        "two_flow_selected_norm_escape_"
                        "holomorphic_reciprocal_germ_upgrade"
                    ),
                    "two_flow_norm_escape_reciprocal_endpoint_limit",
                ),
                inference_proposition_sha256=(
                    two_flow_selected_factorization_maximal_lift_state_escape_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_selected_factorization_maximal_lift_"
                    "bounded_state_or_norm_escape_carrier"
                ),
                proposition_sha256=(
                    two_flow_selected_factorization_maximal_lift_state_norm_escape
                ),
                identity_kind=semantic,
                children=(
                    (
                        "two_flow_selected_uniformly_restartable_"
                        "maximal_lift_carrier"
                    ),
                    "two_flow_uniform_restart_endpoint_escape_alternative",
                ),
                inference_proposition_sha256=(
                    two_flow_selected_factorization_maximal_lift_state_norm_escape_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_selected_uniformly_restartable_"
                    "maximal_lift_carrier"
                ),
                proposition_sha256=(
                    two_flow_selected_uniform_restart_maximal_lift
                ),
                identity_kind=semantic,
                children=(
                    (
                        "two_flow_selected_maximal_lift_bounded_driver_"
                        "local_uniqueness_carrier"
                    ),
                    "two_flow_controlled_polynomial_uniform_restart",
                ),
                inference_proposition_sha256=(
                    two_flow_selected_uniform_restart_maximal_lift_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_selected_maximal_lift_bounded_driver_"
                    "local_uniqueness_carrier"
                ),
                proposition_sha256=(
                    two_flow_selected_maximal_lift_driver_uniqueness
                ),
                identity_kind=semantic,
                children=(
                    (
                        "two_flow_selected_maximal_lift_"
                        "bounded_driver_carrier"
                    ),
                    "two_flow_controlled_polynomial_overlap_uniqueness",
                ),
                inference_proposition_sha256=(
                    two_flow_selected_maximal_lift_driver_uniqueness_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_selected_maximal_lift_"
                    "bounded_driver_carrier"
                ),
                proposition_sha256=two_flow_selected_maximal_lift_driver,
                identity_kind=semantic,
                children=(
                    (
                        "two_flow_selected_factor_loop_driver_initial_data_"
                        "and_endpoint_gluing_carrier"
                    ),
                    "two_flow_controlled_polynomial_maximal_trajectory",
                ),
                inference_proposition_sha256=(
                    two_flow_selected_maximal_lift_driver_inference
                ),
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_selected_factor_loop_driver_initial_data_"
                    "and_endpoint_gluing_carrier"
                ),
                proposition_sha256=(
                    two_flow_selected_factor_loop_driver_endpoint_adapter
                ),
                identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_selected_norm_escape_"
                    "holomorphic_reciprocal_germ_upgrade"
                ),
                proposition_sha256=(
                    two_flow_selected_norm_escape_reciprocal_germ_upgrade
                ),
                identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_bounded_controlled_polynomial_endpoint_limit"
                ),
                proposition_sha256=(
                    bounded_controlled_polynomial_endpoint_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=bounded_controlled_polynomial_endpoint_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_bounded_derivative_endpoint_limit",
                proposition_sha256=(
                    bounded_derivative_endpoint_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=bounded_derivative_endpoint_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_norm_escape_reciprocal_endpoint_limit",
                proposition_sha256=(
                    norm_escape_reciprocal_limit_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=norm_escape_reciprocal_limit_identity,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_uniform_restart_endpoint_escape_alternative"
                ),
                proposition_sha256=(
                    uniform_restart_endpoint_escape_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=uniform_restart_endpoint_escape_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_controlled_polynomial_uniform_restart",
                proposition_sha256=(
                    controlled_polynomial_uniform_restart_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=controlled_polynomial_uniform_restart_identity,
            ),
            FormalClaimNode(
                node_id=(
                    "two_flow_controlled_polynomial_overlap_uniqueness"
                ),
                proposition_sha256=(
                    controlled_polynomial_overlap_uniqueness_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=controlled_polynomial_overlap_uniqueness_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_controlled_polynomial_maximal_trajectory",
                proposition_sha256=(
                    controlled_polynomial_maximal_trajectory_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=controlled_polynomial_maximal_trajectory_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_proportional_autonomous_reduction",
                proposition_sha256=two_flow_proportional_reduction,
                identity_kind=semantic,
                children=(
                    "two_flow_proportional_same_flow_identification",
                    "two_flow_proportional_semigroup_reduction",
                ),
                inference_proposition_sha256=(
                    proportional_reduction_identity.identity_sha256
                ),
                inference_identity_kind=lean,
                inference_lean_identity=proportional_reduction_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_proportional_same_flow_identification",
                proposition_sha256=(
                    proportional_trajectory_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=proportional_trajectory_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_proportional_semigroup_reduction",
                proposition_sha256=(
                    proportional_semigroup_identity.identity_sha256
                ),
                identity_kind=lean,
                lean_identity=proportional_semigroup_identity,
            ),
            FormalClaimNode(
                node_id="two_flow_exponent_interval",
                proposition_sha256=interval_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=interval_identity,
            ),
        ),
        adapter_evidence_sha256=adapter_sha256,
    )
    problem = FormalClaimCoverageProblem(
        decomposition=decomposition,
        supports=tuple(
            support for _role, support, _identity in active_support_rows
        ),
    )
    coverage = compile_formal_claim_coverage(problem)
    assert replay_formal_claim_coverage_certificate(coverage, problem) == (
        coverage
    )
    assert coverage.directly_ratified_node_ids == (
        "analytic_continuation_julia_transport",
        "analytic_germ_to_powerSeries_transport",
        "coefficient_cancellation_mechanism",
        "critical_arithmetic",
        "critical_connection_rational_differential_identification",
        "critical_monodromy_multiplier_non_torsion",
        "critical_residue_polynomial_root_irrationality",
        "discriminant_factorization",
        "julia_formal_flow_identity",
        "normalized_formal_linear_ode_constructor",
        "radical_denominator_at_branch_nonzero",
        "radical_numerator_simple_zero",
        "radical_simple_zero_scale_exact",
        "selected_algebraic_germ_series_passage",
        "selected_constructed_endpoint",
        "selected_constructed_single_flow_obstruction",
        "single_flow_ramified_root_factor_obstruction",
        "single_flow_selected_chart_realization",
        "two_flow_analytic_algebraic_branch_boundary_trichotomy",
        "two_flow_analytic_kummer_lift_classification",
        "two_flow_bounded_controlled_polynomial_endpoint_limit",
        "two_flow_bounded_derivative_endpoint_limit",
        "two_flow_controlled_polynomial_maximal_trajectory",
        "two_flow_controlled_polynomial_overlap_uniqueness",
        "two_flow_controlled_polynomial_uniform_restart",
        "two_flow_coupled_julia_differential_prolongation",
        "two_flow_critical_abel_carrier_exclusion",
        "two_flow_derivation_iterated_leibniz",
        "two_flow_differential_polynomial_invariant_specialization",
        "two_flow_exponent_interval",
        "two_flow_finite_endpoint_ode_continuation",
        "two_flow_finite_julia_valuation_classification",
        "two_flow_finite_state_analytic_trajectory",
        "two_flow_norm_escape_reciprocal_endpoint_limit",
        "two_flow_polynomial_vector_field_finite_prolongation_escape",
        "two_flow_polynomial_vector_field_multiplicity",
        "two_flow_polynomial_vector_field_triangular_prolongation",
        "two_flow_proportional_same_flow_identification",
        "two_flow_proportional_semigroup_reduction",
        "two_flow_ramified_cross_carrier_abel_assembly",
        "two_flow_separated_analytic_branch_assembly",
        "two_flow_separated_polynomial_branch_valuation",
        "two_flow_uniform_restart_endpoint_escape_alternative",
    )
    assert coverage.uncovered_adapter_semantic_leaf_ids == (
        "two_flow_actual_normalized_relation_hypotheses",
        (
            "two_flow_selected_dominant_component_"
            "normalization_lift_and_relation_carrier"
        ),
        (
            "two_flow_selected_factor_loop_driver_initial_data_"
            "and_endpoint_gluing_carrier"
        ),
        "two_flow_selected_nonfinite_cross_carrier_realization",
        (
            "two_flow_selected_norm_escape_"
            "holomorphic_reciprocal_germ_upgrade"
        ),
    )
    assert coverage.uncovered_adapter_semantic_inference_ids == (
        "critical_terminal_excluded",
        "two_flow_actual_prolongation_eliminant_or_dominant_component",
        "two_flow_finite_coupled_monodromy_exclusion",
        "two_flow_nonfinite_cross_carrier_exclusion",
        "two_flow_selected_dominant_component_normalization_and_routing",
        "two_flow_selected_factorization_continuation_carrier",
        (
            "two_flow_selected_factorization_maximal_lift_"
            "bounded_speed_or_reciprocal_escape_carrier"
        ),
        (
            "two_flow_selected_factorization_maximal_lift_"
            "bounded_state_or_norm_escape_carrier"
        ),
        (
            "two_flow_selected_factorization_maximal_lift_"
            "bounded_state_or_reciprocal_escape_carrier"
        ),
        "two_flow_selected_factorization_maximal_path_or_escape_carrier",
        "two_flow_selected_maximal_lift_bounded_driver_carrier",
        (
            "two_flow_selected_maximal_lift_bounded_driver_"
            "local_uniqueness_carrier"
        ),
        "two_flow_selected_route_evidence_exhaustion",
        (
            "two_flow_selected_uniformly_restartable_"
            "maximal_lift_carrier"
        ),
        "two_polynomial_flow_factorization_excluded",
    )
    assert coverage.supported_inference_node_ids == (
        "critical_rational_differential_infinite_monodromy",
        "critical_scalar_holonomy_infinite_monodromy",
        "selected_algebraic_germ_expansion",
        "single_flow_julia_selected_branch_transport",
        "single_polynomial_flow_obstruction",
        "two_flow_actual_prolongation_specialization",
        "two_flow_factorization_loop_continuation_transfer",
        "two_flow_proportional_autonomous_reduction",
    )
    assert coverage.root_authority_promotion_eligible is False
    assert coverage.formal_authority_issued is False

    core: dict[str, object] = {
        "schema": "axiompack.jacobian_critical_puiseux_formal_coverage.v56",
        "existing_semantic_digests": {
            "single_flow": single_digest,
            "two_flow": two_flow_digest,
        },
        "coverage_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v37"
            ),
            "reason": (
                "Exact polynomial-flow countermodels refute the tentative "
                "finite-to-equilibrium loop argument: one flow has two "
                "finite regular sheets and another has Lambert-W finite "
                "regular sheets. The corrected finite route retains the "
                "coupled Julia and derivative-eliminated algebraic identity."
            ),
            "equilibrium_transition_countermodel_sha256": (
                EXPECTED_EQUILIBRIUM_TRANSITION_SHA256
            ),
            "finite_monodromy_countermodels_sha256": (
                EXPECTED_FINITE_MONODROMY_COUNTERMODELS_SHA256
            ),
            "audit_correction": (
                "The governed complex single-flow and complex Julia-transport "
                "supports replace the omitted real-only v32 parents."
            ),
        },
        "kernel_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v38"
            ),
            "reason": (
                "A governed division-free coupled-Julia kernel now constructs "
                "the hidden relation polynomial and proves root membership "
                "from the two Julia rows and visible logarithmic equation. "
                "The factor-loop residual is split at the remaining analytic "
                "continuation carrier."
            ),
        },
        "projection_inversion": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v40"
            ),
            "reason": (
                "Exact Groebner negative controls show that an empty "
                "saturated regular fiber at F=0 does not force a nonzero "
                "endpoint eliminant: a dominant component may project "
                "densely and approach equilibrium or infinity. The finite "
                "route is therefore split into endpoint-eliminant and "
                "dominant-component normalization alternatives."
            ),
            "projection_fallacy_certificate_sha256": (
                EXPECTED_PROJECTION_FALLACY_SHA256
            ),
        },
        "invariant_specialization_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v41"
            ),
            "reason": (
                "A governed total-derivation theorem now proves all-order "
                "specialization along an invariant visible divisor. The "
                "former broad actual-specialization leaf is split into a "
                "concrete normalized-relation leaf and a semantic inference "
                "whose remaining step is the exact iterated-Leibniz bridge."
            ),
            "governed_record_sha256": (
                DIFFERENTIAL_INVARIANT_SPECIALIZATION_RECORD_SHA256
            ),
            "content_bound_receipt_sha256": (
                EXPECTED_DIFFERENTIAL_INVARIANT_SPECIALIZATION_RECEIPT_SHA256
            ),
        },
        "all_order_specialization_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v42"
            ),
            "reason": (
                "A governed iterated-Leibniz kernel and governed concrete "
                "coupled-Julia theorem now construct the tangent tail, exact "
                "visible factor, special fiber, and every triangular "
                "prolongation. Only finite adapter hypotheses remain in the "
                "actual-specialization branch."
            ),
            "governed_record_sha256": (
                COUPLED_JULIA_ALL_ORDER_SPECIALIZATION_RECORD_SHA256
            ),
            "content_bound_receipt_sha256": (
                EXPECTED_COUPLED_JULIA_ALL_ORDER_SPECIALIZATION_RECEIPT_SHA256
            ),
        },
        "dominant_component_kummer_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v43"
            ),
            "reason": (
                "A governed analytic Kummer theorem now proves that every "
                "normalized local automorphism satisfying the lifted power "
                "identity is multiplication by a constructed root. The "
                "dominant-component leaf is narrowed to construction of the "
                "normalization, lifted action, and compatible boundary "
                "carrier."
            ),
            "governed_record_sha256": ANALYTIC_KUMMER_LIFT_RECORD_SHA256,
            "content_bound_receipt_sha256": (
                EXPECTED_ANALYTIC_KUMMER_LIFT_RECEIPT_SHA256
            ),
        },
        "dominant_component_valuation_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v44"
            ),
            "reason": (
                "A governed separated-polynomial valuation theorem derives "
                "nonvanishing of the source scalar and the exact finite "
                "multiplicity or pole-degree balance for every supplied "
                "normalized meromorphic branch. The remaining carrier leaf "
                "no longer assumes a quadratic tangent unit or boundary "
                "classification."
            ),
            "governed_record_sha256": (
                SEPARATED_BRANCH_VALUATION_RECORD_SHA256
            ),
            "content_bound_receipt_sha256": (
                EXPECTED_SEPARATED_BRANCH_VALUATION_RECEIPT_SHA256
            ),
        },
        "scalar_free_all_order_specialization_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v45"
            ),
            "reason": (
                "A strengthened governed all-order specialization terminal "
                "constructs the normalized coupled relation and its entire "
                "triangular tower for arbitrary source scalar, including "
                "zero. Scalar nonvanishing is therefore removed from the "
                "actual-relation adapter leaf."
            ),
            "governed_record_sha256": (
                COUPLED_JULIA_ALL_ORDER_SPECIALIZATION_RECORD_SHA256
            ),
            "content_bound_receipt_sha256": (
                EXPECTED_COUPLED_JULIA_ALL_ORDER_SPECIALIZATION_RECEIPT_SHA256
            ),
        },
        "analytic_algebraic_branch_boundary_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v46"
            ),
            "reason": (
                "A governed local boundary theorem derives meromorphicity "
                "and constructs an exhaustive constant-equilibrium, finite "
                "positive-order, or pole negative-order carrier from a "
                "selected analytic algebraic root of the exact separated "
                "family. The dominant-component leaf no longer assumes a "
                "meromorphic branch or its boundary class."
            ),
            "governed_record_sha256": (
                ANALYTIC_ALGEBRAIC_BRANCH_BOUNDARY_RECORD_SHA256
            ),
            "content_bound_receipt_sha256": (
                EXPECTED_ANALYTIC_ALGEBRAIC_BRANCH_BOUNDARY_RECEIPT_SHA256
            ),
        },
        "raw_separated_branch_assembly_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v47"
            ),
            "reason": (
                "A governed assembly theorem constructs coefficient "
                "analyticity, a uniform degree bound, root membership, and "
                "an active coefficient directly from a selected punctured "
                "analytic branch satisfying the raw separated relation. The "
                "dominant-component leaf no longer supplies a degree-bounded "
                "polynomial family or an activity witness."
            ),
            "governed_record_sha256": (
                SEPARATED_ANALYTIC_BRANCH_ASSEMBLY_RECORD_SHA256
            ),
            "content_bound_receipt_sha256": (
                EXPECTED_SEPARATED_ANALYTIC_BRANCH_ASSEMBLY_RECEIPT_SHA256
            ),
        },
        "finite_endpoint_ode_continuation_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v48"
            ),
            "reason": (
                "A governed finite-endpoint theorem proves that every "
                "punctured controlled-polynomial trajectory with a finite "
                "limit extends analytically and continues to satisfy its ODE "
                "through the endpoint. The selected-factor continuation leaf "
                "is split at the remaining maximal-path and escape carrier."
            ),
            "governed_record_sha256": (
                FINITE_ENDPOINT_ODE_CONTINUATION_RECORD_SHA256
            ),
            "content_bound_receipt_sha256": (
                EXPECTED_FINITE_ENDPOINT_ODE_CONTINUATION_RECEIPT_SHA256
            ),
        },
        "bounded_derivative_endpoint_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v49"
            ),
            "reason": (
                "A governed substrate-neutral compactness theorem derives a "
                "finite endpoint limit from differentiability and a uniform "
                "derivative bound on a finite half-open interval. The "
                "maximal-path leaf is narrowed to construction of the lift "
                "and a bounded-speed versus reciprocal-infinity alternative."
            ),
            "governed_record_sha256": (
                BOUNDED_DERIVATIVE_ENDPOINT_RECORD_SHA256
            ),
            "content_bound_receipt_sha256": (
                EXPECTED_BOUNDED_DERIVATIVE_ENDPOINT_RECEIPT_SHA256
            ),
        },
        "bounded_controlled_polynomial_endpoint_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v50"
            ),
            "reason": (
                "A governed controlled-polynomial theorem derives an "
                "explicit uniform speed bound and finite endpoint limit from "
                "only bounded loop driver, bounded state, and the polynomial "
                "ODE. The maximal-lift leaf is narrowed to construction of "
                "the lift and a bounded-state versus reciprocal-infinity "
                "alternative."
            ),
            "governed_record_sha256": (
                BOUNDED_CONTROLLED_POLYNOMIAL_ENDPOINT_RECORD_SHA256
            ),
            "content_bound_receipt_sha256": (
                EXPECTED_BOUNDED_CONTROLLED_POLYNOMIAL_ENDPOINT_RECEIPT_SHA256
            ),
        },
        "norm_escape_reciprocal_endpoint_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v51"
            ),
            "reason": (
                "A governed substrate-neutral chart-change theorem now "
                "constructs eventual nonvanishing and reciprocal convergence "
                "to zero from norm escape along an arbitrary filter. The "
                "former bounded-state versus reciprocal-chart leaf is split "
                "into maximal-lift norm escape and the algebraic-to-"
                "holomorphic reciprocal-germ upgrade."
            ),
            "governed_record_sha256": (
                NORM_ESCAPE_RECIPROCAL_LIMIT_RECORD_SHA256
            ),
            "content_bound_receipt_sha256": (
                EXPECTED_NORM_ESCAPE_RECIPROCAL_LIMIT_RECEIPT_SHA256
            ),
        },
        "uniform_restart_endpoint_escape_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v52"
            ),
            "reason": (
                "A governed substrate-neutral maximal-continuation theorem "
                "derives finite endpoint extension or norm escape from "
                "restriction-stable local uniqueness and restart time "
                "uniform on bounded state balls. The maximal-lift leaf now "
                "owes construction of exactly that uniformly restartable "
                "selected carrier, rather than the escape conclusion."
            ),
            "governed_record_sha256": (
                UNIFORM_RESTART_ENDPOINT_ESCAPE_RECORD_SHA256
            ),
            "content_bound_receipt_sha256": (
                EXPECTED_UNIFORM_RESTART_ENDPOINT_ESCAPE_RECEIPT_SHA256
            ),
        },
        "controlled_polynomial_uniform_restart_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v53"
            ),
            "reason": (
                "A governed Picard--Lindelof construction now produces one "
                "positive restart time uniform over all real restart centers "
                "and all complex initial states in each fixed norm ball for "
                "a continuous globally bounded controlled-polynomial field. "
                "The selected maximal-lift leaf no longer owes bounded-ball "
                "restart itself."
            ),
            "governed_record_sha256": (
                CONTROLLED_POLYNOMIAL_UNIFORM_RESTART_RECORD_SHA256
            ),
            "content_bound_receipt_sha256": (
                EXPECTED_CONTROLLED_POLYNOMIAL_UNIFORM_RESTART_RECEIPT_SHA256
            ),
        },
        "controlled_polynomial_overlap_uniqueness_revision": {
            "supersedes_schema": (
                "axiompack.jacobian_critical_puiseux_formal_coverage.v54"
            ),
            "reason": (
                "A governed target-by-target Gronwall theorem now derives "
                "complete preconnected-domain uniqueness for two complex "
                "solutions of one bounded-driver controlled-polynomial ODE. "
                "The selected maximal-lift leaf no longer owes overlap "
                "uniqueness itself."
            ),
            "governed_record_sha256": (
                CONTROLLED_POLYNOMIAL_OVERLAP_UNIQUENESS_RECORD_SHA256
            ),
            "content_bound_receipt_sha256": (
                EXPECTED_CONTROLLED_POLYNOMIAL_OVERLAP_UNIQUENESS_RECEIPT_SHA256
            ),
        },
        "adapter_evidence": {
            "combined_sha256": adapter_sha256,
            "puiseux_script_sha256": script_sha256,
            "monodromy_script_sha256": monodromy_script_sha256,
            "monodromy_residue_certificate_sha256": (
                str(monodromy_residue["certificate_sha256"])
            ),
            "finite_monodromy_countermodels_certificate_sha256": (
                str(finite_monodromy_countermodels["certificate_sha256"])
            ),
            "projection_fallacy_certificate_sha256": (
                str(projection_fallacy["certificate_sha256"])
            ),
        },
        "governed_formal_supports": [
            {
                "role": role,
                "target": support.target,
                "record_sha256": support.governed_record_sha256,
                "receipt_sha256": support.receipt.receipt_sha256,
                "target_signature_sha256": identity.target_signature_sha256,
                "formal_proposition_identity_sha256": identity.identity_sha256,
            }
            for role, support, identity in active_support_rows
        ],
        "decomposition": decomposition.to_dict(),
        "coverage": coverage.to_dict(),
        "finite_julia_check_is_formal_leaf": True,
        "enclosing_authority_upgraded": False,
        "claim_boundary": (
            "Fifty governed supports cover the selected Puiseux germ, "
            "complex single-flow obstruction, finite Julia valuation "
            "classification, local ramified-cross Abel contradiction, "
            "proportional reduction, exact degree-seven no-rational-root "
            "arithmetic, the original-connection rationalization identity, "
            "and an explicit analytic loop with an injective critical "
            "orbit, division-free coupled-Julia elimination, local finite-"
            "state flow, first differential prolongation, multiplicity "
            "descent, triangular specialization, finite prolongation escape, "
            "all-order total-derivation specialization, the general iterated "
            "Leibniz law, the concrete triangular recurrence, local "
            "analytic Kummer classification, exact separated-polynomial "
            "finite/pole valuation, and the exhaustive local analytic-"
            "algebraic branch boundary trichotomy, including raw separated-"
            "branch assembly with a derived active coefficient, and finite-"
            "endpoint controlled-polynomial continuation and substrate-"
            "neutral bounded-derivative endpoint compactness and explicit "
            "bounded controlled-polynomial endpoint compactness, plus the "
            "substrate-neutral reciprocal chart change at norm escape and "
            "the uniform-restart finite-endpoint escape alternative and an "
            "explicit bounded-state uniform restart construction and "
            "complete overlap uniqueness for controlled polynomial fields. "
            "Five "
            "semantic leaves remain: finite differential-field hypotheses "
            "for the actual coupled relation, construction of a normalized "
            "dominant carrier with its lifted action, selected punctured "
            "analytic branch satisfying the raw separated relation, and "
            "selected-factor overlap, construction of a maximal selected "
            "lift with a globally bounded continuous loop driver, exact ODE "
            "bindings, and nonextendability, the "
            "selected algebraic reciprocal-germ upgrade, and selected "
            "nonfinite cross-carrier realization. Empty special fiber is not "
            "promoted to endpoint elimination. Fourteen dependent "
            "inference nodes and the "
            "direct root therefore remain outside formal authority."
        ),
    }
    return {
        **core,
        "formal_coverage_envelope_sha256": content_sha256(core),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
