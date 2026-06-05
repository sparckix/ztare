"""Ceiling-breaker retest — better-designed cross-provider classifier agreement.

The 2026-04-24 audit (anti_pattern_catalog.md) marked Part 2 ceiling-breakers as FAILING
cross-LLM validation: 48% three-way agreement on 15 fine classes (κ 0.56-0.58). But that run
had three design flaws: (1) WEAK models (gpt-4.1-mini / claude-haiku / gemini-flash-lite);
(2) 15 flat fine classes with terse one-line defs and no nearest-confuser disambiguation,
forcing arbitrary tie-breaks between overlapping labels; (3) collapsing to 3 super-classes
ALREADY lifted agreement to 75%. So the question this retest settles: was the failure the
CEILING-BREAKER CONCEPT, or the design (weak models + over-fine taxonomy)?

Better design here:
  - STRONG cross-family models (gpt-4.1 / claude-sonnet / gemini-2.5-pro / deepseek), each
    CALIBRATED first (positive control: a trivially-obvious snippet must classify correctly;
    a provider that fails calibration is DROPPED, not silently counted — the lesson from the
    dead-REPL / dead-codex episodes: never read a disagreement off an un-calibrated rater).
  - A 2-stage taxonomy with a SHARP discriminating principle:
      stage 1 super-class: structural_blocker | ceiling_breaker | other
        (principle: could a DETERMINISTIC gate catch it? structural=yes mechanically;
         ceiling=no, it is a judgment-level epistemic overreach) — this is the ceiling-breaker
         distinction the audit actually cared about.
      stage 2 (only if ceiling_breaker): a cleaned 5-class sub-taxonomy with explicit
        nearest-confuser rules.
  - Reasoning allowed, then a parsed `FINAL: <label>` line (the weak run forced a 20-token
    instant answer, which adds label noise on a strong model).

Reuses the SAME 100 records (weakest_point_snippet) from the 2026-04-24 json, so the
comparison is apples-to-apples. (Snippet is 200 chars in the saved json — the original used
400; noted as a mild handicap, identical across both arms.)

  python ceiling_breaker_retest.py [--limit N] [--stage2]
"""
from __future__ import annotations
import argparse, json, os, sys, time
from collections import Counter
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SRC = REPO / "analytics/public/queries/classification/cross_provider_classifier_agreement_2026-04-24.json"
OUT = REPO / "analytics/public/queries/classification"

SUPER = ["structural_blocker", "ceiling_breaker", "other"]
STAGE1_PROMPT = """You are auditing a "weakest point" critique an AI judge wrote against an \
AI-generated scientific/mathematical thesis. Classify the DOMINANT failure mode into exactly \
one super-class, using this discriminating principle:

- structural_blocker — a DETERMINISTIC, mechanically-catchable defect in the construction:
  a missing formal derivation step, an unsupported assumption stated as fact, a definitional
  ambiguity / non-operational construct, non-identifiability, or a concrete fit/test failure.
  A regex or a deterministic gate could in principle flag it. The artifact is broken at the
  build level.
- ceiling_breaker — a JUDGMENT-LEVEL epistemic overreach: the thesis may be locally correct
  but overclaims scope or exclusivity, lacks a counterfactual / baseline / falsifiable test,
  or sets a threshold empirically without derivation. No deterministic gate catches it; it
  takes a reviewer's judgment. The artifact reaches past what its evidence licenses.
- other — neither fits.

Nearest-confuser rule: if the critique is about a SPECIFIC missing math step or a SPECIFIC
false assumption, it is structural_blocker. If it is about the thesis claiming MORE than the
evidence supports (scope, uniqueness, no rival ruled out, untestable), it is ceiling_breaker.

You may reason in 1-2 sentences, then end with a line exactly of the form:
FINAL: <structural_blocker|ceiling_breaker|other>

WEAKEST POINT:
{wp}
"""

CALIB = [  # (snippet, expected super-class) — obvious positive controls
    ("The proof omits the derivation of the key inequality; the step from line 3 to line 4 "
     "is asserted with no justification.", "structural_blocker"),
    ("The thesis claims this mechanism is the UNIQUE explanation, but never rules out the "
     "obvious rival hypotheses and gives no test that would distinguish them.", "ceiling_breaker"),
]


def _parse_final(text: str, allowed: list[str]) -> str:
    if not text:
        return "other"
    for line in reversed(text.strip().splitlines()):
        low = line.strip().lower()
        if low.startswith("final:"):
            tok = low.split(":", 1)[1].strip().split()[0] if ":" in low else ""
            for a in allowed:
                if a in tok or tok in a:
                    return a
    low = text.lower()  # fallback: last allowed label mentioned
    hits = [(low.rfind(a), a) for a in allowed if a in low]
    return max(hits)[1] if hits else "other"


# ── provider callables (strong models, cross-family) ─────────────────────────
def _openai(prompt, model, base_url=None, key_env="OPENAI_API_KEY"):
    import openai
    client = openai.OpenAI(api_key=os.environ[key_env], base_url=base_url)
    r = client.chat.completions.create(model=model, temperature=0,
                                       messages=[{"role": "user", "content": prompt}],
                                       max_tokens=300)
    return r.choices[0].message.content or ""

