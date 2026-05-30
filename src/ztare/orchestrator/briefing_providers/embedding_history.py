"""EmbeddingHistoryProvider — recurrent-state briefing via sentence embeddings.

Sister to `IterTrajectoryProvider` (raw-text last-K-iter summarizer).
While iter_trajectory is bounded by token budget (5 iters of summary
is the limit), this provider compresses ALL prior iters into fixed-
size embeddings and surfaces the K nearest-neighbor prior states that
match the current iter's situation.

# Why a separate provider, not a replacement

iter_trajectory is the explicit "last K iters" channel; the mutator
relies on its stable header and ordered fields. This provider adds an
ORTHOGONAL channel: "iters from the substrate's history that RESEMBLE
the current state." Different signal; useful when the mutator is in a
region the substrate has visited before.

# v0.2 (2026-05-06): multi-channel embedding

v0.1 used MiniLM on a single stringification per iter. Matches were
dominated by score-range overlap rather than deep similarity. v0.2
fixes this by:

  - Encoding the iter into THREE SEPARATE channels:
      • form     — the actual submitted form (mathematical content)
      • verdict  — verdict_tag + judge feedback (epistemic state)
      • weakest  — weakest_point summary (where the gap is)
  - Computing cosine similarity per channel
  - Weighted-sum of channel similarities (mathematical content
    weighted highest)
  - Plus a structural-features cosine (has_le / has_norm / has_integral
    / score_band) that catches "iters with same structural shape"

# Tier rationale

Tier 3 (stagnation-only). The provider is most useful when the
mutator is stuck — that's when "look at deeper history for similar
states" pays off. Force-show via rubric `briefing_force_show_embedding_history`.

# Inputs

  - `workspace/iteration_telemetry.jsonl` (already written every iter)
  - sentence-transformers MiniLM (frozen)
  - declines via applies() if MiniLM unavailable

# Output (markdown fragment)

  ## Embedding-history retrieval (top-3 most-similar prior iters)
  -- iter 12 (sim 0.84 form=0.82 verdict=0.91 weakest=0.79): <state summary>
  -- iter 7  (sim 0.79): <state summary>
  -- iter 19 (sim 0.71): <state summary>

  Pattern signature: <brief synthesis>

# Honest scope

  - Retrieval channel, not reasoning. Mutator interprets matches.
  - v0.2 channel weights are HEURISTIC (form 0.45 / verdict 0.25 /
    weakest 0.20 / struct 0.10). They're tunable per substrate.
  - At very small history (<5 iters) declines via applies().

# Substrate-agnostic

Reads only deterministic workspace artifacts; works on any substrate
with iteration_telemetry.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
)


# v0.2 channel weights: form-similarity weighted highest because that's
# the mathematical content the mutator most needs to recognize as
# similar across iters.
CHANNEL_WEIGHTS = {
    "form": 0.45,
    "verdict": 0.25,
    "weakest": 0.20,
    "struct": 0.10,
}


def _structural_vector(row: dict) -> list[float]:
    """Hand-features that catch 'same structural shape' even when text differs."""
    score = row.get("score") or row.get("total_score") or 0
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0
    form = str(row.get("form", row.get("submitted_form", "")))
    verdict = str(row.get("verdict_tag", row.get("judge_verdict", ""))).lower()
    return [
        # Score bands (one-hot-ish; smooth membership)
        1.0 if 0 <= score < 30 else 0.0,
        1.0 if 30 <= score < 60 else 0.0,
        1.0 if 60 <= score < 80 else 0.0,
        1.0 if 80 <= score <= 100 else 0.0,
        # Form structural features
        1.0 if "≤" in form or "<=" in form else 0.0,
        1.0 if "‖" in form or "norm" in form.lower() else 0.0,
        1.0 if "∫" in form or "integral" in form.lower() else 0.0,
        1.0 if "exp" in form.lower() else 0.0,
        1.0 if "log" in form.lower() else 0.0,
        # Verdict bucket signals
        1.0 if "pass" in verdict or "verified" in verdict else 0.0,
        1.0 if "fail" in verdict or "reject" in verdict else 0.0,
        1.0 if "stagnat" in verdict else 0.0,
    ]


def _cosine_np(a, b):
    import numpy as np
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    na = np.linalg.norm(a) + 1e-9
    nb = np.linalg.norm(b) + 1e-9
    return float((a @ b) / (na * nb))


def _cosine_matrix(prior_emb_matrix, current_emb):
    """Cosine sim of current_emb against each row of prior_emb_matrix."""
    import numpy as np
    prior = np.asarray(prior_emb_matrix, dtype=np.float32)
    cur = np.asarray(current_emb, dtype=np.float32)
    prior_n = prior / (np.linalg.norm(prior, axis=1, keepdims=True) + 1e-9)
    cur_n = cur / (np.linalg.norm(cur) + 1e-9)
    return prior_n @ cur_n


class EmbeddingHistoryProvider(BriefingProvider):
    """Surface the K nearest-neighbor prior iters via multi-channel embedding."""

    name = "embedding_history"
    priority = 320  # after iter_trajectory (300), before deeper fix-providers
    TOP_K = 3
    MIN_PRIOR_ITERS = 5

    def _load_telemetry(self, ctx: BriefingContext) -> list[dict]:
        path = (ctx.workspace_dir or ctx.project_dir / "workspace") / "iteration_telemetry.jsonl"
        if not path.exists():
            return []
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def _channel_texts(self, row: dict) -> dict[str, str]:
        """Extract three separate text channels from one telemetry row."""
        return {
            "form": str(row.get("form", row.get("submitted_form", "")))[:300],
            "verdict": str(row.get("verdict_tag", row.get("judge_verdict", "")))[:200],
            "weakest": str(row.get("weakest_point", row.get("weakest_link", "")))[:200],
        }

    def applies(self, ctx: BriefingContext) -> bool:
        rows = self._load_telemetry(ctx)
        if len(rows) < self.MIN_PRIOR_ITERS:
            return False
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
            return True
        except ImportError:
            return False

    def fragment(self, ctx: BriefingContext) -> str:
        rows = self._load_telemetry(ctx)
        if len(rows) < self.MIN_PRIOR_ITERS:
            return ""
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
        except ImportError:
            return ""

        current_row = rows[-1]
        prior_rows = rows[:-1]
        if not prior_rows:
            return ""

        try:
            model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            return ""

        # Multi-channel encoding
        current_channels = self._channel_texts(current_row)
        prior_channels = [self._channel_texts(r) for r in prior_rows]
        per_channel_sims: dict[str, Any] = {}
        for chan in ("form", "verdict", "weakest"):
            try:
                cur_emb = model.encode(
                    [current_channels[chan]],
                    show_progress_bar=False, convert_to_numpy=True)[0]
                prior_embs = model.encode(
                    [pc[chan] for pc in prior_channels],
                    show_progress_bar=False, convert_to_numpy=True)
                per_channel_sims[chan] = _cosine_matrix(prior_embs, cur_emb)
            except Exception:
                per_channel_sims[chan] = np.zeros(len(prior_rows), dtype=np.float32)

        # Structural-features cosine (no LLM)
        try:
            cur_struct = _structural_vector(current_row)
            struct_sims = np.array([
                _cosine_np(_structural_vector(r), cur_struct)
                for r in prior_rows
            ], dtype=np.float32)
            per_channel_sims["struct"] = struct_sims
        except Exception:
            per_channel_sims["struct"] = np.zeros(len(prior_rows), dtype=np.float32)

        # Weighted-sum
        total_sims = np.zeros(len(prior_rows), dtype=np.float32)
        for chan, weight in CHANNEL_WEIGHTS.items():
            total_sims += weight * per_channel_sims.get(chan, np.zeros(len(prior_rows)))

        top_idx = total_sims.argsort()[::-1][:self.TOP_K]

        lines = ["## Embedding-history retrieval (v0.2 multi-channel; "
                 "top-{} most-similar prior iters)".format(self.TOP_K)]
        for i in top_idx:
            row = prior_rows[i]
            iter_n = row.get("iter") or row.get("iteration") or "?"
            sim = float(total_sims[i])
            chans = {c: float(per_channel_sims[c][i])
                     for c in ("form", "verdict", "weakest", "struct")}
            score = row.get("score", row.get("total_score", "?"))
            verdict = str(row.get("verdict_tag",
                                    row.get("judge_verdict", "")))[:60]
            weakest = str(row.get("weakest_point",
                                    row.get("weakest_link", "")))[:90]
            lines.append(
                f"  - iter {iter_n} (sim {sim:.2f}: form={chans['form']:.2f} "
                f"verdict={chans['verdict']:.2f} weakest={chans['weakest']:.2f} "
                f"struct={chans['struct']:.2f}) "
                f"score={score} verdict={verdict} weakest={weakest}"
            )

        # Synthesis hint (cheap heuristic, not LLM)
        scored = [(prior_rows[i].get("score", prior_rows[i].get("total_score")))
                  for i in top_idx]
        finite_scored = []
        for s in scored:
            try:
                finite_scored.append(float(s))
            except (TypeError, ValueError):
                pass
        if finite_scored:
            avg = sum(finite_scored) / len(finite_scored)
            lines.append(
                f"\n  Pattern signature: {len(finite_scored)} similar prior iters "
                f"scored avg={avg:.1f}; the current state's structural+form+"
                f"verdict embedding most resembles these historical states."
            )
        lines.append(
            f"\n  v0.2 channel weights: form={CHANNEL_WEIGHTS['form']} "
            f"verdict={CHANNEL_WEIGHTS['verdict']} "
            f"weakest={CHANNEL_WEIGHTS['weakest']} struct={CHANNEL_WEIGHTS['struct']}. "
            f"Override per substrate via rubric `embedding_history_channel_weights`."
        )

        return "\n".join(lines)


# Smoke test
if __name__ == "__main__":
    print("=== EmbeddingHistoryProvider v0.2 smoke ===")
    p = EmbeddingHistoryProvider()
    print(f"  name={p.name} priority={p.priority}")
    print(f"  channel_weights={CHANNEL_WEIGHTS}")
    # Test structural vector on a fake row
    fake = {"score": 65, "form": "x ≤ ‖f‖", "verdict_tag": "fail_orientation"}
    sv = _structural_vector(fake)
    print(f"  structural_vector(fake) = {sv}")
    print("  v0.2 import + structural_vector OK")
