# MBTI Skill Implementation Plan

This file tracks the concrete implementation plan for the `mbti` skill so the work stays anchored while files are added.

## Goal

Build an OpenClaw skill package that:

1. discovers candidate data sources and gets explicit authorization
2. fully ingests only the authorized sources into `raw_records`
3. builds an `evidence_pool` from the extracted data
4. infers MBTI only from the `evidence_pool`
5. renders a stable, polished HTML report plus a short Markdown summary

## Deliverables

- `SKILL.md`
- `references/analysis_framework.md`
- `references/evidence_rubric.md`
- `references/report_copy_contract.md`
- `references/report_structure.md`
- `scripts/mbti_common.py`
- `scripts/discover_sources.py`
- `scripts/ingest_all_content.py`
- `scripts/build_evidence_pool.py`
- `scripts/infer_mbti.py`
- `scripts/render_report.py`
- `assets/report-template.html`
- `assets/report.css`
- `assets/type-badges/*.svg`
- standalone report debug mode in `scripts/render_report.py`

## Implementation Order

- [x] Create implementation tracker
- [x] Write `SKILL.md` with OpenClaw-compatible frontmatter
- [x] Add analysis and reporting reference docs
- [x] Add shared Python helpers
- [x] Implement source discovery
- [x] Implement authorized ingestion
- [x] Implement evidence-pool construction
- [x] Implement MBTI inference
- [x] Implement Markdown/HTML report rendering
- [x] Add visual assets and template
- [x] Add standalone HTML debug-preview mode
- [x] Run local validation and smoke tests

## Non-Goals for v1

- exact 16Personalities visual cloning
- remote dependencies or frontend build steps
- a fully learned classifier model
- publishing to ClawHub in this turn
