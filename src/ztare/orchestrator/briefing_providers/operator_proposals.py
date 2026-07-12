"""Operator-proposal briefing provider (GP-250, ENGINE-level).

Surfaces the automated grammar-ceiling evidence: when a project's
``workspace/operator_proposals.jsonl`` holds undispositioned candidate operator
cards, brief the mutator that the residual is irreducible under the current
catalog and a candidate operator card exists. The mutator's job is the LAW
SHAPE (refine the sketch/params in its thesis); the conductor validates each
card via its acceptance test. Reads only the deterministic workspace ledger.
"""
from __future__ import annotations

import json
from pathlib import Path

from ztare.orchestrator.briefing_providers import section_unavailable
from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


def _is_json_object(line: str) -> bool:
    try:
        return isinstance(json.loads(line), dict)
    except Exception:  # noqa: BLE001
        return False

_HEADER = (
    "GRAMMAR CEILING EVIDENCE — the residual is irreducible under the current "
    "operator catalog. Candidate operator card(s) exist; your job is the LAW "
    "SHAPE (refine the sketch/params in your thesis), not code — the conductor "
    "validates each via its acceptance test:"
)


class OperatorProposalsProvider(BriefingProvider):
    name = "operator_proposals"
    max_fragment_chars = 900

    def _cards(self, project: Path, *, raise_on_error: bool = False):
        try:
            from ztare.common.operator_proposal_contract import open_cards
            return open_cards(project / "workspace" / "operator_proposals.jsonl")
        except Exception:  # noqa: BLE001 — never fatal to briefing assembly
            if raise_on_error:
                raise
            return []

    def _ledger_corruption(self, project: Path):
        """Return an exc describing a corrupt ledger, else None.

        `open_cards` tolerates malformed rows silently (returns []), so a fully
        corrupt ledger is indistinguishable from an empty one at that layer. We
        probe here so applies()/fragment() can surface corruption rather than
        omit the section.
        """
        ledger = project / "workspace" / "operator_proposals.jsonl"
        if not ledger.exists():
            return None
        try:
            raw = ledger.read_text(encoding="utf-8")
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            return exc
        rows = [ln for ln in raw.splitlines() if ln.strip()]
        if rows and not any(_is_json_object(ln) for ln in rows):
            import json as _json
            try:
                _json.loads(rows[0])
            except Exception as exc:  # noqa: BLE001
                return exc
        return None

    def applies(self, ctx: BriefingContext) -> bool:
        project = Path(getattr(ctx, "project_dir", "") or "")
        if self._ledger_corruption(project) is not None:
            return True  # corrupt ledger: reach fragment() to banner
        return bool(self._cards(project))

    def fragment(self, ctx: BriefingContext) -> str:
        project = Path(ctx.project_dir)
        corrupt = self._ledger_corruption(project)
        if corrupt is not None:
            return section_unavailable("OPERATOR PROPOSALS", corrupt)
        try:
            cards = self._cards(project, raise_on_error=True)
        except Exception as exc:  # noqa: BLE001 — corrupt/unreadable ledger → banner, not omission
            return section_unavailable("OPERATOR PROPOSALS", exc)
        if not cards:
            return ""
        lines = [_HEADER]
        for c in cards[:4]:
            wef = c.get("why_existing_ops_fail", {}) or {}
            fails = "; ".join(f"{op}: {reason}" for op, reason in list(wef.items())[:3])
            lines.append(
                f"- residual family `{c.get('failure_family', '?')}` "
                f"(evidence transitions {c.get('evidence_indices', [])[:6]}): "
                f"candidate {c.get('proposed_operator_sketch', '?')}. "
                f"why the catalog fails: {fails}. "
                f"acceptance test: {c.get('acceptance_test', '')}"
            )
        return "\n".join(lines) + "\n"
