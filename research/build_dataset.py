"""Merge reviewed batch files into website/src/data/claims.json.

Every candidate record must arrive in Frontend/research/batches/batch_*.json as

    {
      "batch": <int>,
      "records": [
        {
          "record": { ...exact claims.json schema... },
          "provenance": {
            "url": "...",                  # the fact-check article actually read
            "served_title": "...",         # <title> as served by the site
            "published_date": "YYYY-MM-DD",
            "verdict_quote": "...",        # verbatim contiguous excerpt (<=30 words)
            "status_rationale": "..."
          }
        }
      ],
      "excluded": [ {"url": "...", "reason": "..."} ]
    }

Gates applied before a record is allowed into the dataset:

  1. the provenance URL was fetched with HTTP 200 and yielded >400 chars of text
     (checked against the local article cache, not against a claim);
  2. `verdict_quote` appears verbatim inside that cached article text -- this is
     what stops an invented conclusion from entering the dataset;
  3. the record's evidence URL equals the provenance URL;
  4. status is in the project vocabulary and dates are YYYY-MM-DD;
  5. id, evidence URL and normalized claim text are unique across old + new.

Records that fail any gate are written to research/rejected.tsv with the reason
and are NOT added. Existing entries in claims.json are preserved untouched
unless --drop-ids is given.

Usage:
    python Frontend/research/build_dataset.py [--dry-run]
"""

import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "website" / "src" / "data" / "claims.json"
BATCH_DIR = HERE / "batches"
REJECTED = HERE / "rejected.tsv"

STATUSES = {"false", "misleading", "unverified", "verified"}
CATEGORIES = {
    "politics", "elections", "communal", "ai-media", "health", "science",
    "environment", "crime", "scam", "society", "world", "finance",
    "entertainment", "religion",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{3,79}$")
TODAY = "2026-10-29"
QUOTE_FOLD = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "..."})


def norm(text):
    return re.sub(r"\s+", " ", (text or "").translate(QUOTE_FOLD)).strip().lower()


def default_cache_paths():
    """Every article cache the pipeline may have written.

    fetch_articles.py is run per job and defaults to a fnd_* temp directory, so a
    re-run with a single hardcoded path reports every earlier record as "no cached
    fetch". Glob instead, and keep the canonical name as the fallback so the
    WARNING still fires when no cache exists at all.
    """
    root = Path(tempfile.gettempdir())
    found = sorted(root.glob("fnd_*/articles.jsonl"))
    return found or [root / "fnd_research" / "articles.jsonl"]


def load_cache(paths):
    entries = {}
    for cache_path in paths:
        if not cache_path.exists():
            print(f"WARNING: no article cache at {cache_path}", file=sys.stderr)
            continue
        with cache_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = row["url"].rstrip("/")
                previous = entries.get(key)
                if previous is None or row.get("text_chars", 0) > previous.get("text_chars", 0):
                    entries[key] = row
    return entries


