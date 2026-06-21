"""Semantic premise shelf for Lean proof-loop prompts.

This is an advisory retrieval layer. It gives proof-loop workers nearby
Mathlib/APN/NS declarations as candidate premise context, but it does not
create proof value and it does not bypass the existing anti-laundering gates.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from ztare.research_director.apn_semantic import apn_semantic_neighbours
from ztare.research_director.mathlib_semantic import (
    _cosine as _mathlib_cosine,
    _embed_query_genai,
    mathlib_semantic_neighbours,
)


REPO = Path(__file__).resolve().parents[3]


# ── Domain atlas registry (plugin / config-driven) ─────────────────────
# The shelf accepts ZERO hardcoded domain paths. Per-domain atlases are
# registered in the factory policy under
# `operations.semantic_premise_shelf.domain_atlases`, each entry shaped
# {name, atlas_path, corpus_path}. A public clone with no domain atlases
# registered just gets Mathlib + APN hits and a clean "no domain layer"
# fallthrough — never a path-not-found error.
def _domain_atlas_specs() -> list[dict[str, str]]:
    """Read registered domain atlases from policy; empty list if absent."""
    try:
        from ztare.leanmill.policy import read_policy
        policy_path = REPO / "analytics" / "public" / "leanmill" / "dashboard_data" / "leanmill_factory_policy.json"
        pol = read_policy(policy_path)
        ops = pol.get("operations") if isinstance(pol.get("operations"), dict) else {}
        sps = ops.get("semantic_premise_shelf") if isinstance(ops.get("semantic_premise_shelf"), dict) else {}
        specs = sps.get("domain_atlases") if isinstance(sps.get("domain_atlases"), list) else []
        return [s for s in specs if isinstance(s, dict) and s.get("atlas_path") and s.get("corpus_path")]
    except Exception:
        return []


_DOMAIN_ATLAS_CACHE: dict[tuple[str, str], tuple[list[dict[str, Any]], list[list[float]]]] = {}
# Back-compat aliases used by older call sites; deprecated.
_NS_CACHE = _DOMAIN_ATLAS_CACHE


def _load_domain_atlas(
    atlas_path: Path,
    corpus_path: Path,
) -> tuple[list[dict[str, Any]], list[list[float]]]:
    key = (str(atlas_path.resolve()), str(corpus_path.resolve()))
    cached = _NS_CACHE.get(key)
    if cached is not None:
        return cached
    if not atlas_path.exists() or not corpus_path.exists():
        _NS_CACHE[key] = ([], [])
        return [], []
    atlas_payload = json.loads(atlas_path.read_text(encoding="utf-8"))
    corpus_payload = json.loads(corpus_path.read_text(encoding="utf-8"))
    atlas_items = atlas_payload.get("embeddings", []) if isinstance(atlas_payload, dict) else atlas_payload
    embeddings_by_id: dict[str, list[float]] = {}
    for item in atlas_items:
        if isinstance(item, dict) and "id" in item and "embedding" in item:
            embeddings_by_id[str(item["id"])] = item["embedding"]
    corpus_entries = corpus_payload.get("entries", []) if isinstance(corpus_payload, dict) else corpus_payload
    rows: list[dict[str, Any]] = []
    vecs: list[list[float]] = []
    for entry in corpus_entries:
        if not isinstance(entry, dict):
            continue
        eid = str(entry.get("id") or "")
        vec = embeddings_by_id.get(eid)
        if not eid or vec is None:
            continue
        rows.append(entry)
        vecs.append(vec)
    _NS_CACHE[key] = (rows, vecs)
    return rows, vecs


def _cached_embedder() -> Callable[[str], list[float] | None]:
    cache: dict[str, list[float] | None] = {}

    def embed(query: str) -> list[float] | None:
        if query not in cache:
            cache[query] = _embed_query_genai(query)
        return cache[query]

    return embed


def _domain_atlas_semantic_hits(
    query: str,
    *,
    embedder: Callable[[str], list[float] | None],
    top_k: int,
    threshold: float,
) -> tuple[list[dict[str, Any]], int, str | None]:
    """Query every registered domain atlas (via policy) and return merged hits.
    Empty list when no domain atlases registered — that's a clean no-op, not
    an error.
    """
    specs = _domain_atlas_specs()
    if not specs:
        return [], 0, "no domain atlases registered in policy.operations.semantic_premise_shelf.domain_atlases"
    all_rows: list[dict[str, Any]] = []
    all_vecs: list[list[float]] = []
    atlas_names: list[str] = []
    for spec in specs:
        ap = Path(spec["atlas_path"])
        cp = Path(spec["corpus_path"])
        if not ap.is_absolute(): ap = REPO / ap
        if not cp.is_absolute(): cp = REPO / cp
        rows, vecs = _load_domain_atlas(ap, cp)
        for r in rows: r.setdefault("_atlas_name", spec.get("name") or "domain")
        all_rows.extend(rows); all_vecs.extend(vecs)
        if rows: atlas_names.append(spec.get("name") or str(ap.name))
    if not all_rows:
        return [], 0, f"domain atlases registered but empty: {[s.get('name') for s in specs]}"
    qvec = embedder(query)
    if qvec is None:
        return [], len(all_rows), "query embedding unavailable (no GOOGLE_API_KEY or google.genai)"
    scored = [(_mathlib_cosine(qvec, vec), idx) for idx, vec in enumerate(all_vecs)]
    scored.sort(reverse=True, key=lambda item: item[0])
    hits: list[dict[str, Any]] = []
    for cosine, idx in scored[:top_k]:
        if cosine < threshold:
            break
        row = all_rows[idx]
        hits.append(
            {
                "source": row.get("_atlas_name", "domain_atlas"),
                "name": str(row.get("name") or row.get("id") or "?"),
                "kind": str(row.get("kind") or ""),
                "file": str(row.get("path") or row.get("file") or ""),
                "score": round(float(cosine), 4),
                "preview": str(row.get("text") or "")[:300],
                "metadata": {
                    "status": str(row.get("status") or ""),
                    "tags": row.get("tags") or [],
                },
            }
        )
    return hits, len(all_rows), None   # MERGED corpus size (2026-06-13 audit: was `len(rows)` = last spec only)


import re as _re_shelf


def _shelf_conclusion(stmt: str) -> str:
    """Text after the LAST top-level ':' (binders' ':' sit inside parens), ':='-stripped."""
    body = _re_shelf.split(r":=", stmt or "", 1)[0]
    depth = 0
    last = -1
    for i, ch in enumerate(body):
        if ch in "([{⦃":
            depth += 1
        elif ch in ")]}⦄":
            depth -= 1
        elif ch == ":" and depth == 0:
            last = i
    return body[last + 1:].strip() if last >= 0 else body.strip()


def _shelf_norm(s: str) -> str:
    return _re_shelf.sub(r"[()\s]", "", _re_shelf.sub(r"\bid\b", "", s or ""))


def in_scope_citation_hits(query: str, source: str, lean_root, *, k: int = 6) -> list:
    """The MEMOIZATION fix (RCA 2026-06-04): surface IMPORTED-file lemmas whose CONCLUSION matches the
    goal, so the agent (and the prompt) can `exact <name>` instead of re-deriving a result already in
    scope. The premise shelf used to index only the embedded atlases (Mathlib/APN/NS), NEVER the file
    the ad-hoc imports — so a 1-line citation (e.g. indicatorTranslationInteriorTerm_…) was invisible
    and the warm agent re-derived + failed. EXACT-conclusion match → score 1.0 ('this already closes
    it'); token-overlap ≥0.6 → near-match. Pure regex/CPU; advisory like the rest of the shelf."""
    if not source or lean_root is None:
        return []
    from pathlib import Path as _P
    lean_root = _P(lean_root)
    goal_concl_raw = _shelf_conclusion(query)
    goal_concl = _shelf_norm(goal_concl_raw)
    if len(goal_concl) < 4:
        return []
    goal_tokens = set(_re_shelf.findall(r"[A-Za-z_][\w'.]+", goal_concl_raw))
    hits, seen = [], set()
    for mod in _re_shelf.findall(r"(?m)^\s*import\s+([\w.]+)", source):
        f = lean_root / (mod.replace(".", "/") + ".lean")
        if str(f) in seen or not f.exists():
            continue
        seen.add(str(f))
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in _re_shelf.finditer(
                r"(?ms)^\s*(?:@\[[^\]]*\]\s*)?(?:theorem|lemma)\s+([A-Za-z_][\w'.]*)(.*?):=", text):
            name, sig = m.group(1), m.group(2)
            concl_raw = _shelf_conclusion(sig)
            nconcl = _shelf_norm(concl_raw)
            if len(nconcl) < 4:
                continue
            if nconcl == goal_concl:
                score = 1.0
            else:
                lt = set(_re_shelf.findall(r"[A-Za-z_][\w'.]+", concl_raw))
                ov = len(goal_tokens & lt) / max(1, len(goal_tokens | lt))
                if ov < 0.6:
                    continue
                score = round(0.6 + 0.39 * ov, 4)
            hits.append({"source": "in_scope", "name": name, "kind": "imported_lemma",
                         "file": mod, "score": score, "preview": concl_raw[:160],
                         "metadata": {"citation": f"exact {name}"}})
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:k]


