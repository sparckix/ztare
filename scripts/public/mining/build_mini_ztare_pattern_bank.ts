// Build the mining-derived pattern bank.
//
// Reads the May 4 LLM-classifier output from the operator-private mining
// queries, groups classified records by failure-class, samples up to N
// exemplar weakest-point strings per class (redacted), and emits a
// class-level corpus file at corpus/pattern_bank/<class>.md.
//
// Each class file is a structured markdown artifact with the same shape as a
// teaching-note section so the existing embeddings builder can index it
// without modification.
//
// USAGE:
//   MINING_QUERIES_PATH=/Users/.../analytics/public/queries \
//     tsx scripts/public/mining/build_mini_ztare_pattern_bank.ts
//
// The mining queries path is operator-supplied so the public repo never has
// to ship the raw mining JSON. The pattern-bank output is what gets committed.

import * as fs from "node:fs";
import * as path from "node:path";

const MINING_QUERIES_PATH =
  process.env.MINING_QUERIES_PATH ??
  "/analytics/public/queries";

const LLM_SUBCLASSES = path.join(
  MINING_QUERIES_PATH,
  "weakest_link_llm_subclasses_2026-05-04.json",
);

const PATTERN_BANK_DIR = path.join("/corpus/pattern_bank");
const MIN_RECORDS_PER_CLASS = 10;
const MAX_EXEMPLARS_PER_CLASS = 5;
const EXEMPLAR_TRUNC = 280;

// Minimal redaction. The mining-derived weakest-points already strip case
// identifiers in their phrasing (they describe failures, not identities), but
// we still scrub project slugs and proper-noun-shaped tokens that occasionally
// leak through.
const REDACTION_PATTERNS: [RegExp, string][] = [
  [/\bgp\d{2,4}[a-z]*\b/gi, "[project]"],
  [/\bcentral_station\b/gi, "[venture]"],
  [/\bfigs\b/gi, "[venture]"],
  [/\beu_union[_a-z]*\b/gi, "[institution]"],
  [/\bhbr_[a-z]+\b/gi, "[case]"],
  [/\bglp[-_]?1\b/gi, "[therapy]"],
  [/\bai_[a-z_]+\b/gi, "[domain]"],
];

function redact(s: string): string {
  let out = s;
  for (const [pat, repl] of REDACTION_PATTERNS) {
    out = out.replace(pat, repl);
  }
  return out.length > EXEMPLAR_TRUNC ? out.slice(0, EXEMPLAR_TRUNC).trim() + "…" : out;
}

// Generic killer-question shapes per failure class. These are class-level
// templates; they do not reference any specific case.
const GENERIC_KILLER_QUESTIONS: Record<string, string> = {
  unfalsifiable_claim:
    "What single observable result, if you saw it tomorrow, would force you to abandon this claim? If no such observable exists, the claim is unfalsifiable.",
  missing_mechanism:
    "What is the causal chain from your inputs to your claimed outcome? Trace it step by step. If a step relies on \"and then it happens,\" that step is the missing mechanism.",
  overclaimed_scope:
    "What is the smallest population where your evidence is genuinely informative? If you broadened the scope by one reasonable step, would the claim still hold?",
  unmeasurable_construct:
    "Define the variable you are anchoring on with enough precision that two independent measurers would agree on its value within 10%. If you cannot, the construct is unmeasurable.",
  unsupported_assumption:
    "Which assumption in your argument has not been tested, and what specific test would confirm or refute it?",
  parameter_sensitivity:
    "If the threshold/parameter you are using shifted by a small amount in either direction, would your conclusion still hold? Show the boundaries.",
  missing_counterfactual:
    "What would the world look like if your thesis were wrong? If your evidence is consistent with both worlds, the evidence is non-discriminative.",
  missing_data:
    "What data would you need to actually verify the claim, and what is the gap between that data and what you have?",
  definition_ambiguity:
    "Restate your central term as a one-line operational definition that two strangers could apply to the same case and get the same answer.",
  unverified_assumption:
    "Identify the assumption your argument relies on most heavily, and state the experiment you would run to test it.",
  catastrophic_assumption:
    "What single decision-critical assumption, if false, would collapse your entire conclusion? Defend it directly.",
  exhaustiveness_claim:
    "Have you tested all the cases you claim to cover, or have you tested a sample and assumed the rest follow? Name the gap.",
  tail_generalization:
    "Your evidence covers the visible window. What about the tails — the rare or extreme cases — has been verified, and what is just assumed?",
  unverified_bound:
    "What is the exact bound you are claiming, and what is the proof of that bound rather than its plausibility?",
  circularity:
    "Restate your conclusion. Restate your evidence. If they are restatements of each other, the argument is circular.",
};

