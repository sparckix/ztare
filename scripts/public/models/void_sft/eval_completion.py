#!/usr/bin/env python3
"""Held-out eval: did the LoRA lift the model on void proofs / formalizations? Two signals, no strawman.

1. NLL delta (deterministic, all held-out pairs): mean per-token negative log-likelihood of the GOLD completion
   (prompt masked) under base vs base+adapter. Lower under the fine-tune = it learned the void distribution.
   Plus faithfulness first-word accuracy.
2. Generation for the REAL metric: for each held-out `prove` theorem, generate a proof with base and with
   base+adapter and save it WITH its self-contained probe, so kernel_check (run on the Lean VPS) can splice +
   compile each and report pass@1 base-vs-finetuned — the actual proving lift, not a proxy.

  python eval_completion.py --eval sft_eval.jsonl --model deepseek-ai/DeepSeek-Prover-V1.5-Base --adapter ./void_adapter
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", type=Path, required=True)
    ap.add_argument("--model", default="deepseek-ai/DeepSeek-Prover-V1.5-Base")
    ap.add_argument("--adapter", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("./void_eval_result.json"))
    ap.add_argument("--gens-out", type=Path, default=Path("./void_generations.json"))
    ap.add_argument("--no-4bit", action="store_true")
    ap.add_argument("--gen-max-new", type=int, default=512)
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    rows = [json.loads(l) for l in a.eval.read_text(encoding="utf-8").splitlines() if l.strip()]
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

    def completion_nll(model, prompt: str, completion: str) -> float:
        p_ids = tok(prompt, return_tensors="pt").input_ids
        full = tok(prompt + completion, return_tensors="pt").input_ids.to(model.device)
        labels = full.clone()
        labels[:, : p_ids.shape[1]] = -100
        with torch.no_grad():
            return float(model(full, labels=labels).loss.item())

    def generate(model, prompt: str) -> str:
        ids = tok(prompt, return_tensors="pt").input_ids.to(model.device)
        with torch.no_grad():
            g = model.generate(ids, max_new_tokens=a.gen_max_new, do_sample=False, pad_token_id=tok.pad_token_id)
        return tok.decode(g[0, ids.shape[1]:], skip_special_tokens=True)

    def run(model):
        nll = collections.defaultdict(list)
        faith_hit = faith_n = 0
        gens = {}
        for r in rows:
            nll[r["task"]].append(completion_nll(model, r["prompt"], r["completion"]))
            if r["task"] == "faithfulness":
                faith_n += 1
                gold = "UNFAITHFUL" if r["completion"].strip().upper().startswith("UNFAITHFUL") else "FAITHFUL"
                out = generate(model, r["prompt"]).strip().upper()
                faith_hit += int(out.startswith(gold[:6]))
            if r["task"] == "prove" and r.get("probe"):
                gens[r.get("target") or r["prompt"][:40]] = {
                    "target": r.get("target"), "probe": r.get("probe"), "gold_proof": r.get("gold_proof"),
                    "prompt": r["prompt"], "generated": generate(model, r["prompt"])}
        metrics = {t: round(sum(v) / len(v), 4) for t, v in nll.items()}
        if faith_n:
            metrics["faithfulness_acc"] = round(faith_hit / faith_n, 3)
        return metrics, gens

    base = load(False)
    base_m, base_gens = run(base)
    del base
    torch.cuda.empty_cache()
    ft = load(True)
    ft_m, ft_gens = run(ft)

    delta = {t: round(ft_m[t] - base_m.get(t, 0.0), 4) for t in ("prove", "formalize") if t in ft_m}
    result = {"n_eval": len(rows), "base": base_m, "finetuned": ft_m,
              "nll_delta_lower_is_better": delta,
              "nll_verdict": ("LIFT" if delta and all(d < 0 for d in delta.values()) else "MIXED/NONE")}
    a.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    # merge base/ft generations per target for the downstream kernel pass@k
    merged = []
    for k, g in base_gens.items():
        merged.append({**g, "gen_base": g.pop("generated"), "gen_ft": ft_gens.get(k, {}).get("generated", "")})
    a.gens_out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"[eval] wrote {len(merged)} held-out prove generations to {a.gens_out} for kernel pass@k")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
