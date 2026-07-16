"""Governed artifacts — end-to-end production: compose every declared deliverable, gate through the firewall,
write only what passes (+ the interim governed serialization + a provenance report). See `artifacts.py` for the
module-level docstring."""
from __future__ import annotations

from ztare.scenarios.governed_types import Deliverable, GovernedState
from ztare.scenarios.firewall import _TEMPLATES, provenance_firewall, render
from ztare.scenarios.declarative import compose_declarative, spec_payload
from ztare.scenarios.verdict import assemble_verdict
from ztare.scenarios.adapters import serialize_governed


_BINDING_FILE = "decision_bindings.json"


def _binding_path(out_dir: str):
    from pathlib import Path

    return Path(out_dir) / _BINDING_FILE


def _read_bindings(out_dir: str) -> dict:
    import json

    path = _binding_path(out_dir)
    if not path.is_file():
        return {"schema": "ztare-deliverable-bindings-v1", "artifacts": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"schema": "ztare-deliverable-bindings-v1", "artifacts": {}}
    if not isinstance(payload, dict) or not isinstance(payload.get("artifacts"), dict):
        return {"schema": "ztare-deliverable-bindings-v1", "artifacts": {}}
    return payload


def _bind_written_deliverables(governed: GovernedState, out_dir: str, written: "list[str]") -> dict:
    """Bind only successfully composed artifacts to the decision state that produced them."""
    import json
    from datetime import datetime, timezone

    from ztare.scenarios.decision_state import compile_decision_state

    state = compile_decision_state(governed).to_payload()
    payload = _read_bindings(out_dir)
    artifacts = payload["artifacts"]
    generated_at = datetime.now(timezone.utc).isoformat()
    for name in written:
        artifacts[name] = {
            "decision_fingerprint": state["fingerprint"],
            "decision_status": state["status"],
            "generated_at": generated_at,
            "path": f"{name}.md",
        }
    path = _binding_path(out_dir)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"fingerprint": state["fingerprint"], "status": state["status"]}


def deliverable_binding_status(
    governed: GovernedState,
    declared: "list[str]",
    out_dir: str,
    *,
    root=None,
) -> dict:
    """Compare artifact receipts with the current decision state without mutating the project."""
    from pathlib import Path

    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.decision_state import compile_decision_state

    current = compile_decision_state(governed).to_payload()
    repo_root = (root or REPO_ROOT).resolve()
    bindings = _read_bindings(out_dir).get("artifacts", {})
    base = Path(out_dir)
    rows = {}
    for name in declared:
        binding = bindings.get(name) if isinstance(bindings.get(name), dict) else None
        artifact_path = base / f"{name}.md"
        generated = artifact_path.is_file()
        bound_fingerprint = str((binding or {}).get("decision_fingerprint") or "")
        try:
            display_path = artifact_path.resolve().relative_to(repo_root).as_posix()
        except ValueError:
            display_path = str(artifact_path)
        rows[name] = {
            "generated": generated,
            "stale": generated and bound_fingerprint != current["fingerprint"],
            "decision_fingerprint": bound_fingerprint or None,
            "current_fingerprint": current["fingerprint"],
            "generated_at": (binding or {}).get("generated_at"),
            "path": display_path if generated else None,
        }
    return {"decision": current, "bindings": rows}


def _spec_index(specs) -> dict[str, object]:
    return {str(spec.name): spec for spec in (specs or []) if getattr(spec, "name", "")}


def _apply_spec_metadata(deliverable: Deliverable, spec) -> Deliverable:
    """Let YAML own presentation metadata even when a plugin supplies richer code composition."""
    if spec is None:
        return deliverable
    deliverable.label = str(getattr(spec, "label", "") or deliverable.label or deliverable.name)
    deliverable.audience = str(getattr(spec, "audience", "") or deliverable.audience)
    deliverable.description = str(getattr(spec, "description", "") or deliverable.description)
    deliverable.presentation_brief = str(getattr(spec, "presentation_brief", "") or deliverable.presentation_brief)
    return deliverable


