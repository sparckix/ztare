"""META-GATE 2C — Post-run LLM diagnostic auditor.

When a run caps below the Newton-step threshold (or otherwise stalls),
a cross-family LLM reads the run trace and produces an apparatus-side
meta-audit identifying what detection would have moved the needle.

This is the apparatus-side mechanization of the offline workflow that
diagnosed gp163d's 50-cap ceiling: a separate LLM reads
`eval_history.jsonl + cage_engagement.jsonl + substrate_critique.json
+ iteration_telemetry.jsonl`, identifies the persistent failure mode,
and answers four targeted questions:

  1. What was the run's cap pattern?
  2. Which gates engaged but didn't flag despite the cap?
  3. What apparatus-side detection would have moved the needle?
  4. Was a related gate present but scoped too narrowly?

Cross-family hygiene: default model is `claude-haiku-4-5` (cheap +
cross-family from typical gpt/gemini mutators). Operator can override
via rubric `meta_audit_model_id`.

Cost contract (degraded-mode, fail-graceful):
  * 30s wall-clock timeout
  * ~5K input tokens (trace excerpts pre-truncated)
  * ~2K output tokens
  * On any failure: log a warning, return an empty verdict; the run
    completes normally.

Output:
  * Structured dict returned to caller
  * `workspace/post_run_meta_audit.md` for operator inspection
  * `workspace/post_run_meta_audit.json` raw record

The audit is a PROPOSAL — the operator decides whether to act on the
recommendations.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class PostRunMetaAuditVerdict:
    attempted: bool = False
    succeeded: bool = False
    cap_pattern: str = ""
    gates_engaged_not_flagged: list[str] = field(default_factory=list)
    detection_recommendations: list[str] = field(default_factory=list)
    narrow_scoped_gate: Optional[dict] = None
    raw_response: str = ""
    model_id_used: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    error: Optional[str] = None
    artifact_path: Optional[str] = None
    artifact_path_md: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "cap_pattern": self.cap_pattern,
            "gates_engaged_not_flagged": self.gates_engaged_not_flagged,
            "detection_recommendations": self.detection_recommendations,
            "narrow_scoped_gate": self.narrow_scoped_gate,
            "model_id_used": self.model_id_used,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "error": self.error,
            "raw_response_excerpt": self.raw_response[:2000],
            "artifact_path": self.artifact_path,
            "artifact_path_md": self.artifact_path_md,
        }


# ── Trace readers ─────────────────────────────────────────────────────


def _read_jsonl(path: Path, max_records: int = 50) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    out.append(json.loads(ln))
                except json.JSONDecodeError:
                    continue
                if len(out) >= max_records:
                    break
    except OSError:
        return []
    return out


def _read_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _summarize_eval_history(records: list[dict]) -> dict:
    if not records:
        return {"n_iters": 0, "scores": [], "max_score": None, "weakest_points": []}
    scores = [int(r.get("score", 0)) for r in records]
    weakest = [
        {"iter": r.get("iteration"), "score": r.get("score"), "weakest_point": (r.get("weakest_point") or "")[:240]}
        for r in records
    ]
    return {
        "n_iters": len(records),
        "scores": scores,
        "max_score": max(scores) if scores else None,
        "min_score": min(scores) if scores else None,
        "final_score": scores[-1] if scores else None,
        "weakest_points": weakest,
    }


def _summarize_cage_engagement(records: list[dict]) -> dict:
    if not records:
        return {"n_iters": 0, "engaged_gates_union": [], "skipped_gates_union": []}
    engaged_union: set[str] = set()
    skipped_union: set[str] = set()
    for r in records:
        for g in r.get("engaged", []) or []:
            engaged_union.add(str(g))
        engagements = r.get("engagements", {}) or {}
        for gname, ginfo in engagements.items():
            if isinstance(ginfo, dict) and not ginfo.get("ok", False):
                skipped_union.add(str(gname))
    return {
        "n_iters": len(records),
        "engaged_gates_union": sorted(engaged_union),
        "skipped_gates_union": sorted(skipped_union),
        "first_iter_engagement": records[0].get("engaged", []) if records else [],
    }


def _summarize_substrate_critique(critique: Optional[dict]) -> dict:
    if not critique:
        return {"present": False}
    out: dict[str, Any] = {
        "present": True,
        "classes_visible": critique.get("classes_visible", []),
        "classes_withheld": critique.get("classes_withheld", []),
        "n_invariants": len(critique.get("substrate_invariants", []) or []),
        "feature_dimensionality_collapses": critique.get("feature_dimensionality_collapses", []),
        "withheld_class_feature_collapses": critique.get("withheld_class_feature_collapses", []),
        "cross_class_joint_form_blockers": critique.get("cross_class_joint_form_blockers", []),
        "cross_class_signal_keys": [
            s.get("feature_key") for s in (critique.get("cross_class_signal", []) or [])
        ],
        "regime_breaks_in_data": critique.get("regime_breaks_in_data", []),
        "data_artifacts_suspected": critique.get("data_artifacts_suspected", []),
        "epistemic_voids": critique.get("epistemic_voids", []),
    }
    return out


def _summarize_iteration_telemetry(records: list[dict]) -> dict:
    if not records:
        return {"n_records": 0}
    iter_records = [r for r in records if r.get("record_type") == "iteration"]
    failed_gates_union: set[str] = set()
    stagnation_max = 0
    for r in iter_records:
        for g in r.get("failed_gate_ids", []) or []:
            failed_gates_union.add(str(g))
        sc = int(r.get("stagnation_count", 0) or 0)
        if sc > stagnation_max:
            stagnation_max = sc
    return {
        "n_iter_records": len(iter_records),
        "failed_gate_ids_union": sorted(failed_gates_union),
        "max_stagnation_count": stagnation_max,
        "loop_control_actions": [r.get("loop_control_action") for r in iter_records],
    }


# ── Prompt construction ───────────────────────────────────────────────


def _build_meta_audit_prompt(
    *,
    project: str,
    run_id: Optional[str],
    eval_summary: dict,
    cage_summary: dict,
    critique_summary: dict,
    iter_summary: dict,
    newton_threshold: int = 90,
) -> str:
    """Render the audit prompt. Strictly trace-side; the LLM is told
    nothing about the substrate's domain semantics — it sees gate names,
    score sequences, structural critique flags."""
    payload = {
        "project": project,
        "run_id": run_id,
        "newton_threshold": newton_threshold,
        "eval_history_summary": eval_summary,
        "cage_engagement_summary": cage_summary,
        "substrate_critique_summary": critique_summary,
        "iteration_telemetry_summary": iter_summary,
    }
    payload_json = json.dumps(payload, indent=2, default=str)
    # Bound prompt size
    if len(payload_json) > 18000:
        payload_json = payload_json[:18000] + "\n... [TRUNCATED]"

    return (
        "You are an APPARATUS-SIDE diagnostic auditor for a symbolic-regression "
        "research loop. A run has completed. You receive ONLY the trace summary — "
        "you have no knowledge of the substrate's domain semantics. Your job is to "
        "diagnose what apparatus-side detection would have moved the needle.\n\n"
        "RUN TRACE SUMMARY (JSON):\n"
        f"{payload_json}\n\n"
        f"Newton-step threshold = {newton_threshold}. If max_score < threshold, "
        "the run capped below convergence.\n\n"
        "Answer the four questions below. Be terse, concrete, and SPECIFIC about "
        "gate names and detection mechanisms (you can see which gates engaged in "
        "cage_engagement_summary.engaged_gates_union and which structural critic "
        "fields were populated in substrate_critique_summary).\n\n"
        "QUESTION 1: Cap pattern. What was the maximum score? Did the run plateau, "
        "oscillate, or decline? Identify the persistent failure mode from "
        "weakest_points (one sentence).\n\n"
        "QUESTION 2: Which gates engaged but did NOT flag despite the cap? List "
        "gate names from engaged_gates_union that ran every iter but emitted no "
        "verdict that would have closed the gap.\n\n"
        "QUESTION 3: What apparatus-side detection would have moved the needle? "
        "Be concrete: a new gate, an extension of an existing critic field, a "
        "rubric flag, or a substrate-enrichment trigger. List 1-3 specific "
        "recommendations.\n\n"
        "QUESTION 4: Is there a related gate that EXISTS but is scoped too narrowly? "
        "For example, a gate that checks visible-class feature collapses but not "
        "withheld-class collapses. If so, name the gate and the scope extension.\n\n"
        "Output MUST be a single JSON object with this schema, no markdown:\n"
        "{\n"
        '  "cap_pattern": "one-sentence description",\n'
        '  "gates_engaged_not_flagged": ["gate_name_1", ...],\n'
        '  "detection_recommendations": ["concrete recommendation 1", ...],\n'
        '  "narrow_scoped_gate": {"gate_name": "...", "scope_extension": "..."} or null\n'
        "}\n\n"
        "Return ONLY the JSON object."
    )


def _parse_audit_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    s = raw.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        s = "\n".join(ln for ln in lines if not ln.strip().startswith("```"))
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
    # Find first balanced JSON object
    depth = 0
    start = -1
    for i, ch in enumerate(s):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(s[start:i + 1])
                except json.JSONDecodeError:
                    pass
    return None


# ── Operator-facing markdown ──────────────────────────────────────────


def _render_audit_markdown(
    project: str,
    run_id: Optional[str],
    verdict: PostRunMetaAuditVerdict,
    eval_summary: dict,
) -> str:
    lines = [
        f"# Post-Run Meta-Audit — {project}",
        "",
        f"- run_id: {run_id or '(unknown)'}",
        f"- model_id_used: {verdict.model_id_used}",
        f"- attempted: {verdict.attempted}",
        f"- succeeded: {verdict.succeeded}",
        f"- tokens: in={verdict.tokens_in}, out={verdict.tokens_out}",
        "",
        "## Run shape",
        f"- iters: {eval_summary.get('n_iters')}",
        f"- score sequence: {eval_summary.get('scores')}",
        f"- max_score: {eval_summary.get('max_score')}",
        f"- final_score: {eval_summary.get('final_score')}",
        "",
    ]
    if verdict.error:
        lines += ["## Error", f"- {verdict.error}", ""]
        return "\n".join(lines)
    lines += [
        "## Q1 — Cap pattern",
        verdict.cap_pattern or "(empty)",
        "",
        "## Q2 — Gates engaged but didn't flag",
    ]
    if verdict.gates_engaged_not_flagged:
        for g in verdict.gates_engaged_not_flagged:
            lines.append(f"- {g}")
    else:
        lines.append("- (none identified)")
    lines += ["", "## Q3 — Detection recommendations"]
    if verdict.detection_recommendations:
        for r in verdict.detection_recommendations:
            lines.append(f"- {r}")
    else:
        lines.append("- (none)")
    lines += ["", "## Q4 — Narrow-scoped existing gate"]
    if verdict.narrow_scoped_gate:
        ng = verdict.narrow_scoped_gate
        lines.append(f"- gate: `{ng.get('gate_name', '?')}`")
        lines.append(f"- scope_extension: {ng.get('scope_extension', '?')}")
    else:
        lines.append("- (none identified)")
    lines += [
        "",
        "## Honesty caveat",
        "This is the APPARATUS-side diagnostic. The OPERATOR-side action — "
        "do these recommendations actually fit the substrate? do they generalize? — "
        "stays human. Treat each recommendation as a proposal, not an action.",
        "",
    ]
    return "\n".join(lines)


# ── Public entry point ────────────────────────────────────────────────


def run_post_run_meta_audit(
    project_dir: Path | str,
    *,
    run_id: Optional[str] = None,
    mutator_model_id: Optional[str] = None,
    judge_model_id: Optional[str] = None,
    audit_model_id: str = "claude-haiku-4-5",
    newton_threshold: int = 90,
    timeout_seconds: float = 30.0,
    max_input_tokens: int = 5000,
    max_output_tokens: int = 2000,
    runtime: Any = None,
) -> dict:
    """Run a single post-run meta-audit pass.

    Args:
        project_dir: project root (workspace/ lives under it).
        run_id: optional run-id label for the artifact.
        mutator_model_id, judge_model_id: pass-through so the audit
            model can stay cross-family. The audit_model_id default
            is `claude-haiku-4-5`; override via rubric or kwarg.
        audit_model_id: the LLM that runs the audit. Cross-family from
            mutator AND judge by convention.
        newton_threshold: score below which the run is considered capped.
        timeout_seconds: hard wall-clock cap (degraded-mode contract).
        max_input_tokens: trace summary truncated to fit.
        max_output_tokens: response budget.
        runtime: LLMRuntime instance; constructed if None.

    Returns:
        verdict.to_dict() — the audit record. Also writes
        `workspace/post_run_meta_audit.md` and
        `workspace/post_run_meta_audit.json`.
    """
    project_dir = Path(project_dir)
    workspace_dir = project_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    verdict = PostRunMetaAuditVerdict(
        attempted=True,
        model_id_used=audit_model_id,
    )

    # Read trace artifacts
    eval_records = _read_jsonl(workspace_dir / "eval_history.jsonl", max_records=200)
    cage_records = _read_jsonl(workspace_dir / "cage_engagement.jsonl", max_records=200)
    iter_records = _read_jsonl(workspace_dir / "iteration_telemetry.jsonl", max_records=200)
    critique = _read_json(workspace_dir / "substrate_critique.json")

    eval_summary = _summarize_eval_history(eval_records)
    cage_summary = _summarize_cage_engagement(cage_records)
    iter_summary = _summarize_iteration_telemetry(iter_records)
    critique_summary = _summarize_substrate_critique(critique)

    # Project name from dir
    project = project_dir.name

    if not eval_records:
        verdict.error = "no eval_history.jsonl records found; cannot audit"
        _persist_artifacts(workspace_dir, project, run_id, verdict, eval_summary)
        return verdict.to_dict()

    # Cross-family hygiene check (best-effort warning, not blocking)
    if mutator_model_id and audit_model_id == mutator_model_id:
        verdict.error = (
            f"audit_model_id ({audit_model_id}) matches mutator_model_id; "
            "cross-family hygiene compromised — proceeding anyway"
        )
        # Don't return — operator may have set this deliberately. Continue.

    prompt = _build_meta_audit_prompt(
        project=project,
        run_id=run_id,
        eval_summary=eval_summary,
        cage_summary=cage_summary,
        critique_summary=critique_summary,
        iter_summary=iter_summary,
        newton_threshold=newton_threshold,
    )

    # Truncate prompt if oversized (rough char-to-token ratio of 4)
    max_chars = max_input_tokens * 4
    if len(prompt) > max_chars:
        prompt = prompt[:max_chars] + "\n[PROMPT TRUNCATED — trace-summary too large]"

    # LLM call (fail-graceful)
    if runtime is None:
        try:
            from src.ztare.common.llm_runtime import LLMRuntime as _LLMRuntime
            runtime = _LLMRuntime()
        except Exception as exc:  # noqa: BLE001
            verdict.error = f"LLMRuntime unavailable: {exc}"
            _persist_artifacts(workspace_dir, project, run_id, verdict, eval_summary)
            return verdict.to_dict()

    try:
        response = runtime.call_text(
            prompt,
            model_id=audit_model_id,
            timeout_seconds=int(timeout_seconds),
            max_tokens=max_output_tokens,
            request_label="post_run_meta_audit",
            retries=1,
        )
    except Exception as exc:  # noqa: BLE001
        verdict.error = f"{type(exc).__name__}: {str(exc)[:280]}"
        _persist_artifacts(workspace_dir, project, run_id, verdict, eval_summary)
        return verdict.to_dict()

    raw = response.text or ""
    verdict.raw_response = raw
    usage = getattr(response, "usage", None)
    verdict.tokens_in = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
    verdict.tokens_out = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
    verdict.model_id_used = getattr(response, "effective_model_id", audit_model_id) or audit_model_id

    parsed = _parse_audit_json(raw)
    if not parsed:
        verdict.error = "could not parse JSON from audit response"
        _persist_artifacts(workspace_dir, project, run_id, verdict, eval_summary)
        return verdict.to_dict()

    verdict.cap_pattern = str(parsed.get("cap_pattern", ""))[:600]
    gnf = parsed.get("gates_engaged_not_flagged") or []
    verdict.gates_engaged_not_flagged = [str(g)[:80] for g in gnf if g][:20]
    rec = parsed.get("detection_recommendations") or []
    verdict.detection_recommendations = [str(r)[:600] for r in rec if r][:10]
    nsg = parsed.get("narrow_scoped_gate")
    if isinstance(nsg, dict):
        verdict.narrow_scoped_gate = {
            "gate_name": str(nsg.get("gate_name", ""))[:120],
            "scope_extension": str(nsg.get("scope_extension", ""))[:600],
        }
    verdict.succeeded = True
    _persist_artifacts(workspace_dir, project, run_id, verdict, eval_summary)
    return verdict.to_dict()


def _persist_artifacts(
    workspace_dir: Path,
    project: str,
    run_id: Optional[str],
    verdict: PostRunMetaAuditVerdict,
    eval_summary: dict,
) -> None:
    json_path = workspace_dir / "post_run_meta_audit.json"
    md_path = workspace_dir / "post_run_meta_audit.md"
    try:
        json_path.write_text(json.dumps(verdict.to_dict(), indent=2), encoding="utf-8")
        verdict.artifact_path = str(json_path)
    except OSError:
        pass
    try:
        md_path.write_text(
            _render_audit_markdown(project, run_id, verdict, eval_summary),
            encoding="utf-8",
        )
        verdict.artifact_path_md = str(md_path)
    except OSError:
        pass
