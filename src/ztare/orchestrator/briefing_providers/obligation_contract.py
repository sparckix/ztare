"""GP-241 V4 second-consumer — obligation-contract briefing provider.

OUT-OF-LOOP → IN-LOOP: the V4 mutator was blind to org-wide discipline
(no provider read the catalogs). This T0 provider runs the SAME
substrate-agnostic obligation compiler the RD path uses, but against a
V4-SPECIFIC activation file (org/catalog_routing/v4_activation.yaml)
keyed ONLY to V4 deterministic telemetry — RD prediction-market/NS
obligations are deliberately NOT imported (operator 2026-05-17: V4
obligations are substrate-specific; importing RD ones would never-fire
or flood). Discharge of a V4 obligation = an existing deterministic V4
telemetry/gate result, not an agent witness (V4 has no witness channel).

OBSERVE-MODE: this RENDERS the obligation fragment + PERSISTS a frozen
pre-iteration snapshot (workspace/obligation_contract_iter_NNN.json).
The ENFORCING close-gate (telemetry-discharge at promotion, recomputed
from the frozen snapshot) is deliberately NOT here — it is a new design
element pending cold cross-provider review before any autoresearch_loop
promotion-path edit (GP-241). Degrades safe: any error ⇒ "" (the loop
must never break on this provider).
"""
from __future__ import annotations

import json
from pathlib import Path

from ztare.orchestrator.mutator_briefing import (
    BriefingContext, BriefingProvider)
from ztare.orchestrator.briefing_providers import section_unavailable


class ObligationContractProvider(BriefingProvider):
    name = "obligation_contract"
    priority = 100          # critical / early
    tier = 0                # T0 = always (apparatus contract)

    def applies(self, ctx: BriefingContext) -> bool:
        # always evaluates; fragment() returns "" (abstain) when no
        # mandatory obligation fires — abstention is the preferred
        # output (flooding is itself a failed membrane).
        return True

    def _v4_signals(self, ctx: BriefingContext) -> dict:
        """Typed V4 telemetry → declared signals. ONLY first-class
        deterministic BriefingContext telemetry (paraphrase-proof;
        no prose sniffing). Conservative seed: stagnation only."""
        return {"v4_stalled": int(getattr(ctx, "stagnation_count", 0) or 0) > 2}

    def _activation_corruption(self):
        """None if the V4 activation file is absent (legit not-applicable)
        or parses clean; else the parse/read exc. `_load_clauses` swallows
        a corrupt file to `[]`, which would drop every mandatory obligation
        silently — so we probe the file ourselves to tell the two apart."""
        import yaml
        from ztare.surfacing.pre_tick_obligation_compiler import ROUTING
        p = ROUTING / "v4_activation.yaml"
        if not p.is_file():
            return None  # absent ⇒ genuinely not-applicable
        try:
            yaml.safe_load(p.read_text(encoding="utf-8"))
            return None
        except Exception as exc:  # noqa: BLE001
            return exc

    def fragment(self, ctx: BriefingContext) -> str:
        # A corrupt activation file must NEVER coerce to "no obligations"
        # (that silently drops a possibly-binding mandatory obligation).
        corrupt = self._activation_corruption()
        if corrupt is not None:
            return section_unavailable("OBLIGATION CONTRACT", corrupt)
        try:
            from ztare.surfacing.pre_tick_obligation_compiler import (
                start_tick)
            signals = self._v4_signals(ctx)
            contract = start_tick(
                "", "v4_iter", signals,
                clause_files=["v4_activation.yaml"])
            # frozen pre-iteration snapshot (the close-gate, when
            # cold-reviewed, recomputes from THIS, not live state).
            try:
                ws = ctx.workspace_dir or (ctx.project_dir / "workspace")
                ws.mkdir(parents=True, exist_ok=True)
                snap = ws / f"obligation_contract_iter_{ctx.iter_index:03d}.json"
                snap.write_text(json.dumps({
                    "iter_index": ctx.iter_index,
                    "v4_signals": signals,
                    "contract": contract.as_dict(),
                    "mode": "observe",  # NOT enforcing yet (GP-241)
                }, indent=2), encoding="utf-8")
            except Exception:
                pass  # persistence best-effort; never break the loop
            mand = contract.mandatory_obligations
            if not mand:
                return ""  # abstain — no flood
            lines = [
                "## ⛔ OBLIGATION CONTRACT (GP-241 V4, observe-mode)",
                "Deterministic, telemetry-keyed. These are MANDATORY for "
                "this iteration (discharge = the named deterministic V4 "
                "result; enforcement at promotion is pending cold review):",
            ]
            for o in mand:
                req = ", ".join(o.get("witness_schema", {})
                                .get("required", []))
                lines.append(
                    f"- [{o['layer']}] {o['item_id']} "
                    f"(anchor {o.get('catalog_anchor')}): "
                    f"{o['obligation']}\n  discharge ⇒ {req}")
            return "\n".join(lines) + "\n"
        except Exception as exc:  # noqa: BLE001
            # The activation file parses (probed above), so a failure here
            # is a compute/render fault while obligations may be binding —
            # banner it rather than silently dropping a mandatory obligation.
            return section_unavailable("OBLIGATION CONTRACT", exc)