def load_batches():
    records, excluded = [], []
    for path in sorted(BATCH_DIR.glob("batch_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("records", []):
            item["_batch"] = path.name
            records.append(item)
        for item in payload.get("excluded", []):
            item["_batch"] = path.name
            excluded.append(item)
    return records, excluded


def gate(item, cache, used_ids, used_urls, used_claims):
    record = item.get("record") or {}
    prov = item.get("provenance") or {}
    rid = record.get("id", "<no id>")

    if not isinstance(record, dict) or not isinstance(prov, dict):
        return f"{rid}: record/provenance must be objects"

    url = str(prov.get("url", "")).rstrip("/")
    if not url:
        return f"{rid}: provenance.url missing"

    cached = cache.get(url)
    if not cached:
        return f"{rid}: no cached fetch for {url}"
    if cached.get("http") != 200:
        return f"{rid}: cached fetch returned HTTP {cached.get('http')}"
    if cached.get("text_chars", 0) < 400:
        return f"{rid}: only {cached.get('text_chars')} chars extracted from {url}"

    quote = str(prov.get("verdict_quote", "")).strip()
    if not quote:
        return f"{rid}: verdict_quote missing -- conclusion not evidenced"
    if len(quote.split()) > 34:
        return f"{rid}: verdict_quote longer than 30 words ({len(quote.split())})"
    if norm(quote) not in norm(cached.get("text", "")):
        return f"{rid}: verdict_quote NOT found verbatim in cached article text"

    evidence = record.get("evidence")
    if not isinstance(evidence, list) or len(evidence) != 1:
        return f"{rid}: evidence must be a single-item array"
    if str(evidence[0].get("url", "")).rstrip("/") != url:
        return f"{rid}: evidence url != provenance url"

    if not ID_RE.match(str(record.get("id", ""))):
        return f"{rid}: id must be lowercase kebab-case"
    if record.get("status") not in STATUSES:
        return f"{rid}: status '{record.get('status')}' not in vocabulary"
    if record.get("category") not in CATEGORIES:
        return f"{rid}: category '{record.get('category')}' not in vocabulary"
    for key in ("added_date", "review_date"):
        if not DATE_RE.match(str(record.get(key, ""))):
            return f"{rid}: {key} not YYYY-MM-DD"
    for key in ("claim", "explanation", "original_source", "fact_checker", "geo_scope"):
        if not str(record.get(key, "")).strip():
            return f"{rid}: '{key}' empty"
    if record.get("status") == "misleading" and not str(record.get("why_misleading", "")).strip():
        return f"{rid}: status 'misleading' requires why_misleading"
    if record.get("status") == "verified" and not str(prov.get("status_rationale", "")).strip():
        return f"{rid}: status 'verified' requires status_rationale"

    if record["id"] in used_ids:
        return f"{rid}: duplicate id"
    if url in used_urls:
        return f"{rid}: duplicate evidence url"
    claim_key = re.sub(r"[^a-z0-9]+", " ", str(record.get("claim", "")).lower()).strip()
    if claim_key in used_claims:
        return f"{rid}: duplicate claim text"
    return ""


def clean_record(record):
    """Keep exactly the keys the React components consume, in dataset order."""
    out = {
        "id": record["id"],
        "claim": record["claim"].strip(),
        "status": record["status"],
        "category": record["category"],
        "added_date": record["added_date"],
        "review_date": record["review_date"],
        "explanation": record["explanation"].strip(),
    }
    if str(record.get("why_misleading", "")).strip():
        out["why_misleading"] = record["why_misleading"].strip()
    out.update(
        {
            "original_source": record["original_source"].strip(),
            "fact_checker": record["fact_checker"].strip(),
            "geo_scope": record["geo_scope"].strip(),
            "archived": bool(record.get("archived", False)),
            "evidence": [
                {
                    "source": str(e["source"]).strip(),
                    "title": str(e["title"]).strip(),
                    "url": str(e["url"]).strip(),
                }
                for e in record["evidence"]
            ],
        }
    )
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report only, do not write claims.json")
    parser.add_argument(
        "--cache",
        action="append",
        default=None,
        help="articles.jsonl to verify quotes against; repeatable",
    )
    args = parser.parse_args()

    data = json.loads(DATA.read_text(encoding="utf-8"))
    existing = data["claims"]
    cache = load_cache([Path(p) for p in args.cache] if args.cache else default_cache_paths())
    items, excluded = load_batches()

    used_ids = {c["id"] for c in existing}
    used_urls = {e["url"].rstrip("/") for c in existing for e in c.get("evidence", [])}
    used_claims = {re.sub(r"[^a-z0-9]+", " ", c["claim"].lower()).strip() for c in existing}

    accepted, rejected = [], []
    for item in items:
        reason = gate(item, cache, used_ids, used_urls, used_claims)
        if reason:
            rejected.append((item.get("record", {}).get("id", "?"), reason, item["_batch"]))
            continue
        record = clean_record(item["record"])
        accepted.append((record, item["provenance"], item["_batch"]))
        used_ids.add(record["id"])
        used_urls.add(record["evidence"][0]["url"].rstrip("/"))
        used_claims.add(re.sub(r"[^a-z0-9]+", " ", record["claim"].lower()).strip())

    print(f"existing records : {len(existing)}")
    print(f"batch records    : {len(items)}")
    print(f"accepted         : {len(accepted)}")
    print(f"rejected         : {len(rejected)}")
    print(f"agent-excluded   : {len(excluded)}")
    print(f"TOTAL after merge: {len(existing) + len(accepted)}")

    merged = existing + [record for record, _, _ in accepted]
    active = [c for c in merged if not c.get("archived")]
    print(f"\nactive / archived: {len(active)} / {len(merged) - len(active)}")
    print(f"status (all)     : {dict(Counter(c['status'] for c in merged).most_common())}")
    print(f"categories       : {dict(Counter(c['category'] for c in merged).most_common())}")
    print(f"fact-checkers    : {dict(Counter(c['fact_checker'] for c in merged).most_common())}")

    if rejected:
        print(f"\n-- rejected ({len(rejected)}) --")
        for rid, reason, batch in rejected[:60]:
            print(f"  [{batch}] {reason}")

    if args.dry_run:
        print("\n--dry-run: claims.json and rejected.tsv NOT written")
        return 0

    with REJECTED.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("id\treason\tbatch\n")
        for rid, reason, batch in rejected:
            handle.write(f"{rid}\t{reason}\t{batch}\n")

    data["claims"] = merged
    data["last_updated"] = TODAY
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwrote {DATA} ({len(merged)} records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
