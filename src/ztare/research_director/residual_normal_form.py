"""Residual normal-form compiler for research-director preflight.

The core is substrate-neutral: it reads a profile that names the local
mathematical currencies, killed routes, packet/falsifier templates, and
feature vocabulary.  It then classifies a proposed residual as a likely alias,
strictly narrower/stronger branch, fresh branch, or countermodel-hit.

This is intentionally a deterministic preflight.  It does not prove or refute
the theorem; it tells the RD what must be new before spending another tick.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[a-z0-9]+")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
NEGATION_TOKENS = {
    "avoid",
    "avoids",
    "avoided",
    "avoiding",
    "blocked",
    "cannot",
    "countermodel",
    "defeat",
    "defeated",
    "defeating",
    "defeats",
    "exclude",
    "excluded",
    "excludes",
    "excluding",
    "falsifier",
    "kill",
    "killed",
    "kills",
    "never",
    "no",
    "not",
    "overcome",
    "overcomes",
    "overcoming",
    "prevent",
    "prevents",
    "rule",
    "ruled",
    "rules",
    "ruling",
    "without",
}

GENERIC_FEATURE_TOKENS = {
    "a",
    "an",
    "and",
    "by",
    "for",
    "in",
    "of",
    "or",
    "the",
    "to",
    "with",
}


@dataclass(frozen=True)
class ResidualFeatureHit:
    feature: str
    hits: tuple[str, ...]


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    return next(
        (p for p in here.parents if (p / "src").is_dir() and (p / "projects").is_dir()),
        here.parents[-1],
    )


def _tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower().replace("_", " ").replace("-", " ")))


def _phrase_tokens(phrase: str) -> list[str]:
    return TOKEN_RE.findall(phrase.lower().replace("_", " ").replace("-", " "))


def _has_negation_before(tokens: list[str], idx: int, lookback: int = 5) -> bool:
    return any(token in NEGATION_TOKENS for token in tokens[max(0, idx - lookback):idx])


def _gapped_phrase_start(
    tokens: list[str],
    phrase_tokens: list[str],
    *,
    max_extra_gap: int = 2,
) -> int | None:
    """Return a loose phrase start, allowing short inserts inside a phrase.

    This catches evidence spans like "defeats nested Dirac reuse" for the
    feature phrase "nested reuse" without making the normal deterministic
    matcher more permissive.
    """
    phrase_tokens = [
        token for token in phrase_tokens if token not in GENERIC_FEATURE_TOKENS
    ]
    if not phrase_tokens:
        return None
    max_span = len(phrase_tokens) + max_extra_gap
    for start, token in enumerate(tokens):
        if token != phrase_tokens[0]:
            continue
        pos = start
        matched = True
        for wanted in phrase_tokens[1:]:
            found = None
            for candidate in range(pos + 1, min(len(tokens), start + max_span)):
                if tokens[candidate] == wanted:
                    found = candidate
                    break
            if found is None:
                matched = False
                break
            pos = found
        if matched:
            return start
    return None


def evidence_negates_feature(
    evidence: str,
    feature: str,
    feature_vocab: dict[str, list[str]],
) -> bool:
    """Return true when an evidence span rejects rather than uses a feature.

    The guard is intentionally conservative.  Phrases whose own catalog entry
    contains a negation token, such as "no reuse" for the positive freshness
    feature, are not treated as rejected merely because they contain "no".
    """
    tokens = TOKEN_RE.findall(evidence.lower().replace("_", " ").replace("-", " "))
    if not tokens:
        return False

    candidate_phrases = [feature.replace("_", " "), *feature_vocab.get(feature, [])]
    for phrase in candidate_phrases:
        phrase_tokens = _phrase_tokens(phrase)
        if not phrase_tokens:
            continue
        if any(token in NEGATION_TOKENS for token in phrase_tokens):
            continue
        start = _gapped_phrase_start(tokens, phrase_tokens)
        if start is not None and _has_negation_before(tokens, start):
            return True
    return False


def _phrase_hit(text_norm: str, phrase: str) -> bool:
    phrase_tokens = _phrase_tokens(phrase)
    phrase_norm = " ".join(phrase_tokens)
    if not phrase_norm:
        return False
    if not any(token in NEGATION_TOKENS for token in phrase_tokens):
        text_tokens = text_norm.split()
        window = len(phrase_tokens)
        for idx in range(0, len(text_tokens) - window + 1):
            if text_tokens[idx:idx + window] != phrase_tokens:
                continue
            if _has_negation_before(text_tokens, idx):
                continue
            return True
        return False
    if " " in phrase_norm:
        return phrase_norm in text_norm
    return phrase_norm in _tokens(text_norm)


def _feature_hits(text: str, feature_vocab: dict[str, list[str]]) -> list[ResidualFeatureHit]:
    text_norm = " ".join(TOKEN_RE.findall(text.lower().replace("_", " ")))
    hits: list[ResidualFeatureHit] = []
    for feature, phrases in feature_vocab.items():
        matched = tuple(p for p in phrases if _phrase_hit(text_norm, p))
        if matched:
            hits.append(ResidualFeatureHit(feature=feature, hits=matched))
    return hits


def _merge_feature_hits(
    base: list[ResidualFeatureHit],
    additional: list[dict[str, Any]] | None,
    feature_vocab: dict[str, list[str]] | None = None,
) -> list[ResidualFeatureHit]:
    merged: dict[str, list[str]] = {hit.feature: list(hit.hits) for hit in base}
    for hit in additional or []:
        feature = str(hit.get("feature") or "").strip()
        if not feature:
            continue
        evidence = hit.get("hits") or hit.get("evidence_spans") or []
        if isinstance(evidence, str):
            evidence = [evidence]
        merged.setdefault(feature, [])
        for item in evidence:
            evidence_text = str(item).strip()
            if feature_vocab and evidence_negates_feature(evidence_text, feature, feature_vocab):
                continue
            if evidence_text and evidence_text not in merged[feature]:
                merged[feature].append(evidence_text)
    return [
        ResidualFeatureHit(feature=feature, hits=tuple(hits))
        for feature, hits in merged.items()
        if hits
    ]


def extract_feature_hits(text: str, profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Public feature extraction for sibling deterministic preflight tools."""
    return [
        {"feature": hit.feature, "hits": list(hit.hits)}
        for hit in _feature_hits(text, profile.get("feature_vocab", {}))
    ]


