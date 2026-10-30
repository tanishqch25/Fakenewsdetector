# Indian news model research (preparation only)

This directory contains offline preparation and evaluation tooling, not dataset content. Dataset acquisition, access requests, package installation, script/test execution, model training, and candidate-model creation require separate approval.

## Dataset and rights status

See `dataset_manifest.json`. Public visibility or access does not establish reuse permission. A dataset license marked `UNKNOWN` or `NA` is unresolved and must be reviewed before data use. IFND and HinFakeNews remain on the license review list. FactDrill label mapping is unsupported until actual record-level label definitions are verified. FakeNewsIndia is not a binary real/fake article corpus. The register summarizes published/author-reported information; exact source columns and row-level records have not been inspected.

The experiment scope is English Indian news. The preparation script only accepts explicit English language tags (`en`, `eng`, `english`) and strict raw label values. Hindi HinFakeNews records therefore remain ineligible for this English-only run. Do not put copyrighted dataset contents in this repository.

## Expected input and provenance

`prepare_dataset.py` takes one UTF-8 CSV mapped by an operator from an authorized source. It does not guess dataset columns. Required columns are:

`record_id,dataset,record_type,label_raw,text_article,text_headline,text_claim,text_explanation,source_name,source_url,published_at,event_group,syndication_group,language,text_article_source_field,text_headline_source_field,text_claim_source_field,leakage_review_status`

`dataset` is `ifnd`, `hinfakenews`, `factdrill`, or `fakenewsindia`; `record_type` must be `article`, `headline`, or `claim` for eligibility. For the selected record type, its text field and matching `*_source_field` value must be nonempty. The source-field value records the original source column name; it is not an invitation to use the explanation field. `leakage_review_status` must be exactly `passed` after a human verifies that verdicts, explanations, and other label-revealing text are excluded from the selected input. Pending, failed, missing, or undocumented provenance is excluded.

Only exact documented raw forms map: IFND `Fake` -> fake and `True` -> real; HinFakeNews `0` -> fake and `1` -> real. Case/whitespace normalization is applied, but `real`, `true` aliases for HinFakeNews, arbitrary numeric labels, and inferred labels are not accepted. FactDrill is always excluded until record-level definitions are verified and deliberately mapped in a separately approved change. FakeNewsIndia has no supported real class and is excluded from this binary article task. Missing, misleading, partly true, unverified, irrelevant, and unknown labels never become fake or real.

## Preparation outputs

Example (run only after separate approval):

```powershell
python Frontend/ml/research/prepare_dataset.py --input <authorized-mapped.csv> --output-dir <outside-repository-output-dir> --record-type article
```

The required `--record-type` is `article`, `headline`, or `claim`. Output `eligible.jsonl` contains only rows eligible for that selected task. `records.jsonl` retains all normalized rows and exclusion reasons. `audit.json` reports the same task-specific eligible count, label counts, exclusion counts, and exact duplicate clusters. Outputs should be outside the repository and never under website assets.

The script computes normalized exact-text hashes separately for article, headline, and claim. It does not detect semantic near-duplicates, verify source fields, infer event relationships, or independently validate syndication metadata. Human leakage review and supplied event/syndication IDs are required prerequisites, but those IDs remain unverified metadata. Manual near-duplicate, event, and syndication review must be documented before training or treating results as leakage-aware.

## Evaluation protocol

`evaluate_models.py` scores only existing fitted scikit-learn classifiers. It does not fit, tune, or save models. It loads the baseline from `Frontend/ml/best_model.pkl` by default and only predicts; this does not overwrite the artifact. An optional candidate path must already exist and have been separately authorized. The original baseline training corpus is unknown, so baseline overlap with evaluation records is unknown; baseline scores are descriptive and may reflect prior exposure.

The evaluator requires the prepared `eligible.jsonl`, rejects missing/duplicate record IDs, and evaluates one record type at a time. Its deterministic group holdout uses stable IDs derived from sorted member record IDs, exact hashes, and supplied event/syndication IDs. It reserves nonempty test and non-test sides when possible and reports unsupported when it cannot. The source-held-out view selects a deterministic known source, excludes missing-source rows, and removes all cross-source or unknown-source duplicate/event/syndication groups from both sides; test rows contain only the held source. If clean nonempty partitions cannot be formed, that view is unsupported.

Both splits are diagnostic only. Grouping catches exact normalized matches and trusts supplied metadata; it does not infer or verify near-duplicates, syndication, or event equivalence. The splits are not stratified; report class counts. No independent Indian test set is included. A separately curated independent test set requires separate approval. Do not claim independent Indian-news performance without one.

Metrics are macro precision, recall, and F1 plus per-class values and confusion matrix (rows=true, columns=predicted; order fake, real). The evaluator validates that the model declares classes exactly `{0,1}` and predicts only those values. Labels map to integers only as fake=0, real=1. Unknown, misleading, partly true, unverified, and irrelevant examples are excluded.

## Documented test cases (not executed)

Before any approved run, add automated tests or an equivalent reviewed fixture check for these cases:

- IFND accepts raw `Fake` and `True`; rejects `real`, missing, and arbitrary labels. HinFakeNews accepts raw `0` and `1`; rejects aliases and missing labels.
- FactDrill and FakeNewsIndia remain ineligible; Hindi language tags remain ineligible for this English scope.
- Missing selected text, missing source-column provenance, non-passed leakage review, or wrong record type excludes the row and the same reason appears in the audit.
- Eligibility/audit counts match the selected record type exactly; explanation text is never selected as the model input.
- Exact duplicate, event, and syndication links form transitive groups. Reordering input rows does not change group membership or held-out assignment.
- Group holdout has nonempty disjoint sides for feasible cases and fails clearly for one indivisible group. Source holdout contains only one known source, excludes unknown-source rows and mixed-source groups, and fails clearly when no clean test or non-test side remains.
- Metrics use fake=0/real=1 ordering; a model missing `classes_`, having unexpected classes, or predicting outside `{0,1}` fails before writing results.
- Baseline loading/prediction never writes to the model path. Candidate scoring requires an existing candidate path and never creates one.

Failure conditions include missing required CSV columns, unsupported dataset or raw label, unsupported record type, unverified/non-English language, absent provenance, leakage review not passed, duplicate/empty record IDs at evaluation, invalid model classes/predictions, and impossible nonempty leakage-safe splits. These cases should fail closed rather than silently map, split, or score.

## Limitations and production boundary

The baseline is English word TF-IDF plus LinearSVC, but its training data provenance is unknown. Dataset/source artifacts, duplicate claims, class imbalance, events, and time can inflate scores. Article text, headlines, and isolated claims are separate tasks. The dashboard claims file is not a model training corpus. These scripts write only to caller-selected output paths and do not download data, install packages, train models, or create candidates. `Frontend/ml/best_model.pkl`, the API, backend, website, and existing requirements files are outside the write plan.
