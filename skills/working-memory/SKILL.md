---
name: working-memory
description: Use when starting agent. Saves context per turn.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Obsidian, Memory, Working-Memory, Context]
    related_skills: [episodic-memory, semantic-memory, procedural-memory, forgetting-engine]
---

# Working Memory

## When to Use
- At the start of a session, to establish what the agent can currently see.
- When deciding what to keep versus what to overflow into episodic memory.
- When the context window is approaching its budget and must be compacted.

## Purpose
Working memory is the context window - everything the agent sees right now.

## Vault Structure
- `00-Inbox/working-memory.md` - Current session context
- `00-Inbox/active-task.md` - Active task tracking

## Daily Operations
### Start of Session
1. Create or reset `00-Inbox/working-memory.md` with system prompt and task
2. Check `00-Inbox/active-task.md` for carryover state

### End of Session
1. Save key outcomes to episodic memory
2. Clear temporary context, preserve only critical carryover
3. Archive superseded facts

## Contents Schema
| Content | Purpose | Lifespan |
|---------|---------|----------|
| System prompt | Agent identity and rules | Every call |
| Current conversation | Task context | Current session |
| Tool results | Grounded data | Current task |
| Retrieved documents | RAG context | Current query |
| Injected state | Memory summaries | Current session |

## What NOT to Store
- Verbose reasoning chains (compress them)
- Raw document contents (reference by ID)
- Intermediate drafts (keep only final version and key revision points)

## Operations
### `save_context` - Save current session context
### `clear_temp` - Clear non-essential context before truncation
### `inject_summary` - Inject episodic summary at session start
