#!/usr/bin/env python3
"""Render Markdown and HTML MBTI reports from structured analysis results."""

from __future__ import annotations

import argparse
import html
from pathlib import Path
from string import Template
from typing import Dict, List

from mbti_common import (
    AXIS_SIDES,
    TYPE_FUNCTIONS,
    family_for_type,
    family_label,
    iso_now,
    load_json,
    resolve_path,
    type_label,
)


DEBUG_AXIS_SUPPORT = {
    "E": "Repeated outward processing, collaborative framing, and discussion-driven momentum.",
    "I": "Repeated inward processing, reflective pacing, and self-contained consolidation before expression.",
    "S": "Repeated attention to concrete execution, practical details, and proven anchors.",
    "N": "Repeated movement toward frameworks, patterns, abstraction, and future possibilities.",
    "T": "Repeated reliance on logic checks, contradiction spotting, and tradeoff language.",
    "F": "Repeated reliance on values, meaning, interpersonal impact, and relational interpretation.",
    "J": "Repeated push toward closure, explicit next steps, and external structure.",
    "P": "Repeated preference for optionality, exploration, iterative narrowing, and flexible pacing.",
}

DEBUG_AXIS_COUNTER = {
    "E": "There are still moments of solitary or private processing before speaking.",
    "I": "There are still moments of collaborative energy when shared problem-solving matters.",
    "S": "There are still moments of abstraction and long-range framing.",
    "N": "There are still moments of detail anchoring when execution demands it.",
    "T": "There are still moments where meaning and human consequences shape the call.",
    "F": "There are still moments where logic and impersonal structure take priority.",
    "J": "There are still moments where optionality is kept open to learn before committing.",
    "P": "There are still moments where closure and explicit sequencing are used to ship.",
}

DEBUG_BEHAVIOR_TEMPLATES = {
    "I": {
        "behavior_tag": "reflective-solitude",
        "summary": "The user often forms a view privately before moving into discussion.",
        "excerpt": "让我先自己想一会，把逻辑链顺一下，再给结论。",
        "function": "Ti",
    },
    "E": {
        "behavior_tag": "collaborative-energy",
        "summary": "The user often sharpens ideas through live discussion and visible iteration.",
        "excerpt": "我们先把几个方向抛出来，一边聊一边收敛。",
        "function": "Ne",
    },
    "S": {
        "behavior_tag": "specific-execution",
        "summary": "The user repeatedly grounds discussion in concrete steps, constraints, and implementation details.",
        "excerpt": "别先讲抽象结论，先把具体步骤、依赖和边界列出来。",
        "function": "Si",
    },
    "N": {
        "behavior_tag": "abstract-patterning",
        "summary": "The user repeatedly prefers frameworks, deeper structure, and pattern-level framing.",
        "excerpt": "我更想先搭框架，看模式和演化方向，再回到实现。",
        "function": "Ni",
    },
    "T": {
        "behavior_tag": "logic-optimization",
        "summary": "The user repeatedly evaluates options through coherence, logic, and system efficiency.",
        "excerpt": "这个方案逻辑上说不通，收益和代价也不成比例。",
        "function": "Te",
    },
    "F": {
        "behavior_tag": "values-and-meaning",
        "summary": "The user repeatedly checks whether a decision preserves meaning and human impact.",
        "excerpt": "如果这个做法会伤到人，哪怕效率高也不一定值得。",
        "function": "Fi",
    },
    "J": {
        "behavior_tag": "closure-and-plan",
        "summary": "The user often pushes for closure, sequence, and a concrete next-step path.",
        "excerpt": "先把结论敲定，再把行动项和截止时间排出来。",
        "function": "Te",
    },
    "P": {
        "behavior_tag": "exploration-drive",
        "summary": "The user often keeps multiple live options until more evidence shows up.",
        "excerpt": "先别太早定死，我想同时开几个方向边试边收敛。",
        "function": "Ne",
    },
}

