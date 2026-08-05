#!/usr/bin/env python3
"""Replay theorem-scoped formal support for filtered obstructions.

The support receipts below do not replace or strengthen the authority class
of an enclosing mathematical certificate.  Each receipt says exactly that one
Lean target signature passed the governed carried-theorem lifecycle under the
recorded toolchain and persisted kernel-parity identity.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys


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
from gauge_unrestricted_tail_minimax import run as global_run  # noqa: E402
from ztare.common.content_identity import content_sha256  # noqa: E402
from ztare.leanmill.filtered_evidence_authority import (  # noqa: E402
    make_content_bound_evidence_from_governed_ratification,
    replay_content_bound_evidence_from_governed_ratification,
)
from ztare.leanmill.governed_ratification import (  # noqa: E402
    normalized_target_signature,
)
from ztare.leanmill.lean_source import (  # noqa: E402
    open_decl_for_ratification,
)


LEAN_ROOT = REPO / "ztare_proofs"
CERTIFICATE_LEDGER = (
    REPO / "analytics/public/queries/adhoc_closure_certificates.jsonl"
)
PARITY_LEDGER = REPO / "analytics/public/queries/kernel_parity.jsonl"

TARGETS = (
    (
        "pure_polar_tensor_arithmetic",
        (
            "AxiomPackJacobianPolarTensorInductionArithmetic."
            "polar_tensor_induction_arithmetic_terminal_certificate"
        ),
        "AxiomPackJacobianPolarTensorInductionArithmetic.lean",
        "7de38a81b1862588b83da3cb4bba87deb36069b6d7c8504552cad8e7e5035a95",
    ),
    (
        "least_positive_arithmetic",
        (
            "AxiomPackJacobianMovingBackboneInductionArithmetic."
            "moving_backbone_induction_arithmetic_terminal_certificate"
        ),
        "AxiomPackJacobianMovingBackboneInductionArithmetic.lean",
        "c3d9134868d5900504ca243d219f9b3ee0006f8485e666d5a7a6e8ef747fad65",
    ),
    (
        "critical_puiseux_arithmetic",
        (
            "AxiomPackJacobianCriticalPuiseuxArithmetic."
            "critical_puiseux_arithmetic_terminal_certificate"
        ),
        "AxiomPackJacobianCriticalPuiseuxArithmetic.lean",
        "6caf168f5d071956f6f0d8a3567296c7984bcae13b3b682afb62381fa8c12699",
    ),
    (
        "radial_staircase_arithmetic",
        (
            "AxiomPackJacobianConeRadialStaircaseArithmetic."
            "cone_radial_staircase_arithmetic_terminal_certificate"
        ),
        "AxiomPackJacobianConeRadialStaircaseArithmetic.lean",
        "3e366a5c7db36448e86ec2b7b11e5819870ea27e2454824fce503d7573f771ec",
    ),
    (
        "alien_valuation_arithmetic",
        (
            "FilteredObstructionAlienValuationArithmetic."
            "alien_valuation_arithmetic_terminal_certificate"
        ),
        "FilteredObstructionAlienValuationArithmetic.lean",
        "5552223fa5ecd2b3ecc35c8610634b5c9ee0eb948edbafd96c3c3c7110ad3e77",
    ),
    (
        "global_tail_composition_arithmetic",
        (
            "AxiomPackJacobianTailMinimaxComposition."
            "tail_minimax_composition_terminal_certificate"
        ),
        "AxiomPackJacobianTailMinimaxComposition.lean",
        "eadf2a40b28a4f563b0c58ff5c62485b58b4eb710de83fd27a0346c72270a001",
    ),
)


def _support_receipt(
    label: str,
    target: str,
    source_name: str,
    record_sha256: str,
) -> dict[str, object]:
    source = (LEAN_ROOT / "ZtareProofs" / source_name).read_text(
        encoding="utf-8"
    )
    posed, proof = open_decl_for_ratification(source, target)
    signature = normalized_target_signature(source, target)
    arguments = {
        "certificate_ledger": CERTIFICATE_LEDGER,
        "governed_record_sha256": record_sha256,
        "parity_ledger": PARITY_LEDGER,
        "target": target,
        "expected_signature": signature,
        "posed_source": posed,
        "proof_text": proof,
        "goal": signature,
        "lean_root": LEAN_ROOT,
        "expected_provider": "existing_artifact",
    }
    receipt = make_content_bound_evidence_from_governed_ratification(
        **arguments
    )
    assert replay_content_bound_evidence_from_governed_ratification(
        receipt,
        **arguments,
    ) == receipt
    return {
        "label": label,
        "source_file": f"ztare_proofs/ZtareProofs/{source_name}",
        "governed_record_sha256": record_sha256,
        "receipt": receipt.to_dict(),
    }


def run(*, verify_semantics: bool = True) -> dict[str, object]:
    supports = tuple(_support_receipt(*target) for target in TARGETS)
    semantic_links: dict[str, object] = {
        "authority_boundary": (
            "theorem-scoped arithmetic support only; enclosing adapter and "
            "filtered-compiler authority is unchanged"
        ),
        "support_labels": [row["label"] for row in supports],
    }
    if verify_semantics:
        puiseux = puiseux_run(8)
        global_certificate = global_run(8)
        puiseux_single = puiseux["filtered_obstruction_compiler"][
            "puiseux_flow_certificate_sha256"
        ]
        puiseux_two = puiseux[
            "filtered_two_flow_obstruction_compiler"
        ]["two_flow_puiseux_certificate_sha256"]
        global_compiler = global_certificate["filtered_obstruction_compiler"]
        assert puiseux_single == (
            "6c3a97ebae223d4c0dbf6762d1399d242ea951459d3e7ae44255be2575931926"
        )
        assert puiseux_two == (
            "190c7ff996246b663dc6ab94435aaea81fa8f8e4c009188badac06ec88bc963c"
        )
        assert global_compiler["tail_minimax_certificate_sha256"] == (
            "24bee337068d65d8d81d1fa4ac584cec1130e3b160bef765f5afbd131acc1108"
        )
        semantic_links.update({
            "critical_puiseux_single_sha256": puiseux_single,
            "critical_puiseux_two_flow_sha256": puiseux_two,
            "least_positive_sha256": global_certificate[
                "branch_partition"
            ]["least_positive_contact"]["certificate_sha256"],
            "radial_staircase_upper_sha256": global_certificate[
                "upper_construction"
            ]["certificate_sha256"],
            "global_tail_minimax_sha256": global_compiler[
                "tail_minimax_certificate_sha256"
            ],
            "global_proof_contract_sha256": global_compiler[
                "proof_contract_sha256"
            ],
        })
    core = {
        "schema": "axiompack.filtered_kernel_support_envelope.v1",
        "supports": list(supports),
        "semantic_links": semantic_links,
        "enclosing_authority_upgraded": False,
    }
    return {**core, "proof_envelope_sha256": content_sha256(core)}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
