#!/usr/bin/env python3
"""v33_paraphrase_gate.py — leakage-independent gold-name-verbatim / paraphrase organ.

Second forward gate (after the validated vacuity organ). Catches the
v28-v29 retraction class: a claimed "moat-grade closure" whose proof is
essentially `exact <existing Mathlib gold lemma>` + trivial glue.

Same pattern as the vacuity organ — shape-predict + independent-corpus-
confirm, ZERO audit verdict:

  Component 1 (instant, deterministic, no audit): proof-shape.
    gold_name_verbatim_suspect iff:
      - exactly ONE distinct named (capitalised / dotted) lemma is cited
      - the rest of the proof is only trivial glue
        (obtain / exact / ⟨…⟩ / intro / rintro / refine ⟨…⟩)
      - NO multi-step composition (no linarith/nlinarith/calc combining
        ≥2 `have`s; ≥2 distinct `have := <lemma>` lines = genuine)

  Component 2 (independent, no audit): does that single cited name exist
    in Mathlib's OWN corpus (mathlib_graph.json, 122K decls)? If yes, the
    "closure" is verbatim an existing Mathlib lemma — confirmed leakage-
    independently (uses Mathlib's corpus, not any kill verdict).

Ground-truth validation built in:
  + H12 (intermediate_value_Ioo + obtain/exact)  -> MUST flag + confirm
  - H07 (norm_sub_le... cited twice + linarith)   -> MUST NOT flag (genuine)
"""
from __future__ import annotations
import argparse, json, re, sys, pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V28B = ROOT / "analytics/public/leanmill/results/v28B_dep_graph_artifacts"

TRIVIAL_GLUE = {"obtain", "exact", "intro", "intros", "rintro", "refine",
                "constructor", "use", "⟨", "⟩", "show", "exact?"}
COMPOSITION_TACTICS = {"linarith", "nlinarith", "calc", "polyrith", "gcongr",
                       "field_simp", "ring_nf", "omega"}

# Goal-transforming "work" tactics. Their presence means the proof does real
# reduction over its OWN goal before any library close, so a single cited gold
# lemma is the legitimate CLOSING step of a real proof, NOT a verbatim restatement
# of that lemma. Trivial glue (obtain/exact/intro/rintro/refine/constructor/use/
# show) is deliberately EXCLUDED — that glue wraps a bare restatement (e.g. the
# H12 obtain+exact positive control, which must still flag). Added 2026-05-30
# after the ATLAS + APN audits showed the suspect-only rule false-flags legitimate
# library-composed proofs like `funext; simp; exact <Mathlib lemma>`.
# Tactics that do genuine MATHEMATICAL reduction (not mere reshaping). NOTE the
# deliberate exclusions (2026-05-30, after adversarial SEV1-A): funext/ext/intro/
# dsimp are pure RESHAPING — closing with a gold lemma right after them is still a
# restatement, so they must NOT count as work. `simp` is handled separately because
# an EMPTY `simp only []` is a no-op an author can prepend to evade the blocker.
REAL_WORK_TACTICS = {
    "rw", "rewrite", "erw", "induction", "cases", "rcases", "calc", "conv", "convert",
    "subst", "norm_num", "norm_cast", "push_cast", "field_simp", "ring", "ring_nf",
    "linarith", "nlinarith", "polyrith", "gcongr", "omega", "positivity", "decide",
    "aesop", "tauto", "by_contra", "contrapose", "wlog", "lift", "generalize",
    "interval_cases", "fun_prop", "measurability", "continuity", "bound", "split",
    # added 2026-05-30 (re-review false-positive fix): genuine reduction tactics
    # whose absence wrongly flagged legitimate library-composed proofs as trivial.
    "mono", "group", "abel", "module", "linear_combination", "fin_cases",
    "exact_mod_cast", "apply_mod_cast", "norm_cast", "rel", "gcongr",
}
WORK_TACTICS = REAL_WORK_TACTICS  # back-compat alias

# Lean comments must be stripped before token-scanning so a comment like
# `-- rw lemma_x` cannot flip has_work_tactic on the standalone --file path
# (re-review SEV3 comment-token evasion). audit_l3 already passes clean_block.
_COMMENT_RE = re.compile(r"/-.*?-/|--[^\n]*", re.DOTALL)


