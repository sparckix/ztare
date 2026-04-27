#!/usr/bin/env python3
"""GP-116: Evaluate Pythia models on ARC-challenge with varying CoT length.

Measures A(P, T) where P = model params, T = CoT tokens.

Usage:
    python scripts/eval_cot_exchange.py --model pythia-70m --cot-lengths 0 50 100 200 500
    python scripts/eval_cot_exchange.py --model pythia-70m --all-lengths

Requires: torch, transformers
"""

import argparse
import json
import sys
import time
from pathlib import Path


def eval_with_cot(model_name: str, cot_max_tokens: int, n_samples: int = 50) -> dict | None:
    """Evaluate a Pythia model on ARC-challenge with prompted CoT."""
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        print("ERROR: requires torch, transformers", file=sys.stderr)
        return None

    repo_id = f"EleutherAI/{model_name}"

    try:
        tokenizer = AutoTokenizer.from_pretrained(repo_id)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        dtype = torch.float16 if torch.backends.mps.is_available() else torch.float32
        device = "mps" if torch.backends.mps.is_available() else "cpu"

        model = AutoModelForCausalLM.from_pretrained(repo_id, torch_dtype=dtype)
        model = model.to(device)
        model.eval()

        # Simple pattern completion tasks (70M can handle these)
        # The task: complete a simple arithmetic or letter pattern
        questions = [
            {"q": "1, 2, 3, 4, 5, ?", "answer": "6"},
            {"q": "2, 4, 6, 8, ?", "answer": "10"},
            {"q": "1, 1, 2, 3, 5, 8, ?", "answer": "13"},
            {"q": "A, B, C, D, ?", "answer": "E"},
            {"q": "10, 20, 30, 40, ?", "answer": "50"},
            {"q": "1, 4, 9, 16, 25, ?", "answer": "36"},
            {"q": "3, 6, 9, 12, ?", "answer": "15"},
            {"q": "100, 90, 80, 70, ?", "answer": "60"},
            {"q": "1, 3, 5, 7, 9, ?", "answer": "11"},
            {"q": "2, 3, 5, 7, 11, ?", "answer": "13"},
        ] * (n_samples // 10 + 1)
        questions = questions[:n_samples]

        correct = 0
        total = 0

        for q_data in questions:
            if cot_max_tokens == 0:
                prompt = f"Complete the pattern: {q_data['q']} The answer is"
            else:
                prompt = f"Complete the pattern: {q_data['q']} Let me think step by step."

            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                max_new = max(cot_max_tokens, 5)
                outputs = model.generate(
                    **inputs, max_new_tokens=max_new,
                    do_sample=False, pad_token_id=tokenizer.pad_token_id
                )

            response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:],
                                       skip_special_tokens=True)

            # Check if the answer appears in the response
            if q_data["answer"] in response[:cot_max_tokens + 50]:
                correct += 1
            total += 1

        accuracy = correct / total if total > 0 else 0

        del model
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()

        return {"accuracy": accuracy, "correct": correct, "total": total}

    except Exception as e:
        print(f"  Error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="e.g., pythia-70m")
    parser.add_argument("--cot-lengths", nargs="+", type=int, default=None)
    parser.add_argument("--all-lengths", action="store_true")
    parser.add_argument("--n-samples", type=int, default=50)
    args = parser.parse_args()

    if args.all_lengths:
        cot_lengths = [0, 10, 25, 50, 100, 200, 500, 1000]
    elif args.cot_lengths:
        cot_lengths = args.cot_lengths
    else:
        cot_lengths = [0, 50, 200, 500]

    print(f"Model: {args.model}")
    print(f"CoT lengths: {cot_lengths}")

    out = Path(f"projects/gp116_cot_exchange/raw/{args.model.replace('-','_')}_cot.json")
    out.parent.mkdir(parents=True, exist_ok=True)

    # Load existing results (checkpoint support)
    results = []
    if out.exists():
        try:
            results = json.loads(out.read_text())
            done_lengths = {r["cot_tokens"] for r in results}
            cot_lengths = [T for T in cot_lengths if T not in done_lengths]
            if cot_lengths:
                print(f"  Resuming: {len(done_lengths)} lengths done, {len(cot_lengths)} remaining")
            else:
                print(f"  All lengths done. Remove {out} to rerun.")
                return
        except Exception:
            pass

    for T in cot_lengths:
        print(f"  T={T}...", end=" ", flush=True)
        t0 = time.time()
        r = eval_with_cot(args.model, T, args.n_samples)
        elapsed = time.time() - t0
        if r:
            results.append({"model": args.model, "cot_tokens": T, **r})
            print(f"acc={r['accuracy']:.3f} ({elapsed:.1f}s)")
        else:
            print("FAILED")

        # Save after EACH length (checkpoint)
        out.write_text(json.dumps(results, indent=2))

    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
