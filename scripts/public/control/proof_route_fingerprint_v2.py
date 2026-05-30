#!/usr/bin/env python3
"""proof_route_fingerprint_v2.py — augmented fingerprint with signature features.

After the v1 §4.5 grid-search revealed surface-only cannot pass §4.2 even at
overfit ceiling (75.9% < 80% threshold), this v2 adds signature-level features
that don't require running Lean:

  - target_type_head: the head symbol of the lemma's conclusion type
    (e.g., "Eq", "LE.le", "Continuous", "Measurable", "Summable")
  - signature_identifier_set: sorted multiset of identifiers in the signature
  - namespace_path: surrounding namespace chain (from file path + scope hints)

Distance is augmented with two new axes (statement features) that proxy
SIGNATURE similarity:

  d(f, g) := w1 · LevDist(tactic_family_seq)
          +  w2 · JaccardDist(cited_constants)
          +  w3 · (skeleton_kind != )
          +  w4 · LevDist(normalization_path)
          +  w5 · (target_type_head != )
          +  w6 · JaccardDist(signature_identifier_set)

Weights default to (0.25, 0.25, 0.15, 0.05, 0.15, 0.15) — sums to 1.0.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from proof_route_fingerprint import (  # type: ignore
    parse_proof_body, levenshtein, jaccard_distance,
    extract_theorem_proofs as _v1_extract,
)


def extract_signature_features(file_text: str, theorem_name: str) -> dict[str, Any]:
    """Parse the lemma signature (before `:= by` or `:=`) and extract
    statement-level features. Operates on file text + theorem name (rather
    than the parsed body — these features come from the SIGNATURE)."""
    # Find the declaration block: from `^[theorem|lemma|...] <name>` until the
    # first `:= ` (not `:=` inside types).
    decl_re = re.compile(
        rf"^\s*(?:theorem|lemma|example|def|instance|noncomputable\s+def)\s+"
        rf"(?:@\[[^\]]+\]\s+)?{re.escape(theorem_name)}(?=\s|\(|\{{|:|$)",
        re.MULTILINE,
    )
    m = decl_re.search(file_text)
    if not m:
        return {
            "target_type_head": "?",
            "signature_identifier_set": [],
            "namespace_path": [],
            "found": False,
        }
    # Walk forward to find the `:=` that ends the signature
    after = file_text[m.end():]
    # Strip until `:=` (but `:=` inside `{` ... `}` should be skipped)
    sig_chars = []
    depth = 0
    i = 0
    while i < len(after):
        ch = after[i]
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth -= 1
        if depth == 0 and after[i:i+2] == ":=":
            break
        sig_chars.append(ch)
        i += 1
    signature_text = "".join(sig_chars)

    # Extract target_type_head: find the top-level `:` (depth=0) — what's
    # after it is the conclusion type. Head symbol = first capitalized
    # identifier (or known operator).
    depth = 0
    conclusion_start = None
    last_colon = None
    for j, ch in enumerate(signature_text):
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth -= 1
        if depth == 0 and ch == ":":
            last_colon = j
    if last_colon is not None:
        conclusion = signature_text[last_colon+1:].strip()
    else:
        conclusion = signature_text.strip()

    # target_type_head: detect common Mathlib type heads
    type_head = "?"
    head_patterns = [
        (r"\bContinuous\b", "Continuous"),
        (r"\bContinuousAt\b", "ContinuousAt"),
        (r"\bContinuousOn\b", "ContinuousOn"),
        (r"\bMeasurable\b", "Measurable"),
        (r"\bAEMeasurable\b", "AEMeasurable"),
        (r"\bIntegrable\b", "Integrable"),
        (r"\bSummable\b", "Summable"),
        (r"\bDifferentiable\b", "Differentiable"),
        (r"\bMonotone\b", "Monotone"),
        (r"\bAntitone\b", "Antitone"),
        (r"\bBijective\b", "Bijective"),
        (r"\bInjective\b", "Injective"),
        (r"\bSurjective\b", "Surjective"),
        (r"=", "Eq"),  # any equation
        (r"≤", "LE.le"),
        (r"≥", "GE.ge"),
        (r"<", "LT.lt"),
        (r">", "GT.gt"),
        (r"↔", "Iff"),
        (r"→", "Implies"),
        (r"∀", "Forall"),
        (r"∃", "Exists"),
    ]
    for pat, label in head_patterns:
        if re.search(pat, conclusion):
            type_head = label
            break

    # signature_identifier_set: all capitalized identifiers in the signature
    # (proxy for "what types/objects does this lemma talk about")
    identifiers = set()
    for m_id in re.finditer(r"\b([A-Z][\w'.]*)\b", signature_text):
        s = m_id.group(1)
        # Skip if it's a single-letter type variable (E, F, G, etc.) — those
        # are noise, not content signals.
        if len(s) > 1:
            identifiers.add(s)
    identifier_list = sorted(identifiers)[:30]  # cap at 30

    # namespace_path: extract from `namespace X` declarations BEFORE the theorem
    # in the file, plus from the theorem name itself if it contains dots
    namespace_decls = []
    for m_ns in re.finditer(r"^\s*namespace\s+([\w'.]+)\b", file_text[:m.start()], re.MULTILINE):
        namespace_decls.append(m_ns.group(1))
    # Also pull dotted prefix from theorem name (e.g., `Real.foo` → "Real")
    if "." in theorem_name:
        dotted = theorem_name.rsplit(".", 1)[0]
        if dotted not in namespace_decls:
            namespace_decls.append(dotted)

    return {
        "target_type_head": type_head,
        "signature_identifier_set": identifier_list,
        "namespace_path": namespace_decls,
        "conclusion_preview": conclusion[:200],
        "found": True,
    }


def augmented_distance(
    fp_a: dict, fp_b: dict,
    sig_a: dict, sig_b: dict,
    weights: tuple = (0.25, 0.25, 0.15, 0.05, 0.15, 0.15),
) -> dict:
    """6-axis distance including signature features."""
    w1, w2, w3, w4, w5, w6 = weights
    seq_a = fp_a["tactic_family_sequence"]
    seq_b = fp_b["tactic_family_sequence"]
    lev_seq = levenshtein(seq_a, seq_b) / max(max(len(seq_a), len(seq_b)), 1)
    jac_consts = jaccard_distance(fp_a["cited_constants"], fp_b["cited_constants"])
    skel_diff = 0.0 if fp_a["skeleton_kind"] == fp_b["skeleton_kind"] else 1.0
    norm_a = fp_a["normalization_path"]
    norm_b = fp_b["normalization_path"]
    lev_norm = (levenshtein(norm_a, norm_b) / max(max(len(norm_a), len(norm_b)), 1)) if (norm_a or norm_b) else 0.0
    type_diff = 0.0 if sig_a["target_type_head"] == sig_b["target_type_head"] else 1.0
    jac_ids = jaccard_distance(sig_a["signature_identifier_set"], sig_b["signature_identifier_set"])
    total = w1*lev_seq + w2*jac_consts + w3*skel_diff + w4*lev_norm + w5*type_diff + w6*jac_ids
    return {
        "total_distance": round(total, 3),
        "components": {
            "tactic_seq_lev": round(lev_seq, 3),
            "cited_constants_jaccard": round(jac_consts, 3),
            "skeleton_diff": skel_diff,
            "normalization_path_lev": round(lev_norm, 3),
            "target_type_head_diff": type_diff,
            "signature_identifier_jaccard": round(jac_ids, 3),
        },
        "weights": weights,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="Lean file to fingerprint")
    ap.add_argument("--theorem", help="Specific theorem name")
    args = ap.parse_args()

    if args.file and args.theorem:
        text = Path(args.file).read_text()
        sig = extract_signature_features(text, args.theorem)
        proofs = _v1_extract(text)
        proof = next((p for p in proofs if p["name"] == args.theorem), None)
        result = {
            "name": args.theorem,
            "surface_fingerprint": proof["surface_fingerprint"] if proof else None,
            "signature_features": sig,
        }
        print(json.dumps(result, indent=2))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
