"""Post-loop analyses (Phase 4g, 2026-05-06 PM).

Three opt-in analyses that run AFTER the iter loop ends, all
rubric-gated + fail-graceful:

  - **META-GATE 2C post-run meta-audit** (rubric flag
    ``enable_post_run_meta_audit``): cross-family LLM reads workspace
    trace + critique, writes ``post_run_meta_audit.{json,md}``.
    Proposals from the audit feed the discriminator queue.
  - **GP-190 post-run discriminator replay** (rubric flag
    ``enable_post_run_discriminator_queue``): deterministic scan over
    durable artifacts for known promotion-risk patterns; writes a
    typed replay queue. No LLM call.
  - **GP-193 post-run thesis synthesis** (rubric flag
    ``enable_post_run_thesis_synthesis``, default True for qualitative
    substrates): detects complementary iter clusters and tries to
    compose a candidate combined thesis that beats the per-iter
    champion by the configured margin.

Each block was previously inline in autoresearch_loop after the
``for i in range(ITERATIONS):`` loop (lines 7866-8024 in the
2026-05-06 PM tree). All three are independent of iter-loop locals;
they read final workspace state from disk. Fail-graceful — none
can fail the run.

Behaviour preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_post_loop_analyses(
    *,
    rubric_data: dict,
    project_dir: str | Path,
    project_name: str,
    rubric_name: str,
    judge_model_arg: str,
    mutator_model_arg: str,
    run_id,
    mutator_model_id: str,
    judge_model_id: str,
) -> None:
    """Run the three opt-in post-loop analyses + their downstream
    discriminator-queue appends.

    The function is the single entry point for everything that runs
    AFTER the iter loop finishes and before the final summary
    banner. Each analysis is independent + fail-graceful; a failure
    in one does not skip the others.
    """
    project_dir = Path(project_dir)

    # ---- META-GATE 2C post-run meta-audit ----
    if bool(rubric_data.get("enable_post_run_meta_audit", False)):
        try:
            from src.ztare.orchestrator.post_run_meta_audit import (
                run_post_run_meta_audit as _run_meta_audit,
            )

            audit_model_id = str(
                rubric_data.get("meta_audit_model_id") or "claude-haiku-4-5"
            )
            audit_verdict = _run_meta_audit(
                project_dir=project_dir,
                run_id=str(run_id),
                mutator_model_id=mutator_model_id,
                judge_model_id=judge_model_id,
                audit_model_id=audit_model_id,
            )
            print(
                f"🧭 post-run meta-audit: succeeded={audit_verdict.get('succeeded')} "
                f"model={audit_verdict.get('model_id_used')} "
                f"artifact={audit_verdict.get('artifact_path_md')}"
            )
            try:
                from src.ztare.orchestrator.discriminator_queue import (
                    append_discriminators as _append_discriminators,
                    proposals_from_meta_audit as _proposals_from_meta_audit,
                )

                meta_proposals = _proposals_from_meta_audit(
                    project=project_dir.name,
                    trigger_artifact=str(
                        project_dir / "workspace" / "post_run_meta_audit.json"
                    ),
                    audit_verdict=audit_verdict,
                )
                if meta_proposals:
                    q_path, q_count = _append_discriminators(project_dir, meta_proposals)
                    print(
                        f"🧭 discriminator queue: appended {q_count} "
                        f"meta-audit proposal(s) -> {q_path}"
                    )
            except Exception as dq_exc:  # noqa: BLE001
                print(f"🧭 discriminator queue append error (non-fatal): {dq_exc}")
        except Exception as audit_exc:  # noqa: BLE001
            print(f"🧭 post-run meta-audit error (non-fatal): {audit_exc}")

    # ---- GP-190 post-run discriminator replay (deterministic, no LLM) ----
    if bool(rubric_data.get("enable_post_run_discriminator_queue", False)):
        try:
            from src.ztare.orchestrator.operator_replay_audit import (
                proposals_from_sources as _replay_proposals_from_sources,
                write_replay_queue as _write_replay_queue,
            )

            source_specs = rubric_data.get("post_run_discriminator_sources") or [
                "thesis.md",
                "workspace/post_run_meta_audit.md",
                "workspace/champion_evidence_gaps.json",
                "workspace/latest_information_yield.json",
                "workspace/iteration_telemetry.jsonl",
            ]
            replay_sources: list[Path] = []
            for spec in source_specs:
                p = Path(str(spec))
                if not p.is_absolute():
                    p = project_dir / p
                if p.exists() and p.is_file():
                    replay_sources.append(p)
            replay_proposals = _replay_proposals_from_sources(
                replay_sources,
                project_override=project_dir.name,
            )
            replay_path = _write_replay_queue(project_dir, replay_proposals)
            print(
                f"🧭 discriminator replay: wrote {len(replay_proposals)} proposal(s) "
                f"from {len(replay_sources)} artifact(s) -> {replay_path}"
            )
        except Exception as replay_exc:  # noqa: BLE001
            print(f"🧭 discriminator replay error (non-fatal): {replay_exc}")

    # ---- GP-193 post-run thesis synthesis ----
    # Default ON for qualitative substrates, fail-graceful never aborts the run.
    # See research_areas/private/seams/protocol/GP-193_post_run_thesis_synthesizer_seam.md
    if bool(rubric_data.get("enable_post_run_thesis_synthesis", True)):
        try:
            from src.ztare.synthesis.post_run_thesis_synthesizer import (
                run_post_run_synthesis as _run_post_run_synth,
            )

            def _synthesis_judge_invoker(candidate_path: Path) -> int:
                """Score a synthesis candidate via test_thesis.

                Uses --thesis_path_override so the live thesis file is
                untouched. Temporarily installs the candidate's
                companion test_model.py (written by
                compose_candidate_thesis from the base iter's .py)
                so the falsification suite matches the synthesis
                thesis; restores the live test_model.py in finally.
                """
                tmp_eval = project_dir / "workspace" / "_synthesis_eval_tmp.json"
                live_test_model = project_dir / "test_model.py"
                backup_test_model = (
                    project_dir / "workspace" / "_test_model_backup.py"
                )
                companion_py = candidate_path.with_suffix(".py")
                swapped = False
                try:
                    if companion_py.exists():
                        if live_test_model.exists():
                            backup_test_model.write_text(
                                live_test_model.read_text(encoding="utf-8"),
                                encoding="utf-8",
                            )
                        live_test_model.write_text(
                            companion_py.read_text(encoding="utf-8"),
                            encoding="utf-8",
                        )
                        swapped = True
                    syn_cmd = [
                        sys.executable, "-m", "src.ztare.validator.test_thesis",
                        "--project", project_name,
                        "--rubric", rubric_name,
                        "--judge_model", judge_model_arg,
                        "--mutator_model", mutator_model_arg,
                        "--eval_results_path", str(tmp_eval),
                        "--thesis_path_override", str(candidate_path),
                    ]
                    proc = subprocess.run(syn_cmd, capture_output=False, timeout=600)
                    if proc.returncode != 0:
                        print(
                            f"🧬 synthesis judge subprocess failed (rc={proc.returncode})"
                        )
                        return 0
                    data = json.loads(tmp_eval.read_text(encoding="utf-8"))
                    return int(data.get("score", 0))
                except Exception as je:  # noqa: BLE001
                    print(f"🧬 synthesis judge error: {je}")
                    return 0
                finally:
                    if swapped and backup_test_model.exists():
                        live_test_model.write_text(
                            backup_test_model.read_text(encoding="utf-8"),
                            encoding="utf-8",
                        )

            attempts = _run_post_run_synth(
                project_dir=project_dir,
                rubric_data=rubric_data,
                judge_invoker=_synthesis_judge_invoker,
                margin_threshold=int(
                    rubric_data.get("post_run_synthesis_margin_threshold", 5)
                ),
                max_synthesis_attempts=int(
                    rubric_data.get("post_run_synthesis_max_attempts", 3)
                ),
            )
            if attempts:
                print(
                    f"🧬 post-run synthesis: evaluated {len(attempts)} candidate(s); "
                    "audit at workspace/post_run_synthesis_attempts.jsonl"
                )
                for a in attempts:
                    score_str = (
                        f"score {a.candidate_score}"
                        if a.candidate_score is not None
                        else "unscored"
                    )
                    promoted_str = " → PROMOTED to thesis.md" if a.promoted else ""
                    print(
                        f"   cluster {a.cluster_iter_indices} "
                        f"(base iter-{a.base_iter_index} score {a.base_score}) "
                        f"-> {score_str}{promoted_str} [{a.reason}]"
                    )
            else:
                print(
                    "🧬 post-run synthesis: no synthesis candidates (sparse history "
                    "or no complementary iter pairs found; see "
                    "workspace/post_run_synthesis_attempts.jsonl)"
                )
        except Exception as gp193_exc:  # noqa: BLE001
            print(f"🧬 post-run synthesis error (non-fatal): {gp193_exc}")

    # ---- GP-226 charter-critic V1 (post-run) ----
    # Closed-loop charter tuning against operator value-vector. Reads
    # debate logs + value-spec + score trajectory; emits structured
    # patches in advisory or auto mode. See
    # research_areas/private/seams/reflexive/GP-226_charter_critic_role_seam.md
    if bool(rubric_data.get("enable_charter_critic", False)):
        try:
            from src.ztare.orchestrator.charter_critic import (
                run_charter_critic_post_run as _run_charter_critic,
            )
            cc_result = _run_charter_critic(
                rubric_data=rubric_data,
                project_dir=project_dir,
                run_id=str(run_id),
                mutator_model_id=mutator_model_id,
            )
            if cc_result is not None:
                status = cc_result.get("status", "?")
                if cc_result.get("auto_generated_value_spec"):
                    print(
                        f"🧪 charter-critic: auto-generated default "
                        f"{cc_result['auto_generated_value_spec']} — edit to customize"
                    )
                if status == "candidate:advisory":
                    n = cc_result.get('patches_emitted', 0)
                    print(
                        f"🧪 charter-critic: emitted {n} candidate patch(es) "
                        f"-> {cc_result.get('candidate_path')}"
                    )
                    for s in cc_result.get("patch_summaries", []):
                        cross = s.get('cross_run_patch_count', 0)
                        prim = s.get('primitive') or '?'
                        prim_cross = s.get('cross_run_primitive_count', 0)
                        warn = ""
                        if prim_cross >= 5 and prim != '?':
                            warn = f" 🛑 PRIMITIVE-CEILING: {prim} patched {prim_cross}× across buckets — apparatus failing this primitive structurally"
                        elif cross >= 3:
                            warn = f" ⚠️  cross_run_count={cross} — escalation directive fired (formal derivation demanded)"
                        elif cross == 2:
                            warn = f" (cross_run_count={cross} — apparatus may be at substrate ceiling)"
                        print(
                            f"   • {s['reframe_type']} -> {s['target']} "
                            f"[{prim}] (rec={s['fingerprint_recurrence']}, "
                            f"sim={s['fingerprint_max_similarity']}, "
                            f"gen={s.get('generation', '?')}){warn}"
                        )
                    print(
                        f"   next: {cc_result.get('next_step')}"
                    )
                elif status == "committed:auto":
                    print(
                        f"🧪 charter-critic: auto-applied "
                        f"{cc_result.get('patches_applied')} patch(es) "
                        f"(skipped {cc_result.get('patches_skipped')})"
                    )
                    for s in cc_result.get("patch_summaries", []):
                        cross = s.get('cross_run_patch_count', 0)
                        prim = s.get('primitive') or '?'
                        prim_cross = s.get('cross_run_primitive_count', 0)
                        warn = ""
                        if prim_cross >= 5 and prim != '?':
                            warn = f" 🛑 PRIMITIVE-CEILING: {prim} patched {prim_cross}× across buckets — apparatus failing this primitive structurally"
                        elif cross >= 3:
                            warn = f" ⚠️  cross_run_count={cross} — escalation directive fired (formal derivation demanded)"
                        elif cross == 2:
                            warn = f" (cross_run_count={cross} — apparatus may be at substrate ceiling)"
                        print(
                            f"   • {s['reframe_type']} -> {s['target']} "
                            f"[{prim}] (rec={s['fingerprint_recurrence']}, "
                            f"sim={s['fingerprint_max_similarity']}, "
                            f"gen={s.get('generation', '?')}){warn}"
                        )
                else:
                    print(f"🧪 charter-critic: {status}")
                if cc_result.get("taxonomy_proposal_path"):
                    print(
                        f"💡 charter-critic: {cc_result.get('unmatched_count', 0)} "
                        f"unmatched fingerprint(s) -> "
                        f"{cc_result['taxonomy_proposal_path']} "
                        f"(operator review for taxonomy extension)"
                    )
                if cc_result.get("expired_patches"):
                    expired = cc_result["expired_patches"]
                    print(
                        f"⌛ charter-critic: {len(expired)} committed patch(es) "
                        f"past expiry — operator review:"
                    )
                    for e in expired:
                        print(
                            f"   • {e.get('reframe_type')} -> {e.get('target')} "
                            f"(created run {e.get('created_run_id')}, "
                            f"{e.get('runs_since')} runs ago, expiry={e.get('expiry_runs')})"
                        )
        except Exception as cc_exc:  # noqa: BLE001
            print(f"🧪 charter-critic error (non-fatal): {cc_exc}")
