# Fake News Analyzer — run & handoff guide

Everything lives inside `Frontend/`. The React website talks to a FastAPI
backend over HTTP; the backend loads the existing scikit-learn pipeline from
`Frontend/ml/best_model.pkl`. The browser never touches the model file.

## Layout

```text
Frontend/
├── app.py                  # legacy Streamlit app (preserved)
├── requirements.txt        # legacy file — currently EMPTY (see troubleshooting)
├── ml/best_model.pkl       # trained TfidfVectorizer -> LinearSVC pipeline (do not retrain/move)
├── ml/research/            # preparation-only ML tooling: dataset register + eval scripts (never trains)
├── backend/
│   ├── main.py             # FastAPI API
│   └── requirements.txt    # pinned backend dependencies
├── research/               # offline pipeline that sourced and verified the dashboard claims
│   ├── claims_research_log.md   # per-record verification status, exclusions, blocked hosts
│   └── *.py                     # harvest → fetch → review batches → gated merge → validate
└── website/                # React + Vite frontend
    ├── package.json
    ├── vite.config.js      # dev proxy: /api -> http://127.0.0.1:8000
    └── src/                # pages, components, styles, data/claims.json
```

## Prerequisites (already set up on this machine)

- Python 3.11 virtual environment at `C:\FakeNewsdetector\.venv` with the
  backend dependencies installed from `backend/requirements.txt`
  (fastapi, uvicorn, scikit-learn **1.6.1** — the version the model was trained
  with — joblib, requests, beautifulsoup4).
- Node.js + npm (developed and tested with Node v24). `website/node_modules`
  is already installed; run `npm install` only on a fresh clone.
- No datasets, accounts, or extra services are required.

## 1. Start the FastAPI backend

```bat
cd C:\FakeNewsdetector\Frontend\backend
C:\FakeNewsdetector\.venv\Scripts\python.exe -m uvicorn main:app --port 8000
```

(Equivalent: activate the venv first, then `python -m uvicorn main:app --port 8000`.)

- API base: `http://localhost:8000/api`
- Health check: `http://localhost:8000/api/health`
  → `{"status":"ok","model_loaded":true,"labels":{"0":"Potentially Fake","1":"Potentially Real"}}`
- Analysis endpoint: `POST /api/analyze` with JSON `{"text": "..."}` **or**
  `{"url": "https://..."}` (exactly one of the two).

## 2. Start the React website

```bat
cd C:\FakeNewsdetector\Frontend\website
npm run dev
```

- Site: `http://localhost:5173` — use the `localhost` hostname. On this machine
  Vite binds the IPv6 loopback, so `http://127.0.0.1:5173` may refuse
  connections while `localhost` works.
- The dev server proxies `/api/*` to the backend, so
  `http://localhost:5173/api/health` also works and no CORS setup is needed in
  development. (The backend additionally allows origins
  `http://localhost:5173` and `http://127.0.0.1:5173`.)
- Production build, if ever needed: `npm run build` (output in `website/dist`).

## 3. Legacy Streamlit app (optional)

```bat
cd C:\FakeNewsdetector\Frontend
C:\FakeNewsdetector\.venv\Scripts\python.exe -m pip install streamlit
C:\FakeNewsdetector\.venv\Scripts\python.exe -m streamlit run app.py
```

`Frontend/requirements.txt` is empty (it predates this setup); `app.py` imports
`streamlit`, `joblib`, `requests`, and `beautifulsoup4`, so streamlit must be
installed once as above. Both apps expect the model at `Frontend/ml/best_model.pkl`.

## Model location & labels

- Path expected by backend and Streamlit app: `Frontend/ml/best_model.pkl`
  (lowercase `ml`).
- Labels are fixed: `0 = Potentially Fake`, `1 = Potentially Real`.

## Common startup errors

| Symptom | Cause / fix |
| --- | --- |
| Home page shows "Backend offline" pill | Backend not running or wrong port. Start step 1, keep port 8000. |
| `127.0.0.1:5173` refuses connection | Vite bound IPv6 loopback; open `http://localhost:5173` instead. |
| `Port 5173 is in use, trying another one...` | An older dev server is still running; use the printed port or stop the old process. |
| `Model file not found at ...ml\best_model.pkl` | Model moved/renamed; restore it to `Frontend/ml/best_model.pkl`. Do not edit the path in code. |
| `InconsistentVersionWarning` from scikit-learn | venv has a scikit-learn other than 1.6.1; reinstall `scikit-learn==1.6.1` from `backend/requirements.txt`. |
| URL analysis: "Could not extract enough article text" | Target site needs JavaScript, is paywalled, or blocks bots; paste the article text in News Text mode. |
| URL analysis: "Private or non-public network addresses are not allowed" | Intentional SSRF guard: only public http/https URLs are accepted. |
| `streamlit: command not found` / ModuleNotFoundError | Streamlit was never installed into the venv (see step 3). |

