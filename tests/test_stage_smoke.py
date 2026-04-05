#!/usr/bin/env python3
"""Smoke tests for running each MBTI stage independently."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class StageSmokeTests(unittest.TestCase):
    maxDiff = None

    def run_script(self, script: str, *args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=(
                f"{script} failed with code {result.returncode}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            ),
        )
        return result

    def prepare(self, stage: str, tempdir: Path) -> dict:
        self.run_script("prepare_stage_fixture.py", "--stage", stage, "--output-dir", str(tempdir))
        return json.loads((tempdir / "fixture_paths.json").read_text(encoding="utf-8"))

    def test_discover_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            tempdir = Path(temp)
            paths = self.prepare("discover", tempdir)
            manifest_path = tempdir / "manifest.json"
            self.run_script(
                "discover_sources.py",
                "--workspace-root",
                paths["workspace_root"],
                "--openclaw-home",
                paths["openclaw_home"],
                "--output",
                str(manifest_path),
            )
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["candidates"]), 6)
            self.assertTrue(all(candidate["available"] for candidate in payload["candidates"]))

    def test_ingest_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            tempdir = Path(temp)
            paths = self.prepare("ingest", tempdir)
            out_dir = tempdir / "ingest-output"
            self.run_script(
                "ingest_all_content.py",
                "--manifest",
                paths["source_manifest"],
                "--approved-source-types",
                "all",
                "--output-dir",
                str(out_dir),
            )
            summary = json.loads((out_dir / "source_summary.json").read_text(encoding="utf-8"))
            self.assertGreater(summary["record_count"], 0)
            self.assertIn("workspace-long-memory", summary["sources"])

    def test_evidence_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            tempdir = Path(temp)
            paths = self.prepare("evidence", tempdir)
            output_path = tempdir / "evidence-output.json"
            self.run_script(
                "build_evidence_pool.py",
                "--raw-records",
                paths["raw_records"],
                "--source-summary",
                paths["source_summary"],
                "--output",
                str(output_path),
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            evidence_items = payload["evidence_pool"]
            self.assertGreater(len(evidence_items), 0)
            self.assertTrue(any(not item["is_pseudosignal"] for item in evidence_items))

    def test_infer_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            tempdir = Path(temp)
            paths = self.prepare("infer", tempdir)
            output_path = tempdir / "analysis-output.json"
            self.run_script(
                "infer_mbti.py",
                "--evidence-pool",
                paths["evidence_pool"],
                "--source-summary",
                paths["source_summary"],
                "--output",
                str(output_path),
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["final_type"]), 4)
            self.assertIn("overall_confidence", payload)

    def test_render_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            tempdir = Path(temp)
            paths = self.prepare("render", tempdir)
            analysis = json.loads(Path(paths["analysis_result"]).read_text(encoding="utf-8"))
            out_dir = tempdir / "render-output"
            self.run_script(
                "render_report.py",
                "--analysis",
                paths["analysis_result"],
                "--evidence-pool",
                paths["evidence_pool"],
                "--output-dir",
                str(out_dir),
            )
            report_html = (out_dir / "report.html").read_text(encoding="utf-8")
            report_md = (out_dir / "report.md").read_text(encoding="utf-8")
            self.assertIn('<html lang="en"', report_html.lower())
            self.assertIn(f"People With {analysis['final_type']}", report_html)
            self.assertNotIn("These examples are for pattern calibration only.", report_html)
            self.assertIn('data-action="download-html"', report_html)
            self.assertIn('href="#profile"', report_html)
            self.assertIn('class="hero-type-code"', report_html)
            self.assertIn("is-hero-compact", report_html)
            self.assertNotIn("<h3>E/I</h3>", report_html)
            self.assertIn("Introversion", report_html)
            self.assertIn("https://www.google.com/search?q=", report_html)
            self.assertNotIn("stablecharacter.com/personality-database", report_html)
            self.assertIn(f"## People With {analysis['final_type']}", report_md)
            self.assertIn("# MBTI Report:", report_md)

    def test_render_stage_auto_language_prefers_zh(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            tempdir = Path(temp)
            paths = self.prepare("render", tempdir)
            analysis = json.loads(Path(paths["analysis_result"]).read_text(encoding="utf-8"))
            evidence = json.loads(Path(paths["evidence_pool"]).read_text(encoding="utf-8"))

            for payload in (analysis, evidence):
                for source in payload["source_summary"]["sources"].values():
                    source["language_mix"] = "zh"
                    source["sample_preview"] = ["我通常会先想清楚框架，再和 agent 一起收敛结论。"]

            analysis_path = tempdir / "analysis-zh.json"
            evidence_path = tempdir / "evidence-zh.json"
            analysis_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
            evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

            out_dir = tempdir / "render-output-zh"
            self.run_script(
                "render_report.py",
                "--analysis",
                str(analysis_path),
                "--evidence-pool",
                str(evidence_path),
                "--output-dir",
                str(out_dir),
            )
            report_html = (out_dir / "report.html").read_text(encoding="utf-8")
            self.assertIn('<html lang="zh-cn"', report_html.lower())
            self.assertIn("偏好画像", report_html)
            self.assertIn(f"{analysis['final_type']} 同型名人", report_html)
            self.assertNotIn("这一组名人只用于帮助你快速校准气质轮廓", report_html)

    def test_followup_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            tempdir = Path(temp)
            paths = self.prepare("followup", tempdir)
            out_dir = tempdir / "followup-output"
            self.run_script(
                "apply_followup_answers.py",
                "--raw-records",
                paths["raw_records"],
                "--source-summary",
                paths["source_summary"],
                "--analysis",
                paths["analysis_result"],
                "--output-dir",
                str(out_dir),
                "--answers-file",
                paths["answers_file"],
            )
            updated = json.loads((out_dir / "followup_answers.json").read_text(encoding="utf-8"))
            self.assertEqual(updated["answers"][0]["axis"], "J/P")
            self.assertTrue((out_dir / "analysis_result.json").exists())


if __name__ == "__main__":
    unittest.main()
