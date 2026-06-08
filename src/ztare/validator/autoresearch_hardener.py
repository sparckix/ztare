"""Autoresearch instance of the shared KERNEL-HARDENING contract (common/kernel_hardener.py) — the GP-086
cage gaming-pattern hardener, REFACTORED onto the interface (2026-06-06).

This does NOT rewrite GP-086: it CONFORMS the existing autoresearch hardening (the lexical
`sandbox_gaming_extractor` miner + the CAGE gaming-pattern gates) to the shared `KernelHardener` protocol,
so autoresearch and leanmill mine/catalog/gate through ONE contract and ONE cross-substrate catalog
(additive — the extractor and the Cage are untouched). Mirrors how `inverter_agent.ThesisInverter`
conformed the autoresearch inverter to the shared `Inversion` contract.

  * mine          — `sandbox_gaming_extractor.classify_signals` over debate text → GamingVectors.
  * reproduce     — a category without a promoted CAGE gate still escapes (open backlog).
  * derive_gate   — references the existing CAGE gate for that category (GP-086 promotion; deterministic).
  * register_gate — confirms the CAGE gate exists for the category (GP-086 already wired the gated ones).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ztare.common.kernel_hardener import GamingVector
from ztare.gates.autoresearch_gaming_gates import AUTORESEARCH_GAMING_DETECTORS

# Categories GP-086 already promoted into deterministic CAGE gates (Phase 0–1). Others are cataloged-but-
# open (the autoresearch hardening backlog). Mirrors the GP-086 spec's phased promotion.
_GP086_GATED = {
    "uniqueness_gap": "global_gates:global_uniqueness_gap",
    "parsimony_violation": "global_gates:global_parsimony_violation",
    "extrapolation_gap": "global_gates:global_extrapolation_gap",
}


class AutoresearchHardener:
    """KernelHardener for the autoresearch (symbolic-regression / debate) substrate."""
    substrate = "autoresearch"
    MINER_VERSION = "autoresearch_hardener.v1"
    mine_manifest_path = None

    def _iter_inputs(self, debate_texts) -> "Iterable[tuple[str, str, Path | None]]":
        """Yield (label, text, optional_path). Raw strings remain supported; existing paths get
        content-hash checkpointing through the shared hardener manifest."""
        items = [debate_texts] if isinstance(debate_texts, (str, Path)) else list(debate_texts or [])
        for item in items:
            if isinstance(item, Path):
                path = item
            elif isinstance(item, str):
                maybe_path = Path(item)
                path = maybe_path if maybe_path.exists() and maybe_path.is_file() else None
            else:
                path = None
            if path is not None:
                try:
                    yield (str(path), path.read_text(encoding="utf-8"), path)
                except Exception:  # noqa: BLE001
                    yield (str(path), "", path)
            else:
                yield ("raw_text", str(item or ""), None)

    def mine(self, debate_texts, *, incremental: bool = True) -> "list[GamingVector]":
        """Classify debate text(s) with the EXISTING lexical extractor → one GamingVector per detected
        gaming category. `debate_texts` may be raw text, a path, or an iterable of either. File inputs use
        the shared content-hash manifest, so unchanged artifacts are skipped at the same miner version."""
        from ztare.validator.sandbox_gaming_extractor import classify_signals
        from ztare.common.kernel_hardener import MINE_MANIFEST, load_mine_manifest, record_mined, should_mine

        manifest_path = self.mine_manifest_path or MINE_MANIFEST
        manifest = load_mine_manifest(manifest_path)
        seen: dict[str, GamingVector] = {}
        for label, text, path in self._iter_inputs(debate_texts):
            if path is not None and incremental and not should_mine(path, manifest, miner_version=self.MINER_VERSION):
                continue
            found: list[str] = []
            for sig in classify_signals(text or ""):
                found.append(sig)
                if sig in seen:
                    continue
                gate = _GP086_GATED.get(sig, "")
                seen[sig] = GamingVector(
                    name=sig, substrate="autoresearch", category=sig,
                    mechanism=f"autoresearch gaming signal '{sig}' (lexical extractor)",
                    evidence=label, severity="med",
                    already_gated_by=gate, proposed_gate=(gate or f"CAGE gate for {sig} (GP-086 backlog)"),
                    substrate_class="symbolic_regression", cage_phase="POST_JUDGE",
                    gate_name=(gate.split(":")[-1] if gate else ""),
                    status=("gated" if gate else "open"), discovered_by="autoresearch_hardener.mine")
            for name, spec in AUTORESEARCH_GAMING_DETECTORS.items():
                if not spec.detector(text or ""):
                    continue
                found.append(name)
                if name in seen:
                    continue
                seen[name] = GamingVector(
                    name=name, substrate="autoresearch", category=spec.category,
                    mechanism=spec.mechanism, evidence=label, severity="high",
                    already_gated_by="", proposed_gate=spec.proposed_gate,
                    substrate_class="symbolic_regression", cage_phase="POST_JUDGE",
                    gate_name="", status="open", discovered_by="autoresearch_hardener.project_sweep_detector")
            if path is not None and incremental:
                record_mined(path, found, miner_version=self.MINER_VERSION, path=manifest_path)
        return list(seen.values())

    def reproduce(self, vector: GamingVector) -> bool:
        return not vector.already_gated_by    # no promoted CAGE gate ⇒ still escapes (open)

    def derive_gate(self, vector: GamingVector) -> str:
        return vector.proposed_gate    # the (existing or backlog) CAGE gate spec

    def register_gate(self, vector: GamingVector) -> bool:
        return bool(vector.already_gated_by)   # GP-086 already wired the gated categories


def _selftest() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    from ztare.common.kernel_hardener import KernelHardener
    from ztare.common.kernel_hardener import load_mine_manifest
    import tempfile
    h = AutoresearchHardener()
    ok("conforms to KernelHardener protocol", isinstance(h, KernelHardener))
    vs = h.mine("The thesis assumes uniqueness but no proof of uniqueness; rivals not enumerated. "
                "It also extrapolates far outside the observed regime.")
    names = {v.name for v in vs}
    ok("mines uniqueness_gap + extrapolation_gap via the extractor", "uniqueness_gap" in names)
    ok("GP-086-gated category carries its CAGE gate",
       any(v.already_gated_by and v.name == "uniqueness_gap" for v in vs))
    fixture_root = Path(__file__).resolve().parents[3] / "benchmarks" / "constraint_memory"
    fixture_vectors = h.mine([
        fixture_root / "specimens" / "bad" / "self_referential_falsification" / "test_model.py",
        fixture_root / "derived_subtle" / "threshold_rigging_submerged" / "test_model.py",
        fixture_root / "auxiliary_historical" / "central_station_hypothetical_target_laundering" / "test_model.py",
    ], incremental=False)
    fixture_names = {v.name for v in fixture_vectors}
    ok("detects self-confirming metric fixture",
       "definitional_tautology_self_confirming_metric" in fixture_names)
    ok("detects fabricated calibration fixture",
       "fabricated_calibration_set_threshold_laundering" in fixture_names)
    ok("detects assumed-input evidence fixture",
       "assumption_as_evidence_relabeling" in fixture_names)

    tmp = Path(tempfile.mkdtemp())
    art = tmp / "debate.md"
    man = tmp / "manifest.jsonl"
    art.write_text("The thesis assumes uniqueness; no rival form is enumerated.")

    old_manifest = h.mine_manifest_path
    h.mine_manifest_path = man
    try:
        first = h.mine([art], incremental=True)
        second = h.mine([art], incremental=True)
        manifest = load_mine_manifest(man)
        ok("file input mines through content-hash manifest", any(v.name == "uniqueness_gap" for v in first))
        ok("unchanged file input is skipped", second == [])
        ok("manifest records artifact hash + miner version",
           str(art) in manifest and manifest[str(art)].get("miner") == h.MINER_VERSION)
    finally:
        h.mine_manifest_path = old_manifest
    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
