#!/usr/bin/env python3
"""memory_gate - make an agent actually use the 5-layer memory.

Skills and AGENTS.md text are instructions an agent can forget. This script is
the part that does not forget: Claude Code runs it as hooks, and any agent's CI
or git pre-commit can run its `check` mode.

Modes
    session-start  hook: inject flagged/contradicting facts, recent episodes,
                   skill triggers; record when the session started
    user-prompt    hook: inject the pre-task checklist plus the facts, episodes
                   and skills whose words overlap the prompt
    stop           hook: block once when the project got git commits this
                   session but episodes.jsonl got no new episode
    check          CI / pre-commit: validate the stores, fail on contradictions
    install        copy this script into <project>/.claude/hooks/ and merge the
                   three hooks into <project>/.claude/settings.json

Hook modes never fail the session: an internal error becomes a warning.
No LLM calls. Standard library only (Python 3.9+).

Exit codes (check / install)
    0  ok
    1  check found problems
    2  bad arguments or unreadable input
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_PROBLEMS = 1
EXIT_USAGE = 2

EPISODE_OUTCOMES = {"success", "failure", "partial"}
FACT_STATUSES = {"active", "superseded", "flagged"}
REQUIRED = {
    "episodes.jsonl": ("task_id", "ts", "task_description", "outcome"),
    "facts.jsonl": ("entity", "relation", "value", "status"),
    "skills.jsonl": ("name", "trigger"),
}

EPISODE_TTL_DAYS = 90
TOP_FACTS, TOP_EPISODES, TOP_SKILLS = 6, 4, 3
RECENT_EPISODES = 5

CHECKLIST = (
    "Memory gate - before acting: (1) use a procedural skill whose trigger matches, "
    "(2) read the similar episodes below and skip their dead ends, (3) treat the facts "
    "below as true unless flagged. After the task: append the outcome to episodes.jsonl, "
    "add new facts to facts.jsonl (supersede the old row, never add a second active one), "
    "propose a skill after 3 successes."
)

STOPWORDS = set(
    "the and for are with from that this have what when your will into just make "
    "not but can you our out all any how its was were been has had did does".split()
)

HOOK_MODES = ("session-start", "user-prompt", "stop")
HOOK_EVENTS = {"session-start": "SessionStart", "user-prompt": "UserPromptSubmit", "stop": "Stop"}


# --------------------------------------------------------------- input layer

def read_jsonl(path: Path, strict: bool = False) -> list[dict[str, Any]]:
    """Missing file -> []. Bad lines are skipped, or raise ValueError when strict."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            if strict:
                raise ValueError(f"{path.name}:{lineno}: invalid JSON ({exc.msg})")
            continue
        if not isinstance(obj, dict):
            if strict:
                raise ValueError(f"{path.name}:{lineno}: expected a JSON object")
            continue
        obj["_line"] = lineno
        rows.append(obj)
    return rows


def project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def memory_dir(override: str | None = None) -> Path:
    if override:
        return Path(override)
    if os.environ.get("MEMORY_DIR"):
        return Path(os.environ["MEMORY_DIR"])
    return project_dir() / "memory"


def parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------- the layers