# ── Own-ledger recall (#124, the alien leg) ─────────────────────────────
# Index leanmill's OWN PRODUCTION — the cert ledger's kernel-ratified closures and the attempts-DB GAP
# diagnoses (the agent's own named missing lemmas) — through the SAME embedding pipeline, so every shelf
# build also answers "have WE already proven (or already diagnosed the gap in) something 0.9-similar?".
# The campaign manifest keeps governance NAMES; embeddings do RETRIEVAL. Advisory + fail-open like every
# leg; vectors are disk-cached by content sha so a text is embedded ONCE ever. =0 reverts.
OWN_LEDGER_CERTS = REPO / "analytics" / "public" / "queries" / "adhoc_closure_certificates.jsonl"
OWN_LEDGER_ATTEMPTS_DB = REPO / "analytics" / "public" / "queries" / "solver_lane_attempts.db"
OWN_LEDGER_EMBED_CACHE = REPO / "analytics" / "public" / "leanmill" / "dashboard_data" / "own_ledger_embeddings.json"
_OWN_LEDGER_MAX_NEW_EMBEDS = 48     # bound per-call latency; the remainder is REPORTED, never silent


def _own_sha(text: str) -> str:
    import hashlib
    return hashlib.sha256(" ".join((text or "").split()).encode("utf-8")).hexdigest()[:24]


