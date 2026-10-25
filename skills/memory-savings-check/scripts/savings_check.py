#!/usr/bin/env python3
"""memory-savings-check - deterministic memory ROI audit.

Reads JSONL memory stores plus a per-task ledger and reports how many tokens
memory retrieval saved versus a naive "re-read everything" baseline.

No LLM calls. Standard library only (Python 3.9+).

Exit codes
    0  audit ran
    1  savings below --fail-under (only when that flag is passed)
    2  no memory stores found, or malformed input
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

EXIT_OK = 0
EXIT_BELOW = 1
EXIT_NODATA = 2

STORE_FILES = ("ledger.jsonl", "episodes.jsonl", "facts.jsonl", "skills.jsonl")

BENCHMARK = (
    ("Tokens per query (no memory)", "26,000", "Mem0"),
    ("Tokens per query (with memory)", "1,800", "Mem0"),
    ("Token reduction", "90%", "Mem0"),
    ("Latency reduction", "91%", "Mem0"),
    ("Accuracy gain", "+20%", "Snowflake"),
    ("Tool-call reduction", "39%", "Snowflake"),
)


# --------------------------------------------------------------- input layer

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse a .jsonl file. Missing file -> []. Bad input -> exit 2."""
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
            print(f"error: {path}:{lineno}: invalid JSON ({exc.msg})", file=sys.stderr)
            raise SystemExit(EXIT_NODATA)
        if not isinstance(obj, dict):
            print(f"error: {path}:{lineno}: expected a JSON object", file=sys.stderr)
            raise SystemExit(EXIT_NODATA)
        rows.append(obj)
    return rows


def as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# -------------------------------------------------------------- report model

@dataclass
class Report:
    tasks: int = 0
    tokens_would_be: int = 0
    tokens_injected: int = 0
    episodes_total: int = 0
    episodes_pinned: int = 0
    facts_active: int = 0
    facts_superseded: int = 0
    facts_flagged: int = 0
    skills_total: int = 0
    skill_success_rate: float = 0.0
    stores_present: list[str] = field(default_factory=list)

    @property
    def tokens_saved(self) -> int:
        return max(self.tokens_would_be - self.tokens_injected, 0)

    @property
    def savings_pct(self) -> float:
        if self.tokens_would_be <= 0:
            return 0.0
        return 100.0 * self.tokens_saved / self.tokens_would_be


def build_report(memory_dir: Path) -> Report:
    ledger = read_jsonl(memory_dir / "ledger.jsonl")
    episodes = read_jsonl(memory_dir / "episodes.jsonl")
    facts = read_jsonl(memory_dir / "facts.jsonl")
    skills = read_jsonl(memory_dir / "skills.jsonl")

    report = Report()
    for name, rows in (
        ("ledger", ledger), ("episodes", episodes),
        ("facts", facts), ("skills", skills),
    ):
        if rows:
            report.stores_present.append(name)

    report.tasks = len(ledger)
    report.tokens_would_be = sum(as_int(r.get("context_tokens_would_be")) for r in ledger)
    report.tokens_injected = sum(as_int(r.get("injected_tokens")) for r in ledger)

    report.episodes_total = len(episodes)
    report.episodes_pinned = sum(1 for e in episodes if e.get("pinned"))

    for fact in facts:
        status = str(fact.get("status", "active")).lower()
        if status == "superseded":
            report.facts_superseded += 1
        elif status == "flagged":
            report.facts_flagged += 1
        elif status == "active":
            report.facts_active += 1

    report.skills_total = len(skills)
    if skills:
        rates = [as_float(s.get("success_rate")) for s in skills]
        report.skill_success_rate = sum(rates) / len(rates)

    return report


# ---------------------------------------------------------------- rendering

