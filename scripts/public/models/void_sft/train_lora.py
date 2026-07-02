#!/usr/bin/env python3
"""QLoRA SFT on the LeanMill void corpus — the reachable-scale strange-loop test (task #73).

Design follows the theorem-proving + PEFT literature (so the test is not a strawman):
  • BASE = a Lean-4-competent prover (default DeepSeek-Prover-V1.5-Base, 7B; DeepSeek-Prover 2405.14333 /
    V1.5 2408.08152). A Lean-competent base ISOLATES whether our void data adds signal, rather than a generic
    model learning Lean syntax from scratch.
  • LoRA on ALL linear layers at rank 32 ("LoRA Without Regret" / 2410.21228: LoRA matches full FT only when
    applied to all layers, esp. MLP, with adequate rank; code generation wants higher rank).
  • lr 2e-4 (LoRA optimum ≈ 10× full-FT), cosine, grad-checkpointing.
  • 4-bit QLoRA so a 7B fits the A10's 24 GB with headroom.

The reframe's claim is that a NARROW void fine-tune is domain adaptation (10^2-10^3 examples), so a LoRA on a
few hundred DIVERSE, quality-filtered pairs is the right size to ask whether the corpus carries learnable
signal. eval_completion.py says whether it moved.

  python train_lora.py --train sft_train.jsonl --model deepseek-ai/DeepSeek-Prover-V1.5-Base --out ./void_adapter
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, required=True)
    ap.add_argument("--model", default="deepseek-ai/DeepSeek-Prover-V1.5-Base")
    ap.add_argument("--out", type=Path, default=Path("./void_adapter"))
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--max-seq-len", type=int, default=2048)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=32)
    ap.add_argument("--no-4bit", action="store_true", help="full-precision LoRA (for a small base that fits)")
    a = ap.parse_args()

    import torch
    from datasets import Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, prepare_model_for_kbit_training
    from trl import SFTConfig, SFTTrainer

    rows = [json.loads(l) for l in a.train.read_text(encoding="utf-8").splitlines() if l.strip()]
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    eos = tok.eos_token or ""
    ds = Dataset.from_list([{"text": r["prompt"] + r["completion"] + eos} for r in rows])

    qcfg = None if a.no_4bit else BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(a.model, quantization_config=qcfg, torch_dtype=torch.bfloat16,
                                                 device_map="auto", trust_remote_code=True)
    if not a.no_4bit:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model.config.use_cache = False

    peft_cfg = LoraConfig(r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.05, bias="none",
                          target_modules="all-linear", task_type="CAUSAL_LM")
    cfg = SFTConfig(output_dir=str(a.out), num_train_epochs=a.epochs, per_device_train_batch_size=1,
                    gradient_accumulation_steps=16, learning_rate=a.lr, warmup_ratio=0.03,
                    lr_scheduler_type="cosine", logging_steps=5, save_strategy="epoch", bf16=True,
                    gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False},
                    max_length=a.max_seq_len, dataset_text_field="text", packing=False, report_to=[])
    trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds, peft_config=peft_cfg, processing_class=tok)
    trainer.train()
    trainer.save_model(str(a.out))
    tok.save_pretrained(str(a.out))
    print(json.dumps({"trained_on": len(rows), "base_model": a.model, "rank": a.rank,
                      "four_bit": not a.no_4bit, "adapter_out": str(a.out), "epochs": a.epochs}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
