"""Typed solver config (the YAML-override layer for the solver axis — part of the #49 typed-contract
migration). DESIGN CHOICE that keeps it bug-safe: the CANONICAL defaults live in code (e.g. the
`_NATIVE_HAMMER_TACTICS` cascade with its ordering rationale stays in solver_core), and this config is an
OPTIONAL operator OVERRIDE — an absent YAML / empty field means "use the code default", so behaviour is
byte-identical with no config file present. We do NOT transcribe the canonical lists into the config
default (that would be a second source that can drift); the config only carries an override + pure tuning
knobs.

Soundness note: only PURE-TUNING knobs are exposed (cascade order, timeouts). A worse value costs closures,
never a false closure (the kernel still gates). Soundness-critical constants (the axiom allowlist, the
axiom-clean battery portfolio) are deliberately NOT operator-overridable here — they stay frozen in code.
"""
from __future__ import annotations

from pathlib import Path

from ztare.leanmill.contracts.kernel import YamlConfig

# Optional override file (operator tuning); absent ⇒ all code defaults (byte-parity).
_DEFAULT_PATH = Path(__file__).with_name("solver.yaml")


class SolverConfig(YamlConfig):
    # [] / 0 ⇒ "use the code default" (the canonical cascade + floor stay in solver_core). A non-empty list
    # REPLACES the cascade; a positive floor REPLACES `max(20, …)`.
    native_hammer_tactics: list[str] = []
    native_hammer_per_tactic_floor_s: int = 0   # 0 ⇒ keep the code default (20)
    # Autoformalize firewall round-trip model (back-translate + directional judge). "" ⇒ the code default
    # (a cross-family model vs the formalizer). NOT hardcoded in autoformalize.py — set it in solver.yaml when a
    # model id is deprecated or a different cross-family judge is preferred. Cross-family independence from the
    # formalizer is the soundness-relevant property; the specific id is operator policy.
    roundtrip_model: str = ""
    roundtrip_fallback_model: str = ""   # "" ⇒ code default; comma-separated for multiple fallbacks
    judge_panel_models: str = ""         # firewall judge-diversity panel families (comma-separated); "" ⇒ code default

    @classmethod
    def load_default(cls) -> "SolverConfig":
        return cls.load(path=_DEFAULT_PATH, env_var="ZTARE_LEANMILL_SOLVER_CONFIG")


def _selftest() -> int:
    fails = []
    c = SolverConfig.load_default()  # no YAML present ⇒ all-default ⇒ override is a no-op (byte-parity)
    if c.native_hammer_tactics != [] or c.native_hammer_per_tactic_floor_s != 0:
        fails.append(f"default override should be empty (byte-parity): {c}")
    # an override parses + validates
    c2 = SolverConfig(native_hammer_tactics=["rfl", "decide"], native_hammer_per_tactic_floor_s=30)
    if c2.native_hammer_tactics != ["rfl", "decide"] or c2.native_hammer_per_tactic_floor_s != 30:
        fails.append("override not applied")
    try:
        SolverConfig(bogus=1); fails.append("should forbid a typo'd key")
    except Exception:  # noqa: BLE001
        pass
    print("SOLVER CONFIG SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
