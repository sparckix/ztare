"""`ztare scenario` subverbs intrinsic to scenarios: list | show | validate | new.

`run` is NOT here — it couples to autoresearch, so the top-level CLI router delegates it to
`autoresearch run --scenario <name>` (one binding path, no duplication). Everything here is pure scenario I/O.
"""
from __future__ import annotations

import sys

from ztare.scenarios.config import ScenarioConfig
from ztare.scenarios.loader import list_scenarios, load_scenario, scenario_path

_USAGE = "usage: ztare scenario <list|show|validate|new|run|surface|annotate|reingest|brief|plugins|agenda|baseline|recompile|recheck|rice|beliefs|deliverables|wager|strength> [args]"


def _flag(argv: "list[str]", name: str) -> str:
    for i, arg in enumerate(argv):
        if arg == name and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith(name + "="):
            return arg.split("=", 1)[1]
    return ""

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


def _cmd_list(_argv: "list[str]") -> int:
    names = list_scenarios()
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
        print(f"ztare: {exc}", file=sys.stderr)
        return 2
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
    pos = [a for a in argv if not a.startswith("-")]
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
    pos = [a for a in argv if not a.startswith("-")]
    project = _flag(argv, "--project")
    promote_to = _flag(argv, "--promote")
    if not pos or not project:
        print("usage: ztare scenario reingest <polished.md> --project <slug> [--promote <out.md>]", file=sys.stderr)
        return 2
    from pathlib import Path

    doc = Path(pos[0])
    if not doc.is_file():
        print(f"ztare: {doc} not found", file=sys.stderr)
        return 2
    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.artifacts import governed_state_from_research_map, open_reingest_session, promote_reingest

    governed = governed_state_from_research_map(project, REPO_ROOT)
    if not governed.elements:
        print(f"ztare: no governed research map for project '{project}' — run it first", file=sys.stderr)
        return 2
    text = doc.read_text(encoding="utf-8")
    session = open_reingest_session(project, text, governed)
    d = session.diff
    print(f"reingest diff for {doc.name}: {d.traced_claims} claim(s) traced · "
          f"{len(d.dropped_claims)} claim(s) dropped · {len(d.ungoverned)} ungoverned sentence(s)")
    for violation in d.ungoverned[:20]:
        print(f"  ✗ UNGOVERNED: {violation}", file=sys.stderr)
    if promote_to:
        result = promote_reingest(session, text, governed, promote_to)
        if result["promoted"]:
            print(f"PROMOTED → {result['path']} (+ audit record); {result['traced_claims']} claim(s) traced")
            return 0
        print(f"NOT PROMOTED: {result['reason']}", file=sys.stderr)
        return 1
    return 0 if session.promotable else 1


def _cmd_surface(argv: "list[str]") -> int:
    """Intake funnel: a document → its load-bearing ASSUMPTIONS as bounded claims to test, each anchored to a
    VERBATIM source span. The LLM proposes; the kernel gates every anchor (fail-closed) — a hallucinated
    assumption is dropped. Each surfaced claim is a thesis you can then run through the governed loop."""
    pos = [a for a in argv if not a.startswith("-")]
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
    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.artifacts import (
        GovernedState,
        annotate,
        governed_state_from_research_map,
        render_annotated,
    )
    from ztare.scenarios.surfacing import surface_assumptions

    governed = governed_state_from_research_map(project, REPO_ROOT) if project else GovernedState()
    spans: "list[str]" = []
    rejected: "list[str]" = []
    try:  # surfacing needs an LLM; annotate still runs with [] (governed-map alignment only) if absent
        from ztare.scenarios.providers.llm_proposer import llm_proposer
        sres = surface_assumptions(doc, lambda d: llm_proposer(d, model=_flag(argv, "--model")))
        spans, rejected = [c.span for c in sres.anchored], sres.rejected
    except Exception as exc:  # noqa: BLE001 — degrade to map-only, never crash the round-trip
        print(f"ztare: assumption-surfacing skipped (no LLM: {exc}); annotating against the governed map only",
              file=sys.stderr)

    anns = annotate(doc, governed, surfaced_spans=spans)
    counts = {s: sum(1 for a in anns if a.status == s) for s in
              ("UNTESTED", "BACKED", "CONTRADICTED", "INERT")}
    out = doc_path.with_suffix(doc_path.suffix + ".annotated.md")
    out.write_text(render_annotated(doc_path.name, anns, rejected=rejected), encoding="utf-8")
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
    if out:
        print(f"wrote {out}")
    else:
        print(result.text)
    return 0


