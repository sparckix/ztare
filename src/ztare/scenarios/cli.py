"""`ztare scenario` subverbs intrinsic to scenarios: list | show | validate | new.

`run` is NOT here — it couples to autoresearch, so the top-level CLI router delegates it to
`autoresearch run --scenario <name>` (one binding path, no duplication). Everything here is pure scenario I/O.
"""
from __future__ import annotations

import sys

from ztare.scenarios.config import ScenarioConfig
from ztare.scenarios.loader import list_scenarios, load_scenario, scenario_path

_USAGE = "usage: ztare scenario <list|show|validate|new|run|surface|annotate|reingest|bind|brief|plugins|attribution|agenda|baseline|recompile|recheck|rice|beliefs|deliverables|wager|strength> [args]"


def _flag(argv: "list[str]", name: str) -> str:
    for i, arg in enumerate(argv):
        if arg == name and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith(name + "="):
            return arg.split("=", 1)[1]
    return ""


def _positionals(argv: "list[str]", *, valued_flags: "set[str] | None" = None) -> "list[str]":
    """Return positional arguments without mistaking a named flag's value for one."""
    valued_flags = valued_flags or set()
    out: list[str] = []
    skip_next = False
    for arg in argv:
        if skip_next:
            skip_next = False
            continue
        if arg in valued_flags:
            skip_next = True
            continue
        if any(arg.startswith(flag + "=") for flag in valued_flags) or arg.startswith("-"):
            continue
        out.append(arg)
    return out

_TEMPLATE = """\
name: {name}
description: >
  One line: what claims / decisions this scenario pressure-tests.

# A scenario binds the domain-neutral reasoning kernel to your use-case by DECLARING three things — its
# VOCABULARY (the rubric), its DELIVERABLES (governed outputs), and its EVIDENCE + RENDERER plug-ins. Nothing
# below is code; this file IS the plug. Worked example: scenarios/product-manager.yaml · guide: scenarios/README.md.

# ── VOCABULARY: the rubric is the honored lever — it drives the judge's dimensions, persona, and steering
#    across the whole loop. Point at an existing rubric or create rubrics/{rubric}.json.
rubric: {rubric}
iters: 8
dynamic: true

# ── DELIVERABLES: governed outputs composed AFTER the run from the hardened state, through the provenance
#    firewall (nothing ungoverned ships). `decision_memo` is built in; add a spec / risk-register the same way
#    (each is slots = governed refs, filled verbatim — never fabricated).
deliverables:
  - decision_memo

# Optional one-shot document designs. Sections select governed node kinds;
# facts never come from presentation guidance.
deliverable_specs: []

# ── MECHANISM gates (opt-in): fit/analysis scenarios add Cage gates here; a claim scenario leaves it empty.
gate_package: []

# ── EXTENSION surface — resolved to typed capability plug-ins by the resolver (scenarios.registry).
goal_type: ""
solvers: []
evidence_sources:
  - local_files            # a typed EvidenceProvider; Jira / Confluence / telemetry are drop-in plug-ins
renderer: markdown         # a typed Renderer; workbench / obsidian / pdf are drop-in plug-ins
rechecks: []               # re-executable warrant checks, resolved by name
workbench_panels: []       # declarative panel ids; the Workbench maps installed ids to renderers
"""


def _cmd_list(argv: "list[str]") -> int:
    names = list_scenarios()
    if "--json" in argv:
        import json
        from ztare.scenarios.plugin_management import scenario_rows

        rows = scenario_rows()
        print(json.dumps({"ok": True, "scenarios": rows}, default=str))
        return 0
    if not names:
        print("no scenarios found — add scenarios/<name>.yaml (or: ztare scenario new <name>)")
        return 0
    for n in names:
        try:
            desc = (load_scenario(n).description or "").strip().splitlines()
            desc = desc[0] if desc else ""
        except Exception as exc:  # noqa: BLE001 — a broken manifest still lists, flagged
            desc = f"(invalid: {type(exc).__name__})"
        print(f"  {n:24s} {desc[:90]}")
    return 0


def _cmd_show(argv: "list[str]") -> int:
    if not argv:
        print("usage: ztare scenario show <name>", file=sys.stderr)
        return 2
    try:
        sc = load_scenario(argv[0])
    except Exception as exc:  # noqa: BLE001
        if "--json" in argv:
            import json
            print(json.dumps({"ok": False, "name": argv[0], "error": f"{type(exc).__name__}: {exc}"}))
        else:
            print(f"ztare: {exc}", file=sys.stderr)
        return 2
    if "--effect" in argv:
        import json
        from ztare.scenarios.resolver import scenario_effect

        try:
            payload = scenario_effect(sc.name)
            payload["ok"] = True
        except Exception as exc:  # noqa: BLE001 - a broken extension is a typed preview failure.
            payload = {"ok": False, "name": sc.name, "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(payload, default=str) if "--json" in argv
              else json.dumps(payload, indent=2, default=str))
        return 0 if payload.get("ok") else 2
    from ztare.scenarios.resolver import resolve_capabilities

    notes: "list[str]" = []
    caps = resolve_capabilities(sc, notes=notes)
    print(f"scenario: {sc.name}")
    if sc.description:
        print(f"  description: {sc.description.strip()}")
    print(f"  rubric:       {sc.rubric or '(none)'}")
    print(f"  run:          iters={sc.iters or '(default)'} dynamic={sc.dynamic} "
          f"mutator={sc.mutator_model or '(cli/env)'} judge={sc.judge_model or '(cli/env)'}")
    print(f"  gate_package: {sc.gate_package or '[]'}")
    print(f"  deliverables: {sc.deliverables or '[]'}  (governed outputs via the provenance firewall)")
    if sc.deliverable_specs:
        print(f"  document_specs: {[spec.name for spec in sc.deliverable_specs]}")
    ev = [getattr(p, "name", "?") for p in caps.get("evidence", [])]
    print(f"  evidence:     {ev or '[]'}    renderer: {getattr(caps.get('renderer'), 'name', '(none)')}")
    if sc.solvers:
        print(f"  solvers:      {sc.solvers}")
    if sc.rechecks:
        print(f"  rechecks:     {sc.rechecks}")
    if sc.workbench_panels:
        print(f"  panels:       {sc.workbench_panels}")
    if sc.goal_type:
        print(f"  goal_type:    {sc.goal_type}")
    for m in notes:
        print(f"  ! {m}")
    return 0


def _cmd_validate(argv: "list[str]") -> int:
    if not argv:
        print("usage: ztare scenario validate <name>", file=sys.stderr)
        return 2
    name = argv[0]
    p = scenario_path(name)
    if not p.exists():
        print(f"ztare: scenario '{name}' not found at {p}", file=sys.stderr)
        return 2
    try:
        sc = ScenarioConfig.load(p)
    except Exception as exc:  # noqa: BLE001 — surface the validation error to the user, not a stack trace
        print(f"INVALID {name}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    # A well-formed manifest that names an ABSENT capability is still INVALID — a dropped YAML is only a real
    # extension if its declared plug-ins resolve. Fail loud here (the run path only warns, to stay robust).
    from ztare.scenarios.resolver import resolve_capabilities

    notes: "list[str]" = []
    resolve_capabilities(sc, notes=notes)
    unknown = [m for m in notes if "unknown" in m.lower()]
    if unknown:
        print(f"INVALID {name}: names {len(unknown)} unregistered capability(ies):", file=sys.stderr)
        for m in unknown:
            print(f"  ✗ {m}", file=sys.stderr)
        return 1
    print(f"OK: {name} ({p}) validates")
    return 0


def _cmd_new(argv: "list[str]") -> int:
    force = "--force" in argv
    pos = _positionals(argv, valued_flags={"--project", "--promote", "--base-hash"})
    if not pos:
        print("usage: ztare scenario new <name> [--force]", file=sys.stderr)
        return 2
    name = pos[0]
    p = scenario_path(name)
    if p.exists() and not force:
        print(f"ztare: {p} already exists (use --force to overwrite)", file=sys.stderr)
        return 2
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_TEMPLATE.format(name=name, rubric=name.replace("-", "_")), encoding="utf-8")
    try:
        ScenarioConfig.load(p)  # the scaffold must itself validate
    except Exception as exc:  # noqa: BLE001
        print(f"ztare: scaffolded {p} but it failed validation: {exc}", file=sys.stderr)
        return 1
    _r = name.replace("-", "_")
    print(f"created {p}")
    print("next (a ~30-min plug — no code unless you add a provider):")
    print(f"  1. VOCABULARY: write rubrics/{_r}.json (copy rubrics/product_manager.json and retune the dimensions)")
    print("  2. DELIVERABLES: keep `decision_memo` or add your own governed template")
    print("  3. (optional) drop a custom EvidenceProvider/Renderer .py into a $ZTARE_SCENARIO_PLUGINS dir")
    print(f"  then: ztare scenario validate {name}  ·  ztare scenario run {name} --project <slug>")
    return 0


