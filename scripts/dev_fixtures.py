#!/usr/bin/env python3
"""Synthetic fixtures for isolated MBTI stage testing."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

from build_evidence_pool import build_pool
from discover_sources import discover
from infer_mbti import infer_payload
from ingest_all_content import INGESTORS, build_summary
from mbti_common import ensure_dir, iso_now, resolve_path, write_json, write_jsonl


STAGES = ("discover", "ingest", "evidence", "infer", "render", "followup", "all")


def fixture_paths(output_dir: Path) -> Dict[str, Path]:
    root = resolve_path(output_dir)
    fixture_root = root / "fixture"
    workspace_root = fixture_root / "workspace"
    openclaw_home = fixture_root / "openclaw"
    return {
        "output_dir": root,
        "fixture_root": fixture_root,
        "workspace_root": workspace_root,
        "openclaw_home": openclaw_home,
        "fixture_paths": root / "fixture_paths.json",
        "source_manifest": root / "source_manifest.json",
        "raw_records": root / "raw_records.jsonl",
        "source_summary": root / "source_summary.json",
        "evidence_pool": root / "evidence_pool.json",
        "analysis_result": root / "analysis_result.json",
        "answers_file": root / "answers_input.json",
    }


def _write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _reset_sqlite(path: Path) -> sqlite3.Connection:
    ensure_dir(path.parent)
    if path.exists():
        path.unlink()
    return sqlite3.connect(path)


def create_source_fixture(output_dir: Path) -> Dict[str, Path]:
    paths = fixture_paths(output_dir)
    workspace_root = paths["workspace_root"]
    openclaw_home = paths["openclaw_home"]

    _write_text(
        workspace_root / "MEMORY.md",
        """
        # Long Memory

        I usually need time to think and prefer a clear framework before I speak.
        I check logic, evidence, and trade-off quality before I commit.
        """,
    )
    _write_text(
        workspace_root / "memory" / "2026-04-03.md",
        """
        I usually keep options open and try a few directions while I explore.
        I often connect distant ideas and look for the underlying pattern first.
        """,
    )

    session_rows = [
        {
            "type": "message",
            "id": "m1",
            "timestamp": "2026-04-03T09:15:00",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Let's think it through first, build a framework, and check whether "
                            "the plan is internally consistent."
                        ),
                    }
                ],
            },
        },
        {
            "type": "message",
            "id": "m2",
            "timestamp": "2026-04-03T09:16:00",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Acknowledged."}],
            },
        },
    ]
    write_jsonl(openclaw_home / "agents" / "demo-agent" / "sessions" / "fixture-session.jsonl", session_rows)

    memory_db = _reset_sqlite(openclaw_home / "memory" / "main.sqlite")
    try:
        memory_db.executescript(
            """
            create table files (path text not null);
            create table chunks (
                path text not null,
                start_line integer not null,
                end_line integer not null,
                text text not null,
                updated_at text
            );
            """
        )
        memory_db.execute("insert into files(path) values (?)", ("memory/2026-04-03.md",))
        memory_db.execute(
            """
            insert into chunks(path, start_line, end_line, text, updated_at)
            values (?, ?, ?, ?, ?)
            """,
            (
                "memory/2026-04-03.md",
                1,
                3,
                "I tend to connect distant ideas, keep options open, and adapt as we go.",
                "2026-04-03T10:00:00",
            ),
        )
        memory_db.commit()
    finally:
        memory_db.close()

    task_db = _reset_sqlite(openclaw_home / "tasks" / "runs.sqlite")
    try:
        task_db.executescript(
            """
            create table task_runs (
                task_id text not null,
                runtime text,
                label text,
                task text,
                status text,
                progress_summary text,
                terminal_summary text,
                created_at text
            );
            """
        )
        task_db.execute(
            """
            insert into task_runs(
                task_id, runtime, label, task, status, progress_summary, terminal_summary, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "fixture-task-1",
                "python3",
                "Nightly backup",
                "Archive logs",
                "success",
                "completed",
                "backup finished",
                "2026-04-03T11:00:00",
            ),
        )
        task_db.commit()
    finally:
        task_db.close()

    cron_row = {
        "timestamp": "2026-04-03T12:00:00",
        "job": "heartbeat",
        "status": "ok",
        "note": "no action required",
    }
    write_jsonl(openclaw_home / "cron" / "runs" / "fixture-cron.jsonl", [cron_row])

    write_json(paths["fixture_paths"], serialize_paths(paths))
    return paths


def serialize_paths(paths: Dict[str, Path]) -> Dict[str, str]:
    return {key: str(value) for key, value in paths.items()}


def build_ingest_fixture(output_dir: Path) -> Tuple[Dict[str, Path], Dict, List[Dict], Dict]:
    paths = create_source_fixture(output_dir)
    manifest = discover(paths["workspace_root"], paths["openclaw_home"])
    approved = [candidate["source_type"] for candidate in manifest["candidates"] if candidate["available"]]

    records: List[Dict] = []
    for source_type in approved:
        ingestor = INGESTORS[source_type]
        target_root = paths["workspace_root"] if source_type.startswith("workspace") else paths["openclaw_home"]
        records.extend(ingestor(target_root))

    summary = build_summary(records, approved, paths["workspace_root"], paths["openclaw_home"])
    write_json(paths["source_manifest"], manifest)
    write_jsonl(paths["raw_records"], records)
    write_json(paths["source_summary"], summary)
    return paths, manifest, records, summary


def build_evidence_fixture(output_dir: Path) -> Tuple[Dict[str, Path], Dict, Dict]:
    paths, _, records, summary = build_ingest_fixture(output_dir)
    evidence_payload = build_pool(records, summary)
    write_json(paths["evidence_pool"], evidence_payload)
    return paths, summary, evidence_payload


def build_infer_fixture(output_dir: Path) -> Tuple[Dict[str, Path], Dict, Dict]:
    paths, summary, evidence_payload = build_evidence_fixture(output_dir)
    analysis_payload = infer_payload(evidence_payload, summary)
    write_json(paths["analysis_result"], analysis_payload)
    return paths, evidence_payload, analysis_payload


def write_answers_fixture(paths: Dict[str, Path]) -> None:
    write_json(
        paths["answers_file"],
        {
            "generated_at": iso_now(),
            "answers": [
                {
                    "axis": "J/P",
                    "answer": "I usually keep options open and adapt as we go before closing.",
                }
            ],
        },
    )


def write_stage_fixture(stage: str, output_dir: Path) -> Dict[str, str]:
    if stage not in STAGES:
        raise ValueError(f"Unknown stage {stage!r}; expected one of {STAGES}.")

    if stage == "discover":
        paths = create_source_fixture(output_dir)
        return serialize_paths(paths)

    if stage == "ingest":
        paths, _, _, _ = build_ingest_fixture(output_dir)
        return serialize_paths(paths)

    if stage == "evidence":
        paths, _, _ = build_evidence_fixture(output_dir)
        return serialize_paths(paths)

    if stage in {"infer", "render"}:
        paths, _, _ = build_infer_fixture(output_dir)
        return serialize_paths(paths)

    if stage in {"followup", "all"}:
        paths, _, _ = build_infer_fixture(output_dir)
        write_answers_fixture(paths)
        return serialize_paths(paths)

    raise AssertionError(f"Unhandled stage {stage!r}.")

