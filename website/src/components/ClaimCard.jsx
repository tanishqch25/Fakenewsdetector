import StatusBadge from './StatusBadge.jsx';

export default function ClaimCard({ claim }) {
  return (
    <article className={`claim-card${claim.archived ? ' archived' : ''}`}>
      <div className="claim-top">
        <StatusBadge status={claim.status} />
        <span className="claim-category">{claim.category}</span>
        {claim.archived && <span className="archived-tag">ARCHIVED</span>}
      </div>

      <h3 className="claim-title">{claim.claim}</h3>

      <p className="claim-explain">{claim.explanation}</p>

      {claim.why_misleading && <p className="claim-why">{claim.why_misleading}</p>}

      <div className="claim-provenance">
        {claim.fact_checker && (
          <span>
            Fact-checked by: <strong>{claim.fact_checker}</strong>
          </span>
        )}
        {claim.original_source && (
          <span>
            Original source: <strong>{claim.original_source}</strong>
          </span>
        )}
        {claim.geo_scope && (
          <span>
            Scope: <strong>{claim.geo_scope}</strong>
          </span>
        )}
      </div>

      {claim.evidence && claim.evidence.length > 0 && (
        <div className="claim-evidence">
          <span className="evidence-label">Evidence — open and inspect</span>
          <ul>
            {claim.evidence.map((item, index) => (
              <li key={index}>
                <a href={item.url} target="_blank" rel="noopener noreferrer">
                  {item.source}
                  {item.title ? ` — ${item.title}` : ''}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="claim-foot">
        <span>Added: {claim.added_date}</span>
        <span>Last reviewed: {claim.review_date}</span>
      </div>
    </article>
  );
}
