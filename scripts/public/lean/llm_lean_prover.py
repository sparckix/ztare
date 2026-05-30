#!/usr/bin/env python3
"""GP-216f scale-8 — Option D: long-context LLM-as-prover with Lean verification.

Approach (per principal direction 2026-05-05): instead of LoRA fine-tuning DSP-V2
on 176 closed NS theorems (lossy parameter approximation), use a 1M-context LLM
(Claude Opus 4.7) with all closed NS theorems as in-context examples (lossless
preservation of corpus). Verify each generated proof candidate via `lake build`.

# The killer move

`lake build` is the ground-truth verifier. The LLM either produces a proof that
compiles in real Lean 4 (with full project context, all imports, all dependencies)
or doesn't. This eliminates hallucination — the model can't claim a proof works
unless Lean agrees.

# Workflow

For each open obligation in the closure-tree:
  1. Extract the obligation's signature + parent file's imports
  2. Build a long-context prompt:
     - Lean 4 system prompt for NS Track B
     - All 176 closed NS theorems (signatures + proofs) as in-context examples
     - The target obligation's signature
     - Instruction: produce a proof
  3. Spawn a Claude Code subagent to generate N candidate proofs (vary slightly)
  4. For each candidate: write to temp .lean file in ZtareProofs/, lake build
  5. If any candidate compiles → record as CLOSED; submit the proof
  6. If none compile → record as FAILED with error excerpts (could feed back for retry)
  7. Save outcomes per-obligation

# Status: v1

Ships v1 today. Not bulletproof. Known limitations:
- Subagent prompt size cap may force corpus subsetting (handled below)
- Lake build is single-threaded, ~5-15s per attempt
- No retry-with-error-feedback loop yet (queued for v2 if v1 closure rate ≥30%)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LEAN_DIR = REPO / "ztare_proofs" / "ZtareProofs"
LEAN_PROJECT = REPO / "ztare_proofs"
GRAPH = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "ns_trackb_artifact_graph.json"
)
RECEIPT = "ns_file:ns_gp216_bridge_composition_receipt"
OUT = REPO / "analytics" / "public" / "queries" / "lean" / "llm_lean_prover_results.json"


# ── Lean source parsing ─────────────────────────────────────────────────


THEOREM_RE = re.compile(
    r"^(theorem|lemma)\s+([A-Za-z_][A-Za-z0-9_]*)\s*"
    r"((?:[^:=]|:[^=])*?)"
    r":=\s*"
    r"(.*?)"
    r"(?=\n^(?:theorem|lemma|def|structure|class|instance|namespace|end\s|/-|--))",
    re.DOTALL | re.MULTILINE,
)


def strip_comments(text: str) -> str:
    chars = list(text)
    i = 0
    depth = 0
    while i < len(chars):
        if depth == 0 and i + 1 < len(chars) and chars[i] == "-" and chars[i+1] == "-":
            chars[i] = " "; chars[i+1] = " "; i += 2
            while i < len(chars) and chars[i] != "\n":
                chars[i] = " "; i += 1
            continue
        if i + 1 < len(chars) and chars[i] == "/" and chars[i+1] == "-":
            depth += 1; chars[i] = " "; chars[i+1] = " "; i += 2; continue
        if depth > 0:
            if i + 1 < len(chars) and chars[i] == "-" and chars[i+1] == "/":
                depth -= 1; chars[i] = " "; chars[i+1] = " "; i += 2; continue
            if chars[i] != "\n":
                chars[i] = " "
            i += 1; continue
        i += 1
    return "".join(chars)


def extract_closed_theorems(receipt_tree_files: set[str]) -> list[dict]:
    """Walk receipt-tree files, extract (kind, name, signature, proof) for closed theorems."""
    examples = []
    for name in receipt_tree_files:
        path = LEAN_DIR / f"{name}.lean"
        if not path.exists(): continue
        text = path.read_text(encoding="utf-8")
        cleaned = strip_comments(text)
        for m in THEOREM_RE.finditer(cleaned):
            kind = m.group(1)
            tname = m.group(2)
            sig = m.group(3).strip()
            body = m.group(4).strip()
            if "sorry" in body.lower() or "admit" in body.lower(): continue
            if not body or len(body) < 5: continue
            examples.append({
                "kind": kind, "name": tname, "signature": sig, "proof": body,
                "source_file": name,
            })
    return examples


def get_open_obligations_with_signatures(graph: dict, receipt_tree: set[str]) -> list[dict]:
    """Open theorem-kind obligations that have a real type signature we can target."""
    decls = [n for n in graph["@graph"] if n.get("@type") == "ns_lean_decl"]
    out = []
    for d in decls:
        if d.get("status") != "open_obligation": continue
        if d.get("kind") not in ("theorem", "lemma"): continue  # focus on provable theorems
        if d.get("file", "").replace("ns_file:", "") not in receipt_tree: continue
        out.append(d)
    return out


def build_prompt(obligation: dict, closed_examples: list[dict], file_imports: list[str], n_examples: int = 30) -> str:
    """Build the in-context-learning prompt. Selects N examples from closed corpus."""
    # Pick examples by source-file proximity first, then random
    same_file = [e for e in closed_examples if e["source_file"] == obligation.get("file", "").replace("ns_file:", "")]
    others = [e for e in closed_examples if e not in same_file]
    selected = same_file[:n_examples//2] + others[:n_examples - len(same_file[:n_examples//2])]
    selected = selected[:n_examples]

    examples_block = "\n\n".join(
        f"-- Closed: {e['name']} (in {e['source_file']})\n"
        f"{e['kind']} {e['name']} {e['signature']} := {e['proof']}"
        for e in selected
    )

    target_name = obligation.get("name", "<unnamed>")
    target_kind = obligation.get("kind", "theorem")
    # Read raw type signature from source file
    target_file = LEAN_DIR / f"{obligation.get('file', '').replace('ns_file:', '')}.lean"
    target_signature = ""
    if target_file.exists():
        ftext = target_file.read_text()
        # Find the declaration in source
        sig_m = re.search(
            rf"(?:theorem|lemma)\s+{re.escape(target_name)}\s*((?:[^:=]|:[^=])*?):=",
            ftext
        )
        if sig_m:
            target_signature = sig_m.group(1).strip()

    return f"""You are a Lean 4 theorem prover for the NS Track B proof spine.

