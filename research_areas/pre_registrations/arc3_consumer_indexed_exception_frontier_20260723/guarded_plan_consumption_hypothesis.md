# H-ARC3-GUARDED-PLAN-CONSUMPTION-20260727-48

## Eigenquestion

Can learned generator identity reduce a planning representation while preserving
the exact primitive path and every reference transition?

## Hypothesis

A common plan consumer can take:

- an opaque start key;
- an ordered primitive operation request;
- a guarded skill library;
- a deterministic reference-transition callback.

It first replays the primitive request to establish the reference state at every
prefix. Dynamic programming may replace a contiguous operation word by a skill
token only when:

1. the word matches exactly;
2. the skill admits the current source key;
3. every primitive image under the skill matches the precomputed reference
   state path;
4. no boundary or ambiguous image occurs.

The chosen tokenization minimizes token count and expands exactly to the input
word. An absent or conflicting guard leaves primitive tokens.

## Discriminator

Use the current 13-operation observed-frontier route from the H47 audit. Its
last operation is the unwitnessed experiment and remains outside the compiled
prefix. Tokenize the witnessed 12-operation prefix through the four H47
programs and the exact partial-action relation. Repeat with reversed library
order.

## Success and kill conditions

Success requires fewer tokens than 12 primitive operations, at least one skill
token, exact expansion, the same final witnessed-prefix key, no fallback guard
used, and order invariance.

Kill on no reduction, mismatch, boundary traversal, fallback admission, target
operation inclusion, order sensitivity, or environment contact.

## Claim boundary

A pass proves downstream plan consumption only. The final experiment remains
primitive and unwitnessed; the environment still owns its consequence.