## Classifier limitations (keep visible in the product)

The model is a **screening classifier** trained on a fixed dataset: it compares
writing patterns (TF-IDF word/phrase features + linear SVM), not facts. It has
no knowledge of real-world events, cannot verify any claim, and its output is
not a probability of truth. "Potentially Real" is not a credibility guarantee;
"Potentially Fake" is not proof of a lie. The UI must keep stating this, and
users should consult credible sources for anything important.

## Dashboard manual review workflow (weekly)

Data lives in `website/src/data/claims.json` — currently **114 records (113 active, 1
archived)**. Nothing is scraped or updated automatically; the file is imported
statically by `Dashboard.jsx`, `RecentFactChecks.jsx` and `About.jsx` and bundled
at build time.

1. Add a claim: copy an entry, fill `id`, `claim`, `category`, `added_date`,
   `review_date` (YYYY-MM-DD), `status`, `explanation`, `fact_checker`,
   `original_source`, `geo_scope`, optional `why_misleading`, and `evidence`
   objects (`source`, `title`, direct `url`).
2. Statuses are strict: `unverified` (insufficient reliable evidence either
   way), `misleading` (context omitted/twisted, with evidence), `false`
   (reliable evidence shows the claim false), `verified` (reliable evidence
   supports it). Never mark a claim false because it is unpopular, unfamiliar,
   or flagged by the ML model — and never mark one `verified` just because a
   fact-check wrote about it.
3. Re-review: update `review_date` only on days you actually re-checked the
   entry; replace evidence links in place.
4. Retire: set `"archived": true` (entry hides by default, stays in the file).
5. Bump top-level `last_updated`, save, refresh the site. No backend restart.
   The eight newest non-archived records also surface in the "Recently
   Fact-Checked News" strip on the homepage — no component edit needed.
6. Check the file:

   ```bat
   cd C:\FakeNewsdetector\Frontend
   C:\FakeNewsdetector\.venv\Scripts\python.exe research\validate_claims.py
   ```

   Exit 0 with no warnings means schema, status vocabulary, date formats,
   placeholder text, duplicate ids/URLs/claim text and per-record fetch records
   all pass. Non-zero prints the offending records.

### Adding a batch of claims with `Frontend/research/`

`research/` is how the 102 added records were produced, and it is the recommended
path for a large weekly extension. It is offline, stdlib-only, and never touches
the model, backend or dependency files.

```text
harvest_candidates.py → candidates.tsv          discover article URLs from RSS/listings
fetch_articles.py     → logs/*.tsv + temp cache  fetch, extract body text, log HTTP status
split_batches.py      → cache/batch_NN.json      keep HTTP 200 + >400 chars, group for review
  (human/agent review → batches/batch_NN.json    record + provenance; see REVIEW_INSTRUCTIONS.md)
build_dataset.py      → claims.json + rejected.tsv  gate each record, then merge (--dry-run first)
validate_claims.py                               audit the shipped file
```

The gate in `build_dataset.py` is the point: a record is merged only if a
**verbatim conclusion quote** (≤30 words) from the article actually appears in
the text fetched from its own evidence URL, plus vocabulary, date and uniqueness
checks. Records that fail go to `rejected.tsv` with the reason. Note that the
batches are not cleared after a merge, so re-running `build_dataset.py --dry-run`
once the records are in `claims.json` reports every one of them as
`duplicate id` — that is the dedup gate working, not a regression. Use `--dry-run`
*before* the first merge of a new batch. `check_fidelity.py` and
`find_near_duplicates.py` add a numbers/proper-nouns coverage audit and a
reworded-duplicate detector. `write_research_log.py` regenerates
`claims_research_log.md`, which lists every candidate, its verification status,
every exclusion with its reason, and the hosts that could not be harvested.

Article text is cached in the OS temp directory, outside the repository, so no
copyrighted prose is committed. The cache is ephemeral — `check_fidelity.py` and
`find_near_duplicates.py` need it (or `research/batches/`), whereas
`validate_claims.py` runs from committed files alone.

Some evidence hosts (AFP Fact Check, Reuters, AP) return 401/403 to automated
fetchers, and PIB Fact Check is JS-rendered with no feed; those were not
harvestable. The 5 AFP/Reuters records that predate this pipeline are labelled
`legacy` in `claims_research_log.md` and are exempt from the fetch-record check —
open those links in a browser during the weekly pass.