def _strip_comments(s: str) -> str:
    return _COMMENT_RE.sub(" ", s)


def has_work_tactic(body: str) -> bool:
    """True iff the proof body does genuine goal reduction (so a single cited gold
    lemma is a legitimate CLOSING step, not a verbatim restatement). Closes SEV1-A:
    a no-op `simp only []` / `dsimp` / bare `funext` does NOT count as work.
    KNOWN RESIDUAL (structural, lexical): a no-op invocation of a real tactic token
    (e.g. `conv => skip`, `split` on a non-conjunction, `cases h` on a trivial hyp)
    still flips this True — only a compile-based 'remove the lemma, is a goal left?'
    probe can close that. The gold_name_verbatim BLOCKER is therefore advisory-grade
    against an adversarial author; the SOUND teeth are L1 (sorry/admit) + L2 (kernel
    #print axioms allowlist)."""
    body = _strip_comments(body)
    toks = set(re.findall(r"[A-Za-z_][A-Za-z_']*", body))
    if toks & REAL_WORK_TACTICS:
        return True
    # `simp`/`simp_all`/`simpa` count as work ONLY when non-empty (has lemma args or
    # is a bare powerful simp). `simp only []` is a no-op; `dsimp` is reshaping and
    # never matches `\bsimp` (no word boundary inside "dsimp").
    for m in re.finditer(r"\bsimp(?:_all|a)?\b([^\n;]*)", body):
        if re.match(r"\s*only\s*\[\s*\]", m.group(1)):
            continue  # empty simp -> no-op
        return True
    return False

_name_set = None


def _mathlib_names() -> set:
    """Return the corpus index of Mathlib names this gate paraphrase-checks
    against. Reads `v28B_dep_graph_artifacts/node_index.pkl` when present;
    that index is NS-Track-B-specific. When absent — e.g. when this gate
    runs against an unrelated audit lane like AlphaProof Nexus / Erdős /
    OEIS / any lane that hasn't built its own corpus index — degrade
    gracefully: return an empty name set so the paraphrase check is a
    no-op. The remaining L3 gates (indirect, exact, currency, preflight
    risk) still run.

    TODO (architecture): replace this with a per-audit-lane corpus index
    path. The audit candidate JSON already carries a `target_kind` field
    which is the right place to dispatch the corpus index path.
    """
    global _name_set
    if _name_set is None:
        idx_path = V28B / "node_index.pkl"
        if not idx_path.exists():
            _name_set = set()
            return _name_set
        idx = pickle.load(open(idx_path, "rb"))
        nm = idx["name_to_idx"]
        _name_set = set(nm.keys())
    return _name_set


def extract_proof_body(text: str) -> str:
    m = re.search(r":=\s*by\b(.*)$", text, re.DOTALL)
    return m.group(1).strip() if m else ""


_PROJ_SUFFIX = re.compile(r"\.(mpr|mp|1|2|left|right|symm|le|ge|elim|intro|continuousOn|some|out)$")


def _head_ident(expr: str) -> str | None:
    """First identifier token of an application expression (the load-bearing
    head), skipping leading `@`, parens, and anonymous constructors."""
    expr = expr.strip().lstrip("@(")
    m = re.match(r"\s*([A-Za-z_][\w'.]*)", expr)
    if not m:
        return None
    head = m.group(1)
    if head in ("by", "fun", "if", "then", "else", "show", "have", "let"):
        return None
    return head