The NS Track B project proves regularity properties of Navier-Stokes equations through a
custom proof framework with structures like LeraySelfTaxProfilePriceStream, BoundChain,
TrackBClayClosureObligation, etc. Below are {len(selected)} CLOSED theorems from the
project — they compile and are correct. Use them as the canonical proof style for NS work.

## File context (imports for the target's parent file)

{chr(10).join(file_imports)}

## Closed theorems from NS Track B corpus (in-context examples)

{examples_block}

## Target obligation

Prove the following in the same NS Track B style. Output ONLY the proof body (everything
that goes after `:=`). Do NOT include the theorem keyword, name, or signature — only the proof.

```
{target_kind} {target_name} {target_signature} :=
```

If the proof requires a specific tactic or lemma you don't see in the closed examples,
make a best-effort attempt with `by` tactics that mirror the most-similar closed example.

OUTPUT FORMAT: a single Lean 4 proof body. Start with `by` if using tactic mode, or with a
term-mode proof. Nothing else. No markdown, no commentary.
"""


def verify_proof(target_name: str, target_signature: str, proof_body: str, parent_file: Path) -> dict:
    """Write a candidate proof to a temp test file in the Lean project, run lake build, return result."""
    # Build a self-contained test module that imports the parent file's deps + adds the candidate
    test_module_name = f"ns_llm_test_{abs(hash(target_name)) % (10**8)}"
    test_path = LEAN_DIR / f"{test_module_name}.lean"

    # Read parent file imports
    parent_text = parent_file.read_text() if parent_file.exists() else ""
    imports = [line for line in parent_text.splitlines() if line.startswith("import ")]

    # Construct test file
    test_content = "\n".join(imports) + "\n\n"
    test_content += f"namespace ZtareProofs.NSLLMTest\n"
    test_content += f"theorem {target_name}_attempt {target_signature} := {proof_body}\n"
    test_content += "end ZtareProofs.NSLLMTest\n"

    test_path.write_text(test_content)
    try:
        result = subprocess.run(
            ["lake", "build", f"ZtareProofs.{test_module_name}"],
            cwd=LEAN_PROJECT,
            capture_output=True, text=True, timeout=120,
        )
        outcome = {
            "verified": result.returncode == 0,
            "lake_exit": result.returncode,
            "stderr_tail": result.stderr[-1500:] if result.stderr else "",
            "stdout_tail": result.stdout[-500:] if result.stdout else "",
        }
    except subprocess.TimeoutExpired:
        outcome = {"verified": False, "lake_exit": "timeout", "stderr_tail": "compile timeout"}
    finally:
        try: test_path.unlink()
        except: pass
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", type=Path, default=GRAPH)
    parser.add_argument("--max-obligations", type=int, default=10)
    parser.add_argument("--n-examples", type=int, default=30, help="closed-theorems in prompt")
    parser.add_argument("--obligation-names", nargs="*", default=None,
                        help="specific obligation names to target (overrides max-obligations)")
    parser.add_argument("--prompts-out", type=Path, default=REPO / "analytics" / "public" / "queries" / "llm_lean_prompts",
                        help="dir to dump generated prompts (one per obligation)")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    g = json.loads(args.graph.read_text())
    files = [n for n in g["@graph"] if n.get("@type") == "ns_lean_file"]
    fwd = {f["@id"]: set(f.get("imports", [])) for f in files}
    def reach(s):
        seen, st = {s}, [s]
        while st:
            n = st.pop()
            for nb in fwd.get(n, []):
                if nb not in seen: seen.add(nb); st.append(nb)
        return seen
    rt_ids = reach(RECEIPT)
    rt_names = {fid.replace("ns_file:", "") for fid in rt_ids}

    closed = extract_closed_theorems(rt_names)
    print(f"Found {len(closed)} closed theorems in receipt-tree (the in-context corpus)")

    obligations = get_open_obligations_with_signatures(g, rt_names)
    print(f"Found {len(obligations)} open theorem-kind obligations")

    if args.obligation_names:
        obligations = [o for o in obligations if o.get("name") in args.obligation_names]
        print(f"Filtered to {len(obligations)} named obligations")
    else:
        obligations = obligations[:args.max_obligations]
        print(f"Limited to first {args.max_obligations}")

    # Generate prompts (one per obligation) — caller dispatches via Agent tool
    args.prompts_out.mkdir(parents=True, exist_ok=True)
    prompt_specs = []
    for ob in obligations:
        target_file = LEAN_DIR / f"{ob.get('file', '').replace('ns_file:', '')}.lean"
        ftext = target_file.read_text() if target_file.exists() else ""
        imports = [line for line in ftext.splitlines() if line.startswith("import ")]
        prompt = build_prompt(ob, closed, imports, args.n_examples)
        prompt_path = args.prompts_out / f"{ob['name']}.txt"
        prompt_path.write_text(prompt)
        prompt_specs.append({
            "name": ob["name"], "kind": ob.get("kind"),
            "file": ob.get("file"), "prompt_path": str(prompt_path),
            "prompt_chars": len(prompt),
        })
        print(f"  {ob['name']:60} prompt={len(prompt)} chars  ({prompt_path.name})")

    # Save metadata
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "ts": time.time(),
        "n_closed_examples": len(closed),
        "n_obligations": len(obligations),
        "n_examples_in_prompt": args.n_examples,
        "prompts": prompt_specs,
        "next_step": "Spawn Claude subagent per prompt; call verify_proof() on each candidate; record outcome.",
    }, indent=2))
    print(f"\nWrote {len(prompt_specs)} prompts to {args.prompts_out}/")
    print(f"Metadata: {args.out}")
    print(f"\nNext: spawn one Claude subagent per prompt to generate proof candidate;")
    print(f"      then call verify_proof() to run lake build + check exit code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
