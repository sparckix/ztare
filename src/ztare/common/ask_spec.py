from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from ztare.common.candidate_first_policy import CANDIDATE_FIRST_CONTRACT_ID
from ztare.common.control_work_items import AuthorityLevel, BlockingPolicy, TargetSurface


@dataclass(frozen=True)
class AskSpec:
    contract_id: str
    objective: str
    target_surface: TargetSurface
    expected_output_schema: str
    validator: str
    authority_level: AuthorityLevel
    blocking_policy: BlockingPolicy
    source_file: str = ""
    source_function: str = ""
    examples: tuple[str, ...] = field(default_factory=tuple)
    current_refs: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["examples"] = list(self.examples)
        payload["current_refs"] = list(self.current_refs)
        payload["contract_sha256"] = self.fingerprint()
        return payload

    def fingerprint(self) -> str:
        payload = asdict(self)
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def render_ask_spec_markdown(spec: AskSpec) -> str:
    lines = [
        "## Ask Contract",
        f"- contract_id: {spec.contract_id}",
        f"- contract_sha256: {spec.fingerprint()}",
        f"- target_surface: {spec.target_surface}",
        f"- expected_output_schema: {spec.expected_output_schema}",
        f"- validator: {spec.validator}",
        f"- authority_level: {spec.authority_level}",
        f"- blocking_policy: {spec.blocking_policy}",
    ]
    if spec.source_file or spec.source_function:
        lines.append(f"- source: {spec.source_file}:{spec.source_function}")
    if spec.current_refs:
        lines.append("- current_refs:")
        lines.extend(f"  - {ref}" for ref in spec.current_refs)
    lines.extend(["", "## Objective", "", spec.objective.strip(), ""])
    if spec.examples:
        lines.append("## Examples")
        lines.extend(f"- {example}" for example in spec.examples)
        lines.append("")
    return "\n".join(lines)


def worldmodel_candidate_ask_spec(
    *,
    objective: str,
    current_refs: tuple[str, ...] = (),
) -> AskSpec:
    return AskSpec(
        contract_id=CANDIDATE_FIRST_CONTRACT_ID,
        objective=objective,
        target_surface="candidate",
        expected_output_schema="worldmodel_typed_payload",
        validator="ztare.validator.worldmodel_typed_payload.parse_worldmodel_typed_payload_text",
        authority_level="routing_only",
        blocking_policy="blocks_candidate",
        source_file="src/ztare/common/briefing_pack.py",
        source_function="_worldmodel_task_doc",
        examples=(
            "Assume the current capability set is sufficient unless a typed lowerability receipt proves otherwise.",
            "Use local diagnostics, scratch analyses, and preflights to test candidate laws; report tool gaps as LOWERABILITY_BLOCKED evidence, not direct tool proposals.",
            "If a blocker consumes staged counterexamples, cite the derived analysis artifact, visible diagnostic receipt, or scored candidate that used them.",
            "Treat stopping as a local information-yield decision: if the next visible action is cheap, executable, and informative, run it before returning a blocker.",
            "When stopping after consumed counterexamples, return a local_frontier_decision so the stop can be audited as a bounded search choice.",
        ),
        current_refs=current_refs,
    )
