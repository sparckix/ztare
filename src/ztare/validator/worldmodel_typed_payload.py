from __future__ import annotations

import json

from ztare.common.candidate_first_policy import (
    CAPABILITY_PROPOSAL_RECEIPT,
    LOWERABILITY_BLOCKED_RECEIPT,
    REGISTERED_ACTION_RECEIPT,
    candidate_first_empty_candidate_decision,
    candidate_first_policy_text,
)
from ztare.common.structured_blocks import balanced_object_after_marker, json_object_span
from ztare.common.science_output_policy import SCIENCE_OUTPUT_POLICY
from ztare.common.sealed_boundary_cegar import (
    boundary_cegar_candidate_delta_lowerability,
    validate_lowerability_blocked_receipt,
)
from ztare.common.worldmodel_carrier_purity import validate_worldmodel_carrier_source
from ztare.common.visible_workbench_actions import (
    is_visible_workbench_local_diagnostic_receipt,
)
from ztare.common.leaf_workbench_contract import (
    validate_leaf_workbench_action_request,
    validate_leaf_workbench_capability_proposal,
    validate_leaf_workbench_receipt,
)
from ztare.worldmodel.leaf_workbench import (
    WORLD_MODEL_LEAF_WORKBENCH_CONTRACT,
    render_worldmodel_leaf_workbench_prompt,
)
from ztare.worldmodel.patch_carrier_contract import patch_carrier_brief_line


SCHEMA = "ztare-worldmodel-mutator-payload-v1"

_CAPABILITY_ALIASES = {
    "latest_replay_diagnostics": "inspect_replay_residual_quotient",
    "latest_replay_diagnostics_after_abduce": "inspect_replay_residual_quotient",
}
_CONTROL_RECEIPT_KEYS = (
    "control_receipts",
    "control_receipt",
    "receipts",
    "typed_receipts",
)
_THESIS_KEYS = (
    "thesis_markdown",
    "thesis_prose",
    "thesis",
    "rationale",
    "analysis_markdown",
)
_CARRIER_KEYS = (
    "test_model_py",
    "test_model.py",
    "python_code",
    "code",
    "source",
    "test_model",
    "PROGRAM",
    "program",
    "candidate_source",
    "candidate_py",
    "model_py",
)
_KNOWN_CONTROL_RECEIPT_TYPES = (
    "STRATEGY_CARD_DISCHARGE",
    "LEAF_WORKBENCH_RECEIPT",
    "VISIBLE_WORKBENCH_DIAGNOSTIC",
    REGISTERED_ACTION_RECEIPT,
    CAPABILITY_PROPOSAL_RECEIPT,
    LOWERABILITY_BLOCKED_RECEIPT,
    "INVESTIGATED",
)

_RENDERED_CONTROL_MARKERS = (
    ("STRATEGY_CARD_DISCHARGE:", "STRATEGY_CARD_DISCHARGE"),
    ("LEAF_WORKBENCH_ACTION_REQUEST:", REGISTERED_ACTION_RECEIPT),
    ("LEAF_WORKBENCH_RECEIPT:", "LEAF_WORKBENCH_RECEIPT"),
    ("VISIBLE_WORKBENCH_DIAGNOSTIC:", "VISIBLE_WORKBENCH_DIAGNOSTIC"),
    ("LEAF_WORKBENCH_CAPABILITY_PROPOSAL:", CAPABILITY_PROPOSAL_RECEIPT),
    ("LEAF_WORKBENCH_CAPABILITY_PROPOSAL_QUARANTINED:", "LEAF_WORKBENCH_CAPABILITY_PROPOSAL_QUARANTINED"),
    ("LOWERABILITY_BLOCKED:", LOWERABILITY_BLOCKED_RECEIPT),
    ("INVESTIGATED:", "INVESTIGATED"),
)