def _cmd_plugins(argv: "list[str]") -> int:
    """Everything installed, across the three plugin kinds — SCENARIOS (`scenarios/*.yaml`), RUBRICS
    (`rubrics/*.json`), and CAPABILITIES (`@capability` code, incl. any dropped in a plugin dir). `--reload`
    re-discovers so a just-dropped code plugin goes live without a restart."""
    from ztare.common.paths import RUBRICS_DIR
    from ztare.scenarios import registry

    if "--reload" in argv:
        registry.reload()
        print("reloaded plugin discovery")
    print("SCENARIOS (scenarios/*.yaml):")
    for n in list_scenarios():
        print(f"  {n}")
    print("RUBRICS (rubrics/*.json):")
    for p in sorted(RUBRICS_DIR.glob("*.json")):
        print(f"  {p.stem}")
    print("CAPABILITIES (@capability code):")
    for kind, names in registry.installed().items():
        print(f"  {kind}: {names or '[]'}")
    for row in registry.diagnostics().get("load_errors", []):
        print(f"  ! {row['path']}: {row['error']}")
    dirs = registry.plugin_dirs()
    print(f"PLUGIN DIRS (drop a .py here, then --reload): {dirs or '[none — set $ZTARE_SCENARIO_PLUGINS]'}")
    return 0


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
        print(f"ztare: no governed research map for project '{project}' — run it first", file=sys.stderr)
        return 2
    a = argument_analysis(governed)
    print(f"verdict: {a['verdict']}   warrant ceiling: {a['warrant_ceiling'] or '(no support)'}")
    if a["dominators"]:
        print(f"dominators (every path routes through): {a['dominators']}")
    if a["minimal_cores"]:
        print(f"minimal cores (jointly decide the verdict): {a['minimal_cores'][:8]}")
    # What to test next — the ONE unified agenda (implicit + declared + loop-proposed, all normalized to wagers,
    # ranked once with the Pareto frontier ★ marked). Supersedes the old single-lens test-agenda print.
    from ztare.scenarios.agenda import project_agenda
    ag = project_agenda(project, REPO_ROOT)
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
    if "--emit" in argv:  # close-the-loop producer: write governed_agenda.jsonl the loop steers its next action by
        from ztare.scenarios.agenda import emit_governed_agenda
        info = emit_governed_agenda(project, REPO_ROOT)
        print(f"governed agenda → {info['path']} ({info['count']} rows)")
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

    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.artifacts import assemble_verdict, governed_state_from_research_map, serialize_governed

    governed = governed_state_from_research_map(project, REPO_ROOT)
    if not governed.elements:
        print(f"ztare: no governed research map for project '{project}' — run it first", file=sys.stderr)
        return 2
    path = _baseline_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(serialize_governed(governed, verdict=assemble_verdict(governed)), indent=2),
                    encoding="utf-8")
    print(f"decision baseline snapshotted → {path} (verdict: {assemble_verdict(governed).status})")
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
        print(f"ztare: no decision baseline for '{project}' — snapshot one: ztare scenario baseline --project {project}",
              file=sys.stderr)
        return 2
    old = governed_state_from_serialized(json.loads(path.read_text(encoding="utf-8")))
    new = governed_state_from_research_map(project, REPO_ROOT)
    rc = recompile(old, new)
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
        if not spec:
            print("usage: ztare scenario wager add --project <slug> --spec <wager.json>", file=sys.stderr)
            return 2
        w = wager_from_payload(json.loads(Path(spec).read_text(encoding="utf-8")))
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
        print(json.dumps({"ok": True, "expired": expired}) if js else f"expired {expired} decision test(s) past {now}")
        return 0

    if action == "execute":
        wid, oid = _flag(argv, "--id"), _flag(argv, "--outcome")
        if not (wid and oid):
            print("usage: ztare scenario wager execute --project <slug> --id <wager> --outcome <outcome>", file=sys.stderr)
            return 2
        from ztare.scenarios.wager import execute_project_outcome
        try:
            receipt = execute_project_outcome(project, wid, oid, REPO_ROOT)
        except ValueError as exc:
            print(f"ztare: decision-test outcome refused — {exc}", file=sys.stderr)
            return 1
        if js:
            print(json.dumps(receipt))
        else:
            applied = receipt.get("applied") or {}
            delta = receipt.get("decision_delta") or {}
            print(f"executed decision test '{wid}' → outcome '{oid}' written to the governed map "
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
            r["deadline"], r["lifecycle"] = (w.deadline, w.lifecycle) if w else ("", "")
        print(json.dumps({"ok": True, "project": project, "verdict": _verdict(governed),
                          "agenda": rows, "inadmissible": inadmissible, "blocked_claims": blocked}))
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
                                         "strength_delta": traj.get("strength_delta")}}))
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
    from ztare.scenarios.warrant_recheck import recheck_project

    now = _flag(argv, "--now")
    if not now:
        from datetime import date
        now = date.today().isoformat()
    hl = _flag(argv, "--half-life-days")
    half_life = int(hl) if hl and hl.lstrip("-").isdigit() else None

    result = recheck_project(project, REPO_ROOT, now=now, half_life_days=half_life)
    if "--json" in argv:
        print(json.dumps(result))
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
    from ztare.scenarios.rice import load_rice_inputs, portfolio_rice, rice_scores

    portfolio, project = _flag(argv, "--portfolio"), _flag(argv, "--project")
    if portfolio:
        try:
            spec = json.loads(Path(portfolio).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"ztare: cannot read portfolio {portfolio}: {type(exc).__name__}", file=sys.stderr)
            return 2
        items = spec.get("items", []) if isinstance(spec, dict) else (spec if isinstance(spec, list) else [])
        rows = portfolio_rice(items, REPO_ROOT)
    elif project:
        from ztare.scenarios.artifacts import governed_state_from_research_map
        governed = governed_state_from_research_map(project, REPO_ROOT)
        if not governed.elements:
            print(f"ztare: no governed map for '{project}' — run it first", file=sys.stderr)
            return 2
        rows = rice_scores(governed, load_rice_inputs(project, REPO_ROOT))
    else:
        print("usage: ztare scenario rice (--portfolio <file.json> | --project <slug>) [--json]", file=sys.stderr)
        return 2

    if "--json" in argv:
        print(json.dumps({"ok": True, "rows": rows}))
        return 0
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
        print("usage: ztare scenario deliverables --project <slug> [--scenario <name>] [--declared a,b,c] [--generate <name>] [--json]",
              file=sys.stderr)
        return 2
    import json

    from ztare.common.paths import REPO_ROOT
    from ztare.scenarios.artifacts import governed_state_from_research_map
    from ztare.scenarios.production import deliverable_gaps, produce_scenario_artifacts, scenario_contract

    governed = governed_state_from_research_map(project, REPO_ROOT)
    if not governed.elements:
        print(f"ztare: no governed map for '{project}' — run it first", file=sys.stderr)
        return 2
    scenario = _flag(argv, "--scenario")
    scenario_names, specs = scenario_contract(scenario)
    declared = _flag(argv, "--declared")
    declared_list = [d.strip() for d in declared.split(",") if d.strip()] if declared else (scenario_names or ["decision_memo"])
    gen = _flag(argv, "--generate")
    if gen:
        row = next(iter(deliverable_gaps(governed, [gen], specs=specs)["deliverables"]), None)
        if row and row["status"] == "composable":
            out = str(REPO_ROOT / "projects" / project / "workspace" / "deliverables")
            rep = produce_scenario_artifacts(declared=[gen], governed=governed, out_dir=out, specs=specs)
            print(f"generated '{gen}' → {out}/{gen}.md" if gen in rep["written"] else f"could not generate '{gen}'")
        else:
            print(f"'{gen}' cannot be composed now — {row['action'] if row else 'unknown deliverable'}")
        return 0
    result = deliverable_gaps(governed, declared_list, specs=specs)
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
                "annotate": _cmd_annotate, "brief": _cmd_brief, "plugins": _cmd_plugins,
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