type LLMCategoryEntry = {
  category: string;
  size: number;
  project_count: number;
  exemplars: string[];
  members?: Array<{ project: string; iter_ts: number; weakest_point: string }>;
  confidence?: string;
};

type ClassifierOutput = {
  generated: string;
  source: string;
  total_classified: number;
  total_input: number;
  model: string;
  category_count: number;
  categories: LLMCategoryEntry[];
};

function main() {
  if (!fs.existsSync(LLM_SUBCLASSES)) {
    console.error(`mining queries not found at ${LLM_SUBCLASSES}`);
    console.error(
      "set MINING_QUERIES_PATH to the analytics/public/queries dir of the private repo",
    );
    process.exit(1);
  }

  const data = JSON.parse(fs.readFileSync(LLM_SUBCLASSES, "utf-8")) as ClassifierOutput;

  fs.mkdirSync(PATTERN_BANK_DIR, { recursive: true });

  // Each entry in `categories` already represents one class with its members
  // and exemplars. Use them directly.
  const byCategory: Record<string, LLMCategoryEntry> = {};
  for (const entry of data.categories) {
    byCategory[entry.category || "other"] = entry;
  }

  let written = 0;
  let skipped = 0;
  for (const [cls, entry] of Object.entries(byCategory)) {
    if (entry.size < MIN_RECORDS_PER_CLASS) {
      skipped += 1;
      continue;
    }
    // Use exemplars from the mining output (already deduplicated per-class).
    // Apply our redaction patterns on top, since mining exemplars retain the
    // original phrasing.
    const exemplars: string[] = (entry.exemplars ?? [])
      .slice(0, MAX_EXEMPLARS_PER_CLASS)
      .map((e) => redact(e));

    const familyName = humanizeClass(cls);
    const killerQuestion = GENERIC_KILLER_QUESTIONS[cls] ?? GENERIC_KILLER_QUESTIONS.unsupported_assumption;

    // Same shape as teaching-note sections so the embeddings builder picks
    // them up without modification: level-3 header + Killer Question subhead.
    const md = `# Pattern Bank Entry: ${familyName}

*Mining-derived pattern from a corpus of structured adversarial iterations across many projects. ${entry.size} records across ${entry.project_count} projects classified into this pattern.*

---

### 1. ${familyName}

**Mining N:** ${entry.size} records across ${entry.project_count} projects.

**Mechanism:** This pattern surfaces when ${describeMechanism(cls)}.

**Exemplar critiques (redacted; identifiers removed):**

${exemplars.map((e, i) => `${i + 1}. ${e}`).join("\n\n")}

**The Killer Question:**

${killerQuestion}

**The Instructor's Follow-Up:**

Press for a concrete operationalization or test. If the defender cannot supply one, the pattern is structural; if they can, the pattern was a phrasing artifact and the conversation moves on.
`;

    const fname = `${cls.replace(/[^a-z0-9_]/gi, "_")}.md`;
    fs.writeFileSync(path.join(PATTERN_BANK_DIR, fname), md);
    written += 1;
  }

  console.log(`Wrote ${written} pattern-bank entries to ${PATTERN_BANK_DIR}`);
  console.log(`Skipped ${skipped} classes with N < ${MIN_RECORDS_PER_CLASS} records`);
}

function humanizeClass(cls: string): string {
  return cls
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function describeMechanism(cls: string): string {
  const m: Record<string, string> = {
    unfalsifiable_claim: "the argument cannot be disconfirmed by any observable evidence",
    missing_mechanism: "the argument describes WHAT happens without explaining HOW it happens",
    overclaimed_scope: "the conclusion is generalized beyond the population the evidence covers",
    unmeasurable_construct: "the central variable has no observable proxy",
    unsupported_assumption: "a decision-critical assumption is asserted without test or evidence",
    parameter_sensitivity: "the conclusion depends sensitively on a parameter or threshold that has not been justified",
    missing_counterfactual: "no rival explanation has been considered or excluded",
    missing_data: "the data needed to verify the claim is not available or not gathered",
    definition_ambiguity: "a key term is used without an operational definition",
    unverified_assumption: "an assumption is treated as fact without being tested",
    catastrophic_assumption: "the entire argument hinges on one decision-critical assumption that is itself contested",
    exhaustiveness_claim: "the argument claims completeness over a class but has tested only a sample",
    tail_generalization: "the evidence covers the visible window but the claim extends to extremes that have not been verified",
    unverified_bound: "a numerical bound is asserted without proof of its tightness",
    circularity: "the conclusion restates the evidence in different words",
  };
  return m[cls] ?? "the argument relies on an unstated or untested assumption";
}

main();
