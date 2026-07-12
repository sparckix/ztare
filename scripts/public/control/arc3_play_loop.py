#!/usr/bin/env python3
"""GP-250 "beat" engine: governed identification × planner exploitation, live.

The kernel-first self-improvement loop (NO Frankenstein re-identifier — the
governed `experiment-loop` IS the identifier, with its stagnation-pivot
reconception, judge, and hard gates; this driver only alternates it with
live play and grows the evidence):

  cycle:
    1. run the governed loop on the current episode log -> a ratified model
       (or, on stagnation, a structurally-pivoted reconception of it)
    2. load the ratified model, PLAY the live game under it (novelty / goal-cue
       steering), stopping on the sealed levels_completed reward
    3. LEVEL? report the win. else append the off-basin transitions the live
       game produced (the model was never fit on them) to the episode log,
       re-render evidence, reseal — the next governed cycle re-identifies on the
       richer evidence, and its pivot machinery reconceives if it stalls.

Reuses: experiment-loop (subprocess, sealed subscription workers), the
worldmodel gates/planner, the arc_agi3 adapter. Spends subscription tokens for
the governed cycles. Usage:
    python3 scripts/public/control/arc3_play_loop.py --game ls20 --cycles 4
    python3 scripts/public/control/arc3_play_loop.py --game ls20 --mode competition
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.common.phase_timing import phase  # noqa: E402
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402
from ztare.validator.worldmodel_typed_payload import validate_worldmodel_carrier_source  # noqa: E402
from ztare.worldmodel.adapter import (  # noqa: E402
    committee_read_model_path, episode_log_path, write_committee_read_model,
    write_deterministic_evidence)
from ztare.worldmodel.episode_log import EpisodeLog  # noqa: E402
from ztare.worldmodel.planner import pursue_goal  # noqa: E402
from ztare.worldmodel.policy import context_key  # noqa: E402
from ztare.worldmodel.residual_repair import (  # noqa: E402
    reject_satisfied_seed_prerequisite_cards,
)
from ztare.worldmodel.synthesis import synthesize  # noqa: E402


_ADVICE_MODES = {"advice", "competition", "compiled", "advice_consume"}
_FRONTIER_SCOPE_SCHEMA = "ztare-frontier-memory-scope-v1"
_FRONTIER_ABSTRACTION_VERSION = "arc3-object-frontier-v2"


def _game_prefix(game: str) -> str:
    return str(game or "").split("-", 1)[0]


def _resolve_game_id(game: str) -> str | None:
    game = str(game or "").strip()
    if "-" in game:
        return game
    from ztare.substrates.arc_agi3 import list_games
    return next((g for g in list_games() if g.startswith(game)), None)


def _normalize_play_mode(mode) -> "tuple[str, str]":
    alias = str(mode or "governed").strip().lower().replace("-", "_")
    return ("advice" if alias in _ADVICE_MODES else alias), alias


def _play_config(project: Path) -> dict:
    """Driver scheduling config (NOT research config — the rubric stays sealed):
    mode governed|sprint|hybrid|advice, sprint/checkpoint budgets. Missing file =
    prior behavior (governed).

    `advice` is the competition-time shape: consume the compiled advice string
    (persisted specs/candidates + deterministic abduction) and never launch the
    governed subscription-worker loop. Research happens before this mode, not
    inside it.
    """
    import json as _j
    path = project / "play_config.json"
    cfg = {"mode": "governed", "sprint_steps": 1500, "sprint_rounds": 6,
           "governed_checkpoint_every": 3, "governed_iters": 3,
           "plan_depth": 12, "seed_recovery_steps": 250,
           "seed_recovery_max_carriers": 2,
           "seed_recovery_patch_base_depth": 1}
    if path.exists():
        try:
            cfg.update(_j.loads(path.read_text()))
        except Exception:
            pass
    cfg["mode"], cfg["mode_alias"] = _normalize_play_mode(cfg.get("mode", "governed"))
    return cfg


def _is_env_reset(context_log, round_obs) -> bool:
    """Classify the LAST observed transition as an ENVIRONMENT RESET (episode
    boundary) using the gate's own logic: append the round's observations to the
    evidence context and ask gates.env_frame_indices whether that final row is a
    refill / t-anomaly. No bespoke reset heuristic — the same classifier the
    replay gate excuses on drives the episode-crossing decision."""
    from ztare.worldmodel.gates import env_frame_indices
    tmp = EpisodeLog(list(context_log))
    for (s_, a_, s2_, t_) in round_obs:
        tmp.append(s_, a_, s2_, t=t_)
    return bool(len(tmp)) and (len(tmp) - 1) in env_frame_indices(tmp)


def _play_round_multilife(adapter, play_model, *, budget, context_log, **kw):
    """EPISODE-CROSSING round: run pursue_goal repeatedly within ONE round. When a
    stop is a model divergence that is actually an ENV RESET (the game crossed an
    episode boundary), do NOT end the round — the adapter already sits at the new
    episode start and the visited store still carries the frontier, so continue on
    the remaining action budget. A round is thus multi-life; its action budget is
    the only stop. Returns a pr-shaped namespace so the caller is unchanged."""
    from types import SimpleNamespace
    obs, trace, steps, levels, saturated, status, lives = [], [], 0, 0, False, "plan_exhausted", 1
    divergence = None
    remaining = int(budget)
    while remaining > 0:
        pr = pursue_goal(adapter, play_model, max_steps=remaining, **kw)
        obs.extend(pr.observed_transitions)
        trace.extend(getattr(pr, "trace", []) or [])
        steps += pr.steps_executed
        levels += pr.levels_gained
        saturated = saturated or bool(pr.saturated)
        status = pr.status
        if divergence is None and getattr(pr, "divergence", None) is not None:
            divergence = pr.divergence
        remaining -= max(pr.steps_executed, 0)
        if pr.levels_gained > 0:
            break
        # cross an episode boundary iff the divergence that stopped this life IS an
        # env reset (progress was made, else a 0-step reset loop would spin)
        if (pr.status == "model_diverged" and pr.steps_executed > 0
                and _is_env_reset(context_log, obs)):
            lives += 1
            continue
        break        # genuine stop: saturation / real divergence / budget spent
    return SimpleNamespace(status=("multilife" if lives > 1 else status),
                           steps_executed=steps, levels_gained=levels,
                           saturated=saturated, observed_transitions=obs,
                           lives=lives, divergence=divergence, trace=trace)


def _terminal_witness_sha(pr) -> "str | None":
    div = getattr(pr, "divergence", None)
    if not isinstance(div, dict):
        return None
    witness = div.get("terminal_witness")
    return witness.get("sha256") if isinstance(witness, dict) else None


def _terminal_model_mismatch(pr) -> bool:
    return getattr(pr, "divergence", None) is not None and int(
        getattr(pr, "levels_gained", 0) or 0
    ) > 0


def _transition_model_mismatch(pr) -> bool:
    return getattr(pr, "divergence", None) is not None


def _write_play_report_and_terminal_audit(project: Path, report: dict) -> dict:
    """Persist the play report and its authority-boundary closure audit."""
    ws = project / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "arc3_play_loop_report.json").write_text(json.dumps(report, indent=2))
    try:
        from ztare.worldmodel.search_control_repair import write_terminal_closure_audit
        return write_terminal_closure_audit(project)
    except Exception as exc:  # noqa: BLE001 - report persistence is primary
        audit = {
            "schema": "ztare-worldmodel-terminal-closure-audit-error-v1",
            "status": "audit_write_failed",
            "error": str(exc)[:300],
        }
        (ws / "terminal_closure_audit.json").write_text(
            json.dumps(audit, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return audit


def _kernel_role_bindings(pr) -> list:
    div = getattr(pr, "divergence", None)
    if not isinstance(div, dict):
        return []
    bindings = list(div.get("kernel_role_bindings") or [])
    witness = div.get("terminal_witness")
    if isinstance(witness, dict):
        bindings.extend(witness.get("kernel_role_bindings") or [])
    seen = set()
    out = []
    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        key = (binding.get("term"), tuple(binding.get("roles") or ()))
        if key in seen:
            continue
        seen.add(key)
        out.append(binding)
    return out


def _write_level_boundary_seed(
    project: Path,
    *,
    game_id: str,
    cycle: int,
    completed_level: int,
    actions: list[int],
    source: str = "arc3_play_loop",
) -> dict:
    """Persist a replayable seed for the next level boundary.

    The seed is substrate adapter evidence, not a model claim: it lets bounded
    transfer probes replay the exact terminal path from reset instead of relying
    on an external scratch file.
    """
    next_level = max(1, int(completed_level) + 1)
    receipt = {
        "schema": "ztare-level-boundary-seed-v1",
        "game": game_id,
        "cycle": int(cycle),
        "completed_level": int(completed_level),
        "target_level": next_level,
        "full_sequence_from_reset": [int(a) for a in actions],
        "sequence_len": len(actions),
        "source": source,
        "authority": (
            "replay seed only; transfer, model adoption, and solve claims still "
            "require the normal replay/holdout/live gates"
        ),
    }
    ws = project / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    target = ws / f"level{next_level}_seed.json"
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    (ws / "latest_level_boundary_seed.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def _planner_attention_bindings(pr, *, goal_fn=None, progress_fn=None,
                                evidence_grown_by: int | None = None) -> list[dict]:
    """Typed pressure for the Strategy Office: the transition model can be good
    while search control is under-specified. This is advisory routing only; it
    cannot promote a candidate or claim a solve."""
    if goal_fn is not None or progress_fn is not None:
        return []
    if getattr(pr, "levels_gained", 0):
        return []
    if getattr(pr, "status", "") != "plan_exhausted":
        return []
    if evidence_grown_by not in (None, 0):
        return []
    return [{
        "term": "planner_goal_cue_absent",
        "roles": ["search_control", "selection", "model_update"],
        "evidence": (
            "gate-passing transition model exhausted live planning without "
            "a candidate goal/progress cue or new evidence"
        ),
    }]


def _champion_spec_path(project: Path):
    return project / "workspace" / "champion_spec.json"


def _load_prior_spec(project: Path):
    """Disk-persisted champion: a fresh process warm-starts in seconds instead
    of paying a cold abduction (the in-process prior only covers round->round)."""
    import json as _j
    paths = [_champion_spec_path(project)]
    legacy = REPO / "workspace" / "champion_spec.json"
    if not paths[0].exists() and legacy.exists():
        paths.append(legacy)
    log = None
    try:
        log = EpisodeLog.read_jsonl(episode_log_path(project))
    except Exception:
        log = None
    from ztare.worldmodel.gates import replay_consistency_gate
    from ztare.worldmodel.spec_catalog import lower_spec
    for path in paths:
        try:
            spec = _j.loads(path.read_text())
            if log is not None:
                step, _err = lower_spec(spec)
                if step is None or not replay_consistency_gate(step, log).ok:
                    _append_play_receipt(project, {
                        "site": "arc3_play_loop.py:286",
                        "fallback_taken": "corrupt_champion_spec",
                        "cause": "replay_consistency_gate rejected champion spec",
                        "champion_spec_path": str(path),
                    })
                    continue
            if path != paths[0]:
                _save_champion_spec(project, spec)
            return {"verdict": "loaded", "spec": spec, "source_path": str(path)}
        except Exception:
            _append_play_receipt(project, {
                "site": "arc3_play_loop.py:320",
                "fallback_taken": "corrupt_champion_spec",
                "cause": "champion spec read/parse failed",
                "champion_spec_path": str(path),
            })
            continue
    return {"verdict": "missing", "spec": None}


def _load_abduced_core_spec(project: Path):
    """Advisory warm-start only. A partial abduced core may seed the miner, but
    unlike champion_spec it cannot short-circuit replay/holdout gates."""
    import json as _j
    path = project / "workspace" / "abduced_core.json"
    try:
        payload = _j.loads(path.read_text())
        spec = payload.get("spec")
        if not isinstance(spec, dict):
            return None
        from ztare.worldmodel.spec_catalog import lower_spec
        step, _err = lower_spec(spec)
        if step is None:
            return None
        return spec
    except Exception:
        return None


def _load_warm_prior_spec(project: Path):
    prior = _load_prior_spec(project)
    if isinstance(prior, dict) and prior.get("verdict") == "loaded":
        return prior.get("spec")
    return _load_abduced_core_spec(project)


def _save_champion_spec(project: Path, spec) -> None:
    import json as _j
    try:
        path = _champion_spec_path(project)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_j.dumps(spec))
    except Exception:
        pass


def _append_play_receipt(project: Path, row: dict[str, Any]) -> None:
    ledger = project / "workspace" / "arc3_play_loop_receipts.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def _write_abduced_core_receipt(project: Path, log, ab) -> None:
    import json as _j
    path = project / "workspace" / "abduced_core.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    spec = getattr(ab, "spec", None)
    step_fn = getattr(ab, "step_fn", None)
    rows = list(log)
    if spec is None or step_fn is None:
        path.write_text(_j.dumps({
            "schema": "ztare-abduced-core-v1",
            "spec": None,
            "transitions": len(rows),
            "matched_transitions": 0,
            "residuals": [],
        }))
        return
    residual_classes = {}
    matched = 0
    for tr in rows:
        pred = step_fn(tr.s, tr.a, tr.t)
        if pred == tr.s_next:
            matched += 1
            continue
        cells = []
        for y in range(len(tr.s)):
            for x in range(len(tr.s[0])):
                if pred[y][x] != tr.s_next[y][x]:
                    cells.append(f"({y},{x}) predicted {pred[y][x]} real {tr.s_next[y][x]}")
        signature = (tr.a, len(cells), tuple(cells[:40]))
        row = residual_classes.get(signature)
        if row is None:
            row = {
                "first_t": tr.t,
                "action": tr.a,
                "cell_count": len(cells),
                "count": 0,
                "_t_values": set(),
                "t": tr.t,
                "cells": cells[:40],
            }
            residual_classes[signature] = row
        row["count"] += 1
        row["_t_values"].add(tr.t)
        row["first_t"] = min(int(row["first_t"]), int(tr.t))
    residuals = []
    for row in residual_classes.values():
        out_row = dict(row)
        t_values = sorted(int(t) for t in out_row.pop("_t_values", set()))
        out_row["t_values"] = t_values[:20]
        out_row["t_value_count"] = len(t_values)
        residuals.append(out_row)
    residuals = sorted(
        residuals,
        key=lambda r: (-int(r["count"]), int(r["first_t"]), int(r["action"])),
    )[:3]
    path.write_text(_j.dumps({
        "schema": "ztare-abduced-core-v1",
        "spec": spec,
        "transitions": len(rows),
        "matched_transitions": matched,
        "residual_class_count": len(residual_classes),
        "residuals": residuals,
    }))


def _write_worldmodel_blueprint(project: Path, log, spec) -> "Path | None":
    """Producer edge for the worldmodel <-> LeanMill feedback loop.

    The play loop may prepare proof work from an abduced spec, but it never
    converts conjectures into planner constraints. Only `absorb_ratification`
    can write `invariant_certificates.jsonl` after the kernel accepts a proof.
    """
    if not isinstance(spec, dict):
        return None
    import json as _j
    try:
        from ztare.worldmodel.lean_bridge import write_blueprint
        from ztare.worldmodel.object_roles import induce_roles
        try:
            roles = induce_roles(log, _log_arity(log)).roles
        except Exception:  # noqa: BLE001 — roles are blueprint context, not authority
            roles = []
        path = write_blueprint(project, spec, log, roles)
        try:
            command_path = path.relative_to(REPO)
        except ValueError:
            command_path = path
        blueprint_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        spec_sha256 = hashlib.sha256(
            _j.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        proof_command = (
            f"./venv/bin/python -m ztare.leanmill.cli campaign "
            f"{command_path}"
        )
        async_command = (
            f"./venv/bin/python -m ztare.leanmill.workbench_actions "
            f"autoformalize-notes {command_path} --project {project.name} "
            f"--save --json"
        )
        receipt = {
            "schema": "ztare-worldmodel-lean-feedback-v2",
            "status": "blueprint_emitted",
            "blueprint_ref": str(path.relative_to(project)),
            "blueprint_sha256": blueprint_sha256,
            "spec_sha256": spec_sha256,
            "next_command": proof_command,
            "async_command": async_command,
            "absorb_command_template": (
                f"./venv/bin/python -m ztare.worldmodel.lean_bridge absorb "
                f"--project {project} --lean-file <closed.lean> --theorem <theorem_name>"
            ),
            "evidence_hash": log.content_hash(),
            "routes": {
                "prove_current_spec": {
                    "status": "ready",
                    "command": proof_command,
                    "async_command": async_command,
                    "candidate": "theorem consequence of the frozen concrete spec",
                },
                "repair_single_proof_gap": {
                    "status": "inside_leanmill",
                    "operator": "solver.abduction.route_abduction",
                    "candidate": "missing premise that remains a child proof obligation",
                },
                "discover_reusable_theory": {
                    "status": "awaiting_signed_unseen_task_family",
                    "operator": "ztare.leanmill.axiom_pack",
                    "minimum_distinct_eval_tasks": 2,
                    "required": [
                        "typed_base_theory",
                        "typed_axiom_proposals",
                        "signed_pre_candidate_task_manifest",
                        "unseen_eval_tasks_not_embedded_in_this_blueprint",
                    ],
                    "command_template": (
                        "./venv/bin/python -m ztare.leanmill.axiom_pack "
                        "<typed_axiom_pack_blueprint.json> --out <screen.json>"
                    ),
                    "arc_consumption_rule": (
                        "a pack may assist later proof campaigns; only a separately audited theorem "
                        "derived from this concrete spec may enter invariant_certificates.jsonl"
                    ),
                },
            },
            "authority": (
                "proof-work handoff only; conjectures are not enforced until "
                "a byte-matched L1/L2/L3 proof audit writes certificates to "
                "workspace/invariant_certificates.jsonl"
            ),
        }
        out = project / "workspace" / "worldmodel_lean_feedback_receipt.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_j.dumps(receipt, indent=2, sort_keys=True) + "\n")
        return path
    except Exception as exc:  # noqa: BLE001 — proof handoff must not block play
        out = project / "workspace" / "worldmodel_lean_feedback_receipt.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_j.dumps({
            "schema": "ztare-worldmodel-lean-feedback-v1",
            "status": "blueprint_skipped",
            "reason": f"{type(exc).__name__}: {exc}",
            "evidence_hash": log.content_hash(),
            "authority": "proof-work handoff failure; no planner constraint emitted",
        }, indent=2, sort_keys=True) + "\n")
        return None


def _lean_feedback_checkpoint(project: Path, blueprint_path: "Path | None",
                              blueprint_sha256: "str | None") -> None:
    """Close the ARC↔LeanMill return edge at each governed checkpoint.

    Two non-blocking steps (ZTARE_ARC_LEAN_FEEDBACK=0 disables both):

    (a) KICK: if a freshly-emitted blueprint exists and no async campaign job
        has been launched for its sha, launch one in the background now and
        stamp the sha so re-entry is idempotent.
    (b) POLL: scan <project>/leanmill/jobs/ for any COMPLETED proof_audit job;
        for each, call absorb_ratification to append invariant_certificates.jsonl.
        A malformed job receipt raises loudly; an incomplete job is silently skipped.
    """
    import os as _os
    if _os.environ.get("ZTARE_ARC_LEAN_FEEDBACK", "1") == "0":
        return

    # ---- (a) KICK: idempotent campaign launch keyed by blueprint sha ----------
    if blueprint_path is not None and blueprint_sha256:
        stamp = project / "workspace" / "leanmill_campaign_launched.json"
        launched_sha = ""
        try:
            launched_sha = json.loads(stamp.read_text())["blueprint_sha256"]
        except Exception:  # noqa: BLE001 — missing / malformed stamp == not launched
            pass
        if launched_sha != blueprint_sha256:
            try:
                env = _os.environ.copy()
                src = str((REPO / "src").resolve())
                env["PYTHONPATH"] = src if not env.get("PYTHONPATH") else f"{src}{_os.pathsep}{env['PYTHONPATH']}"
                subprocess.Popen(
                    [sys.executable, "-m", "ztare.leanmill.cli", "campaign", str(blueprint_path)],
                    cwd=str(REPO),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                stamp.parent.mkdir(parents=True, exist_ok=True)
                stamp.write_text(json.dumps({
                    "blueprint_sha256": blueprint_sha256,
                    "blueprint_ref": str(blueprint_path),
                }) + "\n")
                print(f"  [lean-feedback] campaign kicked (sha={blueprint_sha256[:12]})", flush=True)
            except Exception as _kick_err:  # noqa: BLE001 — kick must never block play
                print(f"  [lean-feedback] campaign kick failed (non-fatal): {_kick_err}", flush=True)

    # ---- (b) POLL: absorb any completed proof_audit jobs ----------------------
    jobs_dir = project / "leanmill" / "jobs"
    if not jobs_dir.exists():
        return
    try:
        from ztare.worldmodel.lean_bridge import absorb_ratification, extract_theorem_statements
    except Exception as _imp_err:  # noqa: BLE001
        print(f"  [lean-feedback] import error (non-fatal): {_imp_err}", flush=True)
        return

    for job_path in sorted(jobs_dir.glob("lm_*.json"), reverse=True):
        if job_path.name.endswith("_result.json"):
            continue
        try:
            job = json.loads(job_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(job, dict):
            continue
        if job.get("action") != "proof_audit":
            continue
        if job.get("status") not in ("completed",):
            continue
        # Locate the result file
        result_ref = (job.get("paths") or {}).get("result") or job.get("result_path") or ""
        if not result_ref:
            continue
        result_path = (REPO / result_ref) if not Path(result_ref).is_absolute() else Path(result_ref)
        if not result_path.exists():
            result_path = project / result_ref
        if not result_path.exists():
            continue
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception as _rj_err:
            raise RuntimeError(f"[lean-feedback] malformed result JSON at {result_path}: {_rj_err}") from _rj_err
        if not isinstance(result, dict):
            raise RuntimeError(f"[lean-feedback] result file is not a JSON object: {result_path}")
        if not result.get("ok"):
            continue  # proof_audit failed or timed out — skip quietly
        # Absorb: need the .lean source file and theorem name(s)
        source_ref = job.get("source_file", "")
        if not source_ref:
            continue
        lean_path = (REPO / source_ref) if not Path(source_ref).is_absolute() else Path(source_ref)
        if not lean_path.exists():
            lean_path = project / source_ref
        if not lean_path.exists():
            continue
        target_name = job.get("target_name", "")
        try:
            if target_name:
                source_text = lean_path.read_text(encoding="utf-8")
                stmts = extract_theorem_statements(source_text, [target_name])
            else:
                # absorb_ratification extracts all theorems itself when given a raw source line
                stmts = [f"theorem {n}" for n in _theorem_names_from_lean(lean_path)]
            if stmts:
                certs = absorb_ratification(project, lean_path, stmts)
                if certs:
                    print(f"  [lean-feedback] absorbed {len(certs)} certificate(s) from {lean_path.name}", flush=True)
        except Exception as _abs_err:  # noqa: BLE001 — absorb must not block play
            print(f"  [lean-feedback] absorb_ratification error (non-fatal): {_abs_err}", flush=True)


def _theorem_names_from_lean(lean_path: Path) -> "list[str]":
    """Extract top-level theorem/lemma names from a .lean file (no imports needed)."""
    import re as _re
    pat = _re.compile(r"^(?:private\s+)?(?:theorem|lemma)\s+([A-Za-z0-9_'.]+)\b", _re.MULTILINE)
    try:
        return pat.findall(lean_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []


def _sprint_ident_receipt(project: Path, row: dict) -> None:
    """Append one row to workspace/sprint_identification.jsonl."""
    p = project / "workspace" / "sprint_identification.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def _champion_warm_start(project: Path, log: "EpisodeLog") -> "dict | None":
    """Read-only bitmap check: is the current champion correct on all checked rows?

    Returns {"wrong_rows": [...], "rows": N, "carrier_path": str} on success,
    None on any failure (caller treats None as warmstart_unavailable).
    """
    # ponytail: test_model.py is the canonical champion carrier in the project.
    carrier = project / "test_model.py"
    if not carrier.exists():
        return None
    ep_path = episode_log_path(project)
    if not ep_path.exists():
        return None
    try:
        from ztare.worldmodel.evidence_consolidation import build_row_bitmap
        bitmap = build_row_bitmap(carrier, ep_path, project_dir=project)
        return {
            "wrong_rows": bitmap.get("wrong_rows", []),
            "rows": bitmap.get("total_rows", 0),
            "carrier_path": str(carrier),
        }
    except Exception:  # noqa: BLE001 — failure must not block the sprint
        return None


def _sprint(project: Path, adapter, cfg: dict, progress_fn, goal_fn,
            champion_model=None, game_id: str = "") -> dict:
    """ZERO-TOKEN hot path (the Rodionov-throughput fix): abduce -> play long
    -> absorb divergence -> re-abduce. Plays only gate-passing abduced models;
    the sealed reward and raw gates hold everywhere; governance runs at
    checkpoints, not per step."""
    import os as _os
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.gates import rollout_depth as _rd
    log = EpisodeLog.read_jsonl(episode_log_path(project))
    hold = EpisodeLog.read_jsonl(episode_log_path(project, episode=2))
    out = {"rounds": [], "levels": 0, "deepest": 0}
    from ztare.worldmodel.gates import replay_consistency_gate as _rcg
    # FIX 3: wall-clock budget for the identification step (default 900s).
    try:
        _ident_budget_s = float(_os.environ.get("ZTARE_SPRINT_IDENT_BUDGET_S", "900"))
    except ValueError:
        _ident_budget_s = 900.0
    # Champion first; if absent, seed from a partial abduced-core receipt. The
    # latter is only a search prior and still pays the normal replay gates.
    prior_spec = _load_warm_prior_spec(project)
    verified_prefix = 0
    for rnd in range(1, int(cfg["sprint_rounds"]) + 1):
        # FIX 2: sub-phase receipt for identification (abduce + warm-start check).
        # FIX 1: warm-start / skip — evaluate the champion bitmap before paying
        # the full abduce cost. If wrong_rows is empty the champion already
        # explains every checked row; skip re-identification for this round.
        ab = None
        with phase("sprint.identification", project / "workspace"):
            import time as _time
            _ident_t0 = _time.monotonic()
            # --- warm-start check (read-only, failure-safe) ---
            _ws = None
            try:
                _ws = _champion_warm_start(project, log)
            except Exception:  # noqa: BLE001
                pass
            if _ws is None:
                # bitmap unavailable — full pipeline as before
                _sprint_ident_receipt(project, {
                    "schema": "ztare.sprint_identification.v1",
                    "round": rnd,
                    "action": "warmstart_unavailable",
                    "rows": len(log),
                })
            elif not _ws["wrong_rows"]:
                # champion explains all checked rows — skip from-scratch abduction
                _sprint_ident_receipt(project, {
                    "schema": "ztare.sprint_identification.v1",
                    "round": rnd,
                    "action": "skipped",
                    "reason": "champion_explains_all_checked_rows",
                    "rows": _ws["rows"],
                })
                print(f"  sprint {rnd}: warm-start SKIP (champion explains all "
                      f"{_ws['rows']} rows)", flush=True)
                # Reconstruct ab from the champion spec so downstream code has a
                # valid AbductionResult (replay_ok=True, step_fn set).
                from ztare.worldmodel.spec_abduction import AbductionResult
                from ztare.worldmodel.spec_catalog import lower_spec as _ls
                _champ = _load_prior_spec(project)
                _cs = _champ.get("spec") if isinstance(_champ, dict) and _champ.get("verdict") == "loaded" else None
                if _cs is not None:
                    _csf, _ = _ls(_cs)
                    ab = AbductionResult(
                        status="spec_identified", spec=_cs, step_fn=_csf,
                        replay_ok=True,
                        detail="warmstart: champion_explains_all_checked_rows",
                    )
                    prior_spec = _cs
            if ab is None:
                # full abduction path: warmstart_unavailable, residual non-empty, OR
                # bitmap said 0 wrong rows but champion spec failed to load
                _elapsed = _time.monotonic() - _ident_t0
                if _elapsed >= _ident_budget_s:
                    # budget already exceeded before we started — emit receipt and skip
                    _sprint_ident_receipt(project, {
                        "schema": "ztare.sprint_identification.v1",
                        "round": rnd,
                        "action": "budget_exit",
                        "reason": "budget_already_exceeded",
                        "budget_s": _ident_budget_s,
                        "elapsed_s": round(_elapsed, 2),
                    })
                else:
                    _residual_count = len(_ws["wrong_rows"]) if _ws else None
                    ab = abduce_spec(log, adapter.action_arity, prior_spec=prior_spec,
                                     verified_prefix=verified_prefix)
                    _elapsed2 = _time.monotonic() - _ident_t0
                    if _elapsed2 >= _ident_budget_s:
                        _sprint_ident_receipt(project, {
                            "schema": "ztare.sprint_identification.v1",
                            "round": rnd,
                            "action": "budget_exit",
                            "reason": "exceeded_during_abduce",
                            "budget_s": _ident_budget_s,
                            "elapsed_s": round(_elapsed2, 2),
                            "residual_count": _residual_count,
                        })
                        # ab may be partial; we still use whatever abduce returned
                    else:
                        # label logic:
                        #   _ws is None       -> warmstart_unavailable (bitmap not computable)
                        #   _ws has residuals -> full_reidentification (champion has wrong rows)
                        #   _ws has 0 residuals but ab is None (champion spec failed to load)
                        #     -> warmstart_failed_spec_load (bitmap said OK, but spec missing)
                        if _ws is None:
                            _ident_action = "warmstart_unavailable"
                        elif _residual_count:
                            _ident_action = "full_reidentification"
                        else:
                            # bitmap says 0 wrong rows but champion spec couldn't be loaded ->
                            # fell through to full abduction; this was the residual_count=0
                            # full_reidentification mislabel (first-round cache-miss path)
                            _ident_action = "warmstart_failed_spec_load"
                        _sprint_ident_receipt(project, {
                            "schema": "ztare.sprint_identification.v1",
                            "round": rnd,
                            "action": _ident_action,
                            "residual_count": _residual_count,
                            "rows": len(log),
                            "elapsed_s": round(_elapsed2, 2),
                        })
        # budget_exit with no ab produced → treat as abduction_partial and checkpoint
        if ab is None:
            partial = {"round": rnd, "status": "abduction_partial"}
            out["rounds"].append(partial)
            _write_sprint_receipt(project, {
                "round": rnd, "status": "abduction_partial",
                "saturated": False, "goal_mode": "none", "n_candidates": 0,
                "transition_model_mismatch": False,
                "terminal_verifier_model_mismatch": False,
                "terminal_witness_sha": None, "kernel_role_bindings": [],
            })
            break
        _write_abduced_core_receipt(project, log, ab)
        _write_worldmodel_blueprint(project, log, getattr(ab, "spec", None))
        if getattr(ab, 'spec', None) and getattr(ab, 'replay_ok', False):
            _save_champion_spec(project, ab.spec)
            verified_prefix = len(list(log))
        if ab.spec is not None:
            prior_spec = ab.spec
        abduced_ok = (ab.replay_ok and ab.step_fn is not None
                      and _rd(ab.step_fn, hold) >= len(hold))
        # play the ABDUCED model if complete, else the loaded gate-passing
        # CHAMPION (mutator's) — so exhaustive coverage runs even when abduction
        # is partial (ls20 timer never abduces). Only skip if NO valid model.
        play_model = ab.step_fn if abduced_ok else champion_model
        if play_model is None or not _rcg(play_model, log).ok:
            # CATALOG CEILING. Before deferring to the governed checkpoint, try ONE
            # grammar-reflex round: triage the residual into operator cards, run the
            # sealed-leaf implement path, and re-abduce. If that closes the law the
            # sprint continues IN-RUN (no conductor); else checkpoint as before with
            # the cards now on the ledger as briefing. ZTARE_GRAMMAR_REFLEX=0 restores
            # the old behaviour.
            reflex = None
            # FIX 1: gate grammar_reflex on non-empty residual — if champion
            # explains all rows the reflex has nothing to mine (propose_operators
            # would scan the full log and produce no actionable cards).
            _has_residual = (_ws is None or bool(_ws.get("wrong_rows")))
            if _has_residual and _os.environ.get("ZTARE_GRAMMAR_REFLEX", "1") != "0":
                with phase("sprint.grammar_reflex", project / "workspace"):
                    from ztare.worldmodel.grammar_reflex import attempt_grammar_extension
                    reflex = attempt_grammar_extension(project, log, ab, budget=1)
                out.setdefault("grammar_reflex", []).append(
                    {"round": rnd, "closed": reflex["closed"],
                     "dispositions": [d.get("disposition") for d in reflex["dispositions"]]})
            if not (reflex and reflex["closed"]):
                partial = {"round": rnd, "status": "abduction_partial"}
                out["rounds"].append(partial)
                _write_sprint_receipt(project, {
                    "round": rnd,
                    "status": "abduction_partial",
                    "saturated": False,
                    "goal_mode": "none",
                    "n_candidates": 0,
                    "transition_model_mismatch": False,
                    "terminal_verifier_model_mismatch": False,
                    "terminal_witness_sha": None,
                    "kernel_role_bindings": [],
                })
                break                                # no gate-passing model -> checkpoint
            # reflex closed the law in-run: adopt the extended model and keep playing.
            ab = reflex["result"]
            prior_spec = ab.spec
            _save_champion_spec(project, ab.spec)
            _write_worldmodel_blueprint(project, log, ab.spec)
            verified_prefix = len(list(log))
            play_model = ab.step_fn
            print(f"  grammar reflex closed the catalog ceiling in sprint {rnd} "
                  f"-> continuing in-run", flush=True)
        # goal cascade: candidate goal/progress is steering only; the sealed
        # terminal verifier still decides success. If no candidate cue exists,
        # fall back to abduced structural candidates, then coverage.
        structural_gf, n_cand = (None, 0) if goal_fn is not None else _structural_goal_fn(project, log, ab)
        active_goal = goal_fn or structural_gf
        active_progress = progress_fn if active_goal is None else None
        # VISITED SEED FROM RAW EVIDENCE (single source of truth): the frontier
        # store is the live cache UNION every abstract state in the log, so
        # coverage never re-walks a state the evidence already witnessed.
        af, visited_path, visited_store = _frontier_memory(project, log)
        with phase("sprint.multilife", project / "workspace"):
            pr = _play_round_multilife(
                adapter, play_model, budget=int(cfg["sprint_steps"]), context_log=log,
                goal_fn=active_goal,
                progress_fn=active_progress,
                resource_colors=_resource_colors(project),
                invariants=_invariants(project), abstract_fn=af,
                coverage_fn=_coverage_fn(project),
                visited_store=visited_store, visited_path=visited_path,
                plan_depth=int(cfg["plan_depth"]), max_replans=40)
        for (s_, a_, s2_, t_) in pr.observed_transitions:
            log.append(s_, a_, s2_, t=t_)
        log.write_jsonl(episode_log_path(project))
        out["deepest"] = max(out["deepest"], pr.steps_executed)
        out["rounds"].append({"round": rnd, "pursuit": pr.status,
                              "steps": pr.steps_executed, "log": len(log),
                              "saturated": bool(pr.saturated),
                              "transition_model_mismatch": _transition_model_mismatch(pr),
                              "terminal_verifier_model_mismatch": _terminal_model_mismatch(pr),
                              "reward_model_mismatch": _terminal_model_mismatch(pr),
                              "terminal_witness_sha": _terminal_witness_sha(pr),
                              "kernel_role_bindings": _kernel_role_bindings(pr)})
        _write_sprint_receipt(project, {
            "round": rnd, "saturated": bool(pr.saturated),
            "goal_mode": (
                "candidate_goal" if goal_fn is not None else
                "candidate_progress" if active_progress is not None else
                "structural" if structural_gf else "coverage"
            ),
            "n_candidates": n_cand,
            "transition_model_mismatch": _transition_model_mismatch(pr),
            "terminal_verifier_model_mismatch": _terminal_model_mismatch(pr),
            "terminal_witness_sha": _terminal_witness_sha(pr),
            "kernel_role_bindings": _kernel_role_bindings(pr)})
        print(f"  sprint {rnd}: {pr.status} depth={pr.steps_executed} log={len(log)}",
              flush=True)
        if pr.levels_gained > 0:
            out["levels"] += pr.levels_gained
            completed_level = int(getattr(adapter, "levels_completed", 0) or pr.levels_gained)
            seed = _write_level_boundary_seed(
                project,
                game_id=game_id,
                cycle=rnd,
                completed_level=completed_level,
                actions=list(getattr(pr, "trace", []) or []),
                source="arc3_play_loop_sprint",
            )
            out["level_boundary_seed"] = {
                "target_level": seed["target_level"],
                "sequence_len": seed["sequence_len"],
                "source_ref": f"workspace/level{seed['target_level']}_seed.json",
            }
            if pr.observed_transitions:
                import json as _j
                gs, ga, gnext, gt = pr.observed_transitions[-1]
                (project / "workspace" / "goal_exemplars.jsonl").open("a").write(
                    _j.dumps({"schema": "ztare-goal-exemplar-v1", "cycle": f"sprint{rnd}",
                              "t": gt, "action": ga, "s": [list(r) for r in gs],
                              "s_next": [list(r) for r in gnext]}) + chr(10))
            print(f"  🏆 LEVEL in sprint {rnd}", flush=True)
            break
    # --- LEVEL-3 machinery contradiction detection (append-only wiring) ---
    try:
        from ztare.worldmodel.machinery_contradictions import detect_and_card as _dc
        # derive divergence_indices from round log-length deltas; first round's
        # pre-sprint rows are unknown here so round-1 divergence may be missed —
        # acceptable: the spiral detector needs >=3 rounds anyway.
        _div_idx: set = set()
        _prev_rlog = None
        for _r in out["rounds"]:
            _cur_rlog = _r.get("log")
            if (_prev_rlog is not None and _cur_rlog is not None
                    and (_r.get("pursuit") or _r.get("status", "")) == "model_diverged"):
                _div_idx.update(range(_prev_rlog, _cur_rlog))
            if _cur_rlog is not None:
                _prev_rlog = _cur_rlog
        _mc = _dc(project, log, out["rounds"], divergence_indices=_div_idx)
        out["machinery_cards"] = _mc
        if _mc:
            latest = out["rounds"][-1] if out["rounds"] else {}
            _write_sprint_receipt(project, {
                **latest,
                "machinery_cards": _mc,
            })
    except Exception:  # noqa: BLE001 — detector failure must never break a sprint
        pass
    return out


def _log_arity(log) -> int:
    return 1 + max((tr.a for tr in log), default=0)


def _abstract_fn(project: Path):
    """Object-state key for FSM memoization and coverage.

    Prefer induced role signatures when the log exposes a controlled mover: they
    separate agent pose, passive resource clocks, and reactive terrain. Fall
    back to volatile-cell signatures for early or non-role evidence.
    """
    from ztare.worldmodel.object_roles import (
        induce_roles, object_signature, sound_signature, volatile_positions)
    log = EpisodeLog.read_jsonl(episode_log_path(project))
    try:
        roles = induce_roles(log, _log_arity(log)).roles
        if any(r.name == "moves_under_actions" for r in roles):
            return lambda g: object_signature(g, roles)
    except Exception:
        pass
    vp = volatile_positions(log)
    return (lambda g: sound_signature(g, vp)) if vp else None


def _coverage_fn(project: Path):
    """Frontier projection paired with `_abstract_fn`.

    ARC object roles expose a shorter controllable-state carrier than their full
    transition signature. Substrates without that carrier keep identity
    coverage.
    """
    log = EpisodeLog.read_jsonl(episode_log_path(project))
    try:
        from ztare.worldmodel.object_roles import control_signature, induce_roles
        roles = induce_roles(log, _log_arity(log)).roles
        if any(r.name == "moves_under_actions" for r in roles):
            return control_signature
    except Exception:
        pass
    return None


def _invariants(project: Path) -> list:
    """Kernel-ratified invariants only enforce; conjectured ones ride along.
    Ratification receipts live in workspace/invariant_certificates.jsonl."""
    import json as _j
    path = project / "workspace" / "invariant_certificates.jsonl"
    if not path.exists():
        return []
    from ztare.worldmodel.invariant_bridge import InvariantCertificate
    out = []
    for line in path.read_text().splitlines():
        try:
            d = _j.loads(line)
            out.append(InvariantCertificate(tuple(d["quantity"]), d["relation"],
                                            d["status"], d.get("theorem", "")))
        except Exception:
            pass
    return out


def _structural_goal_fn(project: Path, log, ab):
    """Pre-exemplar goal source (in-loop wiring, 2026-07-03): dormant-event /
    goal-abduction candidates compiled to ONE OR-predicate — reaching ANY
    candidate state is worth probing; the sealed reward disposes. Returns
    (goal_fn_or_None, n_candidates). Falls back to (None, 0) if the module or
    candidates are absent."""
    try:
        from ztare.worldmodel.goal_abduction import (
            abduce_goal_candidates, predicate_from_spec)
        from ztare.worldmodel.object_roles import induce_roles
        roles = induce_roles(log, _log_arity(log))
        out = abduce_goal_candidates(log, getattr(ab, "spec", None), roles)
        trs = list(log)
        start = trs[0].s if trs else None
        if start is None or not out:
            return None, 0
        if out.get("mode") == "post_success" and out.get("goal_predicate_spec"):
            return predicate_from_spec(out["goal_predicate_spec"], start), 1
        cands = [c for c in out.get("candidates", []) if c.get("predicate_spec")]
        preds = [predicate_from_spec(c["predicate_spec"], start) for c in cands]
        if not preds:
            return None, 0
        return (lambda g: any(pf(g) for pf in preds)), len(cands)
    except Exception:
        return None, 0


def _seed_visited(visited_path, log, abstract_fn) -> set:
    """Single source of truth for the exploration frontier: the live-play cache
    (visited_path) UNION every abstract object-state witnessed in the evidence
    log (both endpoints of each transition). The side file is only a live-play
    cache; the evidence log is the master. Pure and testable."""
    from ztare.worldmodel.reachability import load_visited
    store = load_visited(visited_path)
    if abstract_fn is not None:
        for tr in log:
            store.add(abstract_fn(tr.s))
            store.add(abstract_fn(tr.s_next))
    return store


def _frontier_scope(log, abstract_fn) -> dict:
    """Validity key for live frontier memory.

    Frontier memory is a quotient cache, not a substrate fact. It is reusable
    only for the evidence content and abstraction version that defined the
    quotient; otherwise stale coverage can make a fresh play round look
    saturated before it has spent actions.
    """
    return {
        "schema": _FRONTIER_SCOPE_SCHEMA,
        "evidence_hash": log.content_hash(),
        "abstraction_version": (
            _FRONTIER_ABSTRACTION_VERSION if abstract_fn is not None else "none"
        ),
    }


def _frontier_memory_path(project: Path, scope: dict) -> Path:
    raw = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
    sha = hashlib.sha256(raw).hexdigest()[:16]
    return project / "workspace" / "frontier" / f"visited_{sha}.jsonl"


def _write_frontier_scope_receipt(project: Path, scope: dict, visited_path: Path) -> None:
    receipt = dict(scope)
    receipt["visited_path"] = str(visited_path.relative_to(project))
    receipt["authority"] = (
        "frontier cache only; ignored automatically when evidence hash or "
        "abstraction version changes"
    )
    p = project / "workspace" / "latest_frontier_scope.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def _frontier_memory(project: Path, log=None):
    """Shared quotient-frontier memory for sprint and governed play."""
    if log is None:
        log = EpisodeLog.read_jsonl(episode_log_path(project))
    abstract = _abstract_fn(project)
    scope = _frontier_scope(log, abstract)
    visited_path = _frontier_memory_path(project, scope)
    _write_frontier_scope_receipt(project, scope, visited_path)
    visited_store = _seed_visited(visited_path, log, abstract)
    return abstract, visited_path, visited_store


def _write_sprint_receipt(project: Path, receipt: dict) -> None:
    """Minimal latest-sprint receipt the briefing reads (saturation + goal mode)."""
    import json as _j
    p = project / "workspace" / "latest_sprint_receipt.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_j.dumps(receipt))


def _resource_colors(project: Path) -> list:
    """Monotone-depleting roles = the resource whose bar bounds the horizon
    as a search coordinate. Proof-enforced pruning is separate and only comes
    from `_invariants(project)` reading kernel-ratified certificates."""
    try:
        from ztare.worldmodel.object_roles import induce_roles
        log = EpisodeLog.read_jsonl(episode_log_path(project))
        for r in induce_roles(log, _log_arity(log)).roles:
            if r.name == "monotone_depleting":
                return list(r.members)
    except Exception:
        pass
    return []


def _record_spec_receipt(project: Path, spec: dict, cycle: int) -> None:
    """Ratified-spec receipt: the seed data for the calibrated cross-game
    catalog (which operators, which parameter shapes, which game, verdicts)."""
    import json as _json
    path = project / "workspace" / "spec_receipts.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    ops = sorted({r.get("op") for rules in spec.get("actions", {}).values() for r in rules}
                 | {r.get("op") for r in spec.get("always", [])})
    with path.open("a") as f:
        f.write(_json.dumps({"schema": "ztare-spec-receipt-v1", "project": project.name,
                             "cycle": cycle, "ops": ops, "spec": spec,
                             "verdict": "replay_and_holdout_pass",
                             "source": "abduction"}) + chr(10))


def _validate_carrier_rubric_aware(source: str, project) -> None:
    """Honor the rubric's dynamics_assumption (lawful_time etc.) at EVERY
    carrier-validation site. Third occurrence of this contract drift
    (transfer probe 2026-07-11, then _load_ratified_model crashed the loop
    2026-07-12 after a t-reading champion was lawfully promoted): the
    validator grew the dynamics_assumption parameter and bare call sites
    silently kept strict mode."""
    da = None
    try:
        rub = REPO / "rubrics" / f"{Path(project).name}.json"
        da = json.loads(rub.read_text()).get("dynamics_assumption") or None
    except Exception:  # noqa: BLE001
        da = None
    validate_worldmodel_carrier_source(source, dynamics_assumption=da)


def _load_ratified_model(project: Path):
    """The champion the governed loop just ratified — the mutator's test_model.py
    (python carrier or grid_dsl PROGRAM), plus an optional PROGRESS heuristic the
    mutator inferred from the observed frames. Returns (model, progress_fn); the
    progress heuristic is STEERING ONLY (the sealed reward judges success, so a
    wrong cue costs efficiency, never correctness — the non-iatrogenic split)."""
    tm = project / "test_model.py"
    if not tm.exists():
        return None, None, None
    source = tm.read_text()
    _validate_carrier_rubric_aware(source, project)
    ns: dict = {"__name__": "candidate"}
    try:
        exec(compile(source, str(tm), "exec"), ns)  # noqa: S102 — our own sealed file
    except Exception as exc:  # noqa: BLE001 — no-model is a valid outcome, silence is not
        print(f"  ratified model failed to load ({tm}): "
              f"{type(exc).__name__}: {exc}", flush=True)
        return None, None, None
    return _model_from_namespace(project, ns)


def _model_from_namespace(project: Path, ns: dict, *, allow_patch_base: bool = True):
    """Extract a worldmodel carrier from an executed namespace.

    Patch-base carriers are gate-owned compositions: candidate code names a
    prior artifact by hash and supplies a pure delta, while this loader resolves
    and calls the base under project authority. This prevents live advice from
    treating ``PATCH_DELTA`` itself as a standalone ``f``/``model`` callable.
    """

    # optional goal-cue: a `progress(grid)->float` callable, or PROGRESS_SRC to
    # sandbox-compile (defense-in-depth; steering-only so it is not a trust boundary)
    progress = ns.get("progress") if callable(ns.get("progress")) else None
    if progress is None and isinstance(ns.get("PROGRESS_SRC"), str):
        from ztare.worldmodel.planner import compile_progress_heuristic
        fn, _err = compile_progress_heuristic(ns["PROGRESS_SRC"])
        progress = fn
    # GOAL_PREDICATE: the mutator's falsifiable goal HYPOTHESIS (rival: the
    # sealed reward fires elsewhere; discriminator: the level event itself).
    # Steering-only — plan_to_goal targets it, levels_completed judges it.
    goal = ns.get("GOAL_PREDICATE") if callable(ns.get("GOAL_PREDICATE")) else None

    model = None
    if allow_patch_base and (ns.get("PATCH_BASE") or ns.get("PATCH_BASE_REF")
                             or ns.get("PATCH_BASE_PATH")):
        try:
            from ztare.worldmodel.gates import as_predictor
            from ztare.worldmodel.patch_base_carrier import (
                compose_patch_base_carrier,
            )
            model = compose_patch_base_carrier(
                ns,
                project_dir=project,
                load_program_from_namespace=lambda base_ns: _model_from_namespace(
                    project, base_ns, allow_patch_base=True)[0],
                call_program=lambda program, state, action, t: as_predictor(program)(
                    state, action, t),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  PATCH_BASE carrier skipped: {type(exc).__name__}: {exc}",
                  flush=True)
    spec = ns.get("WORLD_MODEL_SPEC")
    if spec is not None:
        try:
            from ztare.worldmodel.spec_catalog import lower_spec
            model, err = lower_spec(spec)
            if model is None:
                print(f"  WORLD_MODEL_SPEC skipped: {err}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  WORLD_MODEL_SPEC skipped: {type(exc).__name__}: {exc}",
                  flush=True)
    for alias in ("step", "f", "model", "I_model"):
        if model is None and callable(ns.get(alias)):
            model = ns[alias]
            break
    if model is None:
        raw = ns.get("PROGRAM")
        if raw is not None:
            def _to(n):
                return tuple(_to(x) for x in n) if isinstance(n, list) else n
            model = _to(raw)
    return model, progress, goal


def _candidate_memory_records(project: Path) -> list[dict]:
    path = project / "workspace" / "candidate_memory.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    records = payload.get("records") if isinstance(payload, dict) else None
    return [r for r in (records or []) if isinstance(r, dict)]


def _candidate_memory_rank(record: dict) -> tuple:
    return (
        int(record.get("visible_exact_rows") or 0),
        int(record.get("passed_gates") or 0),
        int(record.get("holdout_depth") or 0),
        float(record.get("gate_score") or 0.0),
        -int(record.get("visible_wrong_cells") or 10**12),
        str(record.get("observed_at_utc") or ""),
    )


def _load_candidate_memory_advice(project: Path, log: EpisodeLog):
    from ztare.worldmodel.gates import replay_consistency_gate

    for rec in sorted(_candidate_memory_records(project),
                      key=_candidate_memory_rank, reverse=True):
        ref = rec.get("submission") or rec.get("path")
        if not isinstance(ref, str) or not ref.strip():
            continue
        raw = Path(ref)
        if raw.is_absolute() or ".." in raw.parts:
            continue
        path = project / raw
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        _validate_carrier_rubric_aware(source, project)
        ns: dict = {"__name__": "candidate_memory_advice"}
        try:
            exec(compile(source, str(path), "exec"), ns)
            model, progress, goal = _model_from_namespace(project, ns)
            if model is None:
                continue
            replay = replay_consistency_gate(model, log)
            if replay.ok:
                return model, progress, goal, f"candidate_memory:{rec.get('sha') or path.name}"
            print(f"  advice candidate_memory skipped: {path.name}: {replay.detail}",
                  flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  advice candidate_memory skipped: {path.name}: "
                  f"{type(exc).__name__}: {exc}", flush=True)
    return None, None, None, None


def _load_candidate_memory_steering_models(project: Path, *, max_patch_base_depth: int = 1):
    """Yield candidate-memory carriers as steering hypotheses.

    Unlike advice loading, this intentionally does not require replay
    consistency against the current log. The model is not promoted or used as
    authority; it only proposes actions for a live seed-recovery attempt, and
    the environment must confirm any level boundary before a seed is written.
    """
    for rec in sorted(_candidate_memory_records(project),
                      key=_candidate_memory_rank, reverse=True):
        ref = rec.get("submission") or rec.get("path")
        if not isinstance(ref, str) or not ref.strip():
            continue
        raw = Path(ref)
        if raw.is_absolute() or ".." in raw.parts:
            continue
        path = project / raw
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        _validate_carrier_rubric_aware(source, project)
        ns: dict = {"__name__": "candidate_memory_steering"}
        try:
            exec(compile(source, str(path), "exec"), ns)
            from ztare.worldmodel.patch_base_carrier import patch_base_chain_depth
            patch_base_depth = patch_base_chain_depth(
                ns, project_dir=project, max_depth=max(1, int(max_patch_base_depth) + 1))
            if patch_base_depth > max_patch_base_depth:
                print(f"  seed steering candidate skipped: {path.name}: "
                      f"PATCH_BASE depth {patch_base_depth} exceeds "
                      f"budget {max_patch_base_depth}", flush=True)
                continue
            model, progress, goal = _model_from_namespace(
                project, ns, allow_patch_base=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  seed steering candidate skipped: {path.name}: "
                  f"{type(exc).__name__}: {exc}", flush=True)
            continue
        if model is not None:
            yield {
                "source": f"candidate_memory:{rec.get('sha') or path.name}",
                "model": model,
                "progress": progress,
                "goal": goal,
                "patch_base_depth": patch_base_depth,
            }


def _seed_recovery_cards(project: Path) -> list[dict]:
    try:
        from ztare.common.operator_proposal_contract import open_cards
        cards = open_cards(project / "workspace" / "strategy_experiments.jsonl")
    except Exception:  # noqa: BLE001
        return []
    out = []
    for card in cards:
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
        if gate.get("command") == "recover_level_boundary_seed":
            out.append(card)
    return out


def _requested_seed_path(project: Path, cards: list[dict]) -> Path:
    for card in cards:
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        seed = plan.get("seed_prerequisite") if isinstance(plan.get("seed_prerequisite"), dict) else {}
        raw = seed.get("seed_path")
        if isinstance(raw, str) and raw.strip():
            path = Path(raw)
            if not path.is_absolute() and ".." not in path.parts:
                return project / path
    return project / "workspace" / "level2_seed.json"


def _write_seed_recovery_receipt(project: Path, receipt: dict) -> dict:
    path = project / "workspace" / "level_boundary_seed_recovery.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def _recover_level_boundary_seed(
    project: Path,
    *,
    game_id: str,
    cfg: dict,
    adapter_factory=None,
) -> dict:
    """Execute the Strategy Office ``recover_level_boundary_seed`` producer.

    This is evidence acquisition, not candidate promotion. Stale or partial
    carriers may steer live actions, but only a sealed level increment writes a
    replayable seed.
    """
    cards = _seed_recovery_cards(project)
    if not cards:
        return {"schema": "ztare-level-boundary-seed-recovery-v1",
                "status": "skipped_no_open_card"}
    seed_path = _requested_seed_path(project, cards)
    if seed_path.exists():
        return _write_seed_recovery_receipt(project, {
            "schema": "ztare-level-boundary-seed-recovery-v1",
            "status": "seed_already_available",
            "seed_path": str(seed_path.relative_to(project)),
            "open_card_shas": [c.get("failure_family_sha") for c in cards],
        })

    adapter_factory = adapter_factory or ArcAgi3Adapter
    budget = max(1, int(cfg.get("seed_recovery_steps") or cfg.get("sprint_steps") or 250))
    max_carriers = max(0, int(cfg.get("seed_recovery_max_carriers") or 0))
    max_patch_base_depth = max(0, int(cfg.get("seed_recovery_patch_base_depth") or 0))
    log = EpisodeLog.read_jsonl(episode_log_path(project))
    attempts = []
    adapter = adapter_factory(game_id)

    for n_carrier, candidate in enumerate(_load_candidate_memory_steering_models(
            project, max_patch_base_depth=max_patch_base_depth)):
        if max_carriers and n_carrier >= max_carriers:
            break
        print(f"  seed recovery steering: {candidate['source']}", flush=True)
        adapter.reset()
        pr = _play_round_multilife(
            adapter,
            candidate["model"],
            budget=budget,
            context_log=log,
            goal_fn=candidate.get("goal"),
            progress_fn=candidate.get("progress"),
            resource_colors=_resource_colors(project),
            invariants=_invariants(project),
            abstract_fn=None,
            coverage_fn=None,
            visited_store=None,
            visited_path=None,
            plan_depth=int(cfg.get("plan_depth") or 12),
            max_replans=max(12, budget),
        )
        if pr.observed_transitions:
            _grow_evidence(project, pr.observed_transitions, adapter)
            log = EpisodeLog.read_jsonl(episode_log_path(project))
        attempt = {
            "source": candidate["source"],
            "patch_base_depth": int(candidate.get("patch_base_depth") or 0),
            "status": pr.status,
            "steps_spent": int(pr.steps_executed or 0),
            "levels_gained": int(pr.levels_gained or 0),
            "confirmed_level_after": int(getattr(adapter, "levels_completed", 0) or 0),
            "trace_len": len(getattr(pr, "trace", []) or []),
        }
        attempts.append(attempt)
        if int(pr.levels_gained or 0) > 0:
            completed_level = int(getattr(adapter, "levels_completed", 0) or pr.levels_gained)
            seed = _write_level_boundary_seed(
                project,
                game_id=game_id,
                cycle=0,
                completed_level=completed_level,
                actions=list(getattr(pr, "trace", []) or []),
                source=f"strategy_seed_recovery:{candidate['source']}",
            )
            return _write_seed_recovery_receipt(project, {
                "schema": "ztare-level-boundary-seed-recovery-v1",
                "status": "seed_recovered",
                "seed_path": f"workspace/level{seed['target_level']}_seed.json",
                "sequence_len": seed["sequence_len"],
                "source": seed["source"],
                "attempts": attempts,
                "open_card_shas": [c.get("failure_family_sha") for c in cards],
                "composition_policy": {
                    "seed_recovery_patch_base_depth": max_patch_base_depth,
                    "seed_recovery_max_carriers": max_carriers,
                },
                "authority": (
                    "live environment confirmed the boundary; steering model was "
                    "not promoted"
                ),
            })

    # Last resort: spend a deterministic round-robin probe. This is weak but
    # makes the command executable even when no steering carrier is usable.
    adapter.reset()
    baseline = int(getattr(adapter, "levels_completed", 0) or 0)
    observed = []
    trace = []
    for i in range(budget):
        action = i % int(getattr(adapter, "action_arity", 1) or 1)
        before, t = adapter.state, adapter.t
        real = adapter.step(action)
        trace.append(int(action))
        observed.append((before, action, real, t))
        if int(getattr(adapter, "levels_completed", 0) or 0) > baseline:
            _grow_evidence(project, observed, adapter)
            completed_level = int(getattr(adapter, "levels_completed", 0) or 1)
            seed = _write_level_boundary_seed(
                project,
                game_id=game_id,
                cycle=0,
                completed_level=completed_level,
                actions=trace,
                source="strategy_seed_recovery:round_robin",
            )
            return _write_seed_recovery_receipt(project, {
                "schema": "ztare-level-boundary-seed-recovery-v1",
                "status": "seed_recovered",
                "seed_path": f"workspace/level{seed['target_level']}_seed.json",
                "sequence_len": seed["sequence_len"],
                "source": seed["source"],
                "attempts": attempts + [{
                    "source": "round_robin",
                    "steps_spent": len(trace),
                    "levels_gained": completed_level - baseline,
                    "confirmed_level_after": completed_level,
                }],
                "open_card_shas": [c.get("failure_family_sha") for c in cards],
                "composition_policy": {
                    "seed_recovery_patch_base_depth": max_patch_base_depth,
                    "seed_recovery_max_carriers": max_carriers,
                },
                "authority": "live environment confirmed the boundary",
            })
    if observed:
        _grow_evidence(project, observed, adapter)
    return _write_seed_recovery_receipt(project, {
        "schema": "ztare-level-boundary-seed-recovery-v1",
        "status": "seed_not_recovered",
        "budget": budget,
        "attempts": attempts + [{
            "source": "round_robin",
            "steps_spent": len(trace),
            "levels_gained": int(getattr(adapter, "levels_completed", 0) or 0) - baseline,
            "confirmed_level_after": int(getattr(adapter, "levels_completed", 0) or 0),
        }],
        "open_card_shas": [c.get("failure_family_sha") for c in cards],
        "composition_policy": {
            "seed_recovery_patch_base_depth": max_patch_base_depth,
            "seed_recovery_max_carriers": max_carriers,
        },
        "next_action": "increase seed_recovery_steps or provide a replayable seed artifact",
    })


def _load_advice_model(project: Path):
    """Load a gate-passing model from the compiled advice string.

    Order matters: a persisted champion spec is the most compact symbolic advice;
    `test_model.py` is the mutator-produced carrier. Both must replay the current
    visible log before they are used for live play.
    """
    from ztare.worldmodel.gates import replay_consistency_gate
    log = EpisodeLog.read_jsonl(episode_log_path(project))

    prior = _load_prior_spec(project)
    spec = prior.get("spec") if isinstance(prior, dict) and prior.get("verdict") == "loaded" else None
    if spec is not None:
        try:
            from ztare.worldmodel.spec_catalog import lower_spec
            step, err = lower_spec(spec)
            if step is not None and replay_consistency_gate(step, log).ok:
                return step, None, None, "champion_spec"
            if err:
                print(f"  advice champion spec skipped: {err}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  advice champion spec skipped: {type(exc).__name__}: {exc}",
                  flush=True)

    model, progress, goal = _load_ratified_model(project)
    if model is not None:
        try:
            replay = replay_consistency_gate(model, log)
            if replay.ok:
                return model, progress, goal, "test_model"
            print(f"  advice test_model skipped: {replay.detail}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  advice test_model skipped: {type(exc).__name__}: {exc}",
                  flush=True)
    model, progress, goal, source = _load_candidate_memory_advice(project, log)
    if source:
        return model, progress, goal, source
    return None, None, None, None


def _clean_env() -> dict:
    """The make/loop subprocess imports `src.ztare...` and needs REPO (not
    `src`) on PYTHONPATH; this process runs with `src` on path for its own
    `ztare...` imports. Don't leak our PYTHONPATH into the subprocess."""
    import os
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    return env


