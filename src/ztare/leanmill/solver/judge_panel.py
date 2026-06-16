#!/usr/bin/env python3
"""Diverse-family judge PANEL + Dawid–Skene reliability weighting — the "judge-diversity panel" (approved
2026-06-15), the wiring follow-up to the #116 Dawid–Skene estimator (`judge_reliability.py`).

THE PROBLEM IT FIXES. The round-trip faithfulness judge (`autoformalize.default_directional_judge`) polled
N *samples of ONE model* (gemini) and took a strict majority — variance reduction only, NOT error
decorrelation. MEASURED failure mode (2026-06-15 faithfulness pilot, live judge): a single steelmanned judge
false-rejected **5/6 FAITHFUL** statements (the firewall's real edge is precision, and the single judge is
the weak leg). N samples of the same model share that model's systematic over-strictness.

THE PANEL. Poll K *different* model families (gemini / deepseek / …) so their errors decorrelate, then
aggregate:
  • with NO reliability history → STRICT MAJORITY over the live judges (≥3 judges ⇒ one chronically
    over-rejecting judge can no longer VETO a faithful statement — the immediate false-reject fix);
  • with history → Dawid–Skene EM (`judge_reliability.dawid_skene`) estimates each judge's sensitivity/
    specificity WITHOUT an oracle and `weighted_verdict` down-weights the flaky judge.

SOUNDNESS (why a firewall change is safe here). This judge only moves the *faithful-admit / false-reject*
margin. The deterministic `statement_integrity` carrier still OVERRIDES the LLM verdict in production
(`autoformalize`), so NO structural launder (=→≤, dropped hypothesis, ∀→∃) can be admitted by a panel vote —
the panel cannot loosen the no-false-admit floor, only reduce false-rejections of genuinely faithful ones.
All judges dead ⇒ INADMISSIBLE ⇒ fail-CLOSED (reject), never admit on no evidence
(see [[feedback_self_learning_needs_data_admissibility]], [[feedback_claude_subscription_not_metered_api]]).

Default-OFF (`ZTARE_LEANMILL_JUDGE_PANEL`); off ⇒ byte-parity with the single-model majority. PURE-mechanism
+ injectable dispatch/store so the selftest needs no live LLM. Reuses `judge_reliability` (no reimplemented EM).

  python -m ztare.leanmill.solver.judge_panel --selftest
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, Optional

from ztare.leanmill.solver.judge_reliability import dawid_skene, weighted_verdict

# Default panel: ≥3 votes so a single over-rejecting judge cannot veto, across ≥2 families (gemini + deepseek
# are the llm_runtime API families known-wired; NEVER a metered claude/codex call — same rule as `_api_text`).
# Overridable via ZTARE_LEANMILL_JUDGE_PANEL_MODELS (comma-separated llm_runtime model ids).
_DEFAULT_MODELS = "gemini-3.1-pro-preview,deepseek-chat,gemini-2.5-flash"


def panel_enabled() -> bool:
    return os.environ.get("ZTARE_LEANMILL_JUDGE_PANEL", "0") == "1"


def panel_models() -> "list[str]":
    raw = os.environ.get("ZTARE_LEANMILL_JUDGE_PANEL_MODELS", _DEFAULT_MODELS)
    return [m.strip() for m in raw.split(",") if m.strip()]


def _store_path() -> Path:
    p = os.environ.get("ZTARE_LEANMILL_JUDGE_PANEL_STORE")
    if p:
        return Path(p)
    return Path(__file__).resolve().parents[4] / "analytics" / "public" / "leanmill" / "judge_panel_votes.jsonl"


class JudgeVoteStore:
    """Append-only JSONL of per-judge votes `{judge, item, vote}` — the Dawid–Skene SUBSTRATE (the latent
    truth is unknown; DS estimates reliabilities from the votes alone). `reliabilities()` runs the EM over
    everything accumulated. Best-effort IO: a broken store NEVER blocks the gate (falls back to majority)."""

    def __init__(self, path: "str | Path | None" = None):
        self.path = Path(path) if path is not None else _store_path()

    def record(self, item: str, votes: "dict[str, bool]") -> bool:
        if not votes:
            return False
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                for judge, v in votes.items():
                    fh.write(json.dumps({"judge": judge, "item": item, "vote": bool(v)}, ensure_ascii=True) + "\n")
            return True
        except Exception:  # noqa: BLE001 — telemetry must never break the firewall
            return False

    def _load_votes(self) -> "dict[str, dict[str, bool]]":
        votes: "dict[str, dict[str, bool]]" = {}
        try:
            if not self.path.exists():
                return votes
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                    votes.setdefault(r["judge"], {})[r["item"]] = bool(r["vote"])
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            return {}
        return votes

    def reliabilities(self, *, min_items: int = 8) -> "Optional[dict]":
        """Learned {judge: {sensitivity, specificity, n}} via Dawid–Skene, or None when there is too little
        history to trust the estimate (then the caller uses the equal-weight majority — parity)."""
        votes = self._load_votes()
        items = {i for j in votes.values() for i in j}
        if len(votes) < 2 or len(items) < min_items:
            return None
        ds = dawid_skene(votes)
        return ds.get("judges") if ds else None


def aggregate(votes_for_item: "dict[str, bool]", reliabilities: "Optional[dict]") -> "tuple[bool, float, str]":
    """Combine the live judges' votes. Returns (faithful, posterior, method).
    DS-weighted iff a trusted reliability table is supplied; else STRICT MAJORITY (fail-closed on a tie —
    the no-false-admit direction for a faithfulness firewall, exactly the #105 single-model behaviour)."""
    if not votes_for_item:
        return False, 0.0, "no-live-judges"
    if reliabilities:
        faithful, post = weighted_verdict(votes_for_item, reliabilities)
        return faithful, post, "dawid_skene"
    n = len(votes_for_item)
    yes = sum(1 for v in votes_for_item.values() if v)
    faithful = (yes * 2 > n)                                  # strict majority; tie ⇒ reject (fail-closed)
    return faithful, round(yes / n, 4), "majority"


def panel_judge(orig_nl: str, back_nl: str, *, prompt_template: str,
                dispatch: "Callable[[str, str], str]",
                models: "Optional[list[str]]" = None,
                store: "Optional[JudgeVoteStore]" = None,
                parse_yes: "Optional[Callable[[str], Optional[bool]]]" = None) -> "tuple[bool, dict]":
    """Poll a diverse model panel for the directional-faithfulness verdict and aggregate (DS-weighted or
    majority). Returns (faithful, telemetry). `dispatch(prompt, model) -> raw_text`; a dead judge (empty
    text) casts NO vote. ALL dead ⇒ fail-closed. `parse_yes(raw) -> True/False/None` overrides the default
    'first line starts EQUIVALENT' parser. Pure — no env/LLM/IO except via the injected dispatch/store."""
    models = models or panel_models()
    store = store if store is not None else JudgeVoteStore()
    prompt = prompt_template.format(orig_nl=orig_nl, back_nl=back_nl)

    def _default_parse(raw: str) -> "Optional[bool]":
        if not raw:
            return None
        first = raw.upper().splitlines()[0].strip() if raw.strip() else ""
        if first.startswith("EQUIVALENT"):
            return True
        if first.startswith("NOT") or first.startswith("UNFAITHFUL") or first.startswith("NO"):
            return False
        return None  # unparseable ⇒ no vote (don't guess)

    parse = parse_yes or _default_parse
    votes: "dict[str, bool]" = {}
    raws: "list[str]" = []
    for m in models:
        raw = (dispatch(prompt, m) or "").strip()
        raws.append(f"{m}:{raw[:60]}")
        v = parse(raw)
        if v is not None:
            votes[m] = v
    item_key = f"{hash((orig_nl, back_nl)) & 0xFFFFFFFF:08x}"
    store.record(item_key, votes)
    reliab = store.reliabilities()
    faithful, post, method = aggregate(votes, reliab)
    tel = {"models": models, "live_votes": votes, "n_live": len(votes), "method": method,
           "posterior": post, "faithful": faithful, "item": item_key, "raw": raws}
    return faithful, tel


# --------------------------------------------------------------------------------------------------------
def _selftest() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    PT = "{orig_nl} :: {back_nl}"  # trivial template for the selftest

    def mk_dispatch(table):
        """table[model] -> 'EQUIVALENT' / 'NOT EQUIVALENT' / '' (dead)."""
        return lambda prompt, model: table.get(model, "")

    with tempfile.TemporaryDirectory() as td:
        store = JudgeVoteStore(Path(td) / "votes.jsonl")

        # 1) DIVERSITY breaks the single-veto: 1 over-rejecter + 2 faithful-correct ⇒ majority ADMITS faithful.
        f, tel = panel_judge("x", "x", prompt_template=PT, store=store,
                             models=["a", "b", "c"],
                             dispatch=mk_dispatch({"a": "NOT EQUIVALENT", "b": "EQUIVALENT", "c": "EQUIVALENT"}))
        ok("3-judge majority admits faithful despite 1 over-rejecter", f is True and tel["method"] == "majority")

        # 2) launder caught: majority says NOT EQUIVALENT ⇒ reject.
        f2, _ = panel_judge("x", "y", prompt_template=PT, store=store, models=["a", "b", "c"],
                            dispatch=mk_dispatch({"a": "NOT EQUIVALENT", "b": "NOT EQUIVALENT", "c": "EQUIVALENT"}))
        ok("majority catches a launder (2 NOT vs 1)", f2 is False)

        # 3) all judges dead ⇒ fail-CLOSED (no admit on no evidence).
        f3, tel3 = panel_judge("x", "x", prompt_template=PT, store=store, models=["a", "b"],
                              dispatch=mk_dispatch({}))
        ok("all-dead panel fails closed (reject)", f3 is False and tel3["n_live"] == 0)

        # 4) tie ⇒ reject (fail-closed), 2 judges split.
        f4, _ = panel_judge("x", "x", prompt_template=PT, store=store, models=["a", "b"],
                            dispatch=mk_dispatch({"a": "EQUIVALENT", "b": "NOT EQUIVALENT"}))
        ok("tie rejects (fail-closed)", f4 is False)

    # 5) DS-weighting: with accumulated history, a reliable minority outvotes a chronically-flaky judge.
    #    Build a store where 'good1','good2' track truth and 'flaky' is a coin, then a fresh item where the
    #    two good judges say EQUIVALENT and flaky says NOT — DS should ADMIT (down-weight flaky).
    import random
    with tempfile.TemporaryDirectory() as td:
        store = JudgeVoteStore(Path(td) / "votes.jsonl")
        rt = random.Random(7)
        truth = {f"it{k}": rt.random() < 0.5 for k in range(60)}
        def _mk(seed, acc):
            r = random.Random(seed)
            return {it: (tv if r.random() < acc else not tv) for it, tv in truth.items()}
        gv1, gv2, fv = _mk(1, 0.95), _mk(2, 0.95), _mk(3, 0.5)
        for it in truth:
            store.record(it, {"good1": gv1[it], "good2": gv2[it], "flaky": fv[it]})
        reliab = store.reliabilities()
        ok("DS reliabilities learned from history (table non-empty)", bool(reliab) and "good1" in reliab)
        faithful, post, method = aggregate({"good1": True, "good2": True, "flaky": False}, reliab)
        ok(f"DS down-weights the flaky judge (admit on reliable 2; method={method})",
           faithful is True and method == "dawid_skene")
        # reliable judges should out-rank the coin
        rel = {j: (reliab[j]["sensitivity"] + reliab[j]["specificity"]) / 2 for j in reliab}
        ok("learned reliability: good judges > flaky", rel["good1"] > rel["flaky"] and rel["good2"] > rel["flaky"])

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print("judge_panel: diverse-family faithfulness panel + Dawid–Skene weighting. Run --selftest.")
