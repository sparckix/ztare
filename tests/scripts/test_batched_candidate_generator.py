import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "batched_candidate_generator.py"
)


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "batched_candidate_generator",
        SCRIPT_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_source_witness_mode_rejects_target_record_argument():
    mod = _load_script()

    src = """
import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem lowHighReservePDESource_satisfied
    (R : GP216BridgeCompositionReceipt) :
    LowHighLipschitzReservePDEObligationSatisfied R.lowHighReservePDESource.obligation :=
  R.lowHighReservePDESource.satisfied

end ZtareProofs.NS
"""

    reason = mod.candidate_degeneracy_reason(
        src,
        target="GP216BridgeCompositionReceipt",
        field="lowHighReservePDESource",
        require_source_witness=True,
    )

    assert reason == "target_record_argument_in_source_witness_mode"


def test_import_normalization_only_repairs_filesystem_style_ztare_imports():
    mod = _load_script()

    src = "\n".join([
        "import ztare_proofs.ZtareProofs.ns_gp216_bridge_composition_receipt",
        "import ZtareProofs.ns_profile_lipschitz_clay_bridge",
    ])

    normalized = mod.normalize_candidate_source(src)

    assert (
        "import ZtareProofs.ns_gp216_bridge_composition_receipt"
        in normalized
    )
    assert "import ztare_proofs.ZtareProofs" not in normalized
    assert "import ZtareProofs.ns_profile_lipschitz_clay_bridge" in normalized
