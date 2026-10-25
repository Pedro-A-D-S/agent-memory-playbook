# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `enforcement/memory_gate.py`: Claude Code hooks that inject memory at session
  start and on every prompt, and block a stop once when commits landed without a
  new episode; a `check` mode for CI and pre-commit that fails on invalid stores
  and contradicting active facts; an idempotent `install` mode.
- `--enforce DIR` / `-Enforce DIR` in both installers.
- `docs/enforcement.md` and a pytest suite for the gate.

### Changed
- README and installation guide: the "No enforcement" sections now describe the
  opt-in enforcement.

## [1.0.0] - 2026-10-25

### Added
- Five-layer memory skills: `working-memory`, `episodic-memory`,
  `semantic-memory`, `procedural-memory`, `forgetting-engine`.
- `memory-orchestration` skill wiring the layers and the seven-day build path.
- `memory-savings-check` skill with a deterministic, no-LLM token-savings audit.
- Installers for Hermes Agent, Claude Code, and Google Antigravity
  (`install/install.sh`, `install/install.ps1`).
- Templates for the memory config, memory-aware system prompt, and episode record.
- Quickstart example memory store and a pytest suite for the savings check.
- Distilled 5-layer architecture reference and installation guides under `docs/`.
