# MBTI Skill

An [OpenClaw](https://openclaw.ai/) skill that infers your MBTI personality type from your authorized conversation history, memory, and workspace notes — no questionnaire required.

## How It Works

```
Discover → Ingest → Evidence Pool → Inference → Report
```

1. **Discover** — scans your workspace and OpenClaw home for candidate data sources
2. **Authorize** — shows you what's available and asks which sources to use
3. **Ingest** — extracts structured records from authorized sources only
4. **Evidence** — builds a scored, traceable evidence pool (removes noise, flags pseudo-signals)
5. **Infer** — runs MBTI inference against the evidence pool, not raw history
6. **Report** — renders `report.html` + `report.md` with type, confidence, and evidence

## Install

One-command install via [ClawHub](https://clawhub.ai):

```
openclaw skills install mbti-analyzer
```

Or tell your OpenClaw agent:

```
Install this skill and analyze my MBTI: openclaw skills install mbti-analyzer
```

From source:

```bash
git clone https://github.com/kingOfSoySauce/mbti-skill.git
openclaw skills install ./mbti-skill
```

Local development:

```bash
ln -s "$(pwd)" "$CODEX_HOME/skills/mbti"
```

## Usage

Trigger phrases: `MBTI`, `personality analysis`, `type me`, `分析我的 MBTI`

Or run the command:

```
mbti-report
```

### Pipeline (CLI)

```bash
# 1. Discover sources
python3 scripts/discover_sources.py \
  --workspace-root . \
  --openclaw-home ~/.openclaw \
  --output /tmp/mbti-manifest.json

# 2. Ingest authorized sources
python3 scripts/ingest_all_content.py \
  --manifest /tmp/mbti-manifest.json \
  --approved-source-types all \
  --output-dir ./.mbti-reports/run

# 3. Build evidence pool
python3 scripts/build_evidence_pool.py \
  --raw-records ./.mbti-reports/run/raw_records.jsonl \
  --source-summary ./.mbti-reports/run/source_summary.json \
  --output ./.mbti-reports/run/evidence_pool.json

# 4. Infer MBTI
python3 scripts/infer_mbti.py \
  --evidence-pool ./.mbti-reports/run/evidence_pool.json \
  --source-summary ./.mbti-reports/run/source_summary.json \
  --output ./.mbti-reports/run/analysis_result.json

# 5. Render report
python3 scripts/render_report.py \
  --analysis ./.mbti-reports/run/analysis_result.json \
  --evidence-pool ./.mbti-reports/run/evidence_pool.json \
  --output-dir ./.mbti-reports/run
```

Output: `report.html` (primary), `report.md`, `analysis_result.json`, `evidence_pool.json`

## Testing

```bash
# Run all stage smoke tests
python -m pytest tests/test_stage_smoke.py -v

# Single stage
python -m pytest tests/test_stage_smoke.py::StageSmokeTests::test_infer_stage -v

# Prepare a fixture for manual inspection
python3 scripts/prepare_stage_fixture.py --stage infer --output-dir /tmp/mbti-test
```

## Design Principles

- **Authorization first** — never read source content without user confirmation
- **Evidence, not raw history** — MBTI is inferred from a curated evidence pool, not raw chat logs
- **Transparent reasoning** — every scored signal is traceable back to its source
- **Non-clinical** — results are a best-fit hypothesis, not a diagnosis

## References

| Document | Purpose |
|---|---|
| [`SKILL.md`](SKILL.md) | Full execution contract and script reference |
| [`references/analysis_framework.md`](references/analysis_framework.md) | Four-preference + cognitive-function analysis model |
| [`references/evidence_rubric.md`](references/evidence_rubric.md) | Signal strength scoring and pseudo-signal filtering |
| [`references/report_copy_contract.md`](references/report_copy_contract.md) | Copy and tone rules for generated reports |
| [`references/report_structure.md`](references/report_structure.md) | Report section layout |

## License

MIT