WORLDMODEL_TYPED_PAYLOAD_CONTRACT_PROMPT = """
WORLDMODEL TYPED PAYLOAD CONTRACT:
- Return ONLY one raw JSON object. Do not wrap it in markdown fences.
- Required keys:
  - `control_receipts`: list. Use objects like
    {"type":"STRATEGY_CARD_DISCHARGE","payload":{...}} for Strategy Office receipts.
    If active Strategy Office obligations are listed, include one receipt object
    for EACH listed card, using the exact full `failure_family_sha`; do not use
    SHA prefixes, comments, or prose substitutes.
  - `thesis_markdown`: string. Concise explanation / Logic DAG / unresolved boundary.
- `test_model_py`: string. Complete executable `test_model.py` source only
  when submitting a candidate delta. Omit or leave empty only for typed
  workbench action requests or `LOWERABILITY_BLOCKED`
  receipts.
- On a task-hypothesis turn, `test_model_py` is instead a standalone module
  defining exactly one `GOAL_PREDICATE(state) -> bool`. Do not import, repeat,
  or mutate the transition carrier; the kernel binds the immutable companion.
- If the science turn is stuck, the rider is free-form one-line text; do not
  surface a JSON schema for it in the prompt.
- Do not place receipts inside `test_model_py`; the runner will render them outside code.
- Do not place markdown fences inside `test_model_py`.
- If visible evidence cannot lower to executable gamma code, do not submit
  executable carrier code. Emit a registered action request, a morphism-shaped
  `LOWERABILITY_BLOCKED` with attempted visible tools,
  attempted candidate family, obstruction, missing witness/sensor, next action,
  and evidence refs. {SCIENCE_OUTPUT_POLICY_TOOL_GAP_TEXT}
- Candidate code may be a direct executable carrier such as
  `def step(grid, action, t): ...`, `PROGRAM = ...`, or a lowerable
  `WORLD_MODEL_SPEC`.
- To preserve a prior executable artifact without ambient imports, use the
  gate-owned patch-base carrier only when this prompt lists an authoritative
  `patch_base_ref` and full `patch_base_sha`:
  {PATCH_CARRIER_BRIEF_LINE}
  Never invent a patch-base source_ref or sha. If no base is listed, submit a
  direct executable carrier instead.
  {DYNAMICS_ASSUMPTION_LINE}
  For ARC/worldmodel rubrics, `state` is the grid-shaped state passed by the
  adapter; do not promote colors or coordinates into the kernel contract.
  Do not import prior submissions with `__file__`, `importlib`, cwd paths, or
  workspace reads; the deterministic harness loads the base and applies the
  delta under gate authority.
  Treat coordinate-only deltas as diagnostic charts unless you state the
  invariant that makes them transport; full replay/holdout decides.
- `WORLD_MODEL_SPEC` means a literal catalog spec with non-empty `actions`.
  `PATCH_DELTA_SPEC` is the same literal operation algebra applied after an
  authoritative PATCH_BASE while retaining the source state for guards and
  crossing relations. Prefer it over hand-translating a registered operation
  into Python. It is a patch delta, not a standalone carrier.
  It may use only the catalog operators accepted by `ztare.worldmodel.spec_catalog`
  (for example `translate_block`, `recolor_map`, `consume_extremal`,
  `accumulate_extremal`, `identity`) plus documented guards. Never invent an op
  name such as `replace_cells`, `postprocess_clear_pair`, or a one-off overlay.
  If you are writing hand-authored Python, omit `WORLD_MODEL_SPEC` and define
  `step(grid, action, t)`, `PROGRAM`, or aliases directly.
{CANDIDATE_FIRST_POLICY}
"""


def _dynamics_assumption_line(dynamics_assumption: "str | None" = None) -> str:
    import os as _os
    da = (_os.environ.get("ZTARE_DYNAMICS_ASSUMPTION") or dynamics_assumption or "markovian").strip().lower()
    if da == "lawful_time":
        return (
            "This substrate declares lawful time-dependence (dynamics_assumption: "
            "lawful_time): the `t` argument is admissible physics — laws may use t "
            "in lawful, compressible form (arithmetic relations with state), never "
            "as a per-step lookup; held-out rollout still kills memorization."
        )
    return (
        "If a domain has clocked dynamics, derive the phase from state/action "
        "evidence or from an adapter-provided state feature."
    )


