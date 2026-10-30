"""Check that every drafted record's explanation is supported by the cached article text.

build_dataset.py already proves the *verdict* is real by requiring a verbatim quote. This
script checks the rest of the record: the concrete details in `claim`, `explanation` and
`why_misleading` (numbers, proper nouns, place names, quoted phrases) must also appear in
the article text that was actually fetched. Anything that does not is flagged for manual
review rather than silently shipped.

Caveat printed with every run: cached text keeps the head and tail of long articles and
drops the middle, so a legitimately-sourced detail can be missing. The output is a ranked
review list, not an automatic verdict.

Reads only research/batches/batch_*.json, research/cache/batch_*.json and the OS-temp
article cache. Writes nothing.

Usage:
    python Frontend/research/check_fidelity.py [--min-coverage 0.7] [--cache PATH ...]
"""

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BATCH_DIR = HERE / "batches"
CACHE_BATCH_DIR = HERE / "cache"

QUOTE_FOLD = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "..."})

# Words that look like proper nouns but carry no factual weight.
GENERIC = set(
    """alt news boom factly newschecker vishvas quint webqoof india today factcheck org
    facebook instagram whatsapp youtube twitter google x ai the a an of in on at to for
    with from by is are was were be been being it its this that these those there here
    news post posts video videos image images photo photos clip clips claim claims
    report reports reported said says sharing shared viral found search searched reverse
    keyframe keyframes team fact check checked according per also more most other
    january february march april may june july august september october november december
    monday tuesday wednesday thursday friday saturday sunday""".split()
)


def norm(text):
    return re.sub(r"\s+", " ", (text or "").translate(QUOTE_FOLD)).strip().lower()


def default_caches():
    root = Path(tempfile.gettempdir())
    found = sorted(root.glob("fnd_*/articles.jsonl"))
    return found or [root / "fnd_research" / "articles.jsonl"]


def load_caches(paths):
    cache = {}
    for path in paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = row["url"].rstrip("/")
                previous = cache.get(key)
                if previous is None or row.get("text_chars", 0) > previous.get("text_chars", 0):
                    cache[key] = row
    return cache


def details(text):
    """Pull the checkable specifics out of a written field."""
    found = set()
    # numbers, including ranges and units
    for match in re.findall(r"\b\d[\d,\.]*\s?(?:%|percent|lakh|crore|million|billion|tonnes?|kg|km|ft|feet)?\b", text or "", re.I):
        token = match.strip().lower()
        if token and not token.isdigit() or len(token) > 1:
            found.add(token.rstrip("."))
    # capitalized multiword proper nouns and single capitalized words mid-sentence
    for match in re.findall(r"\b([A-Z][A-Za-z\u00c0-\u024f']+(?:\s+[A-Z][A-Za-z\u00c0-\u024f']+){0,3})\b", text or ""):
        phrase = match.strip()
        if phrase.lower() in GENERIC:
            continue
        if len(phrase) < 3:
            continue
        found.add(phrase)
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-coverage", type=float, default=0.7)
    parser.add_argument("--cache", action="append", default=None)
    args = parser.parse_args()

    cache = load_caches([Path(p) for p in args.cache] if args.cache else default_caches())
    if not cache:
        print("no article cache found -- run fetch_articles.py first", file=sys.stderr)
        return 1

    rows = []
    for path in sorted(BATCH_DIR.glob("batch_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("records", []):
            record = item.get("record", {})
            url = str((item.get("provenance") or {}).get("url", "")).rstrip("/")
            article = cache.get(url)
            if article is None:
                rows.append((0.0, path.name, record.get("id", "?"), url, ["<no cached article>"], []))
                continue
            haystack = norm(article.get("text", "")) + " " + norm(article.get("title", ""))
            written = " ".join(
                [
                    record.get("claim", ""),
                    record.get("explanation", ""),
                    record.get("why_misleading", ""),
                    record.get("geo_scope", ""),
                ]
            )
            found = details(written)
            missing, present = [], []
            for token in sorted(found):
                probe = norm(token)
                if not probe or len(probe) < 3:
                    continue
                # numbers are checked exactly; names also pass on their longest word
                if probe in haystack:
                    present.append(token)
                    continue
                words = [w for w in re.findall(r"[a-z\u00c0-\u024f']{4,}", probe) if w not in GENERIC]
                if words and all(w in haystack for w in words):
                    present.append(token)
                    continue
                missing.append(token)
            checked = len(present) + len(missing)
            coverage = (len(present) / checked) if checked else 1.0
            rows.append((coverage, path.name, record.get("id", "?"), url, missing, present))

    rows.sort(key=lambda r: r[0])
    flagged = [r for r in rows if r[0] < args.min_coverage]

    print(f"records checked          : {len(rows)}")
    print(f"coverage >= {args.min_coverage:.0%}          : {len(rows) - len(flagged)}")
    print(f"below threshold          : {len(flagged)}")
    print(f"mean coverage            : {sum(r[0] for r in rows) / max(1, len(rows)):.1%}")
    print(
        "\nNOTE: cached text drops the middle of long articles, so a missing detail is a "
        "review prompt,\n      not proof of fabrication.\n"
    )

    for coverage, batch, rid, url, missing, _ in flagged:
        print(f"{coverage:5.0%}  [{batch}] {rid}")
        print(f"        missing: {', '.join(missing[:12])}")
        print(f"        {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