DEBUG_FAMILY_STRENGTHS = {
    "nt": [
        ("Conceptual leverage", "The report surface emphasizes abstraction, model-building, and compressing complexity into clearer structures."),
        ("System pressure testing", "The narrative repeatedly rewards contradiction spotting and structural quality over smooth but weak reasoning."),
        ("Strategic range", "The page copy assumes a reader who naturally scans for direction, leverage, and second-order effects."),
    ],
    "nf": [
        ("Meaning sensitivity", "The report surface emphasizes interpretation, coherence of values, and what a direction means rather than only what it achieves."),
        ("Patterned empathy", "The narrative gives room for people-impact, motives, and alignment instead of flattening everything into efficiency."),
        ("Integrative framing", "The page copy assumes a reader who wants a whole-picture synthesis rather than isolated tactical fragments."),
    ],
    "st": [
        ("Operational realism", "The report surface emphasizes grounded action, direct constraints, and what can be executed without romanticizing complexity."),
        ("Concrete judgment", "The narrative gives more weight to evidence that reflects practical steps, detail fidelity, and reliability."),
        ("Steady delivery", "The page copy assumes a reader who values clarity, sequence, and observable results."),
    ],
    "sf": [
        ("Practical care", "The report surface emphasizes useful support, steadiness, and concrete forms of responsiveness."),
        ("Relational continuity", "The narrative gives room for harmony, impact on others, and preserving workable trust."),
        ("Grounded warmth", "The page copy assumes a reader who stays close to what is humanly immediate and actionable."),
    ],
}

DEBUG_FAMILY_BLINDSPOTS = {
    "nt": [
        ("Underweighting social texture", "A highly structural reading can miss quieter emotional constraints that still shape whether a plan will hold."),
        ("Premature abstraction", "The cleanest model can arrive before the real-world edges have been fully exposed."),
    ],
    "nf": [
        ("Overprotecting alignment", "A strong concern for meaning and resonance can delay necessary friction or sharper pruning."),
        ("Interpreting before verifying", "Deep motive-reading can outrun the concrete evidence if not checked against specifics."),
    ],
    "st": [
        ("Local optimization", "A strong practical lens can overfit to current constraints and miss strategic or symbolic shifts."),
        ("Underplaying possibility", "Speed and clarity in execution can narrow the set of options too early."),
    ],
    "sf": [
        ("Carrying too much relational load", "A steady support style can absorb tension that would be healthier to surface directly."),
        ("Deferring hard edges", "Practical care can sometimes soften calls that need firmer boundaries."),
    ],
}


def card_html(title: str, body: str, quote: str | None = None, source_ref: str | None = None) -> str:
    parts = [f'<article class="stack-item"><h3>{html.escape(title)}</h3><p>{html.escape(body)}</p>']
    if quote:
        parts.append(f'<p class="quote">{html.escape(quote)}</p>')
    if source_ref:
        parts.append(f'<p class="source-ref">{html.escape(source_ref)}</p>')
    parts.append("</article>")
    return "".join(parts)


def metric_card(axis_result: Dict) -> str:
    selected = axis_result["selected"]
    pct = axis_result["left_pct"] if selected == axis_result["left"] else axis_result["right_pct"]
    support = "; ".join(axis_result["support_summary"]) if axis_result["support_summary"] else "No clear support extracted."
    counter = "; ".join(axis_result["counter_summary"]) if axis_result["counter_summary"] else "No strong opposing pattern captured."
    return (
        '<article class="metric-card">'
        f"<h3>{html.escape(axis_result['axis'])}</h3>"
        f'<p class="metric-meta">Selected: {html.escape(selected)} · {html.escape(axis_result["confidence"])}</p>'
        f'<div class="meter"><span style="width:{pct}%"></span></div>'
        f'<div class="side-pair"><span>{html.escape(axis_result["left"])} {axis_result["left_pct"]}%</span>'
        f'<span>{html.escape(axis_result["right"])} {axis_result["right_pct"]}%</span></div>'
        f"<p>{html.escape(support)}</p>"
        f'<p class="source-ref">{html.escape(counter)}</p>'
        "</article>"
    )


def enhance_badge_svg(badge_path: Path, type_code: str) -> str:
    svg = badge_path.read_text(encoding="utf-8")
    insert = (
        '<text x="160" y="182" text-anchor="middle" '
        'font-family="Georgia, serif" font-size="56" font-weight="700" fill="#111827">'
        f"{html.escape(type_code)}"
        "</text>"
    )
    return svg.replace("</svg>", insert + "</svg>")


def evidence_lookup(evidence_pool: List[Dict]) -> Dict[str, Dict]:
    return {item["evidence_id"]: item for item in evidence_pool}


def source_ref_text(source_ref: Dict) -> str:
    primary = source_ref["primary"]
    return f'{primary["source_type"]} · {primary["location"]}'


def flip_type_letter(type_code: str, index: int) -> str:
    pairs = {"E": "I", "I": "E", "S": "N", "N": "S", "T": "F", "F": "T", "J": "P", "P": "J"}
    letters = list(type_code)
    letters[index] = pairs[letters[index]]
    return "".join(letters)


