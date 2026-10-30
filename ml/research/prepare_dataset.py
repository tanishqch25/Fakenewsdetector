"""Prepare canonical, type-specific records from an authorized mapped CSV.

Offline only. This script does not fetch data, infer source columns, or create
model artifacts. It writes only to the caller-selected output directory.
"""

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


TEXT_FIELDS = {
    "article": "text_article",
    "headline": "text_headline",
    "claim": "text_claim",
}
FIELDS = [
    "record_id", "dataset", "record_type", "label_raw", "text_article",
    "text_headline", "text_claim", "text_explanation", "source_name",
    "source_url", "published_at", "event_group", "syndication_group",
    "language", "text_article_source_field", "text_headline_source_field",
    "text_claim_source_field", "leakage_review_status",
]
SUPPORTED_DATASETS = {"ifnd", "hinfakenews", "factdrill", "fakenewsindia"}
ALLOWED_TYPES = set(TEXT_FIELDS) | {"fact_check_report", "social_post", "unknown"}
ENGLISH_TAGS = {"en", "eng", "english"}


def norm(value):
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"\s+", " ", value).strip()


def classify(dataset, raw):
    """Map only source-reported raw labels; canonical aliases are not accepted."""
    label = norm(raw)
    if dataset == "ifnd":
        if label == "fake":
            return "fake", True, ""
        if label == "true":
            return "real", True, ""
        return None, False, "unsupported_or_missing_ifnd_raw_label"
    if dataset == "hinfakenews":
        if label == "0":
            return "fake", True, ""
        if label == "1":
            return "real", True, ""
        return None, False, "unsupported_or_missing_hinfakenews_raw_label"
    if dataset == "factdrill":
        return None, False, "unsupported_until_record_level_label_definitions_verified"
    if dataset == "fakenewsindia":
        return None, False, "no_supported_binary_real_article_mapping"
    return None, False, "unknown_dataset"


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="UTF-8 canonical mapped CSV")
    parser.add_argument("--output-dir", required=True, type=Path, help="Prefer an output directory outside the repo")
    parser.add_argument("--record-type", required=True, choices=TEXT_FIELDS, help="Build eligibility for exactly one task type")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    records = []
    reasons = Counter()
    exact_groups = defaultdict(set)
    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not set(FIELDS).issubset(reader.fieldnames):
            raise SystemExit("Input CSV is missing required canonical columns: " + ", ".join(FIELDS))
        for index, source in enumerate(reader, start=1):
            row = {field: (source.get(field) or "").strip() for field in FIELDS}
            row["record_id"] = row["record_id"] or f"row-{index}"
            row["dataset"] = norm(row["dataset"])
            row["record_type"] = norm(row["record_type"]) or "unknown"
            if row["record_type"] not in ALLOWED_TYPES:
                row["record_type"] = "unknown"
            if row["dataset"] not in SUPPORTED_DATASETS:
                row["dataset"] = "unknown"
            row["language"] = norm(row["language"])
            row["label_normalized"], label_ok, reason = classify(row["dataset"], row["label_raw"])

            selected_field = TEXT_FIELDS[args.record_type]
            provenance_field = selected_field + "_source_field"
            failures = []
            if not label_ok:
                failures.append(reason)
            if row["record_type"] != args.record_type:
                failures.append("record_type_does_not_match_requested_task")
            if not row[selected_field]:
                failures.append("selected_text_field_missing")
            if not row[provenance_field]:
                failures.append("selected_text_source_field_provenance_missing")
            if row["leakage_review_status"] != "passed":
                failures.append("required_human_leakage_review_not_passed")
            if row["language"] not in ENGLISH_TAGS:
                failures.append("language_not_verified_english")

            row["eligible_record_type"] = args.record_type
            row["binary_eligible"] = not failures
            row["exclusion_reasons"] = failures
            row["exact_hashes"] = {}
            for record_kind, field in TEXT_FIELDS.items():
                value = norm(row[field])
                digest = hashlib.sha256(value.encode("utf-8")).hexdigest() if value else ""
                row["exact_hashes"][record_kind] = digest
                if digest:
                    exact_groups[(record_kind, digest)].add(row["record_id"])
            if failures:
                reasons.update(failures)
            records.append(row)

    for row in records:
        row["exact_duplicate_groups"] = sorted(
            "exact-" + kind + "-" + digest[:16]
            for kind, digest in row["exact_hashes"].items()
            if digest and len(exact_groups[(kind, digest)]) > 1
        )
    eligible = [row for row in records if row["binary_eligible"]]
    write_jsonl(args.output_dir / "records.jsonl", records)
    write_jsonl(args.output_dir / "eligible.jsonl", eligible)
    duplicate_clusters = sum(1 for ids in exact_groups.values() if len(ids) > 1)
    audit = {
        "input": str(args.input.resolve()),
        "requested_record_type": args.record_type,
        "record_count": len(records),
        "eligible_count": len(eligible),
        "eligible_by_label": dict(Counter(row["label_normalized"] for row in eligible)),
        "excluded_by_reason": dict(reasons),
        "exact_duplicate_cluster_count_by_type": duplicate_clusters,
        "near_duplicate_detection_performed": False,
        "event_and_syndication_groups_are_supplied_not_verified": True,
        "human_leakage_review_pass_required_for_eligibility": True,
    }
    (args.output_dir / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
