"""IterTrajectoryProvider — multi-iter form/score history.

The mutator currently sees only the LAST iter's weakest_point. For
multi-iter exploration, this provider summarizes the last K iters
(default 5) so the mutator can recognize when it's tried multiple
forms in the same family and needs to escape the basin.

Reads `workspace/iteration_telemetry.jsonl` (already written every
iter) and `workspace/submissions/iter_NNN_*.py` for forms.
Substrate-agnostic.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from ztare.orchestrator.briefing_providers import section_unavailable
from ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
)


class IterTrajectoryProvider(BriefingProvider):
    name = "iter_trajectory"
    priority = 300
    LOOKBACK = 5  # number of prior iters to summarize

    # FIX E: how many bytes to seek from the end for tail-read; 8 KB covers
    # ~50 typical JSONL rows (each ~160 bytes). Doubled on retry if K lines
    # not found.  ponytail: constant ceiling — add if rows grow beyond ~4KB each.
    _TAIL_BYTES = 8192

    @staticmethod
    def _tail_lines(path: Path, k: int, encoding: str = "utf-8") -> list[str]:
        """Return the last `k` non-empty lines by seeking from the file end.

        Falls back to full read when the file is smaller than the seek window.
        Raises OSError / UnicodeDecodeError on file-level failures (callers handle).
        """
        size = path.stat().st_size
        window = IterTrajectoryProvider._TAIL_BYTES
        # Double the window until we're confident we have k lines, up to full file.
        while True:
            seek_pos = max(0, size - window)
            with path.open("rb") as f:
                f.seek(seek_pos)
                raw = f.read()
            text = raw.decode(encoding, errors="replace")
            # If we seeked mid-line, drop the partial first line.
            if seek_pos > 0:
                nl = text.find("\n")
                text = text[nl + 1:] if nl != -1 else ""
            lines = [l for l in text.splitlines() if l.strip()]
            if len(lines) >= k or seek_pos == 0:
                return lines[-k:] if len(lines) >= k else lines
            # Not enough lines and we haven't reached the start — widen window.
            window = min(window * 4, size)

    def _load_telemetry_lines(self, ctx: BriefingContext) -> list[dict]:
        path = (ctx.workspace_dir or ctx.project_dir / "workspace") / "iteration_telemetry.jsonl"
        if not path.exists():
            return []
        out = []
        try:
            # FIX E: tail-read last LOOKBACK lines only
            for line in self._tail_lines(path, self.LOOKBACK):
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except Exception:
            return []
        return out

    def _load_eval_history_lines(self, ctx: BriefingContext) -> tuple[list[dict], list[int]]:
        """Return (parsed rows, 1-based line numbers of corrupt rows skipped).

        File-level read/decode failures PROPAGATE (so fragment() can banner
        the section instead of silently omitting it); only per-line JSON
        corruption is tolerated, and those rows are counted/named.

        FIX E: tail-reads last LOOKBACK lines via seek-from-end; skipped line
        numbers are relative to the tail window (the consumer only cares that
        some rows were corrupt, not their absolute position in the full file).
        """
        path = (ctx.workspace_dir or ctx.project_dir / "workspace") / "eval_history.jsonl"
        if not path.exists():
            return [], []
        out: list[dict] = []
        skipped: list[int] = []
        tail = self._tail_lines(path, self.LOOKBACK)
        for i, line in enumerate(tail, start=1):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                skipped.append(i)
        return out, skipped

    def _extract_form_summary(self, py_path: Path) -> str:
        """Extract a short form summary from a saved submission .py file.

        Uses the shared AST-based extractor so multi-line implicit-
        concatenation PARAMETRIC_FORM strings resolve correctly.
        """
        try:
            txt = py_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""
        try:
            from ztare.orchestrator.forced_reframe import (
                extract_parametric_form_from_source as _extract_form,
            )
        except ImportError:
            return ""
        form = _extract_form(txt) or ""
        if len(form) > 100:
            form = form[:100] + "..."
        return form

    def applies(self, ctx: BriefingContext) -> bool:
        path = (ctx.workspace_dir or ctx.project_dir / "workspace") / "eval_history.jsonl"
        if not path.exists():
            return False
        try:
            eh, skipped = self._load_eval_history_lines(ctx)
        except Exception:
            # Corrupt/unreadable history: let fragment() run so it renders an
            # explicit UNAVAILABLE banner rather than silently omitting.
            return True
        # Too few rows because every row was corrupt must still reach fragment()
        # (to surface the corruption), not be silently declined as "no history."
        return len(eh) >= 2 or bool(skipped)

    def fragment(self, ctx: BriefingContext) -> str:
        try:
            eh, skipped = self._load_eval_history_lines(ctx)
        except Exception as exc:
            return section_unavailable("ITER TRAJECTORY", exc)
        if len(eh) < 2:
            if skipped:
                return (
                    "## ⚠️  ITER TRAJECTORY (DEGRADED)\n\n"
                    f"ITER TRAJECTORY DEGRADED — {len(skipped)} corrupt row(s) in "
                    f"eval_history.jsonl (line(s) {skipped[:10]}) and fewer than 2 "
                    f"readable prior iters; prior guidance still in force\n\n"
                )
            return ""

        recent = eh[-self.LOOKBACK:]
        ws_subs = (ctx.workspace_dir or ctx.project_dir / "workspace") / "submissions"

        lines = [
            "\n    ### ITER TRAJECTORY (last "
            f"{len(recent)} iters — read before re-using a structural family)\n",
        ]
        if skipped:
            lines.append(
                f"    NOTE: {len(skipped)} corrupt row(s) in eval_history.jsonl "
                f"skipped (line(s) {skipped[:10]}"
                + (f" + {len(skipped) - 10} more" if len(skipped) > 10 else "")
                + "); trajectory below may be incomplete.\n"
            )
        for i, e in enumerate(recent):
            score = e.get("score", "?")
            # 2026-04-27: surface raw judge score when it differs
            # from the capped score. Without this annotation, a capped
            # breakthrough (raw 100 → capped 50) is indistinguishable from
            # a true plateau iter at score 50. The next iter's mutator
            # needs the latent-gradient signal explicitly.
            raw_score = e.get("raw_judge_score")
            cap_reason = e.get("score_cap_reason")
            score_str = f"score={score}"
            if raw_score is not None and isinstance(score, (int, float)) and raw_score != score:
                if cap_reason:
                    score_str = f"score={score} (RAW {raw_score}, capped: {cap_reason})"
                else:
                    score_str = f"score={score} (RAW {raw_score}, capped)"
            wp = (e.get("weakest_point") or "")[:80].replace("\n", " ")
            # find a saved submission .py for this iter
            iter_idx = e.get("iter") or e.get("iteration")
            form_summary = ""
            if iter_idx is not None and ws_subs.exists():
                try:
                    matches = sorted(ws_subs.glob(f"iter_{iter_idx:03d}_*.py"))
                    if matches:
                        form_summary = self._extract_form_summary(matches[-1])
                except Exception:
                    pass
            lines.append(
                f"    iter {iter_idx if iter_idx is not None else '?'}: "
                f"{score_str}"
                + (f", form='{form_summary}'" if form_summary else "")
                + (f", weakest_point: {wp}" if wp else "")
            )

        # Pattern-detection: if recent scores cluster near 0 and forms are
        # similar shape, hint at basin-lock without prescribing a fix.
        scores = [e.get("score") or 0 for e in recent]
        zero_runs = sum(1 for s in scores if s == 0)
        if len(recent) >= 3 and zero_runs == len(recent):
            lines.append(
                "\n    PATTERN: all recent iters scored 0. The structural "
                "family you have been refining has not produced a passing "
                "form. Consider whether you have been adding parameters to "
                "the same skeleton vs. exploring a different structural "
                "family. Both are valid; the trajectory shows which you "
                "have been doing."
            )
        elif len(recent) >= 3 and len(set(scores[-3:])) == 1:
            lines.append(
                "\n    PATTERN: last 3 iters scored identically. The "
                "apparatus is converging to the same fit each iter — your "
                "form may be deterministic given the data, or you are "
                "re-submitting the same form. Either way, the next iter "
                "should change the structural family or the parameter "
                "count, not the constants."
            )

        return "\n".join(lines) + "\n"