def build_debug_dimension_results(type_code: str) -> Dict[str, Dict]:
    selected_strengths = [76, 72, 74, 64]
    confidence_levels = ["high", "high", "high", "medium"]
    results: Dict[str, Dict] = {}
    for index, ((axis, left, right), pct, confidence) in enumerate(zip(AXIS_SIDES, selected_strengths, confidence_levels)):
        selected = type_code[index]
        if selected == left:
            left_pct = pct
            right_pct = 100 - pct
        else:
            right_pct = pct
            left_pct = 100 - pct
        results[axis] = {
            "axis": axis,
            "left": left,
            "right": right,
            "selected": selected,
            "left_pct": left_pct,
            "right_pct": right_pct,
            "margin": round(abs(left_pct - right_pct) / 100, 3),
            "confidence": confidence,
            "support_summary": [DEBUG_AXIS_SUPPORT[selected]],
            "counter_summary": [DEBUG_AXIS_COUNTER[selected]],
        }
    return results


def build_debug_evidence_pool(type_code: str) -> Dict:
    evidence_items = []
    for index, letter in enumerate(type_code, start=1):
        template = DEBUG_BEHAVIOR_TEMPLATES[letter]
        evidence_items.append(
            {
                "evidence_id": f"debug-{index}",
                "summary": template["summary"],
                "excerpt": template["excerpt"],
                "source_ref": {
                    "primary": {
                        "source_type": "debug-preview",
                        "location": f"fixture:{index}",
                    },
                    "alternatives": [],
                },
                "behavior_tag": template["behavior_tag"],
                "dimension_hints": [{"axis": AXIS_SIDES[index - 1][0], "side": letter}],
                "function_hints": [{"function": template["function"], "weight": 1.0}],
                "strength": "strong" if index <= 3 else "moderate",
                "confidence": "high" if index <= 3 else "medium",
                "independence_score": 0.95 if index <= 2 else 0.82,
                "is_counterevidence": False,
                "is_pseudosignal": False,
                "notes": "Bundled fixture used for report-layout preview.",
            }
        )

    evidence_items.append(
        {
            "evidence_id": "debug-counter-1",
            "summary": "The user still shows some outward collaboration when alignment or speed matters.",
            "excerpt": "这个问题我们还是一起过一遍，边聊边发现盲点会更快。",
            "source_ref": {
                "primary": {
                    "source_type": "debug-preview",
                    "location": "fixture:counter-1",
                },
                "alternatives": [],
            },
            "behavior_tag": "counterevidence-collaboration",
            "dimension_hints": [{"axis": "E/I", "side": flip_type_letter(type_code, 0)[0]}],
            "function_hints": [{"function": "Fe", "weight": 0.6}],
            "strength": "weak",
            "confidence": "medium",
            "independence_score": 0.66,
            "is_counterevidence": True,
            "is_pseudosignal": False,
            "notes": "Counter-pattern included so the preview shows non-one-sided evidence.",
        }
    )

    evidence_items.append(
        {
            "evidence_id": "debug-counter-2",
            "summary": "The user still knows how to force closure when delivery pressure gets real.",
            "excerpt": "别再扩了，今天先定一个版本发出去，后面再迭代。",
            "source_ref": {
                "primary": {
                    "source_type": "debug-preview",
                    "location": "fixture:counter-2",
                },
                "alternatives": [],
            },
            "behavior_tag": "counterevidence-closure",
            "dimension_hints": [{"axis": "J/P", "side": flip_type_letter(type_code, 3)[3]}],
            "function_hints": [{"function": "Te", "weight": 0.6}],
            "strength": "weak",
            "confidence": "medium",
            "independence_score": 0.64,
            "is_counterevidence": True,
            "is_pseudosignal": False,
            "notes": "Counter-pattern included so the preview exercises the adjacent-type section.",
        }
    )

    return {
        "generated_at": iso_now(),
        "mode": "debug-preview",
        "evidence_pool": evidence_items,
    }