def _run_governed_cycle(project_slug: str, rubric: str, iters: int, mutator: str,
                        judge: str) -> int:
    # ITERS is a BUDGET; the rubric's `stop_on_gate_pass: true` ends the cycle
    # the moment a champion clears the hard gate, so a cycle never plays a
    # sub-gate model and never burns the full budget once a valid one exists
    # ("iterate until gates pass").
    cmd = ["make", "experiment-loop", f"PROJECT={project_slug}", f"RUBRIC={rubric}",
           f"ITERS={iters}", f"MUTATOR_MODEL={mutator}", f"JUDGE_MODEL={judge}",
           "AGENT_MUTATOR=1", "AGENT_JUDGE=1",
           "AGENT_MUTATOR_RUNTIME=codex", "AGENT_JUDGE_RUNTIME=codex", "AGENT_TIMEOUT=600"]
    return subprocess.run(cmd, cwd=REPO, env=_clean_env()).returncode


def archive_sealed_eval_slice(project: Path, log: EpisodeLog) -> dict:
    """Persist a live-play trajectory as a sealed eval slice.

    The slice is written to raw/episodes/eval_slices/ which is NEVER staged
    into briefing packs (briefing_pack._visible_artifact_ref_allowed blocks it).
    A ledger row is appended to workspace/sealed_eval_slices.jsonl so
    gate_harness can find the newest slice for the optional fresh-slice gate.

    Returns the ledger row dict.
    """
    import hashlib as _hl
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slice_dir = project / "raw" / "episodes" / "eval_slices"
    slice_dir.mkdir(parents=True, exist_ok=True)
    slice_path = slice_dir / f"eval_{ts}.jsonl"
    log.write_jsonl(slice_path)
    sha256 = _hl.sha256(slice_path.read_bytes()).hexdigest()
    row = {
        "path": str(slice_path.relative_to(project)),
        "sha256": sha256,
        "recorded_utc": ts,
        "steps": len(log),
        "source": "live_play",
    }
    ledger = project / "workspace" / "sealed_eval_slices.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def _grow_evidence(project: Path, observed, adapter) -> int:
    """Append the live off-basin transitions to the episode log + re-render the
    evidence, so the next governed cycle re-identifies on richer data."""
    log = EpisodeLog.read_jsonl(episode_log_path(project))
    before = len(log)
    # EVIDENCE CURATION (2026-07-05): in a deterministic environment a duplicate
    # (s, a, phase) transition carries zero information (same context -> same
    # s_next; determinism_check names violations). Random-walk bootstrap floods
    # the log with duplicates whose only effect is superlinear mining cost —
    # keep one witness per context. Lossless for identification; multiplicity
    # is irrelevant to exact replay.
    seen = {(tr.s, tr.a, tr.t % 6) for tr in log}
    for (s, a, s_next, t) in observed:
        key = (s, a, t % 6)
        if key in seen:
            continue
        seen.add(key)
        log.append(s, a, s_next, t=t)
    log.write_jsonl(episode_log_path(project))
    result = synthesize(log, adapter.action_arity)
    witnessed = {context_key(tr.a, tr.t) for tr in log}
    write_committee_read_model(project, result, witnessed, log)
    write_deterministic_evidence(project)
    return len(log) - before