def head_cited_lemmas(body: str) -> list[str]:
    """Load-bearing lemmas only: the HEAD identifier of each
    `have/obtain/let ... := EXPR`, `exact EXPR`, `apply EXPR`,
    `refine EXPR`, `simpa ... using EXPR`. Args / bound locals / trivial
    projections inside EXPR are intentionally NOT counted."""
    heads = []
    for m in re.finditer(r":=\s*([^\n]+)", body):
        h = _head_ident(m.group(1))
        if h:
            heads.append(h)
    for m in re.finditer(r"\b(?:exact|apply|refine)\s+([^\n]+)", body):
        h = _head_ident(m.group(1))
        if h:
            heads.append(h)
    for m in re.finditer(r"\busing\s+([^\n]+)", body):
        h = _head_ident(m.group(1))
        if h:
            heads.append(h)
    # keep only plausible Mathlib lemma names: contain _ or . , len>4,
    # not a bare local hypothesis (h, h1, hc_mem...), not a pure projection
    out = []
    for h in heads:
        if re.match(r"^h[\w']*$", h):           # local hypothesis
            continue
        # Recover the BASE name from a projection rather than discarding it, so a
        # verbatim restatement closed via `.mpr`/`.symm`/`.le` (re-review SEV1-B
        # evasion) still counts as the cited gold lemma.
        base = _PROJ_SUFFIX.sub("", h)
        if re.match(r"^h[\w']*$", base):
            continue
        if (("_" in base) or ("." in base)) and len(base) > 4:
            out.append(base)
    return sorted(set(out))


def _extract_term_body(text: str) -> str:
    """Term-mode proof body: `:= <expr>` where <expr> is NOT a `by` block.
    SEV1-B: previously invisible (extract_proof_body only matched `:= by`)."""
    m = re.search(r":=\s*(.+)$", text, re.DOTALL)
    if not m:
        return ""
    expr = m.group(1).strip()
    return "" if re.match(r"by\b", expr) else expr


def _term_named_lemmas(expr: str) -> list[str]:
    """Distinct plausible-Mathlib-lemma names in a term-mode proof expression."""
    out = []
    for h in re.findall(r"[A-Za-z_][\w'.]*", expr):
        if h in ("fun", "by", "if", "then", "else", "match", "with", "let", "do"):
            continue
        base = _PROJ_SUFFIX.sub("", h)   # recover base (gold_lemma.symm -> gold_lemma)
        if re.match(r"^h[\w']*$", base):
            continue
        if (("_" in base) or ("." in base)) and len(base) > 4:
            out.append(base)
    return sorted(set(out))


def detect_gold_name_verbatim(statement_and_proof: str) -> dict:
    body = extract_proof_body(statement_and_proof)
    if not body:
        # SEV1-B: term-mode proof `:= <expr>` (no `by`). A single-lemma term such as
        # `theorem mine : G := Existing.gold_lemma h` is the simplest verbatim
        # restatement and was previously never even suspect.
        term = _extract_term_body(statement_and_proof)
        if term:
            names = _term_named_lemmas(term)
            # A lambda / arrow construction (`fun x => …`, `λ …`) does real
            # construction, not a bare restatement (re-review SEV1-B false-positive).
            is_construction = ("=>" in term) or bool(re.match(r"(fun\b|λ)", term.strip()))
            suspect = (len(names) == 1) and not is_construction
            return {
                "gold_name_verbatim_suspect": bool(suspect),
                "trivial_restatement": bool(suspect),   # term mode = zero tactic work
                "has_work_tactic": False,
                "mode": "term",
                "distinct_cited_lemmas": names,
                "distinct_have_lemmas": [],
                "has_multistep_composition": False,
                "primary_cited": names[0] if names else None,
                "body_preview": term[:160],
            }
        return {"gold_name_verbatim_suspect": False, "reason": "no proof body"}
    have_lemma_lines = re.findall(r"\bhave\s+[\w']+[^\n]*?:=\s*([^\n]+)", body)
    have_heads = [_head_ident(h) for h in have_lemma_lines]
    have_heads = [h for h in have_heads if h and (("_" in h) or ("." in h)) and len(h) > 4
                  and not _PROJ_SUFFIX.search(h) and not re.match(r"^h[\w']*$", h)]
    distinct_have_lemmas = sorted(set(have_heads))
    distinct_cited = head_cited_lemmas(body)
    has_composition = any(t in body for t in COMPOSITION_TACTICS) and len(have_lemma_lines) >= 2

    suspect = (
        len(distinct_cited) == 1            # exactly one load-bearing lemma
        and not has_composition             # no multi-have composition
        and len(distinct_have_lemmas) <= 1  # not ≥2 distinct lemma-haves
    )
    # A single cited gold lemma is only a TRIVIAL RESTATEMENT (the laundering signal)
    # when the proof does NO goal-transforming work of its own — i.e. it is a bare
    # `exact/apply <lemma>` (or term-mode `:= <lemma>`) with at most trivial glue.
    # If the proof funext/simp/rw/inducts/etc. before closing with the lemma, it is a
    # legitimate library-composed proof, not a restatement. Only trivial_restatement
    # should be elevated to a top-level BLOCKER; suspect-but-not-trivial stays advisory.
    work = has_work_tactic(body)
    trivial_restatement = bool(suspect and not work)
    return {
        "gold_name_verbatim_suspect": bool(suspect),
        "trivial_restatement": trivial_restatement,
        "has_work_tactic": work,
        "distinct_cited_lemmas": distinct_cited,
        "n_have_lemma_lines": len(have_lemma_lines),
        "distinct_have_lemmas": distinct_have_lemmas,
        "has_multistep_composition": has_composition,
        "primary_cited": distinct_cited[0] if distinct_cited else None,
        "body_preview": body[:160],
    }


