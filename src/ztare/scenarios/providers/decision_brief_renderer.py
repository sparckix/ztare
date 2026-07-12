"""decision_brief — a Renderer PLUGIN for a governed decision surface (domain-neutral: any hardened claim, be
it product / finance / security / research). Presentation lives here, NOT in the kernel: the kernel emits DATA
(`serialize_governed`: verdict + coverage + counterfactual `decision_hinges`), and this renderer lays it out —
DECISION → what it hinges on → evidence status → falsifiers → governed document — with the research apparatus
(IDs, edges, provenance) folded into a collapsed audit drawer. It consumes the serialized dict (the export
format), so it is fully decoupled from the kernel objects; deleting this file removes the brief with zero kernel
change (the rot test). Proves the Renderer protocol with a second, non-trivial renderer beyond `markdown`."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ztare.scenarios.protocols import RenderResult
from ztare.scenarios.registry import capability

_RECOMMENDATION = {
    "SUPPORTED": "Proceed — the bet holds under the current governed evidence.",
    "BLOCKED": "Hold — an open question blocks the decision.",
    "REFUTED": "Do not proceed as stated — the governed evidence contradicts the bet.",
}


def _compose_brief(data: "dict[str, Any]") -> str:
    """Lay out the governed-artifact DATA as a decision brief (domain-neutral). Pure over the serialized dict — no kernel
    imports, no model, nothing ungoverned (every line traces to an element the kernel emitted)."""
    verdict = data.get("verdict", {}) or {}
    argument = data.get("argument", {}) or {}
    elements = data.get("elements", []) or []
    edges = data.get("edges", []) or []
    text_of = {e.get("id"): e.get("text", "") for e in elements}
    claims = [e for e in elements if e.get("kind") in ("thesis", "claim")]
    falsifiers = [e for e in elements if e.get("kind") == "falsifier"]
    supported = {e.get("dst") for e in edges if e.get("kind") in ("SUPPORTS", "DERIVES")}
    status = verdict.get("status", "?")
    cores = argument.get("minimal_cores") or []

    lines = [f"# Decision brief — {data.get('title', 'governed claim')}", "",
             f"**Decision: {status}.** {_RECOMMENDATION.get(status, '')}",
             f"<sub>coverage {verdict.get('coverage', 0)} — the fraction of claims that are grounded-accepted</sub>",
             "", "## What the decision hinges on", ""]
    # The ATMS minimal cores: the minimal assumption-sets whose JOINT failure flips the decision (subsumes the
    # old single-toggle hinge — a 2-element core is a jointly-pivotal pair single-toggle can't see).
    if cores:
        for core in cores[:5]:
            if len(core) == 1:
                lines.append(f"- **{text_of.get(core[0], core[0])}** — resolving it alone flips the decision.")
            else:
                joint = " + ".join(text_of.get(a, a) for a in core)
                lines.append(f"- **jointly:** {joint} — together they decide it (none flips alone).")
    else:
        lines.append("- No assumption-set flips the decision from its current state.")

    lines += ["", "## Evidence status", ""]
    lines += [f"- {c.get('text', '')} — _{'backed' if c.get('id') in supported else 'no evidence yet'}._"
              for c in claims] or ["- (no claims in the governed state)"]

    # PRESCRIPTIVE: what to test next (the argument kernel's possibilistic test agenda) + the warrant ceiling.
    arg = data.get("argument") or {}
    agenda = [r for r in (arg.get("test_agenda") or []) if r.get("flips_alone") or r.get("in_cores")]
    if agenda or arg.get("warrant_ceiling"):
        lines += ["", "## What to test next", ""]
        if arg.get("warrant_ceiling"):
            lines.append(f"_Trust ceiling: this decision is no stronger than its weakest support "
                         f"(warrant **{arg['warrant_ceiling']}**)._")
        for r in agenda[:5]:
            why = "resolving it flips the decision" if r.get("flips_alone") else f"in {r['in_cores']} decisive set(s)"
            lines.append(f"- **{r.get('assumption')}** — {why}.")
        if not agenda:
            lines.append("- No single untested assumption flips the decision on its own.")

    lines += ["", "## What would change the decision", ""]
    lines += [f"- {f.get('text', '')}" for f in falsifiers] or ["- (no explicit kill-criterion recorded)"]

    lines += ["", "<details>", "<summary>Audit drawer — provenance, IDs, graph</summary>", "",
              f"- verdict: {status} — {verdict.get('reason', '')}",
              f"- decision hinge (counterfactual): `{verdict.get('load_bearing', '')}`",
              f"- governed elements ({len(elements)}): {sorted(e.get('id', '') for e in elements)}",
              f"- governed edges ({len(edges)}): "
              + (", ".join(f"{e.get('src')}-{e.get('kind')}-{e.get('dst')}" for e in edges[:40]) or "(none)"),
              "", "</details>", ""]
    return "\n".join(lines) + "\n"


@capability("renderer", "decision_brief")
class DecisionBriefRenderer:
    """A Renderer over the serialized governed artifact. `result` is a `serialize_governed(...)` dict; a thin
    dict (title/verdict/score only) still renders a minimal brief."""
    name = "decision_brief"

    def render(self, result: "dict[str, Any]", *, dest: str = "") -> RenderResult:
        text = _compose_brief(result if isinstance(result, dict) else {})
        if dest:
            Path(dest).write_text(text, encoding="utf-8")
        return RenderResult(path=dest, text=text, kind="markdown")


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    data = {
        "title": "one-click checkout",
        "elements": [{"id": "t1", "kind": "thesis", "text": "Net positive ROI"},
                     {"id": "c1", "kind": "claim", "text": "Completion lift >=1pp"},
                     {"id": "e1", "kind": "evidence", "text": "Beta n=40, 82% vs 74%"},
                     {"id": "f1", "kind": "falsifier", "text": "If A/B <1pp lift, roll back"}],
        "edges": [{"src": "e1", "kind": "SUPPORTS", "dst": "c1"}],
        "verdict": {"status": "BLOCKED", "reason": "a target claim is unsupported", "load_bearing": "t1",
                    "load_bearing_ties": ["t1"], "coverage": 0.5},
        "argument": {"verdict": "BLOCKED", "warrant_ceiling": "W2", "minimal_cores": [["t1"], ["c1", "c2"]],
                     "dominators": [], "test_agenda": [
                         {"assumption": "t1", "flips_alone": True, "in_cores": 1, "identification": 1.0, "cost": 1.0}]},
    }
    brief = DecisionBriefRenderer().render(data).text
    ok("brief leads with the DECISION + coverage", "**Decision: BLOCKED.**" in brief and "coverage 0.5" in brief)
    ok("brief shows a size-1 minimal core (resolving it alone flips the decision)",
       "Net positive ROI" in brief and "flips the decision" in brief)
    ok("brief shows a JOINTLY-pivotal core (the case single-toggle misses)",
       "jointly:" in brief and "none flips alone" in brief)
    ok("brief shows a prescriptive 'What to test next' with the trust ceiling",
       "What to test next" in brief and "warrant **W2**" in brief)
    ok("brief shows evidence status (backed vs no evidence yet)",
       "backed" in brief and "no evidence yet" in brief)
    ok("brief lists falsifiers", "roll back" in brief)
    ok("apparatus is in a collapsed audit drawer, not up top",
       "<details>" in brief and brief.index("hinges on") < brief.index("<details>"))
    ok("a thin dict still renders without crashing", "Decision" in DecisionBriefRenderer().render({}).text)

    print("DECISION-BRIEF RENDERER SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
