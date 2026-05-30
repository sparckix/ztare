#!/usr/bin/env python3
"""Typed-first patch proposer — Codex's 10x architecture (2026-05-06).

Old approach (refuted): LLM proposes a novel theorem → typed filter rejects
                       most → 0/22 closure utility because LLM invents
                       non-existent objects, ignores endpoint exposure,
                       proposes already-falsified scalar shortcuts.

10x approach (this script):
  1. Pick a target open obligation from the workmap.
  2. Resolve its fields against the actual Lean spine (declared types,
     parent structures, existing instances).
  3. For each field, find NEARBY EXISTING THEOREMS that reference it,
     plus NEARBY EXISTING FALSIFIER GUARDS already in the spine.
  4. Hand the LLM a strictly-typed prompt: "Here is the open obligation,
     here are 5-10 nearby resolved theorems + 3-5 falsifier guards.
     Propose a PATCH: (a) extend one of the existing theorems to cover
     the obligation's missing case, OR (b) construct a Lean falsifier
     of a specific easy sub-case. Output ONLY a single Lean file
     referring exclusively to declarations in the resolved set."
  5. lake build the patch. If green: real progress. If red: feed error
     back, max 3 revisions.

Reference pattern: the beat/backscatter guard from NS Track B —
a typed candidate that either patches an existing theorem or builds
a Lean falsifier, compiler-verifiable.

Usage:
    python scripts/public/lean/typed_patch_proposer.py \\
        --obligation TrackBProfileLipschitzControlObligation \\
        --max-revisions 3
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LEAN_DIR = REPO / "ztare_proofs" / "ZtareProofs"
WORKMAP_PATH = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "ns_trackb_instantiation_workmap.json"
)
DECL_INDEX_PATH = REPO / "analytics" / "public" / "queries" / "lean" / "lean_decl_index.json"


def load_workmap_obligation(name: str) -> dict | None:
    if not WORKMAP_PATH.exists():
        print(f"missing {WORKMAP_PATH}")
        return None
    workmap = json.loads(WORKMAP_PATH.read_text())
    items = workmap if isinstance(workmap, list) else workmap.get("structures", [])
    for ob in items:
        if ob.get("name") == name or ob.get("structure") == name:
            return ob
    return None


def load_decl_index() -> dict:
    if not DECL_INDEX_PATH.exists():
        sys.path.insert(0, str(REPO))
        import lean_decl_index as ldi
        idx = ldi.build_index(ldi.LEAN_DIR)
        DECL_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        DECL_INDEX_PATH.write_text(json.dumps(idx, indent=2))
        return idx
    return json.loads(DECL_INDEX_PATH.read_text())


def resolve_fields(obligation: dict, decl_index: dict) -> list[dict]:
    """For each field, look up its declared type in the spine."""
    decls = decl_index.get("decls", {})
    resolved = []
    for fld in obligation.get("fields", []):
        name = fld.get("name") if isinstance(fld, dict) else fld
        ftype = fld.get("type", "?") if isinstance(fld, dict) else "?"
        # Find what decls match
        matches = decls.get(name, [])
        resolved.append({
            "field_name": name,
            "field_type": ftype,
            "decl_matches": matches[:3],  # cap
        })
    return resolved


def _camel_split(name: str) -> set[str]:
    parts = re.findall(r"[A-Z][a-z]*|[a-z]+|[0-9]+", name)
    return {p.lower() for p in parts if len(p) >= 4}


def find_nearby_theorems(obligation: dict, decl_index: dict,
                          n_nearby: int = 10) -> list[dict]:
    """Find existing theorems via three search axes:
       (1) field-name hits, (2) obligation-name camelCase token hits,
       (3) theorems from the obligation's own source file."""
    field_names = set()
    for fld in obligation.get("fields", []):
        name = fld.get("name") if isinstance(fld, dict) else fld
        if name:
            field_names.add(name)
    obligation_name = obligation.get("name") or obligation.get("structure", "")
    obligation_file = obligation.get("file", "")
    obligation_tokens = _camel_split(obligation_name)
    field_names.add(obligation_name)

    decl_re = re.compile(
        r"^(theorem|lemma|def|structure|class|instance|abbrev)\s+([A-Za-z_][A-Za-z0-9_]*)",
        re.MULTILINE,
    )
    nearby = []
    for path in LEAN_DIR.glob("ns_*.lean"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        in_obligation_file = (path.stem == obligation_file)
            # Find decl positions; take a bounded window after as the
            # signature/body.  A too-short window hides exactly the endpoint
            # theorem names and falsifier arguments the patcher must reuse.
        positions = [(m.start(), m.group(1), m.group(2)) for m in decl_re.finditer(text)]
        positions.append((len(text), "", ""))
        for i in range(len(positions) - 1):
            start, kind, tname = positions[i]
            end = min(positions[i + 1][0], start + 1000)
            sig = text[start:end].strip()
            # Score across three axes
            field_hits = sum(1 for f in field_names if f in sig)
            tok_hits = sum(1 for t in obligation_tokens
                            if t in sig.lower() or t in tname.lower())
            file_bonus = 2 if in_obligation_file else 0
            total = field_hits + tok_hits + file_bonus
            if total > 0:
                nearby.append({
                    "name": tname, "file": path.stem, "signature": sig[:650],
                    "field_hits": field_hits, "token_hits": tok_hits,
                    "file_bonus": file_bonus, "total": total,
                })
    nearby.sort(key=lambda r: -r["total"])
    return nearby[:n_nearby]


def load_obligation_source_file(obligation: dict, max_chars: int = 14000) -> str:
    """Pull a target-centered slice of the obligation's own source file.

    The old implementation returned the file head. That misses exactly the
    context theorem generation needs when a file is long: the target structure,
    its companion `Satisfied` predicate, and nearby `Falsifier` eliminators.
    Keep this extractor substrate-agnostic by centering on the obligation name
    and then extending to nearby proof-surface keywords when present.
    """
    obligation_file = obligation.get("file", "")
    obligation_name = obligation.get("name") or obligation.get("structure", "")
    if not obligation_file:
        return ""
    path = LEAN_DIR / f"{obligation_file}.lean"
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if not obligation_name or obligation_name not in text:
        return text[:max_chars]

    target = text.find(obligation_name)
    start = max(0, target - max_chars // 3)
    end = min(len(text), target + (2 * max_chars) // 3)

    for marker in (
        f"{obligation_name}Satisfied",
        f"{obligation_name}Falsifier",
        f"no_{obligation_name}",
        "Falsifier",
    ):
        marker_at = text.find(marker, target)
        if marker_at != -1:
            end = min(len(text), max(end, marker_at + max_chars // 3))

    if end - start > max_chars:
        end = start + max_chars
    return text[start:end]


def find_falsifier_guards(obligation: dict, n_guards: int = 5) -> list[dict]:
    """Find existing Lean files that look like falsifier guards related to obligation."""
    obligation_lower = (obligation.get("name", "") or
                          obligation.get("structure", "")).lower()
    keywords = []
    if "profile" in obligation_lower: keywords.append("profile")
    if "lipschitz" in obligation_lower: keywords.append("lipschitz")
    if "tax" in obligation_lower: keywords.append("tax")
    if "lsc" in obligation_lower: keywords.append("lsc")
    if "shell" in obligation_lower: keywords.append("shell")
    keywords.extend(["falsifier", "guard", "no_survivor", "exclusion"])
    out = []
    for path in LEAN_DIR.glob("ns_*.lean"):
        if any(kw in path.stem.lower() for kw in keywords):
            try:
                head = path.read_text(encoding="utf-8")[:600]
            except OSError:
                continue
            out.append({"file": path.stem, "head_preview": head[:300]})
    return out[:n_guards]


PATCH_PROMPT_TEMPLATE = """You are working on closing the NS Track B Clay closure obligation `{obligation_name}`. Your job is to propose a CONCRETE LAKE-CHECKABLE PATCH.

This is NOT a "novel theorem nomination" task. Past novel-theorem prompting produced 0/22 closure utility because LLMs invented non-existent objects, ignored endpoint exposure, and proposed scalar shortcuts already ruled out by existing counterexample guards.

Your output must be ONE of two patch types:

  TYPE A — extend an existing theorem in the nearby corpus to cover the obligation's missing case
  TYPE B — construct a Lean falsifier (a `theorem no_X : ¬ X := by ...`) for a specific sub-case of the obligation

Both types must:
  - Reference ONLY declarations in the "resolved fields" + "nearby theorems" sets below (no inventing names)
  - Produce ONE Lean file (with imports, namespace, single theorem)
  - Be lake-buildable (we will run `lake build` immediately on your output)

# Open obligation

  Name: {obligation_name}
  Leverage score: {leverage}
  Downstream users: {n_downstream}
  Number of fields: {n_fields}

# Resolved fields (from typed lookup against the actual Lean spine)

{resolved_fields}

# Nearby existing theorems (sorted by field-name hit count)

{nearby_theorems}

# Existing falsifier-guard files for reference

{falsifier_guards}

# Obligation source file (target-centered slice — type definitions, constructors)

```lean
{obligation_source}
```

# Instructions

1. Pick ONE patch type (A or B). State which.
2. Write the Lean file. Include `import` lines for whatever modules contain the declarations you reference.
3. Do NOT use `sorry`, `admit`, `axiom`, or `native_decide`.
4. Do NOT restate an existing theorem under the same name, and do NOT add a narrow special-case theorem when an existing falsifier guard already proves exactly the same obstruction.
5. Do NOT return a decorative negation wrapper of the form `theorem no_X (...)(h : ¬ existing_positive_endpoint) : False := h (existing_theorem ...)`; that is compiler-green but not proof-spine progress.
6. If you cannot produce a lake-buildable patch from the resolved set, output `# CANNOT PATCH` followed by a one-paragraph diagnosis of what's missing in the resolved set.

Do not reason aloud. Do not include scratch analysis. Return exactly one of:

  - a single ```lean fenced block containing the patch; or
  - `# CANNOT PATCH` followed by one paragraph.
"""


def call_gemini(prompt, max_tokens=8000):
    if not os.environ.get("GEMINI_API_KEY"):
        return "ERROR: no GEMINI_API_KEY"
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model="gemini-3-pro-preview", contents=prompt,
        config={"max_output_tokens": max_tokens},
    )
    parts = []
    for cand in response.candidates or []:
        if cand.content and cand.content.parts:
            for p in cand.content.parts:
                if hasattr(p, "text") and p.text:
                    parts.append(p.text)
    return "\n".join(parts) if parts else "(empty)"


def extract_lean_block(text: str) -> str | None:
    m = re.search(r"```lean\s*\n([\s\S]*?)\n\s*```", text)
    if m:
        return m.group(1).strip()
    # Some model responses truncate after an opening fence. Treat the suffix as
    # a candidate Lean block so the caller can still run deterministic guards.
    m = re.search(r"```lean\s*\n([\s\S]*)\Z", text)
    return m.group(1).strip() if m else None


def extract_top_level_decl_names(lean_src: str) -> list[str]:
    decl_re = re.compile(
        r"^(?:private\s+)?"
        r"(theorem|lemma|def|structure|class|instance|abbrev|inductive)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)",
        re.MULTILINE,
    )
    return [m.group(2) for m in decl_re.finditer(lean_src)]


def duplicate_decl_names(lean_src: str, decl_index: dict) -> list[str]:
    decls = decl_index.get("decls", {})
    return [name for name in extract_top_level_decl_names(lean_src)
            if name in decls]


def decorative_negation_wrapper(lean_src: str) -> bool:
    """Cheap anti-theater guard for compiler-green but non-progress patches.

    The common failure mode is a theorem of the form
    `theorem no_X (...)(h : ¬ target) : False := h (existing_theorem ...)`.
    It is true and lake-buildable, but only restates an already-exposed
    positive endpoint as a negated falsifier.  Keep this heuristic general:
    it does not know NS names, only the proof shape.
    """
    normalized = re.sub(r"\s+", " ", lean_src)
    return bool(
        re.search(r"\(\s*h\s*:\s*¬", normalized)
        and re.search(r":\s*False\s*:?=\s*(by\s*)?h\s*\(", normalized)
    )


def lake_build_check(lean_src: str, slug: str) -> dict:
    """Write to ztare_proofs and run lake build."""
    sys.path.insert(0, str(REPO / "src"))
    from src.ztare.gates.lean_proof_gate import write_lean_target, compile_lean
    proofs_root = REPO / "ztare_proofs"
    target = write_lean_target(lean_src, slug, proofs_root)
    return compile_lean(target, proofs_root, timeout_seconds=120)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--obligation", required=True,
                    help="open obligation name from workmap")
    ap.add_argument("--max-revisions", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true",
                    help="don't actually run lake")
    ap.add_argument("--out-dir", type=Path,
                    default=REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries" / "typed_patch_runs")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== typed-first patch proposer (Codex 10x architecture) ===")
    print(f"  target obligation: {args.obligation}")

    obligation = load_workmap_obligation(args.obligation)
    if not obligation:
        print(f"  not found in workmap")
        return 1
    print(f"  obligation has {obligation.get('n_fields', '?')} fields, "
          f"leverage={obligation.get('leverage_score', '?')}")

    print(f"\n[1] resolving fields against decl index...")
    decl_index = load_decl_index()
    resolved = resolve_fields(obligation, decl_index)
    print(f"  {len(resolved)} fields, "
          f"{sum(1 for r in resolved if r['decl_matches'])} resolved to decls")

    print(f"\n[2] finding nearby existing theorems...")
    nearby = find_nearby_theorems(obligation, decl_index, n_nearby=12)
    print(f"  {len(nearby)} theorems with field-name hits")

    print(f"\n[3] finding falsifier-guard files...")
    guards = find_falsifier_guards(obligation, n_guards=5)
    print(f"  {len(guards)} candidate guard files")

    print(f"\n[3.5] loading obligation source file (for type definitions)...")
    obligation_source = load_obligation_source_file(obligation, max_chars=14000)
    print(f"  loaded {len(obligation_source)} chars from {obligation.get('file', '?')}.lean")

    # Build the prompt
    prompt = PATCH_PROMPT_TEMPLATE.format(
        obligation_name=args.obligation,
        leverage=obligation.get("leverage_score", "?"),
        n_downstream=obligation.get("n_downstream_users", "?"),
        n_fields=obligation.get("n_fields", "?"),
        resolved_fields="\n".join(
            f"  - {r['field_name']} : {r['field_type']}\n"
            f"    decl matches: {[m['file'] + ':' + m['kind'] for m in r['decl_matches']]}"
            for r in resolved),
        nearby_theorems="\n".join(
            f"  [score={t['total']} fields={t['field_hits']} tokens={t['token_hits']} same_file={t['file_bonus']>0}] {t['name']} (in {t['file']}):\n"
            f"    {t['signature'][:650]}"
            for t in nearby),
        falsifier_guards="\n".join(
            f"  {g['file']}: {g['head_preview'][:150]}"
            for g in guards),
        obligation_source=obligation_source,
    )

    (args.out_dir / f"{args.obligation}_prompt.txt").write_text(prompt)
    print(f"  prompt size: {len(prompt)} chars")

    if args.dry_run:
        print(f"\n[dry-run] would call Gemini + lake build; skipping")
        return 0

    print(f"\n[4] calling Gemini for typed patch...")
    response = call_gemini(prompt)
    (args.out_dir / f"{args.obligation}_response.md").write_text(response)
    print(f"  response: {len(response)} chars")

    if "# CANNOT PATCH" in response:
        print(f"\n  Gemini reported CANNOT PATCH — apparatus correctly refused")
        print(f"\n  diagnosis preview:")
        diag = response.split("# CANNOT PATCH", 1)[1][:500]
        print(diag)
        return 0

    lean_src = extract_lean_block(response)
    if not lean_src:
        print(f"  no Lean block in response; treating as UNVERIFIABLE")
        log_path = args.out_dir / f"{args.obligation}_log.json"
        log_path.write_text(json.dumps({
            "obligation": args.obligation,
            "n_resolved_fields": sum(1 for r in resolved if r["decl_matches"]),
            "n_nearby_theorems": len(nearby),
            "n_falsifier_guards": len(guards),
            "final_verdict": "UNVERIFIABLE",
            "n_attempts": 1,
            "history": [{
                "attempt": 0,
                "compiled": False,
                "no_lean_block": True,
                "response_preview": response[:1000],
            }],
        }, indent=2))
        print(f"  log: {log_path}")
        return 1
    duplicates = duplicate_decl_names(lean_src, decl_index)
    if duplicates:
        print("  duplicate top-level declaration(s) in response; "
              "treating as UNVERIFIABLE before lake build")
        print(f"  duplicates: {duplicates}")
        log_path = args.out_dir / f"{args.obligation}_log.json"
        log_path.write_text(json.dumps({
            "obligation": args.obligation,
            "n_resolved_fields": sum(1 for r in resolved if r["decl_matches"]),
            "n_nearby_theorems": len(nearby),
            "n_falsifier_guards": len(guards),
            "final_verdict": "UNVERIFIABLE",
            "n_attempts": 1,
            "history": [{
                "attempt": 0,
                "compiled": False,
                "duplicate_decl_names": duplicates,
                "response_preview": response[:1000],
            }],
        }, indent=2))
        print(f"  log: {log_path}")
        return 1
    print(f"  extracted Lean patch ({len(lean_src)} chars)")

    print(f"\n[5] lake build verification...")
    slug = f"typed_patch_{args.obligation.lower()[:30]}"
    history = []
    current_src = lean_src
    for attempt in range(args.max_revisions + 1):
        try:
            result = lake_build_check(current_src, slug)
        except Exception as e:
            print(f"  attempt {attempt}: lake build raised {type(e).__name__}: {e}")
            history.append({"attempt": attempt, "raised": str(e)})
            break
        compiled = result.get("compiled", False)
        history.append({
            "attempt": attempt,
            "compiled": compiled,
            "exit_code": result.get("exit_code"),
            "stderr_tail": (result.get("stderr") or "")[-1000:],
        })
        # Non-triviality check: patch must contain at least one theorem/lemma
        has_real_content = bool(re.search(
            r"\b(theorem|lemma|def|structure|instance)\s+\w",
            current_src))
        if compiled and not has_real_content:
            print(f"  attempt {attempt}: lake build green BUT patch is degenerate "
                  f"(no theorem/lemma/def). Treating as failed.")
            history[-1]["compiled"] = False
            history[-1]["degenerate"] = True
            compiled = False
        if compiled and decorative_negation_wrapper(current_src):
            print(f"  attempt {attempt}: lake build green BUT patch is a "
                  "decorative negation wrapper. Treating as failed.")
            history[-1]["compiled"] = False
            history[-1]["decorative_negation_wrapper"] = True
            compiled = False
        if compiled:
            print(f"\n  *** ATTEMPT {attempt} VERIFIED — patch lake-builds ***")
            break
        else:
            print(f"  attempt {attempt} failed (exit={result.get('exit_code')})")
            if attempt >= args.max_revisions:
                break
            # Revise via LLM — INCLUDE ORIGINAL CONTEXT so it doesn't degenerate
            revision_prompt = f"""ORIGINAL TASK (do not lose this context):

{prompt[:6000]}

Your prior patch attempt was:

```lean
{current_src[:3000]}
```

It failed lake build with:

```
{result.get('stderr', '')[:1500]}
```

Revise the patch. Same constraints: only reference declarations in the resolved set; no sorry/admit/axiom/native_decide; MUST contain at least one `theorem`, `lemma`, or `def` declaration (not just comments). Return the revised patch in a single ```lean fenced block."""
            revised = call_gemini(revision_prompt)
            new_src = extract_lean_block(revised)
            if not new_src:
                print(f"  revision had no Lean block; aborting")
                break
            revised_duplicates = duplicate_decl_names(new_src, decl_index)
            if revised_duplicates:
                print("  revision repeated existing top-level declaration(s); "
                      "aborting before lake build")
                history.append({
                    "attempt": attempt + 1,
                    "compiled": False,
                    "duplicate_decl_names": revised_duplicates,
                })
                break
            current_src = new_src

    log_path = args.out_dir / f"{args.obligation}_log.json"
    log_path.write_text(json.dumps({
        "obligation": args.obligation,
        "n_resolved_fields": sum(1 for r in resolved if r["decl_matches"]),
        "n_nearby_theorems": len(nearby),
        "n_falsifier_guards": len(guards),
        "final_verdict": ("VERIFIED" if any(h.get("compiled") for h in history)
                           else "UNVERIFIABLE"),
        "n_attempts": len(history),
        "history": history,
    }, indent=2))
    print(f"\nlog: {log_path}")

    final = "VERIFIED" if any(h.get("compiled") for h in history) else "UNVERIFIABLE"
    print(f"\n=== FINAL: {final} ===")
    if final == "VERIFIED":
        print(f"  This is the 10x route working: typed-first → lake-checkable patch.")
    else:
        print(f"  Still UNVERIFIABLE after {len(history)} attempts.")
        print(f"  Last error tail:")
        last = history[-1].get("stderr_tail", "")
        print(f"    {last[-400:]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
