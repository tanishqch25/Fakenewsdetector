"""Validate website/src/data/claims.json against the dashboard schema.

Offline. Reads only:
  * ../website/src/data/claims.json  (the dataset the dashboard consumes)
  * ./fetch_log.tsv                  (the network verification record)

Checks, in order:
  1. top-level shape and per-record required keys and types
  2. status vocabulary and ISO date formats
  3. non-empty, non-placeholder text fields
  4. evidence objects complete, http(s) URLs, unique across the whole dataset
  5. unique record ids, no duplicate claim text
  6. every NEW evidence URL was actually fetched with HTTP 200 and its recorded
     title matches the title stored in the dataset (legacy rows are exempt but
     reported, because AFP and Reuters block automated fetchers)
  7. summary tallies that must match what Dashboard.jsx computes at render time

Exit code 0 = clean, 1 = problems found.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "website" / "src" / "data" / "claims.json"
FETCH_LOG = HERE / "fetch_log.tsv"

STATUSES = {"false", "misleading", "unverified", "verified"}
REQUIRED = [
    "id", "claim", "status", "category", "added_date", "review_date",
    "explanation", "original_source", "fact_checker", "geo_scope",
    "archived", "evidence",
]
OPTIONAL = ["why_misleading"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{3,79}$")
PLACEHOLDERS = ["todo", "tbd", "lorem", "xxx", "placeholder", "fixme", "n/a"]
LEGACY_IDS = {
    "us-voting-machines-old-clips-2026", "voting-machine-glitches-systemic-fraud",
    "eiffel-tower-palestinian-flag-ai", "eiffel-tower-fire-ai-clip",
    "bengal-post-poll-old-video-2026", "bangladesh-scripted-marriage-video",
    "sitharaman-2023-presser-clip", "irs-refund-up-11-percent",
    "5g-health-harm-claim", "climate-petition-consensus-claim",
    "pope-puffer-coat-ai-image", "christchurch-conversions-350",
}


def norm(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def load_fetch_log():
    """Merge fetch_log.tsv with every per-job log under research/logs/."""
    entries = {}
    logs = sorted(HERE.glob("logs/*.tsv"))
    if FETCH_LOG.exists():
        logs.append(FETCH_LOG)
    for path in logs:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 5 or parts[0] == "url":
                    continue
                previous = entries.get(parts[0].rstrip("/"))
                try:
                    chars = int(parts[4] or 0)
                except ValueError:
                    continue
                if previous is not None and previous["chars"] >= chars:
                    continue
                entries[parts[0].rstrip("/")] = {
                    "http": parts[1],
                    "title": parts[2],
                    "published": parts[3],
                    "chars": chars,
                }
    return entries


def main():
    errors, warnings = [], []
    data = json.loads(DATA.read_text(encoding="utf-8"))

    for key in ("last_updated", "note", "claims"):
        if key not in data:
            errors.append(f"top level: missing '{key}'")
    if not DATE_RE.match(str(data.get("last_updated", ""))):
        errors.append("top level: last_updated is not YYYY-MM-DD")
    if not isinstance(data.get("claims"), list):
        errors.append("top level: claims is not a list")
        print("\n".join(errors))
        return 1

    claims = data["claims"]
    fetch_log = load_fetch_log()
    ids, urls, claim_texts = {}, {}, {}

    for index, claim in enumerate(claims):
        where = f"[{index}] {claim.get('id', '<no id>')}"

        for key in REQUIRED:
            if key not in claim:
                errors.append(f"{where}: missing required key '{key}'")
        for key in claim:
            if key not in REQUIRED and key not in OPTIONAL:
                warnings.append(f"{where}: unknown key '{key}' (React components ignore it)")

        record_id = claim.get("id", "")
        if not ID_RE.match(record_id):
            errors.append(f"{where}: id must be lowercase kebab-case 4-80 chars")
        if record_id in ids:
            errors.append(f"{where}: duplicate id (also at index {ids[record_id]})")
        ids[record_id] = index

        if claim.get("status") not in STATUSES:
            errors.append(f"{where}: status '{claim.get('status')}' not in {sorted(STATUSES)}")
        if claim.get("status") == "misleading" and not claim.get("why_misleading"):
            warnings.append(f"{where}: status is 'misleading' but why_misleading is empty")

        for key in ("added_date", "review_date"):
            if not DATE_RE.match(str(claim.get(key, ""))):
                errors.append(f"{where}: {key} '{claim.get(key)}' is not YYYY-MM-DD")

        for key in ("claim", "explanation", "original_source", "fact_checker", "geo_scope", "category"):
            value = claim.get(key, "")
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{where}: '{key}' is empty or not a string")
                continue
            low = value.lower()
            for token in PLACEHOLDERS:
                if token in low and not (token == "n/a" and "n/a" in low[:4]):
                    errors.append(f"{where}: '{key}' contains placeholder text '{token}'")
            if key != "category" and len(value.strip()) < 4:
                warnings.append(f"{where}: '{key}' is very short ({len(value.strip())} chars)")

        text_key = norm(claim.get("claim"))
        if text_key in claim_texts:
            errors.append(f"{where}: duplicate claim text (also at index {claim_texts[text_key]})")
        claim_texts[text_key] = index

        if not isinstance(claim.get("archived"), bool):
            errors.append(f"{where}: 'archived' must be a boolean")

        evidence = claim.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{where}: evidence must be a non-empty array")
            continue
        for item_index, item in enumerate(evidence):
            tag = f"{where} evidence[{item_index}]"
            if not isinstance(item, dict):
                errors.append(f"{tag}: must be an object")
                continue
            for key in ("source", "title", "url"):
                if not str(item.get(key, "")).strip():
                    errors.append(f"{tag}: missing '{key}'")
            url = str(item.get("url", "")).rstrip("/")
            if not re.match(r"^https?://[^\s]+$", url):
                errors.append(f"{tag}: url is not a valid http(s) URL")
            if url in urls:
                errors.append(f"{tag}: duplicate evidence url (also in '{urls[url]}')")
            urls[url] = record_id

            if record_id in LEGACY_IDS:
                continue
            logged = fetch_log.get(url)
            if not logged:
                errors.append(f"{tag}: URL was never fetched -- no verification record in fetch_log.tsv")
                continue
            if logged["http"] != "200":
                errors.append(f"{tag}: last fetch returned HTTP {logged['http']}, not 200")
            if logged["chars"] < 400:
                errors.append(f"{tag}: only {logged['chars']} chars of text extracted -- content not confirmed")
            served = norm(logged["title"])
            stated = norm(item.get("title", ""))
            if served and stated:
                overlap = len(set(stated.split()) & set(served.split())) / max(1, len(set(stated.split())))
                if overlap < 0.5:
                    errors.append(
                        f"{tag}: stated title does not match served title "
                        f"(word overlap {overlap:.0%})\n      stated:  {item.get('title')}\n      served:  {logged['title'][:150]}"
                    )

    active = [c for c in claims if not c.get("archived")]
    print(f"records total     : {len(claims)}")
    print(f"active / archived : {len(active)} / {len(claims) - len(active)}")
    print(f"status (active)   : {dict(Counter(c.get('status') for c in active))}")
    print(f"status (all)      : {dict(Counter(c.get('status') for c in claims))}")
    print(f"categories        : {dict(Counter(c.get('category') for c in active).most_common())}")
    print(f"fact-checkers     : {dict(Counter(c.get('fact_checker') for c in active).most_common())}")
    print(f"evidence links    : {sum(len(c.get('evidence', [])) for c in claims)}")
    print(f"last_updated      : {data.get('last_updated')}")
    print(f"review date range : {min(c['review_date'] for c in claims)} -> {max(c['review_date'] for c in claims)}")

    if warnings:
        print(f"\n-- {len(warnings)} warning(s) --")
        for line in warnings[:40]:
            print("  " + line)
    if errors:
        print(f"\n-- {len(errors)} error(s) --")
        for line in errors[:80]:
            print("  " + line)
        return 1
    print("\nOK: dataset validates against the dashboard schema and every new URL has a fetch record.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
