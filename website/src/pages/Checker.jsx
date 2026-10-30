import { useState } from 'react';
import { analyzeText, analyzeUrl } from '../api.js';
import ResultCard from '../components/ResultCard.jsx';
import { Spinner, ErrorBlock, EmptyBlock } from '../components/StateBlocks.jsx';

const MIN_TEXT = 30;

export default function Checker() {
  const [mode, setMode] = useState('text');
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const canSubmit =
    !loading &&
    (mode === 'text'
      ? text.trim().length >= MIN_TEXT
      : url.trim().length > 0);

  async function handleSubmit(event) {
    event.preventDefault();

    if (!canSubmit) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response =
        mode === 'text' ? await analyzeText(text.trim()) : await analyzeUrl(url.trim());
      setResult(response);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function switchMode(next) {
    setMode(next);
    setResult(null);
    setError(null);
  }

  return (
    <section className="checker">
      <header className="page-head">
        <p className="page-kicker">NEWS CHECKER</p>
        <h2>Analyze a story</h2>
        <p className="page-sub">
          Paste article text or provide a public article URL. Results describe
          writing patterns, not facts.
        </p>
      </header>

      <div className="checker-grid">
        <form className="input-panel" onSubmit={handleSubmit}>
          <div className="mode-toggle" role="tablist" aria-label="Input method">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'text'}
              className={mode === 'text' ? 'mode-btn active' : 'mode-btn'}
              onClick={() => switchMode('text')}
            >
              News Text
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'url'}
              className={mode === 'url' ? 'mode-btn active' : 'mode-btn'}
              onClick={() => switchMode('url')}
            >
              Article URL
            </button>
          </div>

          {mode === 'text' ? (
            <>
              <label className="field-label" htmlFor="news-text">
                News headline and article
              </label>
              <textarea
                id="news-text"
                rows={12}
                maxLength={20000}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste the headline and article text here…"
              />
              <p className="field-hint">
                {text.trim().length.toLocaleString()} / 20,000 characters ·
                minimum {MIN_TEXT}. Avoid submitting personal information.
              </p>
            </>
          ) : (
            <>
              <label className="field-label" htmlFor="news-url">
                Article URL
              </label>
              <input
                id="news-url"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/news/article"
              />
              <p className="field-note">
                The server tries to extract readable article text. Some sites
                block automated access or require JavaScript — if extraction
                fails, paste the article text instead.
              </p>
            </>
          )}

          <button type="submit" className="btn btn-primary btn-wide" disabled={!canSubmit}>
            {loading ? 'Analyzing…' : 'Analyze story'}
          </button>
        </form>

        <div className="result-panel">
          <p className="page-kicker">SCREENING RESULT</p>

          {loading && <Spinner />}

          {!loading && error && (
            <ErrorBlock
              message={error}
              onRetry={() => handleSubmit({ preventDefault: () => {} })}
            />
          )}

          {!loading && !error && !result && (
            <EmptyBlock
              title="No analysis yet"
              message="Your screening result will appear here after you analyze a story."
            />
          )}

          {!loading && !error && result && <ResultCard result={result} />}
        </div>
      </div>

      <div className="type-legend">
        <h4>Reading the result</h4>
        <p>
          <span className="chip chip-fake">Potentially Fake</span> — the text
          resembles fake-news patterns from the training data. Treat it as
          unverified until credible sources confirm it.
        </p>
        <p>
          <span className="chip chip-real">Potentially Real</span> — the writing
          style resembles real news from the training data. This is{' '}
          <em>not</em> a guarantee that the claims are true.
        </p>
        <p>
          For human-reviewed misinformation, use the{' '}
          <a href="#/dashboard">Claim Dashboard</a>, which keeps four statuses
          clearly apart: unverified, misleading framing, false per cited
          evidence, and verified / supported.
        </p>
      </div>
    </section>
  );
}