def build_scenario_deliverable(name: str, governed: GovernedState, *, specs=None) -> Deliverable:
    """Build one named governed document without writing it.

    Declarative designs own same-named outputs; code templates remain the
    fallback. The caller must still run the provenance firewall before use.
    """
    _ensure_templates()
    spec = _spec_index(specs).get(name)
    builder = (lambda state: compose_declarative(spec, state)) if spec is not None else _TEMPLATES.get(name)
    if builder is None:
        return Deliverable(name, stub_reason=f"no template registered for '{name}'")
    built = _apply_spec_metadata(builder(governed), spec)
    if not built.slots:
        return Deliverable(name, stub_reason="no governed content available for this deliverable")
    return built


def scenario_contract(name: str) -> tuple[list[str], list[object]]:
    """Load a scenario's declared deliverables and safe document recipes."""
    name = str(name or "").strip()
    if not name:
        return [], []
    from ztare.scenarios.loader import load_scenario
    try:
        scenario = load_scenario(name)
    except Exception:
        return [], []
    return list(scenario.deliverables), list(scenario.deliverable_specs)


def _ensure_templates() -> None:
    """Fire the typed provider discovery once so code-owned templates are available to CLI and API callers."""
    from ztare.scenarios import registry
    registry.available("renderer")


def deliverable_gaps(governed: GovernedState, declared: "list[str]", *, specs=None) -> dict:
    """READ-ONLY compose-vs-loop discriminator (writes nothing): for each DECLARED deliverable, can it be COMPOSED
    from the CURRENT governed state now, or does it need new governed content (the loop)? The four invariants a
    workbench 'add a required deliverable' action must hold: a deliverable is a VIEW (never new content); a
    missing one is SHOWN, never fabricated; discriminate COST (don't run a loop when a re-compose suffices);
    gaps are always VISIBLE. Statuses: `composable` (compose now, no loop) · `needs_content` (the loop must
    harden new evidence first) · `no_template` (register a template/plugin) · `ungoverned` (a section lacks
    governed backing — the firewall would reject it) · `error`."""
    _ensure_templates()
    rows: "list[dict]" = []
    spec_by_name = _spec_index(specs)
    for name in declared:
        spec = spec_by_name.get(name)
        # An editable declarative design is the contract the Workbench exposes
        # to an operator.  It must therefore win over a same-named provider
        # template; otherwise changing its sections looks successful but has
        # no effect on the generated document.  Code-owned templates remain
        # available for names that deliberately have no declarative design.
        builder = (lambda state, _spec=spec: compose_declarative(_spec, state)) if spec is not None else _TEMPLATES.get(name)
        if builder is None:
            rows.append({"name": name, "status": "no_template",
                         "action": (f"no template registered for '{name}' — add one: in a scenario provider "
                                    f"module call register_template('{name}', builder), where "
                                    f"builder(governed) -> Deliverable composes slots from governed elements"),
                         "detail": ["copy src/ztare/scenarios/providers/pm_templates.py as the pattern"]})
            continue
        metadata = {"spec": spec_payload(spec)} if spec is not None else {}
        try:
            built = _apply_spec_metadata(builder(governed), spec)
        except Exception as exc:  # noqa: BLE001
            rows.append({"name": name, "status": "error",
                         "action": f"template error: {type(exc).__name__}", "detail": [str(exc)]})
            continue
        if not built.slots:
            rows.append({"name": name, "status": "needs_content",
                         "action": "no governed content yet — run the loop to harden the evidence it needs",
                         "detail": [], **metadata})
            continue
        v = provenance_firewall([built], governed, [name])
        if v.ok:
            rows.append({"name": name, "status": "composable", "slots": len(built.slots),
                         "action": "compose now — no loop needed (a re-view of the current governed state)",
                         "detail": [], **metadata})
        else:
            rows.append({"name": name, "status": "ungoverned",
                         "action": "some sections lack governed backing — do not ship; run the loop or cut them",
                         "detail": list(v.violations), **metadata})
    return {"deliverables": rows,
            "compose_now": [r["name"] for r in rows if r["status"] == "composable"],
            "needs_loop": [r["name"] for r in rows if r["status"] == "needs_content"],
            "missing_template": [r["name"] for r in rows if r["status"] == "no_template"]}


