#!/usr/bin/env python3
"""World-class pass@k SAMPLER (design step 1) — vLLM, N=32, --enable-lora, BOTH arms, ONE model in memory.

Runs on the GPU box (needs vllm + a CUDA GPU). For each held-out `prove` target it samples N proofs from two arms
against ONE loaded base model:
  • gen_ft       : base + void LoRA adapter  (the fine-tune — via vLLM LoRARequest)
  • gen_fewshot  : base + token-Jaccard-retrieved in-context exemplars, NO adapter  (the FAIR baseline)
Zero-shot base is dropped on purpose (it emits the newline floor). vLLM sampling — NOT a transformers `.generate()`
loop (that is gen_samples.py, the small-K fallback). Writes LIST-valued gens (gen_ft / gen_fewshot) in the shape
`passk_score.py` / `kernel_check.py` consume, so scoring is a separate VPS step (the GPU never touches Lean).

  python sample_vllm.py --model deepseek-ai/DeepSeek-Prover-V1.5-Base --adapter ./void_adapter \
      --train sft_train_holdout_v1.jsonl --eval holdout_eval_v1.json --n 32 --out void_gens_passk_r1.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _toks(s: str) -> set:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_']+", s or ""))


def _fewshot_prompt(rec: dict, prove_ex: "list[dict]", shots: int) -> str:
    """Token-Jaccard retrieval of the top-`shots` train `prove` exemplars, prepended in-context (mirrors
    few_shot_eval.py / gen_samples.py so the baseline is the SAME the small-K fallback used)."""
    tgt = rec.get("prompt") or ""
    tt = _toks(tgt)
    scored = sorted(prove_ex, key=lambda e: len(_toks(e.get("prompt", "")) & tt) / max(1, len(_toks(e.get("prompt", "")) | tt)),
                    reverse=True)
    picked = [e for e in scored if e.get("prompt") != tgt][:shots]
    block = "\n\n".join(e.get("prompt", "") + e.get("completion", "") for e in picked)
    return (block + "\n\n" + tgt) if block else tgt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="base HF model id (e.g. deepseek-ai/DeepSeek-Prover-V1.5-Base)")
    ap.add_argument("--adapter", type=Path, required=True, help="void LoRA adapter dir")
    ap.add_argument("--train", type=Path, required=True, help="sft_train_holdout_v1.jsonl (few-shot exemplar pool)")
    ap.add_argument("--eval", type=Path, required=True, help="holdout_eval_v1.json (the ≥30 held-out targets)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n", type=int, default=32, help="samples per target per arm (design: N=32)")
    ap.add_argument("--shots", type=int, default=4)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--max-new", type=int, default=2048)
    ap.add_argument("--max-model-len", type=int, default=4096)
    ap.add_argument("--lora-rank", type=int, default=0, help="0 ⇒ read `r` from the adapter_config.json")
    a = ap.parse_args()

    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    rank = a.lora_rank or int(json.loads((a.adapter / "adapter_config.json").read_text()).get("r", 64))
    prove_ex = [json.loads(l) for l in a.train.read_text().splitlines() if l.strip()
                and (json.loads(l).get("task") == "prove")]
    targets = json.loads(a.eval.read_text())
    print(f"[sample_vllm] {len(targets)} held-out targets · N={a.n} · shots={a.shots} · lora_rank={rank} · {len(prove_ex)} exemplars")

    llm = LLM(model=a.model, enable_lora=True, max_lora_rank=rank, max_model_len=a.max_model_len,
              gpu_memory_utilization=0.90)
    sp = SamplingParams(n=a.n, temperature=a.temp, top_p=a.top_p, max_tokens=a.max_new)

    ft_prompts = [t.get("prompt") or "" for t in targets]                          # adapter arm: the trained prompt as-is
    fs_prompts = [_fewshot_prompt(t, prove_ex, a.shots) for t in targets]          # baseline arm: few-shot retrieval

    # ONE model in memory; the adapter is applied per-request (LoRARequest) so both arms share the load.
    ft_out = llm.generate(ft_prompts, sp, lora_request=LoRARequest("void", 1, str(a.adapter)))
    fs_out = llm.generate(fs_prompts, sp)                                          # no lora_request ⇒ pure base

    gens = []
    for t, fo, so in zip(targets, ft_out, fs_out):
        gens.append({"target": t.get("target"), "probe": t.get("probe"), "gold_proof": t.get("gold_proof"),
                     "prompt": t.get("prompt"),
                     "gen_ft": [o.text for o in fo.outputs], "gen_fewshot": [o.text for o in so.outputs]})
    a.out.write_text(json.dumps(gens))
    print(f"[sample_vllm] wrote {len(gens)} targets × {a.n} samples/arm → {a.out}")
    print(f"[sample_vllm] next: scp to the Lean VPS + `python passk_score.py --gens {a.out.name}`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
