#!/usr/bin/env python3
"""
count_real_sorries.py

Deterministic Lean sorry counter that EXCLUDES docstring substring matches.

Per catch C-2026-05-09-78: a naive `grep -c sorry` over `*.lean` files in
`ztare_proofs/ZtareProofs/` returns 609 (docstring-inflated), but the
real proof-body count is 44.

The discriminator is:
  1. Strip block comments `/- ... -/` (including multi-line).
  2. Strip single-line `--` comments.
  3. Match line-anchored proof-body sorry forms:
        ^\\s*by\\s+sorry$
        ^\\s*exact\\s+sorry$
        ^\\s*:=\\s*sorry$
        ^\\s*sorry\\s*$
        ^\\s*:=\\s*by\\s+sorry$

Usage:
  python scripts/public/analytics_shared/count_real_sorries.py [path]   # path defaults to ztare_proofs/ZtareProofs

Outputs:
  - Total real proof-body sorries
  - File count with at least 1 sorry
  - Top-K files by sorry count (default K=10)
  - JSON summary at analytics/public/sorry_count_<date>.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date


SORRY_BODY_PAT = re.compile(
    r'^\s*(by\s+sorry|exact\s+sorry|:=\s*sorry|sorry\s*$|:=\s*by\s+sorry)',
    re.MULTILINE,
)
BLOCK_COMMENT_PAT = re.compile(r'/-(.*?)-/', re.DOTALL)
LINE_COMMENT_PAT = re.compile(r'--.*')


def count_in_file(path: str) -> int:
    try:
        text = open(path).read()
    except Exception:
        return 0
    cleaned = BLOCK_COMMENT_PAT.sub('', text)
    cleaned = LINE_COMMENT_PAT.sub('', cleaned)
    return len(SORRY_BODY_PAT.findall(cleaned))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'root',
        nargs='?',
        default='ztare_proofs/ZtareProofs',
        help='Directory to scan (default: ztare_proofs/ZtareProofs)',
    )
    parser.add_argument('--top-k', type=int, default=10)
    parser.add_argument('--json-output', type=str, default=None)
    args = parser.parse_args()

    if not os.path.isdir(args.root):
        print(f'ERROR: {args.root} not a directory', file=sys.stderr)
        return 2

    file_counts: list[tuple[int, str]] = []
    total = 0
    for cur_root, _, files in os.walk(args.root):
        for fn in files:
            if not fn.endswith('.lean'):
                continue
            path = os.path.join(cur_root, fn)
            n = count_in_file(path)
            if n > 0:
                file_counts.append((n, path))
                total += n

    file_counts.sort(reverse=True)
    print(f'Real proof-body sorries (block- and line-comments stripped):')
    print(f'  total: {total}')
    print(f'  files with >=1: {len(file_counts)}')
    print()
    print(f'Top {args.top_k}:')
    for n, p in file_counts[: args.top_k]:
        print(f'  {n:4d}  {os.path.basename(p)}')

    summary = {
        'computed_at': date.today().isoformat(),
        'root': args.root,
        'total_sorries': total,
        'files_with_sorries': len(file_counts),
        'top_files': [
            {'count': n, 'path': p} for n, p in file_counts[: args.top_k]
        ],
    }

    out_path = args.json_output or f'analytics/public/sorry_count_{date.today().isoformat()}.json'
    with open(out_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f'\nSummary written: {out_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