def independent_corpus_confirm(name: str | None) -> dict:
    """Is `name` a real Mathlib decl (Mathlib's own corpus, no audit verdict)?"""
    if not name:
        return {"in_mathlib": None, "reason": "no primary cited lemma"}
    nm = _mathlib_names()
    direct = name in nm
    tail = name.rsplit(".", 1)[-1]
    tail_hit = tail in nm
    return {
        "in_mathlib": bool(direct or tail_hit),
        "match_kind": "direct" if direct else ("tail" if tail_hit else "none"),
        "queried": name,
    }


GT_POS = ("H12", """import Mathlib
example (f : ℝ → ℝ) (hf : Continuous f) (a b : ℝ) (hab : a < b) (ha : f a < 0) (hb : 0 < f b) :
    ∃ c ∈ Set.Ioo a b, f c = 0 := by
  obtain ⟨c, hc_mem, hc_eq⟩ :=
    intermediate_value_Ioo hab.le hf.continuousOn (Set.mem_Ioo.mpr ⟨ha, hb⟩)
  exact ⟨c, hc_mem, hc_eq⟩""")

GT_NEG = ("H07", """import Mathlib
example {E : Type*} [SeminormedAddCommGroup E] (a b c d : E) :
    ‖a - d‖ ≤ ‖a - b‖ + ‖b - c‖ + ‖c - d‖ := by
  have h1 : ‖a - d‖ ≤ ‖a - c‖ + ‖c - d‖ := norm_sub_le_norm_sub_add_norm_sub a c d
  have h2 : ‖a - c‖ ≤ ‖a - b‖ + ‖b - c‖ := norm_sub_le_norm_sub_add_norm_sub a b c
  linarith""")

# Legitimate library-COMPOSED proof: real work (funext/simp) over its OWN goal, then
# closes with ONE Mathlib lemma. suspect (one cited lemma) but MUST NOT be a
# trivial_restatement → must NOT become a blocker. This is the ATLAS pullbackForm_id
# false-positive the 2026-05-30 work-tactic fix targets.
GT_NEG_WORK = ("ATLAS_pullbackForm_id", """import Mathlib
theorem pullbackForm_id (ω : M) : pullbackForm LinearMap.id ω = ω := by
  funext x
  simp only [pullbackForm, Function.comp]
  exact AlternatingMap.compLinearMap_id ω""")

# SEV1-A attack: prepend a NO-OP (`simp only []`) to a bare restatement to dodge the
# blocker. MUST still be a trivial_restatement (no-op is not real work).
GT_POS_NOOP = ("noop_evasion", """import Mathlib
theorem mine : SomeProp := by
  simp only []
  exact intermediate_value_Ioo""")

# SEV1-B attack: term-mode verbatim restatement (no `by`). MUST be suspect + trivial.
GT_POS_TERM = ("term_restatement", """import Mathlib
theorem mine (a c d : E) : ‖a - d‖ ≤ ‖a - c‖ + ‖c - d‖ :=
  norm_sub_le_norm_sub_add_norm_sub a c d""")

