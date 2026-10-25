---
name: semantic-memory
description: Use when storing facts. Persists knowledge beyond session.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Obsidian, Memory, Semantic, Knowledge-Graph]
    related_skills: [working-memory, episodic-memory, procedural-memory, forgetting-engine]
---

# Semantic Memory

## When to Use
- When a durable fact is learned (preference, endpoint, ownership, convention).
- Before starting work, to load facts relevant to the current task.
- When a stored fact is contradicted by a newer observation.

## Purpose
Stores durable facts that do not expire when the session ends: user preferences, project configs, API endpoints, team conventions.

## Vault Structure
- `01-Projects/{{project-name}}/semantic/facts.db` - SQLite knowledge graph
- `01-Projects/{{project-name}}/semantic/schema.yaml` - Ontology schema
- `01-Projects/{{project-name}}/semantic/facts.yaml` - Key-value facts
- `02-Areas/{{area}}/semantic/` - Area-level facts

## Ontology Schema (minimal)
```yaml
entity_types: [user, project, api, config]
relation_types: [prefers, owns, depends_on, located_at]
validation:
  user.prefers: {target: string, expires: 90d}
  project.owns: {target: user, required: True}
  api.located_at: {target: string, required: True}
```

## Conflict Resolution
When user now prefers Python over TypeScript: update not append. Operations:
1. Detect duplicates
2. Merge compatible facts
3. Supersede outdated ones (keep newer, flag older)
4. Flag genuine contradictions for human review

## Storage Options
| Storage | Scales To | Query Power |
|---------|-----------|-------------|
| JSON file | <100 facts | Key lookup |
| SQLite | <10K facts | SQL queries |
| Vector DB | Large | Embedding search |
| Knowledge graph | Large | Graph traversal |

## Operations
### `extract_facts` - Extract durable facts from episodic outcomes
### `store_fact` - Store fact with ontology validation
### `resolve_conflicts` - Detect and resolve fact conflicts
### `audit_stale` - Flag facts not confirmed in 90 days