def extract_feature_set(text: str, profile: dict[str, Any]) -> set[str]:
    """Return the canonical normal-form feature ids hit by text."""
    return {hit["feature"] for hit in extract_feature_hits(text, profile)}


def _normal_form_score(
    text: str,
    features: set[str],
    normal_form: dict[str, Any],
) -> dict[str, Any]:
    aliases = [normal_form.get("canonical_name", ""), *normal_form.get("aliases", [])]
    text_norm = " ".join(TOKEN_RE.findall(text.lower().replace("_", " ")))
    alias_hits = [a for a in aliases if _phrase_hit(text_norm, a)]

    expected = set(normal_form.get("feature_signature", []))
    matched_features = sorted(expected & features)
    missing_features = sorted(expected - features)
    extra_features = sorted(features - expected)
    denom = max(1, len(expected))
    feature_score = len(matched_features) / denom
    alias_score = min(1.0, len(alias_hits) / 2) if alias_hits else 0.0
    score = max(feature_score, 0.65 * feature_score + 0.35 * alias_score)
    return {
        "canonical_name": normal_form.get("canonical_name"),
        "score": round(score, 4),
        "alias_hits": alias_hits,
        "matched_features": matched_features,
        "missing_features": missing_features,
        "extra_features": extra_features,
        "normal_form": normal_form,
    }


