"""Decision-facing Markdown reports for autonomous JaggedThoughts compilations."""

from __future__ import annotations

from pathlib import Path

from .autonomy import CompiledAutonomousStrategy
from .jaggedthoughts import Program


def _program_text(program: Program) -> str:
    if program.terminal_id is not None:
        return program.terminal_id.removeprefix("act::").removeprefix("when::")
    children = ", ".join(_program_text(child) for child in program.children)
    return f"{program.operator_id}({children})"


def render_autonomous_strategy_report(
    compiled: CompiledAutonomousStrategy,
    *,
    dest: str | Path | None = None,
) -> str:
    summary = compiled.summary()
    lines = [
        f"# JaggedThoughts — {compiled.question}",
        "",
        f"Status: `{compiled.status}`  ",
        f"Evidence epoch: `{compiled.evidence_epoch}`  ",
        f"Profile: `{compiled.profile_sha256}`",
        "",
        "## Mechanism version space",
        "",
        "| Mechanism | Verdict | Replay MAE | Actor response |",
        "|---|---:|---:|---:|",
    ]
    model_by_id = {
        model.mechanism_id: model for model in compiled.version_space.mechanisms
    }
    for verdict in compiled.version_space.verdicts:
        model = model_by_id[verdict.mechanism_id]
        lines.append(
            f"| `{verdict.mechanism_id}` | {verdict.status} | "
            f"{verdict.replay_mean_absolute_error:.4g} | "
            f"{'yes' if model.has_endogenous_response else 'no'} |"
        )
    synthesis = compiled.policy_synthesis
    if synthesis is not None:
        programs = {
            row.program_id: row
            for row in synthesis.enumeration.programs_of_type("Policy")
        }
        evaluations = {row.program_id: row for row in synthesis.evaluations}
        lines.extend([
            "",
            "## Robust policy frontier",
            "",
            "Each score is sign-normalized so larger is preferred and is the "
            "minimum across surviving mechanisms.",
            "",
            "| Policy | Robust objectives |",
            "|---|---:|",
        ])
        for program_id in synthesis.certificate.frontier_program_ids:
            program = programs[program_id]
            values = ", ".join(
                f"{value:.4g}"
                for value in evaluations[program_id].objective_values
            )
            lines.append(f"| `{_program_text(program)}` | {values} |")
        lines.extend([
            "",
            f"Local peaks: {len(synthesis.certificate.local_peak_program_ids)}. "
            f"Frozen-scope complete: {synthesis.certificate.scope_closed}. "
            f"Representation-audited decision complete: "
            f"{synthesis.certificate.decision_closed}.",
        ])
        residuals = synthesis.certificate.representation_audit.residuals
        if residuals:
            lines.extend(["", "Representation residuals:"])
            lines.extend(f"- {row}" for row in residuals)
    lines.extend(["", "## Next evidence action", ""])
    agenda = compiled.probe_agenda
    if agenda is None or agenda.selected_probe is None:
        lines.append("No admitted probe currently has positive information yield.")
    else:
        probe = agenda.selected_probe
        selected = agenda.selection.selected
        lines.extend([
            f"Selected probe: `{probe.probe_id}` using registered adapter "
            f"`{probe.adapter_id}`.",
            "",
            f"Predicted identification: {selected.identification:.4g} bits; "
            f"cost: {probe.cost.total_units:.4g}; "
            f"density: {selected.yield_density:.4g}.",
            "",
            "The adapter may only read or act within the declared authority "
            "envelope; material strategy actions remain external decisions.",
        ])
    lines.extend([
        "",
        "## Representation diagnostics",
        "",
        f"Next refinement action: `{compiled.diagnostics.next_action}` — "
        f"{compiled.diagnostics.next_action_reason}.",
        "",
    ])
    if compiled.diagnostics.residuals:
        lines.extend(
            f"- `{row.kind}`: {row.counterexample} Refinement: "
            f"{row.required_refinement}."
            for row in compiled.diagnostics.residuals
        )
    else:
        lines.append("No compiled representation residual is active.")
    lines.extend([
        "",
        "## Capability boundary",
        "",
        "This artifact certifies bounded enumeration, replay consistency, "
        "committee-robust evaluation, and guarded probe selection. It does not "
        "certify that the state language contains every strategically relevant "
        "variable or that an external organization will realize simulated effects.",
        "",
    ])
    rendered = "\n".join(lines)
    if dest is not None:
        Path(dest).write_text(rendered, encoding="utf-8")
    return rendered


__all__ = ["render_autonomous_strategy_report"]
