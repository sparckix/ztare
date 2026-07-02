#!/usr/bin/env python3
"""Few-shot (retrieval + in-context) arm — the alternative to SFT for a small corpus (task #73).

For a corpus this small (~few hundred pairs) the field's move is retrieval + in-context exemplars, not SFT
(ReProver/LeanDojo retrieve premises; DSP conditions on a sketch) — it does not overfit and it leverages the
base model's in-context learning. This arm: for each held-out `prove` theorem, retrieve the K most similar TRAIN
`(statement→proof)` exemplars (token-Jaccard on the prompt), put them in the prompt, and generate with the BASE
model (no adapter). It appends `gen_fewshot` to the generations file so kernel_check reports a 3-way pass@1:
zero-shot base vs SFT-LoRA vs few-shot — the honest test of whether fine-tuning 357 proofs beats just retrieving
from them.

  python few_shot_eval.py --train sft_train.jsonl --gens void_generations.json --model <base> --k 3
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _toks(s: str) -> set:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", (s or "").lower()))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, required=True)
    ap.add_argument("--gens", type=Path, required=True)          # void_generations.json (has gen_base/gen_ft)
    ap.add_argument("--model", default="deepseek-ai/DeepSeek-Prover-V1.5-Base")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--gen-max-new", type=int, default=512)
    ap.add_argument("--no-4bit", action="store_true")
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    train = [json.loads(l) for l in a.train.read_text(encoding="utf-8").splitlines() if l.strip()]
    prove_ex = [r for r in train if r.get("task") == "prove"]
    gens = json.loads(a.gens.read_text(encoding="utf-8"))
    qcfg = None if a.no_4bit else BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16)
    base = AutoModelForCausalLM.from_pretrained(a.model, quantization_config=qcfg, torch_dtype=torch.bfloat16,
                                                device_map="auto", trust_remote_code=True)
    base.eval()

    def generate(prompt: str) -> str:
        ids = tok(prompt, return_tensors="pt", truncation=True, max_length=3072).input_ids.to(base.device)
        with torch.no_grad():
            g = base.generate(ids, max_new_tokens=a.gen_max_new, do_sample=False, pad_token_id=tok.pad_token_id)
        return tok.decode(g[0, ids.shape[1]:], skip_special_tokens=True)

    for rec in gens:
        tgt_prompt = rec.get("prompt") or ""
        tt = _toks(tgt_prompt)
        scored = sorted(prove_ex, key=lambda e: len(_toks(e["prompt"]) & tt) / max(1, len(_toks(e["prompt"]) | tt)),
                        reverse=True)
        shots = [e for e in scored if e["prompt"] != tgt_prompt][: a.k]
        block = "\n\n".join(e["prompt"] + e["completion"] for e in shots)
        prompt = (block + "\n\n" + tgt_prompt) if block else tgt_prompt
        rec["gen_fewshot"] = generate(prompt)

    a.gens.write_text(json.dumps(gens, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[few-shot] added gen_fewshot to {len(gens)} held-out prove records (k={a.k})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
