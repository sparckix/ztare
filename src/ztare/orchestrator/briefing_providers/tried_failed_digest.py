"""Negative-space briefing provider for already-tried failures.

The R1 pattern provider covers a few tactical compiler-bounce classes. This
provider summarizes broader failed shapes from existing run artifacts:
R1 rejection reasons, mutation-contract mismatches, and fit failures. It is
externalized memory for the next worker, not a gate.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ztare.orchestrator.briefing_providers import section_unavailable
from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


_R1_REASON_RE = re.compile(
    r"\*\*Rejection reason:\*\*\s*```(.*?)```",
    re.DOTALL,
)


class TriedFailedDigestProvider(BriefingProvider):
    """Surface compact negative memory from prior attempts in this run."""

    name = "tried_failed_digest"
    priority = 19
    max_fragment_chars = 900
    # ponytail: control_plane=True — negative memory governs search direction.
    # Tier 2 already exempts from budget gate, but marking intent explicitly.
    control_plane = True

    def applies(self, ctx: BriefingContext) -> bool:
        if ctx.iter_index < 2:
            return False
        ws = _workspace(ctx)
        return any(
            path.exists()
            for path in (
                ws / "r1_debug",
                ws / "contract_violations.jsonl",
                ws / "eval_history.jsonl",
            )
        ) or any(ws.glob("fit_result_iter_*.json"))

    def fragment(self, ctx: BriefingContext) -> str:
        global _STRICT_READS, _CORRUPT_JSONL_ROWS
        ws = _workspace(ctx)
        bullets: list[str] = []
        _STRICT_READS = True
        _CORRUPT_JSONL_ROWS = 0
        try:
            bullets.extend(_r1_bullets(ws / "r1_debug", ctx.iter_index))
            bullets.extend(_contract_bullets(ws / "contract_violations.jsonl"))
            bullets.extend(_fit_bullets(ws))
            bullets.extend(_eval_bullets(ws / "eval_history.jsonl"))
            bullets.extend(_projection_constraint_bullets(ctx.project_dir))
            bullets.extend(_projection_frontier_bullets(ctx.project_dir))
            bullets.extend(_harness_weakness_bullets(ws / "harness_weakness_receipts.jsonl"))
            bullets.extend(_probe_row_bullets(ws / "strategy_experiment_probe_rows.jsonl"))
        except Exception as exc:  # noqa: BLE001 — unreadable artifact → banner, not omission
            return section_unavailable("TRIED-FAILED DIGEST", exc)
        finally:
            corrupt = _CORRUPT_JSONL_ROWS
            _STRICT_READS = False
        if not bullets:
            if corrupt:
                # Every row was corrupt: surface it, do not omit silently.
                return (
                    "## ⚠️  TRIED-FAILED DIGEST (DEGRADED)\n\n"
                    f"TRIED-FAILED DIGEST DEGRADED — {corrupt} corrupt/unparseable "
                    f"JSONL row(s) and no readable negative-memory bullets; "
                    f"prior guidance still in force\n\n"
                )
            return ""

        lines = [
            "## Tried-and-Failed Digest - negative memory from this run",
            "",
            "Do not re-emit these failed shapes unless your next mutation explicitly changes the failing mechanism.",
            "",
        ]
        for bullet in _dedupe(bullets)[:8]:
            lines.append(f"- {bullet}")
        if corrupt:
            lines.append(
                f"- NOTE: {corrupt} corrupt/unparseable JSONL row(s) skipped while "
                "building this digest."
            )
        # Axis 4: also surface machine-blocked experiment families so the mutator
        # cannot re-propose a killed failure_family that the office already pruned.
        try:
            from ztare.worldmodel.refuted_experiments import render_refuted_block
            _refuted = render_refuted_block(ctx.project_dir)
            if _refuted:
                lines.append("")
                lines.append(_refuted)
        except Exception:  # noqa: BLE001 — always degrade safely
            pass
        lines.append("")
        return "\n".join(lines)

    def structured_records(self, ctx: BriefingContext) -> list[dict[str, Any]]:
        records = _negative_constraint_records(ctx)
        return _dedupe_records(records)[:12]


def _workspace(ctx: BriefingContext) -> Path:
    return ctx.workspace_dir or (ctx.project_dir / "workspace")


def _negative_constraint_records(ctx: BriefingContext) -> list[dict[str, Any]]:
    ws = _workspace(ctx)
    records: list[dict[str, Any]] = []
    records.extend(_r1_records(ws / "r1_debug", ctx.iter_index))
    records.extend(_contract_records(ws / "contract_violations.jsonl"))
    records.extend(_fit_records(ws))
    records.extend(_eval_records(ws / "eval_history.jsonl"))
    records.extend(_projection_constraint_records(ctx.project_dir))
    records.extend(_projection_frontier_records(ctx.project_dir))
    return records


def _harness_weakness_bullets(path: Path) -> list[str]:
    """Surface recent harness weakness classes + recommended routes so the mutator
    knows which capability the kernel flagged for repair (Axis 6 dead-letter fix)."""
    rows = _read_jsonl(path)
    bullets: list[str] = []
    for row in rows[-4:]:
        wc = str(row.get("weakness_class") or "").strip()
        route = str(row.get("recommended_route") or row.get("route") or "").strip()
        cap = str(row.get("recommended_capability_id") or "").strip()
        if not wc:
            continue
        tail = f" → route={route}" if route else ""
        tail += f" capability={cap}" if cap else ""
        # The witness IS the feedback: without the exact mismatch the leaf
        # only learns "you failed", not WHERE the law breaks (cells, t,
        # action) — the one thing a deterministic gate knows better than
        # any judge.
        ce = row.get("counterexample") or {}
        fm = str(ce.get("first_mismatch") or "").strip()
        if fm:
            tail += f" | witness: {fm[:160]}"
        rt = ce.get("residual_table") or []
        if rt:
            # compact residual: the FULL function to fit, not one point —
            # (t,a)->cells, deduped, so the leaf sees which guesses moved rows
            cells = ", ".join(
                f"t{r.get('t')}a{r.get('action')}:{str(r.get('cells'))[:40]}"
                for r in rt[:8])
            tail += f" | residual({len(rt)} rows): {cells}"
        bullets.append(f"harness weakness: {wc}{tail}")
    return bullets[-2:]  # ponytail: cap at 2; full ledger in workspace


def _probe_row_bullets(path: Path) -> list[str]:
    """Surface recent strategy-experiment probe outcomes (Axis 6 dead-letter fix)."""
    rows = _read_jsonl(path)
    bullets: list[str] = []
    for row in rows[-6:]:
        kind = str(row.get("kind") or "").strip()
        status = str(row.get("status") or row.get("outcome") or "").strip()
        summary = _truncate(str(row.get("outcome_summary") or row.get("summary") or ""), 100)
        if not kind and not status:
            continue
        bullets.append(f"probe row: kind={kind} status={status}" + (f": {summary}" if summary else ""))
    return bullets[-2:]  # ponytail: cap at 2; full ledger in workspace


def _r1_bullets(r1_dir: Path, current_iter: int) -> list[str]:
    if not r1_dir.is_dir():
        return []
    bullets: list[str] = []
    for path in sorted(r1_dir.glob("iter_*_r1_attempts.md")):
        iter_no = _iter_from_name(path.name)
        if iter_no is None or iter_no >= current_iter:
            continue
        text = _read_text(path)
        for reason in _R1_REASON_RE.findall(text)[-2:]:
            summary = _summarize_reason(reason)
            if summary:
                bullets.append(f"R1 rejected iter {iter_no}: {summary}")
    return bullets[-4:]


def _r1_records(r1_dir: Path, current_iter: int) -> list[dict[str, Any]]:
    if not r1_dir.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(r1_dir.glob("iter_*_r1_attempts.md")):
        iter_no = _iter_from_name(path.name)
        if iter_no is None or iter_no >= current_iter:
            continue
        text = _read_text(path)
        for reason in _R1_REASON_RE.findall(text)[-2:]:
            summary = _summarize_reason(reason)
            if summary:
                records.append(
                    _record(
                        source_type="r1_rejection",
                        source_ref=str(path),
                        iteration=iter_no,
                        summary=summary,
                        action="change_contract_shape_before_retry",
                    )
                )
    return records[-4:]


def _contract_bullets(path: Path) -> list[str]:
    rows = _read_jsonl(path)
    bullets: list[str] = []
    for row in rows[-8:]:
        violations = row.get("violations") or []
        adheres = row.get("adheres")
        if adheres is True and not violations:
            continue
        if isinstance(violations, str):
            violations = [violations]
        if not isinstance(violations, list):
            violations = []
        codes = ", ".join(str(v) for v in violations[:4]) or "contract_mismatch"
        active = row.get("active_contract") or row.get("contract") or "unknown"
        iter_no = row.get("iter") or row.get("iteration") or "?"
        bullets.append(f"contract mismatch iter {iter_no} ({active}): {codes}")
    return bullets[-3:]


def _contract_records(path: Path) -> list[dict[str, Any]]:
    rows = _read_jsonl(path)
    records: list[dict[str, Any]] = []
    for row in rows[-8:]:
        violations = row.get("violations") or []
        adheres = row.get("adheres")
        if adheres is True and not violations:
            continue
        if isinstance(violations, str):
            violations = [violations]
        if not isinstance(violations, list):
            violations = []
        codes = ", ".join(str(v) for v in violations[:4]) or "contract_mismatch"
        active = row.get("active_contract") or row.get("contract") or "unknown"
        iter_no = row.get("iter") or row.get("iteration")
        records.append(
            _record(
                source_type="mutation_contract_mismatch",
                source_ref=str(path),
                iteration=_coerce_int(iter_no),
                summary=f"{active}: {codes}",
                action="satisfy_or_change_active_contract_before_retry",
            )
        )
    return records[-3:]


def _fit_bullets(workspace: Path) -> list[str]:
    bullets: list[str] = []
    for path in sorted(workspace.glob("fit_result_iter_*.json"))[-8:]:
        obj = _read_json(path)
        if not obj:
            continue
        status = str(obj.get("status") or "").lower()
        failure_class = obj.get("failure_class")
        if status == "success" and not failure_class:
            continue
        if not failure_class and status not in {"failure", "failed", "error"}:
            continue
        diag = str(obj.get("solver_diagnostics") or obj.get("error") or "")
        iter_no = _iter_from_name(path.name) or "?"
        tail = f": {_truncate(diag, 110)}" if diag else ""
        bullets.append(f"fit failure iter {iter_no}: {failure_class or status}{tail}")
    return bullets[-3:]


def _fit_records(workspace: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(workspace.glob("fit_result_iter_*.json"))[-8:]:
        obj = _read_json(path)
        if not obj:
            continue
        status = str(obj.get("status") or "").lower()
        failure_class = obj.get("failure_class")
        if status == "success" and not failure_class:
            continue
        if not failure_class and status not in {"failure", "failed", "error"}:
            continue
        diag = str(obj.get("solver_diagnostics") or obj.get("error") or "")
        iter_no = _iter_from_name(path.name)
        summary = str(failure_class or status)
        if diag:
            summary = f"{summary}: {_truncate(diag, 110)}"
        records.append(
            _record(
                source_type="fit_failure",
                source_ref=str(path),
                iteration=iter_no,
                summary=summary,
                action="change_fit_mechanism_or_diagnostic_boundary",
            )
        )
    return records[-3:]


def _eval_bullets(path: Path) -> list[str]:
    rows = _read_jsonl(path)
    if len(rows) < 2:
        return []
    bullets: list[str] = []
    best: float | None = None
    for row in rows[-8:]:
        score = _number(row.get("score"))
        weakest = str(row.get("weakest_point") or "").strip()
        if score is None:
            continue
        improved = best is None or score > best
        if best is None or score > best:
            best = score
        if improved or not weakest:
            continue
        iter_no = row.get("iteration") or "?"
        bullets.append(f"non-improving iter {iter_no}: {_truncate(weakest, 130)}")
    return bullets[-3:]


def _eval_records(path: Path) -> list[dict[str, Any]]:
    rows = _read_jsonl(path)
    if len(rows) < 2:
        return []
    records: list[dict[str, Any]] = []
    best: float | None = None
    for row in rows[-8:]:
        score = _number(row.get("score"))
        weakest = str(row.get("weakest_point") or "").strip()
        if score is None:
            continue
        improved = best is None or score > best
        if best is None or score > best:
            best = score
        if improved or not weakest:
            continue
        iter_no = _coerce_int(row.get("iteration"))
        records.append(
            _record(
                source_type="non_improving_eval",
                source_ref=str(path),
                iteration=iter_no,
                summary=_truncate(weakest, 130),
                action="exclude_or_alter_non_improving_mechanism",
            )
        )
    return records[-3:]


def _projection_constraint_bullets(project_dir: Path) -> list[str]:
    """Surface reusable failed-branch constraints from the read-only projection."""

    try:
        from ztare.validator.hypothesis_projection import build_projection

        projection = build_projection(project_dir)
    except Exception:
        return []
    bullets: list[str] = []
    for constraint in projection.negative_constraints[:4]:
        if constraint.count < 2 and not constraint.branch_cues:
            continue
        cues = ", ".join(constraint.branch_cues[:4])
        cue_text = f" branch cues [{cues}]" if cues else ""
        bullets.append(
            "negative constraint: "
            f"{constraint.failure_signature!r} recurred {constraint.count}x"
            f"{cue_text}; exclude or alter this mechanism before revisiting. "
            f"Example: {_truncate(constraint.example_weakest_point, 120)}"
        )
    return bullets[-3:]


def _projection_constraint_records(project_dir: Path) -> list[dict[str, Any]]:
    try:
        from ztare.validator.hypothesis_projection import build_projection

        projection = build_projection(project_dir)
    except Exception:
        return []
    records: list[dict[str, Any]] = []
    for constraint in projection.negative_constraints[:4]:
        if constraint.count < 2 and not constraint.branch_cues:
            continue
        records.append(
            _record(
                source_type="projection_negative_constraint",
                source_ref=str(project_dir / "workspace" / "eval_history.jsonl"),
                iteration=None,
                summary=constraint.example_weakest_point,
                action="exclude_or_alter_repeated_failed_branch",
                failure_signature=constraint.failure_signature,
                count=constraint.count,
                branch_cues=constraint.branch_cues[:4],
                node_ids=constraint.node_ids,
            )
        )
    return records[-3:]


def _projection_frontier_bullets(project_dir: Path) -> list[str]:
    """Surface the unresolved critique on the current admitted frontier."""

    try:
        from ztare.validator.hypothesis_projection import build_projection

        projection = build_projection(project_dir)
    except Exception:
        return []
    bullets: list[str] = []
    for constraint in projection.open_frontier_constraints[:1]:
        if not constraint.failure_signature:
            continue
        bullets.append(
            "frontier constraint: "
            f"{constraint.failure_signature!r}; the accepted spine is still open here. "
            f"Change the mechanism or evidence boundary before polishing this branch. "
            f"Example: {_truncate(constraint.example_weakest_point, 140)}"
        )
    return bullets


def _projection_frontier_records(project_dir: Path) -> list[dict[str, Any]]:
    try:
        from ztare.validator.hypothesis_projection import build_projection

        projection = build_projection(project_dir)
    except Exception:
        return []
    records: list[dict[str, Any]] = []
    for constraint in projection.open_frontier_constraints[:1]:
        if not constraint.failure_signature:
            continue
        records.append(
            _record(
                source_type="projection_frontier_constraint",
                source_ref=str(project_dir / "workspace" / "eval_history.jsonl"),
                iteration=None,
                summary=constraint.example_weakest_point,
                action="change_mechanism_or_evidence_boundary",
                failure_signature=constraint.failure_signature,
                count=constraint.count,
                branch_cues=constraint.branch_cues,
                node_ids=constraint.node_ids,
            )
        )
    return records


def _record(
    *,
    source_type: str,
    source_ref: str,
    iteration: int | None,
    summary: str,
    action: str,
    failure_signature: str | None = None,
    count: int = 1,
    branch_cues: list[str] | None = None,
    node_ids: list[str] | None = None,
) -> dict[str, Any]:
    clean_summary = _truncate(summary, 180)
    return {
        "record_type": "negative_constraint",
        "source_type": source_type,
        "source_ref": source_ref,
        "iteration": iteration,
        "failure_signature": failure_signature or _signature(clean_summary),
        "summary": clean_summary,
        "count": count,
        "branch_cues": branch_cues or [],
        "node_ids": node_ids or [],
        "action_constraint": action,
    }


# Strict-read state for the fragment() pass. When _STRICT_READS is on, the
# read helpers propagate OSError (top-level unreadable artifact -> banner) and
# count corrupt JSONL rows into _CORRUPT_JSONL_ROWS so the digest can NAME how
# many rows it skipped instead of silently dropping them. The structured-record
# path leaves this OFF and keeps the lenient empty-on-error behaviour.
# ponytail: module globals, set/reset around one fragment() call — briefing
# assembly is single-threaded; make these threadlocals if that ever changes.
_STRICT_READS = False
_CORRUPT_JSONL_ROWS = 0


def _read_json(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        if _STRICT_READS:
            raise
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    global _CORRUPT_JSONL_ROWS
    rows: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        if _STRICT_READS:
            raise
        return []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            if _STRICT_READS:
                _CORRUPT_JSONL_ROWS += 1  # count corrupt row, name it in fragment
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        if _STRICT_READS:
            raise
        return ""


def _iter_from_name(name: str) -> int | None:
    match = re.search(r"iter_0*(\d+)", name)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _summarize_reason(reason: str) -> str:
    reason = re.sub(r"\s+", " ", reason).strip()
    if not reason:
        return ""
    return _truncate(reason, 150)


def _truncate(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _signature(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return " ".join(words[:12])


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _dedupe_records(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = (
            str(item.get("source_type") or ""),
            str(item.get("failure_signature") or ""),
            str(item.get("action_constraint") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