def worldmodel_typed_payload_contract_prompt(dynamics_assumption: "str | None" = None) -> str:
    return (
        WORLDMODEL_TYPED_PAYLOAD_CONTRACT_PROMPT.replace(
            "{PATCH_CARRIER_BRIEF_LINE}",
            patch_carrier_brief_line(),
        ).replace(
            "{DYNAMICS_ASSUMPTION_LINE}",
            _dynamics_assumption_line(dynamics_assumption),
        ).replace(
            "{SCIENCE_OUTPUT_POLICY_TOOL_GAP_TEXT}",
            SCIENCE_OUTPUT_POLICY.tool_gap_text(),
        ).replace(
            "{CANDIDATE_FIRST_POLICY}",
            "- " + candidate_first_policy_text(),
        ).rstrip()
        + "\n\n"
        + render_worldmodel_leaf_workbench_prompt()
        + "\n"
    )


def parse_worldmodel_typed_payload_text(text: str) -> dict[str, object]:
    """Extract the outer worldmodel typed-payload object from LLM text.

    Generic "first JSON object" recovery is unsafe here because receipts inside
    ``control_receipts`` are themselves JSON-shaped. The schema carrier is the
    object that names a worldmodel payload field, preferably one with an
    executable carrier.
    """
    source = text or ""

    # The contract's carrier is the outer envelope.  Parse that identity before
    # searching nested objects: receipt payloads legitimately contain fields
    # named ``source`` or artifact refs named ``test_model.py``.  Treating one
    # of those properties as a candidate carrier can erase a control-only
    # transition and coerce it into executable-candidate validation.
    whole = _parse_whole_worldmodel_payload(source)
    if whole is not None:
        return whole

    candidates: list[dict[str, object]] = []
    start = source.find("{")
    while start >= 0:
        span = json_object_span(source, start)
        if span is None:
            start = source.find("{", start + 1)
            continue
        raw = source[span[0] : span[1]]
        try:
            obj = json.loads(raw, strict=False)
        except json.JSONDecodeError:
            start = source.find("{", start + 1)
            continue
        if isinstance(obj, dict) and _looks_like_worldmodel_payload(obj):
            candidates.append(_normalize_worldmodel_payload_object(obj))
        start = source.find("{", start + 1)
    if not candidates:
        repaired = _parse_repaired_worldmodel_payload(source)
        if repaired is not None:
            return repaired
        fallback = _parse_whole_worldmodel_payload(source)
        if fallback is not None:
            return fallback
        raise ValueError("No worldmodel typed-payload JSON object found.")
    candidates.sort(
        key=lambda obj: (
            _worldmodel_envelope_identity_rank(obj),
            len(json.dumps(obj, sort_keys=True, default=str)),
            bool(_maybe_test_model_py(obj).strip()),
        ),
        reverse=True,
    )
    return candidates[0]


def _worldmodel_envelope_identity_rank(obj: dict[str, object]) -> int:
    """Rank schema-envelope identity ahead of carrier-looking properties."""

    has_receipts = any(key in obj for key in _CONTROL_RECEIPT_KEYS)
    has_thesis = any(key in obj for key in _THESIS_KEYS)
    if has_receipts and has_thesis:
        return 3
    if has_receipts:
        return 2
    if has_thesis:
        return 1
    return 0


def _parse_repaired_worldmodel_payload(text: str) -> dict[str, object] | None:
    """Recover the typed worldmodel payload from common near-JSON emissions.

    This parser is intentionally schema-bound. It does not return the first
    inner object it can decode, because doing so can collapse a complete carrier
    into a stray receipt. It only accepts a repaired object that still names a
    worldmodel payload field.
    """
    clean = (text or "").strip()
    if not clean.startswith("{"):
        return None
    repairs = [clean]
    if "}}}],\"thesis_markdown\"" in clean:
        repairs.append(clean.replace("}}}],\"thesis_markdown\"", "}}],\"thesis_markdown\"", 1))
    if "}}}], \"thesis_markdown\"" in clean:
        repairs.append(clean.replace("}}}], \"thesis_markdown\"", "}}], \"thesis_markdown\"", 1))
    repairs.extend(_spilled_control_receipt_type_repairs(clean))
    for candidate in repairs:
        try:
            obj = json.loads(candidate, strict=False)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and _looks_like_worldmodel_payload(obj):
            return _normalize_worldmodel_payload_object(obj)
    return None


