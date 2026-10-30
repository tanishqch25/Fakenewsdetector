"""Score already-fitted models on prepared records; this script never trains.

It is offline and writes only to --output. Do not run without separate approval.
No independent Indian test set is bundled and baseline training overlap is unknown.
"""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import joblib
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score


TEXT_FIELD = {"article": "text_article", "headline": "text_headline", "claim": "text_claim"}


def load_rows(path, record_type):
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("eligible_record_type") != record_type or not row.get("binary_eligible"):
                continue
            if row.get("label_normalized") not in {"fake", "real"}:
                continue
            if not row.get(TEXT_FIELD[record_type]):
                continue
            rows.append(row)
    ids = [row.get("record_id") for row in rows]
    if any(not value for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("Eligible records must have unique, nonempty record_id values")
    return rows


class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def make_groups(rows):
    """Return stable IDs for transitive exact-text and supplied metadata groups."""
    uf = UnionFind(len(rows))
    seen = {}
    for i, row in enumerate(rows):
        keys = set()
        hashes = row.get("exact_hashes", {})
        if isinstance(hashes, dict):
            keys.update(f"text:{kind}:{digest}" for kind, digest in hashes.items() if digest)
        elif isinstance(hashes, list):
            # Compatibility with earlier preparation output.
            keys.update(f"text:any:{digest}" for digest in hashes if digest)
        for field in ("event_group", "syndication_group"):
            value = (row.get(field) or "").strip()
            if value:
                keys.add(f"{field}:{value}")
        for key in keys:
            if key in seen:
                uf.union(i, seen[key])
            else:
                seen[key] = i
    members = defaultdict(list)
    for i, row in enumerate(rows):
        members[uf.find(i)].append(row["record_id"])
    group_id = {}
    for root, record_ids in members.items():
        digest = hashlib.sha256("\n".join(sorted(record_ids)).encode("utf-8")).hexdigest()[:20]
        group_id[root] = "group-" + digest
    return [group_id[uf.find(i)] for i in range(len(rows))]


def split_group_holdout(rows, groups):
    unique = sorted(set(groups), key=lambda value: hashlib.sha256(value.encode()).hexdigest())
    if len(unique) < 2:
        return [], [], "unsupported_fewer_than_two_disjoint_groups"
    target = max(1, round(len(rows) * 0.2))
    held, count = set(), 0
    for group in unique:
        group_count = sum(value == group for value in groups)
        # Keep at least one record in the non-test partition.
        if count + group_count >= len(rows):
            continue
        held.add(group)
        count += group_count
        if count >= target:
            break
    test = [i for i, group in enumerate(groups) if group in held]
    train = [i for i, group in enumerate(groups) if group not in held]
    if not train or not test:
        return [], [], "unsupported_cannot_make_nonempty_group_disjoint_partitions"
    return train, test, "deterministic_approx_20pct_group_holdout"


def split_source_holdout(rows, groups):
    source_values = [(row.get("source_name") or "").strip().casefold() for row in rows]
    known_sources = sorted({value for value in source_values if value})
    if len(known_sources) < 2:
        return [], [], "unsupported_fewer_than_two_known_sources"
    held_source = min(known_sources, key=lambda value: hashlib.sha256(value.encode()).hexdigest())
    group_sources = defaultdict(set)
    group_has_unknown_source = defaultdict(bool)
    for i, group in enumerate(groups):
        if source_values[i]:
            group_sources[group].add(source_values[i])
        else:
            group_has_unknown_source[group] = True

    # Shared groups cannot safely appear in either side of a pure source-held-out
    # test. Exclude them from both sides instead of adding other sources to test.
    held_groups = {groups[i] for i, source in enumerate(source_values) if source == held_source}
    contaminated = {
        group for group in held_groups
        if group_sources[group] - {held_source} or group_has_unknown_source[group]
    }
    pure_test_groups = held_groups - contaminated
    test = [i for i, source in enumerate(source_values) if source == held_source and groups[i] in pure_test_groups]
    train = [
        i for i, source in enumerate(source_values)
        if source and source != held_source and groups[i] not in held_groups and groups[i] not in contaminated
    ]
    if not train or not test:
        return [], [], f"unsupported_source_split_no_nonempty_clean_partition:{held_source}"
    description = (
        f"held_source:{held_source}; cross_source_groups_excluded:{len(contaminated)}; "
        "unknown_source_records_excluded"
    )
    return train, test, description


def score(model, rows, indices, record_type):
    if not indices:
        return {"status": "unsupported_empty_split"}
    classes = getattr(model, "classes_", None)
    class_values = list(classes) if classes is not None else []
    if len(class_values) != 2 or set(class_values) != {0, 1}:
        raise ValueError("Model classes_ must be exactly {0, 1} (0=fake, 1=real)")
    actual = [0 if rows[i]["label_normalized"] == "fake" else 1 for i in indices]
    texts = [rows[i][TEXT_FIELD[record_type]] for i in indices]
    raw_predictions = list(model.predict(texts))
    if any(value not in (0, 1) for value in raw_predictions):
        raise ValueError("Model predict() returned labels outside {0, 1}")
    predicted = [int(value) for value in raw_predictions]
    labels = [0, 1]
    return {
        "status": "scored",
        "class_order": ["fake", "real"],
        "support": dict(Counter("fake" if value == 0 else "real" for value in actual)),
        "precision_macro": precision_score(actual, predicted, labels=labels, average="macro", zero_division=0),
        "recall_macro": recall_score(actual, predicted, labels=labels, average="macro", zero_division=0),
        "f1_macro": f1_score(actual, predicted, labels=labels, average="macro", zero_division=0),
        "precision_per_class": precision_score(actual, predicted, labels=labels, average=None, zero_division=0).tolist(),
        "recall_per_class": recall_score(actual, predicted, labels=labels, average=None, zero_division=0).tolist(),
        "f1_per_class": f1_score(actual, predicted, labels=labels, average=None, zero_division=0).tolist(),
        "confusion_matrix_rows_true_columns_predicted": confusion_matrix(actual, predicted, labels=labels).tolist(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="eligible.jsonl from prepare_dataset.py")
    parser.add_argument("--baseline", type=Path, default=Path(__file__).resolve().parents[1] / "best_model.pkl")
    parser.add_argument("--candidate", type=Path, help="Optional already-existing fitted candidate; never created here")
    parser.add_argument("--record-type", choices=TEXT_FIELD, default="article")
    parser.add_argument("--output", required=True, type=Path, help="Metrics JSON path, preferably outside repo")
    args = parser.parse_args()

    rows = load_rows(args.input, args.record_type)
    groups = make_groups(rows)
    splits = {
        "group_holdout": split_group_holdout(rows, groups),
        "source_holdout": split_source_holdout(rows, groups),
    }
    models = {"baseline": args.baseline}
    if args.candidate:
        models["candidate"] = args.candidate
    results = {}
    for model_name, model_path in models.items():
        model = joblib.load(model_path)
        results[model_name] = {}
        for split_name, (train_idx, test_idx, description) in splits.items():
            results[model_name][split_name] = {
                "split": description,
                "non_test_count": len(train_idx),
                "test_count": len(test_idx),
                "metrics": score(model, rows, test_idx, args.record_type),
            }
    report = {
        "record_type": args.record_type,
        "input_count": len(rows),
        "independent_indian_test_set": "not_provided",
        "metrics_are_independent_indian_evidence": False,
        "baseline_training_data_overlap": "unknown; scores may overlap baseline training data",
        "baseline_input_domain_provenance": "unknown; headline/claim evaluation may differ from baseline training input format",
        "models": results,
        "grouping_limitations": (
            "Exact normalized text hashes plus supplied event/syndication IDs only. "
            "Near-duplicates, event links, and syndication groups are not independently inferred or verified."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
