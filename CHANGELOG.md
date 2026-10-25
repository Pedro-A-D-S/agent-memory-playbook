# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