def _cmd_reingest(argv: "list[str]") -> int:
    """The governed-UPDATE path (annotate is read-only analysis; this promotes a rendering). Opens a re-ingest
    session against a project's governed map, shows the diff (traced / dropped-claim / ungoverned), and —
    with `--promote <out.md>` — promotes the polish to canonical ONLY if nothing is ungoverned and the base
    state is unchanged, writing a `.reingest.json` audit record. No LLM, fail-closed."""
    pos = _positionals(argv, valued_flags={"--project", "--model"})
    project = _flag(argv, "--project")
    promote_to = _flag(argv, "--promote")
    expected_base = _flag(argv, "--base-hash")
    js = "--json" in argv
    if not pos or not project:
        message = "usage: ztare scenario reingest <polished.md> --project <slug> [--promote <out.md>] [--base-hash <hash>] [--json]"
        print('{"ok":false,"error":"document and project are required"}' if js else message,
              file=sys.stdout if js else sys.stderr)
        return 2
    import json
    from pathlib import Path

    doc = Path(pos[0])
    if not doc.is_file():
        payload = {"ok": False, "project": project, "error": f"{doc} not found"}
        print(json.dumps(payload) if js else f"ztare: {payload['error']}", file=sys.stdout if js else sys.stderr)
        return 2
    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.artifacts import governed_state_from_research_map, open_reingest_session, promote_reingest
    from ztare.workspace.report_actions import display_path

    governed = governed_state_from_research_map(project, REPO_ROOT)
    if not governed.elements:
        payload = {"ok": False, "project": project, "governed": False, "elements": 0,
                   "ungoverned": [], "error": f"no governed research map for project '{project}' — run it first"}
        print(json.dumps(payload) if js else f"ztare: {payload['error']}", file=sys.stdout if js else sys.stderr)
        return 2
    text = doc.read_text(encoding="utf-8")
    session = open_reingest_session(project, text, governed)
    d = session.diff
    payload = {"ok": True, "project": project, "governed": session.promotable,
               "elements": len(governed.elements), "base_hash": session.base_hash,
               "promotable": session.promotable, "traced_claims": d.traced_claims,
               "dropped_claims": d.dropped_claims, "ungoverned": d.ungoverned}
    if promote_to and (not expected_base or expected_base != session.base_hash):
        payload.update({"ok": False, "promoted": False, "stale": True,
                        "error": "the checked decision changed; check this copy again before promoting"})
        print(json.dumps(payload) if js else f"NOT PROMOTED: {payload['error']}",
              file=sys.stdout if js else sys.stderr)
        return 1
    if promote_to:
        from datetime import datetime, timezone
        result = promote_reingest(session, text, governed, promote_to,
                                  at=datetime.now(timezone.utc).isoformat())
        result["ok"] = bool(result.get("promoted"))
        result["project"] = project
        if result.get("path"):
            out_path = Path(result["path"])
            result["path"] = display_path(out_path)
            result["receipt_path"] = display_path(out_path.with_suffix(".reingest.json"))
        if not result.get("ok"):
            result["error"] = result.get("reason") or "copy was not promoted"
        print(json.dumps(result, default=str) if js else
              (f"PROMOTED → {result['path']} (+ audit record); {result['traced_claims']} claim(s) traced"
               if result.get("promoted") else f"NOT PROMOTED: {result.get('reason')}"),
              file=sys.stdout if js or result.get("promoted") else sys.stderr)
        return 0 if result.get("promoted") else 1
    if js:
        print(json.dumps(payload, default=str))
        return 0 if session.promotable else 1
    print(f"reingest diff for {doc.name}: {d.traced_claims} claim(s) traced · "
          f"{len(d.dropped_claims)} claim(s) dropped · {len(d.ungoverned)} ungoverned sentence(s)")
    for violation in d.ungoverned[:20]:
        print(f"  ✗ UNGOVERNED: {violation}", file=sys.stderr)
    return 0 if session.promotable else 1


def _cmd_surface(argv: "list[str]") -> int:
    """Intake funnel: a document → its load-bearing ASSUMPTIONS as bounded claims to test, each anchored to a
    VERBATIM source span. The LLM proposes; the kernel gates every anchor (fail-closed) — a hallucinated
    assumption is dropped. Each surfaced claim is a thesis you can then run through the governed loop."""
    pos = _positionals(argv, valued_flags={"--project", "--model"})
    project = _flag(argv, "--project")
    if project and not pos:
        import json

        from ztare.common.paths import PROJECTS_DIR
        from ztare.scenarios.surfacing import claims_from_packet, surface_assumptions

        root = PROJECTS_DIR / project
        evidence_files = list(root.glob("**/compiled_evidence_packet.json")) + list(root.glob("*_packet.json"))
        if not evidence_files:
            payload = {"ok": False, "project": project, "claims": [],
                       "error": f"no compiled evidence file for '{project}' — prepare evidence first"}
        else:
            try:
                compiled = json.loads(evidence_files[0].read_text(encoding="utf-8"))
                doc = "\n".join(path.read_text(encoding="utf-8", errors="replace")
                                 for name in ("thesis.md", "current_iteration.md", "evidence.txt")
                                 if (path := root / name).is_file())
                result = surface_assumptions(doc, lambda _doc: claims_from_packet(compiled))
                payload = {"ok": True, "project": project, "dropped": len(result.rejected),
                           "claims": [{"text": claim.text, "span": claim.span} for claim in result.anchored]}
            except Exception as exc:  # noqa: BLE001 - unreadable compiled evidence is visible, not skipped.
                payload = {"ok": False, "project": project, "claims": [],
                           "error": f"unreadable compiled evidence: {type(exc).__name__}"}
        print(json.dumps(payload, default=str) if "--json" in argv else
              (f"surfaced {len(payload.get('claims', []))} anchored assumption(s)" if payload.get("ok")
               else f"ztare: {payload.get('error')}"),
              file=sys.stdout if "--json" in argv or payload.get("ok") else sys.stderr)
        return 0 if payload.get("ok") else 2
    if not pos:
        print("usage: ztare scenario surface <doc.md> [--model <family>]", file=sys.stderr)
        return 2
    from pathlib import Path

    doc_path = Path(pos[0])
    if not doc_path.is_file():
        print(f"ztare: {doc_path} not found", file=sys.stderr)
        return 2
    from ztare.scenarios.providers.llm_proposer import llm_proposer
    from ztare.scenarios.surfacing import surface_assumptions

    model = _flag(argv, "--model")
    try:
        result = surface_assumptions(doc_path.read_text(encoding="utf-8"),
                                     lambda d: llm_proposer(d, model=model))
    except Exception as exc:  # noqa: BLE001 — surface a clear message, not a stack trace
        print(f"ztare: assumption-surfacing needs an LLM (ZTARE runtime or an injected proposer): {exc}",
              file=sys.stderr)
        return 2
    if not result.anchored:
        print("no anchored assumptions surfaced.")
        return 0
    print(f"surfaced {len(result.anchored)} anchored assumption(s) from {doc_path.name} "
          f"({len(result.rejected)} dropped as un-anchored):\n")
    for i, claim in enumerate(result.anchored, 1):
        print(f"{i}. {claim.text}\n   ↳ anchor: \"{claim.span[:80]}\"")
    print("\nEach is a bounded claim to test: ztare scenario run <name> --project <slug>")
    return 0