def _strategy_office_enabled(cfg: dict) -> bool:
    import os as _os
    raw = _os.environ.get("ZTARE_STRATEGY_OFFICE")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return bool(cfg.get("enable_strategy_office", False))


def _has_open_strategy_cards(project: Path) -> bool:
    """Strategy cards are cross-cycle work orders.

    If one is open, producer shortcuts such as full pre-abduction should not
    starve the governed worker that can consume the card from the briefing.
    """
    try:
        from ztare.common.operator_proposal_contract import open_cards
        return bool(open_cards(project / "workspace" / "strategy_experiments.jsonl"))
    except Exception:  # noqa: BLE001
        return False


def _maybe_convene_strategy_office(project: Path, cfg: dict, report: dict,
                                   *, cycle: int, entry: dict) -> dict:
    """Cross-cycle strategy hook.

    Default off for frugality. When enabled, it runs only after the loop has a
    persisted no-progress receipt: no level, no new evidence, and an exhausted
    plan. It commissions experiment cards; it never changes the candidate,
    gates, or terminal status.
    """
    if entry.get("pursuit") != "plan_exhausted":
        return {"enabled": True, "skipped": "pursuit_not_exhausted"}
    if int(entry.get("levels_gained") or 0) != 0:
        return {"enabled": True, "skipped": "level_gained"}
    if int(entry.get("evidence_grown_by") or 0) != 0:
        return {"enabled": True, "skipped": "new_evidence"}

    report_path = project / "workspace" / "arc3_play_loop_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    deterministic_cards = []
    try:
        from ztare.worldmodel.search_control_repair import (
            write_search_control_repair_card,
        )
        deterministic_cards = write_search_control_repair_card(project)
    except Exception:  # noqa: BLE001 — card emission cannot affect play status
        deterministic_cards = []
    if not _strategy_office_enabled(cfg):
        return {"enabled": False,
                "deterministic_cards_written": len(deterministic_cards)}
    try:
        from ztare.research_director.strategy_office import convene
        from ztare.worldmodel.strategy_battery import WorldmodelBattery
        leaf = str(cfg.get("strategy_office_leaf_model") or "gpt-5.5")
        dry = bool(cfg.get("strategy_office_dry_run", False))
        if dry:
            from ztare.research_director.strategy_office import render_dossier
            battery = WorldmodelBattery()
            dossier = battery.run_audits(project)
            text = render_dossier(dossier, battery.query_menu(),
                                  battery.experiment_kinds())
            out = project / "workspace" / "strategy_office_last_dry_run.txt"
            out.write_text(text, encoding="utf-8")
            return {"enabled": True, "dry_run": True,
                    "deterministic_cards_written": len(deterministic_cards),
                    "firing_signal": dossier.get("firing_signal"), "cycle": cycle}
        written = convene(project, WorldmodelBattery(), leaf_model=leaf,
                          judge_model=cfg.get("judge_model"),
                          mutator_model=cfg.get("mutator_model"))
        return {"enabled": True,
                "cards_written": len(written) + len(deterministic_cards),
                "deterministic_cards_written": len(deterministic_cards),
                "cycle": cycle}
    except Exception as exc:  # noqa: BLE001 — office failure cannot affect play status
        return {"enabled": True, "error": f"{type(exc).__name__}: {exc}",
                "deterministic_cards_written": len(deterministic_cards)}


