# Reviewer instructions — turning cached fact-check articles into dashboard records

You are one of several parallel reviewers. You get **one batch file** of already-fetched
fact-check articles and you must turn each usable article into a record for
`Frontend/website/src/data/claims.json`.

You have **no network access for this task** and must not try to fetch anything. Everything
you need is in the batch file. Every conclusion you write must be traceable to text that is
literally present in the cached article you were given.

---

## Input

`Frontend/research/cache/batch_NN.json` — a JSON array. Each element:

```json
{
  "url":          "https://…",            // the article, already fetched with HTTP 200
  "source":       "Alt News",             // organisation name to use verbatim
  "title":        "…",                    // headline as served (may carry a site suffix)
  "feed_title":   "…",                    // headline from the RSS feed / listing
  "published":    "2026-10-22",           // may be empty
  "feed_pubdate": "2026-10-22",           // may be empty
  "text":         "…"                     // extracted article text, possibly truncated in the middle
}
```

`text` is capped: long articles keep the first ~3000 chars and the last ~2400 chars joined by
a literal `...[MIDDLE TRUNCATED]...` marker. **You may only quote and rely on what you can
actually see.** Never reconstruct or guess the missing middle.

## Output

Write exactly one file: `Frontend/research/batches/batch_NN.json` (same NN as your input).

```json
{
  "batch": NN,
  "records": [
    {
      "record":     { …claims.json schema, see below… },
      "provenance": {
        "url":              "…identical to the batch url…",
        "served_title":     "…the title field verbatim…",
        "published_date":   "YYYY-MM-DD or empty string",
        "verdict_quote":    "…verbatim excerpt, <=30 words…",
        "status_rationale": "…why this status and not a neighbouring one…"
      }
    }
  ],
  "excluded": [
    { "url": "…", "reason": "…short, factual reason…" }
  ]
}
```

Every article in the batch must end up either in `records` or in `excluded`. Nothing else.

---

## The record schema

Key order matters (it is the order the file is written in). `why_misleading` is included only
when it has content.

```json
{
  "id":              "kebab-case-4-to-80-chars",
  "claim":           "Neutral one-sentence description of the claim that was circulating.",
  "status":          "false | misleading | unverified | verified",
  "category":        "one of the fixed list below",
  "added_date":      "2026-10-29",
  "review_date":     "2026-10-29",
  "explanation":     "Two or three sentences: what the fact-check found and how it found out.",
  "why_misleading":  "Only for status=misleading. What the framing omits or twists.",
  "original_source": "Where the claim was circulating, e.g. \"Facebook posts\", \"WhatsApp forwards\".",
  "fact_checker":    "The organisation name, exactly as in the batch 'source' field.",
  "geo_scope":       "e.g. \"India\", \"India (Maharashtra)\", \"United States\", \"Global\".",
  "archived":        false,
  "evidence": [
    { "source": "same as fact_checker", "title": "article headline", "url": "the batch url" }
  ]
}
```

### `id`
Lowercase `a-z0-9-` only, 4–80 chars, must start with a letter or digit. Make it descriptive
and globally unique — include the subject and, where useful, the year:
`adani-port-fine-fake-notice`, `cyclone-arnab-old-video-vizag`. Do not include the source name.

### `category` — pick exactly one
`politics` · `elections` · `communal` · `ai-media` · `health` · `science` · `environment` ·
`crime` · `scam` · `society` · `world` · `finance` · `entertainment` · `religion`

Guidance: `ai-media` for deepfakes and AI-generated images/video/audio; `communal` for
claims engineered to inflame religious or ethnic tension; `scam` for fraud/impersonation/
fake-scheme stories; `society` as the fallback for general viral claims that fit nothing else.

### `status` — this is the part that must not drift

| status | use when |
|---|---|
| `false` | the fact-check concludes the claim/video/image is false, fabricated, or an unrelated old item passed off as current |
| `misleading` | something real is presented in a way that omits or twists context — including "partly true", "old video shared with new context", "doctored", "clip shared without context" |
| `verified` | the fact-check concludes the claim **is true / is supported** |
| `unverified` | the fact-check explicitly could not establish truth or falsity |

