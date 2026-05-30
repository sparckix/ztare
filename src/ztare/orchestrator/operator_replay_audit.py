"""Replay operator next-test choices from durable artifacts.

GP-190 Phase A asks whether the recent operator-supervisor moves are
recoverable from artifacts, or whether they exist only in chat. This module is
the first cheap falsifier: scan paper/ledger prose for recurring promotion
risks and emit typed discriminator proposals without calling an LLM.

It is intentionally template-based. If the templates fail to recover important
moves, that is a signal about missing artifacts or missing templates, not an
excuse to add a speculative agent.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.ztare.orchestrator.discriminator_queue import (
    DiscriminatorProposal,
    project_dir_from_slug,
)


REPLAY_FILENAME = "next_discriminator_queue.replay.jsonl"


@dataclass(frozen=True)
class ReplayTemplate:
    name: str
    project_hint: str
    required_patterns: tuple[str, ...]
    claim_under_pressure: str
    rival_explanations: tuple[str, ...]
    cheapest_discriminator: str
    kill_condition: str
    required_artifacts: tuple[str, ...]
    narrative_shortcut: str
    instrument_risk: str = ""
    priority: str = "normal"
    severity_level: int = 4
    license_stage: str = "commit"
    weak_test_risk: str = ""

    def matches(self, text: str) -> bool:
        return all(re.search(pattern, text, re.IGNORECASE | re.DOTALL) for pattern in self.required_patterns)

    def proposal(self, *, project: str, trigger_artifact: str) -> DiscriminatorProposal:
        chosen_project = project if self.project_hint == "*" else self.project_hint
        return DiscriminatorProposal(
            project=chosen_project,
            trigger_artifact=trigger_artifact,
            claim_under_pressure=self.claim_under_pressure,
            rival_explanations=list(self.rival_explanations),
            cheapest_discriminator=self.cheapest_discriminator,
            kill_condition=self.kill_condition,
            required_artifacts=list(self.required_artifacts),
            narrative_shortcut=self.narrative_shortcut,
            instrument_risk=self.instrument_risk,
            source="operator_replay_audit",
            priority=self.priority,
            severity_level=self.severity_level,
            license_stage=self.license_stage,
            weak_test_risk=self.weak_test_risk,
            auto_testable=False,
            needs_human=True,
            metadata={"replay_template": self.name},
        )


DEFAULT_TEMPLATES: tuple[ReplayTemplate, ...] = (
    ReplayTemplate(
        name="gravity_empty_box_background_gate",
        project_hint="gp163d_unified_accel",
        required_patterns=(r"empty[- ]box|no[- ]source", r"krylov|background residual|l-bfgs"),
        claim_under_pressure="A source-run gravity signal may be a solver/background artifact.",
        rival_explanations=("unconverged tidal background", "optimizer stiffness", "source metric amplifies background error"),
        cheapest_discriminator="Run the no-source background with the same boundary, stencil, solver, and box before source interpretation.",
        kill_condition="If the empty box does not converge below the declared residual floor, source metrics are inadmissible.",
        required_artifacts=("empty_box_background_summary.json", "solver_residual_history.jsonl"),
        narrative_shortcut="instrument_null_to_physics_null",
        instrument_risk="nonlinear AQUAL background stiffness",
        priority="high",
        severity_level=4,
    ),
    ReplayTemplate(
        name="gravity_large_box_boundary_gate",
        project_hint="gp163d_unified_accel",
        required_patterns=(r"large[- ]box|box[- ]size|L\s*=", r"boundary|walls|finite[- ]box"),
        claim_under_pressure="A diffuse-source enhancement may be a finite-box boundary artifact.",
        rival_explanations=("Dirichlet wall interaction", "diffuse tail bouncing off boundary", "quadratic tidal boundary contamination"),
        cheapest_discriminator="Hold physical settings fixed and expand the box while preserving resolution enough to compare the separator.",
        kill_condition="If the enhancement collapses or the debt profile changes qualitatively as L grows, demote the physics claim.",
        required_artifacts=("large_box_summary.json", "background_residuals.json", "off_core_profile.json"),
        narrative_shortcut="local_positive_to_universal_claim",
        instrument_risk="boundary-conditioned anisotropy",
        priority="high",
        severity_level=5,
    ),
    ReplayTemplate(
        name="gravity_tensor_rotation_gate",
        project_hint="gp163d_unified_accel",
        required_patterns=(r"rotation|angle|45", r"anisotrop|octant|tensor"),
        claim_under_pressure="A tidal anisotropy signal may be grid-locked rather than field-locked.",
        rival_explanations=("Cartesian grid anisotropy", "Krylov reflection artifact", "boundary-normal locking"),
        cheapest_discriminator="Rotate the applied tidal tensor relative to the grid and check whether the hot region follows the field.",
        kill_condition="If the hot sector remains fixed to grid axes or the binary invariant shatters, classify the anisotropy as an artifact.",
        required_artifacts=("orientation_ladder_summary.json", "octant_profiles.json", "binary_baseline.json"),
        narrative_shortcut="scalar_proxy_to_tensor_claim",
        instrument_risk="grid-axis locking",
        priority="high",
        severity_level=5,
    ),
    ReplayTemplate(
        name="background_debt_ladder_gate",
        project_hint="gp163d_unified_accel",
        required_patterns=(r"off[- ]core|background debt|halo|mu", r"separator|gain|enhancement"),
        claim_under_pressure="A local separator/gain may be exporting debt into the background field.",
        rival_explanations=("off-core field load", "mu saturation", "halo stiffening", "cleanup channel"),
        cheapest_discriminator="Report local gain together with off-core debt and mu-saturation across the same sweep axes.",
        kill_condition="If gain rises only by driving background debt or mu saturation to the critical boundary, block promotion.",
        required_artifacts=("background_debt_ladder.json", "mu_profile.json", "separator_gain.json"),
        narrative_shortcut="local_gain_without_background_debt",
        instrument_risk="profit metric omits liability column",
        priority="high",
        severity_level=4,
        weak_test_risk="A debt ladder with only focal/local metrics is weak; it must include the exported-field liability column.",
    ),
    ReplayTemplate(
        name="ns_dynamic_admissibility_gate",
        project_hint="ns_millennium_hunt",
        required_patterns=(r"near[- ]stealth|cloak|cancellation", r"dynamic admissibility|material derivative|Dq/Dt|vector field"),
        claim_under_pressure="A static near-cancellation may be dynamically inadmissible under the actual PDE flow.",
        rival_explanations=("static Taylor-jet overfit", "cancellation manifold not invariant", "missing material-derivative audit"),
        cheapest_discriminator="Evaluate the PDE vector-field derivative of the signed pressure/orientation coordinate on the near-cloak ensemble.",
        kill_condition="If near-cloaks remain tangent to the cancellation manifold while torque stays active, the dynamic-repulsion claim fails.",
        required_artifacts=("dynamic_admissibility_audit.json", "near_cloak_ensemble.json", "qdot_distribution.json"),
        narrative_shortcut="static_snapshot_to_dynamic_claim",
        instrument_risk="static ansatz mistaken for trajectory",
        priority="high",
        severity_level=5,
    ),
    ReplayTemplate(
        name="generic_farther_tail_asymptotic_gate",
        project_hint="*",
        required_patterns=(r"holdout|farther[- ]tail|tail", r"asymptot|extrapolat|stability|drift"),
        claim_under_pressure="A finite-window holdout pass may not survive the farther-tail/asymptotic regime.",
        rival_explanations=("finite-window overfit", "missing asymptotic term", "coefficient drift outside the visible scale"),
        cheapest_discriminator="Extend the deterministic farther-tail grid and refit/report coefficient drift before promoting the form.",
        kill_condition="If the fitted structure or key coefficient drifts beyond the declared tolerance at the farther tail, demote the claim to finite-window.",
        required_artifacts=("farther_tail_stability.json", "fit_result.json", "eval_history.jsonl"),
        narrative_shortcut="local_positive_to_universal_claim",
        instrument_risk="finite-window validation treated as asymptotic law",
        priority="high",
        severity_level=4,
        weak_test_risk="A same-distribution holdout is too weak for asymptotic promotion; the tail must move the scale.",
    ),
    ReplayTemplate(
        name="generic_retrieval_trap_gate",
        project_hint="*",
        required_patterns=(r"retrieval|ontology trap|known law|named formula|denylist", r"derive|discover|candidate|mutator"),
        claim_under_pressure="A candidate may be retrieved from memorized/named structure rather than discovered from the substrate.",
        rival_explanations=("ontology recognition", "literal-name leakage", "benchmark formula retrieval"),
        cheapest_discriminator="Run the anti-retrieval variant with denied names/symbols and noncanonical variable presentation.",
        kill_condition="If performance collapses only when canonical names are masked, record retrieval rather than discovery.",
        required_artifacts=("anti_retrieval_run_summary.json", "last_prompt_debug.txt", "thesis_denylist"),
        narrative_shortcut="score_gain_to_discovery_claim",
        instrument_risk="semantic leakage through canonical labels",
        priority="high",
        severity_level=5,
    ),
    ReplayTemplate(
        name="generic_complexity_laundering_gate",
        project_hint="*",
        required_patterns=(r"parameter|complexity|bic|aic|mdl|effective[- ]k|hidden[- ]parameter", r"score|fit|improvement|candidate"),
        claim_under_pressure="A score improvement may be hidden complexity rather than structural discovery.",
        rival_explanations=("effective-K laundering", "helper-function parameter hiding", "wrapper complexity"),
        cheapest_discriminator="Run the effective-complexity/MDL audit and compare against the nearest nested simpler rival.",
        kill_condition="If the simpler nested rival is statistically indistinguishable after complexity penalty, block promotion.",
        required_artifacts=("complexity_audit.json", "fit_result.json", "candidate_source.py"),
        narrative_shortcut="score_gain_to_discovery_claim",
        instrument_risk="complexity omitted from the reported score",
        severity_level=4,
    ),
    ReplayTemplate(
        name="generic_distribution_shift_gate",
        project_hint="*",
        required_patterns=(r"out[- ]of[- ]sample|holdout|validation", r"distribution|stratif|class|regime|shift"),
        claim_under_pressure="An out-of-sample pass may be a nearby split that misses the actual regime shift.",
        rival_explanations=("stratification leakage", "holdout not distributionally dark", "class/regime imbalance"),
        cheapest_discriminator="Audit feature/class distributions for visible vs holdout and run a regime-stratified holdout.",
        kill_condition="If the claimed holdout does not cover the hostile regime, do not treat it as dark validation.",
        required_artifacts=("holdout_distribution_audit.json", "split_manifest.json", "validation_summary.json"),
        narrative_shortcut="local_positive_to_universal_claim",
        instrument_risk="holdout label overstates distributional distance",
        severity_level=4,
    ),
    ReplayTemplate(
        name="generic_cross_domain_transfer_license_gate",
        project_hint="*",
        required_patterns=(r"isomorphism|duality|analogy|cross[- ]domain|transfer", r"shared primitive|non[- ]shared physics|license"),
        claim_under_pressure="A cross-domain analogy may be rhetorically useful but formally unlicensed.",
        rival_explanations=("shared metaphor without shared operator", "domain-specific physics omitted", "scratchpad idea promoted as finding"),
        cheapest_discriminator="Require a transfer-license note naming the shared primitive, non-shared physics, conserved observable, and failure mode before F/INS promotion.",
        kill_condition="If the mapping cannot name both the shared primitive and the non-shared physics, keep it scratchpad-only.",
        required_artifacts=("cross_domain_transfer_license.md", "source_artifact_manifest.txt"),
        narrative_shortcut="analogy_to_isomorphism",
        instrument_risk="stochastic resonance mistaken for proof transfer",
        severity_level=4,
        license_stage="commit",
        weak_test_risk="The license gate should not block scratchpad ideation; it only blocks formal promotion.",
    ),
)


def infer_project_from_source(path: Path, text: str) -> str:
    joined = f"{path} {text[:4000]}".lower()
    if "ns_millennium" in joined or "gp186" in joined:
        return "ns_millennium_hunt"
    if "gp163d" in joined or "aqual" in joined or "gravity" in joined:
        return "gp163d_unified_accel"
    return "unknown"


def proposals_from_sources(sources: Iterable[Path], *, project_override: str | None = None) -> list[DiscriminatorProposal]:
    proposals: list[DiscriminatorProposal] = []
    seen: set[tuple[str, str, str]] = set()
    for source in sources:
        try:
            text = source.read_text(encoding="utf-8")
        except OSError:
            continue
        for template in DEFAULT_TEMPLATES:
            if template.matches(text):
                if (
                    project_override
                    and template.project_hint != "*"
                    and template.project_hint != project_override
                ):
                    continue
                # Templates are domain-scoped. A source like the global
                # experiment track record can mention both NS and gravity, so
                # file-level project inference is too coarse here.
                chosen_project = (
                    project_override
                    if template.project_hint == "*" and project_override
                    else template.project_hint
                )
                key = (chosen_project, template.name)
                if key in seen:
                    continue
                seen.add(key)
                proposals.append(template.proposal(project=chosen_project, trigger_artifact=str(source)))
    return proposals


def write_replay_queue(project_dir: Path, proposals: Iterable[DiscriminatorProposal]) -> Path:
    out = project_dir / "workspace" / REPLAY_FILENAME
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for proposal in proposals:
            f.write(json.dumps(proposal.to_record(), sort_keys=True) + "\n")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay operator discriminator choices from durable artifacts.")
    parser.add_argument("--project", required=True, help="Project slug or project directory receiving replay queue.")
    parser.add_argument("sources", nargs="+", type=Path, help="Markdown/text artifacts to scan.")
    args = parser.parse_args()

    project_dir = project_dir_from_slug(args.project)
    proposals = [
        p for p in proposals_from_sources(args.sources, project_override=project_dir.name)
        if p.project == project_dir.name or p.project == args.project
    ]
    if not proposals:
        proposals = proposals_from_sources(args.sources, project_override=project_dir.name)
    out = write_replay_queue(project_dir, proposals)
    print(f"operator replay audit: wrote {len(proposals)} proposal(s) to {out}")
    for proposal in proposals:
        record = proposal.to_record()
        print(f"- {record['metadata'].get('replay_template')}: {record['cheapest_discriminator'][:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