def _spilled_control_receipt_type_repairs(text: str) -> list[str]:
    """Repair one bounded envelope drift in control receipt arrays.

    Some agent responses place an allowed receipt ``type`` inside the receipt
    payload, omit the row-closing brace, then repeat the same type as a
    top-level payload key.  This is not free-form JSON repair: only known
    receipt type literals immediately before a worldmodel thesis field are
    canonicalized, and normal schema validation still runs afterward.
    """

    out: list[str] = []
    for receipt_type in _KNOWN_CONTROL_RECEIPT_TYPES:
        marker = f'"type":"{receipt_type}"'
        for thesis_key in _THESIS_KEYS:
            bad = marker + "}]," + marker + f'}}],"{thesis_key}"'
            if bad not in text:
                continue
            good = marker + "}}],\"" + thesis_key + "\""
            out.append(text.replace(bad, good, 1))
    return out


def _parse_whole_worldmodel_payload(text: str) -> dict[str, object] | None:
    clean = (text or "").strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()
    if not clean.startswith("{"):
        return None
    try:
        obj = json.loads(clean, strict=False)
    except json.JSONDecodeError:
        return None
    if isinstance(obj, dict) and _looks_like_worldmodel_payload(obj):
        return _normalize_worldmodel_payload_object(obj)
    return None


def _looks_like_worldmodel_payload(obj: dict[str, object]) -> bool:
    return any(key in obj for key in (*_CONTROL_RECEIPT_KEYS, *_THESIS_KEYS, *_CARRIER_KEYS, "files"))


def _normalize_worldmodel_payload_object(obj: dict[str, object]) -> dict[str, object]:
    """Canonicalize the typed-payload envelope without weakening validation."""

    normalized = dict(obj)
    if "control_receipts" not in normalized:
        for key in _CONTROL_RECEIPT_KEYS:
            if key in normalized:
                value = normalized.get(key)
                if key == "control_receipt" and isinstance(value, dict):
                    normalized["control_receipts"] = [value]
                else:
                    normalized["control_receipts"] = value
                break
    top_level_receipt_type = str(normalized.get("type") or "").strip()
    if top_level_receipt_type in _KNOWN_CONTROL_RECEIPT_TYPES:
        payload = normalized.get("payload")
        if not isinstance(payload, dict):
            payload = {
                key: value
                for key, value in normalized.items()
                if key
                not in {
                    "control_receipts",
                    "control_receipt",
                    "type",
                    "thesis_markdown",
                    "thesis_prose",
                    "test_model_py",
                    "files",
                }
            }
        if _top_level_receipt_payload_is_complete(top_level_receipt_type, payload):
            receipts = normalized.get("control_receipts")
            row = {"type": top_level_receipt_type, "payload": payload}
            if isinstance(receipts, list):
                normalized["control_receipts"] = [*receipts, row]
            elif receipts:
                normalized["control_receipts"] = [receipts, row]
            else:
                normalized["control_receipts"] = [row]
    if "thesis_markdown" not in normalized:
        for key in _THESIS_KEYS:
            value = normalized.get(key)
            if isinstance(value, str):
                normalized["thesis_markdown"] = value
                break
    if "test_model_py" not in normalized:
        for key in _CARRIER_KEYS:
            value = normalized.get(key)
            if isinstance(value, str) and value.strip():
                normalized["test_model_py"] = value
                break
    return normalized


