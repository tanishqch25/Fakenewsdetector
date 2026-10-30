"""Split the fetched article cache into review batches.

Reads the article cache written by fetch_articles.py (OS temp directory), keeps
only usable pages (HTTP 200 and >400 chars of extracted text), groups them by
source and writes fixed-size JSON batches under research/cache/ for review.

Each batch file is a list of {url, source, title, published, text} -- exactly
what a reviewer needs, with no network access required.

Re-running skips URLs that are already in an existing batch file, so the split
is stable and resumable.

Usage:
    python Frontend/research/split_batches.py [--size 22]
"""

import argparse
import json
import tempfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "cache"


def default_cache_paths():
    root = Path(tempfile.gettempdir())
    return sorted(root.glob("fnd_*/articles.jsonl")) or [root / "fnd_research" / "articles.jsonl"]


def load_cache(paths):
    """Read every cache file and drop the best record per URL."""
    best = {}
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                previous = best.get(row["url"])
                if previous is None or row.get("text_chars", 0) > previous.get("text_chars", 0):
                    best[row["url"]] = row
    return list(best.values())


def already_batched():
    seen = set()
    if not OUT_DIR.exists():
        return seen
    for path in OUT_DIR.glob("batch_*.json"):
        for row in json.loads(path.read_text(encoding="utf-8")):
            seen.add(row["url"])
    return seen


def next_index():
    if not OUT_DIR.exists():
        return 1
    indices = [int(p.stem.split("_")[1]) for p in OUT_DIR.glob("batch_*.json") if p.stem.split("_")[1].isdigit()]
    return (max(indices) + 1) if indices else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=22, help="articles per batch")
    parser.add_argument("--source", default="", help="only split rows whose source contains this string")
    parser.add_argument(
        "--cache",
        action="append",
        default=None,
        help="articles.jsonl to read; repeatable. Defaults to the temp cache written by fetch_articles.py",
    )
    args = parser.parse_args()

    cache_paths = [Path(p) for p in (args.cache or default_cache_paths())]
    missing = [p for p in cache_paths if not p.exists()]
    if missing:
        raise SystemExit(f"cache file(s) not found: {', '.join(str(p) for p in missing)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done = already_batched()

    by_source = defaultdict(list)
    skipped = {"http": 0, "short": 0, "dup": 0}
    for row in load_cache(cache_paths):
        if row["url"] in done:
            skipped["dup"] += 1
            continue
        if row.get("http") != 200:
            skipped["http"] += 1
            continue
        if row.get("text_chars", 0) <= 400:
            skipped["short"] += 1
            continue
        if args.source and args.source.lower() not in row["source"].lower():
            continue
        by_source[row["source"]].append(
            {
                "url": row["url"],
                "source": row["source"],
                "title": row.get("title") or row.get("og_title") or row.get("feed_title") or "",
                "feed_title": row.get("feed_title", ""),
                "published": (row.get("published") or "")[:10],
                "feed_pubdate": row.get("feed_pubdate", ""),
                "text": row.get("text", ""),
            }
        )

    index = next_index()
    first_index = index
    written = 0
    for source in sorted(by_source, key=lambda key: -len(by_source[key])):
        rows = by_source[source]
        for start in range(0, len(rows), args.size):
            chunk = rows[start : start + args.size]
            path = OUT_DIR / f"batch_{index:02d}.json"
            path.write_text(json.dumps(chunk, indent=1, ensure_ascii=False), encoding="utf-8")
            print(
                f"{path.name}  {len(chunk):3d} articles  [{source}]  "
                f"{chunk[0]['published'] or '?'} .. {chunk[-1]['published'] or '?'}"
            )
            written += len(chunk)
            index += 1

    print(f"\nwrote {written} articles into {index - first_index} new batch file(s) under {OUT_DIR}")
    print(f"already batched={skipped['dup']} skipped_non200={skipped['http']} skipped_short_text={skipped['short']}")


if __name__ == "__main__":
    main()