def produce_scenario_artifacts(*, declared: "list[str]", governed: GovernedState, out_dir: str, specs=None) -> dict:
    """Compose each DECLARED deliverable via its template, gate every one through the provenance firewall, and
    write ONLY firewall-passing artifacts (+ a `provenance_report.md`). A deliverable that can't be composed
    purely from the governed state is written as a `*.STUB.md` carrying its violation reasons — never as
    ungoverned prose. Set-completeness is enforced against `declared` (the charter-pre-registered set)."""
    import os
    _ensure_templates()

    os.makedirs(out_dir, exist_ok=True)
    deliverables: "list[Deliverable]" = []
    spec_by_name = _spec_index(specs)
    for name in declared:
        spec = spec_by_name.get(name)
        # Match deliverable_gaps() exactly: a named declarative design owns
        # the composition recipe for that document.
        builder = (lambda state, _spec=spec: compose_declarative(_spec, state)) if spec is not None else _TEMPLATES.get(name)
        if builder is None:
            deliverables.append(Deliverable(name, stub_reason=f"no template registered for '{name}'"))
            continue
        try:
            built = builder(governed)
            built = _apply_spec_metadata(built, spec_by_name.get(name))
            if not built.slots:
                built = Deliverable(name, stub_reason="no governed content available for this deliverable")
            deliverables.append(built)
        except Exception as exc:  # noqa: BLE001 — a bad template stubs, never ships ungoverned
            deliverables.append(Deliverable(name, stub_reason=f"composition error: {type(exc).__name__}: {exc}"))

    verdict = provenance_firewall(deliverables, governed, declared)
    written: "list[str]" = []
    for d in deliverables:
        d_verdict = provenance_firewall([d], governed, [d.name])
        if d.stub_reason:                        # an accounted stub (no template / no governed content)
            payload = render(d, governed)
        elif d_verdict.ok:                       # fully governed → the real deliverable
            payload = render(d, governed)
            written.append(d.name)
        else:                                    # firewall REJECTED a non-stub → down-convert to a stub with
            payload = render(Deliverable(       # the violations, never the ungoverned content
                d.name, stub_reason="firewall rejected: " + "; ".join(d_verdict.violations)))
        with open(os.path.join(out_dir, f"{d.name}.md"), "w", encoding="utf-8") as fh:
            fh.write(payload)
    # The governed decision verdict (over the argument graph) + the interim artifact (Fable's option B —
    # emitted as a serialization, re-check any downstream polish with reingest_gate before it ships).
    decision = assemble_verdict(governed)
    import json as _json

    serialized = serialize_governed(governed, verdict=decision)
    with open(os.path.join(out_dir, "governed_artifact.json"), "w", encoding="utf-8") as fh:
        _json.dump(serialized, fh, indent=2, ensure_ascii=False)
    # Presentation is a RENDERER concern (per-scenario, dynamic) — if a `decision_brief` renderer is registered
    # (a plugin), emit the decision brief from the DATA. Registry lookup, no hard import: absent ⇒ no brief.
    try:
        from ztare.scenarios import registry as _registry
        _brief = _registry.get("renderer", "decision_brief")
        if _brief is not None:
            _brief.render(serialized, dest=os.path.join(out_dir, "decision_brief.md"))
    except Exception:  # noqa: BLE001 — a missing/failing brief renderer never breaks artifact production
        pass
    with open(os.path.join(out_dir, "provenance_report.md"), "w", encoding="utf-8") as fh:
        fh.write("# Provenance report\n\n")
        fh.write(f"- verdict: **{decision.status}** — {decision.reason} (coverage {decision.coverage})\n")
        if decision.load_bearing:
            bearing = governed.by_id(decision.load_bearing)
            ties = f" (ties: {decision.load_bearing_ties})" if len(decision.load_bearing_ties) > 1 else ""
            fh.write(f"- decision hinge (counterfactual): `{decision.load_bearing}`"
                     f"{(' — ' + bearing.text) if bearing else ''}{ties}\n")
        fh.write(f"- firewall: {'PASS' if verdict.ok else 'VIOLATIONS'}\n")
        fh.write(f"- written: {written or '[]'}\n")
        fh.write(f"- governed elements: {sorted(governed.ids()) or '[]'}\n")
        for message in verdict.violations:
            fh.write(f"- ⚠ {message}\n")
    binding = _bind_written_deliverables(governed, out_dir, written)
    return {"written": written, "ok": verdict.ok, "violations": verdict.violations,
            "verdict": decision.status, "dir": out_dir, "decision_binding": binding}