def _cmd_annotate(argv: "list[str]") -> int:
    """The annotated round-trip: a document (a PRD) → THE SAME document back, each sentence tagged with its
    claim lifecycle — backed / contradicted / surfaced-untested / inert — against a project's governed map. A
    doc is INPUT: it never 'fails'; the headline is the load-bearing-assumption COUNT. Pre-run (no governed map
    yet) this degrades to pure surfacing: 'N assumptions, 0 tested'. Writes <doc>.annotated.md."""
    pos = [a for a in argv if not a.startswith("-")]
    project = _flag(argv, "--project")
    if not pos:
        print("usage: ztare scenario annotate <doc.md> [--project <slug>] [--model <family>]", file=sys.stderr)
        return 2
    from pathlib import Path

    doc_path = Path(pos[0])
    if not doc_path.is_file():
        print(f"ztare: {doc_path} not found", file=sys.stderr)
        return 2
    doc = doc_path.read_text(encoding="utf-8")
    from ztare.common.paths import PROJECTS_DIR, REPO_ROOT
    from ztare.scenarios.artifacts import (
        ANNOTATION_STATUSES,
        GovernedState,
        annotate,
        governed_state_from_research_map,
        render_annotated,
    )
    from ztare.scenarios.surfacing import claims_from_packet, surface_assumptions

    governed = governed_state_from_research_map(project, REPO_ROOT) if project else GovernedState()
    spans: "list[str]" = []
    rejected: "list[str]" = []
    model = _flag(argv, "--model")
    proposer = None
    surfaced_from = "none"
    if model:
        from ztare.scenarios.providers.llm_proposer import llm_proposer
        proposer = lambda value: llm_proposer(value, model=model)  # noqa: E731 - explicit live analysis.
        surfaced_from = f"live:{model}"
    elif project:
        root = PROJECTS_DIR / project
        evidence_files = list(root.glob("**/compiled_evidence_packet.json")) + list(root.glob("*_packet.json"))
        if evidence_files:
            try:
                import json
                compiled = json.loads(evidence_files[0].read_text(encoding="utf-8"))
                proposer = lambda _value: claims_from_packet(compiled)  # noqa: E731 - deterministic composition.
                surfaced_from = "compiled_evidence"
            except Exception:  # noqa: BLE001 - map alignment remains available.
                proposer = None
    if proposer is not None:
        try:
            surfaced = surface_assumptions(doc, proposer)
            spans, rejected = [claim.span for claim in surfaced.anchored], surfaced.rejected
        except Exception as exc:  # noqa: BLE001 - surfacing is additive; annotation still runs.
            surfaced_from = f"error:{type(exc).__name__}"

    anns = annotate(doc, governed, surfaced_spans=spans)
    elements_by_id = {element.id: element for element in governed.elements}
    counts = {status: sum(1 for annotation in anns if annotation.status == status)
              for status in ANNOTATION_STATUSES}
    note = ""
    if surfaced_from == "compiled_evidence" and not spans:
        note = ("The project's compiled evidence did not match this draft. Choose live analysis to surface "
                "this draft's own assumptions.")
    elif surfaced_from == "none":
        note = "No live analysis or compiled evidence was available; this checks only against the current map."
    rendered = render_annotated(doc_path.name, anns, rejected=rejected)
    if "--json" in argv:
        import json
        print(json.dumps({"ok": True, "project": project, "elements": len(governed.elements),
                          "pre_run": not governed.elements, "surfaced_from": surfaced_from,
                          "note": note, "dropped": len(rejected), "counts": counts,
                          "annotations": [
                              {
                                  "sentence": item.sentence,
                                  "status": item.status,
                                  "element_id": item.element_id,
                                  "element_text": (
                                      elements_by_id[item.element_id].text
                                      if item.element_id in elements_by_id
                                      else ""
                                  ),
                                  "element_kind": (
                                      elements_by_id[item.element_id].kind
                                      if item.element_id in elements_by_id
                                      else ""
                                  ),
                              }
                              for item in anns
                          ],
                          "rendered": rendered}, default=str))
        return 0
    out = doc_path.with_suffix(doc_path.suffix + ".annotated.md")
    out.write_text(rendered, encoding="utf-8")
    print(f"{counts['UNTESTED']} load-bearing assumption(s) · {counts['BACKED']} backed · "
          f"{counts['CONTRADICTED']} contradicted · {counts['INERT']} no claim surfaced")
    if not project or not governed.elements:
        print("(no governed map — this is pre-run surfacing: nothing tested yet)")
    print(f"wrote {out}")
    return 0


def _cmd_brief(argv: "list[str]") -> int:
    """A governed decision brief for any project.s governed map: DECISION → what it hinges on (counterfactual)
    → evidence status → falsifiers, apparatus in a collapsed audit drawer. Rendered by the `decision_brief`
    Renderer plugin from the governed DATA — presentation, dynamic per project, not a kernel template."""
    project = _flag(argv, "--project")
    if not project:
        print("usage: ztare scenario brief --project <slug> [--out <file.md>]", file=sys.stderr)
        return 2
    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.artifacts import assemble_verdict, governed_state_from_research_map, serialize_governed
    from ztare.scenarios.decision_state import compile_decision_state
    from ztare.scenarios.registry import get as _get

    governed = governed_state_from_research_map(project, REPO_ROOT)
    if not governed.elements:
        print(f"ztare: no governed research map for project '{project}' — run it first", file=sys.stderr)
        return 2
    renderer = _get("renderer", "decision_brief")
    if renderer is None:
        print("ztare: the decision_brief renderer is not registered", file=sys.stderr)
        return 2
    out = _flag(argv, "--out")
    result = renderer.render(serialize_governed(governed, verdict=assemble_verdict(governed)), dest=out)
    if "--json" in argv:
        import json

        decision = compile_decision_state(governed).to_payload()
        print(json.dumps({
            "ok": True,
            "project": project,
            "brief": result.text,
            "decision_fingerprint": decision["fingerprint"],
            "decision_status": decision["status"],
        }))
        return 0
    if out:
        print(f"wrote {out}")
    else:
        print(result.text)
    return 0


def _cmd_bind(argv: "list[str]") -> int:
    """Admit an exact passage from a classified project source as support for one named claim."""
    import json
    from pathlib import Path

    spec_path, spec_json = _flag(argv, "--spec"), _flag(argv, "--spec-json")
    try:
        request = json.loads(Path(spec_path).read_text(encoding="utf-8")) if spec_path else json.loads(spec_json)
        if not isinstance(request, dict):
            raise ValueError("binding spec must be a JSON object")
    except Exception as exc:  # noqa: BLE001 - malformed admission input is a typed refusal.
        payload = {"ok": False, "refused": True, "error": f"invalid binding spec: {exc}"}
        print(json.dumps(payload) if "--json" in argv else f"ztare: {payload['error']}",
              file=sys.stdout if "--json" in argv else sys.stderr)
        return 2
    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.evidence_admission import admit_source_passage

    payload = admit_source_passage(request, REPO_ROOT)
    print(json.dumps(payload, default=str) if "--json" in argv else
          (f"admitted {payload['bound']['source_path']} → {payload['bound']['target']}"
           if payload.get("ok") else f"ztare: {payload.get('error')}"),
          file=sys.stdout if "--json" in argv or payload.get("ok") else sys.stderr)
    return 0 if payload.get("ok") else 2


def _cmd_plugins(argv: "list[str]") -> int:
    """Everything installed, across the three plugin kinds — SCENARIOS (`scenarios/*.yaml`), RUBRICS
    (`rubrics/*.json`), and CAPABILITIES (`@capability` code, incl. any dropped in a plugin dir). `--reload`
    re-discovers so a just-dropped code plugin goes live without a restart."""
    import json
    from pathlib import Path

    from ztare.scenarios.plugin_management import catalog, detail, install

    detail_kind = _flag(argv, "--detail")
    install_kind = _flag(argv, "--install")
    name = _flag(argv, "--name")
    if detail_kind:
        payload = detail(detail_kind, name)
    elif install_kind:
        spec_path, spec_json = _flag(argv, "--spec"), _flag(argv, "--spec-json")
        try:
            spec = json.loads(Path(spec_path).read_text(encoding="utf-8")) if spec_path else json.loads(spec_json)
            if not isinstance(spec, dict):
                raise ValueError("plugin spec must be a JSON object")
            payload = install(install_kind, name, spec, overwrite="--overwrite" in argv)
        except Exception as exc:  # noqa: BLE001 - malformed authoring input is a typed refusal.
            payload = {"ok": False, "error": f"invalid plugin spec: {exc}"}
    else:
        payload = catalog(reload="--reload" in argv)
    if "--json" in argv:
        print(json.dumps(payload, default=str))
        return 0 if payload.get("ok") else 2

    if not payload.get("ok"):
        print(f"ztare: {payload.get('error')}", file=sys.stderr)
        return 2
    print("SCENARIOS:", ", ".join(payload.get("scenarios") or []) or "none")
    print("SCORING GUIDES:", ", ".join(payload.get("rubrics") or []) or "none")
    print("CAPABILITIES:", payload.get("capabilities") or {})
    return 0


