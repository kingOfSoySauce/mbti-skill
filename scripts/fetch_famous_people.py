#!/usr/bin/env python3
"""Fetch MBTI famous people from multiple sources and output structured JSON.

Sources:
  1. stablecharacter.com  — curated list, reliable access
  2. psyctest.cn         — community-voted, large database

Usage:
  python3 fetch_famous_people.py                     # fetch all, output JSON
  python3 fetch_famous_people.py --source stablecharacter
  python3 fetch_famous_people.py --source psyctest
  python3 fetch_famous_people.py --type INTP         # single type
  python3 fetch_famous_people.py --output famous_people.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP",
]


def browser_open(url: str, wait: float = 3.0) -> None:
    subprocess.run(
        ["agent-browser", "open", url],
        capture_output=True, timeout=30,
    )
    time.sleep(wait)


def browser_eval_stdin(js: str, timeout: int = 15) -> str:
    """Eval JS via stdin to avoid shell quoting issues."""
    result = subprocess.run(
        ["agent-browser", "eval", "--stdin"],
        input=js, capture_output=True, text=True, timeout=timeout,
    )
    raw = result.stdout.strip()
    # agent-browser wraps eval output in JSON quotes
    if raw.startswith('"') and raw.endswith('"'):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = raw[1:-1]
    # Remove ANSI codes
    raw = re.sub(r'\x1b\[[0-9;]*m', '', raw)
    return raw


# ---------------------------------------------------------------------------
# Source 1: stablecharacter.com
# ---------------------------------------------------------------------------

SC_BASE = "https://www.stablecharacter.com/personality-database"

# HTML structure per card: <a href="/personality-database/slug">
#   <div><div>
#     <div><h3>NAME</h3><span>type</span></div>
#     <p>DESCRIPTION</p>
#   </div></div>
# </a>
SC_JS = """(function(){
  var out = [];
  document.querySelectorAll('a[href*="/personality-database/"]').forEach(function(a){
    var h = a.getAttribute('href')||'';
    if(h.indexOf('?type=')!==-1) return;
    var h3 = a.querySelector('h3');
    var p = a.querySelector('p');
    var name = h3 ? h3.textContent.trim() : h.split('/').pop().replace(/-/g,' ');
    var desc = p ? p.textContent.trim() : '';
    out.push({name:name, description:desc, detail_url:'https://www.stablecharacter.com'+h});
  });
  return JSON.stringify(out);
})()
"""


def fetch_stablecharacter(types: List[str]) -> Dict[str, List[dict]]:
    data: Dict[str, List[dict]] = {}
    for mbti_type in types:
        print(f"  [stablecharacter] {mbti_type}...", file=sys.stderr)
        browser_open(f"{SC_BASE}?type={mbti_type}", wait=3.0)
        raw = browser_eval_stdin(SC_JS)
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            print(f"    WARN: parse failed: {raw[:200]}", file=sys.stderr)
            items = []
        for item in items:
            item["source"] = "stablecharacter.com"
            item["mbti_type"] = mbti_type
            item["domain"] = _infer_domain(item.get("description", ""))
        data[mbti_type] = items
        print(f"    Got {len(items)}", file=sys.stderr)
    return data


# ---------------------------------------------------------------------------
# Source 2: psyctest.cn
# ---------------------------------------------------------------------------

PC_BASE = "https://m.psyctest.cn/mbti/db/"

PC_CATEGORIES = {
    "名人明星": "Celebrities",
    "历史人物": "Historical Figures",
}

PC_JS = """(function(){
  var results = [];
  var main = document.getElementById('main');
  if (!main) return JSON.stringify([]);
  var lines = main.innerText.split('\\n').map(function(l){return l.trim()}).filter(function(l){return l.length>0});
  var kw = ['Celebrities','Historical','Literati','Scientist','Athlete','Voice',
    'Weblebrity','Chinese','European','Japanese','Korean','Modern',
    'Pre Qin','Qin and Han','Mikuni','Jin/Northern','Sui and Tang',
    'Song and Yuan','Ming','Qing','Republic','Ancient Foreign',
    'Modern Foreign','Anime','Novel','Game','Virtual','Film','Literary','Cartoon'];
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    if (line.length < 2 || line.length > 80) continue;
    var next = (i+1 < lines.length) ? lines[i+1] : '';
    var match = false;
    for (var k = 0; k < kw.length; k++) { if (next.indexOf(kw[k]) !== -1) { match = true; break; } }
    if (match) {
      results.push({name:line, domain:next, description:'', detail_url:''});
      i++;
    }
  }
  return JSON.stringify(results);
})()
"""


def fetch_psyctest(types: List[str]) -> Dict[str, List[dict]]:
    data: Dict[str, List[dict]] = {}
    for mbti_type in types:
        all_people: List[dict] = []
        for cat_cn, cat_en in PC_CATEGORIES.items():
            print(f"  [psyctest] {mbti_type} / {cat_en}...", file=sys.stderr)
            url = f"{PC_BASE}?lang=en&limit=24&mbti_type={mbti_type}&category={cat_cn}"
            browser_open(url, wait=2.5)
            raw = browser_eval_stdin(PC_JS, timeout=15)
            try:
                items = json.loads(raw)
            except json.JSONDecodeError:
                print(f"    WARN: parse failed: {raw[:200]}", file=sys.stderr)
                items = []
            for item in items:
                item["source"] = "psyctest.cn"
                item["mbti_type"] = mbti_type
                item["category"] = cat_en
                if not item.get("domain"):
                    item["domain"] = cat_en
                if not item.get("detail_url"):
                    item["detail_url"] = (
                        f"{PC_BASE}?lang=en&mbti_type={mbti_type}"
                        f"&category={cat_cn}&name={item['name']}"
                    )
            all_people.extend(items)
        data[mbti_type] = all_people
        print(f"    Got {len(all_people)} for {mbti_type}", file=sys.stderr)
    return data


# ---------------------------------------------------------------------------
# Domain inference
# ---------------------------------------------------------------------------

DOMAIN_KEYWORDS = {
    "Tech": ["tech", "software", "ceo", "co-founder", "entrepreneur", "computer",
             "microsoft", "apple", "tesla", "spacex"],
    "Science": ["scientist", "physicist", "mathematician", "biologist", "chemist",
                "inventor", "theory"],
    "Philosophy": ["philosopher", "cultural critic", "thinker", "existential"],
    "Literature": ["author", "novelist", "writer", "poet", "book", "literary"],
    "Music": ["musician", "singer", "rapper", "composer", "pop star", "k-pop",
              "vocalist", "songwriter", "producer", "indie rock"],
    "Film/TV": ["actor", "actress", "director", "filmmaker", "hollywood", "disney",
                "series", "performer"],
    "Sports": ["football", "basketball", "athlete", "soccer", "tennis", "kickboxer",
               "sports", "player"],
    "Politics": ["president", "politician", "minister", "leader", "activist",
                 "political", "russian president"],
    "Psychology": ["psychologist", "psychiatrist", "psychoanalyst"],
    "YouTube/Internet": ["youtube", "youtuber", "content creator", "streamer",
                         "influencer", "online", "minecraft", "commentary", "mukbang"],
    "Art": ["artist", "painter", "sculptor", "avant-garde"],
    "History": ["king", "emperor", "royal", "historical", "ancient"],
}


def _infer_domain(description: str) -> str:
    desc_lower = description.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                return domain
    return "Other"


def merge_data(*sources: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    """Merge multiple source dicts, deduplicating by name (case-insensitive)."""
    merged: Dict[str, List[dict]] = {t: [] for t in TYPES}
    seen: Dict[str, set] = {t: set() for t in TYPES}
    for source in sources:
        for mbti_type, people in source.items():
            for person in people:
                name_key = person["name"].strip().lower()
                if name_key not in seen[mbti_type]:
                    seen[mbti_type].add(name_key)
                    merged[mbti_type].append(person)
    return merged


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch MBTI famous people from online sources.")
    parser.add_argument("--source", choices=["stablecharacter", "psyctest", "all"], default="all",
                        help="Which source to fetch from (default: all).")
    parser.add_argument("--type", choices=TYPES, help="Fetch only one MBTI type.")
    parser.add_argument("--output", default="-", help="Output file path (default: stdout).")
    args = parser.parse_args()

    fetch_types = [args.type] if args.type else TYPES

    sources: List[Dict[str, List[dict]]] = []

    if args.source in ("stablecharacter", "all"):
        print("Fetching stablecharacter.com...", file=sys.stderr)
        sources.append(fetch_stablecharacter(fetch_types))

    if args.source in ("psyctest", "all"):
        print("Fetching psyctest.cn...", file=sys.stderr)
        sources.append(fetch_psyctest(fetch_types))

    if not sources:
        print("No source selected.", file=sys.stderr)
        sys.exit(1)

    final = merge_data(*sources)

    total = sum(len(v) for v in final.values())
    print(f"Total: {total} people across {len(final)} types.", file=sys.stderr)

    output_json = json.dumps(final, ensure_ascii=False, indent=2)

    if args.output == "-":
        print(output_json)
    else:
        Path(args.output).write_text(output_json + "\n", encoding="utf-8")
        print(f"Written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
