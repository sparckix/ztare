# Guarded plan consumption result

Date: 2026-07-27

Status: confirmed

The common plan consumer precomputed the exact reference state at every prefix
and then tokenized only commuting, admitted words.

Input witnessed prefix:

```text
0,0,0,0,0,0,0,0,2,1,1,3
```

Compiled plan:

1. skill `(0,0,0,0,0)`
2. skill `(0,0,0,2,1,1)`
3. primitive `3`

Measurements:

- primitive operations: `12`
- plan tokens: `3`
- skill tokens: `2`
- token savings: `9`
- exact expansion: `true`
- final source digest: `8f9dcb2859f820e2912db50628965f821549a807a5c2d977adc56ae58845bc15`
- library-order invariant: `true`

The frontier operation `1` was not included in the compiler input and remains
primitive. The next registered probe spends that one novel contact after the
unchanged learned-skill prefix.
