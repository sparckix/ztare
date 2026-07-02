#!/usr/bin/env python3
"""Kernel pass@1 for the void SFT test — run ON the Lean VPS (has lake + Mathlib).

For each held-out `prove` theorem, splice the GENERATED proof (base vs fine-tuned) into its self-contained
probe and compile. A proof passes iff the file elaborates with no error and leaves no `sorry`/`sorryAx`. Reports
pass@1 base-vs-finetuned and the targets where the fine-tune FLIPPED a base failure into a close — the actual
proving lift, the metric the NLL delta only proxies.

  PYTHONPATH=src venv/bin/python scripts/public/models/void_sft/kernel_check.py --gens /tmp/void_generations.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
LEAN_ROOT = REPO / "ztare_proofs"


def _splice(probe: str, gold: str, gen: str) -> "str | None":
    """Replace the gold proof in the self-contained probe with the generated one. Prefer an exact gold-substring
    swap; fall back to the canonical lean_source signature-reattach so a differently-shaped gold still splices."""
    gen = gen.strip()
    if not gen:
        return None
    if gold and gold.strip() and gold.strip() in probe:
        return probe.replace(gold.strip(), gen, 1)
    try:
        import sys
        sys.path.insert(0, str(REPO / "src"))
        from ztare.leanmill.lean_source import decl_blocks, signature_before_proof, attach_proof
        for name, block in decl_blocks(probe):
            if gold and gold.strip() and gold.strip() in block:
                new_block = attach_proof(signature_before_proof(block).rstrip() + " :=", gen)
                return probe.replace(block, new_block, 1) if new_block else None
    except Exception:  # noqa: BLE001
        return None
    return None


def _compiles(src: str) -> bool:
    if not src or not src.strip():
        return False                    # an empty file "compiles" but proves nothing — never a pass
    f = LEAN_ROOT / "_void_gen_check.lean"
    f.write_text(src, encoding="utf-8")
    env = {**os.environ, "PATH": os.path.expanduser("~/.elan/bin") + ":" + os.environ.get("PATH", "")}
    try:
        r = subprocess.run(["lake", "env", "lean", str(f)], cwd=str(LEAN_ROOT),
                           capture_output=True, text=True, timeout=400, env=env)
        out = (r.stdout + r.stderr)
        return r.returncode == 0 and "error" not in out.lower() and "sorry" not in out
    except Exception:  # noqa: BLE001
        return False
    finally:
        f.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gens", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("/tmp/void_kernel_passk.json"))
    a = ap.parse_args()
    gens = json.loads(a.gens.read_text(encoding="utf-8"))
    # every arm present as a `gen_<arm>` field (gen_base / gen_ft / gen_fewshot) is scored generically → 3-way pass@1
    arms = sorted({k[4:] for g in gens for k in g if k.startswith("gen_")})
    passes = {arm: 0 for arm in arms}
    for g in gens:
        probe, gold = g.get("probe") or "", g.get("gold_proof") or ""
        for arm in arms:
            spliced = _splice(probe, gold, g.get("gen_" + arm) or "")
            # an empty/unspliceable generation is a FAIL, not a compile-of-nothing (an empty .lean file compiles
            # clean and would be a false pass — the base model emitting whitespace must not score 11/11).
            ok = bool(spliced) and _compiles(spliced)
            g[arm + "_pass"] = ok
            passes[arm] += int(ok)
    base = passes.get("base", 0)
    flips = {arm: [g.get("target") for g in gens if g.get(arm + "_pass") and not g.get("base_pass")]
             for arm in arms if arm != "base"}
    result = {"n": len(gens), "pass@1": passes,
              "flipped_base_failures": flips,
              "best_arm": max(passes, key=passes.get) if passes else None}
    a.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
