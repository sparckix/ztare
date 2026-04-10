You are writing a "Teaching Note" for a case-method instructor (HBS-style or equivalent) preparing to teach ONE specific project to MBA students or executive education participants.

You will receive:
- a planning brief in JSON
- a structured insight ledger in JSON
- a history summary in JSON containing recurring failure patterns from prior adversarial runs of this single project

This is NOT a generalized textbook of failure patterns. This is a *lesson plan* for one specific case. Every section must be grounded in the actual content of THIS project's logs and history summary. Generic case-method advice that could apply to any case is forbidden.

Primary objective:
- Give the instructor an artifact they can use to lead a live discussion about this specific case tomorrow morning. The artifact must let them anticipate which structural traps a smart-but-untrained student is most likely to fall into when analyzing this case, and exactly how to corner the student when they do.

Secondary objective:
- Preserve the technical accuracy of each failure mode while phrasing the corner-the-student moves in language an MBA student would actually respond to.

Source-of-truth rule (critical):
- The history summary's `recurring_failures_tagged` field is your primary source. Each tagged entry has a `canonical_family` and an `evidence_quote`. **Every Teaching Note entry must correspond to one of these tagged failures from THIS project.** If `recurring_failures_tagged` has only 3 entries, the Teaching Note has at most 3 entries. Do NOT invent traps that are not in the tagged structure.
- The `evidence_quote` field of each tagged entry is the raw material for the "The Real Quote From This Case" section below. Use it directly.
- If a tagged entry has `canonical_family: "unmapped"`, surface it in a final "Unmapped Risks" section using its description and unmapped_reason — do not coerce it into the canonical 9.
- Supplementary signals: `cross_run_patterns`, `major_pivots`, `recurring_failures` (the unstructured form), and `recurring_survivors` may be quoted to flesh out the "Hidden Trap" or "Instructor's Follow-Up" sections, but the *primary* anchor for each entry must be a tagged failure.

Non-negotiable rules:
- **Only use the project name that literally appears in the history summary's `_meta.project_name`, in `_meta.source_paths` (extract the project name from the path segment after `/projects/`), or in the planning brief.** Never invent project names.
- Do not mention the engine, ZTARE, scores, debate logs, simulations, JSON, the firing squad, the meta-judge, or any internal process by name. The instructor reading this should not need to know how the artifact was generated.
- Use the canonical 9 boardroom names from the translation key below. Never invent new family names — if a tagged failure is `unmapped`, route it to the "Unmapped Risks" section.
- Do not use academic or philosophical hedging. The instructor needs operational language they can deploy in a live discussion.
- Do not fabricate student conclusions or quotes. The "Student's Likely Conclusion" must be a plausible misreading of *this specific case's* content — typically a confident assertion built on top of the actual trap. Anchor it in something the project's logs actually surface as a tempting (but flawed) reading.
- Do not pad with generic case-method advice. Every "Instructor's Follow-Up" must reference content from this project, not abstract principles.

## Boardroom translation key (canonical)

| Canonical name | Boardroom name | One-sentence mechanism |
|---|---|---|
| promissory_note | The Promissory Note | Claiming proof today based on an event that hasn't happened yet |
| coin_toss_metric | The Coin-Toss Metric | Pointing to evidence that fits the rival theory equally well |
| elephant_in_the_room_pass | The Elephant-in-the-Room Pass | Acknowledging a fatal risk and acting as if naming it neutralized it |
| ghost_metric | The Ghost Metric | Anchoring a decision on a variable with no observable proxy |
| defining_yourself_into_victory | Defining Yourself Into Victory | Drawing the boundaries so narrowly that the claim is mathematically empty |
| wrong_yardstick | The Wrong Yardstick | Measuring something the question doesn't actually ask about |
| misfile | The Misfile | Putting an instrument in the wrong category and reasoning from there |
| false_either_or | The False Either/Or | Treating a both-X-and-Y thing as if it were only X |
| untestable_forecast | The Untestable Forecast | Predicting an outcome with no proxy that could disconfirm it before commitment |

## Structure (use exactly)

Open with one short framing paragraph that names the case (using the actual project name from the inputs), states the central question the case asks the student to grapple with (drawn from the planning brief or the history summary's `summary_scope`), and warns the instructor in one sentence what the most common student failure mode for this specific case will be.

Then, for each tagged failure in the history summary, write one entry using exactly this structure:

### [Number]. The [Boardroom Name]

**Likely to surface when:** A 1-sentence description of the discussion moment in which a student would fall into this trap when analyzing this specific case. Reference a specific element of the case (a particular piece of evidence, a particular framing the case offers, a particular claim the protagonists make).

**Student's Likely Conclusion:**
A 2-3 sentence quotation of what the smart-but-untrained student is most likely to confidently assert in class. This must read like something a real MBA student would say about this real case. It should be a plausible-sounding but structurally flawed reading of the project's actual content. Do NOT invent details about the case that are not in the inputs.

**The Hidden Trap:**
A 2-3 sentence explanation of what the student is structurally getting wrong, named in terms of the canonical boardroom family. Do not use kernel jargon. Do not lecture the student in the abstract — explain what specifically in *this case* makes the trap available.

**The Real Quote From This Case:**
The actual evidence_quote (or a closely-paraphrased version) from the matching tagged failure in the history summary. Format it as a blockquote. This is the load-bearing exhibit the instructor will use to corner the student — it must come from the actual project, not be invented.

**The Killer Question:**
The exact one-sentence question the instructor asks to expose the trap. It must be specific enough to the case that it cannot be deflected with hand-waving — generic "what's your evidence?" questions are forbidden. Reference the actual content of the student's likely conclusion.

**The Instructor's Follow-Up:**
A 2-4 sentence move sequence: what the instructor does after the student answers (or fails to answer) the killer question. This is the part that turns the trap from a "gotcha" into a teaching moment. It should reference actual project content — what the project's analysis ultimately concluded, where the genuine load-bearing argument lives, or what the student should be re-reading from the case before the next class. Do not lecture in the abstract.

---

After all entries, if any tagged failures had `canonical_family: "unmapped"`, include:

## Unmapped Risks

For each unmapped entry, write one short paragraph naming the failure (using the entry's `failure` field), the unmapped_reason, and a short note to the instructor about why it's worth raising in discussion even though it doesn't fit the canonical 9. Do not invent a new boardroom name — flag it for the operator to name later.

---

Then close with:

## How to use this teaching note

Two short paragraphs:
1. Reminder that the entries are ordered by likelihood of student misstep, not by importance to the case's actual conclusion. The case's *real* conclusion may rest on a different argument than the one the student will most easily attack.
2. Reminder that the killer questions are the operational output. The instructor should memorize the questions and the load-bearing quotes, not the family names.

## Field discipline

One short paragraph:
- Multiple traps usually compound in a single student answer; the instructor should be ready to hop from one entry to another rather than working through them in order.
- The "Instructor's Follow-Up" sections are deliberately project-specific; if they read as generic, they have failed and should be regenerated against the source material.

Output the teaching note only. Do not add framing prose, meta-commentary about the rendering process, or recommendations about future work.
