#!/usr/bin/env python3
"""Format the LeanMill training corpus (export_training_corpus.py output) into instruction→completion SFT pairs.

Three tasks from the four exported streams — the strange-loop's OWN void data (task #71/#73):
  • prove       : (statement) -> (kernel-verified proof)          [prover_corpus, void slice = uniquely ours]
  • formalize   : (natural language) -> (Lean statement)          [autoformalization_corpus, firewall-faithful]
  • faithfulness: (Lean statement) -> FAITHFUL / UNFAITHFUL+reason [autoformalization faithful positives +
                                                                    discriminator caught negatives]

The point is the REACHABLE-SCALE test the reframe named: does a narrow LoRA fine-tune on ~270 diverse void pairs
lift proving, at a scale a domain adaptation actually needs (10^2-10^3) — not the 10^4 corpus-size theater. A
held-out split (default 15%) is stratified per task so the eval measures generalization, not memorization.

  python format_corpus.py --corpus <dir with *_corpus.jsonl> --out <dir> [--eval-frac 0.15]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read(p: Path) -> "list[dict]":
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _rec(task: str, prompt: str, completion: str) -> dict:
    # trailing space before completion is the standard SFT convention (the model learns to continue the prompt)
    return {"task": task, "prompt": prompt.rstrip() + "\n", "completion": " " + completion.strip()}


def build(corpus: Path) -> "list[dict]":
    out: "list[dict]" = []
    for r in _read(corpus / "prover_corpus.jsonl"):
        stmt, proof = (r.get("statement") or "").strip(), (r.get("proof") or "").strip()
        if stmt and proof:
            # CoT distillation: when the agent's decomposition reasoning was joined (export _attach_reasoning),
            # train think-then-prove — the plan as a Lean comment the kernel ignores, so a generation still compiles.
            reason = (r.get("reasoning") or "").strip()
            completion = f"/- Plan: {reason} -/\n{proof}" if reason else proof
            prompt = ("Prove the following Lean 4 theorem. If it helps, give a one-line plan as a `/- ... -/` "
                      f"comment first, then the proof.\n\n{stmt}")
            rec = _rec("prove", prompt, completion)
            # carry the self-contained probe + names so a GENERATED proof can be kernel-checked (real pass@k, not just NLL)
            rec["target"] = r.get("target")
            rec["probe"] = r.get("recompilable_probe") or ""
            rec["gold_proof"] = proof   # BARE proof (for splicing the generation into the probe; comment is stripped by the kernel)
            rec["has_cot"] = bool(reason)
            out.append(rec)
    for r in _read(corpus / "autoformalization_corpus.jsonl"):
        nl, lean = (r.get("nl") or "").strip(), (r.get("lean_statement") or "").strip()
        if nl and lean:
            out.append(_rec("formalize", f"Formalize the following as a single Lean 4 statement.\n\n{nl}", lean))
    # faithfulness classification: faithful positives (from autoformalization) + caught negatives (discriminator)
    for r in _read(corpus / "autoformalization_corpus.jsonl"):
        lean = (r.get("lean_statement") or "").strip()
        if lean:
            out.append(_rec("faithfulness", f"Is this Lean 4 statement a faithful formalization of its intended claim? Answer FAITHFUL or UNFAITHFUL with a one-line reason.\n\n{lean}", "FAITHFUL. The statement preserves the intended hypotheses and conclusion."))
    for r in _read(corpus / "faithfulness_discriminator_corpus.jsonl"):
        stmt, why = (r.get("statement") or "").strip(), (r.get("witness") or "").strip()
        if stmt:
            out.append(_rec("faithfulness", f"Is this Lean 4 statement a faithful formalization of its intended claim? Answer FAITHFUL or UNFAITHFUL with a one-line reason.\n\n{stmt}", f"UNFAITHFUL. {why or 'the target signature or a referenced definition was altered.'}"))
    return out


def split(rows: "list[dict]", eval_frac: float) -> "tuple[list, list]":
    """Per-task stratified split. Deterministic (every k-th item to eval), so no RNG (reproducible + the runtime
    forbids Math.random anyway). k derived from eval_frac."""
    tr, ev = [], []
    by_task: "dict[str, list]" = {}
    for r in rows:
        by_task.setdefault(r["task"], []).append(r)
    for task, items in by_task.items():
        k = max(2, round(1 / max(0.01, eval_frac)))  # every k-th → eval
        for i, r in enumerate(items):
            (ev if i % k == 0 else tr).append(r)
    return tr, ev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--eval-frac", type=float, default=0.15)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rows = build(a.corpus)
    tr, ev = split(rows, a.eval_frac)
    (a.out / "sft_train.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in tr), encoding="utf-8")
    (a.out / "sft_eval.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ev), encoding="utf-8")
    from collections import Counter
    manifest = {"total": len(rows), "train": len(tr), "eval": len(ev),
                "by_task": dict(Counter(r["task"] for r in rows)),
                "train_by_task": dict(Counter(r["task"] for r in tr)),
                "eval_by_task": dict(Counter(r["task"] for r in ev))}
    (a.out / "format_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
