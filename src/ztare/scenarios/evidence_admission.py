"""Fail-closed admission of a source passage into the governed argument graph."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def admit_source_passage(request: dict[str, Any], repo_root) -> dict[str, Any]:
    from ztare.scenarios.adapters import append_governed_overlay, governed_state_from_research_map
    from ztare.scenarios.decision_state import compile_decision_state, diff_decision_states
    from ztare.scenarios.evidence_binding import bind_evidence
    from ztare.scenarios.governed_types import normalize
    from ztare.workspace.source_files import project_paths, raw_source_path, repo_rel, split_source_frontmatter

    project = str(request.get("project") or "").strip()
    relative_path = str(request.get("source_path") or request.get("relative_path") or "").strip()
    excerpt = str(request.get("excerpt") or "")
    target = str(request.get("target") or request.get("claim_ref") or "").strip()
    if not (project and relative_path and excerpt.strip() and target):
        return {"ok": False, "error": "choose a project source, select its exact words, and choose a target claim"}

    try:
        source_file = raw_source_path(project, relative_path, root=repo_root)
    except Exception as exc:  # noqa: BLE001 - path refusal is part of the public contract.
        return {"ok": False, "refused": True, "error": f"source is not an indexed project file: {exc}"}
    if not source_file.is_file():
        return {"ok": False, "refused": True,
                "error": f"source is not an indexed project file: {repo_rel(source_file, root=repo_root)}"}

    paths = project_paths(project, root=repo_root)
    type_map: dict[str, Any] = {}
    if paths["source_type_map"].is_file():
        try:
            loaded = json.loads(paths["source_type_map"].read_text(encoding="utf-8"))
            type_map = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            type_map = {}
    relative_raw_path = source_file.relative_to(paths["raw_dir"].resolve()).as_posix()
    raw_text = source_file.read_text(encoding="utf-8")
    fallback_type = str(type_map.get(relative_raw_path) or type_map.get(source_file.name) or "untyped")
    source_type, content = split_source_frontmatter(raw_text, fallback_source_type=fallback_type)
    if source_type != "source_evidence":
        return {"ok": False, "refused": True,
                "error": "that file is not classified as source evidence; classify it before citing it"}

    governed = governed_state_from_research_map(project, repo_root)
    target_element = governed.by_id(target)
    if target_element is None or target_element.kind not in {"claim", "thesis"}:
        return {"ok": False, "error": f"target claim {target!r} is not in the governed map"}
    source_id = repo_rel(source_file, root=repo_root)
    binding = bind_evidence(source_id, content, excerpt, fetched_at=str(request.get("fetched_at") or ""))
    if binding is None:
        return {"ok": False, "refused": True,
                "error": "the selected passage no longer appears verbatim in the source; reload the file and select it again"}

    source_sha256 = hashlib.sha256(source_file.read_bytes()).hexdigest()
    evidence_id = "ev.bound." + hashlib.sha256(
        f"{source_id}|{binding.excerpt}|{target}".encode()).hexdigest()[:10]
    direct_claim_quote = normalize(target_element.text) in normalize(binding.excerpt)
    inference_warrant = "W2" if direct_claim_quote else "W3"
    element = {"id": evidence_id, "kind": "evidence", "text": binding.excerpt,
               "provenance": "sourced", "source_id": source_id, "source_path": source_id,
               "source_sha256": source_sha256, "content_sha256": binding.content_sha256}
    edge = {"src": evidence_id, "kind": "SUPPORTS", "dst": target, "warrant": inference_warrant,
            "source_warrant": "W2",
            "admission": "exact_claim_quote" if direct_claim_quote else "user_targeted_quote"}
    decision_before = compile_decision_state(governed).to_payload()
    append_governed_overlay(project, repo_root, [element], [edge])
    governed_after = governed_state_from_research_map(project, repo_root)
    decision_after = compile_decision_state(governed_after).to_payload()
    decision_delta = diff_decision_states(decision_before, decision_after)
    from ztare.scenarios.research_signals import snapshot_strength
    decision_history = snapshot_strength(project, governed_after, repo_root=repo_root)
    return {
        "ok": True,
        "project": project,
        "bound": {"evidence_id": evidence_id, "source_id": source_id, "source_path": source_id,
                  "source_sha256": source_sha256, "excerpt": binding.excerpt, "target": target,
                  "source_tier": "cited", "inference_tier": "cited" if direct_claim_quote else "unchecked"},
        "decision_before": decision_before,
        "decision_after": decision_after,
        "decision_delta": decision_delta,
        "decision_history": decision_history,
        "strength_before": decision_before["strength"]["profile"],
        "strength_after": decision_after["strength"]["profile"],
        "status_before": decision_before["status"],
        "status_after": decision_after["status"],
    }
