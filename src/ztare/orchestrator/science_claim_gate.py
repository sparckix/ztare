"""Science-vs-instrument promotion gate.

This deterministic gate does not decide whether a claim is true. It prevents a
specific process failure: promoting an instrument signal, score movement,
simulation anomaly, or route ranking into a paper/science claim before the
artifact names the branch-native object and the hostile falsifiers that shaped
its scope.

The gate is intentionally schema-light so manual Codex/Research Director
sessions can use it without a full supervisor run.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SCIENCE_TARGETS = {"science", "math", "paper", "theorem", "physics"}
INSTRUMENT_TARGETS = {"instrument", "methodology", "apparatus", "diagnostic"}


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v not in (None, "", [])]
    if isinstance(value, tuple):
        return [v for v in value if v not in (None, "", [])]
    return [value] if value not in ("", {}) else []


def _has_text(packet: dict[str, Any], key: str) -> bool:
    return bool(_text(packet.get(key)))


def _has_items(packet: dict[str, Any], key: str) -> bool:
    return bool(_items(packet.get(key)))


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "passed", "closed_passed"}
    return bool(value)


@dataclass(frozen=True)
class ScienceClaimGateVerdict:
    claim_id: str
    claim_target: str
    classification: str
    science_ready: bool
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_next_action: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "claim_id": self.claim_id,
            "claim_target": self.claim_target,
            "classification": self.classification,
            "science_ready": self.science_ready,
            "blocking_reasons": self.blocking_reasons,
            "warnings": self.warnings,
            "required_next_action": self.required_next_action,
        }


def _target(packet: dict[str, Any]) -> str:
    target = _text(packet.get("claim_target")).lower()
    if target:
        return target
    kind = _text(packet.get("claim_kind")).lower()
    if kind in {"ins", "paper", "theorem"}:
        return "paper"
    return "science"


def _closed_falsifier_count(packet: dict[str, Any]) -> int:
    count = 0
    for item in _items(packet.get("falsifiers_run")):
        if not isinstance(item, dict):
            continue
        status = _text(item.get("status")).lower()
        evidence = _items(item.get("evidence_artifacts"))
        killed = _text(item.get("killed_overclaim")) or _text(item.get("overclaim_killed"))
        if status in {"closed", "closed_passed", "passed", "survived", "falsified", "demoted"} and evidence and killed:
            count += 1
    return count


def assess_science_claim_packet(packet: dict[str, Any]) -> ScienceClaimGateVerdict:
    claim_id = _text(packet.get("claim_id")) or _text(packet.get("id")) or "unnamed_claim"
    target = _target(packet)
    blockers: list[str] = []
    warnings: list[str] = []

    if not _has_text(packet, "claim"):
        blockers.append("missing claim text")
    if not _has_text(packet, "trigger_artifact"):
        blockers.append("missing trigger_artifact")
    if not _has_items(packet, "evidence_artifacts"):
        blockers.append("missing evidence_artifacts")

    if target in INSTRUMENT_TARGETS:
        if not _has_text(packet, "instrument_signal"):
            blockers.append("instrument claim missing instrument_signal")
        classification = "instrument_claim_ready" if not blockers else "instrument_claim_blocked"
        return ScienceClaimGateVerdict(
            claim_id=claim_id,
            claim_target=target,
            classification=classification,
            science_ready=False,
            blocking_reasons=blockers,
            warnings=warnings,
            required_next_action=(
                "state as instrument/methodology result, not science claim"
                if not blockers
                else "complete missing instrument evidence fields"
            ),
        )

    for key, reason in (
        ("instrument_signal", "missing instrument_signal: what did the apparatus measure?"),
        ("science_object", "missing science_object: invariant/theorem/mechanism object not named"),
        ("why_not_instrument_only", "missing why_not_instrument_only"),
        ("overclaim_killed", "missing overclaim_killed list"),
        ("rival_explanations", "missing rival_explanations"),
        ("scope_limits", "missing scope_limits"),
        ("nonclaims", "missing nonclaims"),
        ("next_theorem_obligation", "missing next_theorem_obligation"),
    ):
        if key in {"overclaim_killed", "rival_explanations", "scope_limits", "nonclaims"}:
            if not _has_items(packet, key):
                blockers.append(reason)
        elif not _has_text(packet, key):
            blockers.append(reason)

    if _truthy(packet.get("ratio_or_scale_claim")) and not _has_items(packet, "denominator_or_scale_audits"):
        blockers.append("ratio/scale claim missing denominator_or_scale_audits")

    if _truthy(packet.get("formal_target")) and not _has_text(packet, "formal_resource_plan"):
        blockers.append("formal target missing formal_resource_plan")

    closed_falsifiers = _closed_falsifier_count(packet)
    if closed_falsifiers == 0:
        blockers.append("no closed falsifier with killed_overclaim and evidence_artifacts")

    if not _has_items(packet, "paper_wording"):
        warnings.append("paper_wording absent; future prose may drift from scoped claim")

    if blockers:
        classification = "science_claim_blocked_instrument_or_overclaim_risk"
        action = "run or record hostile falsifier and complete science-object packet"
    else:
        classification = "science_claim_scope_ready"
        action = "eligible for Paper/INS wording, still subject to domain proof standards"

    return ScienceClaimGateVerdict(
        claim_id=claim_id,
        claim_target=target,
        classification=classification,
        science_ready=not blockers,
        blocking_reasons=blockers,
        warnings=warnings,
        required_next_action=action,
    )


def load_packet(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("science claim packet must be a JSON object")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assess whether a claim packet clears science-vs-instrument promotion discipline.")
    parser.add_argument("--packet", required=True, type=Path, help="JSON packet to assess.")
    parser.add_argument("--json-out", type=Path, default=None, help="Optional path for verdict JSON.")
    args = parser.parse_args(argv)

    verdict = assess_science_claim_packet(load_packet(args.packet))
    record = verdict.to_record()
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0 if verdict.science_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
