#!/usr/bin/env python3
"""proof_route_fingerprint.py — Surface proof-route fingerprint extractor.

GP-235 §4 primitive validation step 1. Implements the SURFACE portion of the
proof-route fingerprint (§2A in the seam) from Lean source files. Does NOT
require running Lean — pure regex / AST-light parsing of tactic-script syntax.

The kernel_fingerprint (§2B — elaborated proof term constants + typeclass
instances + dependency_set) requires Lean tooling and is deferred to step 2.

The surface_fingerprint is a 4-tuple:
  tactic_family_sequence:  list of tactic-family tags in tactic-script order
  cited_constants:         sorted multiset of constant names cited in tactic args
  skeleton_kind:           direct | calc | induction | refine | term | unverified_stub
  normalization_path:      ordered sub-sequence of normalization tactics

Usage:
  proof_route_fingerprint.py --file <lean_file>                  # all theorems
  proof_route_fingerprint.py --file <lean_file> --theorem <name>  # one theorem
  proof_route_fingerprint.py --pair <file1> <theorem1> <file2> <theorem2>
      # extract both, compute distance
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any

# Tactic-family mapping. Surface tactic → family tag.
TACTIC_FAMILY = {
    # linear arithmetic
    "linarith": "linear_arith",
    "nlinarith": "linear_arith",
    "polyrith": "linear_arith",
    "omega": "linear_arith",
    "positivity": "linear_arith",
    # normalization
    "ring": "normalize",
    "ring_nf": "normalize",
    "norm_num": "normalize",
    "field_simp": "normalize",
    "push_cast": "normalize",
    "norm_cast": "normalize",
    "abel": "normalize",
    # simp family
    "simp": "simp",
    "simp_all": "simp",
    "simpa": "simp",
    "dsimp": "simp",
    # rewriting
    "rw": "rewrite",
    "rewrite": "rewrite",
    "rewriteAt": "rewrite",
    # decision procedures
    "decide": "decision_proc",
    "trivial": "decision_proc",
    "rfl": "decision_proc",
    # case analysis
    "cases": "case_split",
    "rcases": "case_split",
    "obtain": "case_split",
    "by_cases": "case_split",
    "match": "case_split",
    "split": "case_split",
    # introduction / construction
    "intro": "intro",
    "intros": "intro",
    "rintro": "intro",
    "constructor": "construct",
    "refine": "construct",
    "use": "construct",
    "exact": "construct",
    "apply": "construct",
    "exact_mod_cast": "construct",
    # induction
    "induction": "induction",
    "Nat.le_induction": "induction",
    # automation
    "aesop": "automation",
    "tauto": "automation",
    "tauto!": "automation",
    "decide!": "automation",
    "fun_prop": "automation",
    "measurability": "automation",
    "gcongr": "automation",
    "polyrith!": "automation",
    "hammer": "automation_hammer",
    # calc / chain
    "calc": "chain",
    "have": "intermediate",
    "show": "goal_rewrite",
    "change": "goal_rewrite",
    "suffices": "goal_rewrite",
    "let": "intermediate",
    "set": "intermediate",
    # filters / membership
    "filter_upwards": "filter",
    # contradiction
    "contradiction": "contradiction",
    "absurd": "contradiction",
    "exfalso": "contradiction",
    # generalization
    "generalize": "generalize",
    # finishing
    "trivially": "decision_proc",
    "sorry": "unverified_stub",
    "admit": "unverified_stub",
}

NORMALIZATION_TACTICS = {
    "ring", "ring_nf", "norm_num", "field_simp", "push_cast", "norm_cast", "abel"
}

# Regex helpers
THEOREM_RE = re.compile(
    r"^\s*(theorem|lemma|example|def|instance)\s+"
    r"(?P<name>[A-Za-z_][\w'.]*)"
    r"(?P<sig>[^:=]*(?:: (?:.|\n)+?)?)"
    r":=\s*(?P<body>.+?)(?=^\s*(?:theorem|lemma|example|def|instance|end|namespace)\b|\Z)",
    re.MULTILINE | re.DOTALL,
)


def parse_proof_body(body: str) -> dict[str, Any]:
    """Extract surface fingerprint from a tactic-script proof body."""
    body = body.strip()
    # Skeleton kind classification
    if "sorry" in body or "admit" in body:
        skeleton = "unverified_stub"
    elif body.startswith("by calc") or "\n  calc " in body or body.startswith("calc"):
        skeleton = "calc"
    elif "by induction" in body or "induction " in body:
        skeleton = "induction"
    elif body.startswith("by refine") or "refine " in body[:50]:
        skeleton = "refine"
    elif body.startswith("by exact") or body.startswith("by apply") or body.startswith("exact "):
        skeleton = "direct"
    elif body.startswith("by"):
        skeleton = "tactic_script"
    else:
        skeleton = "term"

    # Extract tactic tokens — tokenize the body, then map each to its family
    # Surface tactic tokens are typically lowercase identifiers immediately
    # after `by`, `;`, `<;>`, `\n  `, `· ` etc.
    tactic_token_re = re.compile(
        r"(?:^|\bby\s+|;\s*|<;>\s*|·\s*|=>\s*|\n\s+)"
        r"([a-zA-Z_][a-zA-Z0-9_.!?]*)"
    )
    tokens = tactic_token_re.findall(body)

    family_sequence = []
    last_family = None
    for tok in tokens:
        family = TACTIC_FAMILY.get(tok)
        if family is None:
            # Try dropping .! / ?
            base = tok.rstrip("!?")
            family = TACTIC_FAMILY.get(base)
        if family is not None:
            # Optionally collapse consecutive same-family tags
            if family != last_family:
                family_sequence.append(family)
                last_family = family

    # Cited constants — look for tactic-args inside [], (), or after `using`/`with`
    cited = []
    # `simp [foo, bar, baz]` style
    for m in re.finditer(r"\[([^\[\]]+)\]", body):
        inner = m.group(1)
        # Split by comma at top level
        for term in inner.split(","):
            term = term.strip()
            # Lemma references are identifiers (possibly dotted)
            id_match = re.match(r"^([A-Z][\w'.]*|[a-z][\w'.]*\.[A-Z][\w'.]*)\s*$", term)
            if id_match:
                cited.append(id_match.group(1))
    # `exact <name>`, `apply <name>`, `rw <name>`, etc.
    for m in re.finditer(
        r"\b(?:exact|apply|rw|rewrite|refine|simpa|using|specialize|have\s+\w+\s*:=)\s+([A-Z][\w'.]*)",
        body,
    ):
        cited.append(m.group(1))
    # `Nat.add_comm` / namespaced citations
    for m in re.finditer(r"\b([A-Z][\w]*\.[A-Z]?[\w'.]*)\b", body):
        c = m.group(1)
        if "." in c and len(c) < 80:
            cited.append(c)

    cited_multiset = sorted(cited)

    # Normalization path
    norm_path = [f for f in family_sequence if any(
        t in NORMALIZATION_TACTICS for t in TACTIC_FAMILY.items() if TACTIC_FAMILY.get(t) == f
    )]
    # Actually walk the original tactic tokens for normalization-tactic occurrences
    norm_path = []
    last_n = None
    for tok in tokens:
        base = tok.rstrip("!?")
        if base in NORMALIZATION_TACTICS and base != last_n:
            norm_path.append(base)
            last_n = base

    return {
        "tactic_family_sequence": family_sequence,
        "cited_constants": cited_multiset,
        "skeleton_kind": skeleton,
        "normalization_path": norm_path,
    }


def extract_theorem_proofs(file_text: str) -> list[dict[str, Any]]:
    """Parse all theorem/lemma/example declarations and their proof bodies."""
    out = []
    for m in THEOREM_RE.finditer(file_text):
        name = m.group("name")
        sig = m.group("sig")[:200].strip()
        body = m.group("body")
        # Trim trailing whitespace + final declarations bleeding in
        body = re.split(r"^\s*(?:theorem|lemma|example|def|instance|end|namespace)\b", body, maxsplit=1, flags=re.MULTILINE)[0]
        if not body.strip():
            continue
        fp = parse_proof_body(body)
        out.append({
            "name": name,
            "signature_preview": sig,
            "body_preview": body.strip()[:300],
            "surface_fingerprint": fp,
        })
    return out


def levenshtein(a: list[str], b: list[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(
                prev[j] + 1,        # delete
                cur[j-1] + 1,       # insert
                prev[j-1] + (0 if ca == cb else 1),  # substitute
            ))
        prev = cur
    return prev[-1]


def jaccard_distance(a: list[str], b: list[str]) -> float:
    sa = set(a)
    sb = set(b)
    if not sa and not sb:
        return 0.0
    return 1.0 - len(sa & sb) / max(len(sa | sb), 1)


def surface_distance(fp_a: dict, fp_b: dict, weights: tuple = (0.4, 0.3, 0.2, 0.1)) -> dict:
    """Compute distance between two surface fingerprints."""
    w1, w2, w3, w4 = weights
    seq_a = fp_a["tactic_family_sequence"]
    seq_b = fp_b["tactic_family_sequence"]
    lev_seq = levenshtein(seq_a, seq_b)
    lev_seq_norm = lev_seq / max(max(len(seq_a), len(seq_b)), 1)

    jac_consts = jaccard_distance(fp_a["cited_constants"], fp_b["cited_constants"])

    skel_diff = 0.0 if fp_a["skeleton_kind"] == fp_b["skeleton_kind"] else 1.0

    norm_a = fp_a["normalization_path"]
    norm_b = fp_b["normalization_path"]
    lev_norm = levenshtein(norm_a, norm_b)
    lev_norm_norm = lev_norm / max(max(len(norm_a), len(norm_b)), 1) if (norm_a or norm_b) else 0.0

    total = w1*lev_seq_norm + w2*jac_consts + w3*skel_diff + w4*lev_norm_norm
    return {
        "total_distance": round(total, 3),
        "components": {
            "tactic_seq_lev_normalized": round(lev_seq_norm, 3),
            "cited_constants_jaccard": round(jac_consts, 3),
            "skeleton_kind_diff": skel_diff,
            "normalization_path_lev_normalized": round(lev_norm_norm, 3),
        },
        "weights": weights,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="Lean file to fingerprint")
    ap.add_argument("--theorem", help="Specific theorem name to extract")
    ap.add_argument("--pair", nargs=4, metavar=("FILE1", "NAME1", "FILE2", "NAME2"),
                    help="Compare two theorems' fingerprints")
    ap.add_argument("--top", type=int, default=5, help="Show top-N theorems (default 5)")
    args = ap.parse_args()

    if args.pair:
        f1, n1, f2, n2 = args.pair
        text1 = Path(f1).read_text()
        text2 = Path(f2).read_text()
        ts1 = [t for t in extract_theorem_proofs(text1) if t["name"] == n1]
        ts2 = [t for t in extract_theorem_proofs(text2) if t["name"] == n2]
        if not ts1 or not ts2:
            print(f"ERROR: could not find theorem(s)")
            print(f"  {n1} in {f1}: {'found' if ts1 else 'NOT FOUND'}")
            print(f"  {n2} in {f2}: {'found' if ts2 else 'NOT FOUND'}")
            return 1
        fp1 = ts1[0]["surface_fingerprint"]
        fp2 = ts2[0]["surface_fingerprint"]
        print(json.dumps({
            "left":  {"name": n1, "fingerprint": fp1},
            "right": {"name": n2, "fingerprint": fp2},
            "distance": surface_distance(fp1, fp2),
        }, indent=2))
        return 0

    if args.file:
        text = Path(args.file).read_text()
        theorems = extract_theorem_proofs(text)
        if args.theorem:
            theorems = [t for t in theorems if t["name"] == args.theorem]
        print(f"# {len(theorems)} theorem(s) extracted from {args.file}\n")
        for t in theorems[:args.top]:
            print(f"## {t['name']}")
            print(f"   sig: {t['signature_preview'][:100]}")
            fp = t["surface_fingerprint"]
            print(f"   skeleton: {fp['skeleton_kind']}")
            print(f"   tactic_family_sequence ({len(fp['tactic_family_sequence'])}): {fp['tactic_family_sequence'][:15]}")
            print(f"   cited_constants ({len(fp['cited_constants'])}): {fp['cited_constants'][:10]}")
            print(f"   normalization_path: {fp['normalization_path']}")
            print()
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
