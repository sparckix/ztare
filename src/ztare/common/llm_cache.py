"""LLMCallCache — workspace-local cache for deterministic LLM call sites.

Single source of truth for caching expensive LLM calls (cold-LLM Erdős
seed, evidence gap enrichment, future Research Director triangulation,
etc.). Built 2026-04-28 to replace ad-hoc per-callsite cache logic that
was beginning to repeat across modules.

Invalidation model — outcome-driven, not calendar-driven
--------------------------------------------------------

A science apparatus with rich telemetry should invalidate caches
based on what the science says, not on wall-clock time. The cache
invalidates when ANY of the following triggers fire:

1. **Input content (primary gate)** — an SHA-256 of the call's
   inputs is the primary key. If substrate features, rubric flags, or
   model id changes, the hash changes and the cache misses correctly.
   This is the load-bearing invalidation; everything below is a
   safety net.

2. **Prompt template version** — each call site declares an integer
   `prompt_template_version`. Bump this number when the prompt's
   structural/behavioral expectations change. Cached entries stamped
   with an older version are rejected.

3. **Consumption count (outcome-driven)** — every time a cached
   payload is used AND the downstream apparatus records "no useful
   outcome" (e.g., proposals were considered and none broke
   stagnation; cold-seed candidates were tried and all rejected),
   the caller invokes `mark_consumed_unsuccessfully()`. After
   `max_unsuccessful_consumptions` (default 3), the cache is treated
   as stale and the next lookup misses, forcing a fresh LLM call.
   Rationale: if the same proposals haven't helped the run move
   after 3 consumption attempts, repeat consumption is unlikely to
   help; spend the LLM tokens on a fresh proposal set instead.

4. **Operator force-refresh** — passing the rubric flag named in
   `force_refresh_flag` bypasses the lookup for this call. Useful
   when the operator has reason to believe the LLM's training
   surface has shifted in a way the input hash can't see (e.g.,
   provider-side silent model update with the same model_id).

5. **TTL (optional safety net)** — entries older than `ttl_seconds`
   are rejected. **DEFAULT: `ttl_never`** because for deterministic
   apparatus inputs the wall-clock age of the cached payload is
   irrelevant — same inputs ⇒ same answer. Per-callsite override
   available for cases where the LLM's behavior is known to drift
   over time (rare; most ZTARE call sites don't need this).

The cache is intentionally conservative: hits should produce output
that an operator would accept as "the same answer the LLM would have
given again now, modulo non-deterministic sampling jitter." If that's
not a reasonable assumption for a call site, the right answer is NOT
to use this cache — it is to redesign the call site so its inputs
fully determine its output.

Storage
-------
- One JSON file per call site, under `workspace/.llm_cache/<callsite>.json`.
- File schema:
    {
      "callsite": "<str>",
      "input_hash": "<sha256-16>",
      "prompt_template_version": <int>,
      "model_id_used": "<str>",
      "stored_utc": "<ISO8601>",
      "payload": <whatever the call returned>
    }
- Atomic write via tempfile + rename, so a Ctrl-C in the middle of a
  cache write doesn't corrupt the file.

Usage (procedural — no decorator, opt-in per call site)
-------------------------------------------------------

  from src.ztare.common.llm_cache import LLMCallCache, ttl_30_days

  cache = LLMCallCache(
      callsite="evidence_gap_enrichment",
      project_dir=Path(project_dir),
      prompt_template_version=1,
      ttl_seconds=ttl_30_days,
      force_refresh_flag="evidence_gap_force_refresh",
  )

  cache_key = cache.compute_key({
      "critique_collapses": collapses,
      "forbidden_domain": rubric.get("forbidden_domain"),
      "substrate_class_key": rubric.get("substrate_class_key"),
      "model_id": resolved_model_id,
  })

  hit = cache.lookup(cache_key, rubric_data=rubric)
  if hit is not None:
      return hit  # cached payload

  payload = expensive_llm_call(...)
  cache.store(cache_key, payload, model_id_used=resolved_model_id)
  return payload

The deliberately verbose API keeps the cache visible at the call site —
no decorator magic that might silently change the call's behavior.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Convenience TTL constants. Calibration ranges, not hard rules.
ttl_1_hour: int = 3600
ttl_1_day: int = 86_400
ttl_7_days: int = 86_400 * 7
ttl_30_days: int = 86_400 * 30
ttl_never: int = 10**12  # ~32k years — effectively no TTL


@dataclass
class LLMCallCache:
    """Workspace-local cache for one LLM call site.

    Caller computes the input hash via `compute_key`, then asks
    `lookup` for a hit. On miss, caller does the LLM work and calls
    `store`. When the apparatus has used the cached payload and
    determined it did not produce useful progress, the caller invokes
    `mark_consumed_unsuccessfully()` so the cache invalidates after
    `max_unsuccessful_consumptions` such reports.

    The cache writes JSON to `workspace/.llm_cache/<callsite>.json`.

    Fields:
      callsite: short name used as the cache filename. Required.
      project_dir: project root; cache lives under `<project>/workspace/.llm_cache/`.
      prompt_template_version: bump to invalidate when prompt logic changes.
      ttl_seconds: optional max age. Default `ttl_never` because input-
        content hash is the right invalidation gate for deterministic
        apparatus calls; TTL is a per-callsite safety net only.
      max_unsuccessful_consumptions: invalidate after this many
        outcome-driven "didn't help" reports. Default 3.
      force_refresh_flag: rubric key that, when True, bypasses lookup.
    """
    callsite: str
    project_dir: Path
    prompt_template_version: int = 1
    ttl_seconds: int = ttl_never
    max_unsuccessful_consumptions: int = 3
    force_refresh_flag: Optional[str] = None
    _file_override: Optional[Path] = field(default=None, repr=False)

    @property
    def file(self) -> Path:
        if self._file_override is not None:
            return self._file_override
        d = self.project_dir / "workspace" / ".llm_cache"
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{self.callsite}.json"

    def compute_key(self, inputs: dict) -> str:
        """Hash a dict of inputs into a short cache key.

        Inputs MUST be JSON-serializable. Sort keys for determinism.
        Use `default=str` so non-trivial objects (Path, datetime) are
        coerced to strings rather than failing.
        """
        canonical = json.dumps(
            inputs, sort_keys=True, default=str, ensure_ascii=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def lookup(
        self,
        input_hash: str,
        *,
        rubric_data: Optional[dict] = None,
    ) -> Optional[Any]:
        """Return the cached payload if and only if every invalidation
        gate passes. Returns None on any miss kind.
        """
        # Gate 1: operator force-refresh.
        if rubric_data and self.force_refresh_flag:
            if bool(rubric_data.get(self.force_refresh_flag, False)):
                logger.info(
                    "LLMCallCache[%s]: bypassed (rubric.%s=true)",
                    self.callsite, self.force_refresh_flag,
                )
                return None
        # Gate 2: file existence.
        if not self.file.exists():
            return None
        # Gate 3: parse.
        try:
            entry = json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "LLMCallCache[%s]: corrupt cache file: %s", self.callsite, exc,
            )
            return None
        # Gate 4: input-hash match.
        if entry.get("input_hash") != input_hash:
            return None
        # Gate 5: prompt template version.
        if entry.get("prompt_template_version") != self.prompt_template_version:
            logger.info(
                "LLMCallCache[%s]: stale prompt template (cache=%s, current=%d)",
                self.callsite, entry.get("prompt_template_version"),
                self.prompt_template_version,
            )
            return None
        # Gate 6: outcome-driven invalidation. After enough "didn't help"
        # reports, treat the cache as stale and force a fresh LLM call.
        unsuccessful = int(entry.get("unsuccessful_consumptions", 0))
        if unsuccessful >= self.max_unsuccessful_consumptions:
            logger.info(
                "LLMCallCache[%s]: outcome-stale (unsuccessful=%d ≥ max=%d); "
                "forcing refresh",
                self.callsite, unsuccessful, self.max_unsuccessful_consumptions,
            )
            return None
        # Gate 7: TTL (off by default since ttl_never).
        stored_utc = entry.get("stored_utc")
        if stored_utc:
            try:
                stored_dt = _dt.datetime.fromisoformat(stored_utc.replace("Z", "+00:00"))
                age = (_dt.datetime.now(_dt.timezone.utc) - stored_dt).total_seconds()
                if age > self.ttl_seconds:
                    logger.info(
                        "LLMCallCache[%s]: TTL expired (age=%.0fs > ttl=%ds)",
                        self.callsite, age, self.ttl_seconds,
                    )
                    return None
            except (ValueError, TypeError):
                pass  # malformed timestamp → fall through to hit
        logger.info(
            "LLMCallCache[%s]: HIT (hash=%s, age_check_passed)",
            self.callsite, input_hash,
        )
        return entry.get("payload")

    def store(
        self,
        input_hash: str,
        payload: Any,
        *,
        model_id_used: str = "",
    ) -> None:
        """Write the payload to the cache. Atomic via tempfile+rename."""
        entry = {
            "callsite": self.callsite,
            "input_hash": input_hash,
            "prompt_template_version": self.prompt_template_version,
            "model_id_used": model_id_used,
            "stored_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "payload": payload,
        }
        # Atomic write — write to a temp file in the same dir, then rename.
        # `os.replace` is atomic on POSIX/macOS. Avoids partial writes on
        # Ctrl-C mid-store.
        target = self.file
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=f".{self.callsite}.", suffix=".tmp", delete=False,
        ) as tf:
            json.dump(entry, tf, indent=2, default=str)
            tmp_path = Path(tf.name)
        os.replace(tmp_path, target)
        logger.info(
            "LLMCallCache[%s]: STORED (hash=%s, file=%s)",
            self.callsite, input_hash, target.name,
        )

    def invalidate(self) -> bool:
        """Delete the cache file. Returns True if a file was deleted."""
        if self.file.exists():
            self.file.unlink()
            logger.info("LLMCallCache[%s]: invalidated", self.callsite)
            return True
        return False

    def mark_consumed_unsuccessfully(self, *, note: str = "") -> int:
        """Increment the unsuccessful-consumption counter on the
        currently-cached entry. Returns the new counter value.

        Caller invokes this when the apparatus has read the cached
        payload, used it for a downstream decision, and determined
        the decision did not produce useful progress (e.g.,
        proposals exhausted without breaking stagnation; cold-seed
        candidates all rejected by the cage). After
        `max_unsuccessful_consumptions` such reports, lookups return
        None until the cache is refreshed.
        """
        if not self.file.exists():
            return 0
        try:
            entry = json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 0
        entry["unsuccessful_consumptions"] = (
            int(entry.get("unsuccessful_consumptions", 0)) + 1
        )
        if note:
            entry.setdefault("consumption_notes", []).append({
                "utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "note": note,
            })
        self.file.write_text(json.dumps(entry, indent=2, default=str))
        new_count = entry["unsuccessful_consumptions"]
        logger.info(
            "LLMCallCache[%s]: marked unsuccessful (%d/%d)",
            self.callsite, new_count, self.max_unsuccessful_consumptions,
        )
        return new_count

    def mark_consumed_successfully(self, *, note: str = "") -> int:
        """Reset the unsuccessful-consumption counter to 0.

        Caller invokes this when the apparatus consumed the cached
        payload AND a downstream success metric registered (champion
        improved, stagnation broken, falsification yielded a
        publishable null). The cache stays valid; future iters can
        keep using the same payload.

        Returns the prior unsuccessful count (so the caller knows how
        many strikes were forgiven).
        """
        if not self.file.exists():
            return 0
        try:
            entry = json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 0
        prior = int(entry.get("unsuccessful_consumptions", 0))
        if prior == 0 and not note:
            return 0  # nothing to do
        entry["unsuccessful_consumptions"] = 0
        if note:
            entry.setdefault("consumption_notes", []).append({
                "utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "note": note,
                "kind": "successful_reset",
            })
        self.file.write_text(json.dumps(entry, indent=2, default=str))
        if prior > 0:
            logger.info(
                "LLMCallCache[%s]: counter reset (%d → 0; %d strikes forgiven)",
                self.callsite, prior, prior,
            )
        return prior


# ─────────────────────────────────────────────────────────────────────
# Post-iter outcome-driven invalidation hook
# ─────────────────────────────────────────────────────────────────────

def update_caches_post_iter(
    project_dir: Path,
    *,
    iter_index: int,
    champion_improved: bool,
    callsites: Optional[list[str]] = None,
) -> dict:
    """Post-iter hook: walk every cache file under `<project>/workspace/.llm_cache/`
    and update each entry's outcome counter based on whether the iter
    improved the champion.

    Behavior:
      - champion_improved=True  → reset every cache's unsuccessful counter
        (the cache contributed to a successful iter).
      - champion_improved=False → increment every cache's unsuccessful
        counter (the cache contributed to a stagnant iter).

    Args:
      project_dir: project root containing `workspace/.llm_cache/`.
      iter_index: 0-based iter index, recorded in the consumption note
        for audit traceability.
      champion_improved: did the post-iter score-update reflect a real
        improvement over the prior champion? Caller computes this from
        iteration_telemetry.
      callsites: optional list of callsite names to update; default is
        every cache file in the directory.

    Returns:
      A dict {callsite: new_counter_value} for each cache touched. Used
      by the caller's logging.
    """
    cache_dir = project_dir / "workspace" / ".llm_cache"
    if not cache_dir.exists():
        return {}
    out: dict[str, int] = {}
    for f in sorted(cache_dir.glob("*.json")):
        callsite = f.stem
        if callsites is not None and callsite not in callsites:
            continue
        cache = LLMCallCache(callsite=callsite, project_dir=project_dir)
        note = f"iter {iter_index} — {'champion improved' if champion_improved else 'no champion improvement'}"
        if champion_improved:
            cache.mark_consumed_successfully(note=note)
            out[callsite] = 0
        else:
            new_count = cache.mark_consumed_unsuccessfully(note=note)
            out[callsite] = new_count
    return out