def _packet_hits(
    features: set[str],
    packet_templates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for packet in packet_templates:
        triggers = set(packet.get("triggers", []))
        trigger_mode = packet.get("trigger_mode", "any")
        kills_if_any = set(packet.get("kills_if_any", []))
        kills_if_all = set(packet.get("kills_if_all", []))
        blocked_by = set(packet.get("blocked_by_features", []))
        trigger_hits = sorted(triggers & features)
        kill_any_hits = sorted(kills_if_any & features)
        kill_all_hits = sorted(kills_if_all & features)
        blocked_hits = sorted(blocked_by & features)
        if blocked_hits:
            continue
        if trigger_mode == "all":
            triggered = triggers.issubset(features)
        else:
            triggered = bool(trigger_hits) or not triggers
        kills = bool(kill_any_hits) or (
            bool(kills_if_all) and kills_if_all.issubset(features)
        )
        if triggered and kills:
            hits.append({
                "packet_id": packet.get("id"),
                "name": packet.get("name"),
                "verdict": packet.get("verdict", "countermodel_hit"),
                "trigger_hits": trigger_hits,
                "kill_hits": sorted(set(kill_any_hits) | set(kill_all_hits)),
                "what_it_tests": packet.get("what_it_tests"),
                "required_escape": packet.get("required_escape"),
            })
    return hits


def _currency_hits(
    features: set[str],
    currency_rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for rule in currency_rules:
        target = set(rule.get("target_features", []))
        produced = set(rule.get("produced_features", []))
        blocked_by = set(rule.get("blocked_by_features", []))
        target_hits = sorted(target & features)
        produced_hits = sorted(produced & features)
        blocked_hits = sorted(blocked_by & features)
        if target_hits and produced_hits and not blocked_hits:
            hits.append({
                "rule_id": rule.get("id"),
                "target": rule.get("target"),
                "produced": rule.get("produced"),
                "verdict": rule.get("verdict", "currency_mismatch"),
                "target_hits": target_hits,
                "produced_hits": produced_hits,
                "missing_exchange_rate": rule.get("missing_exchange_rate"),
            })
    return hits


def _novelty_label(
    best: dict[str, Any] | None,
    packet_hits: list[dict[str, Any]],
    currency_hits: list[dict[str, Any]],
    features: set[str],
    profile: dict[str, Any],
) -> str:
    if packet_hits:
        return "COUNTERMODEL_HIT"
    if currency_hits:
        return "ALIAS"
    if not best or best["score"] < profile.get("new_threshold", 0.42):
        return "NEW"

    stronger_markers = set(profile.get("strictly_stronger_features", []))
    narrower_markers = set(profile.get("strictly_narrower_features", []))
    if stronger_markers & features:
        return "STRICTLY_STRONGER"
    if narrower_markers & features:
        return "STRICTLY_NARROWER"
    if best["score"] >= profile.get("alias_threshold", 0.66):
        return "ALIAS"
    return "NARROWER_OR_ALIAS"


def compile_residual_normal_form(
    text: str,
    profile: dict[str, Any],
    additional_feature_hits: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Classify a residual against a substrate profile."""
    features_hit = _merge_feature_hits(
        _feature_hits(text, profile.get("feature_vocab", {})),
        additional_feature_hits,
        profile.get("feature_vocab", {}),
    )
    features = {hit.feature for hit in features_hit}
    scores = [
        _normal_form_score(text, features, nf)
        for nf in profile.get("normal_forms", [])
    ]
    scores.sort(key=lambda row: row["score"], reverse=True)
    best = scores[0] if scores else None
    packets = _packet_hits(features, profile.get("packet_falsifiers", []))
    currencies = _currency_hits(features, profile.get("currency_rules", []))
    label = _novelty_label(best, packets, currencies, features, profile)
    required_next_move = None
    if packets:
        required_next_move = packets[0].get("required_escape")
    elif currencies:
        required_next_move = currencies[0].get("missing_exchange_rate")
    elif best:
        required_next_move = best["normal_form"].get("required_new_signal")

    return {
        "schema_version": profile.get("schema_version", "unknown"),
        "profile_name": profile.get("name", "unnamed_profile"),
        "classification": label,
        "best_match": best,
        "top_matches": scores[:5],
        "feature_hits": [
            {"feature": hit.feature, "hits": list(hit.hits)}
            for hit in features_hit
        ],
        "packet_hits": packets,
        "currency_mismatches": currencies,
        "required_next_move": required_next_move,
        "anti_laundering_note": (
            "Routing output only. A NEW/STRONGER label still needs a crisp "
            "estimate, packet falsifier survival, and formal/proof artifact."
        ),
    }


def iter_markdown_sections(path: Path, min_heading_level: int = 2) -> list[dict[str, Any]]:
    """Split a Markdown file into heading-delimited sections."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    body: list[str] = []
    for line_no, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if match and len(match.group(1)) >= min_heading_level:
            if current:
                current["body"] = "\n".join(body).strip()
                sections.append(current)
            current = {
                "source_path": str(path),
                "line": line_no,
                "level": len(match.group(1)),
                "heading": match.group(2).strip(),
            }
            body = [line]
            continue
        if current:
            body.append(line)
    if current:
        current["body"] = "\n".join(body).strip()
        sections.append(current)
    return sections


def _is_residual_relevant_section(section: dict[str, Any]) -> bool:
    """Keep sections that look like residual/tick findings."""
    heading = str(section.get("heading") or "").lower()
    body = str(section.get("body") or "").lower()
    if "tick" in heading:
        return True
    markers = (
        "verdict:",
        "**verdict:**",
        "decisive reason",
        "corrected next lever",
        "forbidden false paths",
        "canonical open nodes",
        "next lever",
        "anti-rehash outcome",
    )
    return any(marker in heading or marker in body for marker in markers)


def scan_markdown_sections(
    paths: list[Path],
    profile: dict[str, Any],
    min_heading_level: int = 2,
    residual_relevant_only: bool = False,
) -> dict[str, Any]:
    """Classify every Markdown section in a set of files."""
    rows: list[dict[str, Any]] = []
    for path in paths:
        for section in iter_markdown_sections(path, min_heading_level=min_heading_level):
            if residual_relevant_only and not _is_residual_relevant_section(section):
                continue
            result = compile_residual_normal_form(
                f"{section['heading']}\n\n{section.get('body', '')}",
                profile,
            )
            best = result.get("best_match") or {}
            rows.append({
                "source_path": section["source_path"],
                "line": section["line"],
                "heading": section["heading"],
                "classification": result["classification"],
                "best_match": best.get("canonical_name"),
                "score": best.get("score"),
                "required_next_move": result.get("required_next_move"),
                "packet_hits": result.get("packet_hits", []),
                "currency_mismatches": result.get("currency_mismatches", []),
                "feature_hits": result.get("feature_hits", []),
            })

    by_class: dict[str, int] = {}
    by_best: dict[str, int] = {}
    by_packet: dict[str, int] = {}
    by_currency: dict[str, int] = {}
    for row in rows:
        by_class[row["classification"]] = by_class.get(row["classification"], 0) + 1
        best = row.get("best_match") or "none"
        by_best[best] = by_best.get(best, 0) + 1
        for hit in row.get("packet_hits") or []:
            pid = str(hit.get("packet_id") or "unknown")
            by_packet[pid] = by_packet.get(pid, 0) + 1
        for hit in row.get("currency_mismatches") or []:
            rid = str(hit.get("rule_id") or "unknown")
            by_currency[rid] = by_currency.get(rid, 0) + 1

    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "schema_version": profile.get("schema_version", "unknown"),
        "profile_name": profile.get("name", "unnamed_profile"),
        "n_sections": len(rows),
        "by_classification": dict(sorted(by_class.items())),
        "by_best_match": dict(sorted(by_best.items(), key=lambda kv: (-kv[1], kv[0]))),
        "by_packet_hit": dict(sorted(by_packet.items(), key=lambda kv: (-kv[1], kv[0]))),
        "by_currency_mismatch": dict(sorted(by_currency.items(), key=lambda kv: (-kv[1], kv[0]))),
        "rows": rows,
    }


def render_batch_markdown(scan: dict[str, Any]) -> str:
    lines = [
        "# Residual Normal-Form Ex-Post Scan",
        "",
        f"- Generated UTC: `{scan['generated_utc']}`",
        f"- Profile: `{scan['profile_name']}`",
        f"- Sections scanned: `{scan['n_sections']}`",
        "",
        "## Classification Counts",
        "",
    ]
    for key, value in scan["by_classification"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Best-Match Counts", ""])
    for key, value in scan["by_best_match"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Packet Hits", ""])
    if scan["by_packet_hit"]:
        for key, value in scan["by_packet_hit"].items():
            lines.append(f"- `{key}`: {value}")
    else:
        lines.append("- (none)")
    lines.extend(["", "## Currency Mismatches", ""])
    if scan["by_currency_mismatch"]:
        for key, value in scan["by_currency_mismatch"].items():
            lines.append(f"- `{key}`: {value}")
    else:
        lines.append("- (none)")
    lines.extend(["", "## Highest-Signal Rows", ""])
    ranked = sorted(
        scan["rows"],
        key=lambda row: (
            row["classification"] not in {"COUNTERMODEL_HIT", "ALIAS"},
            -(row.get("score") or 0.0),
            row["source_path"],
            row["line"],
        ),
    )
    for row in ranked[:40]:
        lines.append(
            f"- `{row['classification']}` `{row.get('best_match')}` "
            f"score=`{row.get('score')}` "
            f"{row['source_path']}:{row['line']} — {row['heading']}"
        )
        if row.get("required_next_move"):
            lines.append(f"  next: {row['required_next_move']}")
    lines.extend([
        "",
        "## Use",
        "",
        "A row classified as `ALIAS` or `COUNTERMODEL_HIT` is not forbidden to pursue, but a new tick must name the specific field that escapes the normal form: new proof-producing signal, stricter theorem hypothesis, or a packet-surviving counterargument.",
    ])
    return "\n".join(lines)


def load_profile(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_text_arg(args: argparse.Namespace) -> str:
    chunks: list[str] = []
    if args.text:
        chunks.append(args.text)
    for path in args.text_file or []:
        chunks.append(Path(path).read_text(encoding="utf-8"))
    for candidate in args.candidate or []:
        chunks.append(candidate)
    return "\n".join(chunks)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Classify a proposed residual against a normal-form profile."
    )
    ap.add_argument("--profile", required=True, help="JSON profile path")
    ap.add_argument("--text", help="Residual/proposal text")
    ap.add_argument("--text-file", action="append", help="File to include")
    ap.add_argument("--candidate", action="append", help="Candidate estimate/theorem text")
    ap.add_argument(
        "--batch-markdown",
        action="store_true",
        help="Classify heading-delimited sections from --text-file paths.",
    )
    ap.add_argument("--min-heading-level", type=int, default=2)
    ap.add_argument(
        "--residual-relevant-only",
        action="store_true",
        help=(
            "For batch Markdown scans, skip generic sections without "
            "residual/tick markers."
        ),
    )
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--json", action="store_true", help="Emit full JSON")
    args = ap.parse_args()

    profile = load_profile(args.profile)
    if args.batch_markdown:
        if not args.text_file:
            raise SystemExit("--batch-markdown requires at least one --text-file")
        scan = scan_markdown_sections(
            [Path(path) for path in args.text_file],
            profile,
            min_heading_level=args.min_heading_level,
            residual_relevant_only=args.residual_relevant_only,
        )
        if args.out_json:
            args.out_json.parent.mkdir(parents=True, exist_ok=True)
            args.out_json.write_text(json.dumps(scan, indent=2), encoding="utf-8")
        if args.out_md:
            args.out_md.parent.mkdir(parents=True, exist_ok=True)
            args.out_md.write_text(render_batch_markdown(scan), encoding="utf-8")
        if args.json or not args.out_md:
            print(json.dumps(scan, indent=2))
        else:
            print(f"wrote: {args.out_md}")
        return 0

    text = _read_text_arg(args)
    if not text.strip():
        raise SystemExit("provide --text, --text-file, or --candidate")
    result = compile_residual_normal_form(text, profile)
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print(f"profile: {result['profile_name']}")
    print(f"classification: {result['classification']}")
    best = result.get("best_match") or {}
    print(f"best_match: {best.get('canonical_name')} score={best.get('score')}")
    if result.get("packet_hits"):
        print("packet_hits:")
        for hit in result["packet_hits"]:
            print(f"- {hit['packet_id']}: {hit['name']} -> {hit['verdict']}")
    if result.get("currency_mismatches"):
        print("currency_mismatches:")
        for hit in result["currency_mismatches"]:
            print(f"- {hit['rule_id']}: {hit['verdict']}")
    if result.get("required_next_move"):
        print(f"required_next_move: {result['required_next_move']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