def build_debug_analysis(type_code: str) -> Dict:
    family_key = family_for_type(type_code)
    stack = " -> ".join(TYPE_FUNCTIONS[type_code])
    dimension_results = build_debug_dimension_results(type_code)
    adjacent_one = flip_type_letter(type_code, 3)
    adjacent_two = flip_type_letter(type_code, 0)

    strengths = [{"title": title, "body": body} for title, body in DEBUG_FAMILY_STRENGTHS[family_key]]
    blindspots = [{"title": title, "body": body} for title, body in DEBUG_FAMILY_BLINDSPOTS[family_key]]

    pressure_patterns = [
        {
            "title": "Pressure response",
            "body": "This preview intentionally shows a type that can become narrower and sharper under load, especially when weak assumptions need to be cut quickly.",
        },
        {
            "title": "Decision style",
            "body": "The fixture emphasizes a reader who wants strong reasoning, visible tradeoffs, and a clear sense of why one interpretation outranks nearby alternatives.",
        },
    ]

    adjacent = [
        {
            "title": f"Why not {adjacent_one}",
            "body": f"The preview keeps {type_code} ahead of {adjacent_one} because the evidence mix favors {type_code[3]} over {adjacent_one[3]} on closure versus optionality, even though both remain plausible neighbors.",
        },
        {
            "title": f"Why not {adjacent_two}",
            "body": f"The preview keeps {type_code} ahead of {adjacent_two} because the evidence mix favors {type_code[0]} over {adjacent_two[0]} on inward versus outward processing, while still leaving some live counterevidence.",
        },
    ]

    uncertainties = [
        {
            "title": "Preview fixture bias",
            "body": "This standalone preview uses bundled mock evidence so layout work can proceed without rerunning extraction and inference.",
        },
        {
            "title": "Real-run calibration",
            "body": "In a real report, confidence, adjacent-type comparison, and evidence wording will tighten around the authorized source set rather than these canned examples.",
        },
    ]

    return {
        "generated_at": iso_now(),
        "mode": "debug-preview",
        "final_type": type_code,
        "type_label": type_label(type_code),
        "family_key": family_key,
        "family_label": family_label(type_code),
        "overall_confidence": {"score": 0.81, "label": "High confidence"},
        "snapshot": "A standalone report-preview fixture that exercises the full visual system without requiring collection, extraction, or inference to run first.",
        "type_narrative": f"This preview renders {type_code} as a best-fit hypothesis with a full report surface. It combines the expected preference pattern with enough counterevidence to exercise the uncertainty and adjacent-type sections instead of producing an unrealistically clean page.",
        "function_validation": {
            "summary": f"The function-stack validation block is also populated in preview mode. For {type_code}, the template shows the stack {stack}, so typography, spacing, and prose density can be tuned without depending on upstream artifacts.",
        },
        "dimension_results": dimension_results,
        "strengths": strengths,
        "blindspots": blindspots,
        "pressure_patterns": pressure_patterns,
        "selected_evidence_ids": ["debug-1", "debug-2", "debug-3", "debug-4"],
        "adjacent_type_comparison": adjacent,
        "uncertainties": uncertainties,
        "followup_questions": [],
    }


def render_markdown(analysis: Dict, evidence_pool: Dict, quote_mode: str) -> str:
    lookup = evidence_lookup(evidence_pool["evidence_pool"])
    lines = [
        f"# MBTI Report: {analysis['final_type']}",
        "",
        f"- Label: {analysis['type_label']}",
        f"- Confidence: {analysis['overall_confidence']['label']}",
        f"- Family: {analysis['family_label']}",
        "",
        "## Snapshot",
        analysis["snapshot"],
        "",
        "## Preference Profile",
    ]
    for axis, result in analysis["dimension_results"].items():
        lines.extend(
            [
                f"### {axis}",
                f"- Selected: {result['selected']} ({result['confidence']})",
                f"- Support: {'; '.join(result['support_summary']) or 'None'}",
                f"- Counterevidence: {'; '.join(result['counter_summary']) or 'None'}",
                "",
            ]
        )

    lines.extend(["## Evidence Chain"])
    for evidence_id in analysis["selected_evidence_ids"]:
        item = lookup[evidence_id]
        lines.append(f"- {item['summary']} [{source_ref_text(item['source_ref'])}]")
        if quote_mode == "summary":
            lines.append(f"  Quote: {item['excerpt']}")
    lines.extend(["", "## Why Not The Adjacent Type"])
    for candidate in analysis["adjacent_type_comparison"]:
        lines.append(f"- {candidate['title']}: {candidate['body']}")
    lines.extend(["", "## Uncertainty"])
    for item in analysis["uncertainties"]:
        lines.append(f"- {item['title']}: {item['body']}")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_html(analysis: Dict, evidence_pool: Dict, quote_mode: str, asset_dir: Path) -> str:
    template = Template((asset_dir / "report-template.html").read_text(encoding="utf-8"))
    embedded_css = (asset_dir / "report.css").read_text(encoding="utf-8")
    badge_svg = enhance_badge_svg(asset_dir / "type-badges" / f"{analysis['family_key']}.svg", analysis["final_type"])
    lookup = evidence_lookup(evidence_pool["evidence_pool"])

    dimension_cards = "\n".join(metric_card(result) for result in analysis["dimension_results"].values())
    strengths = "\n".join(card_html(item["title"], item["body"]) for item in analysis["strengths"])
    blindspots = "\n".join(card_html(item["title"], item["body"]) for item in analysis["blindspots"])
    pressure = "\n".join(card_html(item["title"], item["body"]) for item in analysis["pressure_patterns"])
    adjacent = "\n".join(card_html(item["title"], item["body"]) for item in analysis["adjacent_type_comparison"])
    uncertainty = "\n".join(card_html(item["title"], item["body"]) for item in analysis["uncertainties"])

    evidence_cards = []
    for evidence_id in analysis["selected_evidence_ids"]:
        item = lookup[evidence_id]
        quote = item["excerpt"] if quote_mode == "summary" else None
        evidence_cards.append(
            card_html(
                item["behavior_tag"].replace("-", " ").title(),
                item["summary"],
                quote=quote,
                source_ref=source_ref_text(item["source_ref"]),
            )
        )

    return template.substitute(
        page_title=f"MBTI Report · {analysis['final_type']}",
        embedded_css=embedded_css,
        badge_svg=badge_svg,
        family_key=analysis["family_key"],
        family_label=analysis["family_label"],
        type_code=analysis["final_type"],
        type_label=analysis["type_label"],
        confidence_label=analysis["overall_confidence"]["label"],
        snapshot=html.escape(analysis["snapshot"]),
        dimension_cards=dimension_cards,
        type_narrative=f"<p>{html.escape(analysis['type_narrative'])}</p>",
        function_validation=f"<p>{html.escape(analysis['function_validation']['summary'])}</p>",
        strength_cards=strengths,
        blindspot_cards=blindspots,
        pressure_cards=pressure,
        evidence_cards="\n".join(evidence_cards),
        adjacent_cards=adjacent,
        uncertainty_cards=uncertainty,
        footer_note="Best-fit hypothesis generated from authorized evidence. This is a personality preference model, not a clinical assessment.",
    )