def render_plain(report: Report, benchmark: bool) -> str:
    if report.tasks == 0:
        head = "No ledger data yet (memory/ledger.jsonl is empty or missing)."
    else:
        head = (
            f"Memory saved {report.tokens_saved:,} tokens "
            f"({report.savings_pct:.1f}%) over {report.tasks} task(s) "
            f"[{report.tokens_injected:,} injected vs "
            f"{report.tokens_would_be:,} naive]."
        )
    lines = [
        head,
        f"Episodes: {report.episodes_total} ({report.episodes_pinned} pinned) | "
        f"Facts: {report.facts_active} active, {report.facts_superseded} superseded, "
        f"{report.facts_flagged} flagged | "
        f"Skills: {report.skills_total} (avg success {report.skill_success_rate:.2f})",
    ]
    if benchmark:
        lines.append("Benchmark (playbook): 26,000 -> 1,800 tokens/query = 90% (Mem0)")
    return "\n".join(lines)


def render_table(report: Report, benchmark: bool) -> str:
    rows = [
        ("Tokens without memory (naive)", f"{report.tokens_would_be:,}"),
        ("Tokens injected (with memory)", f"{report.tokens_injected:,}"),
        ("Tokens saved", f"{report.tokens_saved:,}"),
        ("Savings", f"{report.savings_pct:.1f}%"),
        ("Tasks audited", f"{report.tasks}"),
        ("Episodes stored", f"{report.episodes_total}"),
        ("Episodes pinned", f"{report.episodes_pinned}"),
        ("Facts active", f"{report.facts_active}"),
        ("Facts superseded", f"{report.facts_superseded}"),
        ("Facts flagged", f"{report.facts_flagged}"),
        ("Skills promoted", f"{report.skills_total}"),
        ("Average skill success rate", f"{report.skill_success_rate:.2f}"),
    ]
    out = ["| Metric | Value |", "| --- | --- |"]
    out += [f"| {key} | {value} |" for key, value in rows]
    if benchmark:
        out += ["", "| Playbook benchmark | Value |", "| --- | --- |"]
        out += [f"| {key} | {value} |" for key, value, _src in BENCHMARK]
    return "\n".join(out)


def render_json(report: Report, benchmark: bool) -> str:
    payload: dict[str, Any] = {
        "tokens_would_be": report.tokens_would_be,
        "tokens_injected": report.tokens_injected,
        "tokens_saved": report.tokens_saved,
        "savings_pct": round(report.savings_pct, 2),
        "tasks": report.tasks,
        "episodes": {"total": report.episodes_total, "pinned": report.episodes_pinned},
        "facts": {
            "active": report.facts_active,
            "superseded": report.facts_superseded,
            "flagged": report.facts_flagged,
        },
        "skills": {
            "total": report.skills_total,
            "avg_success_rate": round(report.skill_success_rate, 3),
        },
        "stores_present": report.stores_present,
    }
    if benchmark:
        payload["benchmark_source"] = "Mem0 / Snowflake via the 5-Layer Playbook"
    return json.dumps(payload, indent=2, sort_keys=True)


RENDERERS = {"plain": render_plain, "table": render_table, "json": render_json}


# --------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="savings_check",
        description="Deterministic memory ROI audit. No LLM calls.",
    )
    parser.add_argument(
        "--memory-dir", default="memory", type=Path,
        help="Directory holding %s (default: ./memory)" % ", ".join(STORE_FILES),
    )
    parser.add_argument(
        "--format", choices=tuple(RENDERERS), default="plain",
        help="Output format (default: plain)",
    )
    parser.add_argument(
        "--benchmark", action="store_true",
        help="Append the playbook's reference numbers",
    )
    parser.add_argument(
        "--fail-under", type=float, default=None, metavar="PCT",
        help="Exit 1 when savings are below PCT (opt-in CI gate)",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    report = build_report(args.memory_dir)
    print(RENDERERS[args.format](report, args.benchmark))

    if not report.stores_present:
        print(
            f"hint: no memory stores found under {args.memory_dir} - "
            "create them with the memory-orchestration skill",
            file=sys.stderr,
        )
        return EXIT_NODATA

    if args.fail_under is not None and report.savings_pct < args.fail_under:
        print(
            f"FAIL: savings {report.savings_pct:.1f}% "
            f"< required {args.fail_under:.1f}%",
            file=sys.stderr,
        )
        return EXIT_BELOW

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
