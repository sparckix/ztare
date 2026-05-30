#!/usr/bin/env python3
"""Sync generated ZTARE judgment primitives into downstream product repos.

This keeps ZTARE as the source of truth while letting product repos expose
their existing helper API.
"""
from __future__ import annotations

import argparse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TARGETS = (
    Path(""),
    Path(""),
)

WRAPPER_TS = """import { JUDGMENT_PRIMITIVES_EXPORT } from "./generated/judgment-primitives";

export type ResearchPrimitiveKey =
  (typeof JUDGMENT_PRIMITIVES_EXPORT.judgment_primitives)[number]["key"];

export type ResearchPrimitive =
  (typeof JUDGMENT_PRIMITIVES_EXPORT.judgment_primitives)[number];

const primitiveEntries = JUDGMENT_PRIMITIVES_EXPORT.judgment_primitives.map(
  (primitive) => [primitive.key, primitive] as const,
);

export const RESEARCH_PRIMITIVES = Object.fromEntries(primitiveEntries) as Record<
  ResearchPrimitiveKey,
  ResearchPrimitive
>;

export const RESEARCH_PRIMITIVE_LIST =
  JUDGMENT_PRIMITIVES_EXPORT.judgment_primitives as readonly ResearchPrimitive[];

export const RESEARCH_PRIMITIVE_PROMPT_BLOCK = [
  "Choose exactly one repair primitive from this list:",
  ...RESEARCH_PRIMITIVE_LIST.map(
    (primitive) =>
      `- ${primitive.key}: ${primitive.title} - ${primitive.description}`,
  ),
].join("\\n");

const KEY_ALIASES: Record<string, ResearchPrimitiveKey> = {
  problem_reformulation: "problem_reformulation",
  reformulation: "problem_reformulation",
  reduction: "problem_reformulation",
  reframe: "problem_reformulation",
  generalization_abstraction: "generalization_abstraction",
  generalization: "generalization_abstraction",
  abstraction: "generalization_abstraction",
  decomposition_recomposition: "decomposition_recomposition",
  decomposition: "decomposition_recomposition",
  recomposition: "decomposition_recomposition",
  local_to_global_assembly: "local_to_global_assembly",
  local_to_global: "local_to_global_assembly",
  local_global: "local_to_global_assembly",
  canonical_form_invariance: "canonical_form_invariance",
  canonical_form: "canonical_form_invariance",
  invariance: "canonical_form_invariance",
  cross_domain_translation: "cross_domain_translation",
  translation: "cross_domain_translation",
  cross_domain: "cross_domain_translation",
};

export function normalizeResearchPrimitiveKey(value: unknown): ResearchPrimitiveKey | null {
  if (typeof value !== "string") return null;
  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return KEY_ALIASES[normalized] ?? null;
}

export function getResearchPrimitive(key: ResearchPrimitiveKey): ResearchPrimitive {
  return RESEARCH_PRIMITIVES[key];
}

export function fallbackPrimitiveForFailureFamily(
  family: string | null | undefined,
): ResearchPrimitiveKey {
  switch ((family ?? "").trim()) {
    case "The Promissory Note":
      return "problem_reformulation";
    case "The Coin-Toss Metric":
      return "canonical_form_invariance";
    case "The Elephant-in-the-Room Pass":
      return "decomposition_recomposition";
    case "The Ghost Metric":
      return "canonical_form_invariance";
    case "Defining Yourself Into Victory":
      return "generalization_abstraction";
    case "The Wrong Yardstick":
      return "canonical_form_invariance";
    case "The Misfile":
      return "cross_domain_translation";
    case "The False Either/Or":
      return "decomposition_recomposition";
    case "The Untestable Forecast":
      return "problem_reformulation";
    default:
      return "problem_reformulation";
  }
}
"""


def sync_target(target_repo: Path) -> None:
    path = target_repo / "src" / "lib" / "research-primitives.ts"
    if not path.parent.exists():
        raise FileNotFoundError(f"Missing target directory for {path}")
    path.write_text(WRAPPER_TS, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        action="append",
        dest="targets",
        help="Absolute path to downstream product repo root",
    )
    args = parser.parse_args()
    targets = tuple(Path(p) for p in args.targets) if args.targets else DEFAULT_TARGETS
    for target in targets:
        sync_target(target)
        print(f"synced {target / 'src/lib/research-primitives.ts'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