def open_html_report(html_path: Path) -> None:
    """Open the HTML report in the default browser."""
    import subprocess
    import sys

    html_path = html_path.resolve()
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(html_path)])
    elif sys.platform.startswith("linux"):
        subprocess.Popen(["xdg-open", str(html_path)])
    elif sys.platform == "win32":
        subprocess.Popen(["cmd", "/c", "start", "", str(html_path)])
    else:
        print(f"Cannot auto-open on {sys.platform}; open manually: {html_path}")


def write_reports(analysis: Dict, evidence_pool: Dict, output_dir: Path, quote_mode: str = "summary", auto_open: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    asset_dir = Path(__file__).resolve().parent.parent / "assets"
    markdown = render_markdown(analysis, evidence_pool, quote_mode)
    html_doc = render_html(analysis, evidence_pool, quote_mode, asset_dir)
    html_path = output_dir / "report.html"
    (output_dir / "report.md").write_text(markdown, encoding="utf-8")
    html_path.write_text(html_doc, encoding="utf-8")
    if auto_open:
        open_html_report(html_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render MBTI HTML and Markdown reports.")
    parser.add_argument("--analysis", help="Path to analysis_result.json")
    parser.add_argument("--evidence-pool", help="Path to evidence_pool.json")
    parser.add_argument("--output-dir", required=True, help="Where to write report.md and report.html")
    parser.add_argument("--quote-mode", choices=["summary", "none"], default="summary", help="How much to quote from evidence.")
    parser.add_argument("--debug-preview", action="store_true", help="Render a bundled preview fixture without depending on analysis_result.json or evidence_pool.json.")
    parser.add_argument("--debug-type", choices=sorted(TYPE_FUNCTIONS.keys()), default="INTP", help="Type code to use when --debug-preview is enabled.")
    parser.add_argument("--open", action="store_true", help="Open the HTML report in the default browser after rendering.")
    args = parser.parse_args()

    if args.debug_preview:
        if args.analysis or args.evidence_pool:
            parser.error("--debug-preview cannot be combined with --analysis or --evidence-pool.")
        analysis = build_debug_analysis(args.debug_type)
        evidence_pool = build_debug_evidence_pool(args.debug_type)
    else:
        if not args.analysis or not args.evidence_pool:
            parser.error("--analysis and --evidence-pool are required unless --debug-preview is used.")
        analysis = load_json(resolve_path(args.analysis))
        evidence_pool = load_json(resolve_path(args.evidence_pool))

    output_dir = resolve_path(args.output_dir)
    auto_open = getattr(args, "open", False)
    write_reports(analysis, evidence_pool, output_dir, args.quote_mode, auto_open=auto_open)


if __name__ == "__main__":
    main()
