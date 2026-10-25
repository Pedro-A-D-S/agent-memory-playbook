---
name: episodic-memory
description: Use when saving interaction logs. Records outcomes per task.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Obsidian, Memory, Episodic, Logs]
    related_skills: [working-memory, semantic-memory, procedural-memory, forgetting-engine]
---

# Episodic Memory

## When to Use
- After finishing any task, to record what was attempted and what happened.
- Before starting a task that resembles one done previously.
- When the agent is about to repeat an approach that may already have failed.

## Purpose
Records what happened during agent interactions: tasks attempted, approaches tried, successes/failures, and why. Prevents repeating mistakes.

## Vault Structure
- `00-Inbox/episodic-log.jsonl` - Append-only journal of episodes
- `01-Projects/{{project-name}}/episodic/` - Project-specific logs
- `02-Areas/{{area}}/episodic/` - Area-specific logs

## Episode Record Schema
```yaml
task_id: str
timestamp: datetime
task_description: str
approach: str
outcome: str  # success | failure | partial
errors_encountered: list[str]
key_decisions: list[str]
```

## Daily Operations
### Save Episode (after each task)
1. Append JSON object to `00-Inbox/episodic-log.jsonl`
2. Include: task_id, timestamp, description, approach, outcome, errors, key decisions
3. Tag with project/area for filtering

### Retrieve Relevant Episodes
1. Before starting a new task, query `00-Inbox/episodic-log.jsonl`
2. Filter by similarity to task description, tool overlap, or tags
3. Inject top 3 most relevant episode summaries into working memory

### Retention Policy
- Keep last 90 days by default
- Archive high-value episodes permanently
- Expire routine episodes after 30 days
- User can override with explicit pins

## Operations
### `save_episode` - Append episode to JSONL journal
### `retrieve_similar` - Find episodes similar to current task
### `check_retention` - Verify episodes within retention policy
