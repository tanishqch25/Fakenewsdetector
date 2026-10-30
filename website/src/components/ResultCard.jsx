export default function ResultCard({ result }) {
  const isFake = result.label === 0;

  return (
    <div className={`result-card ${isFake ? 'result-fake' : 'result-real'}`}>
      <div className="result-head">
        <span className="result-kicker">SCREENING RESULT</span>
        <h3 className="result-verdict">
          {isFake ? '🚩' : '📰'} {result.verdict}
        </h3>
      </div>

      {result.input_mode === 'url' && (
        <div className="result-source">
          {result.source_title && (
            <p className="source-title">{result.source_title}</p>
          )}
          {result.source_hostname && (
            <p className="source-host">Source website: {result.source_hostname}</p>
          )}
        </div>
      )}

      <p className="result-explain">{result.disclaimer}</p>

      {result.extracted_chars != null && (
        <p className="result-meta">
          {result.extracted_chars.toLocaleString()} characters analysed
        </p>
      )}
    </div>
  );
}
