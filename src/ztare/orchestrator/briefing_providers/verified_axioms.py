"""WAR-T5 (2026-04-27): Verified-Axiom briefing provider — Sacred DNA.

When a project's `verified_axioms.json` contains an axiom whose
`status == "verified_axiom"` and `successor_lock.active == true`, this
provider surfaces it to every iter as a permanent constraint. The
mutator must produce algebraic descendants of the locked form, not
discard it.

This closes the gp163d run_id 1777250273 failure mode: iter 8 produced a
breakthrough form bridging Class A + Class B, capped to 50; iter 9
threw the form away because its briefing carried no successor lock.

Substrate-agnostic. Reads `<project_dir>/verified_axioms.json` only —
no rubric coupling.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
)


class VerifiedAxiomsProvider(BriefingProvider):
    name = "verified_axioms"
    priority = 50  # render very early — before forced_reframe and cold-LLM

    def _load(self, ctx: BriefingContext) -> list[dict]:
        path = ctx.project_dir / "verified_axioms.json"
        if not path.exists():
            return []
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if isinstance(blob, list):
            return [a for a in blob if isinstance(a, dict)]
        if isinstance(blob, dict):
            axioms = blob.get("axioms")
            if isinstance(axioms, list):
                return [a for a in axioms if isinstance(a, dict)]
        return []

    def applies(self, ctx: BriefingContext) -> bool:
        for ax in self._load(ctx):
            if ax.get("status") == "verified_axiom":
                lock = ax.get("successor_lock") or {}
                if lock.get("active"):
                    return True
        return False

    def fragment(self, ctx: BriefingContext) -> str:
        active = [
            a for a in self._load(ctx)
            if a.get("status") == "verified_axiom"
            and (a.get("successor_lock") or {}).get("active")
        ]
        if not active:
            return ""
        parts = [
            "## VERIFIED AXIOMS (Sacred DNA — successor lock active)",
            "",
            "Forms below have been verified out-of-band against the substrate ",
            "and locked as ground truth. Any submission this iter MUST be an ",
            "algebraic descendant of the locked form unless the prose offers ",
            "a one-paragraph justification AND the new form beats the locked ",
            "form's raw judge score on the in-scope classes.",
            "",
        ]
        for ax in active:
            parts.append(f"### {ax.get('name', ax.get('axiom_id', 'unnamed'))}")
            scope = ax.get("scope")
            if scope:
                parts.append(f"**Scope**: {scope}")
            claim = ax.get("claim")
            if claim:
                parts.append(f"**Claim**: {claim}")
            human = ax.get("form_human_readable")
            if human:
                parts.append(f"**Form**: `{human}`")
            params = ax.get("parameters") or {}
            if params:
                pstr = ", ".join(f"{k}={v}" for k, v in params.items())
                parts.append(f"**Fitted parameters**: {pstr}")
            ev = ax.get("evidence") or {}
            if ev:
                ev_summary_lines = []
                for k, v in ev.items():
                    if k.endswith("_pass") and isinstance(v, bool):
                        continue
                    if k.endswith("_threshold"):
                        continue
                    if isinstance(v, (int, float, str, bool)):
                        ev_summary_lines.append(f"  - {k}: {v}")
                if ev_summary_lines:
                    parts.append("**Evidence**:")
                    parts.extend(ev_summary_lines[:10])  # cap at 10 lines
            lock = ax.get("successor_lock") or {}
            rule = lock.get("rule")
            if rule:
                parts.append(f"\n**Successor-lock rule**: {rule}")
            caveats = ax.get("caveats") or []
            if caveats:
                parts.append("\n**Open frontiers (where the bridge does NOT yet hold)**:")
                for c in caveats[:6]:
                    parts.append(f"  - {c}")
            next_steps = ax.get("next_steps") or []
            if next_steps:
                parts.append("\n**Newton tasks (what the next iter should attempt)**:")
                for s in next_steps[:6]:
                    parts.append(f"  - {s}")
            # WAR-T6 follow-up: surface external consistency checks (e.g.
            # NFW degeneracy probe verdict) so the next iter knows the
            # bridge has been independently differentiated from competing
            # explanations. Otherwise the mutator is blind to where the
            # bridge has already been stress-tested.
            ext_checks = ax.get("external_consistency_checks") or {}
            if ext_checks:
                parts.append("\n**External consistency checks (independently verified)**:")
                for check_name, check_blob in ext_checks.items():
                    if not isinstance(check_blob, dict):
                        continue
                    verdict = check_blob.get("verdict") or "(no verdict)"
                    interp = check_blob.get("interpretation") or ""
                    parts.append(f"  - **{check_name}**: {verdict}")
                    if interp:
                        # truncate to keep briefing tight
                        parts.append(f"    {interp[:300]}{'...' if len(interp) > 300 else ''}")
            data_conv = ax.get("data_convention_notes") or {}
            if data_conv:
                parts.append("\n**Data conventions to know**:")
                for key, note in data_conv.items():
                    if isinstance(note, str):
                        parts.append(f"  - **{key}**: {note}")
            parts.append("")
        parts.append(
            "Default this iter: extend or refine the locked form. "
            "Discarding it requires explicit prose justification."
        )
        parts.append("")
        return "\n".join(parts)
