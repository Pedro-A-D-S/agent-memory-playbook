"""Tests for enforcement/memory_gate.py (stdlib + pytest only)."""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "enforcement" / "memory_gate.py"
QUICKSTART = REPO / "examples" / "quickstart" / "memory"


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def run(*args: str, stdin: dict | None = None, project: Path | None = None, tmp=None):
    env = {**os.environ}
    if project is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project)
    if tmp is not None:  # isolate per-session state between tests
        env["TMP"] = env["TEMP"] = env["TMPDIR"] = str(tmp)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=json.dumps(stdin or {}), capture_output=True, text=True, env=env,
    )


def additional_context(proc) -> str:
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


# --------------------------------------------------------------- user-prompt

def test_prompt_injects_checklist_and_matching_memory(tmp_path):
    proc = run("user-prompt", "--memory-dir", str(QUICKSTART),
               stdin={"prompt": "deploy the frontend to production again"}, tmp=tmp_path)
    ctx = additional_context(proc)
    assert ctx.startswith("Memory gate - before acting")
    assert "deploy-frontend: deploy frontend to production" in ctx
    assert "deploy frontend to staging -> success" in ctx


def test_prompt_with_no_overlap_gets_only_checklist(tmp_path):
    ctx = additional_context(run("user-prompt", "--memory-dir", str(QUICKSTART),
                                 stdin={"prompt": "explain a biquad filter"}, tmp=tmp_path))
    assert "Matching skills" not in ctx and "Related facts" not in ctx


def test_prompt_hides_superseded_facts(tmp_path):
    ctx = additional_context(run("user-prompt", "--memory-dir", str(QUICKSTART),
                                 stdin={"prompt": "where is the users api located"}, tmp=tmp_path))
    assert "/v2/users" in ctx and "/v1/users" not in ctx


# --------------------------------------------------------------- session-start

def test_session_start_lists_contradictions(tmp_path):
    mem = tmp_path / "memory"
    write_jsonl(mem / "facts.jsonl", [
        {"entity": "deploy", "relation": "target", "value": "staging", "status": "active"},
        {"entity": "deploy", "relation": "target", "value": "production", "status": "active"},
    ])
    ctx = additional_context(run("session-start", "--memory-dir", str(mem),
                                 stdin={"session_id": "s"}, tmp=tmp_path))
    assert "Not usable as premises" in ctx
    assert "deploy target staging" in ctx and "deploy target production" in ctx


def test_session_start_without_store_says_so(tmp_path):
    ctx = additional_context(run("session-start", "--memory-dir", str(tmp_path / "none"),
                                 stdin={"session_id": "s"}, tmp=tmp_path))
    assert "no memory store" in ctx


def test_old_unpinned_episodes_are_not_injected(tmp_path):
    mem = tmp_path / "memory"
    old = iso(datetime.now(timezone.utc) - timedelta(days=200))
    write_jsonl(mem / "episodes.jsonl", [
        {"task_id": "a", "ts": old, "task_description": "ancient task", "outcome": "success"},
        {"task_id": "b", "ts": old, "task_description": "pinned task", "outcome": "success",
         "pinned": True},
    ])
    ctx = additional_context(run("session-start", "--memory-dir", str(mem),
                                 stdin={"session_id": "s"}, tmp=tmp_path))
    assert "pinned task" in ctx and "ancient task" not in ctx


# --------------------------------------------------------------- stop

def stop_setup(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    git(project, "init", "-q")
    mem = project / "memory"
    write_jsonl(mem / "episodes.jsonl", [])
    run("session-start", "--memory-dir", str(mem), stdin={"session_id": "s"},
        project=project, tmp=tmp_path)
    (project / "f.txt").write_text("x")
    git(project, "add", ".")
    git(project, "commit", "-q", "-m", "work")
    return project, mem


def test_stop_blocks_once_after_commit_without_episode(tmp_path):
    project, mem = stop_setup(tmp_path)
    first = run("stop", "--memory-dir", str(mem), stdin={"session_id": "s"},
                project=project, tmp=tmp_path)
    assert json.loads(first.stdout)["decision"] == "block"
    second = run("stop", "--memory-dir", str(mem), stdin={"session_id": "s"},
                 project=project, tmp=tmp_path)
    assert second.stdout == ""


def test_stop_passes_when_episode_was_logged(tmp_path):
    project, mem = stop_setup(tmp_path)
    write_jsonl(mem / "episodes.jsonl", [{
        "task_id": "t", "ts": iso(datetime.now(timezone.utc) + timedelta(seconds=1)),
        "task_description": "work", "outcome": "success"}])
    proc = run("stop", "--memory-dir", str(mem), stdin={"session_id": "s"},
               project=project, tmp=tmp_path)
    assert proc.stdout == ""


def test_stop_respects_stop_hook_active(tmp_path):
    project, mem = stop_setup(tmp_path)
    proc = run("stop", "--memory-dir", str(mem),
               stdin={"session_id": "s", "stop_hook_active": True}, project=project, tmp=tmp_path)
    assert proc.stdout == ""


def test_hook_error_is_a_warning_not_a_crash(tmp_path):
    bad = tmp_path / "memory"
    bad.mkdir()
    (bad / "facts.jsonl").mkdir()  # a directory where a file is expected
    proc = run("session-start", "--memory-dir", str(bad), stdin={"session_id": "s"}, tmp=tmp_path)
    assert proc.returncode == 0
    assert "failed" in json.loads(proc.stdout)["systemMessage"]


# --------------------------------------------------------------- check

def test_check_quickstart_is_clean():
    proc = run("check", "--memory-dir", str(QUICKSTART))
    assert proc.returncode == 0, proc.stderr


def test_check_fails_on_contradiction_and_bad_fields(tmp_path):
    write_jsonl(tmp_path / "facts.jsonl", [
        {"entity": "user", "relation": "prefers", "value": "Python", "status": "active"},
        {"entity": "user", "relation": "prefers", "value": "TypeScript", "status": "active"},
    ])
    write_jsonl(tmp_path / "episodes.jsonl", [
        {"task_id": "t", "ts": "yesterday", "task_description": "x", "outcome": "done"},
    ])
    proc = run("check", "--memory-dir", str(tmp_path))
    assert proc.returncode == 1
    assert "contradiction on user.prefers" in proc.stderr
    assert "outcome must be one of" in proc.stderr
    assert "ts is not ISO 8601" in proc.stderr


# --------------------------------------------------------------- install

def test_install_is_idempotent_and_keeps_other_hooks(tmp_path):
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    other = {"hooks": [{"type": "command", "command": "echo mine"}]}
    settings.write_text(json.dumps({"hooks": {"Stop": [other]}, "model": "opus"}))
    for _ in range(2):
        assert run("install", "--project", str(tmp_path)).returncode == 0
    data = json.loads(settings.read_text())
    assert data["model"] == "opus"
    assert other in data["hooks"]["Stop"]
    for event in ("SessionStart", "UserPromptSubmit", "Stop"):
        ours = [m for m in data["hooks"][event]
                if "memory_gate.py" in m["hooks"][0]["command"]]
        assert len(ours) == 1
    assert (tmp_path / ".claude" / "hooks" / "memory_gate.py").exists()
