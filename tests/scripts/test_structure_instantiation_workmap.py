import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "projects"
    / "ns_millennium_hunt"
    / "workspace"
    / "structure_instantiation_workmap.py"
)


def _load_script():
    spec = importlib.util.spec_from_file_location("structure_instantiation_workmap", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_semantic_surface_normalization_exposes_prop_field_duties():
    mod = _load_script()
    surface = mod.normalize_semantic_surface(
        "fixed_leray_profile_decomposition : Prop "
        "smoothLimitPreservesCostAndReserve : Prop"
    )

    matches = mod.PDE_TERM_RE.findall(surface)

    assert "profile" in [m.lower() for m in matches]
    assert "decomposition" in [m.lower() for m in matches]
    assert "smooth" in [m.lower() for m in matches]
    assert "reserve" in [m.lower() for m in matches]
