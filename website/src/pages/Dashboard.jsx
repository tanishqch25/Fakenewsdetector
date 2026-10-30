import { useEffect, useMemo, useState } from 'react';
import claimData from '../data/claims.json';
import ClaimCard from '../components/ClaimCard.jsx';
import StatusBadge from '../components/StatusBadge.jsx';
import { EmptyBlock } from '../components/StateBlocks.jsx';

const STATUS_ORDER = ['unverified', 'misleading', 'false', 'verified'];

const PAGE_SIZE = 24;

const SUMMARY_CARDS = [
  { key: 'total', label: 'Active reviewed' },
  { key: 'unverified', label: 'Unverified' },
  { key: 'misleading', label: 'Misleading' },
  { key: 'false', label: 'False per evidence' },
  { key: 'verified', label: 'Verified / supported' },
];

export default function Dashboard() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const [category, setCategory] = useState('all');
  const [sort, setSort] = useState('review');
  const [showArchived, setShowArchived] = useState(false);
  const [visible, setVisible] = useState(PAGE_SIZE);

  const claims = claimData.claims;

  const categories = useMemo(() => {
    const set = new Set(claims.map((claim) => claim.category));
    return ['all', ...Array.from(set).sort()];
  }, [claims]);

  const counts = useMemo(() => {
    const result = { total: 0 };
    for (const key of STATUS_ORDER) result[key] = 0;
    for (const claim of claims) {
      if (claim.archived) continue;
      result.total += 1;
      result[claim.status] = (result[claim.status] || 0) + 1;
    }
    return result;
  }, [claims]);

  const lastReviewed = useMemo(() => {
    const dates = claims
      .filter((claim) => !claim.archived)
      .map((claim) => claim.review_date)
      .sort();
    return dates.length ? dates[dates.length - 1] : '—';
  }, [claims]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();

    const list = claims.filter((claim) => {
      if (!showArchived && claim.archived) return false;
      if (status !== 'all' && claim.status !== status) return false;
      if (category !== 'all' && claim.category !== category) return false;
      if (
        q &&
        !claim.claim.toLowerCase().includes(q) &&
        !claim.explanation.toLowerCase().includes(q) &&
        !(claim.why_misleading || '').toLowerCase().includes(q)
      ) {
        return false;
      }
      return true;
    });

    const key = sort === 'added' ? 'added_date' : 'review_date';
    return list.sort((a, b) => (a[key] < b[key] ? 1 : a[key] > b[key] ? -1 : 0));
  }, [claims, query, status, category, sort, showArchived]);

  const listSignature = `${query}|${status}|${category}|${sort}|${showArchived}`;

  useEffect(() => {
    setVisible(PAGE_SIZE);
  }, [listSignature]);

  const shown = filtered.slice(0, visible);
  const hiddenCount = filtered.length - shown.length;

  return (
    <section className="dashboard">
      <header className="page-head">
        <p className="page-kicker">CLAIM DASHBOARD</p>
        <h2>Circulating claims, manually reviewed</h2>
        <p className="page-sub">
          A curated, human-maintained record of claims circulating online —
          separate from the ML screening model. Every entry states its
          verification status, the organisation that checked it, the evidence
          behind the verdict, and when it was last reviewed. Nothing here is
          monitored automatically.
        </p>
        <div className="dashboard-meta">
          <span>
            Dataset last updated: <strong>{claimData.last_updated}</strong>
          </span>
          <span>
            Most recent claim review: <strong>{lastReviewed}</strong>
          </span>
          <span>
            Archived entries: <strong>{claims.length - counts.total}</strong>
          </span>
        </div>
      </header>

      <div className="summary-grid">
        {SUMMARY_CARDS.map((card) => (
          <button
            key={card.key}
            type="button"
            className={`summary-card ${card.key} ${
              status === card.key ? 'active' : ''
            }`}
            onClick={() =>
              card.key === 'total'
                ? setStatus('all')
                : setStatus(status === card.key ? 'all' : card.key)
            }
          >
            <span className="summary-count">{counts[card.key] || 0}</span>
            <span className="summary-label">{card.label}</span>
          </button>
        ))}
      </div>

      <div className="filter-bar">
        <input
          type="search"
          aria-label="Search claims"
          placeholder="Search claims, explanations…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />

        <select
          aria-label="Filter by category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          {categories.map((item) => (
            <option key={item} value={item}>
              {item === 'all' ? 'All categories' : item}
            </option>
          ))}
        </select>

        <select
          aria-label="Filter by status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="all">All statuses</option>
          {STATUS_ORDER.map((item) => (
            <option key={item} value={item}>
              {item === 'false'
                ? 'False per cited evidence'
                : item === 'misleading'
                  ? 'Misleading framing'
                  : item === 'verified'
                    ? 'Verified / supported'
                    : 'Unverified claim'}
            </option>
          ))}
        </select>

        <select
          aria-label="Sort claims"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
        >
          <option value="review">Recently reviewed first</option>
          <option value="added">Recently added first</option>
        </select>

        <label className="filter-toggle">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
          />
          Show archived
        </label>

        <span className="result-count">
          {filtered.length} of {showArchived ? claims.length : counts.total}
        </span>
      </div>

      {filtered.length === 0 ? (
        <EmptyBlock
          title="No matching claims"
          message="Nothing matches this search or filter combination. Try clearing the filters or enabling archived entries."
        />
      ) : (
        <>
          <div className="claim-grid" key={listSignature}>
            {shown.map((claim) => (
              <ClaimCard key={claim.id} claim={claim} />
            ))}
          </div>

          <div className="claim-more">
            <span className="claim-more-count">
              Showing {shown.length} of {filtered.length} matching{' '}
              {filtered.length === 1 ? 'claim' : 'claims'}
            </span>
            {hiddenCount > 0 && (
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setVisible((count) => count + PAGE_SIZE)}
              >
                Show {Math.min(PAGE_SIZE, hiddenCount)} more
              </button>
            )}
          </div>
        </>
      )}

      <div className="update-band">
        <h4>Weekly manual update workflow</h4>
        <ol>
          <li>
            Open <code>website/src/data/claims.json</code> in any text editor.
          </li>
          <li>
            <strong>Add a new claim:</strong> copy an existing entry and fill
            in <code>id</code>, <code>claim</code>, <code>category</code>,{' '}
            <code>added_date</code>, <code>review_date</code> (both YYYY-MM-DD),{' '}
            <code>status</code>, <code>explanation</code>,{' '}
            <code>fact_checker</code>, <code>original_source</code>,{' '}
            <code>geo_scope</code>, <code>why_misleading</code> and{' '}
            <code>evidence</code> links.
          </li>
          <li>
            <strong>Update a status or review date:</strong> change{' '}
            <code>status</code> (<code>unverified</code> /{' '}
            <code>misleading</code> / <code>false</code> / <code>verified</code>)
            and set <code>review_date</code> to the day you actually re-checked
            it — never bump dates without reviewing.
          </li>
          <li>
            <strong>Replace evidence:</strong> edit the{' '}
            <code>evidence</code> array; keep one object per source with{' '}
            <code>source</code>, <code>title</code> and a direct{' '}
            <code>url</code>.
          </li>
          <li>
            <strong>Archive an outdated entry:</strong> set{' '}
            <code>"archived": true</code>. Archived entries stay in the file
            and history but hide from the default view.
          </li>
          <li>
            Bump <code>last_updated</code> at the top of the file, save, and
            refresh the site. No backend restart needed.
          </li>
        </ol>
        <p className="dataset-note">
          Status vocabulary: <StatusBadge status="unverified" /> insufficient
          reliable evidence either way · <StatusBadge status="misleading" />{' '}
          omits or twists context, with evidence ·{' '}
          <StatusBadge status="false" /> reliable evidence shows the claim
          false · <StatusBadge status="verified" /> reliable evidence supports
          the claim. A claim is never marked false because it is unpopular,
          unfamiliar, or flagged by the ML model. {claimData.note}
        </p>
      </div>
    </section>
  );
}
