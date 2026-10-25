---
name: forgetting-engine
description: Use when pruning stale data. Resolves contradictions.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Obsidian, Memory, Forgetting, Engine]
    related_skills: [working-memory, episodic-memory, semantic-memory, procedural-memory]
---

# Forgetting Engine

## When to Use
- On a schedule (daily), to expire, supersede and flag.
- When two facts about the same entity contradict each other.
- When a stored skill's preconditions are no longer satisfied.

## Purpose
Prevents contradictions and cognitive load by pruning stale data, resolving contradictions, and superseding outdated facts. Forgetting is a feature, not a bug.

## Vault Structure
- `00-Inbox/forgetting-rules.yaml` - Forgetting rules configuration
- `00-Inbox/forgetting-log.jsonl` - Archive of expired/superseded items
- `01-Projects/{{project-name}}/forgetting/` - Project-specific rules

## Three Forgetting Operations
| Operation | When to Use |
|-----------|-------------|
| Expiration | Routine cleanup - remove facts older than threshold |
| Supersession | When facts change - replace old fact with new version |
| Contradiction resolution | When both facts are current - flag for review |

## Retention Policies
### Episodic TTL
- Default: 90 days
- Archive high-value episodes permanently
- Expire routine episodes after 30 days
- User can pin episodes that should never expire

### Semantic Fact Expiration
- Schedule regular audits: compare facts against current reality
- Flag facts not confirmed in 90 days
- Let users correct facts directly

### Skill Obsolescence
- Skills become invalid when tools change
- Version skills track compatibility
- Auto-expire skills whose preconditions are no longer met

## Operations
### `expire_old` - Expire episodes beyond TTL
### `supersede_fact` - Replace old fact with newer version
### `resolve_contradictions` - Flag conflicting facts
### `daily_cleanup` - Run daily forgetting engine cycle

## Hot/Warm/Cold Storage Tiers
| Tier | Access Time | Storage | Contents |
|------|-------------|---------|---------|
| Hot | 0ms (in context) | Context window | Current state, top-3 episodes |
| Warm | 100-500ms | SQLite / Mem0 | 30-day episodes, active facts |
| Cold | 1-5s | S3 / Archive | Old episodes, superseded facts |
