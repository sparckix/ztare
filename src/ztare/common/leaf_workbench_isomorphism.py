from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "ztare-leaf-workbench-structural-isomorphism-v1"
RECEIPT_REF = "workspace/latest_structural_isomorphism.json"
_MODES = {"solve", "impossibility", "completion", "correspondence", "conjecture"}


def run_structural_isomorphism_action(
    project_dir: str | Path,
    input_refs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run or retrieve a bounded structural-isomorphism workbench receipt.

    Live model calls require `allow_live_query=true` and an explicit `model`.
    Without that permission, this action is cache-only.
    """
    project = Path(project_dir)
    refs = input_refs if isinstance(input_refs, dict) else {}
    mode = str(refs.get("mode") or "solve").strip()
    if mode not in _MODES:
        raise ValueError(f"run_structural_isomorphism invalid mode {mode!r}")
    n = max(1, min(int(refs.get("n") or 3), 3))
    fingerprint = _input_fingerprint({**refs, "mode": mode, "n": n})
    cached = _read_cached(project, fingerprint)
    if cached is not None:
        return cached
    if not bool(refs.get("allow_live_query")):
        raise ValueError(
            "run_structural_isomorphism requires allow_live_query=true for a "
            "new query, or a matching cached receipt"
        )
    model = str(refs.get("model") or "").strip()
    if not model:
        raise ValueError("run_structural_isomorphism live query requires explicit model")

    if mode == "conjecture":
        left = _state_from_refs(project, refs, "left_state", "left_state_ref")
        right = _state_from_refs(project, refs, "right_state", "right_state_ref")
        if left is None:
            left = _state_from_refs(project, refs, "failure_state", "failure_state_ref")
        if left is None or right is None:
            raise ValueError("mode=conjecture requires left_state/right_state or refs")
        from ztare.research_director import research_isomorphism as ri

        out = ri.conjecture_between(
            left,
            right,
            n=n,
            model=model,
            ledger=project / "workspace" / "structural_isomorphism_candidates.jsonl",
        )
        result = {
            "mode": mode,
            "candidate_count": len(out.get("conjectures") or []),
            "rejected_count": len(out.get("rejected") or []),
            "left": _fingerprint_to_dict(out.get("left")),
            "right": _fingerprint_to_dict(out.get("right")),
            "conjectures": [_conjecture_to_dict(c) for c in out.get("conjectures") or []],
        }
    else:
        state = _state_from_refs(project, refs, "failure_state", "failure_state_ref")
        if state is None:
            state = _state_from_fields(refs)
        if state is None:
            raise ValueError("run_structural_isomorphism requires failure_state or seam fields")
        from ztare.research_director import research_isomorphism as ri

        result = ri.prescribe_for_seam(
            str(state.get("constraint_class") or "unresolved structural seam"),
            abstract_form=str(state.get("abstract_form") or ""),
            home_field=str(state.get("home_field") or ""),
            model=model,
            n=n,
            invariants={
                k: v
                for k, v in state.items()
                if k not in {"constraint_class", "abstract_form", "home_field"}
            },
            typed_mapping=bool(refs.get("typed_mapping", True)),
            mode=mode,
        )
        result = {"mode": mode, "prescription": result}

    receipt = {
        "schema": SCHEMA,
        "mode": mode,
        "model": model,
        "n": n,
        "input_fingerprint": fingerprint,
        "status": "ok",
        "result": result,
    }
    path = project / RECEIPT_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    receipt["receipt_ref"] = RECEIPT_REF
    receipt["receipt_sha256"] = _sha_path(path)
    return receipt


def _input_fingerprint(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _read_cached(project: Path, fingerprint: str) -> dict[str, Any] | None:
    path = project / RECEIPT_REF
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("input_fingerprint") != fingerprint:
        return None
    payload = dict(payload)
    payload["receipt_ref"] = RECEIPT_REF
    payload["receipt_sha256"] = _sha_path(path)
    return payload


def _state_from_refs(project: Path, refs: dict[str, Any], value_key: str, ref_key: str) -> dict[str, Any] | None:
    value = refs.get(value_key)
    if isinstance(value, dict):
        return value
    ref = str(refs.get(ref_key) or "").strip()
    if not ref:
        return None
    path = _resolve_project_ref(project, ref)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{ref_key} must point to a JSON object")
    return payload


def _state_from_fields(refs: dict[str, Any]) -> dict[str, Any] | None:
    if not any(key in refs for key in ("constraint_class", "abstract_form", "home_field")):
        return None
    return {
        "constraint_class": refs.get("constraint_class") or "unresolved structural seam",
        "abstract_form": refs.get("abstract_form") or "",
        "home_field": refs.get("home_field") or "",
        **(refs.get("invariants") if isinstance(refs.get("invariants"), dict) else {}),
    }


def _resolve_project_ref(project: Path, ref: str) -> Path:
    path = Path(ref)
    if path.is_absolute():
        return path
    return project / path


def _fingerprint_to_dict(fp: object) -> dict[str, Any]:
    return {
        "constraint_class": getattr(fp, "constraint_class", ""),
        "abstract_form": getattr(fp, "abstract_form", ""),
        "invariants": dict(getattr(fp, "invariants", {}) or {}),
        "home_field": getattr(fp, "forbidden_domain", ""),
    }


def _conjecture_to_dict(conj: object) -> dict[str, Any]:
    return {
        "mother_structure": getattr(conj, "mother_structure", ""),
        "lowerings": getattr(conj, "lowerings", {}) or {},
        "novel_predictions": getattr(conj, "novel_predictions", {}) or {},
        "prediction_cards": getattr(conj, "prediction_cards", None),
        "kill_conditions": getattr(conj, "kill_conditions", {}) or {},
        "specificity": getattr(conj, "specificity", None),
        "offline_adjudication": getattr(conj, "offline_adjudication", None),
    }


def _sha_path(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""
