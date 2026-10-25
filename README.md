# agent-memory-playbook

**A five-layer memory architecture for AI agents — packaged as installable skills for Hermes Agent, Claude Code, and Google Antigravity, plus a deterministic audit that reports how many tokens memory actually saved.**

Your agent reads the same twelve files every morning, reaches the same conclusions, and charges you the same tokens for the privilege. This repository gives it memory.

---

## The five layers

| Layer | Stores | Retrieval | Expiration |
| --- | --- | --- | --- |
| 1. Working | The context window | Always loaded | End of call |
| 2. Episodic | What happened | By similarity | 30–90 days |
| 3. Semantic | What is true | By entity / query | On supersession |
| 4. Procedural | How to do things | By trigger match | On version update |
| 5. Forgetting | What to delete | Scheduled | Continuous |

Working memory overflows into episodic memory. Repeated episodic patterns distil into semantic facts. Reliable semantic methods are promoted to procedural skills. The forgetting engine expires, supersedes, and flags contradictions.

---

## Install

Install the **whole set** — the skills are interdependent and are not useful one at a time.

```bash
git clone https://github.com/Pedro-A-D-S/agent-memory-playbook.git
cd agent-memory-playbook
./install/install.sh         # Linux / macOS / Git-Bash
```

```powershell
git clone https://github.com/Pedro-A-D-S/agent-memory-playbook.git
cd agent-memory-playbook
.\install\install.ps1        # Windows PowerShell
```

| Tool | Installed to |
| --- | --- |
| Hermes Agent | `<HERMES_HOME>/skills/memory/` |
| Claude Code | `<CLAUDE_HOME>/skills/` |
| Google Antigravity | `<workspace>/.agent/skills/` + `<workspace>/AGENTS.md` |

Preview with `--dry-run` / `-DryRun`. Full detail in [docs/installation.md](docs/installation.md).

---

## The savings audit

![savings](https://img.shields.io/badge/savings-92.3%25-brightgreen)

```bash
python skills/memory-savings-check/scripts/savings_check.py \
  --memory-dir ./memory --format table
```

```
| Metric | Value |
| --- | --- |
| Tokens without memory (naive) | 71,000 |
| Tokens injected (with memory) | 5,500 |
| Tokens saved | 65,500 |
| Savings | 92.3% |
| Tasks audited | 3 |
| Episodes stored | 3 |
| Episodes pinned | 1 |
| Facts active | 2 |
| Facts superseded | 1 |
| Facts flagged | 1 |
| Skills promoted | 2 |
| Average skill success rate | 0.83 |
```

Deterministic, standard-library Python, **no LLM calls** — the audit itself costs a few hundred tokens.

| Caller | Flag | Shape |
| --- | --- | --- |
| Human in a terminal | default | short plain-text summary |
| Agent (Hermes / Claude Code / Antigravity) | `--format table` | markdown table |
| Script or CI | `--format json` | one JSON object |

Reproduce the table above straight from a fresh clone:

```bash
python skills/memory-savings-check/scripts/savings_check.py \
  --memory-dir examples/quickstart/memory --format table
```

---

## What is in the box

```
skills/     7 skills (5 layers + orchestration + savings check)
enforcement/ memory_gate.py: Claude Code hooks + a CI/pre-commit check
templates/  MEMORY_CONFIG.yaml, system prompt, episode record
install/    install.sh (POSIX) and install.ps1 (Windows)
examples/   a quickstart memory store you can audit immediately
tests/      pytest suites for the savings check and the memory gate
docs/       distilled 5-layer architecture reference and installation guides
```

---

## Quickstart: the seven-day build path

| Day | Build | Exit test |
| --- | --- | --- |
| 1 | Episodic log (JSON) | Agent recalls yesterday's failure |
| 2 | Retrieval before starting a task | Agent skips known dead ends |
| 3 | Semantic store for durable facts | Agent knows your preferences |
| 4 | Ontology: entity and relation types | Store validates against schema |
| 5 | Procedural skills from repeated success | Agent uses the saved method |
| 6 | Forgetting: expire and supersede | No contradictions in the store |
| 7 | Wire the full pipeline | A multi-session task runs end to end |

Start with Day 1. It costs one file write and one file read per session, and it immediately stops the agent repeating yesterday's mistakes.

---

## Enforcement

Skills are instructions, and an agent can skip them. `enforcement/memory_gate.py` makes the workflow run anyway:

| Where | Mode | Effect |
| --- | --- | --- |
| Claude Code `SessionStart` | `session-start` | Injects flagged or contradicting facts, recent episodes and skill triggers |
| Claude Code `UserPromptSubmit` | `user-prompt` | Every prompt gets the pre-task checklist plus the skills, facts and episodes that match it |
| Claude Code `Stop` | `stop` | Blocks once when the session committed code but logged no episode |
| CI / pre-commit, any agent | `check` | Fails on invalid stores and on contradicting active facts |

```bash
./install/install.sh --enforce /path/to/project     # or: .\install\install.ps1 -Enforce C:\path\to\project
```

Opt-in: nothing is enforced until you pass `--enforce` or run `check`. Details and limits in [docs/enforcement.md](docs/enforcement.md). `--fail-under` on the savings check remains a separate, optional CI gate.

---

## Running the tests

```bash
python -m pytest tests/ -q
```

---

## License

MIT — see [LICENSE](LICENSE).

## Attribution

The architecture is an independent compilation (September 2026) drawing on CoALA, Mem0, Anthropic memory systems, Snowflake ontology research, and LangChain production materials. It is **not affiliated with, or endorsed by, Anthropic, Mem0, Snowflake, or any other organisation.** The distilled summary is documented in [docs/5-layer-architecture.md](docs/5-layer-architecture.md).