def _top_level_receipt_payload_is_complete(receipt_type: str, payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    if receipt_type != LOWERABILITY_BLOCKED_RECEIPT:
        return True
    try:
        validate_lowerability_blocked_receipt(payload)
    except ValueError:
        return False
    return True


def render_worldmodel_typed_payload(payload: dict[str, object]) -> str:
    """Compile a structured worldmodel mutator payload to legacy response text."""
    if not isinstance(payload, dict):
        raise ValueError("Worldmodel typed payload must be a JSON object.")
    payload = _normalize_worldmodel_payload_object(payload)
    receipt_lines = _render_control_receipts(payload.get("control_receipts", []))
    candidate_delta_blocked = _candidate_delta_blocked_by_receipts(payload)
    empty_candidate_decision = candidate_first_empty_candidate_decision(
        _validated_control_receipt_types(receipt_lines),
        lowerability_blocked=candidate_delta_blocked,
    )
    raw_candidate = _maybe_test_model_py(payload).strip()
    if raw_candidate and candidate_delta_blocked:
        raise ValueError(
            "Worldmodel typed payload cannot pair executable `test_model_py` "
            "with LOWERABILITY_BLOCKED or a receipt family that marks "
            "candidate_delta_admissible=false."
        )
    test_model_py = _extract_test_model_py(
        payload,
        allow_missing=empty_candidate_decision.may_omit_candidate and not raw_candidate,
    )
    thesis_markdown = payload.get("thesis_markdown")
    if thesis_markdown is None:
        thesis_markdown = payload.get("thesis_prose")
    if thesis_markdown is None:
        thesis_markdown = ""
    if not isinstance(thesis_markdown, str):
        raise ValueError(
            "Worldmodel typed payload field `thesis_markdown`/`thesis_prose` must be a string."
        )
    parts: list[str] = []
    if receipt_lines:
        parts.append("\n".join(receipt_lines))
    if thesis_markdown.strip():
        parts.append(thesis_markdown.strip())
    if test_model_py.strip():
        parts.append("```python\n" + test_model_py.strip() + "\n```")
    return "\n\n".join(parts)


def extract_worldmodel_control_receipts(text: str) -> list[dict[str, object]]:
    """Extract canonical control receipt rows from rendered payload text.

    This is the inverse read-model for ``render_worldmodel_typed_payload``.
    Autoresearch persistence and briefing projection should consume this
    function instead of re-parsing prose or maintaining sibling marker lists.
    """

    rows: list[dict[str, object]] = []
    seen: set[str] = set()

    try:
        payload = parse_worldmodel_typed_payload_text(text or "")
    except ValueError:
        payload = {}
    receipts = payload.get("control_receipts") if isinstance(payload, dict) else None
    if isinstance(receipts, list):
        for raw in receipts:
            if not isinstance(raw, dict):
                continue
            try:
                row = _normalize_control_receipt_row(raw)
            except ValueError:
                continue
            receipt_type = str(row.get("type") or "").strip()
            if not receipt_type:
                continue
            payload_obj = row.get("payload")
            if not isinstance(payload_obj, dict):
                continue
            out: dict[str, object] = {
                "type": receipt_type,
                "payload": payload_obj,
            }
            identity = json.dumps(out, sort_keys=True, separators=(",", ":"), default=str)
            if identity in seen:
                continue
            seen.add(identity)
            rows.append(out)

    for marker, receipt_type in _RENDERED_CONTROL_MARKERS:
        for raw in balanced_object_after_marker(text or "", marker):
            try:
                payload = json.loads(raw, strict=False)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            row: dict[str, object] = {
                "type": receipt_type,
                "payload": payload,
            }
            identity = json.dumps(row, sort_keys=True, separators=(",", ":"), default=str)
            if identity in seen:
                continue
            seen.add(identity)
            rows.append(row)
    return rows


def _control_receipts_include_type(payload: dict[str, object], receipt_type: str) -> bool:
    return _control_receipts_include_any(payload, {receipt_type})


def _validated_control_receipt_types(receipt_lines: list[str]) -> set[str]:
    types: set[str] = set()
    for line in receipt_lines:
        marker = str(line or "").split(":", 1)[0].strip()
        if marker in _KNOWN_CONTROL_RECEIPT_TYPES:
            types.add(marker)
    return types


def _control_receipts_include_any(payload: dict[str, object], receipt_types: set[str]) -> bool:
    receipts = payload.get("control_receipts")
    if not isinstance(receipts, list) or not receipts:
        return False
    for row in receipts:
        if not isinstance(row, dict):
            continue
        normalized = _normalize_control_receipt_row(row)
        if str(normalized.get("type") or "").strip() in receipt_types:
            return True
    return False


def _candidate_delta_blocked_by_receipts(payload: dict[str, object]) -> bool:
    """Return whether carried receipts explicitly remove candidate submission.

    This enforces the boundary-CEGAR chart at the compiler boundary. A receipt
    that says an alpha-chart distinction has no gamma-lowerable witness may be
    used to block, request another typed observation, or propose a capability;
    it must not be silently paired with an executable candidate.
    """

    receipts = payload.get("control_receipts")
    if not isinstance(receipts, list) or not receipts:
        return False
    normalized: list[object] = []
    for row in receipts:
        if isinstance(row, dict):
            normalized_row = _normalize_control_receipt_row(row)
            if str(normalized_row.get("type") or "").strip() == LOWERABILITY_BLOCKED_RECEIPT:
                validate_lowerability_blocked_receipt(normalized_row.get("payload"))
                return True
            normalized.append(normalized_row)
        else:
            normalized.append(row)
    try:
        lowerability = boundary_cegar_candidate_delta_lowerability(
            json.dumps(normalized, sort_keys=True, separators=(",", ":"), default=str)
        )
    except Exception:  # noqa: BLE001 - malformed receipts fail in the renderer later.
        return False
    return lowerability is False


def _extract_test_model_py(payload: dict[str, object], *, allow_missing: bool = False) -> str:
    raw = _maybe_test_model_py(payload)
    if raw.strip():
        return raw
    if allow_missing:
        return ""
    raise ValueError(
        "Worldmodel typed payload requires non-empty `test_model_py` "
        "or an equivalent executable carrier field."
    )


def _maybe_test_model_py(payload: dict[str, object]) -> str:
    raw = payload.get("test_model_py")
    if isinstance(raw, str) and raw.strip():
        return raw
    files = payload.get("files")
    if isinstance(files, dict):
        for key in ("test_model.py", "test_model_py"):
            file_value = files.get(key)
            if isinstance(file_value, str) and file_value.strip():
                return file_value
    for key in _CARRIER_KEYS:
        alias_value = payload.get(key)
        if isinstance(alias_value, str) and alias_value.strip():
            return alias_value
    return ""


def _render_control_receipts(raw: object) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("Worldmodel typed payload field `control_receipts` must be a list.")
    valid_action_request_present = _raw_control_receipts_include_valid_action_request(raw)
    lowerability_present = _raw_control_receipts_include_type(raw, LOWERABILITY_BLOCKED_RECEIPT)
    lines: list[str] = []
    for row in raw:
        if isinstance(row, str):
            line = row.strip()
            if line:
                lines.append(line)
            continue
        if not isinstance(row, dict):
            raise ValueError("Each worldmodel control receipt must be a string or object.")
        row = _normalize_control_receipt_row(row)
        receipt_type = str(row.get("type") or "").strip()
        receipt_payload = row.get("payload")
        if not receipt_type:
            raise ValueError("Worldmodel control receipt object requires `type`.")
        if receipt_type == "STRATEGY_CARD_DISCHARGE":
            if not isinstance(receipt_payload, dict):
                raise ValueError("STRATEGY_CARD_DISCHARGE receipt requires object `payload`.")
            lines.append(
                "STRATEGY_CARD_DISCHARGE: "
                + json.dumps(receipt_payload, sort_keys=True, separators=(",", ":"))
            )
        elif receipt_type == "LEAF_WORKBENCH_RECEIPT":
            if isinstance(receipt_payload, dict):
                if is_visible_workbench_local_diagnostic_receipt(receipt_payload):
                    lines.append(
                        "VISIBLE_WORKBENCH_DIAGNOSTIC: "
                        + json.dumps(receipt_payload, sort_keys=True, separators=(",", ":"))
                    )
                    continue
                capability_id = str(receipt_payload.get("capability_id") or "").strip()
                canonical_id = _CAPABILITY_ALIASES.get(capability_id)
                if canonical_id:
                    receipt_payload = dict(receipt_payload)
                    receipt_payload["capability_id"] = canonical_id
            normalized = validate_leaf_workbench_receipt(
                receipt_payload,
                WORLD_MODEL_LEAF_WORKBENCH_CONTRACT,
            )
            lines.append(
                "LEAF_WORKBENCH_RECEIPT: "
                + json.dumps(normalized, sort_keys=True, separators=(",", ":"))
            )
        elif receipt_type == CAPABILITY_PROPOSAL_RECEIPT:
            if not valid_action_request_present and not lowerability_present:
                raise ValueError(
                    "LEAF_WORKBENCH_CAPABILITY_PROPOSAL is optional meta evidence only; "
                    "it does not satisfy the science turn. Pair it with "
                    "LOWERABILITY_BLOCKED or a registered workbench action request."
                )
            try:
                normalized = validate_leaf_workbench_capability_proposal(receipt_payload)
            except ValueError as exc:
                lines.append(
                    "LEAF_WORKBENCH_CAPABILITY_PROPOSAL_QUARANTINED: "
                    + json.dumps(
                        {
                            "reason": str(exc),
                            "status": "ignored_optional_meta_evidence",
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
                continue
            lines.append(
                "LEAF_WORKBENCH_CAPABILITY_PROPOSAL: "
                + json.dumps(normalized, sort_keys=True, separators=(",", ":"))
            )
        elif receipt_type == REGISTERED_ACTION_RECEIPT:
            normalized = validate_leaf_workbench_action_request(
                receipt_payload,
                WORLD_MODEL_LEAF_WORKBENCH_CONTRACT,
            )
            lines.append(
                "LEAF_WORKBENCH_ACTION_REQUEST: "
                + json.dumps(normalized, sort_keys=True, separators=(",", ":"))
            )
        elif receipt_type == LOWERABILITY_BLOCKED_RECEIPT:
            normalized = validate_lowerability_blocked_receipt(receipt_payload)
            lines.append(
                "LOWERABILITY_BLOCKED: "
                + json.dumps(normalized, sort_keys=True, separators=(",", ":"))
            )
        elif receipt_payload is None:
            lines.append(receipt_type)
        else:
            lines.append(
                f"{receipt_type}: "
                + json.dumps(receipt_payload, sort_keys=True, separators=(",", ":"))
            )
    return lines


def _raw_control_receipts_include_valid_action_request(raw: list[object]) -> bool:
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            normalized = _normalize_control_receipt_row(row)
        except Exception:
            continue
        if str(normalized.get("type") or "").strip() != "LEAF_WORKBENCH_ACTION_REQUEST":
            continue
        try:
            validate_leaf_workbench_action_request(
                normalized.get("payload"),
                WORLD_MODEL_LEAF_WORKBENCH_CONTRACT,
            )
        except ValueError:
            continue
        return True
    return False


def _raw_control_receipts_include_type(raw: list[object], receipt_type: str) -> bool:
    for row in raw:
        if isinstance(row, str):
            if row.strip().split(":", 1)[0].strip() == receipt_type:
                return True
            continue
        if not isinstance(row, dict):
            continue
        try:
            normalized = _normalize_control_receipt_row(row)
        except Exception:
            continue
        if str(normalized.get("type") or "").strip() == receipt_type:
            return True
    return False


def _normalize_control_receipt_row(row: dict[str, object]) -> dict[str, object]:
    """Recover unambiguous wrapper/payload shape drift.

    The canonical carrier is {"type": ..., "payload": ...}. Leaves sometimes
    keep the wrapper object but place the type inside payload. Accept only the
    bounded second-order/action/receipt type strings we already know how to
    validate; everything else still fails at the normal type check.
    """

    receipt_type = str(row.get("type") or row.get("marker") or "").strip()
    if not receipt_type and str(row.get("schema") or "") == "ztare-visible-workbench-cli-receipt-v1":
        receipt_obj = row.get("receipt")
        if isinstance(receipt_obj, dict):
            return _normalize_control_receipt_row(receipt_obj)
        return {"type": "LEAF_WORKBENCH_RECEIPT", "payload": row}
    if receipt_type:
        if isinstance(row.get("payload"), dict):
            return {"type": receipt_type, "payload": row["payload"]}
        if receipt_type in _KNOWN_CONTROL_RECEIPT_TYPES:
            payload = {
                key: value
                for key, value in row.items()
                if key not in {"type", "marker", "payload"}
            }
            if receipt_type == "STRATEGY_CARD_DISCHARGE":
                if "strategy_card_ref" in payload and "card_ref" not in payload:
                    payload["card_ref"] = payload.pop("strategy_card_ref")
                if "blocker" in payload and "blocker_kind" not in payload:
                    payload["blocker_kind"] = payload.pop("blocker")
            return {"type": receipt_type, "payload": payload}
        return row
    payload = row.get("payload")
    if not isinstance(payload, dict):
        return row
    inner_type = str(payload.get("type") or "").strip()
    if inner_type not in _KNOWN_CONTROL_RECEIPT_TYPES:
        return row
    inner_payload = dict(payload)
    inner_payload.pop("type", None)
    return {"type": inner_type, "payload": inner_payload}
