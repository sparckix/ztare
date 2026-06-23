"""GP-166 Contamination Defense Briefing — surfaces .denylist hits to
the mutator so it knows which forbidden term tripped the gate.

Background: substrates with cold-LLM null framing carry a `.denylist`
file naming canonical theory keywords (e.g. "MOND", "Milgrom",
"SPARC", "rotation curve"). The `global_named_import_check` gate
hard-fails any iter whose thesis text mentions a denylist term —
this is the contamination defense that ensures the mutator is
abducting from data, not reciting from training-data priors.

Problem before this provider existed: the gate fires silently from
the mutator's perspective. It sees its iter zeroed but doesn't know
WHICH word triggered it. So next iter it reuses similar language and
hits the gate again. The contamination feedback loop is broken.

This provider scans the previous iter's submitted thesis (saved in
`workspace/submissions/iter_NNN_*.md` — the most recent one) against
the project's `.denylist` (or `.thesis_denylist` if present) and
surfaces the hits with explicit guidance: "remove these terms;
re-derive the same structural argument from anonymized data alone."

Engagement: applies whenever a `.denylist` (or `.thesis_denylist`)
file exists in the project dir AND a previous-iter submission exists.
Skips quietly otherwise.
"""
from __future__ import annotations

import re
from pathlib import Path

from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


class ContaminationDefenseBriefingProvider(BriefingProvider):
    """Surfaces .denylist hits found in the previous iter's thesis."""

    name = "contamination_defense"
    priority = 240  # right after fit_telemetry (200) / noise_profile (220)

    def applies(self, ctx: BriefingContext) -> bool:
        if ctx.workspace_dir is None or ctx.project_dir is None:
            return False
        # Need either .thesis_denylist or .denylist
        if not (
            (ctx.project_dir / ".thesis_denylist").exists()
            or (ctx.project_dir / ".denylist").exists()
        ):
            return False
        # Need at least one prior submission
        sub_dir = ctx.workspace_dir / "submissions"
        if not sub_dir.exists():
            return False
        return any(sub_dir.glob("iter_*_*.md"))

    def fragment(self, ctx: BriefingContext) -> str:
        # Load denylist (.thesis_denylist takes priority, sentinel-safer
        # by design per global_gates.py)
        denylist_path = ctx.project_dir / ".thesis_denylist"
        if not denylist_path.exists():
            denylist_path = ctx.project_dir / ".denylist"
        try:
            terms = [
                line.strip()
                for line in denylist_path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
        except Exception:
            return ""
        if not terms:
            return ""

        # Find the most recent submission
        sub_dir = ctx.workspace_dir / "submissions"
        try:
            subs = sorted(
                sub_dir.glob("iter_*_*.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except Exception:
            return ""
        if not subs:
            return ""
        latest = subs[0]
        try:
            text = latest.read_text(encoding="utf-8")
        except Exception:
            return ""

        # Scan: case-insensitive whole-word match; record line numbers for
        # surgical-edit guidance.
        hits: dict[str, list[int]] = {}
        lines_text = text.splitlines()
        for term in terms:
            # Build a regex with word boundaries unless the term contains
            # spaces (in which case it's a phrase — match literally).
            if re.search(r"\s", term):
                pattern = re.compile(re.escape(term), re.IGNORECASE)
            else:
                pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            line_hits: list[int] = []
            for i, line in enumerate(lines_text, start=1):
                if pattern.search(line):
                    line_hits.append(i)
            if line_hits:
                hits[term] = line_hits

        if not hits:
            return ""  # clean iter — no need to surface anything

        out: list[str] = []
        out.append("## Contamination Defense (GP-166)")
        out.append("")
        out.append(
            "The previous iter's thesis named **forbidden terms** from this "
            "project's `.denylist`. The `global_named_import_check` gate "
            "hard-fails any iter whose thesis prose contains these terms "
            "(domain priors leaking from training data → not blind "
            "abduction). The hits this iter:"
        )
        out.append("")
        for term, line_nums in sorted(hits.items()):
            out.append(f"  - `{term}` on line(s) {line_nums[:5]}"
                       + (f" + {len(line_nums) - 5} more" if len(line_nums) > 5 else ""))
        out.append("")
        out.append(
            "**To make progress on this substrate, do not name the canonical "
            "theory.** Restate the same structural argument using the "
            "anonymized feature names this substrate exposes (`x`, "
            "`mass_log10`, `radius_log10`, `system_class`). The Newton-step "
            "claim must come from the data's asymptotic structure, not from "
            "theoretical labels. If you cannot articulate the form without "
            "naming the theory, that itself is evidence the form is recital, "
            "not abduction."
        )
        out.append("")

        return "\n".join(out)
