"""R1 pattern warning briefing provider.

Reads r1_debug/iter_NNN_r1_attempts.md from prior iters in the current run,
extracts recurring failure classes, and injects a compact warning block so the
mutator does not repeat the same R1 class it already bounced on.

Priority 18 — renders before contract_rules (20) so the live-run failure record
appears first, right at the top of the briefing.

Applies only when iter_index ≥ 2 (iter-1 has no prior r1_debug/ to read) and
when at least one R1 pattern was observed.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider

# ── Pattern classifiers ──────────────────────────────────────────────────────

_DENYLIST_RE = re.compile(
    r"denylist terms.*?\[([^\]]+)\]", re.IGNORECASE
)
_IMODEL_CALL_RE = re.compile(
    r"module-level i_model.*?call detected", re.IGNORECASE
)
_RECURSION_RE = re.compile(
    r"recursionerror", re.IGNORECASE
)
_PINT_RE = re.compile(
    r"pint\s+unitregistry|not defined as dimension in the pint", re.IGNORECASE
)
_PARAMETRIC_RE = re.compile(
    r"PARAMETRIC_FORM.*?syntaxerror|PARAMETRIC_FORM AST/whitelist pre-flight FAILED",
    re.IGNORECASE,
)
_IMODEL_QUALITATIVE_RE = re.compile(
    r"qualitative.*?I_model|I_model.*?qualitative|require_i_model.*?false",
    re.IGNORECASE,
)


def _extract_rejection_reasons(md_text: str) -> list[str]:
    """Pull the raw text inside each ``` block after 'Rejection reason:'."""
    reasons = []
    for m in re.finditer(
        r"\*\*Rejection reason:\*\*\s*```(.*?)```",
        md_text,
        re.DOTALL,
    ):
        reasons.append(m.group(1).strip())
    return reasons


def _parse_r1_file(path: Path) -> dict:
    """Return a dict of pattern → count for one iter's R1 attempts file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    reasons = _extract_rejection_reasons(text)
    counts: dict[str, int] = {}
    denylist_terms: set[str] = set()

    for r in reasons:
        if _DENYLIST_RE.search(r):
            m = _DENYLIST_RE.search(r)
            if m:
                raw = m.group(1)
                terms = [t.strip().strip("'\"") for t in raw.split(",")]
                denylist_terms.update(t for t in terms if t)
            counts["denylist"] = counts.get("denylist", 0) + 1
        if _IMODEL_CALL_RE.search(r):
            counts["imodel_call"] = counts.get("imodel_call", 0) + 1
        if _RECURSION_RE.search(r):
            counts["recursion"] = counts.get("recursion", 0) + 1
        if _PINT_RE.search(r):
            counts["pint"] = counts.get("pint", 0) + 1
        if _PARAMETRIC_RE.search(r):
            counts["parametric_form"] = counts.get("parametric_form", 0) + 1

    if denylist_terms:
        counts["_denylist_terms"] = list(denylist_terms)  # type: ignore[assignment]
    return counts


def _aggregate_r1_patterns(r1_debug_dir: Path, current_iter: int) -> dict:
    """Aggregate R1 patterns across all prior iters (iter < current_iter)."""
    totals: dict[str, int] = {}
    all_denylist: set[str] = set()

    for i in range(1, current_iter):
        candidate = r1_debug_dir / f"iter_{i:03d}_r1_attempts.md"
        if not candidate.exists():
            # Try without zero-padding (legacy naming)
            candidate = r1_debug_dir / f"iter_{i}_r1_attempts.md"
        if not candidate.exists():
            continue
        counts = _parse_r1_file(candidate)
        for k, v in counts.items():
            if k == "_denylist_terms":
                all_denylist.update(v)  # type: ignore[arg-type]
            else:
                totals[k] = totals.get(k, 0) + int(v)

    if all_denylist:
        totals["_denylist_terms"] = list(all_denylist)  # type: ignore[assignment]
    return totals


class R1PatternWarningProvider(BriefingProvider):
    """Inject live R1 failure history from this run into the briefing."""

    name = "r1_pattern_warning"
    priority = 18  # before contract_rules (20)

    def applies(self, ctx: BriefingContext) -> bool:
        if ctx.iter_index < 2:
            return False
        r1_dir = ctx.project_dir / "workspace" / "r1_debug"
        return r1_dir.is_dir()

    def fragment(self, ctx: BriefingContext) -> str:
        r1_dir = ctx.project_dir / "workspace" / "r1_debug"
        patterns = _aggregate_r1_patterns(r1_dir, ctx.iter_index)
        if not patterns or all(k.startswith("_") for k in patterns):
            return ""

        lines: list[str] = []
        lines.append("## ⚠️ R1 Pattern Warning — live failures from this run")
        lines.append("")
        lines.append(
            "The following R1 failure classes have already fired earlier in THIS run. "
            "Each one burned expensive tokens. DO NOT repeat them."
        )
        lines.append("")
        lines.append("```")

        if "denylist" in patterns:
            terms = patterns.get("_denylist_terms", [])
            terms_str = ", ".join(f"`{t}`" for t in sorted(terms)) if terms else "(see .thesis_denylist)"
            lines.append(
                f"DENYLIST-R1 ({patterns['denylist']}x): terms {terms_str} "
                "appeared in thesis prose → immediate R1. Do NOT use these words anywhere in your output."
            )

        if "imodel_call" in patterns:
            lines.append(
                f"I_MODEL-CALL-R1 ({patterns['imodel_call']}x): module-level I_model(...) call detected. "
                "Any call at module scope → R1. Keep ALL I_model(...) calls inside `if __name__ == '__main__':` or test functions."
            )

        if "pint" in patterns:
            lines.append(
                f"PINT-R1 ({patterns['pint']}x): `pint` is not allowed — it is not stdlib. "
                "Use `math` for unit arithmetic, no third-party unit libraries."
            )

        if "parametric_form" in patterns:
            lines.append(
                f"PARAMETRIC_FORM-R1 ({patterns['parametric_form']}x): PARAMETRIC_FORM had SyntaxError or pseudo-code. "
                "On qualitative substrates: DO NOT write PARAMETRIC_FORM at all. "
                "On numeric substrates: PARAMETRIC_FORM must be pure Python expression syntax."
            )

        if "recursion" in patterns:
            lines.append(
                f"RECURSION-R1 ({patterns['recursion']}x): RecursionError at module import time. "
                "Do NOT define recursive functions that call themselves at module scope. "
                "Move any recursive logic inside `if __name__ == '__main__':` guards."
            )

        lines.append("```")
        lines.append("")
        return "\n".join(lines) + "\n"