def resolve_declared_set(project: str, *, scenario_deliverables: "list[str] | None" = None,
                         repo_root=None) -> "list[str]":
    """The SINGLE declared-deliverable set for a project (Fable's B4 — unify the two disconnected notions). The
    scenario's `deliverables` (if a scenario is bound) UNION the per-project `workspace/required_deliverables.json`,
    defaulting to `[decision_memo]`. The pin, the panel, and the completeness firewall all read THIS one function
    — never the scenario YAML and the JSON as two separate code paths (which never merged and confused the model
    of what a project must produce)."""
    import json as _json

    from ztare.common.paths import PROJECTS_DIR

    names = list(scenario_deliverables or [])
    base = (repo_root / "projects") if repo_root is not None else PROJECTS_DIR
    path = base / project / "workspace" / "required_deliverables.json"
    if path.is_file():
        try:
            data = _json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                names.extend(str(d) for d in data)
        except Exception:  # noqa: BLE001
            pass
    out = list(dict.fromkeys(names))  # dedup, insertion-stable
    return out or ["decision_memo"]


def add_required_deliverable(project: str, name: str, *, repo_root=None) -> "list[str]":
    """Persist one project-owned handoff requirement; scenario declarations remain read-only inputs."""
    import json

    from ztare.common.paths import PROJECTS_DIR

    clean = str(name or "").strip()
    if not clean:
        raise ValueError("deliverable name required")
    base = (repo_root / "projects") if repo_root is not None else PROJECTS_DIR
    path = base / project / "workspace" / "required_deliverables.json"
    current: "list[str]" = []
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                current = [str(item) for item in payload if str(item).strip()]
        except (OSError, ValueError):
            current = []
    if clean not in current:
        current.append(clean)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    return current


def produce_all_declared(project: str, *, repo_root=None, out_dir: "str | None" = None,
                         scenario: str = "") -> dict:
    """Produce the FULL declared set at once, so the set-completeness firewall actually FIRES (the per-deliverable
    generate button passes a singleton — `declared=[name]` — which can never catch a silent drop). The declared
    set is the PINNED set from the run-start receipt when one exists (exogenous by time — the anti-cherry-pick
    teeth), else the current resolved set. A declared deliverable that can't compose is written as an accounted
    stub, never dropped — the firewall verifies the whole set is emitted-or-stubbed."""
    from pathlib import Path

    from ztare.common.paths import PROJECTS_DIR, REPO_ROOT
    from ztare.scenarios.adapters import governed_state_from_research_map
    from ztare.scenarios.contract_receipts import pinned_receipts

    rr = repo_root if repo_root is not None else REPO_ROOT
    receipts = pinned_receipts(project, rr)
    pinned_scenario = str((receipts[-1].get("scenario") if receipts else "") or "")
    scenario_name = str(scenario or pinned_scenario)
    scenario_names, specs = scenario_contract(scenario_name)
    if receipts:
        declared = sorted(receipts[-1].get("declared", [])) or ["decision_memo"]
        source = "pinned"
    else:
        declared = resolve_declared_set(project, scenario_deliverables=scenario_names, repo_root=rr)
        source = "current"
    governed = governed_state_from_research_map(project, rr)
    base = (repo_root / "projects") if repo_root is not None else PROJECTS_DIR
    out = out_dir or str(base / project / "workspace" / "deliverables")
    report = produce_scenario_artifacts(declared=declared, governed=governed, out_dir=out, specs=specs)
    try:
        report["dir"] = Path(out).resolve().relative_to(rr.resolve()).as_posix()
    except ValueError:
        report["dir"] = str(out)
    report["scenario"] = scenario_name or None
    report["declared"] = declared
    report["declared_source"] = source
    return report
