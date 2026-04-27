# Orbit — Governance for Human-AI Organizations

You don't manage agents. You set gravity. They orbit. You intervene only when something escapes.

A governance interface for autonomous AI agents. Each agent is a luminous orb encoding state through color, breathing animation, and position. Silent by default — surfaces nothing unless a boundary is crossed or a decision is required.

Designed through 4 rounds of expert panel debate (27 experts including organizational economists, UX researchers, distributed systems architects, ethnographers, and simulated alien AI from 2035/2040).

## Quick Start

```bash
cd orbit && npm install

# Terminal 1: event bus + org watcher
npm run sync

# Terminal 2: dev server
npm run dev

# Open http://localhost:3000
```

## Architecture

```
org/ (system of record, git-tracked)
  ├── members/*.yaml        → Agent orbs on canvas
  ├── roles/*.yaml          → Governance pane
  ├── mandates/*.md         → Scope boundaries
  ├── events/*.jsonl        → Event stream (append-only)
  ├── gates/                → Approval queue
  ├── directives/           → Human → agent messages
  └── controls/             → STOP / PAUSE / RESUME
         │
    event bus (WebSocket broadcast, Lamport timestamps, content-based routing)
         │
    Orbit web app (projection — never writes to org/ directly)
```

## Design Principles

1. **Silent by default.** Agents orbit quietly. Interface surfaces nothing unless a boundary is crossed.
2. **Govern by boundary, not instruction.** Set invariants, not procedures.
3. **File-based system of record.** org/ is the truth. Orbit is a projection. Git is the audit trail.
4. **Bidirectional legibility.** Agents are legible to humans AND humans are legible to agents.
5. **Attention is finite.** Budget interrupts. Track governance time. Resist engagement.

## License

Business Source License 1.1 — see LICENSE-BSL
