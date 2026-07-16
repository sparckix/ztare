"""Governed RICE — PM prioritization where every factor is GOVERNED and WARRANTED, a capability INSIDE the
product-manager scenario (not a new scenario). Classic RICE = Reach x Impact x Confidence / Effort, but with two
governed twists that no spreadsheet has:

  1. CONFIDENCE IS NOT TYPED. It is READ from the initiative's warrant-strength profile (the kernel), so a bet
     backed by re-executable evidence outranks a quote-backed one at the same nominal score. You cannot inflate
     a bet's rank by asserting high confidence — you earn it with checkable backing (and lose it on a recheck).
  2. EVERY FACTOR CARRIES A WARRANT TIER. Reach / Impact / Effort each cite a governed source at a tier
     (re-executable telemetry > a quoted doc > a proposed guess), and the ranking surfaces the WEAKEST-warranted
     factor per row — "ranks #1, but its Reach is a proposed guess; go check it."

Plain-language only in outputs (no internal codes — the tiers are proven / reproducible / cited / unchecked,
hardest to flimsiest). Deterministic, no LLM; Confidence has NO free numeric prior (it is the kernel strength).
"""
from __future__ import annotations

import math
import re

# The one tier vocabulary (scenarios.tiers). `_TIER_RANK` here is CODE-keyed (factors carry a warrant code).
from ztare.scenarios.tiers import (  # noqa: E402 — one vocab, no local copies
    PROFILE_TIER as _PROFILE_TIER, TIER_NAME as _TIER_NAME, WARRANT_RANK as _TIER_RANK)

_EPS = 1e-6