def _bootstrap_explore(project: Path, adapter, cfg: dict) -> int:
    """Evidence-acquisition cold-start every fresh game needs.

    With no ratified model to play, take budgeted exploratory actions —
    round-robin over the action set with a light novelty bias from the visited
    store — and append the transitions through the honest `_grow_evidence` path
    so the next cycle's sprint re-abduces on a non-empty log and the checkpoint
    gets real evidence. No model assumptions: pure exploration. ls20 was
    bootstrapped by historical probes; a brand-new game has none, so it gathers
    its own. Budget: cfg['sprint_steps']."""
    af, _visited_path, visited = _frontier_memory(
        project, EpisodeLog.read_jsonl(episode_log_path(project)))
    arity, observed, tried = adapter.action_arity, [], {}
    for i in range(int(cfg["sprint_steps"])):
        s, t = adapter.state, adapter.t
        sig = af(s) if af is not None else None
        seen = tried.setdefault(sig, set())
        # light novelty bias: prefer an action not yet taken from this signature;
        # else round-robin so coverage still rotates the whole action set.
        a = next((x for x in range(arity) if x not in seen), i % arity)
        seen.add(a)
        s2 = adapter.step(a)
        observed.append((s, a, s2, t))
        if af is not None:
            visited.add(af(s2))
    return _grow_evidence(project, observed, adapter)


