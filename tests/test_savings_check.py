"""TDD tests for memory-savings-check (stdlib + pytest only)."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "memory-savings-check" / "scripts" / "savings_check.py"


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def run(memory_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--memory-dir", str(memory_dir), *args],
        capture_output=True,
        text=True,
    )


def test_totals_and_percentage(tmp_path):
    write_jsonl(tmp_path / "ledger.jsonl", [
        {"task_id": "t1", "context_tokens_would_be": 26000, "injected_tokens": 1800},
        {"task_id": "t2", "context_tokens_would_be": 24000, "injected_tokens": 2000},
    ])
    proc = run(tmp_path, "--format", "json")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["tokens_saved"] == 46200
    assert data["savings_pct"] == 92.4
    assert data["tasks"] == 2


def test_no_stores_exits_2(tmp_path):
    proc = run(tmp_path)
    assert proc.returncode == 2
    assert "no memory stores" in proc.stderr


def test_table_output_is_markdown(tmp_path):
    write_jsonl(tmp_path / "ledger.jsonl",
                [{"context_tokens_would_be": 26000, "injected_tokens": 1800}])
    proc = run(tmp_path, "--format", "table")
    assert proc.returncode == 0
    lines = proc.stdout.splitlines()
    assert lines[0] == "| Metric | Value |"
    assert lines[1] == "| --- | --- |"
    assert "| Savings | 93.1% |" in proc.stdout


def test_facts_status_is_counted(tmp_path):
    write_jsonl(tmp_path / "facts.jsonl", [
        {"entity": "user", "status": "active"},
        {"entity": "api", "status": "superseded"},
        {"entity": "config", "status": "flagged"},
    ])
    proc = run(tmp_path, "--format", "json")
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["facts"] == {
        "active": 1, "superseded": 1, "flagged": 1,
    }


def test_fail_under_gate(tmp_path):
    write_jsonl(tmp_path / "ledger.jsonl",
                [{"context_tokens_would_be": 10000, "injected_tokens": 9000}])
    proc = run(tmp_path, "--fail-under", "50")
    assert proc.returncode == 1
    assert "FAIL" in proc.stderr


def test_malformed_jsonl_is_reported(tmp_path):
    (tmp_path / "ledger.jsonl").write_text("{not json}\n", encoding="utf-8")
    proc = run(tmp_path)
    assert proc.returncode == 2
    assert "invalid JSON" in proc.stderr


def test_plain_output_mentions_savings(tmp_path):
    write_jsonl(tmp_path / "ledger.jsonl",
                [{"context_tokens_would_be": 26000, "injected_tokens": 1800}])
    proc = run(tmp_path)
    assert proc.returncode == 0
    assert "Memory saved 24,200 tokens" in proc.stdout
