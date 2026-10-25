# Installation

The six memory skills and the savings check are **interdependent**. Install the
whole set — installing one or two in isolation leaves the pipeline broken.

## One command per tool

### Linux / macOS / Git-Bash

```bash
git clone https://github.com/Pedro-A-D-S/agent-memory-playbook.git
cd agent-memory-playbook
./install/install.sh                 # all three tools
./install/install.sh --target hermes # just one (not recommended)
./install/install.sh --dry-run       # preview
```

### Windows PowerShell

```powershell
git clone https://github.com/Pedro-A-D-S/agent-memory-playbook.git
cd agent-memory-playbook
.\install\install.ps1
.\install\install.ps1 -Target hermes
.\install\install.ps1 -DryRun
```

Both installers are idempotent. Re-running them backs up the previous copy of a
skill to `<skill>.bak-<timestamp>` before replacing it.

## Where each tool looks

| Tool | Destination | Override |
| --- | --- | --- |
| Hermes Agent | `<HERMES_HOME>/skills/memory/` | `HERMES_HOME` — defaults to `~/.hermes`, else `%LOCALAPPDATA%\hermes` |
| Claude Code | `<CLAUDE_HOME>/skills/` | `CLAUDE_HOME` — defaults to `~/.claude` |
| Google Antigravity | `<workspace>/.agent/skills/` plus a generated `<workspace>/AGENTS.md` | `ANTIGRAVITY_WORKSPACE` |

> The Antigravity destination was verified against Antigravity's documentation
> while writing `install/install.sh`. If your Antigravity build reads a different
> directory, pass `ANTIGRAVITY_WORKSPACE` or copy `skills/*` there manually and
> open an issue.

## What gets installed

| Skill | Purpose |
| --- | --- |
| `working-memory` | The context window: what the agent sees right now |
| `episodic-memory` | What happened: task, approach, outcome, errors |
| `semantic-memory` | What is true: durable facts and relations |
| `procedural-memory` | How to do things: reusable, versioned skills |
| `forgetting-engine` | What to delete: expire, supersede, flag |
| `memory-orchestration` | Wires the five layers and follows the 7-day build path |
| `memory-savings-check` | Reports how many tokens memory actually saved |

## Enforcement (opt-in)

Add `--enforce <project>` (`-Enforce <project>` in PowerShell) to also install
the Claude Code hooks that make an agent load memory before each prompt and log
an episode before it stops:

```bash
./install/install.sh --enforce ~/code/my-project
```

For Hermes Agent and Antigravity, gate commits or CI with
`python enforcement/memory_gate.py check`. See [enforcement.md](enforcement.md).

## Verify the install

```bash
python skills/memory-savings-check/scripts/savings_check.py \
  --memory-dir examples/quickstart/memory --format table
```

Expected `| Savings | 92.3% |`.