def main() -> int:
    a = sys.argv
    if "--help" in a or "-h" in a:
        print(
            "usage: arc3_play_loop.py [--game GAME] [--cycles N] "
            "[--iters N] [--mode governed|sprint|hybrid|advice|competition]"
        )
        return 0
    game = a[a.index("--game") + 1] if "--game" in a else "ls20"
    cycles = int(a[a.index("--cycles") + 1]) if "--cycles" in a else 4
    iters = int(a[a.index("--iters") + 1]) if "--iters" in a else 3
    mode_override = a[a.index("--mode") + 1] if "--mode" in a else None
    slug = f"arc3_{_game_prefix(game)}_gov"
    rubric = f"rubrics/{slug}.json"
    project = REPO / "projects" / slug

    game_id = _resolve_game_id(game)
    if game_id is None:
        print(json.dumps({"error": f"game {game} not found"}))
        return 1

    cfg = _play_config(project)
    if mode_override is not None:
        cfg["mode"], cfg["mode_alias"] = _normalize_play_mode(mode_override)
    print(f"play mode: {cfg['mode']} (sprint_steps={cfg['sprint_steps']}, "
          f"checkpoint_every={cfg['governed_checkpoint_every']})", flush=True)
    report = {"game": game_id, "cycles": [], "mode": cfg["mode"]}
    seed_recovery = _recover_level_boundary_seed(project, game_id=game_id, cfg=cfg)
    if seed_recovery.get("status") not in {"skipped_no_open_card", None}:
        # producer emits seed_already_available|seed_recovered|seed_not_recovered
        # (never "replayable_boundary_seed_available" — that dead value left
        # satisfied seed cards permanently unrejected)
        if seed_recovery.get("status") in {"seed_already_available", "seed_recovered"}:
            rejected = reject_satisfied_seed_prerequisite_cards(
                project,
                source_ref=str(seed_recovery.get("seed_path") or "workspace/level2_seed.json"),
            )
            if rejected:
                seed_recovery["rejected_superseded_seed_cards"] = len(rejected)
        print(f"  seed recovery: {seed_recovery.get('status')}", flush=True)
        report["seed_recovery"] = seed_recovery
    # CHAMPION PERSISTENCE (bug fix): always PLAY the deepest-playing model ever
    # found, never the latest cycle's possibly-regressed submission. A governed
    # cycle only tries to IMPROVE the champion; a worse model never displaces it.
    best_model = None
    best_progress = None
    best_goal = None
    best_depth = -1
    advice_only = cfg["mode"] == "advice"
    if advice_only:
        best_model, best_progress, best_goal, _advice_source = _load_advice_model(project)
        if _advice_source:
            print(f"  advice model loaded: {_advice_source}", flush=True)
    for cyc in range(1, cycles + 1):
        # SPRINT HOT PATH (mode sprint|hybrid): zero-token act-learn rounds.
        # Governance runs as a CHECKPOINT (on catalog ceiling, or every Nth
        # cycle in hybrid) — the throughput fix, with every guarantee intact.
        if cfg["mode"] in ("sprint", "hybrid", "advice"):
            sp_adapter = ArcAgi3Adapter(game_id)
            # Probe rider: scripted distinguishing probes fire during ordinary
            # sprint play when unresolved scripted-probe targets exist (the
            # sprints reach the post-boundary regime; steered sessions do not).
            # Inert passthrough when no targets pending. ZTARE_PROBE_RIDER=0 kills.
            import os as _os_pr
            if _os_pr.environ.get("ZTARE_PROBE_RIDER", "1") != "0":
                try:
                    from ztare.worldmodel.distinguishing_play import ProbeRiderAdapter
                    sp_adapter = ProbeRiderAdapter(sp_adapter, project)
                except Exception as _pr_exc:  # noqa: BLE001
                    print(f"  probe rider unavailable: {_pr_exc}", flush=True)
            sp_adapter.reset()
            print(f"\n===== CYCLE {cyc}/{cycles}: SPRINT (zero-token act-learn) =====",
                  flush=True)
            # The sprint (abduce -> play -> re-abduce) is an OPTIMIZATION, never a
            # blocker — same contract as the governed-path abduce guard below. It
            # was previously UNPROTECTED: an abduce failure (or the process being
            # reaped mid-abduce under memory pressure surfacing as an error here)
            # killed the whole loop with no output. Catch, LOG loudly, and degrade
            # to a governed checkpoint so a slow/failed sprint is observable and
            # recoverable rather than a silent death. (Uncatchable SIGKILL/OOM is
            # handled upstream by keeping abduce RSS bounded; see spec_abduction.)
            try:
                with phase("sprint", project / "workspace"):
                    sp = _sprint(project, sp_adapter, cfg, best_progress, best_goal,
                                 champion_model=best_model, game_id=game_id)
            except Exception as _sp_err:  # noqa: BLE001 — sprint is optional, never fatal
                print(f"  ⚠️  sprint failed ({type(_sp_err).__name__}: {_sp_err}) "
                      f"-> degrading to governed checkpoint", flush=True)
                import traceback as _tb
                _tb.print_exc()
                sp = {"rounds": [{"status": "abduction_partial", "error": str(_sp_err)}],
                      "levels": 0, "deepest": 0}
            report["cycles"].append({"cycle": cyc, "sprint": sp})
            if sp["levels"] > 0:
                report["result"] = "beat"
                print(f"  🏆 LEVEL COMPLETED (sprint, cycle {cyc})", flush=True)
                break
            hit_ceiling = any(r.get("status") == "abduction_partial" for r in sp["rounds"])
            if cfg["mode"] == "sprint":
                continue
            if advice_only and hit_ceiling:
                report["cycles"].append({"cycle": cyc, "status": "advice_boundary",
                                         "reason": "catalog_ceiling",
                                         "sprint": sp})
                report["result"] = "advice_boundary"
                print("  advice boundary reached: catalog ceiling; governed loop suppressed",
                      flush=True)
                break
            if not hit_ceiling and (cyc % max(int(cfg["governed_checkpoint_every"]), 1)) != 0:
                continue          # hybrid: no ceiling + not a checkpoint -> keep sprinting
            if advice_only:
                report["cycles"].append({"cycle": cyc, "status": "advice_boundary",
                                         "reason": "checkpoint_due",
                                         "sprint": sp})
                report["result"] = "advice_boundary"
                print("  advice boundary reached: checkpoint due; governed loop suppressed",
                      flush=True)
                break
            print("  sprint hit catalog ceiling / checkpoint due -> governed cycle",
                  flush=True)

        # ENGINE ROUTER (hybrid mode): deterministic engine selection from receipts.
        # Kill-switch: ZTARE_ENGINE_ROUTER=0 → unconditional governed-loop (old behavior).
        import os as _os_er
        _er_active = (cfg["mode"] == "hybrid"
                      and not advice_only
                      and _os_er.environ.get("ZTARE_ENGINE_ROUTER", "1") != "0")
        if _er_active:
            try:
                from ztare.worldmodel.engine_router import decide as _er_decide, execute as _er_execute
                with phase("engine_router", project / "workspace"):
                    _er_state, _er_decision = _er_decide(project)
                print(f"  [engine_router] {_er_decision['engine']}"
                      + (f"/{_er_decision['phase']}" if _er_decision.get("phase") else "")
                      + f": {_er_decision['reason']}", flush=True)
                _er_engine = _er_decision["engine"]
                # FIX C: open_world_brief receipt → log instruction so governed pass
                # sees the class-escape mandate before running autoresearch.
                if _er_engine == "autoresearch" and _er_decision.get("phase") == "open_world":
                    try:
                        _brief_path = project / "workspace" / "open_world_brief.jsonl"
                        if _brief_path.exists():
                            _brief_lines = [l for l in _brief_path.read_text(encoding="utf-8").splitlines() if l.strip()]
                            if _brief_lines:
                                _brief_row = json.loads(_brief_lines[-1])
                                _brief_instruction = _brief_row.get("instruction", "")
                                if _brief_instruction:
                                    print(f"  [open_world_brief] {_brief_instruction}", flush=True)
                                    # ponytail: write to well-known path the governed briefing reads
                                    _active_brief = project / "workspace" / "active_open_world_brief.json"
                                    _active_brief.write_text(
                                        json.dumps(_brief_row, sort_keys=True) + "\n",
                                        encoding="utf-8"
                                    )
                    except Exception:  # noqa: BLE001 — brief read must never block play
                        pass
                if _er_engine != "autoresearch":
                    # Non-autoresearch branch: execute and record, then continue outer loop
                    with phase(f"engine_router.{_er_engine}", project / "workspace"):
                        _er_result = _er_execute(_er_decision, project)
                    report["cycles"].append({
                        "cycle": cyc,
                        "engine_router": {
                            "engine": _er_engine,
                            "phase": _er_decision.get("phase"),
                            "reason": _er_decision["reason"],
                            "signals": _er_state,
                            "result_keys": list((_er_result or {}).keys()),
                        },
                        "sprint": sp,
                    })
                    continue   # skip governed-loop path for this cycle
                # autoresearch → fall through to existing governed-loop path unchanged
            except Exception as _er_err:  # noqa: BLE001 — router must never block play
                print(f"  [engine_router] error (falling through to governed): "
                      f"{type(_er_err).__name__}: {_er_err}", flush=True)

        # STEP 0 — spec abduction: try to identify the law deterministically
        # from diffs (zero model calls) before spending any mutator tokens.
        # Abduction proposes; the SAME gates verify; the mutator is the
        # fallback for what the catalog cannot express.
        rc = None
        candidate, cand_progress, cand_goal, abduced = None, None, None, False
        strategy_pending = _has_open_strategy_cards(project)
        if strategy_pending and not advice_only:
            print("  open strategy card present -> deterministic abduction still runs; "
                  "governed worker consumes briefing only if gates do not close", flush=True)
        try:
            import os as _os
            from ztare.worldmodel.spec_abduction import abduce_spec
            from ztare.worldmodel.gates import rollout_depth as _rd
            _log = EpisodeLog.read_jsonl(episode_log_path(project))
            _hold = EpisodeLog.read_jsonl(episode_log_path(project, episode=2))
            _champion_prior = _load_prior_spec(project)
            _prior = (
                _champion_prior.get("spec")
                if isinstance(_champion_prior, dict) and _champion_prior.get("verdict") == "loaded"
                else _load_abduced_core_spec(project)
            )
            _warm_only = (
                isinstance(_champion_prior, dict) and _champion_prior.get("verdict") == "loaded"
                and _os.environ.get("ZTARE_CHECKPOINT_FULL_ABDUCE", "0") != "1"
            )
            _ab = abduce_spec(_log, _log_arity(_log), prior_spec=_prior,
                              warm_only=_warm_only)
            _bp = _write_worldmodel_blueprint(project, _log, getattr(_ab, "spec", None))
            try:
                _bp_sha = json.loads(
                    (project / "workspace" / "worldmodel_lean_feedback_receipt.json").read_text()
                ).get("blueprint_sha256")
            except Exception:  # noqa: BLE001
                _bp_sha = None
            _lean_feedback_checkpoint(project, _bp, _bp_sha)
            if _ab.replay_ok and _ab.step_fn is not None \
                    and _rd(_ab.step_fn, _hold) >= len(_hold):
                candidate, abduced = _ab.step_fn, True
                _record_spec_receipt(project, _ab.spec, cyc)
                import json as _j
                from ztare.worldmodel.candidate_pool import add_candidate
                add_candidate(project, "WORLD_MODEL_SPEC = " + _j.dumps(_ab.spec),
                              carrier="spec", origin=f"abduction_cycle_{cyc}")
                print(f"\n===== CYCLE {cyc}/{cycles}: law ABDUCED from diffs "
                      f"(zero model calls; replay+holdout pass) =====", flush=True)
            elif _warm_only and _ab.status == "prior_refuted":
                print("  checkpoint champion refuted; full re-abduction skipped "
                      "(set ZTARE_CHECKPOINT_FULL_ABDUCE=1 to force it)",
                      flush=True)
        except Exception as _ab_err:  # noqa: BLE001 — abduction is an optimization, never a blocker
            print(f"  abduction step-0 error (falling through to mutator): {_ab_err}", flush=True)

        if not abduced and advice_only:
            candidate, cand_progress, cand_goal, _advice_source = _load_advice_model(project)
            if candidate is None:
                report["cycles"].append({"cycle": cyc, "status": "advice_boundary",
                                         "reason": "no_gate_passing_advice"})
                report["result"] = "advice_boundary"
                print("  advice boundary reached: no gate-passing advice model",
                      flush=True)
                break
            print(f"  advice fallback model loaded: {_advice_source}", flush=True)
        elif not abduced:
            print(f"\n===== CYCLE {cyc}/{cycles}: governed identification =====", flush=True)
            with phase("governed_loop", project / "workspace"):
                rc = _run_governed_cycle(slug, rubric, iters, "gpt5.5", "gpt5.5")
            candidate, cand_progress, cand_goal = _load_ratified_model(project)
            if candidate is not None:
                from ztare.worldmodel.candidate_pool import add_candidate
                add_candidate(project, (project / "test_model.py").read_text(),
                              carrier="mutator", origin=f"governed_cycle_{cyc}")

        # Evaluate the candidate by PLAY DEPTH (the beat metric), and always play
        # the best model we hold so exploration continues from real strength.
        adapter = ArcAgi3Adapter(game_id)
        adapter.reset()
        if candidate is not None:
            play_model, play_progress, play_goal = candidate, cand_progress, cand_goal
        else:
            play_model, play_progress, play_goal = best_model, best_progress, best_goal
        if play_model is None:
            grew = _bootstrap_explore(project, adapter, cfg)
            report["cycles"].append({"cycle": cyc, "status": "bootstrap_exploration",
                                     "transitions_added": grew, "loop_rc": rc})
            print(f"  no ratified model yet -> BOOTSTRAP EXPLORATION "
                  f"(cold-start): +{grew} transitions gathered; continuing", flush=True)
            continue
        # LOOP-LEVEL COMMITTEE: if multiple pooled candidates still survive the
        # log, spend a few live steps on their maximum-disagreement frontier —
        # the cheapest experiment that kills the most hypotheses — before
        # exploiting. (The seam's disagreement-frontier contract, multi-step.)
        try:
            from ztare.worldmodel.candidate_pool import surviving_committee
            from ztare.worldmodel.planner import plan_disagreement
            _log_now = EpisodeLog.read_jsonl(episode_log_path(project))
            committee = surviving_committee(project, _log_now)
            prelude_actions = []
            if len(committee) >= 2:
                dplan = plan_disagreement(committee, adapter.state,
                                          adapter.action_arity, start_step=adapter.t)
                if dplan and dplan.actions:
                    print(f"  committee of {len(committee)} survives; probing "
                          f"disagreement frontier: {dplan.actions[:12]}", flush=True)
                    disc = []
                    for a in dplan.actions[:20]:
                        t_now, s_now = adapter.t, adapter.state
                        s2 = adapter.step(a)
                        prelude_actions.append(int(a))
                        disc.append((s_now, a, s2, t_now))
                    _grow_evidence(project, disc, adapter)
        except Exception as _dc_err:  # noqa: BLE001 — discrimination is an optimization
            print(f"  committee-discrimination skipped: {_dc_err}", flush=True)
            prelude_actions = []

        steer = (
            "goal-cue" if play_goal is not None else
            "progress-cue" if play_progress is not None else
            "novelty"
        )
        print(f"===== CYCLE {cyc}: live play ({steer} steering) =====", flush=True)
        af, visited_path, visited_store = _frontier_memory(project)
        with phase("live_play", project / "workspace"):
            pr = pursue_goal(adapter, play_model,
                             goal_fn=play_goal,
                             progress_fn=play_progress if play_goal is None else None,
                             resource_colors=_resource_colors(project),
                             invariants=_invariants(project), abstract_fn=af,
                             coverage_fn=_coverage_fn(project),
                             visited_store=visited_store, visited_path=visited_path,
                             max_steps=250, plan_depth=10, max_replans=12,
                             receipts_dir=project / "workspace")
        # Truthful provenance: a governed cycle that exited rc!=0 leaves a STALE
        # test_model.py on disk; "candidate" would launder it as fresh output.
        played = "candidate" if play_model is candidate else "prior_champion"
        if rc not in (None, 0) and play_model is candidate:
            played = "stale_champion_after_failed_cycle"
        entry = {"cycle": cyc, "pursuit": pr.status, "steps": pr.steps_executed,
                 "levels_gained": pr.levels_gained, "observed": len(pr.observed_transitions),
                 "planner_detail": getattr(pr, "detail", ""),
                 "planner_saturated": bool(getattr(pr, "saturated", False)),
                 "lives": int(getattr(pr, "lives", 1) or 1),
                 "played": played,
                 "loop_rc": rc,
                 "transition_model_mismatch": _transition_model_mismatch(pr),
                 "terminal_verifier_model_mismatch": _terminal_model_mismatch(pr),
                 "reward_model_mismatch": _terminal_model_mismatch(pr),
                 "terminal_witness_sha": _terminal_witness_sha(pr),
                 "kernel_role_bindings": _kernel_role_bindings(pr)}
        if pr.levels_gained > 0:
            entry["status"] = "LEVEL_COMPLETED"
            completed_level = int(getattr(adapter, "levels_completed", 0) or pr.levels_gained)
            seed = _write_level_boundary_seed(
                project,
                game_id=game_id,
                cycle=cyc,
                completed_level=completed_level,
                actions=list(prelude_actions) + list(getattr(pr, "trace", []) or []),
            )
            entry["level_boundary_seed"] = {
                "target_level": seed["target_level"],
                "sequence_len": seed["sequence_len"],
                "source_ref": f"workspace/level{seed['target_level']}_seed.json",
            }
            # GOAL EXEMPLAR: the transition that triggered the terminal verifier is
            # a labeled example of the goal predicate — abduction fuel for
            # goal-directed planning on this and future levels. Never lose it.
            if pr.observed_transitions:
                import json as _json
                gs, ga, gnext, gt = pr.observed_transitions[-1]
                (project / "workspace" / "goal_exemplars.jsonl").open("a").write(
                    _json.dumps({"schema": "ztare-goal-exemplar-v1",
                                 "game": game_id, "cycle": cyc, "t": gt, "action": ga,
                                 "s": [list(r) for r in gs],
                                 "s_next": [list(r) for r in gnext]}) + chr(10))
            report["cycles"].append(entry)
            report["result"] = "beat"
            try:
                from ztare.worldmodel.search_control_repair import (
                    disposition_search_control_cards_from_report as _close_strategy_cards,
                )
                dispositions = _close_strategy_cards(project, report)
                if dispositions:
                    entry["strategy_card_dispositions"] = [
                        {
                            "kind": d.get("kind"),
                            "failure_family_sha": d.get("failure_family_sha"),
                            "disposition": d.get("disposition"),
                            "discharge": d.get("discharge"),
                        }
                        for d in dispositions
                    ]
            except Exception as _strategy_close_err:  # noqa: BLE001
                print(f"  strategy-card disposition skipped: {_strategy_close_err}", flush=True)
            print(f"  🏆 LEVEL COMPLETED in cycle {cyc} ({pr.steps_executed} steps)", flush=True)
            break
        # promote the candidate to champion only if it plays DEEPER (beat metric)
        if pr.steps_executed > best_depth and play_model is candidate:
            best_depth, best_model, best_progress, best_goal = \
                pr.steps_executed, candidate, cand_progress, cand_goal
            entry["champion_updated"] = True
        grown = _grow_evidence(project, pr.observed_transitions, adapter)
        entry["evidence_grown_by"] = grown
        entry["kernel_role_bindings"].extend(
            _planner_attention_bindings(
                pr, goal_fn=play_goal, progress_fn=play_progress,
                evidence_grown_by=grown))
        if pr.observed_transitions:
            _fresh_log = EpisodeLog.read_jsonl(episode_log_path(project))
            _slice_row = archive_sealed_eval_slice(project, _fresh_log)
            entry["eval_slice"] = {"path": _slice_row["path"], "sha256": _slice_row["sha256"]}
        entry["best_depth"] = best_depth
        report["cycles"].append(entry)
        office = _maybe_convene_strategy_office(project, cfg, report,
                                                cycle=cyc, entry=entry)
        if office.get("enabled") or office.get("deterministic_cards_written"):
            entry["strategy_office"] = office
        print(f"  no level; depth {pr.steps_executed} (best {best_depth}); grew evidence "
              f"by {grown} ({pr.status}); re-sealing", flush=True)
        with phase("reseal", project / "workspace"):
            subprocess.run(["make", "seal", f"PROJECT={slug}", f"RUBRIC={rubric}"],
                           cwd=REPO, input="pass\nyes\npass\n", text=True,
                           env=_clean_env(), stdout=subprocess.DEVNULL)

    report.setdefault("result", "no_level_in_budget")
    # Trace-auditor sweep at cycle end: the mechanized conductor's checks
    # (stale-latest, gate-achievability, alpha-measurability, champion-surface
    # conservation, file-seams, ...) had NO in-loop caller until 2026-07-11 —
    # built-but-unwired, the exact zero-caller class the auditor itself hunts.
    try:
        from ztare.orchestrator.trace_auditor import run_audit as _ta_run
        _ta = _ta_run(project, emit=True)
        _anoms = [f["check_id"] for f in _ta.get("findings", [])
                  if f.get("verdict") == "anomaly"]
        print(f"  trace-auditor: {len(_anoms)} anomalies"
              + (f" -> {_anoms}" if _anoms else ""), flush=True)
        report["trace_auditor_anomalies"] = _anoms
    except Exception as _ta_exc:  # noqa: BLE001
        print(f"  trace-auditor error (non-fatal): {_ta_exc}", flush=True)
    _write_play_report_and_terminal_audit(project, report)
    print("\n" + json.dumps({k: report[k] for k in ("game", "result")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