def own_ledger_corpus(cert_ledger: "Path | None" = None, attempts_db: "Path | None" = None,
                      max_rows: int = 300) -> list[dict[str, Any]]:
    """Rows {id, kind: proven_rung|open_gap, name, text, ts} from our own production. Proven rungs =
    cert rows with outcome=='closed' (statement extracted from the recompilable probe — the kernel-
    verified artifact, not the narrated goal); open gaps = the attempts-DB `GAP:` diagnoses. Read-only,
    newest-first, deduped by content."""
    cert_ledger = Path(cert_ledger) if cert_ledger else OWN_LEDGER_CERTS
    attempts_db = Path(attempts_db) if attempts_db else OWN_LEDGER_ATTEMPTS_DB
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        lines = cert_ledger.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    for line in reversed(lines):                      # newest first
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("outcome") != "closed":
            continue
        target = str(r.get("target") or "")
        probe = str(r.get("recompilable_probe") or "")
        # canonical, binder-safe statement extraction (was an ad-hoc `(.*?):=` regex = the first-`:=`
        # binder bug; 2026-06-13 lexical sweep). extract_signature returns `<binders> : <conclusion>`.
        from ztare.leanmill.lean_source import extract_signature as _exsig
        _sig = _exsig(probe, target) if (target and probe) else ""
        stmt = f"theorem {target} {_sig}".rstrip() if _sig else ""
        if not stmt:
            continue
        sha = _own_sha(stmt)
        if sha in seen:
            continue
        seen.add(sha)
        # #129: carry the PROOF (the kernel-verified recompilable probe) so a HIGH-similarity recall can
        # surface it for tactic-skeleton transport, not just the statement. Capped; kernel re-verifies.
        rows.append({"id": sha, "kind": "proven_rung", "name": target, "text": stmt,
                     "proof": probe[:4000], "ts": str(r.get("ts") or "")})
        if len(rows) >= max_rows:
            return rows
    try:
        import sqlite3
        con = sqlite3.connect(f"file:{attempts_db}?mode=ro", uri=True)
        cur = con.execute("SELECT row_id, attempt_at, notes FROM attempts "
                          "WHERE notes LIKE '%GAP:%' ORDER BY attempt_at DESC LIMIT ?", (max_rows,))
        for row_id, ts, notes in cur:
            txt = str(notes or "")
            # sqlite LIKE is case-INSENSITIVE: the query also matches the lowercase "agent's own gap:"
            # cap-echo rows (derivative duplicates of an earlier GAP row). Case-sensitive re-check per
            # row — found by the live positive control (the first echo row IndexError'd the whole leg).
            if "GAP:" not in txt:
                continue
            gap = txt.split("GAP:", 1)[1].split(" | ", 1)[0].strip()
            if len(gap) < 12:
                continue
            sha = _own_sha(gap)
            if sha in seen:
                continue
            seen.add(sha)
            rows.append({"id": sha, "kind": "open_gap", "name": str(row_id or ""), "text": gap,
                         "ts": str(ts or "")})
            if len(rows) >= max_rows:
                break
        con.close()
    except Exception:  # noqa: BLE001 — no DB / old schema ⇒ certs-only corpus, never an error
        pass
    return rows