Rules:

- Follow the article's own conclusion. Read the verdict sentence, do not infer it from the headline alone.
- Headlines like *"Fact Check: video is old and unrelated"* → usually `misleading` **if** the video itself is genuine but the context is wrong; `false` if the article says the underlying claim/event is fabricated or never happened. Where the article states both, prefer the wording of its explicit conclusion and record your reasoning in `status_rationale`.
- **Do not use `verified` just because an article discusses the claim.** Use it only when the article concludes the claim is true as presented. `verified` records must have a non-empty `status_rationale`.
- Never compress a genuinely nuanced verdict into `false`. If the article says "partly true but misleading", the status is `misleading`.
- `misleading` records must have a non-empty `why_misleading`.

### `verdict_quote` — the hard gate

Copy a **contiguous, verbatim excerpt of at most 30 words** from the cached `text` that
carries the article's conclusion. A build script checks that this string appears in the
cached article text after folding curly quotes/dashes and collapsing whitespace. So:

- take it from **inside one paragraph** — do not join two paragraphs, the cached text has a
  newline between them;
- do not span the `...[MIDDLE TRUNCATED]...` marker;
- do not correct the article's spelling, punctuation or capitalisation;
- prefer the sentence that actually states the verdict ("The claim is false.", "…we found the
  video dates back to 2019…", "Conclusion: Misleading").

If you cannot find such a sentence in the visible text, **exclude the article** rather than
invent a quote.

---

## What to exclude

Put these in `excluded` with a short reason:

- not a fact-check (straight news report, opinion, explainer, sports, business brief, listicle);
- the article's conclusion is not visible in the cached text (truncation cut it off);
- the article only aggregates other outlets' checks without reaching its own conclusion;
- paywalled / stub content with no substantive text;
- the same claim already covered by another article in your batch (keep the more substantive one, exclude the other, reason `"duplicate of <url>"`);
- the claim is primarily graphic violence, sexual content, or targeted abuse of a named private individual — the dashboard is educational and should not amplify it.

Do not exclude an article merely because it is old or about another country.

---

## Writing style

- `claim`: neutral, third person, no verdict language, no ALL CAPS, no quotation marks around
  the whole sentence. Describe what was circulating: *"A video shows …"*, *"A post claims …"*,
  *"An image is shared as …"*. One sentence, under ~180 chars.
- `explanation`: your own words. **Do not copy sentences from the article** beyond the short
  `verdict_quote` in provenance (which is not published). Say what was checked and what was
  found, and name the concrete evidence the article cites (reverse image search, official
  statement, government data, geolocation, the person who made the statement).
- No personal data: name public figures, officials and organisations, but never private
  individuals, and never include the names of victims, accused persons in unproven allegations,
  or minors.
- No sensational repetition of harmful falsehoods. Describe the claim once, neutrally.
- Do not use em dashes as a stylistic tic; write plainly.
- `original_source`: what the article says the claim was circulating on. If the article does
  not say, use `"Social media posts"`.
- `geo_scope`: the country the claim is about, not the country of the fact-checker. Add a state
  or region in parentheses when the article is specific. Use `"Global"` for claims with no
  single country.

### `evidence[0].title`

Use the article headline. Strip a trailing site suffix such as ` – Alt News`, ` | BOOM`,
` - FACTLY`, ` - India Today`, ` | The Quint`, ` - Newschecker` when present, because the
`source` field already names the site. Keep the rest of the headline exactly as served.

---

## Before you write the file

1. Re-read every record against the rules above.
2. Confirm each `verdict_quote` is copied character-for-character from that article's `text`.
3. Confirm every `records[].provenance.url` and `records[].record.evidence[0].url` equals the
   batch `url` for the same article, with no typo and no trailing-slash difference.
4. Confirm no two records in your file share an `id`.
5. Confirm the JSON parses: `python -c "import json;json.load(open(PATH,encoding='utf-8'))"`
   using `C:/FakeNewsdetector/.venv/Scripts/python.exe`.
6. Report back only: batch number, records written, articles excluded, and any article where
   the verdict was genuinely ambiguous.
