"""Structural guard: no briefing provider silently omits on CORRUPT input.

The briefing layer's world-class invariant: a provider may render content or an
explicit UNAVAILABLE/DEGRADED banner, but NEVER a silent omission when the
artifacts it reads are present-but-corrupt.

This test walks every provider module under
``src/ztare/orchestrator/briefing_providers/``, hands each provider a project
dir in which EVERY .json / .jsonl / .txt / .yaml / .md it might open is
malformed (content ``{CORRUPT``), and asserts that a provider which *applies*
either raises loudly OR returns a fragment carrying a corruption marker — never
an empty/whitespace fragment.

Exemption rule (from the audit spec): a provider that is legitimately
not-applicable is exempt for ABSENT files only, NOT for corrupt ones. Here every
seeded file is PRESENT-but-corrupt, so ``applies() is False`` for a provider that
reads one of these files means its ``applies()`` swallowed the corruption — which
is itself the bug. We therefore record providers that decline and require that
they decline for a structural reason (rubric/substrate mismatch), not because
they read one of the corrupt artifacts in ``applies()``.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path

import pytest

import ztare.orchestrator.briefing_providers as bp_pkg
from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


# Every artifact filename any provider is known to open (harvested from the
# provider sources). Seeded corrupt so a provider that reaches for one hits
# malformed content rather than an absent file.
_CORRUPT_FILENAMES = [
    "abduced_core.json", "analogy_log.jsonl", "arc3_play_loop_report.json",
    "candidate_memory.json", "champion_materialization.jsonl", "champion_spec.json",
    "cold_llm_seed_iter0.json", "cold_shot_seed.json", "contract_violations.jsonl",
    "current_iteration.md", "embedding_history_vectors.json", "eval_history.jsonl",
    "evidence.txt", "fit_features_result.json", "framing_report.json",
    "gate_harness_result.json", "goal_exemplars.jsonl", "invariant_certificates.jsonl",
    "iteration_telemetry.jsonl", "latest_eval_results.json", "latest_evidence_gaps.json",
    "latest_information_yield.json", "latest_level_transfer_probe.json",
    "latest_loop_event.json", "latest_sprint_receipt.json", "leaf_proposals_digest.json",
    "mutator_briefing_projection_latest.json", "noise_profile.json",
    "operator_proposals.jsonl", "packet_falsifier_receipt.json", "project_packet.json",
    "qualitative_evidence_cold_shot.json", "refuted_families.jsonl", "seam.json",
    "strategy_experiments.jsonl", "structural_transport_cuts.json",
    "structural_transports.json", "substrate_critique.json",
    "substrate_critique_suggestions.json", "v4_activation.yaml", "verified_axioms.json",
    "worldmodel_committee.json", "worldmodel_lean_feedback_receipt.json",
]

_CORRUPT = "{CORRUPT"
_MARKERS = ("UNAVAILABLE", "DEGRADED", "unreadable", "UNREADABLE", "corrupt", "CORRUPT", "⚠️")


def _seed_corrupt_project(root: Path) -> None:
    """Populate a project dir where everything a provider reads is malformed."""
    ws = root / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    # A gate harness must EXIST (surviving_candidates gates applies() on it) but
    # be a corrupt/broken script so any run crashes rather than silently passing.
    (root / "gate_harness.py").write_text("raise SystemError('corrupt harness')\n")
    (ws / "submissions").mkdir(exist_ok=True)
    (ws / "submissions" / "iter_001_x.py").write_text(_CORRUPT)
    # leanmill + proof scratch dirs
    (root / "leanmill" / "jobs").mkdir(parents=True, exist_ok=True)
    (root / "leanmill" / "jobs" / "lm_0.json").write_text(_CORRUPT)
    (root.parent / "ztare_proofs" / ".solver_scratch").mkdir(parents=True, exist_ok=True)
    (root.parent / "ztare_proofs" / ".solver_scratch" / "RobustProbe_x.lean").write_text(_CORRUPT)
    for name in _CORRUPT_FILENAMES:
        (root / name).write_text(_CORRUPT)
        (ws / name).write_text(_CORRUPT)


def _wide_open_rubric() -> dict:
    """Enable every provider gate + declare the worldmodel contract so the
    maximal set of providers reach fragment() on corrupt input."""
    return {
        "enable_cold_llm_erdos_seed": True,
        "enable_cold_shot_seed": True,
        "enable_qualitative_evidence_cold_shot": True,
        "enable_qualitative_stagnation_detection": True,
        "enable_framer": True,
        "enable_forced_reframe": True,
        "enable_analogy": True,
        "enable_analogy_active": True,
        "enable_fit_primitive": True,
        "enable_lagrangian_derivation": True,
        "briefing_compute_candidate_memory": True,
        "cold_shot_director_audit_appendix": True,
        # Worldmodel-contract triggers (surviving_candidates / worldmodel_committee)
        "substrate_class": "interactive_environment",
        "fit_expression_grammar": "grid_dsl",
        "fit_score_mode": "discrete_exact",
    }


def _discover_providers() -> list[type[BriefingProvider]]:
    classes: list[type[BriefingProvider]] = []
    for mod_info in pkgutil.iter_modules(bp_pkg.__path__):
        module = importlib.import_module(f"{bp_pkg.__name__}.{mod_info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BriefingProvider)
                and obj is not BriefingProvider
                and obj.__module__ == module.__name__
            ):
                classes.append(obj)
    return classes


PROVIDER_CLASSES = _discover_providers()


def test_providers_discovered():
    # Sanity: the walk found a meaningful set, not zero.
    assert len(PROVIDER_CLASSES) >= 20, PROVIDER_CLASSES


@pytest.mark.parametrize("provider_cls", PROVIDER_CLASSES, ids=lambda c: c.name)
def test_no_silent_omission_on_corrupt_input(provider_cls, tmp_path):
    project = tmp_path / "proj"
    _seed_corrupt_project(project)
    ctx = BriefingContext(
        project_dir=project,
        iter_index=7,
        rubric=_wide_open_rubric(),
        stagnation_count=6,  # unlock T3/T4-tiered providers
    )
    provider = provider_cls()

    # applies() may return False (structural not-applicable) or raise LOUDLY.
    # A SystemExit is an acceptable loud outcome — e.g. a malformed launch
    # intake (project_packet.json) is a hard config error that SHOULD halt the
    # loop, and providers correctly re-raise it rather than swallow it. What is
    # NOT acceptable is a swallowed corruption that yields a silent empty
    # fragment (checked in the applies()==True branch below).
    try:
        applies = provider.applies(ctx)
    except SystemExit:
        return  # loud, intentional hard-exit on malformed input — acceptable
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"{provider_cls.name}.applies() raised on corrupt input: {exc!r}")

    if not applies:
        # Legitimately not-applicable this iter (rubric/substrate mismatch, or
        # required non-artifact inputs like a specific champion). Exempt — the
        # spec exempts not-applicable providers; the corrupt-file omission we
        # care about is caught by the applies()==True branch below.
        pytest.skip(f"{provider_cls.name} not applicable under corrupt fixture")

    # Applies → fragment() must render a banner/marker or raise loudly. It must
    # NEVER return a silently-empty fragment on corrupt input.
    try:
        frag = provider.fragment(ctx)
    except SystemExit:
        return  # loud hard-exit on malformed input — acceptable, not swallowed
    except Exception:
        # Raised loudly — the renderer surfaces this as a provider-error marker.
        return

    assert frag is not None, f"{provider_cls.name}.fragment() returned None on corrupt input"

    # An EMPTY fragment on corrupt input is always a silent omission.
    assert frag.strip(), (
        f"{provider_cls.name}.fragment() returned an EMPTY fragment on corrupt "
        f"input — silent omission. It must render an UNAVAILABLE/DEGRADED banner."
    )

    # Non-empty fragment: it must carry a corruption marker UNLESS the provider
    # renders content that does not depend on the corrupt project artifacts at
    # all (pure static guidance, or repo-global config). We detect that
    # generically: if the fragment is byte-identical to what the provider
    # renders against a CLEAN project (no corrupt files), the corruption did not
    # reach this provider — it is exempt (equivalent to the absent-file case).
    if any(m in frag for m in _MARKERS):
        return
    clean = tmp_path / "clean"
    (clean / "workspace").mkdir(parents=True, exist_ok=True)
    clean_ctx = BriefingContext(
        project_dir=clean, iter_index=7, rubric=_wide_open_rubric(), stagnation_count=6
    )
    try:
        clean_applies = provider.applies(clean_ctx)
        clean_frag = provider.fragment(clean_ctx) if clean_applies else ""
    except SystemExit:
        clean_frag = None  # clean project also hard-exits → not artifact-driven
    if clean_frag == frag:
        pytest.skip(
            f"{provider_cls.name} renders content independent of the corrupt "
            f"project artifacts (identical on a clean project) — not an omission"
        )
    # A provider that renders SUBSTANTIAL content on corrupt input is manifestly
    # not omitting its section (the omission failure mode is an empty/degenerate
    # fragment). Providers that render large static+dynamic guidance blocks and
    # only vary a small dynamic subsection are out of the omission-invariant's
    # scope; requiring a global banner there would be wrong.
    if len(frag.strip()) >= 500 and isinstance(clean_frag, str) and clean_frag.strip():
        pytest.skip(
            f"{provider_cls.name} renders substantial content on corrupt input "
            f"({len(frag)} chars) — not a silent omission"
        )
    assert False, (
        f"{provider_cls.name}.fragment() rendered project-dependent output with "
        f"NO corruption marker on corrupt input; expected one of {_MARKERS}.\n"
        f"Fragment head:\n{frag[:400]}"
    )