def _own_cache_load(cache_path: Path) -> dict[str, list[float]]:
    try:
        d = json.loads(cache_path.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def own_ledger_hits(
    query: str,
    *,
    embedder: Callable[[str], list[float] | None],
    top_k: int = 4,
    threshold: float = 0.55,
    cert_ledger: "Path | None" = None,
    attempts_db: "Path | None" = None,
    cache_path: "Path | None" = None,
) -> tuple[list[dict[str, Any]], int, str | None]:
    """Cosine-match the query against our own proven rungs + gap diagnoses. Same return contract as
    the other legs: (hits, corpus_size, skip_reason)."""
    if os.environ.get("ZTARE_LEANMILL_OWN_LEDGER", "1") == "0":
        return [], 0, "own_ledger disabled (ZTARE_LEANMILL_OWN_LEDGER=0)"
    corpus = own_ledger_corpus(cert_ledger, attempts_db)
    if not corpus:
        return [], 0, None     # an empty ledger is a young campaign, not a degradation
    cache_path = Path(cache_path) if cache_path else OWN_LEDGER_EMBED_CACHE
    cache = _own_cache_load(cache_path)
    new_embeds, pending = 0, 0
    for row in corpus:
        if row["id"] in cache:
            continue
        if new_embeds >= _OWN_LEDGER_MAX_NEW_EMBEDS:
            pending += 1       # REPORTED below — a capped sweep must never read as "covered everything"
            continue
        vec = embedder(row["text"])
        new_embeds += 1
        if vec:
            cache[row["id"]] = vec
    if new_embeds:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache), encoding="utf-8")
        except OSError:
            pass               # cache is an optimization; recall still works this call
    qvec = embedder(query)
    if qvec is None:
        return [], len(corpus), "query embedding unavailable (no GOOGLE_API_KEY or google.genai)"
    scored = [( _mathlib_cosine(qvec, cache[row["id"]]), row) for row in corpus if row["id"] in cache]
    scored.sort(reverse=True, key=lambda item: item[0])
    hits = []
    _proof_sim = float(os.environ.get("ZTARE_LEANMILL_OWN_LEDGER_PROOF_SIM", "0.82"))
    for cosine, row in scored[:top_k]:
        if cosine < threshold:
            break
        _hit = {"source": "own_ledger", "name": row["name"], "kind": row["kind"],
                "file": "", "score": round(float(cosine), 4), "preview": row["text"][:300],
                "metadata": {"ts": row["ts"]}}
        # #129: a HIGH-similarity proven rung carries its FULL proof for tactic-skeleton transport (a
        # mathematician reuses the proof structure, not just cites the statement). The agent decides
        # whether/how to adapt it; the kernel re-verifies any transported proof. Advisory, more agency.
        if row["kind"] == "proven_rung" and cosine >= _proof_sim and row.get("proof"):
            _hit["proof"] = row["proof"]
        hits.append(_hit)
    skip = f"own_ledger: {pending} texts pending embed (capped at {_OWN_LEDGER_MAX_NEW_EMBEDS}/call)" if pending else None
    return hits, len(corpus), skip


