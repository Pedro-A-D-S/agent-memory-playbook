---
name: procedural-memory
description: Use when promoting methods. Saves skills after repeats.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Obsidian, Memory, Procedural, Skills]
    related_skills: [working-memory, episodic-memory, semantic-memory, forgetting-engine]
---

# Procedural Memory

## When to Use
- When the same task type has succeeded three or more times.
- When a new task arrives and a saved method may already cover it.
- When an existing skill's steps no longer match reality and must be versioned.

## Purpose
Stores methods that worked as reusable skills. Promotes methods only when task recurs weekly, succeeds 3+ times, steps are unambiguous, and tools are reliably available.

## Vault Structure
- `01-Projects/{{project-name}}/procedural/skills.yaml` - Skills catalog
- `01-Projects/{{project-name}}/procedural/skill-{{name}}.yaml` - Individual skill files
- `02-Areas/{{area}}/procedural/` - Area-level skills

## Skill Structure
```yaml
name: deploy-frontend
ttrigger: 'deploy frontend to production'
steps:
- run: npm run build
- verify: build/index.html exists
- run: aws s3 sync build/ s3://prod-bucket
- verify: curl https://app.example.com returns 200
preconditions:
- AWS credentials configured
- npm dependencies installed
failure_modes:
- build failure: check node version
- s3 permission denied: check IAM role
```

## Skill Promotion Bar
All criteria must be met:
- Task recurs at least weekly
- Method succeeded at least 3 times
- Steps described without ambiguity
- Tools reliably available

## Versioning
Update steps, increment version, keep rollback to previous version.

## Operations
### `promote_skill` - Trigger promotion after 3 successes
### `load_skill` - Load matching skill for task type
### `version_skill` - Update skill with new version
### `list_skills` - List available skills with triggers and success rates