def _cmd_attribution(argv: "list[str]") -> int:
    """Report which scenario and scoring guide governed a project's saved runs."""
    project = _flag(argv, "--project")
    if not project:
        print("usage: ztare scenario attribution --project <slug> [--json]", file=sys.stderr)
        return 2
    import json

    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.attribution import scenario_attribution

    try:
        payload = {**scenario_attribution(project, REPO_ROOT), "ok": True, "project": project}
    except Exception as exc:  # noqa: BLE001 - malformed run history is visible to the operator.
        payload = {"ok": False, "project": project, "error": f"{type(exc).__name__}: {exc}"}
    if "--json" in argv:
        print(json.dumps(payload, default=str))
    elif payload.get("ok"):
        print(f"project '{project}' used scenario {payload.get('scenario') or '(none)'} "
              f"and scoring guide {payload.get('rubric') or '(none)'}")
    else:
        print(f"ztare: {payload.get('error')}", file=sys.stderr)
    return 0 if payload.get("ok") else 2


def _cmd_agenda(argv: "list[str]") -> int:
    """The TEST AGENDA — 'what do I test next?' The argument kernel (ATMS/ABA) over a project's governed map:
    the grounded verdict, the minimal cores (which assumption-sets jointly decide it), the dominators (claims
    every path routes through), the warrant ceiling (weakest load-bearing warrant), and the untested assumptions
    ranked by whether testing one flips the verdict / how many cores it sits in. Deterministic, no LLM."""
    project = _flag(argv, "--project")
    if not project:
        print("usage: ztare scenario agenda --project <slug>", file=sys.stderr)
        return 2
    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.argument_kernel import argument_analysis
    from ztare.scenarios.artifacts import governed_state_from_research_map

    governed = governed_state_from_research_map(project, REPO_ROOT)
    if not governed.elements:
        if "--json" in argv:
            import json
            print(json.dumps({"ok": False, "project": project,
                              "error": f"no governed research map for project '{project}' — run it first"}))
        else:
            print(f"ztare: no governed research map for project '{project}' — run it first", file=sys.stderr)
        return 2
    a = argument_analysis(governed)
    # What to test next — the ONE unified agenda (implicit + declared + loop-proposed, all normalized to wagers,
    # ranked once with the Pareto frontier ★ marked). Supersedes the old single-lens test-agenda print.
    from ztare.scenarios.agenda import project_agenda
    ag = project_agenda(project, REPO_ROOT)
    emitted = None
    if "--emit" in argv:  # close-the-loop producer: write governed_agenda.jsonl the loop steers its next action by
        from ztare.scenarios.agenda import emit_governed_agenda
        emitted = emit_governed_agenda(project, REPO_ROOT)
    if "--json" in argv:
        import json
        payload = dict(a)
        payload.update({
            "ok": True,
            "project": project,
            "agenda": ag,
            "text_of": {element.id: element.text for element in governed.elements},
        })
        if emitted:
            payload["emitted"] = emitted
        print(json.dumps(payload, default=str))
        return 0
    print(f"verdict: {a['verdict']}   warrant ceiling: {a['warrant_ceiling'] or '(no support)'}")
    if a["dominators"]:
        print(f"dominators (every path routes through): {a['dominators']}")
    if a["minimal_cores"]:
        print(f"minimal cores (jointly decide the verdict): {a['minimal_cores'][:8]}")
    print("what to test next (unified agenda — ★ = on the tradeoff frontier):")
    if not ag:
        print("  (nothing decision-material left to test — the decision is robust as it stands)")
    for r in ag[:12]:
        star = "★" if r["on_frontier"] else " "
        cost = "undeclared" if r["cost"] is None else f"{r['cost']:g}"
        sev = max(r["max_displacement"]) if r["max_displacement"] else 0.0
        tags = ("" if not r["flips_crisp"] else " · flips verdict") + ("" if not r["status_change"] else " · shifts status")
        print(f"  {star} [{r['source']}] {r['test']}")
        print(f"        info-yield {r['bits']:.2f} bits · severity Δ{sev:.2f} · cost {cost}{tags}")
    if emitted:
        print(f"governed agenda → {emitted['path']} ({emitted['count']} rows)")
    return 0


def _baseline_path(project: str):
    from ztare.common.paths import PROJECTS_DIR
    return PROJECTS_DIR / project / "workspace" / "decision_baseline.json"


