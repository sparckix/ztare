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


def _splice(probe: str, gold: str, gen: str, target: "str | None" = None) -> "str | None":
    """Replace the gold proof in the self-contained probe with the generated one. Prefer an exact gold-substring
    swap; fall back to the canonical lean_source signature-reattach so a differently-shaped gold still splices.

    The fallback locates the target decl by NAME (not by gold-substring): the stored gold can be whitespace-reflowed
    vs the probe (e.g. "by norm_num" vs "by\n  norm_num"), which silently makes the target unspliceable for EVERY
    arm — the real cause of the e2e_conj_route_conj3 gold-control miss."""
    gen = gen.strip()
    if not gen:
        return None
    if gold and gold.strip() and gold.strip() in probe:
        return probe.replace(gold.strip(), gen, 1)
    try:
        import sys
        sys.path.insert(0, str(REPO / "src"))
        from ztare.leanmill.lean_source import decl_blocks, signature_before_proof, attach_proof
        blocks = decl_blocks(probe)
        cand = [(n, b) for n, b in blocks if target and n == target]        # by name (whitespace-independent)
        if not cand:
            cand = [(n, b) for n, b in blocks if gold and gold.strip() and gold.strip() in b]
        if not cand and len(blocks) == 1:
            cand = blocks                                                   # single-decl probe → it's the target
        if cand:
            _, block = cand[-1]
            new_block = attach_proof(signature_before_proof(block).rstrip() + " :=", gen)
            return probe.replace(block, new_block, 1) if new_block else None
    except Exception:  # noqa: BLE001
        return None
    return None


_VERDICTS: "dict[str, bool]" = {}       # spliced-source → verdict (temp-sampled duplicates are common; a K=16
                                        # run would otherwise re-pay the compile for every identical sample)


def _compiles(src: str) -> bool:
    if not src or not src.strip():
        return False                    # an empty file "compiles" but proves nothing — never a pass
    if src in _VERDICTS:
        return _VERDICTS[src]
    # WARM-FIRST (§4.5 warm-compile door): a cold `lake env lean` re-imports Mathlib per sample (~30-45s), and a
    # pass@K run is up to targets×arms×K compiles (~hours). The warm REPL elaborates each probe over a preloaded
    # Mathlib in seconds, SAME verdict (reject_sorry=True matches this checker's policy: a sorried generation is
    # a FAIL). None ⇒ REPL unusable here ⇒ the cold path below is the unchanged authoritative fallback.
    try:
        import sys
        sys.path.insert(0, str(REPO / "src"))
        from ztare.formal.repl_compile import compile_probe_via_repl
        warm = compile_probe_via_repl(src, LEAN_ROOT, timeout=240, reject_sorry=True)
        if warm is not None:
            _VERDICTS[src] = bool(warm[0])
            return _VERDICTS[src]
    except Exception:  # noqa: BLE001 — warm path is an optimization; the cold fallback is authoritative
        pass
    f = LEAN_ROOT / "_void_gen_check.lean"
    f.write_text(src, encoding="utf-8")
    env = {**os.environ, "PATH": os.path.expanduser("~/.elan/bin") + ":" + os.environ.get("PATH", "")}
    try:
        r = subprocess.run(["lake", "env", "lean", str(f)], cwd=str(LEAN_ROOT),
                           capture_output=True, text=True, timeout=400, env=env)
        out = (r.stdout + r.stderr)
        _VERDICTS[src] = r.returncode == 0 and "error" not in out.lower() and "sorry" not in out
        return _VERDICTS[src]
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
    # every arm present as a `gen_<arm>` field (gen_base / gen_ft / gen_fewshot) is scored generically.
    # gen_<arm> may be a STRING (one sample → pass@1) OR a LIST of samples (→ pass@K = any sample compiles). One
    # scorer for both so greedy and sampled runs go through the same door.
    arms = sorted({k[4:] for g in gens for k in g if k.startswith("gen_")})
    pass1 = {arm: 0 for arm in arms}
    passK = {arm: 0 for arm in arms}
    for g in gens:
        probe, gold, target = g.get("probe") or "", g.get("gold_proof") or "", g.get("target")
        for arm in arms:
            gv = g.get("gen_" + arm)
            samples = gv if isinstance(gv, list) else [gv or ""]
            ok_first = ok_any = False
            for i, s in enumerate(samples):
                spliced = _splice(probe, gold, s or "", target)
                # an empty/unspliceable generation is a FAIL, not a compile-of-nothing (an empty .lean file compiles
                # clean and would be a false pass — the base model emitting whitespace must not score 11/11).
                ok = bool(spliced) and _compiles(spliced)
                if i == 0:
                    ok_first = ok
                if ok:
                    ok_any = True
                    break                                   # pass@K only needs one; stop compiling this arm
            g[arm + "_pass"] = ok_any                        # "_pass" == pass@K (any sample)
            g[arm + "_pass1"] = ok_first
            pass1[arm] += int(ok_first)
            passK[arm] += int(ok_any)
    k = max((len(g.get("gen_" + a)) for g in gens for a in arms if isinstance(g.get("gen_" + a), list)), default=1)
    flips = {arm: [g.get("target") for g in gens if g.get(arm + "_pass") and not g.get("base_pass")]
             for arm in arms if arm != "base"}
    result = {"n": len(gens), "k": k, "pass@1": pass1, "pass@K": passK,
              "flipped_base_failures": flips,
              "best_arm": max(passK, key=passK.get) if passK else None}
    a.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