def _number(value, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def _factor(raw: "dict | float | int | str | None", *, default_warrant: str = "W3") -> dict:
    """One bounded factor estimate plus the compiler-derived warrant of its source."""
    raw = raw if isinstance(raw, dict) else ({"value": raw} if raw is not None else {})
    warrant = str(raw.get("warrant") or default_warrant)
    if warrant not in _TIER_NAME:
        warrant = default_warrant
    value = _number(raw.get("value"))
    low = _number(raw.get("low"), value)
    high = _number(raw.get("high"), value)
    low, high = min(low, value, high), max(low, value, high)
    return {
        "value": value,
        "low": low,
        "high": high,
        "warrant": warrant,
        "tier": _TIER_NAME[warrant],
        "ref": str(raw.get("ref") or ""),
        "unit": str(raw.get("unit") or ""),
        "backing_status": str(raw.get("backing_status") or "unchecked"),
    }


def _text_contains_value(text: str, value: float) -> bool:
    """Deterministic numeric grounding: the selected evidence must actually contain the estimate."""
    for token in re.findall(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?", text or ""):
        try:
            if math.isclose(float(token.replace(",", "")), value, rel_tol=1e-9, abs_tol=1e-9):
                return True
        except ValueError:
            continue
    return False


def _derived_factor(governed, target_id: str, raw: "dict | None") -> dict:
    """Derive a factor's warrant from its selected evidence and admitted SUPPORTS edge.

    A stored ``warrant`` field is ignored. The numeric estimate must appear in the cited evidence text and that
    evidence must support this exact initiative; otherwise the factor remains unchecked.
    """
    factor = _factor(raw)
    ref = factor["ref"]
    source = governed.by_id(ref) if ref else None
    if not source or source.kind != "evidence":
        factor.update({"warrant": "W3", "tier": _TIER_NAME["W3"],
                       "backing_status": "no_source" if not ref else "source_unavailable"})
        return factor
    edge = next((edge for edge in governed.edges
                 if edge.src == ref and edge.dst == target_id and edge.kind == "SUPPORTS"), None)
    if edge is None:
        factor.update({"warrant": "W3", "tier": _TIER_NAME["W3"], "backing_status": "source_not_linked"})
        return factor
    if not _text_contains_value(source.text, factor["value"]):
        factor.update({"warrant": "W3", "tier": _TIER_NAME["W3"], "backing_status": "value_not_in_source"})
        return factor
    warrant = edge.warrant if edge.warrant in _TIER_NAME else "W3"
    factor.update({"warrant": warrant, "tier": _TIER_NAME[warrant], "backing_status": "matched"})
    return factor


def _derived_inputs(governed, target_id: str, raw: "dict | None") -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {name: _derived_factor(governed, target_id, raw.get(name))
            for name in ("reach", "impact", "effort")}


_DEFEATED_STATUS = {"REFUTED", "CONTRADICTED", "NONCONVERGENT"}  # kernel-grade defeats — never laundered to a score


def _confidence_from_profile(profile: "list[float]", status: "str | None" = None) -> "tuple[float, str | None]":
    """Confidence = the initiative's OVERALL strength (s3, all tiers counted), in [0,1]; the accompanying tier is
    the BEST (hardest-to-fake) tier at which it has any support — that is the quality of the confidence, and the
    governed value-add. 0.6 all-from-quotes and 0.6 with re-executable backing are the same number, very
    different bets. A kernel-grade DEFEAT (`status` REFUTED/CONTRADICTED/NONCONVERGENT) floors confidence to 0 —
    RICE must never launder a refutation into a positive score, exactly as the override lattice refuses to (Fable)."""
    if status in _DEFEATED_STATUS:
        return 0.0, None
    p = list(profile or [0.0, 0.0, 0.0, 0.0])
    conf = float(p[3]) if len(p) >= 4 else 0.0
    best = next((_PROFILE_TIER[i] for i in range(len(p)) if float(p[i]) > _EPS), None)
    return round(conf, 4), best


def _score_row(name: str, ident: str, profile: "list[float]", f: "dict", status: "str | None" = None) -> dict:
    """Score one initiative: Reach/Impact/Effort from `f` (each a factor with its own tier), Confidence READ
    from `profile` (the initiative's backing strength), floored to 0 on a kernel-grade defeat (`status`). Names
    the weakest-backed factor. The ONE scoring body, shared by the per-claim and portfolio entry points."""
    reach, impact, effort = _factor(f.get("reach")), _factor(f.get("impact")), _factor(f.get("effort"))
    conf, conf_tier = _confidence_from_profile(profile, status)
    score = (reach["value"] * impact["value"] * conf) / max(effort["value"], 0.01)
    score_low = (reach["low"] * impact["low"] * conf) / max(effort["high"], 0.01)
    score_high = (reach["high"] * impact["high"] * conf) / max(effort["low"], 0.01)
    # weakest LINK across all four factors by tier rank — confidence's rank is its best-supported tier.
    conf_warrant = next((w for w, n in _TIER_NAME.items() if n == conf_tier), "W3")
    legs = [("Reach", reach["warrant"]), ("Impact", impact["warrant"]),
            ("Confidence", conf_warrant), ("Effort", effort["warrant"])]
    weak_name, weak_warrant = min(legs, key=lambda kv: _TIER_RANK.get(kv[1], 0))
    return {"initiative": name, "id": ident, "reach": reach, "impact": impact, "effort": effort,
            "confidence": conf, "confidence_tier": conf_tier or "none", "score": round(score, 2),
            "score_low": round(score_low, 2), "score_high": round(score_high, 2),
            "weakest": {"factor": weak_name, "tier": _TIER_NAME.get(weak_warrant, "unchecked")}}


def _ranked(rows: "list[dict]") -> "list[dict]":
    from bisect import bisect_right

    rows.sort(key=lambda r: r["score"], reverse=True)
    lows = sorted(float(row["score_low"]) for row in rows)
    highs = sorted(float(row["score_high"]) for row in rows)
    total = len(rows)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
        guaranteed_ahead = total - bisect_right(lows, float(r["score_high"]))
        possibly_ahead = total - bisect_right(highs, float(r["score_low"]))
        if float(r["score_high"]) > float(r["score_low"]):
            possibly_ahead -= 1  # the row's own high endpoint is in the second count
        best, worst = 1 + guaranteed_ahead, 1 + max(0, possibly_ahead)
        r["rank_band"] = [best, worst]
        r["rank_stable"] = best == worst
    return rows


def rice_scores(governed, inputs: "dict") -> "list[dict]":
    """Single-decision RICE: rank the CLAIMS of ONE governed map, Confidence read from each claim's per-node
    strength, Reach/Impact/Effort from `inputs` ({claim_id: {reach|impact|effort: factor}}). (For a roadmap of
    separate decisions use `portfolio_rice`.)"""
    from ztare.scenarios.argument_kernel import claim_status
    from ztare.scenarios.strength import strength_profile

    per = strength_profile(governed).get("per_node") or {}
    inputs = inputs if isinstance(inputs, dict) else {}
    rows = [_score_row(c.text, c.id, per.get(c.id) or [0.0, 0.0, 0.0, 0.0],
                       _derived_inputs(governed, c.id, inputs.get(c.id, {})),
                       status=claim_status(governed, c.id))  # CONTRADICTED claim ⇒ confidence 0, not laundered
            for c in governed.of_kind("claim")]
    return _ranked(rows)


def portfolio_rice(items: "list[dict]", repo_root) -> "list[dict]":
    """Roadmap RICE: rank a PORTFOLIO of initiatives, each its OWN governed decision (project). Confidence per
    initiative is READ from that project's THESIS backing strength (a measured strength, not a typed guess) —
    so a well-evidenced bet outranks a hunch at the same Reach/Impact/Effort. `items` = [{project, label?,
    reach, impact, effort}]. A project with no governed map scores at confidence 0 (unchecked), never crashes."""
    from ztare.scenarios.adapters import governed_state_from_research_map
    from ztare.scenarios.strength import strength_profile

    rows: "list[dict]" = []
    for it in items or []:
        proj = str(it.get("project") or "")
        profile, status, governed, target_id = None, None, None, ""
        try:
            g = governed_state_from_research_map(proj, repo_root)
            if g.elements:
                governed = g
                targets = g.of_kind("thesis") or g.of_kind("claim")
                target_id = targets[0].id if targets else ""
                sp = strength_profile(g)
                profile, status = sp.get("profile"), sp.get("status")
        except Exception:  # noqa: BLE001 — a missing/unbuildable project scores as unchecked, never blocks the rest
            profile = None
        factors = _derived_inputs(governed, target_id, it) if governed and target_id else {
            name: _factor(it.get(name)) for name in ("reach", "impact", "effort")
        }
        row = _score_row(str(it.get("label") or proj), proj,
                         profile or [0.0, 0.0, 0.0, 0.0], factors, status=status)
        row["project"] = proj
        rows.append(row)
    return _ranked(rows)


def rice_inputs_path(project: str, repo_root):
    from pathlib import Path
    return Path(repo_root) / "projects" / project / "workspace" / "rice_inputs.json"


def load_rice_inputs(project: str, repo_root) -> dict:
    """The project's RICE factor inputs (data, part of the seed): {claim_id: {reach|impact|effort: {value,
    low/value/high, ref, unit}}}. Warrant is never loaded from this file; it is derived from the graph."""
    import json

    p = rice_inputs_path(project, repo_root)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


def save_rice_inputs(project: str, repo_root, claim_id: str, factors: dict) -> dict:
    """Validate and atomically persist one initiative's bounded factor estimates.

    Only values, ranges, units, and governed evidence refs are stored. Warrant fields are discarded because the
    scorer derives them from the current graph every time.
    """
    from ztare.scenarios.adapters import governed_state_from_research_map

    governed = governed_state_from_research_map(project, repo_root)
    claim = governed.by_id(claim_id)
    if claim is None or claim.kind != "claim":
        raise ValueError(f"{claim_id!r} is not a governed initiative claim")
    cleaned: dict[str, dict] = {}
    for name in ("reach", "impact", "effort"):
        raw = factors.get(name) if isinstance(factors, dict) else None
        raw = raw if isinstance(raw, dict) else {}
        value = _number(raw.get("value"))
        low = _number(raw.get("low"), value)
        high = _number(raw.get("high"), value)
        if min(low, value, high) < 0 or not low <= value <= high:
            raise ValueError(f"{name} must satisfy 0 <= low <= likely <= high")
        if name == "effort" and low <= 0:
            raise ValueError("effort low estimate must be greater than zero")
        ref = str(raw.get("ref") or "").strip()
        if ref:
            source = governed.by_id(ref)
            if source is None or source.kind != "evidence":
                raise ValueError(f"{name} source {ref!r} is not governed evidence")
        cleaned[name] = {"low": low, "value": value, "high": high, "ref": ref,
                         "unit": str(raw.get("unit") or "").strip()[:40]}

    current = load_rice_inputs(project, repo_root)
    current[claim_id] = cleaned
    path = rice_inputs_path(project, repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    staged = path.with_name(f".{path.name}.tmp")
    staged.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    staged.replace(path)
    return cleaned


def _selftest() -> int:
    from ztare.scenarios.governed_types import GovernedEdge, GovernedElement, GovernedState

    # two initiatives under a thesis: A backed by re-executable evidence, B backed only by a quote.
    els = [GovernedElement("thesis", "thesis", "prioritize the roadmap"),
           GovernedElement("A", "claim", "ship the recompute-backed bet"),
           GovernedElement("B", "claim", "ship the quote-backed bet"),
           GovernedElement("eA", "evidence", "Reach 5,000; impact 2; effort 2."),
           GovernedElement("eB", "evidence", "Reach 50,000; impact 3; effort 1.")]
    edges = [GovernedEdge("eA", "SUPPORTS", "A", "W1"), GovernedEdge("A", "SUPPORTS", "thesis", "W2"),
             GovernedEdge("eB", "SUPPORTS", "B", "W2"), GovernedEdge("B", "SUPPORTS", "thesis", "W2")]
    g = GovernedState(els, edges)

    inputs = {
        # A: modest reach, but every factor well-backed
        "A": {"reach": {"low": 4000, "value": 5000, "high": 6000, "ref": "eA"},
              "impact": {"low": 1.5, "value": 2, "high": 2.5, "ref": "eA"},
              "effort": {"low": 1.5, "value": 2, "high": 3, "ref": "eA"}},
        # B: the stored W0 is ignored; impact 4 does not appear in the cited source, so that factor stays W3.
        "B": {"reach": {"value": 50000, "ref": "eB"},
              "impact": {"value": 4, "ref": "eB", "warrant": "W0"},
              "effort": {"value": 1, "ref": "eB"}},
    }
    rows = rice_scores(g, inputs)
    by = {r["id"]: r for r in rows}
    # A has reproducible confidence; B's confidence is only cited
    assert by["A"]["confidence_tier"] == "reproducible", by["A"]
    assert by["B"]["confidence_tier"] == "cited", by["B"]
    # B's weakest link is an unchecked factor; A's weakest is at worst cited
    assert by["B"]["weakest"]["tier"] == "unchecked", by["B"]["weakest"]
    assert by["A"]["weakest"]["tier"] == "reproducible", by["A"]["weakest"]
    assert by["B"]["impact"]["backing_status"] == "value_not_in_source", by["B"]["impact"]
    assert by["A"]["score_low"] < by["A"]["score"] < by["A"]["score_high"], by["A"]
    # ranking is by score and stamped
    assert [r["id"] for r in rows] == sorted(by, key=lambda c: -by[c]["score"])
    assert rows[0]["rank"] == 1
    assert all(len(row["rank_band"]) == 2 for row in rows)
    # a claim with NO inputs scores 0 (unchecked-zero factors), never crashes
    empty = rice_scores(GovernedState([GovernedElement("c", "claim", "x")], []), {})
    assert empty[0]["score"] == 0.0 and empty[0]["confidence_tier"] == "none", empty

    # PORTFOLIO: each initiative is its own project; Confidence read from that project's thesis strength.
    # Hermetic — two tiny projects, one well-cited thesis, one bare (no map).
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "projects" / "well" / "workspace").mkdir(parents=True)
        (root / "projects" / "well" / "latest_probability_dag.json").write_text(
            '{"outcome":{"label":"well-backed initiative","probability":0.6},"nodes":[]}')
        (root / "projects" / "well" / "compiled_evidence_packet.json").write_text(
            '{"immutable_ground_truth":[{"statement":"a filed figure backs it","strength":"strong"}]}')
        (root / "projects" / "well" / "workspace" / "governed_overlay.json").write_text(
            '{"elements":[{"id":"ev.pm","kind":"evidence","text":"Reach 1000; impact 2; effort 1."}],'
            '"edges":[{"src":"ev.pm","kind":"SUPPORTS","dst":"thesis","warrant":"W2"}]}')
        items = [{"project": "well", "label": "Well-backed", "reach": {"value": 1000, "warrant": "W2"},
                  "impact": {"value": 2, "warrant": "W2"}, "effort": {"value": 1, "warrant": "W2"}},
                 {"project": "nope", "label": "No map yet", "reach": {"value": 9000, "warrant": "W3"},
                  "impact": {"value": 3, "warrant": "W3"}, "effort": {"value": 1, "warrant": "W3"}}]
        prows = portfolio_rice(items, root)
        pby = {r["project"]: r for r in prows}
        assert pby["well"]["confidence_tier"] == "cited", pby["well"]        # read from the real thesis strength
        assert pby["nope"]["confidence_tier"] == "none" and pby["nope"]["score"] == 0.0, pby["nope"]  # no map => 0
        assert prows[0]["project"] == "well", prows                          # the backed bet outranks the hunch

    print("GOVERNED-RICE SELFTEST PASSED",
          {"single": {r["id"]: (r["score"], r["confidence_tier"]) for r in rows},
           "portfolio": {r["project"]: (r["score"], r["confidence_tier"]) for r in prows}})
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
