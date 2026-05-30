#!/usr/bin/env python3
"""LeanMill provider registry — the router's provider table.

Phase G (2026-05-28): enumerates the pluggable Lean provers the audit substrate
can run, normalises their invocation, and returns a typed_exit-compatible record
per (provider, goal). This is the "router" surface of LeanMill-as-LangChain-for-
Lean-provers: any prover wired here flows through the same semantic premise shelf,
the same leak-tight benchmark, and the same matched-negative-control governance.

Each provider is a wrapper under scripts/public/lean/providers/. The registry
records: kind (native_tactic / subscription_llm / open_weights / ide), the
invocation shape (goal_file vs goal_text), tested status, and cost class.

CLI:
  list                          show the provider table
  invoke --provider X --goal-file F   run one provider on one goal, print typed_exit
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PROVIDERS_DIR = REPO / "scripts" / "public" / "lean" / "providers"

# kind: native_tactic | subscription_llm | open_weights | ide
# arg_shape: goal_file | goal_text
# tested: whether this wrapper has been run end-to-end in this repo
REGISTRY = {
    "native_hammer": {
        "wrapper": "native_hammer.sh",
        "kind": "native_tactic",
        "arg_shape": "goal_file_and_proof_file",
        "cost_class": "zero_token",
        "tested": True,   # lean_tactic_hammer.py is shipped + runs in typed-endpoint workflow
        "note": "exact?/aesop/.../rfl cascade. Static-first baseline. CONSTRAINT: needs a complete Lean statement (theorem header := by), not a bare goal — statement synthesis from a goal needs field-type elaboration we lack (see lean_tactic_hammer.py Honest scope).",
    },
    "claude_opus": {
        "wrapper": "claude_opus.sh",
        "kind": "subscription_llm",
        "arg_shape": "goal_text",
        "cost_class": "subscription",
        "tested": True,   # claude -p subscription path verified via v28 dispatcher
        "note": "Claude Opus 4.7 via claude code subscription (no API key).",
    },
    "codex_gpt5": {
        "wrapper": "codex_gpt5.sh",
        "kind": "subscription_llm",
        "arg_shape": "goal_text",
        "cost_class": "subscription",
        "tested": True,   # codex exec subscription path verified via v28 dispatcher
        "note": "Codex GPT-5.5 via codex CLI subscription.",
    },
    "deepseek_v2": {
        "wrapper": "deepseek_v2.sh",
        "kind": "open_weights",
        "arg_shape": "goal_text",
        "cost_class": "local_gpu_or_endpoint",
        "tested": False,  # requires Ollama pull or HF endpoint; wrapper written to documented interface
        "note": "DeepSeek-Prover-V2 (88.9% miniF2F pass@8192). Local Ollama default; ZTARE_DEEPSEEK_ENDPOINT for vLLM/HF.",
    },
    "leancopilot": {
        "wrapper": "leancopilot.sh",
        "kind": "ide",
        "arg_shape": "goal_file",
        "cost_class": "local",
        "tested": False,  # requires LeanCopilot in the Lake project
        "note": "LeanCopilot search_proof/suggest_tactics. IDE incumbent; needs install in ztare_proofs Lake project.",
    },
}


def provider_path(name: str) -> Path:
    if name not in REGISTRY:
        raise SystemExit(f"unknown provider: {name}; known: {sorted(REGISTRY)}")
    return PROVIDERS_DIR / REGISTRY[name]["wrapper"]


def invoke(name: str, goal_file: str | None = None, goal_text: str | None = None,
           proof_file: str | None = None, timeout_s: int = 300) -> dict:
    """Run one provider on one goal. Returns a typed_exit-compatible dict.

    Implementation (2026-05-28): delegates to the typed Provider layer at
    `ztare.leanmill.providers.get_provider()`. The kernel-side typed providers
    are the single source of truth for invocation; the bash wrappers under
    `scripts/public/lean/providers/*.sh` are deprecated for any provider that
    appears in `ztare.leanmill.providers.REGISTRY`. Providers not yet migrated
    fall through to the legacy bash-wrapper path below.

    Return shape preserves the legacy dict keys so existing callers keep
    working without change. Typed error reasons are surfaced under the new
    `provider_error` /
    `provider_error_detail` keys; downstream callers that branch on them
    can stop conflating credit-exhausted / rate_limited with proof text.
    """
    spec = REGISTRY[name]

    # ── 1. Typed Python provider path (preferred) ──────────────────────────
    sys.path.insert(0, str(REPO / "src"))
    try:
        from ztare.leanmill.providers import (  # type: ignore
            REGISTRY as TYPED_REG,
            get_provider,
        )
    except Exception:
        TYPED_REG = {}
        get_provider = None  # type: ignore

    if get_provider is not None and name in TYPED_REG:
        text = goal_text
        if text is None and goal_file:
            text = Path(goal_file).read_text()
        if not text:
            raise SystemExit(f"{name} needs --goal-text or --goal-file")
        tr = get_provider(name).invoke(text, timeout_s=timeout_s)
        return {
            "schema": "leanmill-provider-invoke-v1",
            "provider": name,
            "kind": spec["kind"],
            "cost_class": spec["cost_class"],
            "returncode": 0 if tr.ok else 1,
            "wallclock_s": tr.wallclock_s,
            "proof_text": tr.proof_text or "",
            "proof_nonempty": bool((tr.proof_text or "").strip()) and tr.error.value == "none",
            "error": tr.error_detail if tr.error.value != "none" else None,
            "provider_error": tr.error.value,
            "provider_error_detail": tr.error_detail,
            "credit_boundary": "provider output only; requires governance + matched-negative-control receipt before proof credit",
        }

    # ── 2. Legacy bash-wrapper fallback (deprecated, kept for un-migrated providers) ──
    wrapper = provider_path(name)
    shape = spec["arg_shape"]
    if shape == "goal_file_and_proof_file":
        if not goal_file or not proof_file:
            raise SystemExit(f"{name} needs --goal-file and --proof-file")
        cmd = [str(wrapper), goal_file, proof_file]
    elif shape == "goal_file":
        if not goal_file:
            raise SystemExit(f"{name} needs --goal-file")
        cmd = [str(wrapper), goal_file]
    else:  # goal_text
        text = goal_text
        if text is None and goal_file:
            text = Path(goal_file).read_text()
        if not text:
            raise SystemExit(f"{name} needs --goal-text or --goal-file")
        cmd = [str(wrapper), text]

    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        stdout = proc.stdout or ""
        rc = proc.returncode
        err = proc.stderr[:500] if proc.returncode != 0 else None
    except subprocess.TimeoutExpired:
        stdout, rc, err = "", -1, f"timeout_{timeout_s}s"
    except Exception as e:  # noqa: BLE001
        stdout, rc, err = "", -1, repr(e)
    wall = round(time.time() - t0, 2)

    proof_text = stdout
    if shape == "goal_file_and_proof_file" and proof_file and Path(proof_file).exists():
        proof_text = Path(proof_file).read_text()

    return {
        "schema": "leanmill-provider-invoke-v1",
        "provider": name,
        "kind": spec["kind"],
        "cost_class": spec["cost_class"],
        "returncode": rc,
        "wallclock_s": wall,
        "proof_text": proof_text,
        "proof_nonempty": bool(proof_text.strip()),
        "error": err,
        "credit_boundary": "provider output only; requires governance + matched-negative-control receipt before proof credit",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p_inv = sub.add_parser("invoke")
    p_inv.add_argument("--provider", required=True)
    p_inv.add_argument("--goal-file")
    p_inv.add_argument("--goal-text")
    p_inv.add_argument("--proof-file")
    p_inv.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    if args.cmd == "list":
        print(f"{'provider':<16}{'kind':<18}{'cost':<24}{'tested':<8}note")
        print("-" * 100)
        for name, spec in REGISTRY.items():
            print(f"{name:<16}{spec['kind']:<18}{spec['cost_class']:<24}{str(spec['tested']):<8}{spec['note'][:50]}")
        return 0

    if args.cmd == "invoke":
        result = invoke(args.provider, goal_file=args.goal_file, goal_text=args.goal_text,
                        proof_file=args.proof_file, timeout_s=args.timeout)
        print(json.dumps(result, indent=2))
        return 0 if result["proof_nonempty"] else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
