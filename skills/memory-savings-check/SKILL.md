---
name: memory-savings-check
description: Use when auditing token savings. Reports memory ROI.
version: 1.0.0
author: Pedro Alves da Silva
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Memory, Audit, Metrics, ROI]
    related_skills: [memory-orchestration, episodic-memory, semantic-memory, procedural-memory, forgetting-engine]
---

# Memory Savings Check

## When to Use
- The user asks "how much did memory actually save?"
- A weekly or monthly audit of the five-layer system.
- Just after enabling a new layer, to prove it earns its keep.
- As an **opt-in** CI gate via `--fail-under` (never forced).

## What It Does

Reads the JSONL memory stores plus a per-task ledger and reports tokens saved
against a naive "re-read everything" baseline. Deterministic, standard library
only, **no LLM calls** — the audit itself costs a few hundred tokens.

## Command

```bash
python skills/memory-savings-check/scripts/savings_check.py --memory-dir ./memory --format table
```

## Output format per caller

| Invoked by | Flag | Shape |
| --- | --- | --- |
| A human in a terminal | `--format plain` (default) | two short lines |
| An agent (Hermes, Claude Code, Antigravity) | `--format table` | markdown table |
| A script or CI job | `--format json` | one JSON object |

## Ledger format

`memory/ledger.jsonl` — one object per completed task:

```json
{"task_id": "t-001", "ts": "2026-10-25T12:00:00Z", "context_tokens_would_be": 26000, "injected_tokens": 1800, "episodes_reused": 3, "skills_used": 1}
```

- `context_tokens_would_be` — tokens a memoryless agent would have burned re-reading context.
- `injected_tokens` — tokens actually injected from memory for that task.

Savings = `sum(context_tokens_would_be) - sum(injected_tokens)`.

## Read stores

| File | Counts towards |
| --- | --- |
| `memory/ledger.jsonl` | tokens saved, tasks audited |
| `memory/episodes.jsonl` | episodes stored, pinned |
| `memory/facts.jsonl` | facts active / superseded / flagged |
| `memory/skills.jsonl` | skills promoted, average success rate |

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | audit ran |
| `1` | savings below `--fail-under` (only when that flag is passed) |
| `2` | no memory stores found, or malformed JSONL |

## Enforcement policy

This package **does not enforce** memory usage. The check is read-only.
`--fail-under` exists for teams that want a CI gate; it is off unless passed.
