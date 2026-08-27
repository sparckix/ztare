"""Human-readable JaggedThoughts decision reports."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .jaggedthoughts import Program
from .evaluation import score_program
from .exploration import build_exploration_agenda
from .profile import CompiledJaggedThoughtsProfile, program_terminal_ids


def _program_label(program: Program) -> str:
    return " + ".join(program_terminal_ids(program))


def _number(value: float) -> str:
    return f"{value:.4g}"


def _table(headers: Iterable[str], rows: Iterable[Iterable[str]]) -> list[str]:
    header = tuple(headers)
    result = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    result.extend("| " + " | ".join(row) + " |" for row in rows)
    return result


def render_strategy_report(
    compiled: CompiledJaggedThoughtsProfile,
    *,
    dest: str | Path | None = None,
) -> str:
    """Render a named decision surface from a compiled certificate."""
    certificate = compiled.certificate
    programs = {
        program.program_id: program
        for program in compiled.enumeration.programs
        if program.program_id in certificate.target_program_ids
    }
    evaluations = {
        evaluation.program_id: evaluation for evaluation in compiled.evaluations
    }
    claims = {claim.claim_id: claim for claim in compiled.claims}
    dispositions = {
        disposition.claim_id: disposition
        for disposition in compiled.claim_dispositions
    }

    if certificate.decision_closed:
        state = "Decision space closed under the declared representation audit."
    elif certificate.scope_closed:
        state = (
            "The frozen grammar is exhausted. The decision remains open because "
            f"representation is {certificate.representation_audit.status}."
        )
    else:
        state = "The frozen grammar still has evaluation, evidence, or budget debt."

    lines = [
        f"# JaggedThoughts decision report — {compiled.title}",
        "",
        f"**Decision question:** {compiled.decision_question}",
        f"**Owner:** {compiled.owner}  ",
        f"**As of:** {compiled.as_of}  ",
        f"**State:** {state}",
        "",
        "## Decision boundary",
        "",
        f"- Grammar: `{compiled.grammar.grammar_id}` version `{compiled.grammar.version}`",
        "- Evaluation model: `"
        + (
            compiled.evaluation_model.model_id
            if compiled.evaluation_model is not None
            else certificate.scope.evaluation_model_id.split("@sha256:", 1)[0]
        )
        + "`",
        f"- Landscape mode: `{certificate.scope.landscape_mode}`",
        f"- Evidence epoch: `{certificate.scope.evidence_epoch}`",
        "- Aggregation: `"
        + (
            compiled.evaluation_model.aggregation
            if compiled.evaluation_model is not None
            else "table"
        )
        + "`",
        f"- Candidate programs: `{len(certificate.target_program_ids)}`",
        f"- Global frontier: `{len(certificate.frontier_program_ids)}`",
        f"- Local peaks: `{len(certificate.local_peak_program_ids)}`",
        "",
        "## Global frontier",
        "",
    ]

    objective_names = certificate.scope.objective_names
    frontier_rows = []
    for program_id in certificate.frontier_program_ids:
        evaluation = evaluations[program_id]
        frontier_rows.append((
            _program_label(programs[program_id]),
            *(_number(value) for value in evaluation.objective_values),
        ))
    lines.extend(_table(("Option", *objective_names), frontier_rows))

    if compiled.evaluation_model is not None:
        lines += ["", "## Scenario breakdown for frontier options", ""]
        scenario_rows = []
        for program_id in certificate.frontier_program_ids:
            program = programs[program_id]
            for scenario_score in score_program(
                program,
                compiled.evaluation_model,
            ):
                scenario_rows.append((
                    _program_label(program),
                    scenario_score.scenario_id,
                    *(_number(value) for value in scenario_score.values),
                    ", ".join(scenario_score.applied_factor_ids),
                ))
        lines.extend(_table(
            (
                "Option",
                "Scenario",
                *compiled.evaluation_model.objective_names,
                "Applied factors",
            ),
            scenario_rows,
        ))

    lines += ["", "## Neighborhood-relative local peaks", ""]
    peak_rows = []
    frontier_set = set(certificate.frontier_program_ids)
    for program_id in certificate.local_peak_program_ids:
        evaluation = evaluations[program_id]
        peak_rows.append((
            _program_label(programs[program_id]),
            "global-frontier" if program_id in frontier_set else "local-only",
            *(_number(value) for value in evaluation.objective_values),
        ))
    lines.extend(_table(("Option", "Peak class", *objective_names), peak_rows))

    surfaced_ids = tuple(dict.fromkeys((
        *certificate.frontier_program_ids,
        *certificate.local_peak_program_ids,
    )))
    lines += ["", "## Burdens of proof on surfaced options", ""]
    for program_id in surfaced_ids:
        program = programs[program_id]
        lines.append(f"### {_program_label(program)}")
        lines.append("")
        if not program.claim_ids:
            lines.append("- No burden claims are attached to this program.")
        for claim_id in program.claim_ids:
            claim = claims.get(claim_id)
            disposition = dispositions.get(claim_id)
            status = disposition.status if disposition else "missing"
            evidence_ref = disposition.evidence_ref if disposition else "—"
            text = claim.text if claim else "Undefined claim"
            kind = claim.kind if claim else "unknown"
            lines.append(
                f"- **{kind} / {status}:** {text} — evidence `{evidence_ref}`"
            )
        lines.append("")

    lines += ["## Eliminations and residuals", ""]
    if certificate.dominated:
        lines.append("### Dominated")
        lines.append("")
        for witness in certificate.dominated:
            lines.append(
                f"- {_program_label(programs[witness.dominated_program_id])} "
                f"is dominated by {_program_label(programs[witness.dominator_program_id])}."
            )
        lines.append("")
    if certificate.infeasible:
        lines.append("### Infeasible")
        lines.append("")
        for witness in certificate.infeasible:
            lines.append(
                f"- {_program_label(programs[witness.program_id])}: refuted claims "
                f"{', '.join(witness.refuted_claim_ids)}."
            )
        lines.append("")
    if certificate.equivalent:
        lines.append("### Behaviorally equivalent")
        lines.append("")
        for witness in certificate.equivalent:
            lines.append(
                f"- {_program_label(programs[witness.program_id])} is represented by "
                f"{_program_label(programs[witness.representative_program_id])}."
            )
        lines.append("")
    if certificate.residuals:
        lines.append("### Open residuals")
        lines.append("")
        for residual in certificate.residuals:
            subject = (
                _program_label(programs[residual.program_id])
                if residual.program_id in programs
                else "enumeration"
            )
            lines.append(f"- **{residual.kind} / {subject}:** {residual.detail}")
        lines.append("")
    if not (
        certificate.infeasible
        or certificate.equivalent
        or certificate.residuals
    ):
        lines.append("- Every non-frontier program has a dominance witness.")
        lines.append("")

    lines += ["## Representation status", ""]
    lines.append(
        f"- Status: `{certificate.representation_audit.status}`"
    )
    for residual in certificate.representation_audit.residuals:
        lines.append(f"- Residual: {residual}")
    if certificate.representation_audit.status == "unassessed":
        lines.append(
            "- Next action: challenge this grammar with an independently authored "
            "operator/terminal expansion under the same evaluation surface."
        )

    lines += ["", "## Bound sources", ""]
    lines.extend(_table(
        ("Source", "Path", "SHA-256"),
        (
            (source.source_id, source.relative_path, source.content_sha256)
            for source in compiled.evidence_manifest.sources
        ),
    ))
    agenda = build_exploration_agenda(compiled)
    lines += ["", "## Next-question agenda", ""]
    lines.append(f"**Next action:** {agenda.next_action}")
    lines += ["", agenda.boundary, ""]
    pivotal_rows = []
    for index, probe in enumerate(agenda.probes[:10], start=1):
        pivotal_rows.append((
            str(index),
            "yes" if probe.decision_pivotal else "no",
            " + ".join(probe.factor_ids),
            str(probe.frontier_outcome_count),
            str(probe.max_frontier_membership_change),
            _number(probe.information_per_cost),
            _number(probe.cost),
            " | ".join(probe.tests),
        ))
    lines.extend(_table(
        (
            "Rank",
            "Pivotal",
            "Factor probe",
            "Frontier outcomes",
            "Max membership change",
            "Information / cost",
            "Cost",
            "Declared test",
        ),
        pivotal_rows,
    ))
    top_pivotal = next(
        (probe for probe in agenda.probes if probe.decision_pivotal),
        None,
    )
    if top_pivotal is not None:
        lines += ["", "### Top probe consequences", ""]
        lines.append(
            "- Baseline frontier: "
            + "; ".join(
                _program_label(programs[program_id])
                for program_id in agenda.baseline_frontier_program_ids
            )
        )
        for index, outcome in enumerate(
            top_pivotal.frontier_outcomes,
            start=1,
        ):
            lines.append(
                f"- Possible frontier {index}: "
                + "; ".join(
                    _program_label(programs[program_id])
                    for program_id in outcome
                )
            )
    lines += [
        "",
        "<details>",
        "<summary>Audit identities</summary>",
        "",
        f"- scope: `{certificate.scope.scope_id}`",
        f"- grammar: `{compiled.grammar.grammar_digest}`",
        f"- enumeration: `{compiled.enumeration.enumeration_digest}`",
        f"- evidence manifest: `{compiled.evidence_manifest.manifest_sha256}`",
        f"- decision surface: `{certificate.scope.evaluation_model_id}`",
        f"- certificate: `{certificate.certificate_sha256}`",
        "",
        "</details>",
        "",
    ]
    rendered = "\n".join(lines)
    if dest is not None:
        Path(dest).write_text(rendered, encoding="utf-8")
    return rendered