def build_semantic_premise_shelf(
    query: str,
    *,
    top_k_mathlib: int = 8,
    top_k_apn: int = 5,
    top_k_ns: int = 5,
    top_k_own: int = 4,
    threshold: float = 0.55,
    include_ns: bool = True,
    embedder: Callable[[str], list[float] | None] | None = None,
    source: str = "",
    lean_root=None,
) -> dict[str, Any]:
    """Return an advisory candidate-premise shelf for a proof-loop query."""
    query = str(query or "").strip()
    if not query:
        return {
            "schema": "leanmill-semantic-premise-shelf-v1",
            "query_preview": "",
            "hits": [],
            "skip_reasons": ["empty query"],
        }
    embed_fn = embedder or _cached_embedder()
    hits: list[dict[str, Any]] = []
    skip_reasons: list[str] = []

    # IN-SCOPE citation leg FIRST (the memoization fix) — imported lemmas whose conclusion matches the
    # goal; an exact match (score 1.0) is a direct `exact <name>` closure. Surfaced ABOVE the atlas hits.
    try:
        hits.extend(in_scope_citation_hits(query, source, lean_root))
    except Exception as _e:  # never let the new leg break the shelf
        skip_reasons.append(f"in_scope: {str(_e)[:80]}")

    # OWN-LEDGER recall (#124) — our proven rungs + gap diagnoses, BEFORE the generic atlases (a
    # 0.9-similar rung we already kernel-proved beats any Mathlib neighbour for campaign work).
    own_size = 0
    if top_k_own > 0:
        try:
            own_hits, own_size, own_skip = own_ledger_hits(
                query, embedder=embed_fn, top_k=top_k_own, threshold=threshold)
            if own_skip:
                skip_reasons.append(own_skip)
            hits.extend(own_hits)
        except Exception as _e:  # noqa: BLE001 — never let the new leg break the shelf
            skip_reasons.append(f"own_ledger: {str(_e)[:80]}")

    mathlib_hits, mathlib_size, mathlib_filtered, mathlib_skip = mathlib_semantic_neighbours(
        query,
        top_k=top_k_mathlib,
        threshold=threshold,
        embedder=embed_fn,
    )
    if mathlib_skip:
        skip_reasons.append(f"mathlib: {mathlib_skip}")
    for hit in mathlib_hits:
        hits.append(
            {
                "source": "mathlib",
                "name": hit.name,
                "kind": hit.kind,
                "file": hit.file,
                "score": hit.cosine,
                "preview": hit.preview,
                "metadata": {"shapes": hit.shapes},
            }
        )

    apn_hits, apn_size, apn_filtered, apn_skip = apn_semantic_neighbours(
        query,
        top_k=top_k_apn,
        threshold=threshold,
        domain_filter=None,
        embedder=embed_fn,
    )
    if apn_skip:
        skip_reasons.append(f"apn: {apn_skip}")
    for hit in apn_hits:
        hits.append(
            {
                "source": "apn",
                "name": hit.name,
                "kind": hit.kind,
                "file": hit.file,
                "score": hit.cosine,
                "preview": hit.snippet,
                "metadata": {
                    "domain": hit.domain,
                    "variant_tag": hit.variant_tag,
                    "id": hit.id,
                },
            }
        )

    ns_size = 0
    # `include_ns` parameter name retained for back-compat; meaning is now
    # "include domain atlas hits from any registered atlas in policy".
    if include_ns:
        domain_hits, ns_size, domain_skip = _domain_atlas_semantic_hits(
            query,
            embedder=embed_fn,
            top_k=top_k_ns,
            threshold=threshold,
        )
        if domain_skip:
            skip_reasons.append(f"domain_atlas: {domain_skip}")
        hits.extend(domain_hits)

    hits.sort(key=lambda item: (float(item.get("score") or 0.0), str(item.get("source") or "")), reverse=True)
    return {
        "schema": "leanmill-semantic-premise-shelf-v1",
        "query_preview": query[:500],
        "threshold": threshold,
        "corpus_sizes": {
            "mathlib": mathlib_size,
            "mathlib_filtered": mathlib_filtered,
            "apn": apn_size,
            "apn_filtered": apn_filtered,
            "domain_atlas": ns_size,
            "own_ledger": own_size,
        },
        "hits": hits,
        "skip_reasons": skip_reasons,
        "science_rule": "Advisory retrieval context only; proof value still requires Lean replay, matched controls, and Governance Gate receipts.",
    }


