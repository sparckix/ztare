"""surfaced_consumption_gate.py — RC3: force probe-SELECTION to consume
the apparatus surfacing, not anchored free-recall.

RCA (2026-05-17): the surfacing apparatus (void-audit, primitive_tick_
surface §9c, menu, structural-vocab) is all on the PRODUCE side; the
only consumption check (GAP-F) is advisory and inspects the F-row AFTER
the tick, not the SELECTION before it. So probe-selection stayed
anchored free-recall, the surfaced set sat unconsumed, every tick
recurred. Producing more surfacing cannot fix a consumption gap.

This gate moves the forcing to the SELECTION step: a tick's F-row MUST
carry `consumes_surfaced:<id>` and that <id> MUST validate against the
CURRENT surfaced set (the live void-audit min-vertex-cuts /
source-void-nodes). A probe not drawn from the surfaced set cannot
close its tick. Wired into the fail-closed owner-scoped `tick_close`
path (H5), so it is owner-scoped-HARD by construction.

Degrade-safe: if no void-audit artifact exists (genuine first run /
harness error) the gate is advisory (never false-block) — but a
present-but-unmatched claim is a HARD violation (that is the gloss the
gate exists to stop). Substring/normalized match against the surfaced
node ids (the audit emits long snake_case ids; the F-row may cite a
prefix/sub-id).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
# void-audit emits this (verified from ns_residual_void_audit.py output:
# "out_json": "projects/ns_millennium_hunt/workspace/queries/ns_trackb_residual_void_audit.json")
VOID_AUDIT_JSON = REPO / "projects/ns_millennium_hunt/workspace/queries/ns_trackb_residual_void_audit.json"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def surfaced_set() -> tuple[list[str], str]:
    """(ids, source). The live surfaced set = the void-audit
    min-vertex-cuts ∪ source-void-nodes. Empty list ⇒ no artifact."""
    if not VOID_AUDIT_JSON.is_file():
        return [], "no void-audit artifact (advisory — run ns_residual_void_audit.py)"
    try:
        j = json.loads(VOID_AUDIT_JSON.read_text(encoding="utf-8", errors="ignore"))
    except Exception as e:
        return [], f"void-audit unreadable ({e}) — advisory"
    ids: list[str] = []
    for cut in (j.get("min_vertex_cuts") or []):
        if isinstance(cut, list):
            ids += [str(x) for x in cut]
        elif isinstance(cut, str):
            ids.append(cut)
    ids += [str(x) for x in (j.get("source_void_nodes") or [])]
    return [i for i in ids if i], f"void-audit ({VOID_AUDIT_JSON.name})"


def _is_ns_tick(substrate_hint: str | None) -> bool:
    """The void-audit surfaced set is NS-Track-B-specific. H5 may only
    HARD-enforce on an NS/Track-B tick (review must-fix: scope guard —
    a generic non-NS tick has no business consuming a Track-B cut and
    must NOT be HARD-refused / incentivized to fake an NS id)."""
    # PRECISE token match (self-caught regression: bare `"ns" in s`
    # false-trips on "nonNS"/"answers"/etc — the very false-refuse-non-NS
    # the review flagged. NS tick-row ids are `F-NS-...`; otherwise
    # require a distinct NS token.)
    s = (substrate_hint or "").lower()
    if re.search(r"\bf-ns-", s) or re.search(r"(^|[^a-z])ns($|[^a-z])", s):
        return True
    # Review must-fix (#27 spoof): id-only detection is spoofable
    # (mislabel the F-row id non-NS). When the hint is the H3a-anchored
    # F-ROW BODY (passed by tick_close), an NS tick's findings text
    # inevitably contains NS science markers — far harder to spoof than
    # the id (you'd have to falsify the audit record). Conservative:
    # any of these ⇒ NS (fail toward requiring the surfaced-id bind).
    # Re-review must-fix: STRONG = NS-specific, low-false-positive
    # (standalone-trigger). The bare high-frequency words
    # (clay/vortex/vorticity/leray/millennium/route1/enstrophy) were
    # dropped as standalone triggers — they false-refused legitimate
    # non-NS ticks that mention them in passing (the exact must-fix-2
    # hazard). Residual: an NS body avoiding ALL strong markers stays
    # advisory here, but the close-gate H5b backstop (contract must
    # carry the gate-validated consumes_surfaced) still catches it.
    STRONG_NS = (
        "trackb", "track-b", "navier", "ns_residual", "ns residual",
        "caffarelli", "de giorgi", "degiorgi", "ns-clay", "ns_clay",
        "ns millennium", "ns_millennium",
    )
    if any(m in s for m in STRONG_NS):
        return True
    # C3/C5/C7 as delimited tokens (NS-node names, low false-positive)
    return bool(re.search(r"(^|[^a-z0-9])c[357]($|[^a-z0-9])", s))


def consumed_id_is_surfaced(claimed_id: str | None,
                            substrate_hint: str | None = None
                            ) -> tuple[bool, str]:
    """(ok, reason). Review must-fixes applied:
    (1) FULL-ID EXACT normalized match only (no substring — the prior
        `n in ni` let `consumes_surfaced:source` pass by one word; the
        agent must cite the FULL surfaced id);
    (2) NS-SUBSTRATE GUARD — only HARD-enforce on an NS/Track-B tick;
        non-NS ⇒ advisory (no false-refuse, no incentive to fake);
    (3) NS-TICK + NO-ARTIFACT ⇒ HARD (run the void-audit first) so
        deleting/renaming the json does NOT silently bypass for the
        ticks it governs; non-NS + no-artifact ⇒ advisory."""
    ns = _is_ns_tick(substrate_hint)
    ids, src = surfaced_set()
    if not ids:
        if ns:
            return False, (f"surfaced_consumption_gate: NS/Track-B tick "
                           f"but {src} — RUN ns_residual_void_audit.py "
                           f"first; no-artifact does NOT bypass H5 for "
                           f"the ticks it governs (review must-fix #3).")
        return True, (f"surfaced_consumption_gate: non-NS tick + {src} "
                      f"⇒ ADVISORY (the surfaced set is NS-Track-B "
                      f"specific; nothing to enforce here).")
    if not ns:
        return True, (f"surfaced_consumption_gate: non-NS/Track-B tick "
                      f"⇒ ADVISORY (the void-audit surfaced set is "
                      f"NS-specific; H5 scope-guarded — no false-refuse "
                      f"of a legitimate non-NS tick).")
    if not claimed_id:
        return False, (f"surfaced_consumption_gate: live NS surfaced set "
                       f"({src}, {len(ids)} ids) but the tick declares "
                       f"NO `consumes_surfaced:<id>` — probe selection "
                       f"MUST consume a surfaced item. Cite the FULL id "
                       f"of one of: {[i for i in ids[:6]]}")
    n = _norm(claimed_id)
    surfaced_norm = {_norm(i): i for i in ids}
    if n in surfaced_norm:
        return True, (f"surfaced_consumption_gate: '{claimed_id}' is an "
                      f"EXACT match of surfaced id "
                      f"'{surfaced_norm[n]}' ({src}) — probe is "
                      f"surfacing-driven.")
    return False, (f"surfaced_consumption_gate: '{claimed_id}' is NOT a "
                   f"FULL-ID match of any live surfaced id ({src}); a "
                   f"token/substring is NOT sufficient (review must-fix "
                   f"#1 — kills the one-word gloss). Cite the FULL id of "
                   f"one of: {[i for i in ids[:8]]}")


def main() -> int:
    import sys
    claimed = sys.argv[1] if len(sys.argv) > 1 else None
    hint = sys.argv[2] if len(sys.argv) > 2 else None
    ok, why = consumed_id_is_surfaced(claimed, hint)
    print(("OK: " if ok else "REFUSE: ") + why)
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
