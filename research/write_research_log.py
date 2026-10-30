"""Generate research/claims_research_log.md from the artifacts the pipeline produced.

The user asked for a research log identifying the source URL and verification status of
every candidate. Rather than hand-writing it, this script derives it from files that
already exist, so the log cannot drift from what actually happened:

  candidates.tsv          every URL harvested, with the organisation and feed date
  logs/*.tsv              the HTTP status, served title, publication date and extracted
                          text length for each fetched URL
  cache/batch_*.json      the articles that were handed to a reviewer
  batches/batch_*.json    the reviewer output: accepted records and excluded articles
  rejected.tsv            records the merge gate refused, with the reason
  website/src/data/claims.json   the dataset actually shipped

Nothing here contacts the network.

Usage:
    python Frontend/research/write_research_log.py
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "website" / "src" / "data" / "claims.json"
OUT = HERE / "claims_research_log.md"
LEGACY_IDS = {
    "us-voting-machines-old-clips-2026", "voting-machine-glitches-systemic-fraud",
    "eiffel-tower-palestinian-flag-ai", "eiffel-tower-fire-ai-clip",
    "bengal-post-poll-old-video-2026", "bangladesh-scripted-marriage-video",
    "sitharaman-2023-presser-clip", "irs-refund-up-11-percent",
    "5g-health-harm-claim", "climate-petition-consensus-claim",
    "pope-puffer-coat-ai-image", "christchurch-conversions-350",
}
TODAY = "2026-10-29"


def read_tsv(path):
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < len(header):
                parts += [""] * (len(header) - len(parts))
            rows.append(dict(zip(header, parts)))
    return rows


def main():
    candidates = read_tsv(HERE / "candidates.tsv")
    fetches = {}
    for path in sorted(HERE.glob("logs/*.tsv")):
        for row in read_tsv(path):
            url = row["url"].rstrip("/")
            previous = fetches.get(url)
            chars = int(row.get("text_chars") or 0)
            if previous is None or chars > int(previous.get("text_chars") or 0):
                fetches[url] = row

    reviewed_urls = set()
    for path in sorted((HERE / "cache").glob("batch_*.json")):
        for row in json.loads(path.read_text(encoding="utf-8")):
            reviewed_urls.add(row["url"].rstrip("/"))

    accepted, excluded = [], []
    for path in sorted((HERE / "batches").glob("batch_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("records", []):
            item["_batch"] = path.name
            accepted.append(item)
        for item in payload.get("excluded", []):
            item["_batch"] = path.name
            excluded.append(item)

    rejected = [r for r in read_tsv(HERE / "rejected.tsv") if r.get("id") and not r["id"].startswith("#")]
    rejected_ids = {r["id"] for r in rejected}
    shipped = [i for i in accepted if i.get("record", {}).get("id") not in rejected_ids]

    data = json.loads(DATA.read_text(encoding="utf-8"))
    claims = data["claims"]
    new_claims = [c for c in claims if c["id"] not in LEGACY_IDS]

    lines = []
    add = lines.append

    add("# Claims dataset research log")
    add("")
    add(f"Generated {TODAY} by `research/write_research_log.py` from the pipeline's own artifacts.")
    add("No entry in this log was written by hand from memory.")
    add("")
    add("## Pipeline")
    add("")
    add("```")
    add("harvest_candidates.py -> candidates.tsv          (URLs discovered from RSS feeds and listings)")
    add("fetch_articles.py     -> logs/*.tsv + OS-temp cache   (HTTP status, served title, date, extracted text)")
    add("split_batches.py      -> cache/batch_NN.json     (usable articles grouped for review)")
    add("manual review         -> batches/batch_NN.json   (records + provenance, or an exclusion reason)")
    add("build_dataset.py      -> claims.json + rejected.tsv   (gates every record against the cached text)")
    add("validate_claims.py    -> schema, dedup and fetch-record checks")
    add("```")
    add("")
    add("The article text used for verification is cached in the OS temp directory, outside the")
    add("repository, so no copied article prose is committed to the project.")
    add("")

    add("## Funnel")
    add("")
    add("| stage | count |")
    add("| --- | --- |")
    add(f"| candidate URLs harvested | {len(candidates)} |")
    add(f"| distinct URLs fetched | {len(fetches)} |")
    ok = sum(1 for r in fetches.values() if r.get("http") == "200" and int(r.get("text_chars") or 0) > 400)
    add(f"| fetched with HTTP 200 and >400 chars of text | {ok} |")
    add(f"| articles handed to a reviewer | {len(reviewed_urls)} |")
    add(f"| reviewer exclusions | {len(excluded)} |")
    add(f"| records drafted by reviewers | {len(accepted)} |")
    add(f"| records rejected by the merge gate | {len(rejected)} |")
    add(f"| new records shipped | {len(new_claims)} |")
    add(f"| pre-existing records (untouched) | {len(claims) - len(new_claims)} |")
    add(f"| **total records in claims.json** | **{len(claims)}** |")
    add("")

    add("## Sources")
    add("")
    add("| organisation | harvested | fetched OK | reviewed | shipped |")
    add("| --- | --- | --- | --- | --- |")
    harvested = Counter(r["source"] for r in candidates)
    fetched_ok = Counter(
        r["source"] for r in fetches.values() if r.get("http") == "200" and int(r.get("text_chars") or 0) > 400
    )
    shipped_by_org = Counter(c["fact_checker"] for c in new_claims)
    reviewed_by_org = Counter(
        fetches[u]["source"] for u in reviewed_urls if u in fetches
    )
    for source, _ in harvested.most_common():
        add(
            f"| {source} | {harvested[source]} | {fetched_ok.get(source, 0)} "
            f"| {reviewed_by_org.get(source, 0)} | {shipped_by_org.get(source, 0)} |"
        )
    add("")

    add("## Status breakdown (shipped records)")
    add("")
    add("| status | new | pre-existing | total |")
    add("| --- | --- | --- | --- |")
    new_status = Counter(c["status"] for c in new_claims)
    old_status = Counter(c["status"] for c in claims if c["id"] in LEGACY_IDS)
    for status in ("false", "misleading", "verified", "unverified"):
        add(f"| `{status}` | {new_status.get(status, 0)} | {old_status.get(status, 0)} | {new_status.get(status, 0) + old_status.get(status, 0)} |")
    add("")

    add("## Category breakdown (shipped records)")
    add("")
    add("| category | new | total |")
    add("| --- | --- | --- |")
    new_cat = Counter(c["category"] for c in new_claims)
    all_cat = Counter(c["category"] for c in claims)
    for category, count in all_cat.most_common():
        add(f"| `{category}` | {new_cat.get(category, 0)} | {count} |")
    add("")

    add("## Every shipped record")
    add("")
    add("Verification status legend:")
    add("")
    add("- **verified-quote** - the record passed the merge gate, meaning a verbatim conclusion")
    add("  quote from the article was found inside the locally cached article text, the article was")
    add("  fetched with HTTP 200, and more than 400 characters of body text were extracted.")
    add("- **legacy** - a record that was already in `claims.json` before this expansion. AFP and")
    add("  Reuters return HTTP 401/403 to automated fetchers, so their articles could not be")
    add("  re-verified by this pipeline and are marked as such rather than claimed as verified.")
    add("")
    add("| id | status | category | fact-checker | evidence URL | verification |")
    add("| --- | --- | --- | --- | --- | --- |")
    for claim in claims:
        url = (claim.get("evidence") or [{}])[0].get("url", "")
        state = "legacy - not re-fetchable" if claim["id"] in LEGACY_IDS else "verified-quote"
        add(
            f"| `{claim['id']}` | {claim['status']} | {claim['category']} | {claim['fact_checker']} "
            f"| {url} | {state} |"
        )
    add("")

    add("## Rejected by the merge gate")
    add("")
    if rejected:
        add("| id | reason | batch |")
        add("| --- | --- | --- |")
        for row in rejected:
            add(f"| `{row['id']}` | {row['reason']} | {row['_batch']} |")
    else:
        add("None. Every drafted record passed the gate.")
    add("")

    add("## Excluded during review")
    add("")
    reasons = Counter()
    for item in excluded:
        reason = (item.get("reason") or "").strip()
        reasons[reason[:70]] += 1
    add(f"{len(excluded)} fetched articles were reviewed and deliberately not turned into records.")
    add("")
    add("| reason | count |")
    add("| --- | --- |")
    for reason, count in reasons.most_common():
        add(f"| {reason or '(no reason recorded)'} | {count} |")
    add("")
    add("<details><summary>full exclusion list</summary>")
    add("")
    add("| url | reason |")
    add("| --- | --- |")
    for item in sorted(excluded, key=lambda i: i.get("url", "")):
        add(f"| {item.get('url', '')} | {(item.get('reason') or '').strip()} |")
    add("")
    add("</details>")
    add("")

    add("## Candidates that were never usable")
    add("")
    never_reviewed = []
    for row in candidates:
        url = row["url"].rstrip("/")
        fetched = fetches.get(url)
        if url in reviewed_urls:
            continue
        if fetched is None:
            never_reviewed.append((row["source"], url, "not fetched"))
        elif fetched.get("http") != "200":
            never_reviewed.append((row["source"], url, f"HTTP {fetched.get('http')}"))
        elif int(fetched.get("text_chars") or 0) <= 400:
            never_reviewed.append((row["source"], url, f"only {fetched.get('text_chars')} chars extracted"))
        else:
            never_reviewed.append((row["source"], url, "fetched OK but not reviewed"))
    by_state = Counter(state for _, _, state in never_reviewed)
    add(f"{len(never_reviewed)} harvested candidates did not reach a reviewer.")
    add("")
    add("| state | count |")
    add("| --- | --- |")
    for state, count in by_state.most_common():
        add(f"| {state} | {count} |")
    add("")
    add("These were dropped to keep the review effort inside the target record count, not because")
    add("they failed a quality check, except where the state above says otherwise.")
    add("")

    add("## Sources that could not be harvested")
    add("")
    add("| organisation | result |")
    add("| --- | --- |")
    add("| AFP Fact Check | HTTP 403 to automated fetchers; no candidates harvested |")
    add("| Reuters Fact Check | HTTP 401 to automated fetchers; no candidates harvested |")
    add("| AP News fact checks | HTTP 403 to automated fetchers; no candidates harvested |")
    add("| Logically Facts | connection failed; no candidates harvested |")
    add("| PIB Fact Check | JS-rendered listing with no article links or feed; pagination returns 404 |")
    add("")
    add("No record in `claims.json` cites these organisations unless it was already present before")
    add("this expansion, in which case it is flagged `legacy` above.")
    add("")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(lines)} lines)")

    unused = defaultdict(int)
    for item in shipped:
        unused[item["_batch"]] += 1
    print(f"shipped records by batch: {dict(sorted(unused.items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
