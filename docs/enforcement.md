# Enforcement

The skills tell an agent to query memory before a task and to write it back
afterwards. An instruction can be skipped: the agent forgets, the context gets
compacted, or a task feels too small to bother. `enforcement/memory_gate.py`
is the part that runs whether or not the agent remembers.

It is one standard-library Python script with five modes. Three are Claude Code
hooks, one is a gate for CI or git, and one installs the hooks.

| Mode | Runs when | What it does | Layer it guards |
| --- | --- | --- | --- |
| `session-start` | Claude Code `SessionStart` | Injects store counts, every fact that is `flagged` or contradicts another active fact, the 5 most recent episodes, and all skill triggers. Records when the session started. | Working, Forgetting |
| `user-prompt` | Claude Code `UserPromptSubmit` (every prompt you type or paste) | Injects the pre-task checklist, then up to 3 skills, 6 facts and 4 episodes whose words overlap the prompt. Superseded facts and episodes older than 90 days (unless `pinned`) are never injected. | Procedural, Semantic, Episodic |
| `stop` | Claude Code `Stop` | If the project got git commits during the session and `episodes.jsonl` got no episode with a `ts` after the session started, it blocks the stop **once** per commit and asks the agent to log the episode. | Episodic |
| `check` | CI, pre-commit, by hand | Validates the stores (required fields, `outcome` and `status` values, ISO timestamps) and fails on two active facts with the same `entity` + `relation` and different values. | Semantic, Forgetting |
| `install` | Once per project | Copies the script to `<project>/.claude/hooks/` and merges the three hooks into `<project>/.claude/settings.json`. | none |

## Install the hooks (Claude Code)

```bash
./install/install.sh --enforce /path/to/project          # with the skills
python enforcement/memory_gate.py install --project /path/to/project   # hooks only
```

```powershell
.\install\install.ps1 -Enforce C:\path\to\project
```

`install` is idempotent. It replaces its own previous entries, keeps any other
hooks already in `settings.json`, and refuses to touch a `settings.json` that is
not valid JSON. Add `--dry-run` (`-DryRun`) to preview. The hooks take effect in
the next Claude Code session started in that project.

The store is read from `$MEMORY_DIR`, or `<project>/memory/` when that is unset,
in the JSONL format of [`examples/quickstart/memory/`](../examples/quickstart/memory/).

## Gate other agents with `check`

Hermes Agent and Google Antigravity get the skills and the generated `AGENTS.md`,
which are instructions. This package does not install hooks for them. What works
for any agent is to refuse a commit or a merge when the memory is inconsistent:

```bash
# .git/hooks/pre-commit
python enforcement/memory_gate.py check --memory-dir memory || exit 1
```

```yaml
# GitHub Actions step
- run: python enforcement/memory_gate.py check --memory-dir memory
```

`check` exits 0 when the stores are valid, 1 when it found problems (each one
printed with its file and line), and 2 on bad arguments.

## What it does not do

- **Retrieval is word overlap, not meaning.** A prompt that shares no word of
  three or more letters with the store gets the checklist and nothing else.
- **`stop` only notices git commits.** Work that was never committed does not
  trigger it, and a project that is not a git repository is never blocked.
- **It never writes memory.** The agent still writes the episode and the facts;
  the gate only makes skipping that visible.
- **A hook error is a warning, not a failure.** If the script crashes, Claude
  Code shows `memory_gate <mode> failed: ...` and the session goes on.
- It makes no network calls and no LLM calls.