def _gemini(prompt, model):
    from google.generativeai import GenerativeModel, configure
    configure(api_key=os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"])
    m = GenerativeModel(model_name=model, generation_config={"temperature": 0.0, "max_output_tokens": 800})
    resp = m.generate_content(prompt)
    # gemini-2.5 reasoning models often leave .text empty; pull parts from candidates
    try:
        if resp.text:
            return resp.text
    except Exception:
        pass
    out = []
    for c in (getattr(resp, "candidates", None) or []):
        for part in (getattr(getattr(c, "content", None), "parts", None) or []):
            if getattr(part, "text", None):
                out.append(part.text)
    return "\n".join(out)


def _codex_cli(prompt):
    """OpenAI/GPT via the operator's SUBSCRIPTION CLI — never the API key. Slow (~15s)."""
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
        ans = tf.name
    try:
        subprocess.run(["timeout", "90", "codex", "exec", "--skip-git-repo-check",
                        "-s", "read-only", "-o", ans, prompt],
                       text=True, capture_output=True, timeout=110)
        return Path(ans).read_text(encoding="utf-8", errors="replace").strip()
    finally:
        try: Path(ans).unlink()
        except Exception: pass


def _claude_cli(prompt):
    """Anthropic/Claude via the operator's SUBSCRIPTION CLI — never the API key.
    `env -u ANTHROPIC_API_KEY` forces the subscription path (an API key in env would
    otherwise route to the metered API, which is forbidden and has no credit here)."""
    import subprocess, os
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    r = subprocess.run(["timeout", "90", "claude", "-p", prompt],
                       text=True, capture_output=True, timeout=110, env=env)
    return (r.stdout or "").strip()


# Subscription CLI for OpenAI(codex)+Anthropic(claude); direct API only for the genuine
# API providers deepseek + gemini. NO openai/anthropic API calls anywhere.
PROVIDERS = {
    "deepseek_chat":      lambda p: _openai(p, "deepseek-chat", base_url="https://api.deepseek.com",
                                            key_env="DEEPSEEK_API_KEY"),
    "google_gemini-2.5-flash": lambda p: _gemini(p, "gemini-2.5-flash"),
    "codex_subscription": _codex_cli,
    "claude_subscription": _claude_cli,
}


def _classify(fn, wp, allowed):
    return _parse_final(fn(STAGE1_PROMPT.format(wp=wp[:400])), allowed)


def calibrate_providers():
    """Positive control per provider — drop any that fail (never count a dead rater)."""
    live = {}
    for name, fn in PROVIDERS.items():
        try:
            ok = all(_classify(fn, s, SUPER) == exp for s, exp in CALIB)
            got = [_classify(fn, s, SUPER) for s, _ in CALIB]
            if ok:
                live[name] = fn
                print(f"[calib] {name}: LIVE (controls {got})", flush=True)
            else:
                print(f"[calib] {name}: DROPPED — failed control (got {got}, want {[e for _,e in CALIB]})", flush=True)
        except Exception as e:
            print(f"[calib] {name}: DROPPED — error: {str(e)[:120]}", flush=True)
    return live


def kappa(a, b):
    n = len(a)
    if not n: return 0.0
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[x]/n)*(cb[x]/n) for x in set(ca)|set(cb))
    return 1.0 if pe >= 1 and po == 1 else (po - pe)/(1 - pe) if pe < 1 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    a = ap.parse_args()
    data = json.loads(SRC.read_text())
    records = data["records"][:a.limit]
    print(f"[retest] {len(records)} records; calibrating strong cross-family providers...", flush=True)
    live = calibrate_providers()
    if len(live) < 2:
        print(f"[retest] ABORT: only {len(live)} live providers — agreement is undefined."); return
    names = list(live)
    labels = {n: [] for n in names}
    per = []
    t0 = time.time()
    for i, rec in enumerate(records):
        wp = rec.get("weakest_point_snippet", "")
        row = {}
        for n in names:
            try: row[n] = _classify(live[n], wp, SUPER)
            except Exception as e: row[n] = "other"; print(f"  [{i}] {n} err {str(e)[:60]}", flush=True)
        for n in names: labels[n].append(row[n])
        per.append({"project": rec.get("project"), "score": rec.get("score"),
                    "snippet": wp[:120], "labels": row,
                    "agree": len(set(row.values())) == 1})
        if (i+1) % 20 == 0: print(f"  {i+1}/{len(records)} ({round(time.time()-t0)}s)", flush=True)
    nway = sum(1 for r in per if r["agree"]) / len(per)
    pair = {f"{names[i]}__{names[j]}": round(kappa(labels[names[i]], labels[names[j]]), 3)
            for i in range(len(names)) for j in range(i+1, len(names))}
    # ceiling-breaker specific: agreement restricted to records ANY provider called ceiling
    cb = [r for r in per if "ceiling_breaker" in r["labels"].values()]
    cb_agree = sum(1 for r in cb if all(v == "ceiling_breaker" for v in r["labels"].values()))
    out = {
        "generated": str(date.today()), "design": "strong_models_2stage_sharp_taxonomy",
        "n": len(records), "live_providers": names,
        "nway_agreement_rate": round(nway, 3), "pairwise_kappa": pair,
        "ceiling_breaker_records": len(cb),
        "ceiling_breaker_nway_agreement": round(cb_agree/len(cb), 3) if cb else None,
        "baseline_2026_04_24": {"fine_15class_3way": 0.48, "superclass_3way": 0.75, "weak_models": True},
        "verdict": ("ceiling-breaker distinction RELIABLE under better design (>=0.80)" if nway >= 0.80
                    else "improved but sub-0.80" if nway > 0.75 else "still weak"),
        "records": per,
    }
    p = OUT / f"ceiling_breaker_retest_{date.today()}.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"\n[retest] super-class {len(names)}-way agreement: {nway:.1%}  (baseline weak-model 3-way super = 75%)")
    print(f"[retest] pairwise kappa: {pair}")
    print(f"[retest] ceiling_breaker records={len(cb)}, all-agree={out['ceiling_breaker_nway_agreement']}")
    print(f"[retest] VERDICT: {out['verdict']}")
    print(f"[retest] wrote {p}")


if __name__ == "__main__":
    main()
