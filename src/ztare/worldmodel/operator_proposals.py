"""Automated operator-proposal channel for the grid world-model catalog (GP-250).

This shifts GRAMMAR EXPANSION from the human conductor to the system. When the
abduced champion leaves a residual the current operator catalog cannot explain,
``propose_operators`` triages that residual DETERMINISTICALLY: it clusters the
mismatched transitions by diff signature and, per cluster, proves (one line per
allowed op family) why no existing op fits, then sketches a candidate operator
and states the acceptance test that would falsify it.

It is the worldmodel INSTANCE of the kernel operator-proposal contract
(``ztare.common.operator_proposal_contract``) — the same card shape the fit,
leanmill, and deai substrates reuse. This module supplies only the three
substrate plug-ins: the grid residual clusterer, the per-op-family failure
checks, and the planted-synthetic acceptance recipe.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from ztare.common.operator_proposal_contract import (
    OperatorProposalSubstrate,
    operator_proposal_card,
    write_proposal_cards,
)

SCHEMA = "worldmodel-operator-proposal-v1"

# The allowed operator families this residual is measured AGAINST. Kept local
# (not imported from the concurrently-edited spec_catalog) so an API shift there
# cannot break residual triage; the names are the stable catalog v1 vocabulary.
_ALLOWED_OP_FAMILIES = (
    "translate_block", "recolor_map", "consume_extremal", "region_event", "identity",
)

ACCEPTANCE_TEST = (
    "planted synthetic log where ONLY the proposed operator explains all "
    "transitions; recovery via abduce_spec; strict transition-level improvement "
    "on the real log (mismatch count must drop when the operator is added)."
)


# ── diff geometry (local; no dependency on the sibling-edited modules) ───────

def _diff(s, s_next):
    return [(y, x, s[y][x], s_next[y][x])
            for y in range(len(s)) for x in range(len(s[0]))
            if s[y][x] != s_next[y][x]]


def _bbox(cells):
    ys = [y for y, x in cells]
    xs = [x for y, x in cells]
    return (min(ys), min(xs), max(ys), max(xs))


def _rigid_offset(diff):
    """The single uniform non-zero (dy, dx) if the diff is a color-preserving
    rigid translation, else None (with the reason readable from the caller)."""
    lost, gained = defaultdict(list), defaultdict(list)
    for (y, x, a, b) in diff:
        lost[a].append((y, x))
        gained[b].append((y, x))
    offsets = set()
    for c, src in lost.items():
        dst = gained.get(c)
        if not dst or len(dst) != len(src):
            return None
        for s0, d in zip(sorted(src), sorted(dst)):
            offsets.add((d[0] - s0[0], d[1] - s0[1]))
    if len(offsets) == 1:
        off = next(iter(offsets))
        return off if off != (0, 0) else None
    return None


def _translate_param_fit(diff):
    """Translate-family parameter fit for residual triage. Unlike the cluster
    classifier, this ignores the background fill swap and asks whether any
    moved non-background color has one uniform displacement."""
    lost, gained = defaultdict(list), defaultdict(list)
    for (y, x, a, b) in diff:
        lost[a].append((y, x))
        gained[b].append((y, x))
    offsets = set()
    for c, src in lost.items():
        if c == 0:
            continue
        dst = gained.get(c)
        if not dst or len(dst) != len(src):
            continue
        offsets |= {(d[0] - s0[0], d[1] - s0[1])
                    for s0, d in zip(sorted(src), sorted(dst))}
    if len(offsets) == 1:
        off = next(iter(offsets))
        return off if off != (0, 0) else None
    return None


def _functional_map(diff):
    m = {}
    for (_, _, a, b) in diff:
        if a in m and m[a] != b:
            return None
        m[a] = b
    return m


def _classify_motion(diff):
    """rigid | permutation | rewrite | count | other — the cluster axis."""
    if not diff:
        return "identity"
    if _rigid_offset(diff) is not None:
        return "rigid"
    old = Counter(a for (_, _, a, _) in diff)
    new = Counter(b for (_, _, _, b) in diff)
    if old == new:
        return "permutation"          # colors conserved, positions rearranged
    if _functional_map(diff) is not None:
        return "rewrite"
    pairs = {(a, b) for (_, _, a, b) in diff}
    rows = {y for (y, _, _, _) in diff}
    if len(pairs) == 1 and len(rows) == len(diff):
        return "count"
    return "other"


# ── per-op-family failure checks (one deterministic line each) ───────────────

def _translate_reason(diff):
    off = _rigid_offset(diff)
    if off is not None:
        return f"fits as rigid translate {off} (left residual by the assembler)"
    lost, gained = defaultdict(list), defaultdict(list)
    for (y, x, a, b) in diff:
        lost[a].append((y, x))
        gained[b].append((y, x))
    for c, src in lost.items():
        if len(gained.get(c, [])) != len(src):
            return "not rigid: cells gained != cells lost per color"
    return "not rigid: non-uniform displacement (offsets vary by color)"


def _recolor_reason(s, s_next, diff):
    m = _functional_map(diff)
    if m is None:
        return "not a recolor: a source color maps to multiple targets (non-functional)"
    for y in range(len(s)):
        for x in range(len(s[0])):
            src = s[y][x]
            if src in m and s_next[y][x] != m[src]:
                return f"not a global recolor: color {src} present outside the rewrite region"
            if src not in m and s_next[y][x] != src:
                return "not a recolor: a cell changed with no color-map entry"
    return "fits as a global recolor (left residual by the assembler)"


def _consume_reason(s, diff):
    pairs = {(a, b) for (_, _, a, b) in diff}
    if len(pairs) != 1:
        return "not consume_extremal: more than one (color -> replacement) flip"
    by_row = defaultdict(list)
    for (y, x, _, _) in diff:
        by_row[y].append(x)
    if any(len(xs) != 1 for xs in by_row.values()):
        return "not consume_extremal: more than one changed cell per row"
    (a, _b), = pairs
    for y, xs in by_row.items():
        idxs = [x for x in range(len(s[0])) if s[y][x] == a]
        if not idxs or xs[0] not in (min(idxs), max(idxs)):
            return "not consume_extremal: changed cell is not the row's extremal-index color"
    return "fits as consume_extremal (left residual by the assembler)"


def _consume_param_fit(s, diff):
    """General consume geometry with an arbitrary count. This is the triage
    check for "same family, wrong count" before proposing a new operator."""
    pairs = {(a, b) for (_, _, a, b) in diff}
    if len(pairs) != 1:
        return None
    by_row = defaultdict(list)
    for (y, x, _, _) in diff:
        by_row[y].append(x)
    if not by_row:
        return None
    (a, _b), = pairs
    counts = {len(xs) for xs in by_row.values()}
    if len(counts) != 1:
        return None
    n = next(iter(counts))
    for extreme in ("min", "max"):
        ok = True
        for y, xs in by_row.items():
            idxs = sorted(x for x in range(len(s[0])) if s[y][x] == a)
            expected = idxs[:n] if extreme == "min" else idxs[-n:]
            if sorted(xs) != expected:
                ok = False
                break
        if ok:
            return {"family": "consume_extremal", "suspect_parameter": "count",
                    "observed_value": n, "extreme": extreme}
    return None


def _parameter_generalization(cluster):
    trs = cluster["transitions"]
    if not trs:
        return None
    hits: "dict[tuple, list[dict]]" = defaultdict(list)
    for tr in trs:
        d = _diff(tr.s, tr.s_next)
        off = _translate_param_fit(d)
        if off is not None:
            hits[("translate_block", "dy_dx")].append(
                {"family": "translate_block", "suspect_parameter": "dy_dx",
                 "observed_value": [int(off[0]), int(off[1])]})
        cf = _consume_param_fit(tr.s, d)
        if cf is not None:
            hits[(cf["family"], cf["suspect_parameter"])].append(cf)
    need = max(1, int(0.9 * len(trs) + 0.999999))
    best_key, best_rows = None, []
    for key, rows in hits.items():
        if len(rows) >= need and len(rows) > len(best_rows):
            best_key, best_rows = key, rows
    if best_key is None:
        return None
    vals = Counter(str(r.get("observed_value")) for r in best_rows)
    family, param = best_key
    return {"family": family, "suspect_parameter": param,
            "coverage": len(best_rows), "total": len(trs),
            "modal_observed_value": vals.most_common(1)[0][0]}


def _region_event_reason(trs):
    """region_event paints a FIXED learned cell-set on a crossing. If the write
    (changed cells -> new colors) varies across the cluster, no fixed write fits."""
    writes = {frozenset((y, x, b) for (y, x, a, b) in _diff(tr.s, tr.s_next)) for tr in trs}
    if len(writes) <= 1:
        return "a fixed region_event write MIGHT fit (left residual by the assembler)"
    return "not region_event: write-set varies across the cluster (no fixed learned cell-set)"


# ── proposed-operator sketch (heuristic — the only non-computed field) ───────

def _sketch(motion, colors, fp):
    cs = sorted(colors)
    if motion == "permutation":
        return (f"rotate_block(colors={cs}, pivot~{fp['center']}) — diff is a "
                "permutation of a color-set within a fixed bbox (rigid rotation/reflection)")
    if motion == "rewrite":
        return (f"local_recolor(region={fp['bbox']}, mapping over {cs}) — a color "
                "rewrite confined to a region, not global")
    if motion == "count":
        return (f"count_transform(colors={cs}) — count-like flip not matching the "
                "per-row/col extremal-consume shape")
    if motion == "rigid":
        return (f"translate_multiblock(colors={cs}, offset~{fp['bbox']}) — rigid "
                "motion the single-component translate could not assemble")
    return (f"region_rewrite(region={fp['bbox']}, colors={cs}) — a local structured "
            "rewrite outside the current catalog")


def _footprint(trs):
    cells = [(y, x) for tr in trs for (y, x, a, b) in _diff(tr.s, tr.s_next)]
    y0, x0, y1, x1 = _bbox(cells)
    sizes = sorted(len(_diff(tr.s, tr.s_next)) for tr in trs)
    return {"bbox": [y0, x0, y1, x1], "height": y1 - y0 + 1, "width": x1 - x0 + 1,
            "center": [(y0 + y1) / 2, (x0 + x1) / 2],
            "median_cells_changed": sizes[len(sizes) // 2], "n_transitions": len(trs)}


# ── the substrate plug-in (kernel OperatorProposalSubstrate seam) ────────────

class WorldmodelOperatorProposals:
    """Grid-catalog instance of the kernel operator-proposal contract."""

    schema = SCHEMA

    def cluster_residual(self, log, spec, residual_indices) -> list[dict]:
        rows = list(log)
        if residual_indices is None:
            residual_indices = _infer_mismatches(rows, spec)
        clusters: "dict[tuple, list[int]]" = defaultdict(list)
        for i in residual_indices:
            if i < 0 or i >= len(rows):
                continue
            tr = rows[i]
            d = _diff(tr.s, tr.s_next)
            if not d:
                continue
            cells = [(y, x) for (y, x, a, b) in d]
            y0, x0, y1, x1 = _bbox(cells)
            colors = frozenset(c for (_, _, a, b) in d for c in (a, b))
            sig = (tr.a, _classify_motion(d), (y1 - y0 + 1, x1 - x0 + 1), colors)
            clusters[sig].append(i)
        return [{"signature": sig, "indices": idxs, "transitions": [rows[i] for i in idxs]}
                for sig, idxs in clusters.items()]

    def family_failures(self, cluster) -> dict:
        trs = cluster["transitions"]
        rep = trs[0]
        d = _diff(rep.s, rep.s_next)
        return {
            "translate_block": _translate_reason(d),
            "recolor_map": _recolor_reason(rep.s, rep.s_next, d),
            "consume_extremal": _consume_reason(rep.s, d),
            "region_event": _region_event_reason(trs),
            "identity": "state changed (diff non-empty)" if d else "fits as identity",
        }

    def acceptance_test(self, cluster) -> str:
        return ACCEPTANCE_TEST

    def card_for(self, cluster) -> dict:
        action, motion, (h, w), colors = cluster["signature"]
        fp = _footprint(cluster["transitions"])
        pg = _parameter_generalization(cluster)
        if pg is not None:
            fam = (f"parameter_generalization|action={action}|family={pg['family']}|"
                   f"param={pg['suspect_parameter']}|bbox={h}x{w}|colors={sorted(colors)}")
            card = operator_proposal_card(
                schema=self.schema,
                failure_family=fam,
                evidence_indices=cluster["indices"],
                spatial_footprint=fp,
                why_existing_ops_fail=self.family_failures(cluster),
                proposed_operator_sketch=(
                    f"parameter_generalization({pg['family']}, "
                    f"{pg['suspect_parameter']}~{pg['modal_observed_value']})"),
                acceptance_test=self.acceptance_test(cluster),
            )
            card["kind"] = "parameter_generalization"
            card["parameter_generalization"] = pg
            return card
        fam = f"action={action}|motion={motion}|bbox={h}x{w}|colors={sorted(colors)}"
        card = operator_proposal_card(
            schema=self.schema,
            failure_family=fam,
            evidence_indices=cluster["indices"],
            spatial_footprint=fp,
            why_existing_ops_fail=self.family_failures(cluster),
            proposed_operator_sketch=_sketch(motion, colors, fp),
            acceptance_test=self.acceptance_test(cluster),
        )
        card["kind"] = "novel_operator"
        return card


# runtime plug-in registration for the contract Protocol (documents the seam)
assert isinstance(WorldmodelOperatorProposals(), OperatorProposalSubstrate)

_SUBSTRATE = WorldmodelOperatorProposals()


# ── public API (BUILD 1) ─────────────────────────────────────────────────────

def propose_operators(log, spec=None, mismatch_indices=None) -> list[dict]:
    """Deterministic residual triage -> one proposal card per residual cluster.

    ``mismatch_indices`` are the transitions the champion mispredicts; if None,
    they are inferred by lowering ``spec`` (defensively) or treated as the whole
    log."""
    return [_SUBSTRATE.card_for(c)
            for c in _SUBSTRATE.cluster_residual(log, spec, mismatch_indices)]


def write_proposals(project, cards) -> list[dict]:
    """Persist proposal cards to ``<project>/workspace/operator_proposals.jsonl``,
    dedup by failure_family sha. Returns the rows actually written (empty on a
    fully-duplicate batch)."""
    path = Path(project) / "workspace" / "operator_proposals.jsonl"
    return write_proposal_cards(path, cards)


# ── defensive mismatch inference (tolerates the sibling's shifting APIs) ──────

def _infer_mismatches(rows, spec) -> list[int]:
    step = _step_from_spec(spec)
    if step is None:
        return list(range(len(rows)))
    out = []
    for i, tr in enumerate(rows):
        try:
            pred = step(tr.s, tr.a, tr.t)
        except Exception:  # noqa: BLE001
            pred = None
        if pred != tr.s_next:
            out.append(i)
    return out


def _step_from_spec(spec):
    if spec is None:
        return None
    if callable(spec):
        return spec
    step_fn = getattr(spec, "step_fn", None)
    if callable(step_fn):
        return step_fn
    if isinstance(spec, dict) and spec.get("actions"):
        try:
            from ztare.worldmodel.spec_catalog import lower_spec
            step, _err = lower_spec(spec)
            return step
        except Exception:  # noqa: BLE001 — catalog API in flux; fall back
            return None
    return None
