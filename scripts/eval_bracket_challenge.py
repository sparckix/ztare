#!/usr/bin/env python3
"""GP-116 Candidate 0: Evaluate a model on the bracket challenge.

Measures accuracy as a function of sequence length L.
The output is the ZTARE substrate: (L, accuracy) pairs.

Usage:
    python scripts/eval_bracket_challenge.py --model pythia-70m
    python scripts/eval_bracket_challenge.py --model pythia-410m
"""

import argparse
import json
import time
from pathlib import Path


def eval_model_on_brackets(model_name: str, data: list[dict]) -> dict:
    """Evaluate a causal LM on bracket-matching classification."""
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        print("ERROR: requires torch, transformers")
        return {}

    repo = f"EleutherAI/{model_name}"
    tokenizer = AutoTokenizer.from_pretrained(repo)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float16 if torch.backends.mps.is_available() else torch.float32
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    model = AutoModelForCausalLM.from_pretrained(repo, torch_dtype=dtype).to(device)
    model.eval()

    # Group by length
    from collections import defaultdict
    by_length = defaultdict(list)
    for d in data:
        by_length[d["length"]].append(d)

    results = {}
    for L in sorted(by_length.keys()):
        samples = by_length[L]
        correct = 0
        total = 0

        for sample in samples:
            prompt = f"Is this bracket sequence balanced? {sample['sequence']}\nAnswer (yes/no):"

            inputs = tokenizer(prompt, return_tensors="pt", truncation=True,
                             max_length=L + 50)
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=5,
                                        do_sample=False,
                                        pad_token_id=tokenizer.pad_token_id)

            response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:],
                                       skip_special_tokens=True).lower().strip()

            predicted_balanced = "yes" in response[:10]
            actual_balanced = sample["label"] == 1

            if predicted_balanced == actual_balanced:
                correct += 1
            total += 1

        accuracy = correct / total if total > 0 else 0
        results[L] = {"accuracy": accuracy, "correct": correct, "total": total}
        print(f"  L={L:>4d}: acc={accuracy:.3f} ({correct}/{total})")

    del model
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    data_path = Path("projects/gp116_cot_exchange/raw/bracket_challenge.json")
    if not data_path.exists():
        print("Run generate_bracket_challenge.py first")
        return

    data = json.loads(data_path.read_text())
    print(f"Model: {args.model}")
    print(f"Data: {len(data)} samples")

    t0 = time.time()
    results = eval_model_on_brackets(args.model, data)
    elapsed = time.time() - t0

    # Save as ZTARE evidence format
    out_dir = Path("projects/gp116_cot_exchange/raw")
    evidence = []
    for L, r in sorted(results.items()):
        evidence.append({"length": L, "accuracy": r["accuracy"],
                        "model": args.model})

    out = out_dir / f"bracket_{args.model.replace('-','_')}.json"
    out.write_text(json.dumps(evidence, indent=2))
    print(f"\nSaved to {out} ({elapsed:.0f}s)")
    print(f"\nTo run ZTARE on this: convert to evidence.txt (n=L, z=accuracy)")


if __name__ == "__main__":
    main()