def render_semantic_premise_shelf(shelf: dict[str, Any], *, max_hits: int = 12) -> str:
    """Render a compact prompt block."""
    hits = [h for h in shelf.get("hits") or [] if isinstance(h, dict)]
    lines = [
        "Candidate lemma shelf (semantic retrieval context only; not a negative dictionary and not proof credit):"
    ]
    if not hits:
        skips = "; ".join(str(x) for x in (shelf.get("skip_reasons") or []) if str(x))
        lines.append(f"- none available above threshold{': ' + skips if skips else ''}")
        return "\n".join(lines)
    for hit in hits[:max_hits]:
        source = str(hit.get("source") or "?")
        score = float(hit.get("score") or 0.0)
        kind = str(hit.get("kind") or "").strip()
        name = str(hit.get("name") or "?").strip()
        file = str(hit.get("file") or "").strip()
        preview = " ".join(str(hit.get("preview") or "").split())[:180]
        meta = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        tag = ""
        if source == "mathlib" and meta.get("shapes"):
            tag = f" shapes={','.join(str(s) for s in meta.get('shapes')[:4])}"
        elif source == "apn" and meta.get("domain"):
            tag = f" domain={meta.get('domain')}"
        elif meta.get("status"):
            tag = f" status={meta.get('status')}"
        loc = f" @ {file}" if file else ""
        if source == "in_scope":
            # the memoization hit: an imported lemma already in scope whose conclusion matches — the
            # agent should CITE it, not re-derive. A match≈1.0 is a direct one-line closure.
            verb = "CLOSES (try `exact " + name + "`)" if score >= 0.999 else "candidate (try `exact " + name + "`)"
            lines.append(f"- [IN-SCOPE match={score:.2f}] {verb} — imported lemma, conclusion matches the goal{loc}")
        elif source == "own_ledger":
            # #124 recall over OUR OWN production: a similar statement we already kernel-proved is a
            # cite/transport target; a similar GAP we already diagnosed must not be re-derived blind.
            if kind == "proven_rung":
                lines.append(f"- [OWN-LEDGER cos={score:.4f}] PROVEN rung {name} — a ~similar statement is"
                             " ALREADY KERNEL-PROVEN in this repo's campaigns; cite/transport it, do not re-derive")
                # #129: on a HIGH-similarity hit the agent gets the FULL kernel-verified proof to adapt
                # the tactic skeleton (not just the statement). The kernel re-verifies any transport.
                _pf = str(hit.get("proof") or "").strip()
                if _pf:
                    lines.append("  proof to transport (kernel-verified; adapt the skeleton, do not assume it ports verbatim):")
                    lines.append("  ```lean\n  " + _pf.replace("\n", "\n  ") + "\n  ```")
            else:
                lines.append(f"- [OWN-LEDGER cos={score:.4f}] KNOWN GAP ({name}) — a ~similar gap was already"
                             " diagnosed; read it before re-attacking the same wall")
        else:
            lines.append(f"- [{source} cos={score:.4f}] {kind} {name}{tag}{loc}")
        if preview:
            lines.append(f"  preview: {preview}")
    if shelf.get("skip_reasons"):
        lines.append("Retrieval degradation notes: " + "; ".join(str(x) for x in shelf.get("skip_reasons")))
    return "\n".join(lines)


def semantic_premise_shelf_enabled() -> bool:
    return os.environ.get("LEANMILL_DISABLE_SEMANTIC_PREMISE_SHELF", "").lower() not in {"1", "true", "yes"}