def contradictions(facts: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    """Active facts sharing entity+relation with different values."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for f in facts:
        if f.get("status") == "active":
            groups.setdefault(f"{f.get('entity')}.{f.get('relation')}", []).append(f)
    return [(k, g) for k, g in groups.items() if len({json.dumps(x.get("value")) for x in g}) > 1]


def fact_text(f: dict[str, Any]) -> str:
    return f"{f.get('entity')} {f.get('relation')} {f.get('value')} [{f.get('status')}]"


def episode_text(e: dict[str, Any]) -> str:
    extra = e.get("resolution") or e.get("errors_encountered") or ""
    tail = f" - {extra}" if extra else ""
    return f"{e.get('ts', '?')[:10]} {e.get('task_description')} -> {e.get('outcome')}{tail}"


def hot_episodes(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Episodes inside the TTL, plus pinned ones (the forgetting rule for retrieval)."""
    cutoff = now() - timedelta(days=EPISODE_TTL_DAYS)
    out = []
    for e in episodes:
        ts = parse_ts(e.get("ts"))
        if e.get("pinned") or ts is None or ts >= cutoff:
            out.append(e)
    return out


# --------------------------------------------------------------- retrieval

def tokenize(text: str) -> set[str]:
    norm = unicodedata.normalize("NFD", text)
    norm = "".join(c for c in norm if unicodedata.category(c) != "Mn").lower()
    return {w for w in re.findall(r"[a-z0-9_]{3,}", norm) if w not in STOPWORDS}


def rank(items: list[tuple[str, Any]], tokens: set[str], k: int) -> list[str]:
    """Term overlap; a long shared word counts double. Needs a score of 2 to show."""
    scored = []
    for text, _ in items:
        words = tokenize(text)
        score = sum(2 if len(t) >= 6 else 1 for t in tokens if t in words)
        if score >= 2:
            scored.append((score, text))
    scored.sort(key=lambda s: -s[0])
    return [t for _, t in scored[:k]]


# --------------------------------------------------------------- session state

def state_path(session_id: str) -> Path:
    safe = re.sub(r"[^\w-]", "_", session_id or "default")
    return Path(tempfile.gettempdir()) / "memory-gate" / f"{safe}.json"


def load_state(session_id: str) -> dict[str, Any] | None:
    try:
        return json.loads(state_path(session_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save_state(session_id: str, state: dict[str, Any]) -> dict[str, Any]:
    p = state_path(session_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state), encoding="utf-8")
    return state


def git_commits_since(cwd: Path, since: str) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(cwd), "log", "--all", f"--since={since}", "--format=%h"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return out.stdout.split() if out.returncode == 0 else []


# --------------------------------------------------------------- hook modes

def hook_session_start(payload: dict[str, Any], mem: Path) -> dict[str, Any]:
    save_state(payload.get("session_id", ""), {"start": now().isoformat(), "blocked_for": None})
    facts = read_jsonl(mem / "facts.jsonl")
    episodes = hot_episodes(read_jsonl(mem / "episodes.jsonl"))
    skills = read_jsonl(mem / "skills.jsonl")
    if not (facts or episodes or skills):
        return context("SessionStart", f"Memory gate: no memory store at {mem}. "
                       "Create it with the episodic-memory skill before the first task.")

    parts = [f"# Memory (injected by memory_gate from {mem})"]
    active = [f for f in facts if f.get("status") == "active"]
    parts.append(f"{len(active)} active facts, {len(episodes)} episodes in the last "
                 f"{EPISODE_TTL_DAYS} days or pinned, {len(skills)} skills.")
    bad = [f for f in facts if f.get("status") == "flagged"]
    for key, group in contradictions(facts):
        bad.extend(group)
    if bad:
        parts.append("## Not usable as premises until resolved (flagged or contradicting)\n"
                     + "\n".join(f"- {fact_text(f)}" for f in bad))
    recent = sorted(episodes, key=lambda e: e.get("ts", ""), reverse=True)[:RECENT_EPISODES]
    if recent:
        parts.append("## Recent episodes\n" + "\n".join(f"- {episode_text(e)}" for e in recent))
    if skills:
        parts.append("## Skill triggers\n" + "\n".join(
            f"- {s.get('name')}: {s.get('trigger')}" for s in skills))
    return context("SessionStart", "\n\n".join(parts))


def hook_user_prompt(payload: dict[str, Any], mem: Path) -> dict[str, Any]:
    tokens = tokenize(str(payload.get("prompt", "")))
    lines = [CHECKLIST]
    if tokens:
        facts = [(fact_text(f), f) for f in read_jsonl(mem / "facts.jsonl")
                 if f.get("status") != "superseded"]
        eps = [(episode_text(e), e) for e in hot_episodes(read_jsonl(mem / "episodes.jsonl"))]
        skills = [(f"{s.get('name')}: {s.get('trigger')}", s) for s in read_jsonl(mem / "skills.jsonl")]
        for title, items, k in (("Matching skills", skills, TOP_SKILLS),
                                ("Related facts", facts, TOP_FACTS),
                                ("Similar episodes", eps, TOP_EPISODES)):
            hits = rank(items, tokens, k)
            if hits:
                lines.append(f"{title}:\n" + "\n".join(f"- {h}" for h in hits))
    return context("UserPromptSubmit", "\n\n".join(lines))


def hook_stop(payload: dict[str, Any], mem: Path) -> dict[str, Any] | None:
    if payload.get("stop_hook_active"):
        return None
    sid = payload.get("session_id", "")
    state = load_state(sid) or save_state(sid, {"start": now().isoformat(), "blocked_for": None})
    commits = git_commits_since(project_dir(), state["start"])
    if not commits:
        return None
    start = parse_ts(state["start"])
    new_eps = [e for e in read_jsonl(mem / "episodes.jsonl")
               if (ts := parse_ts(e.get("ts"))) and start and ts >= start]
    if new_eps or state.get("blocked_for") == commits[0]:
        return None  # already logged, or already asked once for these commits
    save_state(sid, {**state, "blocked_for": commits[0]})
    return {
        "decision": "block",
        "reason": (
            f"{len(commits)} commit(s) landed this session (latest {commits[0]}) but "
            f"{mem / 'episodes.jsonl'} has no episode since {state['start']}. Before stopping: "
            "append the episode (task, approach, outcome, errors, resolution), move new durable "
            "facts to facts.jsonl, supersede what they replace. If nothing here is worth "
            "remembering, say so to the user in one line and stop."
        ),
    }


def context(event: str, text: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


def run_hook(mode: str, mem: Path) -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    try:
        handler = {"session-start": hook_session_start, "user-prompt": hook_user_prompt,
                   "stop": hook_stop}[mode]
        out = handler(payload, mem)
    except Exception as exc:  # a memory hook must never break the session
        out = {"systemMessage": f"memory_gate {mode} failed: {exc}"}
    if out:
        sys.stdout.write(json.dumps(out))
    return EXIT_OK


# --------------------------------------------------------------- check

def check(mem: Path) -> list[str]:
    problems: list[str] = []
    found = False
    for name, fields in REQUIRED.items():
        path = mem / name
        if not path.exists():
            continue
        found = True
        try:
            rows = read_jsonl(path, strict=True)
        except ValueError as exc:
            problems.append(str(exc))
            continue
        for r in rows:
            where = f"{name}:{r['_line']}"
            missing = [f for f in fields if f not in r]
            if missing:
                problems.append(f"{where}: missing {', '.join(missing)}")
            if name == "episodes.jsonl":
                if "outcome" in r and r["outcome"] not in EPISODE_OUTCOMES:
                    problems.append(f"{where}: outcome must be one of {sorted(EPISODE_OUTCOMES)}")
                if "ts" in r and parse_ts(r["ts"]) is None:
                    problems.append(f"{where}: ts is not ISO 8601")
            if name == "facts.jsonl" and "status" in r and r["status"] not in FACT_STATUSES:
                problems.append(f"{where}: status must be one of {sorted(FACT_STATUSES)}")
        if name == "facts.jsonl":
            for key, group in contradictions(rows):
                lines = ", ".join(str(f["_line"]) for f in group)
                problems.append(f"facts.jsonl: contradiction on {key} (lines {lines}); "
                                "supersede or flag all but one")
    if not found:
        problems.append(f"no memory stores in {mem}")
    return problems


# --------------------------------------------------------------- install

def python_cmd() -> str:
    return "python" if os.name == "nt" else "python3"


def install(project: Path, dry_run: bool = False) -> list[str]:
    hooks_dir = project / ".claude" / "hooks"
    settings_path = project / ".claude" / "settings.json"
    script = hooks_dir / "memory_gate.py"
    log = [f"copy {Path(__file__).name} -> {script}", f"merge hooks -> {settings_path}"]
    if dry_run:
        return log

    settings: dict[str, Any] = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise SystemExit(f"error: {settings_path} is not valid JSON ({exc}); fix it first")
    hooks = settings.setdefault("hooks", {})
    for mode in HOOK_MODES:
        event = HOOK_EVENTS[mode]
        # Idempotent: drop our previous entries, keep everyone else's.
        kept = [m for m in hooks.get(event, [])
                if not any("memory_gate.py" in h.get("command", "") for h in m.get("hooks", []))]
        kept.append({"hooks": [{
            "type": "command",
            "command": f'{python_cmd()} "$CLAUDE_PROJECT_DIR/.claude/hooks/memory_gate.py" {mode}',
            "timeout": 15,
        }]})
        hooks[event] = kept

    hooks_dir.mkdir(parents=True, exist_ok=True)
    if Path(__file__).resolve() != script.resolve():
        shutil.copyfile(Path(__file__), script)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return log


# --------------------------------------------------------------- cli

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="memory_gate", description=__doc__.split("\n\n")[0])
    ap.add_argument("mode", choices=(*HOOK_MODES, "check", "install"))
    ap.add_argument("--memory-dir", help="default: $MEMORY_DIR, else <project>/memory")
    ap.add_argument("--project", help="install: project root (default: current directory)")
    ap.add_argument("--dry-run", action="store_true", help="install: print, write nothing")
    args = ap.parse_args(argv)

    if args.mode in HOOK_MODES:
        return run_hook(args.mode, memory_dir(args.memory_dir))
    if args.mode == "check":
        problems = check(memory_dir(args.memory_dir))
        for p in problems:
            print(f"error: {p}", file=sys.stderr)
        if not problems:
            print("memory_gate: stores valid, no contradictions")
        return EXIT_PROBLEMS if problems else EXIT_OK
    for line in install(Path(args.project or os.getcwd()), args.dry_run):
        print(("(dry-run) " if args.dry_run else "") + line)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
