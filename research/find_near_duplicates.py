"""Find near-duplicate claims across reviewed batches before merging.

Different fact-checking organisations routinely publish separate articles about the same
viral post, and build_dataset.py only rejects *identical* claim text. This script flags
records that describe substantially the same claim so a human can keep the best-evidenced
one and drop the rest.

It compares three signals for every pair of records across all batches:
  * token overlap of the normalized claim text (Jaccard),
  * token overlap of the normalized explanation,
  * shared rare tokens (proper nouns / numbers) in the claim.

Reads only Frontend/research/batches/batch_*.json plus the existing claims.json. Writes
nothing; prints a ranked report.

Usage:
    python Frontend/research/find_near_duplicates.py [--threshold 0.55]
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BATCH_DIR = HERE / "batches"
DATA = HERE.parent / "website" / "src" / "data" / "claims.json"

STOP = set(
    """a an and are as at be but by for from has have in is it its of on or that the to was were
    with which what when who whom whose this these those there their they them he she his her
    video image photo post claim claims says said sharing shared viral being been not no
    fact check factcheck""".split()
)


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in STOP and len(t) > 1]


def jaccard(left, right):
    a, b = set(left), set(right)
    return len(a & b) / len(a | b) if a | b else 0.0


def load_records():
    rows = []
    for path in sorted(BATCH_DIR.glob("batch_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("records", []):
            record = item.get("record", {})
            rows.append(
                {
                    "origin": f"{path.name}:new",
                    "id": record.get("id", "?"),
                    "claim": record.get("claim", ""),
                    "explanation": record.get("explanation", ""),
                    "fact_checker": record.get("fact_checker", ""),
                    "url": (item.get("provenance") or {}).get("url", ""),
                    "claim_tokens": tokens(record.get("claim", "")),
                    "expl_tokens": tokens(record.get("explanation", "")),
                }
            )
    data = json.loads(DATA.read_text(encoding="utf-8"))
    for record in data.get("claims", []):
        rows.append(
            {
                "origin": "claims.json:existing",
                "id": record.get("id", "?"),
                "claim": record.get("claim", ""),
                "explanation": record.get("explanation", ""),
                "fact_checker": record.get("fact_checker", ""),
                "url": (record.get("evidence") or [{}])[0].get("url", ""),
                "claim_tokens": tokens(record.get("claim", "")),
                "expl_tokens": tokens(record.get("explanation", "")),
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=float, default=0.55, help="claim Jaccard cutoff")
    args = parser.parse_args()

    rows = load_records()
    new_rows = [r for r in rows if r["origin"].endswith(":new")]
    print(f"records scanned: {len(rows)} ({len(new_rows)} new, {len(rows) - len(new_rows)} existing)")

    rare = {t for t, n in Counter(t for r in rows for t in r["claim_tokens"]).items() if n >= 2}

    pairs = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            left, right = rows[i], rows[j]
            claim_sim = jaccard(left["claim_tokens"], right["claim_tokens"])
            if claim_sim < args.threshold:
                continue
            expl_sim = jaccard(left["expl_tokens"], right["expl_tokens"])
            shared_rare = sorted(set(left["claim_tokens"]) & set(right["claim_tokens"]) & rare)
            score = claim_sim + 0.4 * expl_sim
            pairs.append((score, claim_sim, expl_sim, shared_rare, left, right))

    pairs.sort(key=lambda p: -p[0])
    print(f"candidate near-duplicate pairs at threshold {args.threshold}: {len(pairs)}\n")
    for score, claim_sim, expl_sim, shared_rare, left, right in pairs:
        print(f"--- score {score:.2f}  claim {claim_sim:.2f}  expl {expl_sim:.2f}  shared: {', '.join(shared_rare[:8])}")
        for row in (left, right):
            print(f"    [{row['origin']}] {row['id']}")
            print(f"        {row['claim'][:150]}")
            print(f"        {row['fact_checker']}  {row['url'][:100]}")
        print()

    if not pairs:
        print("No near-duplicate pairs found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