# Re-review SEV1-B evasion: restatement closed via a projection (`.mpr`/`.symm`/`.le`)
# must NOT vanish to not-suspect — base name recovered, MUST stay suspect + trivial.
GT_POS_PROJ = ("projection_restatement", """import Mathlib
theorem mine : P := by
  exact some_gold_iff_lemma.mpr h""")

# Re-review SEV1-B false-positive: a term-mode LAMBDA construction is real work, NOT
# a bare restatement — must NOT be flagged trivial.
GT_NEG_LAMBDA = ("term_lambda_construction", """import Mathlib
theorem mine : ∀ x, P x :=
  fun x => some_real_construction x""")


def run_validation() -> dict:
    res = {}
    for tag, src in (("positive_H12", GT_POS), ("negative_H07", GT_NEG),
                     ("negative_work_ATLAS", GT_NEG_WORK),
                     ("positive_noop", GT_POS_NOOP), ("positive_term", GT_POS_TERM),
                     ("positive_proj", GT_POS_PROJ), ("negative_lambda", GT_NEG_LAMBDA)):
        name, txt = src
        d = detect_gold_name_verbatim(txt)
        c = independent_corpus_confirm(d.get("primary_cited"))
        res[tag] = {"row": name, "detect": d, "corpus_confirm": c}
    pos = res["positive_H12"]
    neg = res["negative_H07"]
    work = res["negative_work_ATLAS"]
    # H12: bare obtain+exact of one gold lemma = trivial restatement -> MUST flag (blocker).
    pos_ok = pos["detect"]["trivial_restatement"] and pos["corpus_confirm"]["in_mathlib"]
    # H07: two distinct lemma-haves + linarith -> not even suspect.
    neg_ok = not neg["detect"]["gold_name_verbatim_suspect"]
    # ATLAS: real work (funext/simp) then closes with one lemma -> suspect but NOT trivial,
    # so it must NOT be elevated to a blocker (the 2026-05-30 false-positive fix).
    work_ok = (work["detect"]["gold_name_verbatim_suspect"]
               and not work["detect"]["trivial_restatement"])
    # SEV1-A: a no-op `simp only []` must NOT save a bare restatement.
    noop_ok = res["positive_noop"]["detect"]["trivial_restatement"]
    # SEV1-B: a term-mode single-lemma restatement must be suspect + trivial.
    term_ok = (res["positive_term"]["detect"]["gold_name_verbatim_suspect"]
               and res["positive_term"]["detect"]["trivial_restatement"])
    # SEV1-B evasion: projection restatement must stay suspect+trivial.
    proj_ok = (res["positive_proj"]["detect"]["gold_name_verbatim_suspect"]
               and res["positive_proj"]["detect"]["trivial_restatement"])
    # SEV1-B false-positive: lambda construction must NOT be trivial.
    lambda_ok = not res["negative_lambda"]["detect"].get("trivial_restatement")
    ok = pos_ok and neg_ok and work_ok and noop_ok and term_ok and proj_ok and lambda_ok
    res["verdict"] = "PARAPHRASE_GATE_VALIDATED" if ok else "GATE_FAILS_GROUND_TRUTH"
    res["pos_ok"], res["neg_ok"], res["work_ok"] = pos_ok, neg_ok, work_ok
    res["noop_ok"], res["term_ok"] = noop_ok, term_ok
    res["proj_ok"], res["lambda_ok"] = proj_ok, lambda_ok
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--file", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.validate:
        r = run_validation()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        if args.out:
            Path(args.out).write_text(json.dumps(r, indent=2, ensure_ascii=False))
        return 0 if r["verdict"] == "PARAPHRASE_GATE_VALIDATED" else 1
    if args.file:
        txt = Path(args.file).read_text()
        d = detect_gold_name_verbatim(txt)
        c = independent_corpus_confirm(d.get("primary_cited"))
        in_ml = c.get("in_mathlib")
        print(json.dumps({"detect": d, "corpus_confirm": c,
                          "gold_name_verbatim_confirmed": bool(
                              d["trivial_restatement"] and in_ml),
                          "gold_name_verbatim_advisory": bool(
                              d["gold_name_verbatim_suspect"]
                              and not d["trivial_restatement"] and in_ml)},
                         indent=2, ensure_ascii=False))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