def _cmd_baseline(argv: "list[str]") -> int:
    """Snapshot the project's governed state as a DECISION BASELINE — the frozen argument at decision time, to
    recompile against later. Writes workspace/decision_baseline.json."""
    project = _flag(argv, "--project")
    if not project:
        print("usage: ztare scenario baseline --project <slug>", file=sys.stderr)
        return 2
    import json
    from datetime import datetime, timezone

    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.artifacts import assemble_verdict, governed_state_from_research_map, serialize_governed

    path = _baseline_path(project)
    if "--status" in argv:
        if not path.is_file():
            payload = {"ok": True, "project": project, "exists": False}
        else:
            try:
                stored = json.loads(path.read_text(encoding="utf-8"))
                payload = {
                    "ok": True,
                    "project": project,
                    "exists": True,
                    "verdict": str(((stored.get("verdict") or {}).get("status") or "")),
                    "saved_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                }
            except Exception:  # noqa: BLE001 - an unreadable reference is surfaced, never compared.
                payload = {"ok": False, "project": project, "exists": True,
                           "error": "saved reference is unreadable"}
        if "--json" in argv:
            print(json.dumps(payload))
        elif payload.get("exists"):
            print(f"decision baseline: {payload.get('verdict') or 'unknown'} · {payload.get('saved_at')}")
        else:
            print("no decision baseline")
        return 0 if payload.get("ok") else 2

    governed = governed_state_from_research_map(project, REPO_ROOT)
    if not governed.elements:
        message = f"no governed research map for project '{project}' — run it first"
        if "--json" in argv:
            print(json.dumps({"ok": False, "project": project, "error": message}))
        else:
            print(f"ztare: {message}", file=sys.stderr)
        return 2
    path.parent.mkdir(parents=True, exist_ok=True)
    verdict = assemble_verdict(governed)
    path.write_text(json.dumps(serialize_governed(governed, verdict=verdict), indent=2), encoding="utf-8")
    payload = {"ok": True, "project": project, "verdict": verdict.status,
               "path": str(path), "elements": len(governed.elements)}
    if "--json" in argv:
        print(json.dumps(payload))
    else:
        print(f"decision baseline snapshotted → {path} (verdict: {verdict.status})")
    return 0


def _cmd_recompile(argv: "list[str]") -> int:
    """The stale-decision diff (incremental recompile) — recompile the CURRENT governed map against the stored baseline:
    did the decision go stale, which claims flipped state, and what to test next. 'make' for arguments."""
    project = _flag(argv, "--project")
    if not project:
        print("usage: ztare scenario recompile --project <slug>  (snapshot first: ztare scenario baseline …)",
              file=sys.stderr)
        return 2
    import json

    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.argument_kernel import recompile
    from ztare.scenarios.artifacts import governed_state_from_research_map, governed_state_from_serialized

    path = _baseline_path(project)
    if not path.is_file():
        message = f"no decision baseline for '{project}' — snapshot one first"
        if "--json" in argv:
            print(json.dumps({"ok": False, "project": project, "error": message}))
        else:
            print(f"ztare: {message}: ztare scenario baseline --project {project}", file=sys.stderr)
        return 2
    try:
        old = governed_state_from_serialized(json.loads(path.read_text(encoding="utf-8")))
    except Exception as exc:  # noqa: BLE001 - corrupt state must not be silently compared.
        message = f"unreadable baseline: {type(exc).__name__}"
        if "--json" in argv:
            print(json.dumps({"ok": False, "project": project, "error": message}))
        else:
            print(f"ztare: {message}", file=sys.stderr)
        return 2
    new = governed_state_from_research_map(project, REPO_ROOT)
    rc = recompile(old, new)
    text_of = {element.id: element.text for element in new.elements}
    text_of.update({element.id: element.text for element in old.elements if element.id not in text_of})
    old_nodes = {element.id: element for element in old.elements}
    new_nodes = {element.id: element for element in new.elements}
    shared_ids = old_nodes.keys() & new_nodes.keys()

    # Historical maps used shorter generated ids. Pair direct ids first, then unchanged
    # nodes by semantic identity so an id-format migration does not masquerade as research
    # movement. The pairing and the edge comparison remain O(V + E).
    def semantic_key(element) -> tuple[str, str]:
        return (str(element.kind), " ".join(str(element.text).split()))

    old_tokens: dict[str, tuple] = {node_id: ("id", node_id) for node_id in shared_ids}
    new_tokens: dict[str, tuple] = {node_id: ("id", node_id) for node_id in shared_ids}
    old_by_semantic: dict[tuple[str, str], list[str]] = {}
    new_by_semantic: dict[tuple[str, str], list[str]] = {}
    for node_id, element in old_nodes.items():
        if node_id not in shared_ids:
            old_by_semantic.setdefault(semantic_key(element), []).append(node_id)
    for node_id, element in new_nodes.items():
        if node_id not in shared_ids:
            new_by_semantic.setdefault(semantic_key(element), []).append(node_id)
    for key in old_by_semantic.keys() & new_by_semantic.keys():
        for ordinal, (old_id, new_id) in enumerate(zip(sorted(old_by_semantic[key]),
                                                        sorted(new_by_semantic[key]))):
            token = ("semantic", *key, ordinal)
            old_tokens[old_id] = token
            new_tokens[new_id] = token

    removed_ids = old_nodes.keys() - old_tokens.keys()
    added_ids = new_nodes.keys() - new_tokens.keys()

    def edge_signature(edge, tokens: dict[str, tuple]) -> tuple:
        return (tokens.get(edge.src, ("unmatched", edge.src)), edge.kind,
                tokens.get(edge.dst, ("unmatched", edge.dst)), edge.warrant)

    old_edges = {edge_signature(edge, old_tokens): edge for edge in old.edges}
    new_edges = {edge_signature(edge, new_tokens): edge for edge in new.edges}

    def node_row(element) -> dict:
        return {"id": element.id, "kind": element.kind, "text": element.text}

    def edge_row(edge) -> dict:
        return {"from": edge.src, "from_text": text_of.get(edge.src, edge.src), "relation": edge.kind,
                "to": edge.dst, "to_text": text_of.get(edge.dst, edge.dst), "warrant": edge.warrant}

    changed_nodes = [
        {"id": node_id, "kind": new_nodes[node_id].kind,
         "before": old_nodes[node_id].text, "after": new_nodes[node_id].text}
        for node_id in sorted(shared_ids)
        if old_nodes[node_id].text != new_nodes[node_id].text
        or old_nodes[node_id].kind != new_nodes[node_id].kind
    ]
    graph_delta = {
        "counts": {
            "nodes_added": len(added_ids), "nodes_removed": len(removed_ids),
            "nodes_changed": len(changed_nodes), "edges_added": len(new_edges.keys() - old_edges.keys()),
            "edges_removed": len(old_edges.keys() - new_edges.keys()),
        },
        "nodes_added": [node_row(new_nodes[node_id]) for node_id in sorted(added_ids)[:25]],
        "nodes_removed": [node_row(old_nodes[node_id]) for node_id in sorted(removed_ids)[:25]],
        "nodes_changed": changed_nodes[:25],
        "edges_added": [edge_row(new_edges[key]) for key in sorted(new_edges.keys() - old_edges.keys())[:25]],
        "edges_removed": [edge_row(old_edges[key]) for key in sorted(old_edges.keys() - new_edges.keys())[:25]],
    }
    if "--json" in argv:
        print(json.dumps({
            "ok": True,
            "project": project,
            "was": rc["was"],
            "now": rc["now"],
            "decision_stale": rc["decision_stale"],
            "flipped": [{**row, "text": text_of.get(row["id"], row["id"])} for row in rc["flipped"]],
            "to_test": [
                {"assumption": row["assumption"], "text": text_of.get(row["assumption"], row["assumption"])}
                for row in rc["agenda"] if row.get("flips_alone") or row.get("in_cores")
            ][:5],
            "graph_delta": graph_delta,
        }, default=str))
        return 1 if rc["decision_stale"] else 0
    stale = "⚠️  STALE" if rc["decision_stale"] else "unchanged"
    print(f"decision: {rc['was']} → {rc['now']}   [{stale}]")
    for f in rc["flipped"]:
        el = new.by_id(f["id"]) or old.by_id(f["id"])
        print(f"  · {f['was']} → {f['now']}: {el.text[:70] if el else f['id']}")
    pivotal = [r for r in rc["agenda"] if r.get("flips_alone") or r.get("in_cores")]
    if pivotal:
        print("what to test next:")
        for r in pivotal[:5]:
            el = new.by_id(r["assumption"])
            print(f"  - {r['assumption']}{('  — ' + el.text[:60]) if el else ''}")
    return 1 if rc["decision_stale"] else 0


def _print_wager_receipt(w, r) -> None:
    print(f"decision test '{w.id}' on {w.claim_ref}: {r['reason']}")
    print(f"  admissible={r['admissible']} · info-yield {r['identification_bits']} bits · base verdict {r['base_verdict']}")
    for o in r["outcomes"]:
        if not o["edits_valid"]:
            print(f"  outcome {o['id']}: INVALID EDIT — {o.get('error', '')}")
        elif o["flips"]:
            print(f"  outcome {o['id']}: {o['was']} → {o['verdict']}  (moves the decision)")
        else:
            print(f"  outcome {o['id']}: {o['verdict']}  (no change)")


def _cmd_wager(argv: "list[str]") -> int:
    """Decision tests on a BLOCKED claim — the kernel simulates every declared outcome and admits a test only if
    a real result would move the decision; ranked by info-yield then cost. The claim's verdict is never changed
    (a test is not a fourth verdict). Actions: list | add | sim | expire."""
    action = argv[0] if argv and not argv[0].startswith("-") else "list"
    project = _flag(argv, "--project")
    if not project:
        print("usage: ztare scenario wager <list|add|sim|expire|execute> --project <slug> [--spec f.json] "
              "[--now ISO] [--id W --outcome O]", file=sys.stderr)
        return 2
    import json
    from datetime import date
    from pathlib import Path

    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.artifacts import governed_state_from_research_map
    from ztare.scenarios.wager import (expire_if_due, load_wagers as _load_wagers,
                                       save_wagers as _save_wagers, simulate,
                                       to_payload, wager_from_payload, wagers_path as _wagers_path)

    governed = governed_state_from_research_map(project, REPO_ROOT)
    if not governed.elements:
        print(f"ztare: no governed research map for '{project}' — run it first", file=sys.stderr)
        return 2

    js = "--json" in argv

    if action in ("add", "sim"):
        spec = _flag(argv, "--spec")
        spec_json = _flag(argv, "--spec-json")
        if not (spec or spec_json):
            print("usage: ztare scenario wager add --project <slug> (--spec <wager.json> | --spec-json <json>)", file=sys.stderr)
            return 2
        try:
            payload = json.loads(spec_json) if spec_json else json.loads(Path(spec).read_text(encoding="utf-8"))
            w = wager_from_payload(payload)
        except Exception as exc:  # noqa: BLE001
            if js:
                print(json.dumps({"ok": False, "error": f"malformed decision test: {type(exc).__name__}"}))
            else:
                print(f"ztare: malformed decision test: {type(exc).__name__}", file=sys.stderr)
            return 2
        r = simulate(governed, w)
        registered = bool(action == "add" and r["admissible"])
        if registered:
            _save_wagers(project, [p for p in _load_wagers(project) if p.get("id") != w.id] + [to_payload(w)])
        if js:
            print(json.dumps({"ok": True, "action": action, "registered": registered, "receipt": r}))
            return 0 if r["admissible"] else 1
        _print_wager_receipt(w, r)
        if action == "add" and not r["admissible"]:
            print("not added — a decision test must name a real result that moves the decision.", file=sys.stderr)
        elif registered:
            print(f"registered decision test '{w.id}' → {_wagers_path(project)}")
        return 0 if r["admissible"] else 1

    if action == "expire":
        now = _flag(argv, "--now") or date.today().isoformat()
        expired, out = 0, []
        for p in _load_wagers(project):
            w = expire_if_due(wager_from_payload(p), now)
            if w.lifecycle == "expired" and p.get("lifecycle") != "expired":
                expired += 1
            out.append(to_payload(w))
        _save_wagers(project, out)
        print(json.dumps({"ok": True, "expired": expired, "now": now}) if js else f"expired {expired} decision test(s) past {now}")
        return 0

    if action in ("preview", "execute"):
        wid, oid = _flag(argv, "--id"), _flag(argv, "--outcome")
        if not (wid and oid):
            print(f"usage: ztare scenario wager {action} --project <slug> --id <wager> --outcome <outcome>", file=sys.stderr)
            return 2
        from ztare.scenarios.wager import execute_project_outcome, preview_project_outcome
        try:
            receipt = (preview_project_outcome(project, wid, oid, REPO_ROOT) if action == "preview"
                       else execute_project_outcome(project, wid, oid, REPO_ROOT))
        except ValueError as exc:
            if js:
                print(json.dumps({"ok": False, "refused": True, "error": str(exc)}))
            else:
                print(f"ztare: decision-test outcome refused — {exc}", file=sys.stderr)
            return 1
        if js:
            print(json.dumps(receipt))
        else:
            applied = receipt.get("applied") or {}
            delta = receipt.get("decision_delta") or {}
            verb = "previewed" if action == "preview" else "executed"
            print(f"{verb} decision test '{wid}' → outcome '{oid}' "
                  f"({applied.get('evidence', 0)} evidence, {applied.get('edges', 0)} edge(s)); "
                  f"decision_changed={bool(delta.get('decision_changed'))}")
        return 0

    # list — the human's DECLARED wagers, ranked through the ONE unified agenda (same admission gate + lenses as
    # every other candidate — no separate rank_wagers / severity doors that could disagree), plus
    # inadmissible-with-reason + BLOCKED claims (candidates for a new wager).
    from ztare.scenarios.agenda import unified_agenda
    from ztare.scenarios.argument_kernel import claim_status, verdict as _verdict
    wagers = [wager_from_payload(p) for p in _load_wagers(project)]
    wmap = {w.id: w for w in wagers}
    rows = [r for r in unified_agenda(governed, declared=wagers) if r["source"] != "implicit"]  # declared + loop
    adm_ids = {r["id"] for r in rows}
    blocked = [{"id": c.id, "text": c.text} for c in (governed.of_kind("thesis") + governed.of_kind("claim"))
               if claim_status(governed, c.id) != "BACKED"]
    inadmissible = [{"id": w.id, "reason": simulate(governed, w)["reason"]} for w in wagers if w.id not in adm_ids]
    if js:
        for r in rows:
            w = wmap.get(r["id"])
            claim = governed.by_id(r["claim_ref"])
            r["claim_text"] = claim.text if claim else ""
            r["deadline"], r["lifecycle"] = (w.deadline, w.lifecycle) if w else ("", "")
            r["identification_bits"] = r["bits"]
            r["declared_cost"] = w.declared_cost if w else 0
            r["stakes"] = w.stakes if w else ""
            r["outcomes"] = simulate(governed, w).get("outcomes", []) if w else []
        print(json.dumps({"ok": True, "project": project, "verdict": _verdict(governed),
                          "wagers": rows, "agenda": rows, "inadmissible": inadmissible,
                          "blocked_claims": blocked}))
        return 0
    if not wagers:
        print(f"no decision tests for '{project}'. add one: ztare scenario wager add --project {project} --spec <wager.json>")
        return 0
    print(f"open decision tests on '{project}', ranked by the unified agenda (★ = on the tradeoff frontier):")
    for r in rows:
        w = wmap.get(r["id"])
        claim = governed.by_id(r["claim_ref"])
        star = "★" if r["on_frontier"] else " "
        cost = "undeclared" if r["cost"] is None else f"{r['cost']:g}"
        sev = max(r["max_displacement"]) if r["max_displacement"] else 0.0
        print(f"  {star} [{r['id']}] {r['test']}")
        print(f"       on: {claim.text[:70] if claim else r['claim_ref']}")
        print(f"       info-yield {r['bits']:.2f} bits · severity Δ{sev:.2f} · cost {cost}"
              + (f" · by {w.deadline}" if w and w.deadline else ""))
    for w in wagers:
        if w.id not in adm_ids:
            print(f"  · [{w.id}] not admitted — {simulate(governed, w)['reason']}")
    return 0


def _cmd_strength(argv: "list[str]") -> int:
    """The graded DECISION read (Fable's PM depth over one door): strength profile + status, what it rests on
    (Shapley), independent corroboration per warrant tier, hard cruxes, and the challenge queue by drag. Read-only;
    `--snapshot` also appends a trajectory point ('what moved since last run')."""
    project = _flag(argv, "--project")
    if not project:
        print("usage: ztare scenario strength --project <slug> [--json] [--snapshot]", file=sys.stderr)
        return 2
    import json

    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.argument_kernel import argument_analysis
    from ztare.scenarios.artifacts import governed_state_from_research_map
    from ztare.scenarios.research_signals import (challenge_queue, corroboration_independence, crux_pairs,
                                                  decision_trajectory, snapshot_strength)
    from ztare.scenarios.warrant_recheck import tier_hold_rates
    from ztare.scenarios.strength import shapley_support

    governed = governed_state_from_research_map(project, REPO_ROOT)
    if not governed.elements:
        print(f"ztare: no governed research map for '{project}' — run it first", file=sys.stderr)
        return 2
    analysis = argument_analysis(governed)
    strength = analysis.get("strength", {})
    from ztare.scenarios.decision_state import compile_decision_state
    decision_state = compile_decision_state(governed, analysis=analysis).to_payload()
    # Per-node profiles power the graph overlay, but this endpoint never renders them. Keep the decision
    # payload compact; the map derives its overlay from the same analysis contract.
    public_strength = {key: value for key, value in strength.items() if key != "per_node"}
    rests, corro = shapley_support(governed), corroboration_independence(governed)
    meaningful_rests = [
        row for row in rests.get("contributions", [])
        if abs(float(row[1] if len(row) > 1 else 0.0)) >= 0.005
    ]
    crux, queue = crux_pairs(governed), challenge_queue(governed)
    text = {e.id: e.text for e in governed.elements}
    if "--snapshot" in argv:
        snapshot_strength(project, governed)
    traj = decision_trajectory(project)

    if "--json" in argv:
        print(json.dumps({"ok": True, "project": project, "decision_state": decision_state,
                          "strength": public_strength, "text_of": text,
                          "calibration": tier_hold_rates(project, REPO_ROOT),
                          "rests_on": meaningful_rests[:8], "shapley": rests, "corroboration": corro,
                          "crux": crux, "challenge_queue": queue[:12],
                          "trajectory": {"iterations": traj.get("iterations"), "score_delta": traj.get("score_delta"),
                                         "strength_delta": traj.get("strength_delta"),
                                         "strength_series": traj.get("strength_series", [])[-24:]}}))
        return 0

    print(f"decision strength for '{project}': {strength.get('status')}   profile {strength.get('profile')}")
    print(f"  independent sources per tier (proven / reproducible / cited / unchecked): {corro}")
    if meaningful_rests:
        print("  what it rests on (top sources):")
        for sid, c in meaningful_rests[:5]:
            print(f"     {c:+.3f}  {text.get(sid, sid)[:64]}")
    elif rests.get("contributions"):
        print("  what it rests on: no source has a measurable contribution yet")
    elif rests.get("note"):
        print(f"  what it rests on: {rests['note']}")
    if crux:
        print(f"  hard cruxes (cannot both stand): {len(crux)}")
        for c in crux[:3]:
            print(f"     {c['a_text']}  x  {c['b_text']}")
    if queue:
        print("  challenges to resolve first (by drag):")
        for r in queue[:5]:
            print(f"     drag {r['drag']:+.3f}  {r['text']}")
    scores = [it.get("score") for it in traj.get("iterations", []) if it.get("score") is not None]
    if scores:
        d = f"  (Δ {traj['score_delta']:+})" if traj.get("score_delta") is not None else ""
        print(f"  score trajectory across {len(scores)} run(s): {scores}{d}")
    if traj.get("strength_delta"):
        print(f"  strength moved since last snapshot: Δ {traj['strength_delta']}")
    return 0


def _cmd_recheck(argv: "list[str]") -> int:
    """Re-earn / demote / expire the project's re-executable (W1) warrants by RE-RUNNING each bound recheck
    capability (e.g. a covenant recompute). PASS (re)mints W1, FAIL demotes, and a warrant older than
    `--half-life-days` expires — the warrant is minted by the check, never by fiat. Writes the recheck-owned
    slice of the governed overlay; re-run `strength` to see it move."""
    project = _flag(argv, "--project")
    if not project:
        print("usage: ztare scenario recheck --project <slug> [--half-life-days N] [--now YYYY-MM-DD] [--json]",
              file=sys.stderr)
        return 2
    import json

    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.artifacts import governed_state_from_research_map
    from ztare.scenarios.strength import strength_profile
    from ztare.scenarios.warrant_recheck import recheck_project

    now = _flag(argv, "--now")
    if not now:
        from datetime import date
        now = date.today().isoformat()
    hl = _flag(argv, "--half-life-days")
    half_life = int(hl) if hl and hl.lstrip("-").isdigit() else None

    before = strength_profile(governed_state_from_research_map(project, REPO_ROOT))
    result = recheck_project(project, REPO_ROOT, now=now, half_life_days=half_life)
    governed_after = governed_state_from_research_map(project, REPO_ROOT)
    after = strength_profile(governed_after)
    from ztare.scenarios.research_signals import snapshot_strength
    decision_history = snapshot_strength(project, governed_after, repo_root=REPO_ROOT)
    if "--json" in argv:
        print(json.dumps({"ok": True, "project": project, "now": now,
                          "receipts": result.get("receipts", []),
                          "before": {"status": before.get("status"), "profile": before.get("profile")},
                          "after": {"status": after.get("status"), "profile": after.get("profile")},
                          "decision_history": decision_history}))
        return 0
    receipts = result.get("receipts", [])
    if not receipts:
        print(f"recheck '{project}': no bound recheck capabilities (workspace/warrant_rechecks.json)")
        return 0
    print(f"recheck '{project}' @ {now}:")
    for r in receipts:
        tgt = r.get("target", {})
        edge = f" [{tgt.get('src')} {tgt.get('kind')} {tgt.get('dst')}]" if tgt else ""
        print(f"  {r['status']:>9}  {r['capability']}  {r.get('warrant','')}{edge}  — {r.get('detail') or r.get('reason','')}")
    print("  re-run `ztare scenario strength --project " + project + "` to see the profile move.")
    return 0


def _cmd_rice(argv: "list[str]") -> int:
    """Governed RICE — rank initiatives by Reach x Impact x Confidence / Effort, with Confidence READ from real
    backing strength (never typed) and each row flagging its weakest-backed factor. `--portfolio <file.json>`
    ranks a roadmap of decisions (each its own project, Confidence from its thesis strength); `--project <slug>`
    ranks the claims inside one decision. A bet with no backing scores 0 — you cannot buy rank with a claim."""
    import json
    from pathlib import Path

    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.rice import load_rice_inputs, portfolio_rice, rice_scores, save_rice_inputs

    portfolio, project = _flag(argv, "--portfolio"), _flag(argv, "--project")
    items_json, update_json = _flag(argv, "--items-json"), _flag(argv, "--update-json")
    payload: dict
    if portfolio or items_json:
        try:
            spec = json.loads(items_json) if items_json else json.loads(Path(portfolio).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            payload = {"ok": False, "mode": "portfolio",
                       "error": f"cannot read portfolio: {type(exc).__name__}: {exc}"}
            print(json.dumps(payload) if "--json" in argv else f"ztare: {payload['error']}",
                  file=sys.stdout if "--json" in argv else sys.stderr)
            return 2
        items = spec.get("items", []) if isinstance(spec, dict) else (spec if isinstance(spec, list) else [])
        payload = {"ok": True, "mode": "portfolio", "rows": portfolio_rice(items, REPO_ROOT)}
    elif project:
        from ztare.scenarios.artifacts import governed_state_from_research_map
        governed = governed_state_from_research_map(project, REPO_ROOT)
        if not governed.elements:
            payload = {"ok": False, "mode": "single", "project": project,
                       "error": f"no governed map for '{project}' — run it first"}
            print(json.dumps(payload) if "--json" in argv else f"ztare: {payload['error']}",
                  file=sys.stdout if "--json" in argv else sys.stderr)
            return 2
        saved = None
        if update_json:
            try:
                update = json.loads(update_json)
                claim_id = str(update.get("claim_id") or "").strip() if isinstance(update, dict) else ""
                factors = update.get("factors") if isinstance(update, dict) and isinstance(update.get("factors"), dict) else {}
                if not claim_id:
                    raise ValueError("choose an initiative")
                saved_factors = save_rice_inputs(project, REPO_ROOT, claim_id, factors)
                saved = {"claim_id": claim_id, "factors": saved_factors}
            except (json.JSONDecodeError, OSError, ValueError) as exc:
                payload = {"ok": False, "refused": True, "mode": "single", "project": project,
                           "error": str(exc)}
                print(json.dumps(payload) if "--json" in argv else f"ztare: {payload['error']}",
                      file=sys.stdout if "--json" in argv else sys.stderr)
                return 2
        inputs = load_rice_inputs(project, REPO_ROOT)
        payload = {"ok": True, "mode": "single", "project": project,
                   "rows": rice_scores(governed, inputs), "inputs": inputs,
                   "evidence": [{"id": element.id, "text": element.text}
                                for element in governed.of_kind("evidence")]}
        if saved:
            payload["saved"] = saved
    else:
        payload = {"ok": False, "error": "provide items[] (a portfolio) or a project slug"}
        print(json.dumps(payload) if "--json" in argv else
              "usage: ztare scenario rice (--portfolio <file.json> | --items-json <json> | --project <slug>) [--json]",
              file=sys.stdout if "--json" in argv else sys.stderr)
        return 2

    if "--json" in argv:
        print(json.dumps(payload, default=str))
        return 0
    rows = payload["rows"]
    if not rows:
        print("no initiatives to score")
        return 0
    print("Governed RICE — Confidence is READ from backing strength, not typed (a bet with no backing scores 0):")
    print(f"  {'#':>2}  {'RICE':>9}  {'confidence':>24}  {'weakest factor':<22}  initiative")
    for r in rows:
        conf = f"{r['confidence']:.2f} ({r['confidence_tier']})"
        weak = f"{r['weakest']['factor']} is {r['weakest']['tier']}"
        print(f"  {r['rank']:>2}  {r['score']:>9.1f}  {conf:>24}  {weak:<22}  {str(r['initiative'])[:46]}")
    return 0


def _cmd_beliefs(argv: "list[str]") -> int:
    """The belief ledger — 'what would you have to believe?' (Rivkin), COMPUTED not generated: the load-bearing
    conditions the decision rests on (minimal cores + dominators), each with its backing tier, the RISKS (load-
    bearing but still unchecked/cited — bet on blind), and the next-best experiment to firm the weakest."""
    project = _flag(argv, "--project")
    if not project:
        print("usage: ztare scenario beliefs --project <slug> [--json]", file=sys.stderr)
        return 2
    import json

    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.artifacts import governed_state_from_research_map
    from ztare.scenarios.belief_ledger import belief_ledger

    governed = governed_state_from_research_map(project, REPO_ROOT)
    if not governed.elements:
        print(f"ztare: no governed map for '{project}' — run it first", file=sys.stderr)
        return 2
    led = belief_ledger(governed)
    if "--json" in argv:
        print(json.dumps({"ok": True, "project": project, **led}))
        return 0
    conds = led["conditions"]
    if not conds:
        print(f"'{project}': the thesis rests on nothing checkable yet — no load-bearing conditions to show "
              "(it is unsupported; you would have to believe something, and right now you believe nothing checked).")
        return 0
    print(f"What you'd have to believe — '{project}' ({len(led['cores'])} way(s) it could be right):")
    for r in conds:
        flag = "  ⚑ load-bearing everywhere" if r["load_bearing_everywhere"] else ""
        print(f"  [{r['tier']:>12}]  {str(r['text'])[:60]}{flag}")
    if led["risks"]:
        print("  RISKS (load-bearing but bet on blind):")
        for r in led["risks"]:
            print(f"     {r['tier']}: {str(r['text'])[:64]}")
    ne = led.get("next_experiment")
    if ne:
        print(f"  Next-best experiment → {str(ne['text'])[:56]}  ({ne['do']})")
    return 0


def _cmd_deliverables(argv: "list[str]") -> int:
    """Compose-vs-loop gap map: for each required deliverable, can it be COMPOSED from the current governed state
    now, or does it need the loop / a template? `--declared a,b,c` (else decision_memo); `--generate <name>`
    composes it now if composable (never fabricates), else reports it needs the loop. A selected scenario may
    add declarative document recipes with `--scenario <name>`."""
    project = _flag(argv, "--project")
    if not project:
        print("usage: ztare scenario deliverables --project <slug> [--scenario <name>] [--declared a,b,c] "
              "[--add <name>] [--generate <name>] [--editorial <name>] [--produce-all] [--json]",
              file=sys.stderr)
        return 2
    import json

    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.artifacts import governed_state_from_research_map
    from ztare.scenarios.production import (add_required_deliverable, deliverable_binding_status,
                                            deliverable_gaps, produce_scenario_artifacts,
                                            resolve_declared_set, scenario_contract)
    from ztare.workspace.report_actions import display_path

    governed = governed_state_from_research_map(project, REPO_ROOT)
    if not governed.elements:
        print(f"ztare: no governed map for '{project}' — run it first", file=sys.stderr)
        return 2
    scenario = _flag(argv, "--scenario")
    scenario_names, specs = scenario_contract(scenario)
    declared = _flag(argv, "--declared")
    declared_list = ([d.strip() for d in declared.split(",") if d.strip()] if declared
                     else resolve_declared_set(project, scenario_deliverables=scenario_names, repo_root=REPO_ROOT))
    add = _flag(argv, "--add")
    if add:
        add_required_deliverable(project, add, repo_root=REPO_ROOT)
        declared_list = resolve_declared_set(project, scenario_deliverables=scenario_names, repo_root=REPO_ROOT)
    if "--provenance" in argv:
        from ztare.scenarios.contract_receipts import contract_drift, deliverable_provenance

        try:
            payload = {"ok": True, "project": project,
                       "provenance": deliverable_provenance(project, declared_list, REPO_ROOT),
                       "drift": contract_drift(project, REPO_ROOT)}
        except Exception as exc:  # noqa: BLE001 - malformed history is visible, not treated as clean.
            payload = {"ok": False, "project": project, "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(payload, default=str) if "--json" in argv else
              (f"document history for '{project}': {len((payload.get('provenance') or {}).get('deliverables', []))} item(s)"
               if payload.get("ok") else payload.get("error")))
        return 0 if payload.get("ok") else 2
    if "--produce-all" in argv:
        from ztare.scenarios.production import produce_all_declared

        try:
            report = produce_all_declared(project, repo_root=REPO_ROOT, scenario=scenario)
            payload = {"ok": report.get("ok", True), "project": project, **report}
        except Exception as exc:  # noqa: BLE001 - a failed firewall/build is returned, never partially hidden.
            payload = {"ok": False, "project": project, "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(payload, default=str) if "--json" in argv else
              (f"created {len(payload.get('written', []))} checked draft(s)" if payload.get("ok")
               else f"could not create document set: {payload.get('error')}"))
        return 0 if payload.get("ok") else 2
    editorial = _flag(argv, "--editorial")
    if editorial:
        import re

        from ztare.common.llm_runtime import LLMRuntime, pick_model_for_tier, resolve_model_id
        from ztare.scenarios.editorial import create_editorial_draft
        from ztare.scenarios.firewall import provenance_firewall
        from ztare.scenarios.production import build_scenario_deliverable
        from ztare.workspace.report_actions import display_path, report_model

        deliverable = build_scenario_deliverable(editorial, governed, specs=specs)
        if deliverable.stub_reason:
            payload = {"ok": False, "project": project, "name": editorial,
                       "error": deliverable.stub_reason}
        else:
            firewall = provenance_firewall([deliverable], governed, [editorial])
            if not firewall.ok:
                payload = {"ok": False, "project": project, "name": editorial,
                           "error": "checked draft failed its provenance check",
                           "violations": firewall.violations}
            else:
                configured = report_model(root=REPO_ROOT)
                model_id = resolve_model_id(configured) if configured else pick_model_for_tier("balanced")
                if not model_id:
                    payload = {"ok": False, "project": project, "name": editorial,
                               "error": "no report model is configured"}
                else:
                    def call(prompt: str) -> str:
                        response = LLMRuntime().call_text(prompt, model_id=model_id, timeout_seconds=120,
                                                          retries=0, fallback_model_ids=())
                        return str(getattr(response, "text", "") or "")

                    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", editorial).strip("._-") or "document"
                    out_path = (REPO_ROOT / "projects" / project / "workspace" / "deliverables"
                                / f"{safe_name}.editorial-draft.md")
                    try:
                        payload = create_editorial_draft(deliverable, governed, call=call, out_path=out_path)
                        payload.update({"project": project, "name": editorial, "model": model_id,
                                        "path": display_path(payload["path"]),
                                        "receipt_path": display_path(payload["receipt_path"])})
                    except Exception as exc:  # noqa: BLE001 - invalid model output is refused, never promoted.
                        payload = {"ok": False, "project": project, "name": editorial,
                                   "error": f"audience shaping refused: {type(exc).__name__}: {exc}"}
        print(json.dumps(payload, default=str) if "--json" in argv else
              (f"audience draft → {payload.get('path')}" if payload.get("ok") else payload.get("error")))
        return 0 if payload.get("ok") else 2
    gen = _flag(argv, "--generate")
    if gen:
        row = next(iter(deliverable_gaps(governed, [gen], specs=specs)["deliverables"]), None)
        if row and row["status"] == "composable":
            out = str(REPO_ROOT / "projects" / project / "workspace" / "deliverables")
            rep = produce_scenario_artifacts(declared=[gen], governed=governed, out_dir=out, specs=specs)
            generated = gen in rep["written"]
            if "--json" in argv:
                print(json.dumps({"ok": generated, "project": project, "name": gen, "generated": generated,
                                  "path": display_path(f"{out}/{gen}.md") if generated else None,
                                  "verdict": rep.get("verdict"), "violations": rep.get("violations", [])}))
            else:
                print(f"generated '{gen}' → {out}/{gen}.md" if generated else f"could not generate '{gen}'")
        else:
            payload = {"ok": False, "project": project, "name": gen, "generated": False,
                       "status": row["status"] if row else "unknown",
                       "action": row["action"] if row else "unknown deliverable"}
            print(json.dumps(payload) if "--json" in argv
                  else f"'{gen}' cannot be composed now — {payload['action']}")
        return 0
    result = deliverable_gaps(governed, declared_list, specs=specs)
    out_dir = str(REPO_ROOT / "projects" / project / "workspace" / "deliverables")
    binding = deliverable_binding_status(governed, declared_list, out_dir, root=REPO_ROOT)
    for row in result["deliverables"]:
        row.update(binding["bindings"].get(row["name"], {}))
    result["decision"] = binding["decision"]
    if "--json" in argv:
        print(json.dumps({"ok": True, "project": project, **result}))
        return 0
    print(f"required deliverables for '{project}' (compose now vs needs the loop):")
    for d in result["deliverables"]:
        print(f"  [{d['status']:>13}] {d['name']} — {d['action']}")
    return 0


def main(argv: "list[str]") -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(_USAGE)
        return 0
    handlers = {"list": _cmd_list, "show": _cmd_show, "validate": _cmd_validate,
                "new": _cmd_new, "reingest": _cmd_reingest, "surface": _cmd_surface,
                "annotate": _cmd_annotate, "bind": _cmd_bind, "brief": _cmd_brief, "plugins": _cmd_plugins,
                "attribution": _cmd_attribution,
                "agenda": _cmd_agenda, "baseline": _cmd_baseline, "recompile": _cmd_recompile,
                "wager": _cmd_wager, "strength": _cmd_strength, "recheck": _cmd_recheck, "rice": _cmd_rice,
                "beliefs": _cmd_beliefs, "deliverables": _cmd_deliverables}
    h = handlers.get(argv[0])
    if h is None:
        print(f"ztare scenario: unknown subverb '{argv[0]}'\n{_USAGE}", file=sys.stderr)
        return 2
    return h(argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
