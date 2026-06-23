"""commit_membrane_gate.py — GP-241 terminating enforcer (PAYLOAD).

STATUS: SPEC v3 payload. Design converged via GP-129 Panel Rounds 1-3
(adversarial design-review discipline satisfied). NOT yet trusted: gated
by the corrected turn-level 3-pronged replay test (GP-241). The harness
hook that INVOKES this is an operator-confirmed environment change
(global blast radius) — this module is the payload, not the wiring.

WHY THIS EXISTS (Panel Round 3 fixed point): every prior "forcing" was
agent-self-administered (printed gates, mandate rules, read-side honor
system, session-close samplers) ⇒ infinite regress ⇒ glossable by the
corrupt-but-authorized driver. A regress terminates only at an enforcer
OUTSIDE the set of entities that can bypass it. In an agent runtime that is a
HARNESS-OWNED HOOK (Stop / PostToolUse / UserPromptSubmit): the runtime
runs it, the agent cannot emit-around it. This module is what that hook
runs. The agent calling it itself is NOT the enforcement path — the hook
calling it is.

"OFFICIAL" ≡ hook-stamped by this gate. Unstamped state (prose terminus,
hand-written F-row, raw transitions/git write, edited artifact) is
non-authoritative by construction; downstream readers trust ONLY the
stamp this gate emits (the stamp is applied here, by one terminating
enforcer — NOT by N cooperating readers, which was the Round-2 regress).

GATE-DAG = Default-FAIL on the three catalogs (operator's three-layer
directive — this is what makes the shipped cage serve the research
goal). A research-state transition cannot be stamped official unless it
declares, machine-checkably, one item from EACH layer:
  L1 research process  — org/patterns/*.md + org/menu/orchestration_menu.yaml
  L2 math content      — structural_language_catalog_20260514.json
  L3 failure modes     — org/anti-patterns/*.md  + relapse-fingerprint
Every criterion starts FALSE; evidence opens it (proven Default-FAIL
contract pattern, same as tick_close H1-H6).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from ztare.common.paths import REPO_ROOT

PATTERNS_DIR = REPO_ROOT / "org" / "patterns"
ANTIPATTERNS_DIR = REPO_ROOT / "org" / "anti-patterns"
ORCH_MENU = REPO_ROOT / "org" / "menu" / "orchestration_menu.yaml"
STRUCT_ANCHORS_REGISTRY = REPO_ROOT / "org" / "structural_anchors" / "registry.yaml"
# Canonical TRACKED home (per export_structural_language_catalog.py: the
# workingpapers/ dated path is gitignored/ephemeral = dead-path fragility).
STRUCT_CATALOG = REPO_ROOT / "docs" / "reference" / "structural_language_catalog.json"


def _slugs_md(d: Path) -> set[str]:
    if not d.is_dir():
        return set()
    # _norm both sides (bug found by the GP-241 replay test: raw
    # underscored stems never matched space-normalized declarations).
    return {_norm(p.stem) for p in d.glob("*.md") if p.stem != "INDEX"}


def _catalog_terms() -> set[str]:
    """Named structural-language moves (L2). Free-form JSON — collect
    string leaves under obvious name keys; tolerant by design."""
    if not STRUCT_CATALOG.is_file():
        return set()
    try:
        j = json.loads(STRUCT_CATALOG.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return set()
    out: set[str] = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and k.lower() in (
                        "name", "id", "move", "pattern", "label", "key"):
                    out.add(_norm(v))
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(j)
    return {t for t in out if t}


def _orch_menu_keys() -> set[str]:
    if not ORCH_MENU.is_file():
        return set()
    txt = ORCH_MENU.read_text(encoding="utf-8", errors="ignore")
    # leaf/sub_class/menu keys are yaml mapping keys; tolerant scan.
    return {_norm(m.group(1))
            for m in re.finditer(r"^\s*([a-z0-9_\-]{4,}):", txt, re.M)}


def _registry() -> dict:
    if not STRUCT_ANCHORS_REGISTRY.is_file():
        return {}
    try:
        import yaml
        return yaml.safe_load(
            STRUCT_ANCHORS_REGISTRY.read_text(
                encoding="utf-8", errors="ignore"
            )
        ) or {}
    except Exception:
        return {}


def _relapse_source_paths(substrate: str | None = None) -> list[Path]:
    """Configured relapse-fingerprint sources for the active substrate.

    The membrane gate is generic; substrate memory files are declared in
    `org/structural_anchors/registry.yaml` and copied into the root-owned
    gate tree by deploy/configured_gate_sources.py.
    """
    reg = _registry()
    selected: Iterable[tuple[str, object]]
    if substrate:
        selected = [(substrate, reg.get(substrate))]
    else:
        selected = ((k, v) for k, v in reg.items() if k != "schema_version")
    out: list[Path] = []
    for _name, cfg in selected:
        if not isinstance(cfg, dict):
            continue
        gate_sources = cfg.get("gate_guard_sources") or {}
        raw_sources: list[object] = []
        if isinstance(gate_sources, dict):
            raw = gate_sources.get("relapse_fingerprint") or []
            raw_sources.extend(raw if isinstance(raw, list) else [raw])
        raw = cfg.get("relapse_guard_sources") or []
        raw_sources.extend(raw if isinstance(raw, list) else [raw])
        for raw_path in raw_sources:
            rel = Path(str(raw_path or "").strip())
            if not str(rel) or rel.is_absolute() or ".." in rel.parts:
                continue
            if not rel.as_posix().startswith("projects/"):
                continue
            out.append(REPO_ROOT / rel)
    return sorted(set(out))


def _prior_alias_fingerprints(substrate: str | None = None) -> list[str]:
    """Normalized atom-fingerprints already in the recurrence ledger.
    A new transition whose fingerprint matches one of these is a
    relapse (the tick638 alias #22 / tick639 tautology failure)."""
    chunks: list[str] = []
    for path in _relapse_source_paths(substrate):
        if path.is_file():
            chunks.append(path.read_text(
                encoding="utf-8", errors="ignore"
            ).lower())
    if not chunks:
        return []
    txt = "\n".join(chunks)
    fps: list[str] = []
    for m in re.finditer(r"alias\s*#?\d+|c[357]\b|strict[- ]?margin|"
                          r"perennial|recurrence", txt):
        fps.append(m.group(0).strip())
    return sorted(set(fps))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


@dataclass
class MembraneVerdict:
    official: bool
    stamp: str | None
    failed: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_json(self) -> str:
        return json.dumps({
            "official": self.official, "stamp": self.stamp,
            "failed": self.failed, "notes": self.notes,
        }, indent=2)


_CORPUS_DIRS = (PATTERNS_DIR, ANTIPATTERNS_DIR,
                REPO_ROOT / "org" / "menu")
_CORPUS_CACHE: list[str] | None = None


def _corpus_docs() -> list[str]:
    """Normalized contents of the checked corpus (patterns +
    anti-patterns + menu). A witness equal-to / substring-of any of
    these is copied doctrine, not proposal-specific evidence (cold
    blocker #4). Bounded + cached: small corpus, deterministic."""
    global _CORPUS_CACHE
    if _CORPUS_CACHE is not None:
        return _CORPUS_CACHE
    docs: list[str] = []
    for d in _CORPUS_DIRS:
        try:
            for f in sorted(d.rglob("*")):
                if f.is_file() and f.suffix in (".md", ".yaml", ".yml"):
                    n = _norm(f.read_text(encoding="utf-8",
                                          errors="ignore"))
                    if len(n) >= 60:
                        docs.append(n)
        except Exception:
            continue
    # cold re-review blocker #2: STRUCT_CATALOG (the L2 structural-
    # language catalog) is ALSO checked doctrine — omitting it let an
    # l2_witness copied from structural_language_catalog.json pass.
    try:
        n = _norm(STRUCT_CATALOG.read_text(encoding="utf-8",
                                           errors="ignore"))
        if len(n) >= 60:
            docs.append(n)
    except Exception:
        pass
    _CORPUS_CACHE = docs
    return docs


_TYPED_CLOSURE = {"closure", "tick_close", "forecast_resolution"}


def evaluate(transition_text: str,
             declared: dict | None = None,
             proposal_id: str | None = None,
             transition_type: str | None = None,
             substrate: str | None = None) -> MembraneVerdict:
    """The terminating gate. `transition_text` = the emitted turn /
    research-state transition (closure, F-row, terminus, contract).
    `declared` = machine-checkable declarations the tick must carry:
      {l1_pattern, l2_move, l3_antipattern, consumes_surfaced, ...}.
    `proposal_id` binds witnesses to THIS proposal (cold blocker #4).
    Default-FAIL: official only if EVERY criterion opens.
    """
    declared = declared or {}
    substrate = (substrate or declared.get("substrate")
                 or declared.get("substrate_slug") or "")
    t = _norm(transition_text)
    failed: list[str] = []
    notes: list[str] = []

    def _witness_ok(key: str) -> bool:
        """Cold blocker #4 STRUCTURAL FIX. The prior check (path exists
        + non-empty) was a semantic bypass: an arbitrary note was
        dressed by pointing l1/l2/l3 witnesses at EXISTING CATALOG
        FILES. Fix, in order:
          1. the witness is INLINE CONTENT carried in THIS proposal,
             never a filesystem path — so it is intrinsically
             proposal-specific and works cross-host (a VPS daemon
             cannot stat a laptop path). Path-like ⇒ reject.
          2. non-trivial length (not a checkbox token).
          3. it must NOT be copied catalog/anti-pattern DOCTRINE
             (bounded exact/substring check over the small corpus) —
             that is the "dress it with the catalog" move itself.
        The daemon additionally sha256-binds the witness + proposal_id
        into the stamped row (tamper-evident provenance)."""
        w = declared.get(key)
        if not w or not isinstance(w, str):
            return False
        w = w.strip()
        if len(w) < 60:
            return False
        if w.startswith("/") or w.startswith("./") or "\n" not in w and (
                "/" in w and w.endswith(
                    (".md", ".json", ".txt", ".jsonl", ".py", ".yaml"))):
            return False  # a path, not inline evidence ⇒ reject
        wn = _norm(w)
        for doc in _corpus_docs():
            if wn in doc or doc in wn:
                return False  # copied catalog/anti-pattern doctrine
        return True

    # L1 — a real research-process pattern consumed + witness artifact.
    l1 = _norm(declared.get("l1_pattern", ""))
    pat = _slugs_md(PATTERNS_DIR) | _orch_menu_keys()
    if not (l1 and any(l1 == p or l1 in p or p in l1 for p in pat)):
        failed.append("L1 research-process pattern (org/patterns + "
                       "orchestration_menu) not declared/consumed")
    elif not _witness_ok("l1_witness"):
        failed.append("L1 names a pattern but has NO witness artifact "
                       "(l1_witness path missing/empty) — semantic-"
                       "checkbox bypass; name what was consumed + where")

    # L2 — a named structural-language move + witness artifact.
    l2 = _norm(declared.get("l2_move", ""))
    cat = _catalog_terms()
    if not (l2 and any(
            l2 == c
            or (len(l2) >= 5 and l2 in c)
            or (len(c) >= 5 and c in l2)
            for c in cat)):
        failed.append("L2 structural-language move "
                       "(structural_language_catalog) not declared")
    elif not _witness_ok("l2_witness"):
        failed.append("L2 names a move but has NO witness artifact "
                       "(l2_witness: the generated object/probe) — "
                       "semantic-checkbox bypass")

    # L3 — an anti-pattern checked + witness (the check's verifier log).
    l3 = _norm(declared.get("l3_antipattern", ""))
    anti = _slugs_md(ANTIPATTERNS_DIR)
    if not (l3 and any(l3 == a or l3 in a or a in l3 for a in anti)):
        failed.append("L3 anti-pattern (org/anti-patterns) not declared/"
                       "checked")
    elif not _witness_ok("l3_witness"):
        failed.append("L3 names an anti-pattern but has NO witness "
                       "artifact (l3_witness: the check/verifier log) — "
                       "semantic-checkbox bypass")

    # L3b — relapse fingerprint: a transition that just re-asserts a
    # prior-alias atom under new vocabulary is a relapse (tick638/639).
    fps = _prior_alias_fingerprints(str(substrate or ""))
    hit = [f for f in fps if f in t]
    # cold re-review blocker #3: the relapse data source (residual
    # manifest) is excluded from the VPS gate deploy ⇒ on the VPS the
    # detector silently no-ops (deployed FAIL-OPEN). The deploy now
    # ships the manifest into the gate tree; additionally, if it is
    # MISSING the gate must FAIL-CLOSED for terminus/closure (a guard
    # whose data is absent must block, not silently pass). The
    # is_terminus computation below is also needed for this check.
    TERM = ("terminus", "exhausted", "no pivot", "stop ticking",
            "dead end", "settled", "impossible", "no further",
            "channel exhausted")
    # Negation-aware (dogfood bug 2026-05-17: "NOT a terminus claim"
    # tripped the naive substring match). A terminus word that is
    # explicitly negated nearby is NOT a terminus assertion.
    is_terminus = False
    for k in TERM:
        i = t.find(k)
        if i < 0:
            continue
        window = t[max(0, i - 24):i]
        if not any(neg in window for neg in ("not ", "no ", "never ",
                                             "isnt ", "is not ")):
            is_terminus = True
            break
    # An explicit HONEST-CONCESSION / kill-record is the disciplined
    # output (conceding an adversary kill). The membrane exists to
    # ENFORCE honest concession, NEVER to punish it — blocking it would
    # invert the incentive (train the agent to stop recording kills).
    concession = any(m in t for m in (
        "resolved false", "success false", "success=false", "conceded",
        "adversary killed", "adversary-killed", "honest negative",
        "not laundered", "kill recorded", "md-survived as honest"))
    _typed_closure = (transition_type or "").strip().lower() \
        in _TYPED_CLOSURE
    _configured_relapse_sources = _relapse_source_paths(str(substrate or ""))
    _relapse_data_missing = bool(_configured_relapse_sources) and not any(
        p.is_file() for p in _configured_relapse_sources
    )
    if _relapse_data_missing \
            and (is_terminus or _typed_closure) and not concession:
        failed.append(
            "RELAPSE-GUARD DATA MISSING: the prior-alias residual "
            f"source(s) configured for substrate {substrate!r} are "
            "absent on this deployment, so non-relapse of a terminus/"
            "closure cannot be verified — fail-closed. Configure the "
            "source in structural_anchors/registry.yaml and ship it "
            "through deploy/configured_gate_sources.py. Honest-"
            "concession records are still allowed.")
    if hit and is_terminus and concession:
        notes.append(f"prior-alias {hit[:3]} + terminus-word, but this "
                     f"is an explicit HONEST-CONCESSION / kill-record — "
                     f"ALLOWED (the membrane enforces honest concession, "
                     f"never punishes it)")
    elif hit and is_terminus and not declared.get("operationally_distinct"):
        failed.append(
            f"RELAPSE: transition ASSERTS prior-alias atom {hit[:3]} as "
            f"terminus/settled WITHOUT operationally_distinct AND is not "
            f"an honest-concession record (tick638 alias / tick639 "
            f"tautology guard)")
    elif hit:
        notes.append(f"prior-alias terms present {hit[:3]} — allowed "
                     f"(not a terminus assertion / concession / "
                     f"operationally_distinct)")

    if failed:
        return MembraneVerdict(False, None, failed, notes)
    import hashlib
    stamp = "CMV1:" + hashlib.sha256(
        (t + json.dumps(declared, sort_keys=True)).encode()).hexdigest()[:16]
    return MembraneVerdict(True, stamp, [], notes
                           + ["all three layers + relapse guard passed"])


def main() -> int:
    """Invoked by the harness-owned hook (NOT by the agent's own flow).
    Reads the emitted transition on argv/stdin, exits non-zero to
    quarantine. Non-zero from a hook is enforced by the runtime."""
    import sys
    text = sys.stdin.read() if not sys.stdin.isatty() else ""
    if len(sys.argv) > 1:
        text = sys.argv[1]
    decl = {}
    if len(sys.argv) > 2:
        try:
            decl = json.loads(sys.argv[2])
        except Exception:
            decl = {}
    v = evaluate(text, decl)
    print(v.as_json())
    return 0 if v.official else 2


if __name__ == "__main__":
    import sys
    sys.exit(main())