def _selftest() -> int:
    """Hermetic (#124 own-ledger leg): injectable embedder, tmp cert ledger + attempts DB + vector
    cache — no network, no real-repo writes."""
    import sqlite3
    import tempfile
    fails: list[str] = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    td = Path(tempfile.mkdtemp(prefix="sps_"))
    certs = td / "certs.jsonl"
    db = td / "attempts.db"
    cache = td / "own_cache.json"
    probe = ("import Mathlib\n\ntheorem rung_residue (p : Polynomial ℚ) :\n"
             "    p.eval 0 = 0 → True := by\n  intro h\n  trivial\n")
    certs.write_text(
        json.dumps({"target": "rung_residue", "outcome": "closed", "ts": "2026-06-12T00:00:00+00:00",
                    "recompilable_probe": probe}) + "\n"
        + json.dumps({"target": "rung_rejected", "outcome": "rejected_governance", "ts": "t",
                      "recompilable_probe": probe.replace("rung_residue", "rung_rejected")}) + "\n",
        encoding="utf-8")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE attempts (row_id TEXT, attempt_at TEXT, provider TEXT, outcome TEXT, notes TEXT)")
    con.execute("INSERT INTO attempts VALUES ('adhoc::crux', '2026-06-12T01:00:00', 'x', 'open', "
                "'agentic_leaf open: budget | GAP: residue of the derivative at a simple root needs a partial-fraction API | tail')")
    con.execute("INSERT INTO attempts VALUES ('adhoc::other', '2026-06-12T02:00:00', 'x', 'open', 'no gap here')")
    # the cap-echo row: lowercase "gap:" — sqlite LIKE matches it case-insensitively but it is a
    # derivative duplicate; it must be SKIPPED, never crash the leg (live-control regression)
    con.execute("INSERT INTO attempts VALUES ('adhoc::echo', '2026-06-12T03:00:00', 'x', 'open', "
                "'warm_goal_cap: 2 prior (last: uses_sorry; agent''s own gap: residue_not_localized)')")
    con.commit(); con.close()

    corpus = own_ledger_corpus(certs, db)
    ok("corpus: closed cert in, rejected cert OUT, GAP row in, lowercase cap-echo SKIPPED",
       {r["kind"] for r in corpus} == {"proven_rung", "open_gap"} and len(corpus) == 2
       and any(r["name"] == "rung_residue" for r in corpus)
       and not any("residue_not_localized" in r["text"] for r in corpus))

    calls = {"n": 0}

    def embed(text: str):
        calls["n"] += 1
        t = text.lower()
        return [1.0, 0.0] if "residue" in t else [0.0, 1.0]

    hits, size, skip = own_ledger_hits("residue vanishing at simple roots", embedder=embed,
                                       cert_ledger=certs, attempts_db=db, cache_path=cache)
    ok("hits: residue-similar rows recalled, ranked, both kinds",
       size == 2 and len(hits) == 2 and hits[0]["score"] >= hits[1]["score"]
       and {h["kind"] for h in hits} == {"proven_rung", "open_gap"} and skip is None)
    n_first = calls["n"]
    hits2, _, _ = own_ledger_hits("residue vanishing at simple roots", embedder=embed,
                                  cert_ledger=certs, attempts_db=db, cache_path=cache)
    ok("vector cache: second call embeds ONLY the query (corpus cached on disk)",
       calls["n"] == n_first + 1 and len(hits2) == 2)
    rendered = render_semantic_premise_shelf({"hits": hits})
    ok("render: OWN-LEDGER branches (proven=cite/transport, gap=read-before-reattack)",
       "ALREADY KERNEL-PROVEN" in rendered and "KNOWN GAP" in rendered)
    ok("#129: high-sim proven rung carries its full proof + renders the transport block",
       any(h["kind"] == "proven_rung" and h.get("proof") for h in hits) and "proof to transport" in rendered)
    _sv = os.environ.get("ZTARE_LEANMILL_OWN_LEDGER")
    try:
        os.environ["ZTARE_LEANMILL_OWN_LEDGER"] = "0"
        h0, s0, sk0 = own_ledger_hits("residue", embedder=embed, cert_ledger=certs,
                                      attempts_db=db, cache_path=cache)
        ok("kill-switch: =0 reverts (no hits, reason named)", h0 == [] and "disabled" in (sk0 or ""))
    finally:
        os.environ.pop("ZTARE_LEANMILL_OWN_LEDGER", None) if _sv is None else os.environ.__setitem__("ZTARE_LEANMILL_OWN_LEDGER", _sv)
    h_missing, s_missing, sk_missing = own_ledger_hits("q", embedder=embed,
                                                       cert_ledger=td / "absent.jsonl",
                                                       attempts_db=td / "absent.db",
                                                       cache_path=cache)
    ok("young campaign: absent ledgers ⇒ clean empty, not an error",
       h_missing == [] and s_missing == 0 and sk_missing is None)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
