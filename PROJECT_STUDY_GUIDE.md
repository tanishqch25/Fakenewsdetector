# Fake News Analyzer — Complete Project Study Guide

**Prepared for:** a third-year CSE–AIML student presenting, demoing and defending this project in a viva.
**Scope:** everything in this guide was verified by reading the actual files in `Frontend/` and by inspecting the saved model artifact. Nothing here is invented.
**Date of verification:** 2026-10-29

> ### How to read the honesty markers used throughout
>
> | Marker | Meaning |
> | --- | --- |
> | ✅ **Verified** | Confirmed by reading a file in this repo or by inspecting the model artifact directly. |
> | ⚠️ **Unknown / not recorded** | The project does not contain this information. Say "not recorded" in a viva — never guess a number. |
> | 🔜 **Future work** | Planned but **not implemented**. Never describe these as existing features. |
>
> The single most important rule for your viva: **this repository contains no measured accuracy, precision, recall or F1 score for `best_model.pkl`.** If an examiner asks "what accuracy did you get?", the correct, defensible answer is in [§3.8](#38-metrics-what-was-measured-nothing-yet-and-how-to-answer-that-question).

---

## Contents

1. [Project Overview & Architecture](#1-project-overview--architecture)
2. [Technologies Actually Used](#2-technologies-actually-used)
3. [How the Machine Learning Works](#3-how-the-machine-learning-works)
4. [Code Walkthrough, File by File](#4-code-walkthrough-file-by-file)
5. [End-to-End Request Trace](#5-end-to-end-request-trace)
6. [Limitations & Future Improvements](#6-limitations--future-improvements)
7. [Viva & Presentation Preparation](#7-viva--presentation-preparation)
8. [Appendix A — Verified facts vs. unknowns](#appendix-a--verified-facts-vs-unknowns)
9. [Appendix B — Command reference](#appendix-b--command-reference)
10. [Appendix C — One-line file map](#appendix-c--one-line-file-map)

---

## 1. Project Overview & Architecture

### 1.1 What the project is

A full-stack **news screening tool**. A user pastes article text or supplies a public article URL; a trained scikit-learn classifier reads the *writing style* of that text and returns one of two labels:

- `0` → **"Potentially Fake"**
- `1` → **"Potentially Real"**

The project ships **two independent subsystems** that are deliberately kept apart:

| | **A. ML screening** | **B. Claim dashboard** |
| --- | --- | --- |
| Purpose | Fast, automatic, style-based first-pass signal | Slow, human-reviewed record of specific circulating claims |
| Data source | `ml/best_model.pkl` (trained classifier) | `website/src/data/claims.json` (hand-maintained) |
| Runs on | Python FastAPI backend | Browser only — **no backend call at all** |
| Can it establish truth? | **No.** Patterns only. | Only as far as the cited evidence does |
| Updates | Frozen artifact; would need retraining | Manual weekly edit of a JSON file |
| Output vocabulary | 2 labels (`Potentially Fake` / `Potentially Real`) | 4 statuses (`unverified`, `misleading`, `false`, `verified`) |

### 1.2 ML screening vs. fact-checking — the distinction you must be able to state

This is the concept most likely to be probed in a viva.

- **Fact-checking** answers *"is this claim true?"* It requires evidence: primary documents, expert statements, official records, on-the-ground reporting. It is slow, expensive and done by humans.
- **This model** answers *"does this text look like the fake-news examples in its training data?"* It compares surface language patterns — vocabulary, phrasing, headline style, bigram frequencies. It has **no knowledge of the real world**, no database of events, and no ability to check whether anything actually happened.

Consequences you should state proactively:

- A **true** story written in a sensational style can be labelled *Potentially Fake*.
- A **fabricated** story written in calm, formal prose can be labelled *Potentially Real*.
- "Potentially Real" is **not** a credibility guarantee; "Potentially Fake" is **not** proof of a lie.

The product surfaces this everywhere: the backend attaches a `DISCLAIMER` string to every response ([`backend/main.py:24`](file:///C:/FakeNewsdetector/Frontend/backend/main.py#L24)), [`ResultCard.jsx`](file:///C:/FakeNewsdetector/Frontend/website/src/components/ResultCard.jsx) renders it under every verdict, [`Home.jsx`](file:///C:/FakeNewsdetector/Frontend/website/src/pages/Home.jsx) has a `notice-band` ("Know the limits."), [`Footer.jsx`](file:///C:/FakeNewsdetector/Frontend/website/src/components/Footer.jsx) repeats it site-wide, and [`About.jsx`](file:///C:/FakeNewsdetector/Frontend/website/src/pages/About.jsx) has a full "Limitations" card.

### 1.3 Architecture diagram

```text
                          BROWSER (React 18 SPA, Vite dev server :5173)
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │  index.html → main.jsx → App.jsx  (hash router: #/ #/checker #/dashboard #/about)
   │                                                                                 │
   │   Home.jsx ──── checkHealth() ─┐   Dashboard.jsx · RecentFactChecks.jsx         │
   │   About.jsx                    │   import claims.json  (NO network call)        │
   │   Checker.jsx ── analyzeText() / analyzeUrl()                                   │
   │        │              │                                                          │
   │        │        api.js  request()  →  fetch('/api/...')                          │
   │        ▼                                                                         │
   │   StateBlocks (Spinner / ErrorBlock / EmptyBlock) + ResultCard                   │
   └────────────────────────────────────────┬───────────────────────────────────────┘
                                            │  Vite proxy: '/api' → http://127.0.0.1:8000
                                            ▼
                    FASTAPI BACKEND (uvicorn, 127.0.0.1:8000)  backend/main.py
        ┌─────────────────────────────────────────────────────────────────────┐
        │ GET  /api/health   → { status, model_loaded, labels }                │
        │ POST /api/analyze  → AnalyzeRequest {text | url}  (exactly one)      │
        │                                                                      │
        │  url mode:  validate_public_url() → fetch_html() → extract_article() │
        │             (SSRF guards, redirect loop ≤6, 2 MB cap, BeautifulSoup) │
        │  then:      run_screening(article) → get_model() → model.predict()   │
        │  returns:   AnalyzeResponse {label, verdict, disclaimer, ...}        │
        └───────────────────────────────┬──────────────────────────────────────┘
                                        │ joblib.load() once, cached in `_model`
                                        ▼
                        ml/best_model.pkl  (2,443,296 bytes)
                        Pipeline: TfidfVectorizer(50,000 features) → LinearSVC

   ── separate, offline, never imported by the app ──────────────────────────────
   ml/research/  prepare_dataset.py · evaluate_models.py · dataset_manifest.json
                 (🔜 future dataset/training phase; no data acquired, nothing run)
   app.py        legacy single-file Streamlit version of the same classifier
```

### 1.4 Component responsibilities

| Layer | Files | Responsibility |
| --- | --- | --- |
| Presentation | `website/src/pages/*.jsx`, `website/src/components/*.jsx`, `website/src/styles.css` | Routing, forms, loading/empty/error/success states, dashboard filtering, theming |
| Transport | `website/src/api.js`, `website/vite.config.js` | One `fetch` wrapper, friendly offline message, dev proxy so no CORS handling is needed in development |
| API / business logic | `backend/main.py` | Request validation, SSRF-safe URL fetching, article extraction, model invocation, label→verdict mapping, disclaimer attachment |
| Model | `ml/best_model.pkl` | Frozen TF-IDF + LinearSVC pipeline; loaded server-side only |
| Curated data | `website/src/data/claims.json` | Human-reviewed claims with status, evidence links, dates |
| Legacy UI | `app.py` | Original Streamlit app, same model, same guards |
| Research tooling | `ml/research/*` | Offline dataset-preparation and evaluation scripts for the **future** Indian-news training phase |

### 1.5 Repository layout ✅ Verified

```text
Frontend/
├── PROJECT_STUDY_GUIDE.md          ← this document
├── README.md                       ← run & handoff guide
├── app.py                          ← legacy Streamlit app (549 lines)
├── requirements.txt                ← EMPTY (0 bytes) — see §2.3
├── ml/
│   ├── best_model.pkl              ← 2,443,296 bytes, do not retrain or move
│   └── research/
│       ├── README.md               ← preparation-only policy, protocol, limitations
│       ├── dataset_manifest.json   ← register of 4 candidate datasets, no data acquired
│       ├── prepare_dataset.py      ← CSV → eligible.jsonl / records.jsonl / audit.json
│       └── evaluate_models.py      ← scores existing models only; never trains
├── backend/
│   ├── main.py                     ← FastAPI app (343 lines)
│   └── requirements.txt            ← 6 pinned dependencies
├── research/                       ← offline pipeline that verified the 102 new claims (§4.17)
│   ├── harvest_candidates.py       ← RSS/listing discovery → candidates.tsv
│   ├── fetch_articles.py           ← fetch + extract body text → fetch logs + OS-temp cache
│   ├── split_batches.py            ← group usable articles for review
│   ├── REVIEW_INSTRUCTIONS.md      ← the rules a reviewer must follow per record
│   ├── batches/batch_NN.json       ← reviewed records + verbatim-quote provenance
│   ├── build_dataset.py            ← gates every record against cached text, merges
│   ├── validate_claims.py          ← schema, dedup, fetch-record checks on claims.json
│   ├── check_fidelity.py           ← do the numbers/nouns in a record appear in its source?
│   ├── find_near_duplicates.py     ← Jaccard similarity across claim texts
│   ├── write_research_log.py       ← regenerates claims_research_log.md from pipeline state
│   └── claims_research_log.md      ← per-record verification status, exclusions, blocked hosts
└── website/
    ├── index.html
    ├── package.json                ← react ^18.3.1, vite ^5.4.11
    ├── vite.config.js              ← port 5173 + /api proxy
    ├── public/favicon.svg
    └── src/
        ├── main.jsx                ← ReactDOM.createRoot(...).render(<App/>)
        ├── App.jsx                 ← hash router
        ├── api.js                  ← fetch wrapper
        ├── styles.css              ← design tokens + all component styles
        ├── data/claims.json        ← 114 curated claims (113 active)
        ├── components/  Header · Footer · ResultCard · StateBlocks · StatusBadge · ClaimCard · RecentFactChecks
        └── pages/       Home · Checker · Dashboard · About
```

### 1.6 What runs where ✅ Verified

| Process | Command | Address | Notes |
| --- | --- | --- | --- |
| FastAPI backend | `python -m uvicorn main:app --port 8000` (from `backend/`) | `http://localhost:8000` | Health: `GET /api/health`. Also runnable via `python backend/main.py` because of the `if __name__ == "__main__"` block at [`main.py:339`](file:///C:/FakeNewsdetector/Frontend/backend/main.py#L339) |
| Vite dev server | `npm run dev` (from `website/`) | `http://localhost:5173` | Use the hostname `localhost`, **not** `127.0.0.1` — Vite binds the IPv6 loopback on this machine |
| Production build | `npm run build` | output in `website/dist` | Static files; still needs the backend for analysis |
| Legacy Streamlit | `python -m streamlit run app.py` | default `:8501` | ⚠️ Streamlit is **not installed** in the venv; see §2.3 |

---

## 2. Technologies Actually Used

### 2.1 Confirmed stack

Every row below is backed by a file in the repo. ✅

| Technology | Version / pin | Where it is confirmed | What it does here |
| --- | --- | --- | --- |
| **Python** | 3.11 (venv at `C:\FakeNewsdetector\.venv`) | `README.md` prerequisites; `backend/__pycache__/main.cpython-311.pyc` | Backend runtime |
| **FastAPI** | pinned `fastapi==0.115.*`; **installed 0.162.0** | [`backend/requirements.txt:1`](file:///C:/FakeNewsdetector/Frontend/backend/requirements.txt#L1); imported at [`main.py:18`](file:///C:/FakeNewsdetector/Frontend/backend/main.py#L18) | HTTP API, request/response validation, automatic OpenAPI docs |
| **Uvicorn** | pinned `uvicorn[standard]==0.30.*`; **installed 0.54.0** | `backend/requirements.txt:2`; `main.py:340` | ASGI server that runs the FastAPI app |
| **Pydantic** | comes with FastAPI | `from pydantic import BaseModel` [`main.py:20`](file:///C:/FakeNewsdetector/Frontend/backend/main.py#L20); `AnalyzeRequest`, `AnalyzeResponse` | Typed request/response schemas; FastAPI rejects malformed JSON automatically |
| **scikit-learn** | pinned **exactly** `scikit-learn==1.6.1`; installed 1.6.1 | `backend/requirements.txt:3`; the pickle contains `TfidfVectorizer` + `LinearSVC` | The ML library the model was built with; needed at load time to unpickle the estimators |
| **joblib** | pinned `joblib==1.6.*`; installed 1.6.0 | `backend/requirements.txt:4`; `main.py:15`, `app.py:7` | Loads the `.pkl` pipeline (`joblib.load`) |
| **requests** | pinned `requests==2.32.*`; installed 2.34.2 | `backend/requirements.txt:5`; `main.py:16` | Fetches article HTML with timeouts, streaming and manual redirect control |
| **BeautifulSoup 4** | pinned `beautifulsoup4==4.12.*`; installed 4.15.0 | `backend/requirements.txt:6`; `from bs4 import BeautifulSoup` `main.py:17` | Parses HTML and extracts readable article text |
| **Python stdlib** | — | `pathlib`, `urllib.parse` (`urlparse`, `urljoin`), `ipaddress`, `socket` in `main.py:10-13` | Path handling and the SSRF guards |
| **React** | `^18.3.1` (+ `react-dom`) | [`website/package.json`](file:///C:/FakeNewsdetector/Frontend/website/package.json) dependencies | UI components, hooks (`useState`, `useEffect`, `useMemo`) |
| **Vite** | `^5.4.11` + `@vitejs/plugin-react ^4.3.4` | `package.json` devDependencies; `vite.config.js` | Dev server, HMR, `/api` proxy, production bundling |
| **JavaScript (ES modules, JSX)** | `"type": "module"` | all of `website/src/**` | Plain JSX — **no** router library, **no** state library, **no** UI kit |
| **CSS (hand-written)** | custom properties | [`website/src/styles.css`](file:///C:/FakeNewsdetector/Frontend/website/src/styles.css) (1,441 lines) | All theming, layout, transitions, responsive breakpoints |
| **JSON** | — | `website/src/data/claims.json`, `ml/research/dataset_manifest.json` | Curated claim data; dataset research register |
| **Node.js / npm** | developed on Node v24 (`v24.21.0` verified) | `README.md`; `package-lock.json` | Frontend tooling |

**Deliberately absent:** no TypeScript, no Redux/Zustand, no React Router, no Tailwind, no database, no Docker, no CI config, no automated tests. If asked "why not React Router?" — the app has four routes and a hash router in ~20 lines of `App.jsx`, so an extra dependency was not justified. That is a real engineering trade-off, and a good viva answer.

### 2.2 ML-specific techniques actually present ✅

| Technique | Evidence |
| --- | --- |
| **TF-IDF vectorization** with unigrams + bigrams | `TfidfVectorizer(ngram_range=(1, 2), ...)` inside the loaded pipeline (§3.4) |
| **English stop-word removal** | `stop_words='english'` |
| **Sub-linear term frequency** | `sublinear_tf=True` (uses `1 + log(tf)`) |
| **L2 normalization** of feature vectors | `norm='l2'` |
| **Vocabulary pruning** by document frequency | `min_df=2`, `max_df=0.7`, `max_features=50000` |
| **Linear Support Vector Classification** | `LinearSVC(C=1.0, loss='squared_hinge', penalty='l2', random_state=42)` |
| **Pipeline composition** | `sklearn.pipeline.Pipeline` with steps `tfidf` → `classifier` |
| **Model persistence** | joblib pickle at `ml/best_model.pkl` |

### 2.3 Present-but-unused, and mismatches you should know before the viva ⚠️

These are honest gaps. Examiners respect a candidate who knows them; they punish a candidate caught out by them.

1. **`pandas` and `numpy` are installed in the venv (pandas 3.1.0, numpy 2.4.6) but are imported nowhere in this project.** A grep across every `.py` file finds no `import pandas` / `import numpy`. They arrived as transitive dependencies of scikit-learn (numpy is required by scikit-learn and *is* used internally by the model, e.g. the sparse TF-IDF matrix and `coef_` array). **Do not claim "I used pandas for data cleaning"** — there is no such code in this repository. Correct statement: *"NumPy is used indirectly through scikit-learn; pandas is installed in the environment but not used by the application code."*
2. **`streamlit` is imported by `app.py:9` but is NOT installed in the venv.** The legacy Streamlit app therefore will not run until you `pip install streamlit` (documented in `README.md` §3).
3. **`Frontend/requirements.txt` is an empty 0-byte file.** It is a legacy placeholder. The real dependency list is `Frontend/backend/requirements.txt`.
4. **Installed versions are newer than the pins** for fastapi, uvicorn, requests and beautifulsoup4 (e.g. pin `fastapi==0.115.*`, installed `0.162.0`). Only `scikit-learn` is pinned exactly and matched exactly, because unpickling estimators across scikit-learn versions is the fragile part. The app works with the installed set (verified end-to-end), but a strict `pip install -r backend/requirements.txt` in a fresh environment would resolve to the older pins — worth mentioning if asked about reproducibility.
5. **The model artifact does not record its training scikit-learn version.** `_sklearn_version` is absent on the pipeline and on both steps, so the training version is **not recoverable from the file**. Loading it under the installed 1.6.1 produces **no warnings** (verified). Say: *"the pin to 1.6.1 is a reproducibility choice that loads cleanly; the artifact itself doesn't record its training version."*
6. **The training dataset is not in the repository, and its identity is not recorded.** `ml/research/dataset_manifest.json` states `"baseline_training_data_provenance": "UNKNOWN; evaluation overlap cannot be ruled out"`. See §3.3.

---

## 3. How the Machine Learning Works

### 3.1 The artifact — verified by loading it ✅

Loading `ml/best_model.pkl` with joblib and printing its parameters gives exactly this:

```text
object type          : sklearn.pipeline.Pipeline
steps                : [('tfidf', TfidfVectorizer(...)), ('classifier', LinearSVC(...))]
classes_             : [0, 1]
vocabulary size      : 50,000 terms
classifier.n_features_in_ : 50,000
coef_.shape          : (1, 50000)     ← one weight vector: binary, one-vs-rest
intercept_.shape     : (1,)
has predict_proba    : False          ← IMPORTANT (see §3.6)
has decision_function: True
file size            : 2,443,296 bytes (~2.33 MB)
sample vocabulary    : '00', '00 mark', '00 pm', '000', '000 000', '000 according', ...
```

The sample tokens prove the bigram setting is real: single words (`'000'`) and two-word phrases (`'000 according'`) both appear in the vocabulary.

**TfidfVectorizer parameters (verbatim from the artifact):**

```python
analyzer='word', lowercase=True, token_pattern='(?u)\\b\\w\\w+\\b',
stop_words='english', ngram_range=(1, 2),
min_df=2, max_df=0.7, max_features=50000,
sublinear_tf=True, use_idf=True, smooth_idf=True, norm='l2',
input='content', encoding='utf-8', decode_error='strict', dtype=numpy.float64
```

**LinearSVC parameters (verbatim from the artifact):**

```python
C=1.0, loss='squared_hinge', penalty='l2', dual='auto',
fit_intercept=True, intercept_scaling=1, class_weight=None,
multi_class='ovr', max_iter=1000, tol=0.0001, random_state=42, verbose=0
```

### 3.2 Labels and the mapping ✅

The model's `classes_` is `[0, 1]`, and both the backend and the Streamlit app map them identically:

```python
LABEL_VERDICTS = {0: "Potentially Fake", 1: "Potentially Real"}   # backend/main.py:34
```

`app.py` uses explicit branches instead ([`app.py:408-419`](file:///C:/FakeNewsdetector/Frontend/app.py#L408)) but produces the same strings. Both paths also **reject any other label** and raise an error rather than silently mislabelling — a nice defensive detail to mention.

The word "Potentially" is intentional and load-bearing: it is the product's honesty mechanism.

### 3.3 Training data: what is known and what is not ⚠️

| Question | Answer | Source |
| --- | --- | --- |
| What dataset was it trained on? | **Not recorded.** "baseline_training_data_provenance": "UNKNOWN" | [`dataset_manifest.json:98`](file:///C:/FakeNewsdetector/Frontend/ml/research/dataset_manifest.json#L98) |
| Is the dataset in the repo? | No. Only the model artifact. | file listing ✅ |
| How many training samples? | **Unknown** — not stored in the pickle | introspection ✅ |
| Class balance? | **Unknown** | — |
| Language? | The vectorizer uses `stop_words='english'` and an English token pattern, so the features are English-oriented. The research register's scope for *future* work is "English Indian news". | artifact + manifest |
| Train/validation/test split used at training time? | **Not documented anywhere in this project.** | ⚠️ |
| Which scikit-learn version trained it? | **Not recorded** (`_sklearn_version` absent) | introspection ✅ |
| What is measured accuracy? | **No metric is recorded anywhere in this repo.** | ⚠️ |

Be direct about this in the viva: *"The model was supplied as a pre-trained artifact for this project. I integrated it, verified its interface and parameters by loading it, and built the serving stack around it. Its training corpus and original scores are not documented, so I don't quote numbers for it — instead I built an evaluation protocol so scores can be produced honestly later."* That last clause is true and points at `ml/research/evaluate_models.py`.

### 3.4 Text preprocessing, step by step

`model.predict([text])` runs the whole chain internally. Here is what happens to a raw article:

1. **Tokenization** — `token_pattern=r'(?u)\b\w\w+\b'` extracts sequences of **two or more** word characters. Single letters are dropped; punctuation and whitespace act as separators.
2. **Lowercasing** — `lowercase=True`, so "Government" and "government" are the same feature. This is why the model is case-insensitive.
3. **Stop-word removal** — `stop_words='english'` drops ~318 common English words (the, and, of, is…). Rationale: they carry almost no discriminative signal for topic/style and would dominate raw counts.
4. **N-gram generation** — `ngram_range=(1, 2)` produces every single token *and* every adjacent token pair. Bigrams let the model learn phrases ("shock ing", "officials confirm", "viral video") that individual words cannot express. This roughly squares the candidate feature space, which is why step 5 matters.
5. **Vocabulary filtering** —
   - `min_df=2`: a term must appear in **at least 2 documents**, else it is dropped. Kills typos, one-off names and noise; also shrinks the model.
   - `max_df=0.7`: a term appearing in **more than 70 % of documents** is dropped. Such terms cannot separate the classes.
   - `max_features=50000`: keep only the 50,000 highest-frequency surviving terms, ordered by corpus frequency. This caps memory and training time — verified as the final vocabulary size.
6. **Term frequency with sub-linear scaling** — `sublinear_tf=True` replaces raw count `tf` with `1 + log(tf)`. Rationale: a word repeated 50 times is not 50× as meaningful as one appearing once; log scaling damps keyword stuffing and length effects.
7. **Inverse document frequency** — `use_idf=True`, `smooth_idf=True`:
   `idf(t) = ln((1 + n) / (1 + df(t))) + 1`, where `n` = number of training documents and `df(t)` = documents containing `t`. Rare terms get high weight, ubiquitous terms get low weight. Smoothing avoids division by zero.
8. **L2 normalization** — `norm='l2'`: each document vector is scaled to unit length, so **document length stops mattering**. A 200-word article and a 5,000-word article become comparable. This is essential because inputs here range from 30 characters to 20,000 characters.
9. The result is a **sparse matrix** of shape `(n_documents, 50000)` fed to the classifier.

### 3.5 TF-IDF in one formula (be ready to write this on paper)

```
tfidf(t, d) = (1 + log tf(t,d))  ×  [ ln((1 + n) / (1 + df(t))) + 1 ]      then L2-normalize the row
              └── sublinear_tf ──┘   └──────────── smooth_idf ────────────┘
```

**Intuition to say out loud:** TF-IDF converts text into numbers by asking *"which words are unusually important in this document compared with the whole corpus?"* It is a **bag-of-words** model: word *order* is discarded except inside bigrams. There is no grammar, no semantics, no world knowledge.

**Why TF-IDF and not deep learning here?** Fast to train and to predict (milliseconds on CPU), tiny (2.3 MB vs. hundreds of MB for a transformer), fully interpretable (you can inspect the 50,000 weights and list the most "fake-flavoured" and most "real-flavoured" terms), needs no GPU, and is a strong published baseline for text classification. Excellent viva answer.

### 3.6 LinearSVC — what the classifier actually computes

`LinearSVC` fits a **maximum-margin linear hyperplane** in the 50,000-dimensional TF-IDF space by minimizing the **squared hinge loss** with **L2 regularization**:

```
minimize over w, b:   (1/2)‖w‖²  +  C · Σᵢ max(0, 1 − yᵢ(w·xᵢ + b))²
```

- `w` = `coef_`, shape `(1, 50000)` — one weight per vocabulary term. Because `classes_ = [0, 1]` and `multi_class='ovr'`, binary classification needs only **one** separating hyperplane: `w·x + b > 0` → class 1, otherwise class 0.
- `b` = `intercept_`, shape `(1,)`.
- `C = 1.0` — the regularization strength (inverse). Small `C` → wider margin, more regularization, simpler model; large `C` → fewer training errors allowed, higher overfitting risk. `C=1.0` is scikit-learn's default.
- `penalty='l2'` — penalizes the squared magnitude of weights; spreads weight across many correlated terms instead of collapsing onto a few. It does **not** produce exact zeros, so it does not do feature *selection* (that would be `l1`).
- `loss='squared_hinge'` — the hinge loss squared; smooth and differentiable, which lets the solver converge faster than plain hinge.
- `dual='auto'` — the solver picks the primal or dual formulation based on the shape of the data. With `n_samples ≫ n_features` the primal is preferred; here features (50,000) likely exceed samples, so the dual is typical.
- `max_iter=1000`, `tol=1e-4` — stopping criteria for the liblinear solver.
- `random_state=42` — fixes the seed so any future retraining is reproducible.
- `class_weight=None` — no re-weighting for class imbalance was applied. ⚠️ Since the class balance is unknown, this is a limitation worth naming: if the training set was imbalanced, the model is biased toward the majority class.

**Why the UI shows no percentage — the `predict_proba` point.**
`LinearSVC` has **no `predict_proba`** (verified: `hasattr(model, 'predict_proba') == False`). It only has `decision_function`, which returns the signed distance from the hyperplane — an unbounded real number, **not a probability**. Converting it to a probability would require extra calibration (e.g. `CalibratedClassifierCV` with Platt scaling or isotonic regression), which was not applied. That is precisely why the product shows a **label plus a disclaimer** rather than "87 % fake" — and it is the honest design. If you ever want confidence numbers, calibrating a wrapper around the SVC is the correct future step (🔜).

**Why linear and not an RBF kernel?** With 50,000 sparse text features, a linear boundary is the standard, well-performing choice; kernel methods are far more expensive and prone to overfitting on high-dimensional sparse bags-of-words.

### 3.7 Train / validation / test split ⚠️ Not documented — but a protocol exists

**No split from the original training run is recorded in this project.** Do not describe one as if it happened.

What *does* exist is a rigorous **evaluation protocol** for the future phase, in [`ml/research/evaluate_models.py`](file:///C:/FakeNewsdetector/Frontend/ml/research/evaluate_models.py). Understanding it is a strong viva differentiator, because it shows awareness of **data leakage** — the classic mistake in fake-news classification:

- **`make_groups()`** builds *transitive* groups using a `UnionFind` (disjoint-set) structure. Two records land in the same group if they share an exact normalized-text SHA-256 hash, an `event_group`, or a `syndication_group`. Rationale: the same story republished by ten outlets is **one** story; if nine copies train and one tests, your test score is meaningless.
- **`split_group_holdout()`** holds out ~20 % of records **by whole group**, never splitting a group across train and test. Group order is fixed by hashing group IDs, so the split is deterministic and reproducible.
- **`split_source_holdout()`** holds out an entire **source** (`source_name`) to measure generalization to an unseen publisher. It then removes any group that touches more than one source, or has an unknown source, from **both** sides — contaminated records are excluded rather than allowed to leak.
- Both splits are explicitly labelled **diagnostic only** and are **not stratified**; the report includes class counts so the reader can judge.
- The report hard-codes its own honesty: `"independent_indian_test_set": "not_provided"`, `"metrics_are_independent_indian_evidence": False`, `"baseline_training_data_overlap": "unknown; scores may overlap baseline training data"`.

### 3.8 Metrics: what was measured (nothing yet) and how to answer that question

> ⚠️ **There is no confusion matrix, accuracy, precision, recall or F1 score recorded anywhere in this repository.** No metrics JSON exists; `evaluate_models.py` writes to a caller-supplied `--output` path and has not been run here (running it requires separate approval and prepared data that has not been acquired).

**What you should say if asked "what's your accuracy?":**

> "I can't quote a number honestly. The model came to this project as a pre-trained artifact and its original evaluation isn't documented, so any figure I gave would be invented. What I did instead was define the evaluation protocol — macro precision, recall and F1, per-class values, and a confusion matrix — plus leakage-safe splits, in `ml/research/evaluate_models.py`. Producing a real number requires an authorized dataset and a run of that script, which is the next phase of the project."

That answer demonstrates integrity *and* technical command. Memorize it.

**The metric definitions you must still know cold** (the protocol uses all of them):

*Confusion matrix* — rows = true class, columns = predicted class. In this project's convention (`labels=[0, 1]`, class order `["fake", "real"]`):

|  | predicted **fake** (0) | predicted **real** (1) |
| --- | --- | --- |
| **actually fake** (0) | TN-style: correctly caught fake | FN: fake news missed ← **most dangerous error** |
| **actually real** (1) | FP: real news smeared as fake | TP-style: correctly passed real |

*(With fake = class 0 the usual TN/TP naming flips, which is exactly why the script stores the matrix plus an explicit `class_order` instead of relying on names.)*

```
Accuracy  = (correct predictions) / (all predictions)
Precision = TP / (TP + FP)     "of everything I flagged, how much was really that class?"
Recall    = TP / (TP + FN)     "of everything that really was that class, how much did I catch?"
F1        = 2 · P · R / (P + R)   harmonic mean — punishes lopsided P/R
Macro avg = compute the metric per class, then take the unweighted mean
```

**Why macro and not accuracy?** Because accuracy is misleading under class imbalance — a model that always says "real" scores 95 % on a 95/5 dataset while catching zero fake news. Macro-F1 forces the model to be good on *both* classes. Say this; it is the single best metrics answer in a fake-news viva.

**Which error is worse here?** A **false positive** (real journalism labelled "Potentially Fake") can unjustly damage a credible outlet and is the reason the UI says *potentially* and never *fake*. A **false negative** (fake news labelled "Potentially Real") lets misinformation through with an implied endorsement. The product mitigates both with disclaimers and by pointing users to the human-reviewed dashboard — a design decision worth highlighting.

### 3.9 Model limitations (technical)

1. **Bag-of-words**: word order beyond bigrams is invisible. Sarcasm, negation ("did **not** happen") and paraphrase are poorly handled.
2. **Style, not truth**: it can be fooled by a well-written fabrication and can flag a sensational but true story.
3. **Vocabulary bound to training era**: `max_df=0.7`, `min_df=2` and a 50,000-term cap mean new events, new names and new slang are simply out-of-vocabulary and contribute nothing.
4. **Unknown provenance ⇒ unknown generalization**: without knowing the training corpus, performance on Indian news, on 2026 news, or on non-English text cannot be claimed.
5. **No probabilities**: uncalibrated `decision_function` only; no reliable confidence to threshold on.
6. **Possible class imbalance**: `class_weight=None` and unknown balance.
7. **Leakage risk**: near-duplicate stories across train/test can inflate any future score; the research scripts address this but have not been run.
8. **Truncation**: inputs are cut to 20,000 characters (`MAX_ARTICLE_CHARS`), so very long articles are only partly read.
9. **Static artifact**: no retraining pipeline, no drift monitoring.

---

## 4. Code Walkthrough, File by File

### 4.1 `Frontend/app.py` — the legacy Streamlit app (549 lines)

Same classifier, same guards, single file, no API. Useful to show the project's evolution.

| Lines | What is there |
| --- | --- |
| 2–10 | Imports: `pathlib.Path`, `urlparse`, `ipaddress`, `socket`, `joblib`, `requests`, `streamlit as st`, `BeautifulSoup` |
| **15** | `MODEL_PATH = Path(__file__).parent / "ml" / "best_model.pkl"` — relative to the file, so it works from any CWD |
| 17–21 | `st.set_page_config(page_title="AI Fake News Detector", page_icon="🔎", layout="wide")` |
| 26–111 | Injected CSS (light blue theme — the *old* look; the React site uses the new dark palette) |
| **116–124** | `@st.cache_resource def load_model()` — loads the pickle **once** per process and caches it; raises `FileNotFoundError` with a helpful path message if missing |
| **129–158** | `validate_public_url(url)` — the SSRF guard (see §4.3) |
| **163–303** | `extract_article(url)` — returns `(title, article_text, hostname)` |
| 308–317 | Page header markdown |
| 319 | `left, right = st.columns([1, 1], gap="large")` — two-column layout |
| 332–336 | `st.radio("Choose input method", ["News Text", "Article URL"], horizontal=True)` |
| 342–352 | `st.text_area(..., max_chars=20000)` + caption warning against personal data |
| 355–365 | `st.text_input` for the URL + `st.info` explaining extraction can fail |
| 367 | `analyze = st.button("Analyze story", type="primary")` |
| 378–379 | Initializes `st.session_state.screening_result = None` — Streamlit reruns the whole script on every interaction, so results must live in session state |
| 381–437 | Text branch: validation (empty / `< 30` chars), then `model.predict([article])[0]`, mapping 0→"Potentially Fake", 1→"Potentially Real", else raising on an unexpected label |
| 439–493 | URL branch: `extract_article(url)` → `model.predict([article_text])[0]`; stores `title`, `hostname`, `article_text` in the result dict |
| 498–539 | Result panel: `st.info` (nothing yet), `st.error` (error or fake), `st.success` (real), plus an `st.expander("View extracted article text")` |
| **544–549** | Site-wide disclaimer caption: *"…does not establish whether a claim is true or false. Always verify important news using reliable independent sources."* |

### 4.2 `Frontend/ml/best_model.pkl`

- 2,443,296 bytes; a joblib-serialized `Pipeline` of `TfidfVectorizer` → `LinearSVC`. Full parameters in §3.1.
- **Loaded server-side only.** No code path exposes the file to the browser: Vite serves `website/`, the pickle lives in `ml/`, and the API returns only a label, a verdict string, a disclaimer and metadata. This matters both for security (model extraction) and for size (2.3 MB never ships to the client).
- **Do not retrain, move or rename it.** Both `app.py:15` and `backend/main.py:22` resolve `ml/best_model.pkl` (lowercase) relative to their own location.

### 4.3 `Frontend/backend/main.py` — the FastAPI backend (342 lines)

**Configuration block**

| Line | Name | Value / role |
| --- | --- | --- |
| 22 | `MODEL_PATH` | `Path(__file__).resolve().parent.parent / "ml" / "best_model.pkl"` |
| 24 | `DISCLAIMER` | The screening-not-fact-check sentence attached to **every** response |
| 30 | `MAX_ARTICLE_CHARS` | `20000` — truncation cap |
| 31 | `MIN_ARTICLE_CHARS` | `100` — minimum extracted text |
| 32 | `MIN_INPUT_CHARS` | `30` — minimum pasted text |
| 34 | `LABEL_VERDICTS` | `{0: "Potentially Fake", 1: "Potentially Real"}` |
| 36 | `app` | `FastAPI(title="Fake News Analyzer API", version="1.0.0")` |
| 38–46 | CORS middleware | allows `http://localhost:5173` and `http://127.0.0.1:5173`, methods `GET`/`POST`, header `Content-Type` |
| 48 | `_model` | module-level cache, initially `None` |

**`get_model()` (line 51)** — lazy singleton. On first call it checks `MODEL_PATH.is_file()` (503 with a fix-it message if absent), then `_model = joblib.load(MODEL_PATH)`. Subsequent calls return the cached object. *Why:* unpickling 2.3 MB and rebuilding the vectorizer on every request would add needless latency; loading at import time would slow startup and make failures harder to report. This mirrors `@st.cache_resource` in `app.py`.

**Pydantic schemas**

```python
class AnalyzeRequest(BaseModel):      # line 66
    text: str | None = None
    url:  str | None = None

class AnalyzeResponse(BaseModel):     # line 71
    label: int
    verdict: str
    disclaimer: str
    input_mode: str                   # "text" | "url"
    source_title:    str | None = None
    source_hostname: str | None = None
    extracted_chars: int | None = None
```

FastAPI validates these automatically: a non-JSON body or a wrong type returns `422` before your code runs, and `response_model=AnalyzeResponse` filters the output to exactly these fields.

**`validate_public_url(url)` (line 81)** — the SSRF defence. It raises `HTTPException(422, ...)` when:

1. scheme is not `http`/`https`, or there is no hostname → *"Enter a valid URL beginning with http:// or https://."*
2. `parsed.username` or `parsed.password` is set → embedded credentials rejected (`http://user:pass@host`)
3. hostname is `localhost` or ends with `.local`
4. `socket.getaddrinfo(hostname, None)` fails (`socket.gaierror`) → *"The website hostname could not be resolved."*
5. **any** resolved address fails `ipaddress.ip_address(...).is_global` → *"Private or non-public network addresses are not allowed."*

*Why this matters (great viva material):* without it, a user could submit `http://169.254.169.254/…` (cloud metadata), `http://127.0.0.1:8000/api/health` (the server itself), or `http://192.168.1.1` (the local router) and turn your server into a proxy for attacking internal networks. Checking **all** addresses returned by DNS also blocks DNS-rebinding-style tricks where a public-looking hostname resolves to a private IP. Note the guard is re-applied to **every redirect hop**, not just the first URL.

**`fetch_html(url)` (line 123)** → `(final_url, html)`

- Loop of at most **6** iterations; `validate_public_url(current_url)` at the top of each.
- `requests.get(..., headers={"User-Agent": "Mozilla/5.0 …Chrome/124.0 Safari/537.36"}, timeout=(5, 15), allow_redirects=False, stream=True)`.
  - `timeout=(5, 15)` = 5 s connect / 15 s read — prevents a hung server from blocking the worker.
  - `allow_redirects=False` + manual handling is what makes per-hop validation possible.
  - `stream=True` = body is not downloaded until iterated, enabling the size cap.
  - A browser-like `User-Agent` avoids trivial bot blocking.
- Redirects: `urljoin(current_url, location)` resolves relative `Location` headers; the `for … else` clause raises *"Too many website redirects."*
- `status_code >= 400` → 502 with the actual status.
- `Content-Type` must contain `text/html` or `text/plain` → otherwise 502 (stops someone pointing the server at a 2 GB video).
- Body is read in `chunk_size=16384` pieces with `max_bytes = 2_000_000`; exceeding it raises *"The webpage is too large to process safely."*
- Decoded with `response.encoding or "utf-8"` and `errors="replace"` so malformed bytes cannot crash the request.
- Any `requests.RequestException` becomes **502** (upstream fault), never a 500 — correct HTTP semantics: the *other* site failed.

**`extract_article(url)` (line 214)** → `(title, article_text, hostname)`

```python
soup = BeautifulSoup(html, "html.parser")
title = soup.title.get_text(" ", strip=True) if soup.title else ""
# strip non-content elements:
for element in soup(["script","style","nav","footer","header","aside","form","noscript","svg"]):
    element.decompose()
container = soup.find("article") or soup.find("main") or soup.find(attrs={"role":"main"}) or soup.body or soup
paragraphs = [el.get_text(" ", strip=True) for el in container.find_all(["p","h1","h2","h3"])]
article_text = "\n\n".join(p for p in paragraphs if p)
if len(article_text.strip()) < MIN_ARTICLE_CHARS:      # paragraph heuristic failed
    article_text = container.get_text(" ", strip=True) # fall back to all container text
article_text = article_text.strip()[:MAX_ARTICLE_CHARS]
if len(article_text) < MIN_ARTICLE_CHARS: raise HTTPException(422, "Could not extract enough article text…")
```

The `article → main → role=main → body → soup` chain is a graceful-degradation ladder for messy real-world HTML. `decompose()` physically removes boilerplate so nav/footer text cannot pollute the prediction. The 422 on too-little text tells the user to paste the article instead — an actionable error, not a crash.

**`run_screening(article)` (line 265)** → `(label, verdict)`

```python
model = get_model()
prediction = int(model.predict([article])[0])   # predict takes a LIST of documents
if prediction not in LABEL_VERDICTS: raise HTTPException(500, f"Unexpected model label: {prediction}")
return prediction, LABEL_VERDICTS[prediction]
```

Any other exception becomes `HTTPException(500, "Model analysis failed (<ExceptionType>).")` — note it leaks only the exception *class*, not the traceback, which keeps internal details out of responses.

**Endpoints**

```python
@app.get("/api/health")           # line 286
def health(): return {"status": "ok", "model_loaded": MODEL_PATH.is_file(), "labels": LABEL_VERDICTS}
```
Cheap liveness probe; the React home page calls it to render the online/offline pill. `model_loaded` reports file presence, not a successful load.

```python
@app.post("/api/analyze", response_model=AnalyzeResponse)   # line 295
def analyze(request: AnalyzeRequest):
    has_text = bool(request.text and request.text.strip())
    has_url  = bool(request.url  and request.url.strip())
    if has_text == has_url:                 # both, or neither
        raise HTTPException(422, "Provide exactly one of: article text or an article URL.")
    if has_text:
        article = request.text.strip()
        if len(article) < MIN_INPUT_CHARS: raise HTTPException(422, f"Please provide at least {MIN_INPUT_CHARS} characters…")
        label, verdict = run_screening(article[:MAX_ARTICLE_CHARS])
        return AnalyzeResponse(label=label, verdict=verdict, disclaimer=DISCLAIMER,
                               input_mode="text", extracted_chars=len(article))
    title, article_text, hostname = extract_article(request.url)
    label, verdict = run_screening(article_text)
    return AnalyzeResponse(label=label, verdict=verdict, disclaimer=DISCLAIMER, input_mode="url",
                           source_title=title or None, source_hostname=hostname or None,
                           extracted_chars=len(article_text))
```

`has_text == has_url` is a compact XOR test: it is true when both are present *or* both absent, and either way the request is ambiguous. Note the server truncates with `article[:MAX_ARTICLE_CHARS]` **before** predicting but reports `extracted_chars=len(article)` — the client sees how much was supplied.

**`if __name__ == "__main__"` (line 339)** — `uvicorn.run(app, host="127.0.0.1", port=8000)`, a convenience so `python main.py` also works. Binding to loopback only means the API is not exposed on the network by default — a sensible secure default worth mentioning.

### 4.4 `website/vite.config.js`, `index.html`, `main.jsx`

```js
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } } },
});
```

The proxy is the reason the frontend can call `/api/analyze` with a **relative** URL: the browser talks only to `:5173`, Vite forwards `/api/*` to `:8000`. Same-origin from the browser's perspective ⇒ no CORS preflight in development, and no hard-coded host in the code (so a production deployment can point `/api` anywhere via its own reverse proxy).

`main.jsx` is the entry point: `ReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)` plus `import './styles.css'`. `StrictMode` double-invokes effects in development, which is why `Home.jsx` uses an `alive` flag to avoid setting state after unmount.

### 4.5 `website/src/App.jsx` — a 20-line hash router

```jsx
const ROUTES = { '/': Home, '/checker': Checker, '/about': About, '/dashboard': Dashboard };

function currentPath() {
  const hash = window.location.hash.replace(/^#/, '');
  return hash || '/';
}

const [path, setPath] = useState(currentPath());
useEffect(() => {
  const onHashChange = () => setPath(currentPath());
  window.addEventListener('hashchange', onHashChange);
  return () => window.removeEventListener('hashchange', onHashChange);   // cleanup prevents leaks
}, []);
useEffect(() => { window.scrollTo(0, 0); }, [path]);                     // new page starts at top

const Page = ROUTES[path] || Home;                                       // unknown route → Home
return (<div className="app-shell"><Header path={path} />
          <main className="main-content"><div className="page-enter" key={path}><Page /></div></main>
          <Footer /></div>);
```

Points to make: `key={path}` forces React to **unmount and remount** the page on navigation, which restarts the CSS `page-in` animation — a one-attribute transition effect. Hash routing needs no server rewrite rules (works from static hosting and from `file://`-style previews), unlike path routing which 404s on refresh without configuration. `Header` receives `path` so it can mark the active link.

### 4.6 `website/src/api.js` — the single network boundary

```js
const API_BASE = '/api';

async function request(path, options = {}) {
  let response;
  try { response = await fetch(`${API_BASE}${path}`, options); }
  catch { throw new Error('Could not reach the analysis backend. Make sure the FastAPI server is running on port 8000.'); }

  let data = null;
  try { data = await response.json(); } catch { /* non-JSON body */ }

  if (!response.ok) {
    const detail = data && data.detail ? data.detail : `Request failed (HTTP ${response.status}).`;
    throw new Error(detail);
  }
  return data;
}

export function analyzeText(text) { return request('/analyze', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ text }) }); }
export function analyzeUrl(url)   { return request('/analyze', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ url }) }); }
export function checkHealth()     { return request('/health'); }
```

Why this design is worth explaining:

- `fetch` **does not reject** on 4xx/5xx — it only rejects on network failure. So the wrapper distinguishes the two cases: the first `try/catch` means "server unreachable", the `!response.ok` branch means "server answered with an error".
- It surfaces FastAPI's `detail` field, so the **exact** backend message ("Private or non-public network addresses are not allowed.") reaches the user instead of a generic "Error 422".
- The JSON parse is defensively wrapped because a proxy or a 500 page can return HTML.
- Every component uses these three functions; no component calls `fetch` directly. One place to change auth, base URL or retries later.

### 4.7 `website/src/pages/Home.jsx` + `components/RecentFactChecks.jsx`

`const [backend, setBackend] = useState('checking')` with a `useEffect` that calls `checkHealth()` and sets `'online'` / `'offline'`; the `alive` flag prevents a state update after unmount. The result drives `<div className={`backend-pill ${backend}`} role="status">` with three messages — an instant, honest indicator of whether analysis will work. The page also has a `hero`, two CTA buttons (`#/checker`, `#/dashboard`), the `<RecentFactChecks />` strip, one `feature-grid single` card ("Paste or link") and the `notice-band` limitations statement.

The homepage is deliberately **reader-facing**: everything that explains *how the project was built* (TF-IDF, LinearSVC, the curated-dataset process) lives on the About page instead. The only implementation detail on Home is the one-liner that tells a first-time visitor what to do.

`RecentFactChecks` is the one component that reads `data/claims.json` besides `Dashboard.jsx`, and it reads it directly at module scope — so a weekly dataset edit surfaces on the homepage with **no component change**:

```jsx
const SHOW = 8;
const STATUS_RANK = { false: 0, misleading: 1, verified: 2, unverified: 3 };
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

recencyDate(claim)   // later of added_date / review_date, '' if neither is ISO
selectRecent(claims) // drop archived + blank claims → sort by status rank, then date desc, then id → slice(0, 8)
displayedDate(claim) // "Added: <date>" → else "Reviewed: <date>" → else "Date not recorded"
evidenceUrl(claim)   // first evidence entry whose url is http(s), else null → no link rendered
```

- Status rank comes first so established-false and misleading stories lead; the date break the tie, so a re-reviewed record resurfaces automatically.
- A missing or malformed date never throws and never pretends to be recent: it sorts last and prints "Date not recorded". Verified with a throwaway fixture (empty `added_date`, `null`, `29/10/2026`, `recently`), then `claims.json` was restored byte-identical.
- `role="region"` + `aria-label` + `tabIndex="0"` makes the strip itself a keyboard-reachable scroll area; `‹` / `›` are real `<button>`s with `aria-label`s that disable at each end (with a 4 px tolerance, because scroll-snap settles on fractional pixels), and `nudge()` scrolls by exactly one card + gap.
- `behavior: 'smooth'` is downgraded to `'auto'` when `prefers-reduced-motion: reduce` matches — CSS cannot affect JS scrolling, so the check has to live in JS.
- No auto-play and no timer: nothing moves unless the reader moves it.
- `recent.length === 0` renders the shared `<EmptyBlock>` instead of a strip, and the controls are hidden with it.
- The `recent-note` line states the boundary in the reader's terms: these are human-reviewed fact-checks, not model predictions.

### 4.8 `website/src/pages/Checker.jsx` — the core UI

```jsx
const MIN_TEXT = 30;                                    // mirrors backend MIN_INPUT_CHARS
const [mode, setMode] = useState('text');               // 'text' | 'url'
const [text, setText] = useState('');
const [url, setUrl]     = useState('');
const [loading, setLoading] = useState(false);
const [result, setResult]   = useState(null);
const [error, setError]     = useState(null);

const canSubmit = !loading && (mode === 'text' ? text.trim().length >= MIN_TEXT : url.trim().length > 0);

async function handleSubmit(event) {
  event.preventDefault();                               // stop the full-page reload
  if (!canSubmit) return;
  setLoading(true); setError(null); setResult(null);
  try { setResult(mode === 'text' ? await analyzeText(text.trim()) : await analyzeUrl(url.trim())); }
  catch (err) { setError(err.message); }
  finally { setLoading(false); }                        // runs on success AND failure
}

function switchMode(next) { setMode(next); setResult(null); setError(null); }   // no stale results across modes
```

UI structure: a `mode-toggle` with `role="tablist"` and `aria-selected` on each tab; in text mode a `<textarea maxLength={20000}>` with a live `{text.trim().length.toLocaleString()} / 20,000 characters` hint; in URL mode `<input type="url">` (free browser format validation) plus a note that some sites block automated access; then the submit button whose label swaps to "Analyzing…" while `loading` and which is `disabled={!canSubmit}`.

The result panel renders **exactly one** of four states — the state machine examiners like to see:

| Condition | Rendered |
| --- | --- |
| `loading` | `<Spinner />` ("Running the screening model…", `role="status"`) |
| `error` | `<ErrorBlock message={error} onRetry={…} />` (`role="alert"` + Try again) |
| nothing yet | `<EmptyBlock title="No analysis yet" … />` |
| `result` | `<ResultCard result={result} />` |

Below it, a `type-legend` explains how to read a result and links to `#/dashboard`, explicitly separating "unverified" from "established as false".

**Client + server validation is duplicated on purpose.** `MIN_TEXT = 30` in the browser gives instant feedback and keeps the button disabled; `MIN_INPUT_CHARS = 30` on the server is the *actual* security boundary, because anyone can call the API directly with `curl`. Never trust client-side validation — say this line.

### 4.9 `website/src/pages/Dashboard.jsx` — filtering with `useMemo`

```jsx
const STATUS_ORDER = ['unverified', 'misleading', 'false', 'verified'];       // least → most certain
const PAGE_SIZE = 24;
const SUMMARY_CARDS = [ {key:'total',label:'Active reviewed'}, {key:'unverified',…}, {key:'misleading',…}, {key:'false',…}, {key:'verified',…} ];

const claims = claimData.claims;                        // static JSON import — bundled at build time
const categories   = useMemo(...)   // 'all' + sorted unique claim.category values
const counts       = useMemo(...)   // { total, unverified, misleading, false, verified } — SKIPS archived
const lastReviewed = useMemo(...)   // max review_date among non-archived, else '—'
const filtered     = useMemo(...)   // archive → status → category → text search, then sort desc by review_date|added_date
const listSignature = `${query}|${status}|${category}|${sort}|${showArchived}`;

useEffect(() => { setVisible(PAGE_SIZE); }, [listSignature]);   // back to page 1 on any filter change
const shown       = filtered.slice(0, visible);
const hiddenCount = filtered.length - shown.length;
```

- `counts` skips archived entries (`if (claim.archived) continue;`), so the summary cards always describe the **active** set. Every number on the page is computed from the dataset at render time — nothing is hard-coded, which is exactly what makes the cards trustworthy.
- The search matches against `claim.claim`, `claim.explanation` **and** `claim.why_misleading`, all lower-cased.
- Sorting is descending string comparison on ISO dates (`YYYY-MM-DD`), which sorts correctly as plain text — a small but genuinely useful trick.
- `useMemo` recomputes only when its dependency array changes, so typing in the search box does not re-derive `categories` or `counts` on every keystroke.
- The summary cards are `<button>`s, not `<div>`s: clicking one toggles the matching status filter (`card.key === 'total'` resets to `'all'`), and the active one gets the `active` class. Keyboard-accessible by construction.
- `key={listSignature}` on `.claim-grid` remounts the grid whenever filters change, replaying the CSS fade-in — the same technique as `App.jsx`.
- **Pagination is a `visible` count, not a page number.** With 113 active records, mounting every card at once makes the first paint heavy, so the grid renders `filtered.slice(0, visible)` and a `Show {Math.min(PAGE_SIZE, hiddenCount)} more` button increments `visible` by `PAGE_SIZE`. The button disappears when `hiddenCount === 0`, and the `useEffect` on `listSignature` resets `visible` so a filter change never leaves you staring at page 3 of a 2-result list. A `claim-more-count` line always states "Showing N of M matching claims", so the truncation is visible rather than silent.
- The `dashboard-meta` line shows dataset `last_updated`, `lastReviewed`, and `Archived entries: {claims.length - counts.total}`.
- `filtered.length === 0` renders `<EmptyBlock title="No matching claims" …/>` instead of an empty grid.
- The `update-band` `<ol>` documents the six-step weekly workflow **in the UI itself**, and the `dataset-note` renders four live `<StatusBadge>` components next to their definitions — the vocabulary is explained with the real components, so it can never drift from the code.

### 4.10 `website/src/pages/About.jsx`

Seven numbered `about-card` blocks, in the order a first-time reader asks questions: **01 What is Fake News Analyzer?**, **02 Why did we build it?**, **03 How does it work?**, **04 The machine-learning model and technology used**, **05 How the fact-check dashboard works**, **06 Screening result vs. verified fact-check** (a two-column `compare-grid`: "A checker result" against "A dashboard record"), **07 Limitations and responsible use** — plus a `notice-band` titled *"Use it as a first pass."*.

Cards 04 and 05 absorb the technical copy that used to sit on the homepage, so nothing was deleted in the redesign, only relocated: card 04 is the ready-made 30-second project summary (labelled dataset → TF-IDF uni- and bi-grams → linear SVM → pipeline saved as `ml/best_model.pkl` → loaded once by FastAPI → browser never touches the model file, and no probability is output), and card 05 explains the curated dashboard with a live `{activeClaims}` count from `claims.json` plus four real `<StatusBadge>` components next to their definitions, so the vocabulary can never drift from the code. The "Unverified is not false" rule and the pattern-vs-truth disclaimer are both stated here in plain language.

### 4.11 Components

**`Header.jsx`** — `LINKS` array (`/` Home, `/checker` News Checker, `/dashboard` Claim Dashboard, `/about` About Project) rendered as `href={`#${link.to}`}`; the active link gets `nav-link active` by comparing against the `path` prop. A `nav-toggle` button with `aria-label`/`aria-expanded` and three `<span>` bars drives `open` state for the mobile menu; every link click calls `setOpen(false)`.

**`Footer.jsx`** — the site-wide disclaimer plus `Fake News Analyzer · React + FastAPI + scikit-learn`.

**`ResultCard.jsx`** — `const isFake = result.label === 0;` picks the `result-fake`/`result-real` class; header shows 🚩 or 📰 with `result.verdict`; for `input_mode === 'url'` it renders `result.source_title` and `result.source_hostname`; then `result.disclaimer`; then `{result.extracted_chars.toLocaleString()} characters analysed` when present. Note it trusts the backend's `verdict` and `disclaimer` strings rather than re-deriving them — one source of truth.

**`StateBlocks.jsx`** — three stateless components: `Spinner` (`role="status"`, CSS `.spinner`), `ErrorBlock({ message, onRetry })` (`role="alert"`, ⚠ icon, optional Try again button), `EmptyBlock({ title, message })`. The ARIA roles make loading and errors announceable by screen readers.

**`StatusBadge.jsx`** — two lookup maps, `LABELS` and `CLASSES`, over the four statuses:

```js
false      → "False per cited evidence"  / status-badge status-false
misleading → "Misleading framing"        / status-badge status-misleading
unverified → "Unverified claim"          / status-badge status-unverified
verified   → "Verified / supported"      / status-badge status-verified
```

`const key = LABELS[status] ? status : "unverified";` — an unknown or missing status **fails safe to "unverified"**, the weakest claim, never to "false". A small detail with real ethical weight; mention it.

**`ClaimCard.jsx`** — `claim-card` (plus `archived` when applicable); top row = `<StatusBadge status={claim.status} />`, the `claim-category` chip and an `ARCHIVED` tag; then `claim-title`, `claim-explain`, and `claim-why` (only if `why_misleading` exists); a `claim-provenance` grid showing *Fact-checked by* / *Original source* / *Scope*; a `claim-evidence` list labelled **"Evidence — open and inspect"** where each link opens in a new tab with `rel="noopener noreferrer"`; and a `claim-foot` with *Added* and *Last reviewed* dates. Every field is conditionally rendered, so a sparse entry cannot break the layout.

### 4.12 `website/src/styles.css` (1,441 lines)

**Design tokens in `:root` (line 6)** — the whole theme is driven by variables, so re-theming means editing six values:

```css
--black:#0b0d10; --navy:#092634; --navy-deep:#061c26; --navy-line:#14465e;
--blue:#004e72;  --blue-hover:#00648f;
--orange:#ff6e42; --orange-soft:rgba(255,110,66,.14); --blue-soft:rgba(0,78,114,.35);
--white:#f9f9f9; --gray:#9aa3aa;
--radius:14px; --font:"Segoe UI", system-ui, -apple-system, sans-serif;
--speed:200ms; --ease:cubic-bezier(0.22,0.61,0.36,1);
```

Semantics: near-black page background, navy panels/cards/nav, blue for primary actions and the selected nav item, orange for accents/badges/active indicators, off-white text, gray for metadata and dates. Status colours: `false` and `misleading` in the orange family, `verified` in white, `unverified` in gray — deliberately, so "unverified" never looks as loud as "false".

**Motion** — `.page-enter` (line 86) applies `animation: page-in var(--speed) var(--ease)`; `@keyframes page-in` (line 90) fades opacity 0→1 with a small upward slide. `@keyframes spin` (894) drives the loading spinner; `@keyframes pulse` (900) the backend-status dot. Interactive elements transition at `var(--speed)` = 200 ms, inside the 150–250 ms band that feels instantaneous without being abrupt.

**Homepage fact-check strip** — the `/* home: recently fact-checked */` block (line 418) is the only new visual language the redesign added, and it is built entirely from the existing tokens: `.recent-strip` is a `scroll-snap-type: x mandatory` flex row with a thin themed scrollbar, `.fact-card` is `flex: 0 0 calc((100% - 3 * 1rem) / 4)` with `min-width: 15.5rem` so four cards fit the 1,120 px shell and never shrink past a readable width, `.fact-title` / `.fact-explain` clamp to 4 and 5 lines with `-webkit-line-clamp` (truncation happens in CSS, never by cutting strings in JS), and `.fact-card.is-false` / `.is-misleading` / `.is-verified` / `.is-unverified` colour only the 3 px top accent bar — orange, orange, blue, gray. The `is-` prefix matters: a bare `status-*` class would collide with the `.status-false` badge rule and paint the whole card orange. `.round-btn:focus-visible` and `.recent-strip:focus-visible` add the site's first explicit `:focus-visible` outlines (2 px orange, 3 px offset).

**Responsive** — `@media (max-width: 980px)`, `(max-width: 900px)` and `(max-width: 720px)` (lines 1359 / 1365 / 1386) collapse the two-column checker grid, the claim grid, the summary-card row and the nav into mobile layouts; 900 px also stacks the fact-check header and the About compare-grid, and 720 px sets `.fact-card { flex-basis: 76vw }` so a phone shows one card plus a sliver of the next.

**Accessibility** — `@media (prefers-reduced-motion: reduce)` (line 1432) disables animations and transitions for users who request it. It cannot affect `Element.scrollBy({ behavior: 'smooth' })`, which is why `RecentFactChecks.jsx` checks the same media query in JavaScript. Also present: visible focus styles, ARIA roles on state blocks and tabs, `aria-label`s on icon-only controls, and semantic HTML (`header`, `main`, `nav`, `article`, `footer`).

### 4.13 `website/src/data/claims.json` ✅ Verified contents

Top level: `last_updated: "2026-10-29"`, a `note` string, and `claims` (114 entries — 12 originally hand-written, 102 added after the evidence-verification pass described in §4.17).

Per-claim schema (12 keys present on every entry, plus an optional 13th):
`id`, `claim`, `status`, `category`, `added_date`, `review_date`, `explanation`, `why_misleading` *(optional)*, `original_source`, `fact_checker`, `geo_scope`, `archived`, `evidence[]` where each evidence object is `{ source, title, url }`.

| Statistic | Value |
| --- | --- |
| Total entries | **114** |
| Active / archived | **113 / 1** |
| Status (all 114) | false **78**, misleading **33**, verified **2**, unverified **1** |
| Status (113 active) | false **77**, misleading **33**, verified **2**, unverified **1** |
| Categories | politics 49, ai-media 16, communal 13, world 11, society 6, environment 5, crime 4, religion 3, scam 3, health 2, finance 1, elections 1 |
| Evidence links | **115** total (only `5g-health-harm-claim` carries two — WHO and ICNIRP) |
| Entries with a `why_misleading` note | 41 of 114 |
| Added / review dates | 2026-10-27 → 2026-10-29 |
| Fact-check attributions | Alt News ×52 (plus ×1 where Alt News is cited for *media provenance only*, the figure itself being unverified); Newschecker ×27; India Today Fact Check ×16; The Quint WebQoof ×8; AFP Fact Check ×4; BOOM ×1; Factly ×1; PolitiFact ×1; Reuters Fact Check ×1; WHO/ICNIRP institutional review ×1; NASA institutional consensus record ×1 |
| Geographic scopes | 35 distinct values; India ×31, India (Delhi) ×15, India (West Bengal) ×8, India (Bihar) ×5, United States ×4, Global ×4, India (Arunachal Pradesh) ×4, then a long tail of single-state and single-country scopes |

Three entries carry deliberately cautious labelling worth pointing out: one is **`unverified`** (a claim about the Christchurch attacks where reliable evidence either way was not established), one is **`archived`** (the "Pope Francis puffer coat" item, attributed to Reuters Fact Check), and only **two are `verified`** — a US IRS refund figure confirmed by PolitiFact, and a pellet-gun report that Alt News confirmed against a police General Diary entry. Nothing is marked `verified` merely because a fact-check wrote about it. Also note that AFP and Reuters pages return 403/401 to automated fetchers — those 5 entries predate the verification pass, are labelled `legacy` in `research/claims_research_log.md`, and must be re-opened in a browser during review.

**This file is not a training corpus.** It is display data, imported statically by `Dashboard.jsx` and bundled at build time. Editing it and refreshing the page is the entire update mechanism — no backend restart, no redeploy in development.

### 4.14 `ml/research/prepare_dataset.py` (150 lines) 🔜 future-phase tooling

Purpose (from its own docstring): *"Prepare canonical, type-specific records from an authorized mapped CSV. Offline only. This script does not fetch data, infer source columns, or create model artifacts."*

| Name | Line | Role |
| --- | --- | --- |
| `TEXT_FIELDS` | 17 | `{"article": "text_article", "headline": "text_headline", "claim": "text_claim"}` — one task type at a time |
| `FIELDS` | 22 | the 18 required CSV columns; `main()` exits if any is missing |
| `SUPPORTED_DATASETS` | 29 | `{ifnd, hinfakenews, factdrill, fakenewsindia}` |
| `ALLOWED_TYPES` | 30 | the three text types plus `fact_check_report`, `social_post`, `unknown` |
| `ENGLISH_TAGS` | 31 | `{en, eng, english}` — anything else is excluded |
| `norm(value)` | 34 | NFKC normalize → `casefold()` → collapse whitespace → strip. Deterministic normalization before hashing/comparison |
| `classify(dataset, raw)` | 39 | Returns `(label, ok, reason)`. **Only** documented raw forms map: IFND `fake`→fake, `true`→real; HinFakeNews `0`→fake, `1`→real. FactDrill → unsupported until record-level definitions are verified; FakeNewsIndia → no supported binary mapping; anything else → `unknown_dataset` |
| `write_jsonl(path, rows)` | 61 | one JSON object per line, UTF-8, `ensure_ascii=False` |
| `main()` | 67 | argparse (`--input`, `--output-dir`, `--record-type`), per-row eligibility, hashing, grouping, output writing |

**Eligibility is fail-closed.** A row is `binary_eligible` only if *all* of these hold; every failure is recorded in `exclusion_reasons` and counted in the audit:

1. the raw label mapped successfully;
2. `record_type` equals the requested `--record-type`;
3. the selected text field is non-empty;
4. its `*_source_field` **provenance** is non-empty (which original column the text came from);
5. `leakage_review_status == "passed"` — a *human* confirmed that verdicts, explanations and other label-revealing text are excluded from the model input;
6. `language` is an explicit English tag.

Then, for each of the three text kinds, it stores a SHA-256 of the normalized text in `exact_hashes` and builds `exact_duplicate_groups` for any hash seen more than once.

**Outputs** (written only to `--output-dir`, which the docs insist should be *outside* the repository): `records.jsonl` (all rows + reasons), `eligible.jsonl` (only eligible rows for the selected task), and `audit.json`:

```json
{ "input": "...", "requested_record_type": "article", "record_count": N, "eligible_count": M,
  "eligible_by_label": {"fake": …, "real": …}, "excluded_by_reason": {…},
  "exact_duplicate_cluster_count_by_type": K,
  "near_duplicate_detection_performed": false,
  "event_and_syndication_groups_are_supplied_not_verified": true,
  "human_leakage_review_pass_required_for_eligibility": true }
```

The last three fields are the script declaring its own blind spots — near-duplicates are **not** detected, and event/syndication metadata is **trusted, not verified**. Pointing this out shows you understand the difference between a tool and a guarantee.

**Why leakage review is the big idea:** if a fact-check *report* (which contains the words "fake", "false", "the claim is untrue") is fed to the model as input, the label is literally inside the features. The model then learns to detect fact-check vocabulary, scores near 100 %, and fails completely in production on real articles. That is the most common published failure mode in fake-news detection, and this script hard-blocks it.

### 4.15 `ml/research/evaluate_models.py` (217 lines) 🔜 future-phase tooling

Docstring: *"Score already-fitted models on prepared records; this script never trains. It is offline and writes only to `--output`. Do not run without separate approval. No independent Indian test set is bundled and baseline training overlap is unknown."*

| Name | Line | Role |
| --- | --- | --- |
| `TEXT_FIELD` | 17 | record-type → column map (same three tasks) |
| `load_rows(path, record_type)` | 20 | reads `eligible.jsonl`, keeps only rows matching the task, `binary_eligible`, labelled fake/real, with non-empty text; **raises** on missing or duplicate `record_id` |
| `UnionFind` | 38 | disjoint-set with path compression (`find`) and union by index (`union`) |
| `make_groups(rows)` | 53 | unions rows sharing an exact-text hash, `event_group` or `syndication_group`; hashes each group's sorted member IDs into a stable `group-<sha256[:20]>` ID so **row order cannot change grouping** |
| `split_group_holdout(rows, groups)` | 84 | deterministic ~20 % holdout **by whole group** (`target = max(1, round(len(rows)*0.2))`); returns `unsupported_…` when fewer than two disjoint groups exist or a non-empty partition is impossible |
| `split_source_holdout(rows, groups)` | 106 | picks one `source_name` deterministically by hash; removes cross-source and unknown-source groups from **both** sides; test contains only the held source |
| `score(model, rows, indices, record_type)` | 142 | validates `model.classes_` is exactly `{0, 1}` (raises otherwise), maps fake→0 / real→1, calls `model.predict(texts)`, rejects any prediction outside `{0,1}`, then computes macro and per-class precision/recall/F1 plus `confusion_matrix(actual, predicted, labels=[0,1])` with `class_order: ["fake","real"]` |
| `main()` | 170 | argparse: `--input` (eligible.jsonl), `--baseline` (**defaults to `../best_model.pkl`**), optional `--candidate` (must already exist), `--record-type` (default `article`), `--output` |

The written report embeds its own caveats: `independent_indian_test_set: "not_provided"`, `metrics_are_independent_indian_evidence: false`, `baseline_training_data_overlap: "unknown; scores may overlap baseline training data"`, `baseline_input_domain_provenance: "unknown; …"`, and a `grouping_limitations` paragraph.

Two subtleties worth quoting in a viva:

- The baseline is **loaded and predicted with, never written to** — scoring cannot damage `best_model.pkl`.
- A `--candidate` must *already exist*; the script refuses to create one. Training and evaluation are separated by design so nobody can accidentally tune on the test split.

### 4.16 `ml/research/dataset_manifest.json` + `ml/research/README.md` 🔜

`dataset_manifest.json` (schema_version 2) has `"status": "research_register_only_no_data_acquired"`, `last_reviewed: "2026-10-29"`, a `policy` block (scope "English Indian news", `download_or_access_request_authorized: false`, license rule "UNKNOWN or NA means review required", `independent_test_set: "None verified"`, `explanations_are_model_inputs: false`, `human_leakage_review_pass_required: true`) and a `datasets` array of four candidates. A `workspace` block records the baseline path, the `{0: Potentially Fake, 1: Potentially Real}` mapping, the unknown provenance, the existing API contract, and `production_files_must_remain_unchanged`.

| Dataset | Reported size | Language | Labels | Reuse status |
| --- | --- | --- | --- | --- |
| **IFND** (Indian Fake News Dataset) | 56,868 | English | `True` / `Fake` | `REVIEW_REQUIRED_DO_NOT_USE_UNTIL_CONFIRMED`; license `UNKNOWN`; paper reports augmentation of fake examples that must be identified first |
| **FactDrill** | 22,435 | 13 languages incl. Hindi/English | annotation terms `fake`, `non-relevant` | Mapping `UNSUPPORTED` until record-level definitions are verified |
| **FakeNewsIndia** | 4,803 | English | "fake incidents" + impact low/med/high | `UNSUPPORTED` for a binary real/fake article task — impact is not veracity |
| **HinFakeNews** | ~68,000 listed (a related publication says ~33,300 — a recorded discrepancy) | Hindi | `0=FAKE`, `1=REAL` | Ineligible under the English-only scope; license `UNKNOWN_AI_KOSH_LISTS_NA` |

⚠️ Every size, date range and label set above is **author-reported or listing-reported, not verified** — the register states that exact source columns and row-level records have not been inspected, and that *"public visibility or access does not establish reuse permission."* Present them as "reported", never as facts you confirmed.

`ml/research/README.md` adds the operating rules: dataset acquisition, package installation, script execution, training and candidate creation all require **separate approval**; no copyrighted dataset contents go in the repository; documented test cases are listed but **"not executed"**; and both splits are diagnostic only — *"Do not claim independent Indian-news performance without one."*

### 4.17 `Frontend/research/` — how the 102 new claim records were verified ✅

A separate offline pipeline, unrelated to the ML model, that grew the dashboard dataset from 12 records to 114. It exists because *"the URL returns 200"* is not evidence that a verdict was checked, and because a hand-written claim list of that size cannot be trusted without a machine-checkable audit trail. It reads and writes only files under `Frontend/` plus an OS-temporary article cache: no packages were installed, no dataset downloaded, and nothing in `ml/` or `backend/` is touched.

```text
harvest_candidates.py → candidates.tsv              discover URLs from RSS feeds and article listings
fetch_articles.py     → logs/*.tsv + temp cache     fetch each URL, extract body text, record HTTP status
split_batches.py      → cache/batch_NN.json         keep articles with HTTP 200 and >400 chars, group for review
manual review         → batches/batch_NN.json       reviewer writes record + provenance, or an exclusion reason
build_dataset.py      → claims.json + rejected.tsv  GATE the record, then merge
validate_claims.py                                  schema / dedup / fetch-record checks over the shipped file
check_fidelity.py                                   do the numbers and proper nouns in a record appear in its source?
find_near_duplicates.py                             Jaccard similarity across claim and explanation texts
write_research_log.py → claims_research_log.md      regenerate the audit log from pipeline state
```

**The gate is the part worth explaining in a viva.** A record is only merged when `build_dataset.py` can independently confirm it:

1. its provenance URL was fetched with HTTP 200 and yielded more than 400 characters of body text;
2. `provenance.verdict_quote` — at most 30 words — appears **verbatim** inside that cached article text, after folding curly quotes, en/em dashes and ellipses and collapsing whitespace. This is the check that stops an invented conclusion from entering the dataset;
3. `record.evidence[0].url` equals the provenance URL, so a citation can't drift from the article actually read;
4. status, category and both dates are in the project vocabulary, `misleading` carries a `why_misleading`, `verified` carries a `status_rationale`;
5. `id`, evidence URL and normalised claim text are unique across old *and* new records.

Failures are written to `rejected.tsv` with the reason and are not added. In this run the funnel was **701 candidates harvested → 693 articles reviewed → 96 deliberately excluded → 102 records drafted → 0 rejected by the gate → 102 shipped**, and every exclusion carries a logged reason (the largest groups being straight news reports, roundups covering several claims at once, and two Eiffel Tower items that duplicated the existing `eiffel-tower-palestinian-flag-ai` entry).

**Honest limits of this pipeline**, stated in `claims_research_log.md` itself:

- Body text is capped (head 3,000 + tail 2,400 characters) to keep the cache small, so `check_fidelity.py` reports a *review prompt*, not proof of fabrication, when a detail falls in a truncated middle. Its measured mean coverage over the 102 shipped records is 93.2%, with 99 of 102 at or above 70%; the three below threshold are a punctuation artefact, a capitalised verb, and a state name inferred from a city.
- Five hosts could not be harvested at all: AFP Fact Check (HTTP 403), Reuters Fact Check (401), AP News (403), Logically Facts (connection failed) and PIB Fact Check (JS-rendered listing, no feed, `/page/2/` returns 404). No record added by this pass cites them.
- The 12 pre-existing records are flagged **`legacy - not re-fetchable`** in the log rather than claimed as verified, because 5 of them point at AFP/Reuters hosts. `validate_claims.py` exempts them from the fetch-record check by an explicit id list — visible technical debt, not an accident.
- Article text lives in the OS temp directory, outside the repository, so no copyrighted prose is committed.

---

## 5. End-to-End Request Trace

### 5.1 Starting the demo

1. `cd Frontend/backend` → `python -m uvicorn main:app --port 8000`. Uvicorn imports `backend/main.py`, builds `app`, registers CORS and the two routes. `_model` is still `None` — nothing is loaded yet.
2. `cd Frontend/website` → `npm run dev`. Vite serves `index.html`, which loads `main.jsx`, which renders `<App/>` inside `<React.StrictMode>`.
3. Browser opens `http://localhost:5173`. `App.jsx` reads `window.location.hash` (empty → `'/'`) and renders `Home`.
4. `Home`'s `useEffect` calls `checkHealth()` → `request('/health')` → `fetch('/api/health')` → Vite proxy → `http://127.0.0.1:8000/api/health` → `health()` returns `{"status":"ok","model_loaded":true,"labels":{"0":"Potentially Fake","1":"Potentially Real"}}`. The pill switches from "Checking analysis backend…" to **"Analysis backend online"**.

### 5.2 Text mode — paste an article

| # | Where | What happens |
| --- | --- | --- |
| 1 | `Header.jsx` | Click **News Checker** → `href="#/checker"` → `hashchange` fires → `App.jsx` `setPath('/checker')` → `ROUTES['/checker']` renders `Checker`; `key={path}` remount triggers the `page-in` animation |
| 2 | `Checker.jsx` | Default `mode = 'text'`. Typing in the `<textarea>` calls `setText(e.target.value)`; React re-renders and the character counter updates; `canSubmit` flips to `true` at 30+ non-whitespace characters, enabling the button |
| 3 | `Checker.jsx` | Click **Analyze story** → `handleSubmit(event)` → `event.preventDefault()` (no page reload) → `setLoading(true)`, `setError(null)`, `setResult(null)` |
| 4 | `Checker.jsx` → `StateBlocks.jsx` | `loading && <Spinner/>` renders; the button label becomes "Analyzing…" and is disabled |
| 5 | `api.js` | `analyzeText(text.trim())` → `request('/analyze', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text})})` |
| 6 | `vite.config.js` | Dev proxy forwards `/api/analyze` to `http://127.0.0.1:8000/api/analyze` (same-origin to the browser ⇒ no CORS preflight) |
| 7 | `main.py` | FastAPI parses the body into `AnalyzeRequest`. Malformed JSON or a wrong type → automatic `422` before your code runs |
| 8 | `main.py:296` `analyze()` | `has_text=True`, `has_url=False`; `has_text == has_url` is `False`, so the XOR check passes |
| 9 | `main.py:309` | `len(article) < MIN_INPUT_CHARS` (30)? → `422` "Please provide at least 30 characters of meaningful text." Otherwise `article[:MAX_ARTICLE_CHARS]` truncates to 20,000 chars |
| 10 | `main.py:265` `run_screening()` | `get_model()` → first call does `joblib.load(MODEL_PATH)` into the module-level `_model` cache (later requests reuse it) |
| 11 | inside the pipeline | `model.predict([article])` → TF-IDF: tokenize → lowercase → drop English stop-words → build unigrams+bigrams → keep only the 50,000 known terms → `1+log(tf)` → × idf → L2-normalize → a sparse `1 × 50000` row → LinearSVC: `w·x + b` → `> 0` ⇒ class `1`, else class `0` |
| 12 | `main.py:277` | `prediction not in LABEL_VERDICTS` ⇒ `500` "Unexpected model label". Otherwise return `(label, LABEL_VERDICTS[label])` |
| 13 | `main.py:317` | Build `AnalyzeResponse(label=…, verdict=…, disclaimer=DISCLAIMER, input_mode="text", extracted_chars=len(article))`; FastAPI serializes it to JSON |
| 14 | `api.js` | `response.ok` is true → `data` returned; otherwise `data.detail` becomes the thrown `Error` message |
| 15 | `Checker.jsx` | `setResult(response)`; `finally { setLoading(false) }` |
| 16 | `ResultCard.jsx` | `isFake = result.label === 0` → `result-fake` (🚩) or `result-real` (📰) card with `result.verdict`, then `result.disclaimer`, then "{n} characters analysed" |

**Typical latency:** TF-IDF + a dot product over 50,000 sparse features is sub-millisecond; the request is dominated by HTTP and the one-off model load. ✅ No benchmark is recorded in this repo, so don't quote a millisecond figure — say "milliseconds on a laptop CPU".

### 5.3 URL mode — the SSRF-safe path

Steps 1–6 are the same except the body is `{url: "…"}` and the client uses `analyzeUrl(url.trim())` with `<input type="url">`. Then:

7. `analyze()`: `has_text=False`, `has_url=True` → XOR passes.
8. `extract_article(request.url)` → `fetch_html(url)`:
   - **Hop 1:** `validate_public_url(url)` — scheme must be http/https; no embedded `username`/`password`; hostname not `localhost`/`*.local`; `socket.getaddrinfo` must succeed; **every** resolved IP must satisfy `ipaddress.ip_address(...).is_global`. Any failure ⇒ `422` with a specific message.
   - `requests.get(..., timeout=(5,15), allow_redirects=False, stream=True)` with a browser `User-Agent`. Network error ⇒ `502`.
   - If `response.is_redirect or response.is_permanent_redirect`: read `Location`, `urljoin` it, `continue` — **and re-validate the new URL**. After 6 hops the `for…else` raises `502` "Too many website redirects."
   - `status_code >= 400` ⇒ `502` with the code. `Content-Type` must contain `text/html` or `text/plain` ⇒ else `502`.
   - Stream in 16 KB chunks, aborting above `2_000_000` bytes ⇒ `502` "The webpage is too large to process safely." Decode with `errors="replace"`.
9. `extract_article()` parses with BeautifulSoup: read `soup.title`; `decompose()` all `script/style/nav/footer/header/aside/form/noscript/svg`; choose `article` → `main` → `[role=main]` → `body` → whole soup; join text of all `p/h1/h2/h3`; if under 100 chars, fall back to the container's full text; truncate to 20,000; if still under 100 chars ⇒ `422` "Could not extract enough article text… Try pasting the article text in News Text mode instead."
10. Steps 10–13 of §5.2 run on the extracted text, and the response also carries `input_mode="url"`, `source_title` and `source_hostname`.
11. `ResultCard.jsx` additionally renders the source title and "Source website: {hostname}" so the user can see *what* was actually analysed.

### 5.4 Error paths, mapped end to end

| HTTP | Raised by | Typical cause | What the user sees |
| --- | --- | --- | --- |
| — (network) | `api.js` first `catch` | backend not running / wrong port | "Could not reach the analysis backend. Make sure the FastAPI server is running on port 8000." |
| `422` | FastAPI/Pydantic | body isn't valid JSON or wrong types | the framework's validation detail |
| `422` | `analyze()` | both or neither of `text`/`url` | "Provide exactly one of: article text or an article URL." |
| `422` | `analyze()` | fewer than 30 characters | "Please provide at least 30 characters of meaningful text." |
| `422` | `validate_public_url()` | bad scheme, credentials in URL, localhost/`.local`, unresolvable host, non-global IP | the specific guard message |
| `422` | `extract_article()` | < 100 chars of readable text (JS-heavy, paywalled, bot-blocked) | "Could not extract enough article text… Try pasting the article text…" |
| `500` | `run_screening()` | model raised, or returned a label outside `{0,1}` | "Model analysis failed (ExceptionType)." |
| `502` | `fetch_html()` | target site unreachable, HTTP ≥ 400, wrong content type, > 2 MB, > 6 redirects | the upstream-failure message |
| `503` | `get_model()` | `ml/best_model.pkl` missing | "Model file not found at … Place best_model.pkl inside Frontend/ml/" |

All of them arrive in the same place: `api.js` throws `new Error(data.detail)`, `handleSubmit`'s `catch` calls `setError(err.message)`, and `ErrorBlock` shows it with a **Try again** button wired to `onRetry`.

### 5.5 The dashboard is a completely separate path

Opening `#/dashboard` performs **zero** network requests:

```
Dashboard.jsx  →  import claimData from '../data/claims.json'   (bundled by Vite at build time)
               →  useMemo: categories, counts, lastReviewed, filtered
               →  SUMMARY_CARDS buttons  ⇄  status filter state
               →  filter-bar: search input, category select, status select, sort select, "Show archived" checkbox
               →  filtered.map(claim => <ClaimCard key={claim.id} claim={claim} />)
                      └── <StatusBadge status={claim.status} />  + evidence <a target="_blank" rel="noopener noreferrer">
               →  filtered.length === 0  ⇒  <EmptyBlock title="No matching claims" />
```

Every interaction is pure client-side state: `setQuery`, `setStatus`, `setCategory`, `setSort`, `setShowArchived` each change a `useMemo` dependency, which recomputes `filtered`, which re-renders the grid; `listSignature` changes ⇒ the grid remounts ⇒ the fade-in replays. Evidence links leave the app and open in a new tab. **No model, no backend, no database is involved** — and that separation is the point: an automatic style classifier must never be allowed to decide whether a specific factual claim is false.

---

## 6. Limitations & Future Improvements

### 6.1 Model and data limitations

1. **It detects style, not truth.** TF-IDF + a linear SVM has no world model. It cannot know whether an event occurred.
2. **Unknown training provenance ⇒ unknown real-world performance.** No dataset, no split, no metrics are recorded (§3.3, §3.8).
3. **Leakage risk in any future evaluation.** Republished and syndicated stories duplicate across splits; without group-aware splitting, scores inflate. The research scripts address this but have not been run.
4. **Generalization to Indian news is unestablished.** The feature space is English-oriented (`stop_words='english'`), and the register's stated scope for future work is English Indian news with **no independent Indian test set provided**.
5. **Language limitation.** Anything but English is out of scope: stop-word removal and the token pattern are English-specific, and Hindi/regional-language text would mostly produce out-of-vocabulary tokens. HinFakeNews is explicitly ineligible under the current English-only scope.
6. **Temporal drift.** The vocabulary is frozen at training time; new events, people, platforms and slang contribute no signal.
7. **Bag-of-words blindness.** Negation, sarcasm, irony and paraphrase are largely invisible; only adjacent bigrams carry any ordering information.
8. **No calibrated confidence.** No `predict_proba`; `decision_function` is an unbounded margin, so there is no principled threshold to tune precision/recall trade-offs on.
9. **Unknown class balance with `class_weight=None`.** If training data was imbalanced, predictions are biased toward the majority class.
10. **Adversarial triviality.** An attacker who knows the model is TF-IDF-based can rewrite a fabrication in the vocabulary of legitimate reporting and flip the label. There is no adversarial robustness here.
11. **Truncation.** Only the first 20,000 characters are screened; a misleading article could carry its key claim later.

### 6.2 Product and engineering limitations

12. **URL extraction fails often in the real world.** JavaScript-rendered pages, paywalls, consent walls and bot-blocking return little or no readable text. The 2 MB cap and 6-redirect limit also reject some legitimate pages. Fallback is manual pasting.
13. **SSRF guards are necessary but not exhaustive.** `is_global` rejects private/reserved ranges, and every hop is re-validated, but the check is at DNS-resolution time — a DNS record could change between resolution and connection (TOCTOU), and IPv6/CGNAT edge cases deserve review. This is a known hard problem, not a solved one.
14. **No authentication, rate limiting or abuse protection.** Anyone who can reach port 8000 can submit URLs, making the server fetch third-party sites. Fine for a localhost demo; **not** acceptable for public deployment.
15. **No automated tests and no CI.** Correctness currently rests on manual end-to-end verification. `ml/research/README.md` lists documented test cases that are explicitly **"not executed"**.
16. **Single-process dev topology.** Uvicorn on loopback + Vite dev server. No production WSGI/ASGI hardening, no HTTPS, no reverse proxy, no horizontal scaling, no caching of fetched articles.
17. **Blocking I/O in async framework.** `analyze()` is a `def` (not `async def`), so FastAPI runs it in a threadpool — acceptable, but slow external fetches still consume worker threads.
18. **Dashboard is manual and local.** `claims.json` is edited by hand and bundled at build time: a content change requires a rebuild/redeploy in production, there is no CMS, no audit trail, no multi-editor workflow and no automatic monitoring. The UI states plainly that "Nothing here is monitored automatically."
19. **Evidence links can rot**, and some hosts (AFP, Reuters) block automated verification with 403/401, so link checking must be manual.
20. **No persistence or analytics.** Nothing is logged or stored: no history of what was analysed, no feedback loop, no way to measure real-world usefulness.
21. **Dependency pins vs. installed versions differ** (§2.3), and `Frontend/requirements.txt` is empty.

### 6.3 Why machine learning cannot establish truth — say this clearly

A classifier is a function from text features to a label, fitted to imitate the labels humans assigned in a **fixed, past dataset**. It has no access to the world: no records, no witnesses, no official statements, no ability to run an experiment. It learns *correlates* of the labels — the vocabulary, tone and structure that happened to accompany fake examples in that corpus. Those correlates are (a) not necessary for falsehood, (b) not sufficient for truth, and (c) not stable over time or across outlets.

Therefore the best possible outcome is a well-calibrated **triage signal**: "this deserves human attention." Truth-establishment requires evidence and reasoning about the world, which is exactly what the **dashboard** subsystem does — with named fact-checkers, direct evidence links, review dates, and four statuses that separate *unverified* from *false*. The architecture encodes the ethics: the model ranks attention; humans and evidence decide truth.

### 6.4 🔜 Future work, phase 1 — dataset acquisition and model training (NOT started)

This is the planned next phase. **It has not been executed: no dataset has been downloaded, no training has run, and no candidate model exists.** The repository currently contains only the *tooling and the register* for it.

What the register (`ml/research/dataset_manifest.json`, status `research_register_only_no_data_acquired`) already fixes:

- **Scope:** English Indian news.
- **Candidate sources:** IFND, FactDrill, FakeNewsIndia, HinFakeNews — with author-reported sizes of 56,868 / 22,435 / 4,803 / ~68,000 respectively, **all unverified** and **none acquired**.
- **Blocking conditions:** every dataset license is `UNKNOWN`/`NA` ⇒ `REVIEW_REQUIRED_DO_NOT_USE_UNTIL_CONFIRMED`; download/access requests are **not authorized**; FactDrill's label mapping is `UNSUPPORTED` pending record-level definitions; FakeNewsIndia is not a binary real/fake article corpus; HinFakeNews is Hindi and therefore ineligible under the English scope.
- **Mandatory preconditions before any training run:** an operator maps an authorized source into the 18-column canonical CSV; a human sets `leakage_review_status = "passed"` per row after confirming that verdicts/explanations are excluded from the model input; text provenance (`*_source_field`) is recorded; near-duplicate, event and syndication review is documented.

The intended sequence, using the scripts that already exist:

1. Resolve licensing and obtain authorization for at least one dataset.
2. Map it to the canonical CSV and run `prepare_dataset.py --record-type article` → `eligible.jsonl` + `audit.json`; inspect eligibility counts and exclusion reasons **before** training.
3. Split by group (never by row) into train/validation/test; stratify by class if the audit shows imbalance.
4. Train candidates (start with the existing TF-IDF + LinearSVC recipe, tune `C`, `min_df`/`max_df`, `ngram_range`; then compare against a stronger baseline).
5. Score with `evaluate_models.py` under both `group_holdout` and `source_holdout` and record macro P/R/F1, per-class values and the confusion matrix.
6. Wrap the winner in `CalibratedClassifierCV` if confidence scores are wanted.
7. Only then replace `ml/best_model.pkl` — with the current artifact archived, and with the API contract (`{0: Potentially Fake, 1: Potentially Real}`) unchanged.

**Phrasing for your report/slides:** *"The Indian-news dataset and training phase is planned future work. The preparation and evaluation tooling is written and reviewed; no data has been acquired and no training has been run, so the model currently deployed is the pre-existing baseline artifact."*

### 6.5 🔜 Other future improvements

**Model quality**
- Calibrated probabilities (`CalibratedClassifierCV`) so the UI can show honest confidence and support a tunable threshold.
- Group-aware, time-aware splits (train on older news, test on newer) to measure drift rather than memorization.
- Feature upgrades: char n-grams for morphological robustness, multilingual TF-IDF, or a fine-tuned transformer (e.g. IndicBERT/MuRIL for Indian English) — at real cost in size, latency and interpretability.
- Interpretability surface: expose the top positive/negative TF-IDF terms for a given article so users see *why* it was flagged.
- Ensemble or cascade: cheap linear screen first, expensive model only for borderline cases.
- Class-imbalance handling (`class_weight='balanced'`) once the audit reports label counts.

**Product**
- Claim-level analysis (the schema already supports a `claim` record type) alongside article-level.
- Side-by-side "model says / fact-checkers say" view linking a screened story to matching dashboard entries.
- Source-credibility context (domain age, known publisher) presented as *context*, never as an automatic verdict.
- Multi-language support; browser extension; shareable result links with the disclaimer embedded.
- User feedback ("I think this is wrong") logged for later analysis.

**Engineering**
- pytest suite: unit tests for `validate_public_url`, `fetch_html`, `extract_article`, `run_screening` plus API tests with `fastapi.testclient`; contract tests for `AnalyzeResponse`; frontend tests for the four render states.
- CI (GitHub Actions) running lint + tests + `npm run build` on every push.
- Dockerfiles for backend and frontend; `docker-compose` for one-command startup.
- Authentication, API keys and rate limiting before any public deployment; a queue/worker for URL fetching with a strict egress allow-list.
- Structured logging, request IDs, error tracking (Sentry), and basic metrics (latency, label distribution, extraction failure rate).
- Move `claims.json` to a small database or headless CMS with an editorial review workflow, timestamps and an audit trail; add scheduled link-checking that flags dead evidence URLs for human review instead of silently updating anything.
- Fill in `Frontend/requirements.txt` (or delete it) and reconcile installed versions with the pins.

---

## 7. Viva & Presentation Preparation

### 7.1 Two-minute presentation script (336 words ≈ 2 min at a normal presenting pace)

> "My project is a Fake News Analyzer — a full-stack tool that gives readers a fast, honest first-pass signal on a news story, and keeps that signal strictly separate from actual fact-checking.
>
> The architecture has three layers. A React 18 front end built with Vite provides four pages: Home, News Checker, Claim Dashboard and About. A FastAPI backend, served by Uvicorn, exposes two endpoints — `GET /api/health` and `POST /api/analyze`. And underneath sits a scikit-learn pipeline, loaded once with joblib and cached in memory. The model never leaves the server; the browser only ever sees a JSON label.
>
> The model itself is a two-stage pipeline. Stage one is a `TfidfVectorizer` configured with unigrams and bigrams, English stop-word removal, sub-linear term frequency, L2 normalization, and a vocabulary pruned by document frequency to exactly 50,000 terms. Stage two is a `LinearSVC` — a linear support vector machine trained with squared hinge loss and L2 regularization. It outputs class `0`, which we map to 'Potentially Fake', or class `1`, 'Potentially Real'.
>
> When a user submits a URL rather than text, the backend validates it first: HTTP or HTTPS only, no embedded credentials, no localhost, and every IP address the hostname resolves to must be globally routable. That is an SSRF defence — without it, someone could point my server at internal infrastructure. Redirects are followed manually, at most six hops, and re-validated at each hop, with a two-megabyte download cap. BeautifulSoup then extracts readable article text before screening.
>
> The most important design decision is honesty. `LinearSVC` has no `predict_proba`, so I do not show fake percentages. Every response carries a disclaimer that this is a screening result based on writing patterns, not fact verification. Alongside the model there is a separate, human-curated Claim Dashboard with 113 active entries, four strict statuses — unverified, misleading, false per cited evidence, and verified — plus named fact-checkers, direct evidence links and review dates, and no entry enters the file unless a verbatim conclusion quote from its source article was matched against the fetched text.
>
> The model ranks what deserves attention. Humans and evidence decide what is true."

### 7.2 Explaining the architecture in 60 seconds

"Three processes, one frozen artifact. React in the browser talks to `/api` with relative URLs; Vite's dev proxy forwards those to Uvicorn on port 8000, so the browser sees one origin and there is no CORS problem in development. FastAPI validates the request with Pydantic, applies the SSRF guards and article extraction if it's a URL, then calls `model.predict([text])` on a pipeline that's loaded lazily and cached in a module-level variable. The response is a strict Pydantic model: label, verdict, disclaimer, input mode, source metadata, character count. The dashboard bypasses all of it — it's a static JSON import rendered client-side, because a style classifier must never decide whether a factual claim is false."

### 7.3 Twenty viva questions and answers

**1. What does your project actually do?**
It screens news text — pasted or fetched from a public URL — with a trained TF-IDF + LinearSVC classifier and returns "Potentially Fake" or "Potentially Real", always with a disclaimer. Separately, it shows a manually reviewed dashboard of specific circulating claims with evidence links. It does not establish truth.

**2. Why the word "Potentially"?**
Because the model measures stylistic similarity to its training data, not veracity. "Potentially" is a deliberate hedge that keeps the tool from defaming real journalism or endorsing fabrication. It appears in `LABEL_VERDICTS` in `backend/main.py:34`, in `app.py`, and in the disclaimer attached to every API response.

**3. What is TF-IDF?**
Term Frequency–Inverse Document Frequency: a way to turn text into numbers by weighting words that are frequent in *this* document but rare across the corpus. Here `tf` becomes `1 + log(tf)` because `sublinear_tf=True`, and `idf` is `ln((1+n)/(1+df)) + 1` with `smooth_idf=True`. Each row is then L2-normalized so document length stops mattering.

**4. Why unigrams *and* bigrams?**
Unigrams capture topic vocabulary; bigrams capture phrases whose meaning isn't the sum of their parts — "officials confirm", "viral video", "shock ing". You can see both in the loaded vocabulary (`'000'` and `'000 according'`). The cost is a much larger feature space, which is why `max_features=50000` caps it.

**5. What do `min_df=2` and `max_df=0.7` do?**
`min_df=2` drops terms appearing in fewer than two documents — typos, unique names, noise. `max_df=0.7` drops terms in more than 70 % of documents — they can't discriminate between classes. Together they shrink the vocabulary and reduce overfitting.

**6. Why `sublinear_tf=True`?**
Raw counts let long documents and keyword stuffing dominate. `1 + log(tf)` compresses that: the 50th occurrence of a word adds far less than the first. It makes short and long articles comparable.

**7. Why L2 normalization?**
It scales each document vector to unit length, so the classifier compares *composition* rather than *length*. Essential here, since inputs range from 30 characters to 20,000.

**8. What is LinearSVC and how does it decide?**
It fits a maximum-margin linear hyperplane by minimizing `(1/2)‖w‖² + C·Σ max(0, 1 − y(w·x + b))²`. With `classes_ = [0,1]` there is a single weight vector `coef_` of shape `(1, 50000)` and one `intercept_`. Prediction is the sign of `w·x + b`: positive → 1 ("Potentially Real"), otherwise 0 ("Potentially Fake").

**9. What is `C=1.0`?**
The inverse regularization strength — the trade-off between a wide margin and training errors. Small `C` allows more training violations (simpler model); large `C` pushes toward fitting the training data (overfitting risk). `1.0` is scikit-learn's default and is what the artifact contains.

**10. Why a linear kernel instead of RBF?**
Text TF-IDF vectors are high-dimensional and extremely sparse; in that regime a linear boundary is the standard strong choice, far cheaper to train and predict, and less prone to overfitting than kernel methods.

**11. Does your model give probabilities? Why not?**
No. `LinearSVC` has no `predict_proba` — I verified `hasattr(model, 'predict_proba')` is `False`. It only exposes `decision_function`, the signed distance from the hyperplane, which is unbounded and not a probability. Turning it into one would need calibration (`CalibratedClassifierCV` with Platt scaling or isotonic regression). Showing "87 % fake" without calibration would be misleading, so the UI shows a label plus a disclaimer.

**12. What dataset did you train on, and what accuracy did you get?**
The model is a pre-trained artifact supplied for this project. Its training corpus is **not recorded** — `ml/research/dataset_manifest.json` literally says `"baseline_training_data_provenance": "UNKNOWN"`. And **no accuracy, precision, recall or F1 is recorded anywhere in the repository**, so I won't invent one. What I built instead is the evaluation protocol — macro and per-class precision/recall/F1 plus a confusion matrix, with leakage-safe group and source holdouts — in `ml/research/evaluate_models.py`. Producing a real number needs an authorized dataset and an approved run of that script; that is the next phase.

**13. What is data leakage, and why does it ruin fake-news models?**
Leakage is when information about the label reaches the features. Two common forms here: (a) feeding the model fact-check *report* text that contains "the claim is false" — the label is in the input, so the model scores near-perfectly and fails in production; (b) putting near-duplicate copies of the same syndicated story in both train and test, so the test set is memorization, not generalization. My preparation script requires `leakage_review_status == "passed"` from a human and never selects the explanation field as input; my evaluator unions rows by exact text hash, `event_group` and `syndication_group` and splits **by whole group**.

**14. Why macro-F1 rather than accuracy?**
Accuracy collapses under class imbalance: a model that always predicts "real" can score 95 % on a 95/5 dataset while catching zero fake news. Macro-F1 computes F1 per class and averages unweighted, so both classes must be handled well. Precision asks "of what I flagged, how much was right?"; recall asks "of what was really there, how much did I catch?".

**15. Which error is worse, a false positive or a false negative?**
Both are harmful and they are harmful differently. A false positive labels genuine journalism as potentially fake — that can defame a credible outlet, which is why the label says *potentially* and never *fake*. A false negative waves misinformation through with an implied endorsement. The product mitigates both with disclaimers and by directing users to the human-reviewed dashboard.

**16. What is SSRF, and how do you prevent it?**
Server-Side Request Forgery: tricking a server into fetching internal resources on the attacker's behalf — e.g. `http://169.254.169.254/` for cloud metadata, `http://127.0.0.1:8000/` for the server itself, or `http://192.168.1.1` for a router. `validate_public_url()` requires http/https, rejects embedded credentials, rejects `localhost` and `.local`, resolves the hostname with `socket.getaddrinfo` and requires **every** returned address to satisfy `ipaddress.is_global`. Redirects are followed manually with `allow_redirects=False`, capped at six hops, and **re-validated at each hop** — otherwise an attacker could redirect from an allowed domain to an internal one.

**17. What other safety limits exist on URL fetching?**
`timeout=(5, 15)` so a hung site can't block the worker; `stream=True` with 16 KB chunks and a hard `2_000_000`-byte cap; a `Content-Type` check accepting only `text/html` or `text/plain`; HTTP ≥ 400 rejected; a browser-like `User-Agent`; and a 20,000-character cap on extracted text. Errors are typed: upstream failures become `502`, input problems `422`, model faults `500`, a missing model file `503`.

**18. How is the model loaded, and why that way?**
`get_model()` is a lazy singleton guarded by a module-level `_model` variable: first request checks the file exists (else `503`) and calls `joblib.load`, later requests reuse the cached object. Loading per request would re-unpickle 2.3 MB every time; loading at import would slow startup and make a missing file harder to report. The Streamlit app does the same thing with `@st.cache_resource`.

**19. How does the React app route between pages without React Router?**
`App.jsx` keeps a `ROUTES` object mapping `'/'`, `'/checker'`, `'/about'`, `'/dashboard'` to page components. `currentPath()` strips the `#` from `window.location.hash`; a `hashchange` listener calls `setPath`. Unknown routes fall back to `Home`. `key={path}` on the wrapper forces a remount so the CSS `page-in` animation replays. Four routes did not justify an extra dependency, and hash routing needs no server rewrite rules.

**20. How does your dashboard decide a claim is false — and why is that not the model's job?**
It doesn't decide automatically at all. Every entry in `claims.json` was reviewed by a human and carries a `status` from a fixed vocabulary — `unverified`, `misleading`, `false`, `verified` — a named `fact_checker`, an `original_source`, a `geo_scope`, `added_date`, `review_date`, and an `evidence` array of direct links. `StatusBadge` even fails safe: an unknown status renders as "Unverified claim", never "False". The project rule, stated in `About.jsx` and on the dashboard itself, is that a claim is never marked false because it is controversial, unfamiliar, popular, or flagged by the ML model. A style classifier has no evidence, so it has no standing to declare a factual claim false.

**Bonus — likely follow-ups**

- *Why FastAPI over Flask/Django?* Native Pydantic validation, automatic OpenAPI docs at `/docs`, async-capable, minimal boilerplate — ideal for a two-endpoint model service.
- *Why joblib over pickle?* Same format, but optimized for NumPy arrays and scikit-learn objects; it's the officially recommended way to persist estimators.
- *Is it safe to serve a pickle?* Loading a pickle executes its class constructors, so you must only load artifacts you trust. Ours is a local file we control; the API never accepts model data from users.
- *Why two front ends (Streamlit and React)?* `app.py` is the original single-file prototype, preserved intact. The React app is the production-style rebuild with proper separation of concerns, real state handling and a design system.
- *What happens if the model file disappears?* `get_model()` raises `503` with "Model file not found at … Place best_model.pkl inside Frontend/ml/", and `/api/health` reports `"model_loaded": false`. The UI shows the error via `ErrorBlock`.

### 7.4 Five limitations to state proactively

1. **No recorded performance metrics, and unknown training data.** I will not quote accuracy for an artifact whose provenance isn't documented; I built the evaluation protocol instead.
2. **It reads style, not facts** — a well-written fabrication can pass and a sensational true story can be flagged. This is fundamental to the approach, not a bug.
3. **English-only and possibly era-bound**, so it cannot be claimed to generalize to Indian-language news or to current events.
4. **No calibrated confidence**, because `LinearSVC` provides a margin, not a probability — so there is no principled threshold to trade precision against recall.
5. **URL extraction is brittle and the service has no auth, rate limiting or tests**, which makes it a localhost demo rather than a deployable public service.

### 7.5 Five future improvements

1. **Execute the dataset phase**: resolve licensing, acquire an authorized English Indian-news corpus, run `prepare_dataset.py`, train candidates and score them with `evaluate_models.py` under group- and source-held-out splits — producing the first honest metrics.
2. **Calibrated probabilities** via `CalibratedClassifierCV`, so the UI can show meaningful confidence and support a tunable decision threshold.
3. **Explainability**: surface the top positive and negative TF-IDF terms for the submitted article so users see *why* it was flagged.
4. **A real test suite and CI**: pytest for the SSRF guards, extraction and endpoints; frontend tests for the four render states; lint + build + test on every push.
5. **Deployment hardening**: Docker, authentication, rate limiting, an egress allow-list for URL fetching, structured logging and monitoring — plus a CMS-backed dashboard with link-rot detection so evidence stays verifiable.

### 7.6 Demo checklist

1. Start the backend: `cd Frontend/backend` → `C:\FakeNewsdetector\.venv\Scripts\python.exe -m uvicorn main:app --port 8000`.
2. Show `http://localhost:8000/api/health` → `{"status":"ok","model_loaded":true,"labels":{…}}`. Mention `http://localhost:8000/docs` for the auto-generated API docs.
3. Start the site: `cd Frontend/website` → `npm run dev`; open **`http://localhost:5173`** (use `localhost`, not `127.0.0.1`).
4. Home: point at the **"Analysis backend online"** pill — then stop the backend and show it flip to "Backend offline". Restart it.
5. Checker → News Text: paste a sensational fabricated story, show the live character counter enabling the button, submit, show the 🚩 verdict **and read the disclaimer aloud**.
6. Checker → News Text: paste a neutral wire-style report, show the 📰 result.
7. Checker → Article URL: use a plain server-rendered news page. Then, for impact, submit `http://localhost:8000/api/health` and show the SSRF rejection — this is the strongest security moment in the demo.
8. Checker: show the empty state before any analysis, the spinner during one, and the error card with **Try again** after a failure.
9. Dashboard: click a summary card to filter, search a keyword, switch category and sort, toggle **Show archived** (the archived Pope-puffer-coat entry appears), open an evidence link in a new tab, and show the weekly-workflow list.
10. Close on the About page's "Unverified ≠ False" band.

**Fallbacks:** backend won't start → check port 8000 is free and that `ml/best_model.pkl` is present (a missing file gives `503` and `model_loaded: false`). `127.0.0.1:5173` refuses → use `localhost`. URL extraction fails on stage → switch to News Text mode and explain *why* it failed (JS rendering, paywall or bot blocking) — that is a feature of the honest error handling, not a bug.

### 7.7 Glossary

| Term | Plain-English meaning |
| --- | --- |
| **TF-IDF** | Weighting scheme: important = frequent in this document, rare across the corpus |
| **Token** | One extracted word-like unit of text |
| **Unigram / bigram** | A single token / a pair of adjacent tokens, treated as one feature |
| **Vocabulary** | The fixed set of 50,000 terms the model knows; anything else is ignored |
| **Stop words** | Common words (the, and, of) removed before counting |
| **Sparse matrix** | A matrix that is mostly zeros, stored compactly — typical for text features |
| **Document frequency (df)** | How many documents contain a term |
| **`min_df` / `max_df`** | Cut off terms that are too rare / too common to be useful |
| **Sub-linear TF** | `1 + log(count)` instead of the raw count |
| **L2 normalization** | Scale a vector to length 1, removing the effect of document length |
| **SVM** | Support Vector Machine: finds the widest separating margin between classes |
| **Hyperplane** | The flat decision boundary; in 50,000 dimensions it is a 49,999-dimensional surface |
| **Hinge loss** | Penalty that is zero once a point is on the correct side with enough margin |
| **Regularization (L2)** | Penalty on large weights to prevent overfitting |
| **`C`** | Inverse regularization strength: how much training error you tolerate |
| **`decision_function`** | Signed distance from the hyperplane — a score, **not** a probability |
| **`predict_proba`** | Probability estimates; **absent** on `LinearSVC` |
| **Calibration** | Fitting a mapping from raw scores to real probabilities (Platt scaling, isotonic regression) |
| **Pipeline** | A scikit-learn object chaining steps so `predict()` runs vectorizer then classifier |
| **`classes_`** | The label values the fitted model knows: here `[0, 1]` |
| **joblib / pickle** | Serialization: saving a fitted model to disk and loading it back |
| **Confusion matrix** | Table of true vs. predicted classes; the source of all other metrics |
| **Precision / Recall / F1** | Of what I flagged, how much was right / of what was there, how much I caught / their harmonic mean |
| **Macro average** | Compute the metric per class, then average without weighting by class size |
| **Train / validation / test split** | Data used to fit / to tune / to report — the test set must be touched once |
| **Holdout** | Data deliberately withheld from training |
| **Data leakage** | Label information or test data contaminating training, inflating scores |
| **Near-duplicate / syndication** | The same story republished, possibly slightly edited — must be split as one unit |
| **Overfitting** | Memorizing the training data instead of learning general patterns |
| **Class imbalance** | Very unequal numbers of fake vs. real examples, which makes accuracy misleading |
| **Drift** | Real-world language and topics changing after training, degrading performance |
| **Bag of words** | Representation that counts words and discards their order |
| **Out-of-vocabulary (OOV)** | A token not in the 50,000-term vocabulary; contributes no signal |
| **SSRF** | Server-Side Request Forgery: abusing a server to reach internal resources |
| **CORS** | Browser rules for cross-origin requests; avoided in dev by the Vite proxy |
| **ASGI / Uvicorn** | The async Python web-server interface and the server implementing it |
| **Pydantic model** | A typed schema that validates JSON in and out of the API |
| **HTTP 422 / 500 / 502 / 503** | Bad input / server bug / upstream site failed / service unavailable (model missing) |
| **JSX** | JavaScript syntax extension for writing React components |
| **SPA** | Single-page application: one HTML page, navigation handled in JavaScript |
| **Hash routing** | Navigation via `#/path`, needing no server configuration |
| **Controlled component** | A React input whose value lives in state (`value` + `onChange`) |
| **`useState` / `useEffect` / `useMemo`** | React hooks for state, side effects, and cached derived values |
| **Component / props** | A reusable UI function / the values passed into it |
| **Remount via `key`** | Changing a `key` forces React to rebuild an element — used to replay animations |
| **`prefers-reduced-motion`** | A CSS media query that disables animation for users who ask for it |
| **ARIA roles** | Attributes (`role="status"`, `role="alert"`) that make dynamic UI accessible |
| **Fact-check status vocabulary** | `unverified` (no reliable evidence either way), `misleading` (context omitted/twisted), `false` (evidence shows it false), `verified` (evidence supports it) |

---

## Appendix A — Verified facts vs. unknowns

| Statement | Status |
| --- | --- |
| Pipeline is `TfidfVectorizer` → `LinearSVC`, steps named `tfidf` and `classifier` | ✅ Verified by loading the artifact |
| Vocabulary = 50,000; `coef_` = `(1, 50000)`; `intercept_` = `(1,)`; `classes_` = `[0, 1]` | ✅ Verified |
| Vectorizer params (`ngram_range=(1,2)`, `min_df=2`, `max_df=0.7`, `stop_words='english'`, `sublinear_tf=True`, `norm='l2'`, `lowercase=True`) | ✅ Verified |
| SVC params (`C=1.0`, `loss='squared_hinge'`, `penalty='l2'`, `random_state=42`, `dual='auto'`, `max_iter=1000`, `tol=1e-4`, `class_weight=None`) | ✅ Verified |
| No `predict_proba`; `decision_function` exists | ✅ Verified |
| Model file is 2,443,296 bytes at `Frontend/ml/best_model.pkl` | ✅ Verified |
| Loading under scikit-learn 1.6.1 emits no warnings; `predict` works | ✅ Verified |
| Backend constants, guards, endpoints, status codes, CORS origins | ✅ Verified by reading `backend/main.py` |
| Frontend routing, API wrapper, checker states, dashboard filters | ✅ Verified by reading `website/src/**` |
| claims.json: 114 entries, 113 active / 1 archived, statuses 77/33/2/1 active, 115 evidence links, last_updated 2026-10-29 | ✅ Verified by parsing the file and by `research/validate_claims.py` (0 errors, 0 warnings) |
| 102 added records each have a verbatim conclusion quote present in the fetched article text | ✅ Verified by `research/build_dataset.py` gate; 0 of 102 rejected |
| Cross-id near-duplicates in the shipped dataset | ✅ Verified none by `research/find_near_duplicates.py` (102 self-matches, 0 distinct-id pairs) |
| Fidelity of numbers/proper nouns in added records to their source text | ✅ Measured: mean 93.2%, 99/102 ≥70%; 3 below threshold are review prompts, not proven fabrications |
| Dashboard renders all 113 active records, pagination, filters, archive toggle, empty state | ✅ Verified in the browser against the dev server (DOM assertions; screenshots unavailable in the in-app browser, so pixel layout was not visually checked) |
| CSS tokens, 200 ms motion, three breakpoints, reduced-motion block | ✅ Verified by reading `styles.css` |
| Research scripts never train, never download, and embed their own caveats | ✅ Verified by reading both scripts |
| Four candidate datasets and their reported sizes/labels/licenses | ✅ Verified **as what the register reports** — ⚠️ the underlying figures are author-reported and unverified |
| Training dataset identity, size, class balance, language mix | ⚠️ **Unknown / not recorded** |
| Train/validation/test split used for the baseline | ⚠️ **Not documented** |
| Accuracy, precision, recall, F1, confusion matrix for the baseline | ⚠️ **None recorded anywhere in this repo — do not invent one** |
| scikit-learn version used to train the artifact | ⚠️ **Not recorded** (`_sklearn_version` absent); 1.6.1 is the runtime pin that loads cleanly |
| The 12 pre-existing claims.json records | ⚠️ **Not re-verified by this pipeline** — 5 cite AFP/Reuters hosts that reject automated fetchers; all 12 are labelled `legacy` in `research/claims_research_log.md` and exempted from the fetch-record check by an explicit id list |
| 8 harvested articles that never reached a reviewer | ⚠️ **Fetched but unreviewed** — dropped to keep the effort inside the target record count, not because they failed a check |
| Responsive layout at phone/tablet widths | ⚠️ **Read from the stylesheet only** — the in-app browser offered no renderable surface, so no screenshot was taken |
| Any runtime latency or throughput figure | ⚠️ Not benchmarked here |
| Indian-news dataset acquisition, training, candidate models, tests, CI, deployment | 🔜 **Future work — not implemented** |
| pandas used for data processing in this project | ❌ **Not true** — installed in the venv, imported nowhere |
| Streamlit app runnable out of the box | ❌ **Not true** — `streamlit` is not installed; `Frontend/requirements.txt` is empty |

---

## Appendix B — Command reference

All commands verified against `Frontend/README.md`. Python is the project venv: `C:\FakeNewsdetector\.venv\Scripts\python.exe`.

```bat
:: 1. Backend  (terminal A)
cd C:\FakeNewsdetector\Frontend\backend
C:\FakeNewsdetector\.venv\Scripts\python.exe -m uvicorn main:app --port 8000

:: 2. Website  (terminal B)
cd C:\FakeNewsdetector\Frontend\website
npm run dev                      :: → http://localhost:5173  (use "localhost", not 127.0.0.1)
npm run build                    :: production bundle → website/dist
npm run preview                  :: serve the built bundle

:: 3. Legacy Streamlit app (optional; streamlit is NOT installed yet)
cd C:\FakeNewsdetector\Frontend
C:\FakeNewsdetector\.venv\Scripts\python.exe -m pip install streamlit
C:\FakeNewsdetector\.venv\Scripts\python.exe -m streamlit run app.py

:: 4. Quick API checks
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/analyze -H "Content-Type: application/json" -d "{\"text\": \"<paste at least 30 characters of article text here>\"}"

:: 5. Dashboard dataset checks (offline, read-only, stdlib only)
cd C:\FakeNewsdetector\Frontend
C:\FakeNewsdetector\.venv\Scripts\python.exe research\validate_claims.py     :: needs only committed files → "OK", exit 0
C:\FakeNewsdetector\.venv\Scripts\python.exe research\check_fidelity.py      :: ⚠ needs the OS-temp article cache from fetch_articles.py
C:\FakeNewsdetector\.venv\Scripts\python.exe research\find_near_duplicates.py :: ⚠ needs research/batches/*.json; reports self-matches vs claims.json
:: C:\FakeNewsdetector\.venv\Scripts\python.exe research\build_dataset.py --dry-run  :: re-run the quote gate without writing

:: 6. Future dataset phase — written but NOT run; requires separate approval and an authorized CSV
:: python Frontend/ml/research/prepare_dataset.py --input <authorized-mapped.csv> --output-dir <outside-repo-dir> --record-type article
:: python Frontend/ml/research/evaluate_models.py --input <outside-repo-dir>/eligible.jsonl --record-type article --output <outside-repo-metrics.json>
```

Useful URLs: site `http://localhost:5173` · health `http://localhost:8000/api/health` · interactive API docs `http://localhost:8000/docs`.

---

## Appendix C — One-line file map

| File | One line |
| --- | --- |
| `app.py` | Legacy 549-line Streamlit app: same model, same SSRF guards, session-state results, site-wide disclaimer |
| `requirements.txt` | Empty legacy placeholder (0 bytes) |
| `ml/best_model.pkl` | The frozen TF-IDF → LinearSVC pipeline; server-side only; do not retrain or move |
| `ml/research/README.md` | Preparation-only policy, evaluation protocol, documented-but-unexecuted test cases, limitations |
| `ml/research/dataset_manifest.json` | Register of 4 candidate Indian-news datasets; no data acquired; all licenses unresolved |
| `ml/research/prepare_dataset.py` | Canonical CSV → `records.jsonl` / `eligible.jsonl` / `audit.json`; fail-closed eligibility; leakage review required |
| `ml/research/evaluate_models.py` | Scores existing models only; group + source holdouts; macro/per-class P/R/F1 + confusion matrix |
| `research/harvest_candidates.py` | Discovers fact-check article URLs from RSS feeds and listings → `candidates.tsv`; records hosts that reject fetchers |
| `research/fetch_articles.py` | Fetches each candidate, extracts largest-container body text, caps it, logs HTTP status/served title/chars |
| `research/split_batches.py` | Keeps articles with HTTP 200 and >400 chars, groups them into review batches |
| `research/REVIEW_INSTRUCTIONS.md` | The reviewer contract: schema, id rules, category and status vocabulary, the verbatim-quote gate, exclusion rules |
| `research/batches/batch_NN.json` | Reviewed records plus provenance (URL, served title, published date, verdict quote, status rationale) or an exclusion reason |
| `research/build_dataset.py` | Gates each record against the cached article text, then merges into `claims.json`; failures go to `rejected.tsv` |
| `research/validate_claims.py` | Schema, vocabulary, placeholder, uniqueness and fetch-record checks over the shipped dataset; exit 0 = clean |
| `research/check_fidelity.py` | Checks that numbers and proper nouns in a record appear in its source text; reports coverage |
| `research/find_near_duplicates.py` | Jaccard similarity over claim and explanation texts to catch reworded duplicates |
| `research/write_research_log.py` | Regenerates the audit log from pipeline state — funnel, per-source and per-record verification status |
| `research/claims_research_log.md` | The research log: every candidate's source URL and verification status, exclusions with reasons, blocked hosts |
| `backend/main.py` | FastAPI app (342 lines): `/api/health`, `/api/analyze`, SSRF guards, extraction, screening, disclaimers |
| `backend/requirements.txt` | fastapi, uvicorn[standard], scikit-learn 1.6.1 (exact), joblib, requests, beautifulsoup4 |
| `website/index.html` | Vite HTML shell with the `#root` mount point |
| `website/package.json` | react ^18.3.1, react-dom ^18.3.1; dev: vite ^5.4.11, @vitejs/plugin-react ^4.3.4; scripts dev/build/preview |
| `website/vite.config.js` | Port 5173 and the `/api` → `http://127.0.0.1:8000` proxy |
| `website/src/main.jsx` | React entry point; renders `<App/>` in StrictMode; imports `styles.css` |
| `website/src/App.jsx` | Hash router over four pages; remounts on navigation for the page transition |
| `website/src/api.js` | The only `fetch` wrapper: `analyzeText`, `analyzeUrl`, `checkHealth` |
| `website/src/styles.css` | Design tokens, all component styling, 200 ms motion, breakpoints, reduced-motion |
| `website/src/data/claims.json` | 114 curated claims (113 active) with statuses, evidence links and dates |
| `website/src/pages/Home.jsx` | Hero, backend status pill, fact-check strip, one "Paste or link" card, limitations band |
| `website/src/pages/Checker.jsx` | Text/URL modes, validation, four render states, result legend |
| `website/src/pages/Dashboard.jsx` | Summary cards, filters, sorting, archive toggle, "Show more" pagination, weekly workflow docs |
| `website/src/pages/About.jsx` | Seven numbered sections: what/why/how, model and stack, dashboard, screening-vs-fact-check, limitations |
| `website/src/components/Header.jsx` | Brand, nav links, active state, accessible mobile toggle |
| `website/src/components/Footer.jsx` | Site-wide disclaimer and stack credit |
| `website/src/components/ResultCard.jsx` | Verdict card: label styling, source info, disclaimer, character count |
| `website/src/components/StateBlocks.jsx` | `Spinner`, `ErrorBlock` (with retry), `EmptyBlock` — ARIA-annotated |
| `website/src/components/StatusBadge.jsx` | Four-status badge; unknown statuses fail safe to "Unverified claim" |
| `website/src/components/ClaimCard.jsx` | One claim: badge, category, explanation, provenance, evidence links, dates |
| `website/src/components/RecentFactChecks.jsx` | Homepage strip: eight latest human-reviewed claims, scroll-snap row, accessible scroll controls |
| `README.md` | Run & handoff guide: layout, prerequisites, start commands, troubleshooting, workflows |
| `PROJECT_STUDY_GUIDE.md` | This document |

---

*End of study guide. Every technical claim above was checked against the files in `Frontend/` on 2026-10-30. Where the project does not contain information — most importantly any performance metric or the identity of the training dataset — that is stated explicitly rather than filled in.*
