#!/usr/bin/env python3
"""pass@K SAMPLING generation for the void-SFT proving test — the metric fix.

Greedy pass@1 on ~10 held-out theorems is NOT how proving ability is measured: SOTA (DeepSeek-Prover, STP,
Goedel-Prover, …) reports pass@K with SAMPLING, K in {32 … 8192}. A single greedy decode massively understates a
prover; our first run's 1/10 was a measurement artifact, not a verdict (the misses were near-hits: 2 truncations,
type-mismatches, `sorry`-after-a-structured-proof — zero garbage).

This script samples K proofs per held-out `prove` theorem for two arms and writes them as LIST-valued fields so
`kernel_check.py` reports pass@1 (sample 0) AND pass@K (any of the K compiles):

  • gen_ft       : base + void LoRA adapter (the fine-tune)
  • gen_fewshot  : base + retrieved in-context exemplars, NO adapter  ← the FAIR baseline

We deliberately DROP a zero-shot base arm: given the instruction prompt the adapter trained on, the un-prompted
base emits only newlines (a useless floor). The few-shot arm is the honest "what the un-adapted base does when it
understands the task" — the real question is whether fine-tuning 84 proofs beats retrieving from them.

  python gen_samples.py --eval sft_eval.jsonl --train sft_train.jsonl \
      --model deepseek-ai/DeepSeek-Prover-V1.5-Base --adapter ./void_adapter \
      --k 16 --temperature 0.8 --gen-max-new 2048 --shots 3 --gens-out void_generations_passk.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _toks(s: str) -> set:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", (s or "").lower()))


def _fewshot_prompt(rec: dict, prove_ex: "list[dict]", shots: int) -> str:
    """Same retrieval as few_shot_eval.py: token-Jaccard on the prompt, top-`shots` train exemplars in-context."""
    tgt = rec.get("prompt") or ""
    tt = _toks(tgt)
    scored = sorted(prove_ex,
                    key=lambda e: len(_toks(e["prompt"]) & tt) / max(1, len(_toks(e["prompt"]) | tt)),
                    reverse=True)
    picked = [e for e in scored if e["prompt"] != tgt][:shots]
    block = "\n\n".join(e["prompt"] + e["completion"] for e in picked)
    return (block + "\n\n" + tgt) if block else tgt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", type=Path, required=True)
    ap.add_argument("--train", type=Path, required=True)
    ap.add_argument("--model", default="deepseek-ai/DeepSeek-Prover-V1.5-Base")
    ap.add_argument("--adapter", type=Path, required=True)
    ap.add_argument("--gens-out", type=Path, default=Path("./void_generations_passk.json"))
    ap.add_argument("--k", type=int, default=16, help="samples per target per arm (pass@K)")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--gen-max-new", type=int, default=2048, help="raised from 512: truncation was a real miss")
    ap.add_argument("--shots", type=int, default=3)
    ap.add_argument("--batch", type=int, default=8, help="num_return_sequences per generate() call (memory knob)")
    ap.add_argument("--no-4bit", action="store_true")
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    rows = [json.loads(l) for l in a.eval.read_text(encoding="utf-8").splitlines() if l.strip()]
    prove = [r for r in rows if r.get("task") == "prove" and r.get("probe")]
    train = [json.loads(l) for l in a.train.read_text(encoding="utf-8").splitlines() if l.strip()]
    prove_ex = [r for r in train if r.get("task") == "prove"]
    qcfg = None if a.no_4bit else BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16)

    def load(with_adapter: bool):
        m = AutoModelForCausalLM.from_pretrained(a.model, quantization_config=qcfg, torch_dtype=torch.bfloat16,
                                                 device_map="auto", trust_remote_code=True)
        if with_adapter:
            from peft import PeftModel
            m = PeftModel.from_pretrained(m, str(a.adapter))
        m.eval()
        return m

    def sample_k(model, prompt: str) -> "list[str]":
        ids = tok(prompt, return_tensors="pt", truncation=True, max_length=3072).input_ids.to(model.device)
        # DYNAMIC max_new (2026-07-02): the base model's context is 4096; a 3072-token few-shot prompt with a
        # fixed 2048 max_new generated PAST the cap — degraded samples + an unbounded-looking runtime. Cap to
        # what actually fits (64-token safety margin); short ft prompts keep the full budget.
        _fit = max(64, 4096 - int(ids.shape[1]) - 64)
        _max_new = min(a.gen_max_new, _fit)
        outs: list[str] = []
        while len(outs) < a.k:
            n = min(a.batch, a.k - len(outs))
            with torch.no_grad():
                g = model.generate(ids, max_new_tokens=_max_new, do_sample=True,
                                   temperature=a.temperature, top_p=a.top_p, num_return_sequences=n,
                                   pad_token_id=tok.pad_token_id)
            outs += [tok.decode(g[i, ids.shape[1]:], skip_special_tokens=True) for i in range(g.shape[0])]
        return outs[: a.k]

    # base first (few-shot arm), then wrap with adapter (ft arm) — hold one model at a time
    gens = {r.get("target") or r["prompt"][:40]:
            {"target": r.get("target"), "probe": r.get("probe"), "gold_proof": r.get("gold_proof"),
             "prompt": r["prompt"]} for r in prove}

    def _flush():
        # INCREMENTAL write (2026-07-02): the prior end-only write meant a kill/crash lost EVERYTHING after
        # hours of GPU sampling. Flush after every target so the file is always the current truth (kill-safe).
        a.gens_out.write_text(json.dumps(list(gens.values()), ensure_ascii=False, indent=2), encoding="utf-8")

    base = load(False)
    for i, r in enumerate(prove):
        key = r.get("target") or r["prompt"][:40]
        gens[key]["gen_fewshot"] = sample_k(base, _fewshot_prompt(r, prove_ex, a.shots))
        _flush()
        print(f"[gen_samples] fewshot {i+1}/{len(prove)}: {key}", flush=True)
    del base
    torch.cuda.empty_cache()
    ft = load(True)
    for i, r in enumerate(prove):
        key = r.get("target") or r["prompt"][:40]
        gens[key]["gen_ft"] = sample_k(ft, r["prompt"])
        _flush()
        print(f"[gen_samples] ft {i+1}/{len(prove)}: {key}", flush=True)

    merged = list(gens.values())
    a.gens_out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[gen_samples] wrote {len(merged)} targets × {a.k} samples/arm (ft, fewshot) → {a.gens_out}")
    print(f"[gen_samples] next: copy to the Lean VPS and run kernel_check.py --gens {a.gens_out.name} for pass@K")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
