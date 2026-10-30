import { useCallback, useEffect, useRef, useState } from 'react';
import claimData from '../data/claims.json';
import StatusBadge from './StatusBadge.jsx';
import { EmptyBlock } from './StateBlocks.jsx';

const SHOW = 8;

// The section leads with the stories evidence shows to be wrong, then the rest.
const STATUS_RANK = { false: 0, misleading: 1, verified: 2, unverified: 3 };

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function evidenceUrl(claim) {
  const match = (claim.evidence || []).find((item) =>
    /^https?:\/\//i.test(String(item && item.url).trim())
  );
  return match || null;
}

// Anything without a well-formed date sorts last rather than throwing or
// pretending to be recent. A record that is re-reviewed resurfaces, so the
// later of the two dates wins.
function recencyDate(claim) {
  const dates = [claim.added_date, claim.review_date].filter((value) =>
    DATE_RE.test(String(value || ''))
  );
  return dates.sort().pop() || '';
}

function displayedDate(claim) {
  const added = String(claim.added_date || '');
  if (DATE_RE.test(added)) return { label: added, kind: 'Added' };
  const reviewed = String(claim.review_date || '');
  if (DATE_RE.test(reviewed)) return { label: reviewed, kind: 'Reviewed' };
  return { label: 'Date not recorded', kind: 'Added' };
}

function selectRecent(claims) {
  return claims
    .filter((claim) => claim && !claim.archived && String(claim.claim || '').trim())
    .sort((a, b) => {
      const rank = (STATUS_RANK[a.status] ?? 9) - (STATUS_RANK[b.status] ?? 9);
      if (rank !== 0) return rank;
      const dateA = recencyDate(a);
      const dateB = recencyDate(b);
      if (dateA !== dateB) return dateA < dateB ? 1 : -1;
      return String(a.id) < String(b.id) ? -1 : 1;
    })
    .slice(0, SHOW);
}

export default function RecentFactChecks() {
  const stripRef = useRef(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(true);

  const recent = selectRecent(claimData.claims);
  const totalActive = claimData.claims.filter((claim) => !claim.archived).length;

  const measure = useCallback(() => {
    const el = stripRef.current;
    if (!el) return;
    // Scroll snapping can settle on a fraction of a pixel, so the end checks
    // need a tolerance instead of an exact comparison.
    const scrollable = el.scrollWidth - el.clientWidth;
    setAtStart(el.scrollLeft <= 4);
    setAtEnd(scrollable <= 4 || el.scrollLeft >= scrollable - 4);
  }, []);

  useEffect(() => {
    const el = stripRef.current;
    if (!el) return;
    measure();
    el.addEventListener('scroll', measure, { passive: true });
    window.addEventListener('resize', measure);
    return () => {
      el.removeEventListener('scroll', measure);
      window.removeEventListener('resize', measure);
    };
  }, [measure, recent.length]);

  const nudge = (direction) => {
    const el = stripRef.current;
    if (!el) return;
    const card = el.querySelector('.fact-card');
    const gap = Number.parseFloat(window.getComputedStyle(el).columnGap) || 0;
    const step = card ? card.offsetWidth + gap : Math.round(el.clientWidth * 0.8);
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    el.scrollBy({ left: direction * step, behavior: reduceMotion ? 'auto' : 'smooth' });
  };

  return (
    <section className="recent-section" aria-labelledby="recent-heading">
      <div className="recent-head">
        <div>
          <p className="page-kicker">HUMAN-REVIEWED FACT-CHECKS</p>
          <h2 className="recent-title" id="recent-heading">
            Recently Fact-Checked News
          </h2>
          <p className="recent-sub">
            Stay informed about misleading and false stories recently reviewed
            by our team.
          </p>
        </div>

        {recent.length > 0 && (
          <div className="recent-side">
            <div className="recent-controls">
              <button
                type="button"
                className="round-btn"
                onClick={() => nudge(-1)}
                disabled={atStart}
                aria-label="Scroll to earlier fact-checks"
              >
                ‹
              </button>
              <button
                type="button"
                className="round-btn"
                onClick={() => nudge(1)}
                disabled={atEnd}
                aria-label="Scroll to more fact-checks"
              >
                ›
              </button>
            </div>
            <a className="recent-all" href="#/dashboard">
              All {totalActive} reviewed claims →
            </a>
          </div>
        )}
      </div>

      {recent.length === 0 ? (
        <EmptyBlock
          title="No fact-checks published yet"
          message="This strip fills itself from the reviewed claim records. Add entries to the dataset and the newest ones appear here."
        />
      ) : (
        <div
          className="recent-strip"
          ref={stripRef}
          role="region"
          aria-label="Recently fact-checked news, scrollable"
          tabIndex="0"
        >
          {recent.map((claim) => {
            const link = evidenceUrl(claim);
            const date = displayedDate(claim);

            return (
              <article className={`fact-card is-${claim.status}`} key={claim.id}>
                <div className="fact-card-top">
                  <StatusBadge status={claim.status} />
                  <span className="fact-category">{claim.category}</span>
                </div>

                <h3 className="fact-title">{claim.claim}</h3>

                <p className="fact-explain">{claim.explanation}</p>

                <p className="fact-by">
                  Fact-checked by <strong>{claim.fact_checker}</strong>
                </p>

                <div className="fact-foot">
                  <span className="fact-date">
                    {date.kind}: {date.label}
                  </span>
                  {link && (
                    <a
                      className="fact-link"
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Read the fact-check for: ${claim.claim}`}
                    >
                      Read fact-check ↗
                    </a>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      {recent.length > 0 && (
        <p className="recent-note">
          Every card here is a claim a person reviewed against named evidence,
          not a prediction from the screening model. Use the checker for that.
        </p>
      )}
    </section>
  );
}
