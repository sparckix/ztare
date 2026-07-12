"""Lateral basin escape: cross-domain structure transport (2026-07-03).

The HORIZONTAL complement to the loop's vertical cold-deanchor
(cold_deanchor_carveout3 / GP-045 residual). When the home basin is
provably stuck, this surfaces established structures from OTHER fields whose
SHAPE matches the current seam — a conjectural functor to try, not a result.

Advisory (tier 2). STAGNATION-GATED in applies() — cross-domain analogy is
noise on a healthy iteration, so it only fires at stagnation_count >= 2.

Fingerprint source, in priority order:
  (a) persisted cuts (workspace/structural_transport_cuts.json).
  (b) persisted champion spec (workspace/champion_spec.json), lowered into cuts.
  (c) generic project (workspace/seam.json): a hand-written failure_state
      {"constraint_class":..., "home_field":..., <invariant keys>...} used as
      the single cut.
Neither present -> the provider does not apply.

Cache discipline: prompt rendering is a reader path. By default this provider
renders only SHA-matched cached candidates in workspace/structural_transports.json.
Legacy live querying is available only behind the explicit rubric flag
``briefing_compute_structural_transport``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ztare.orchestrator.briefing_providers import section_unavailable
from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider

_ARTIFACT = "structural_transports.json"
_HEADER = ("LATERAL TRANSPORT (advisory — cross-domain structures matching "
           "this seam's shape, surfaced because the run is stagnating):")
_FOOTER = ("These are conjectural functors, not results: a transport counts "
           "only if it compiles to a law that passes the deterministic gates.")
_SOURCE_CACHE_VERSION = 2


class _SourceCorrupt(Exception):
    """A present structural-transport source file is unreadable/unparseable."""


class StructuralTransportProvider(BriefingProvider):
    name = "structural_transport"

    def _source_key(self, ctx: BriefingContext) -> "str | None":
        """Cheap source identity. This must stay cheaper than abduction."""
        project = Path(getattr(ctx, "project_dir", "") or "")
        cuts = project / "workspace" / "structural_transport_cuts.json"
        if cuts.exists():
            return "cuts:" + hashlib.sha256(cuts.read_bytes()).hexdigest()
        champion = project / "workspace" / "champion_spec.json"
        if champion.exists():
            return "champion:" + hashlib.sha256(champion.read_bytes()).hexdigest()
        seam = project / "workspace" / "seam.json"
        if seam.exists():
            return "seam:" + hashlib.sha256(seam.read_bytes()).hexdigest()
        return None

    def _has_source(self, ctx: BriefingContext) -> bool:
        project = Path(getattr(ctx, "project_dir", "") or "")
        ws = project / "workspace"
        return (
            (ws / "structural_transport_cuts.json").exists()
            or (ws / "champion_spec.json").exists()
            or (ws / "seam.json").exists()
            or (ws / _ARTIFACT).exists()
        )

    # ── fingerprint sourcing ────────────────────────────────────────────
    def _cuts(self, ctx: BriefingContext) -> "list[dict] | None":
        """The seam cut several ways (worldmodel) or the hand-written seam
        (generic). Deterministic, no model calls. None -> no source.

        Raises ``_SourceCorrupt`` when a PRESENT source file is unparseable:
        a corrupt source must not be silently swallowed into "no transport
        opportunity" — fragment() surfaces it as a banner.
        """
        project = Path(getattr(ctx, "project_dir", "") or "")
        ws = project / "workspace"
        # (a) producer-persisted cuts
        cuts_path = ws / "structural_transport_cuts.json"
        if cuts_path.exists():
            try:
                cuts = json.loads(cuts_path.read_text())
            except SystemExit:
                raise
            except Exception as exc:  # noqa: BLE001
                raise _SourceCorrupt(f"{cuts_path.name}: {exc}") from exc
            if cuts:
                return cuts
        # (b) producer-persisted champion spec. Roles are optional; the
        # fingerprint compiler accepts a spec-only structure.
        champion = ws / "champion_spec.json"
        if champion.exists():
            try:
                from ztare.research_director.research_isomorphism import cuts_from_structure
                spec = json.loads(champion.read_text())
                cuts = cuts_from_structure(None, spec)
            except SystemExit:
                raise
            except Exception as exc:  # noqa: BLE001
                raise _SourceCorrupt(f"{champion.name}: {exc}") from exc
            if cuts:
                return cuts
        # (c) generic: a hand-written seam is the single cut
        seam = ws / "seam.json"
        if seam.exists():
            try:
                data = json.loads(seam.read_text())
            except SystemExit:
                raise
            except Exception as exc:  # noqa: BLE001
                raise _SourceCorrupt(f"{seam.name}: {exc}") from exc
            if isinstance(data, dict) and data.get("constraint_class"):
                return [data]
        return None

    @staticmethod
    def _sha(cuts: "list[dict]") -> str:
        return hashlib.sha256(
            json.dumps(cuts, sort_keys=True, default=str).encode()).hexdigest()

    # ── live query (real API money — only on cache miss/sha change) ──────
    def _query(self, cuts: "list[dict]") -> list:
        from ztare.research_director.research_isomorphism import (
            diversity_query, surface_multicut)
        return surface_multicut(
            cuts, query=diversity_query(("deepseek",), typed_mapping=True),
            n_per_cut=3, ledger=None)

    @staticmethod
    def _to_dict(iso) -> dict:
        return {"theorem": iso.theorem, "field": iso.field,
                "mechanism": iso.mechanism, "mapping_hint": iso.mapping_hint,
                "enrichment": iso.enrichment}

    def _render(self, cands: "list[dict]") -> str:
        if not cands:
            return ""
        ordered = sorted(
            cands, key=lambda c: (c.get("enrichment") is None, -(c.get("enrichment") or 0.0)))
        lines = [_HEADER]
        for c in ordered[:4]:
            enr = c.get("enrichment")
            enr_s = f"{enr:.2f}" if isinstance(enr, (int, float)) else "n/a"
            mech = (c.get("mechanism") or "").strip().splitlines()
            mech = mech[0] if mech else ""
            hint = (c.get("mapping_hint") or "")[:140]
            lines.append(f"- {c.get('theorem', '')} ({c.get('field', '')}, "
                         f"enrichment={enr_s}): {mech}. Hint: {hint}")
        lines.append(_FOOTER)
        return "\n".join(lines) + "\n"

    # ── provider contract ───────────────────────────────────────────────
    def applies(self, ctx: BriefingContext) -> bool:
        # lateral transport only when the home basin is provably stuck
        if int(getattr(ctx, "stagnation_count", 0) or 0) < 2:
            return False
        # Do not compute cuts here. The renderer calls applies() before
        # fragment(), and worldmodel cuts may require abduction over the log.
        return self._has_source(ctx)

    def fragment(self, ctx: BriefingContext) -> str:
        art = Path(ctx.project_dir) / "workspace" / _ARTIFACT
        source_key = self._source_key(ctx)
        if art.exists():
            try:
                payload = json.loads(art.read_text())
                cached = payload.get("candidates") or []
                if cached and (
                    payload.get("source_key") == source_key
                ):
                    return self._render(cached)
            except Exception:  # noqa: BLE001 — corrupt cache -> recompute below
                pass

        try:
            cuts = self._cuts(ctx)
        except _SourceCorrupt as exc:
            return section_unavailable("STRUCTURAL TRANSPORT", exc)
        if not cuts:
            return ""
        sha = self._sha(cuts)
        cached = None
        if art.exists():
            try:
                payload = json.loads(art.read_text())
                if payload.get("fingerprint_sha") == sha:
                    cached = payload.get("candidates") or []
            except Exception:  # noqa: BLE001 — corrupt cache -> re-query
                cached = None
        if cached is None:
            if not bool((ctx.rubric or {}).get("briefing_compute_structural_transport", False)):
                return ""
            try:
                cached = [self._to_dict(i) for i in self._query(cuts)]
            except Exception as exc:  # noqa: BLE001 — query failed: surface the
                # failure via a banner (do NOT overwrite the artifact with a
                # poisoned cache — we skip the write below by returning here).
                return section_unavailable("STRUCTURAL TRANSPORT", exc)
            try:
                art.parent.mkdir(parents=True, exist_ok=True)
                art.write_text(json.dumps(
                    {
                        "cache_version": _SOURCE_CACHE_VERSION,
                        "source_key": source_key,
                        "fingerprint_sha": sha,
                        "candidates": cached,
                    },
                    indent=2,
                ))
            except Exception:  # noqa: BLE001 — cache write is best effort
                pass
        return self._render(cached)


# ── hermetic selftest (no live LLM) ──────────────────────────────────────
def _self_test() -> int:
    import tempfile

    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    td = Path(tempfile.mkdtemp(prefix="structxport_"))
    (td / "workspace").mkdir(parents=True, exist_ok=True)
    (td / "workspace" / "seam.json").write_text(json.dumps({
        "constraint_class": "a monotonically depleting resource gates a rigid translation",
        "home_field": "grid worlds",
        "resource_direction": "monotone_nonincreasing",
    }))
    prov = StructuralTransportProvider()

    ctx0 = BriefingContext(project_dir=td, iter_index=5, rubric={}, stagnation_count=0)
    ctx3 = BriefingContext(project_dir=td, iter_index=5, rubric={}, stagnation_count=3)
    ok("does NOT apply on a healthy iter (stagnation 0)", prov.applies(ctx0) is False)
    ok("applies when stagnating (stagnation 3) with a seam source", prov.applies(ctx3) is True)

    cuts = prov._cuts(ctx3)
    sha = prov._sha(cuts)
    art = td / "workspace" / _ARTIFACT

    # cache-hit render is PURE (matching sha -> no query); candidates unsorted on disk
    art.write_text(json.dumps({"fingerprint_sha": sha, "candidates": [
        {"theorem": "Low", "field": "coding theory", "mechanism": "m-low", "mapping_hint": "h", "enrichment": 0.20},
        {"theorem": "High", "field": "spectral geometry", "mechanism": "m-high", "mapping_hint": "h", "enrichment": 0.90},
        {"theorem": "Null", "field": "topology", "mechanism": "m-null", "mapping_hint": "h", "enrichment": None},
        {"theorem": "Mid", "field": "scheduling", "mechanism": "m-mid", "mapping_hint": "h", "enrichment": 0.50},
    ]}))
    prov._query = lambda _cuts: (_ for _ in ()).throw(  # any query here = test bug
        AssertionError("cache hit must not query"))
    frag = prov.fragment(ctx3)
    ok("cache-hit fragment carries the header", _HEADER in frag)
    i_hi, i_mid, i_lo, i_null = (frag.index("enrichment=0.90"), frag.index("enrichment=0.50"),
                                 frag.index("enrichment=0.20"), frag.index("enrichment=n/a"))
    ok("candidates sorted by enrichment (None last)", i_hi < i_mid < i_lo < i_null)
    ok("footer present", _FOOTER in frag)

    # stale sha without explicit compute -> "" and the artifact is NOT overwritten
    art.write_text(json.dumps({"fingerprint_sha": "STALE", "candidates": [{"theorem": "keep-me"}]}))
    before = art.read_text()
    prov._query = lambda _cuts: (_ for _ in ()).throw(
        AssertionError("default provider path must not query"))
    frag2 = prov.fragment(ctx3)
    ok("stale cache without compute flag renders nothing", frag2 == "")
    ok("stale cache without compute flag does NOT overwrite the artifact", art.read_text() == before
       and "keep-me" in art.read_text())

    # Legacy opt-in live query remains available for explicit experiments.
    ctx3_compute = BriefingContext(
        project_dir=td,
        iter_index=5,
        rubric={"briefing_compute_structural_transport": True},
        stagnation_count=3,
    )
    prov._query = lambda _cuts: []
    ok("explicit compute flag may refresh a stale cache", prov.fragment(ctx3_compute) == "")

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    print("\n--- rendered cache-hit fragment ---\n" + frag)
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
