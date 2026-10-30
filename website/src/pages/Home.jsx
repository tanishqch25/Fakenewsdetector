import { useEffect, useState } from 'react';
import { checkHealth } from '../api.js';
import RecentFactChecks from '../components/RecentFactChecks.jsx';

export default function Home() {
  const [backend, setBackend] = useState('checking');

  useEffect(() => {
    let alive = true;

    checkHealth()
      .then(() => alive && setBackend('online'))
      .catch(() => alive && setBackend('offline'));

    return () => {
      alive = false;
    };
  }, []);

  return (
    <section className="home">
      <div className="hero">
        <p className="hero-kicker">CHECK A STORY · READ THE FACT-CHECKS</p>
        <h1 className="hero-title">
          Spot suspicious news
          <br />
          <span className="hero-accent">before it spreads.</span>
        </h1>
        <p className="hero-sub">
          Paste in a news story or drop its link and get an instant second
          opinion on how it reads — then browse the claims our reviewers have
          already checked against published evidence. It is a screening aid, not
          a fact-checker.
        </p>

        <div className="hero-actions">
          <a className="btn btn-primary" href="#/checker">
            Analyze a story
          </a>
          <a className="btn btn-outline" href="#/dashboard">
            Browse claim dashboard
          </a>
        </div>

        <div
          className={`backend-pill ${backend}`}
          role="status"
        >
          <span className="pill-dot" />
          {backend === 'checking' && 'Checking analysis backend…'}
          {backend === 'online' && 'Analysis backend online'}
          {backend === 'offline' && 'Backend offline — start the FastAPI server to run analyses'}
        </div>
      </div>

      <RecentFactChecks />

      <div className="feature-grid single">
        <div className="feature-card">
          <h3>Paste or link</h3>
          <p>
            Copy the text of a story into the box, or paste its web address and
            let us read it for you. A result comes back in a few seconds, and
            you can run as many stories as you like.
          </p>
        </div>
      </div>

      <div className="notice-band">
        <strong>Know the limits.</strong> This tool has never seen the truth of
        a story — only patterns from its training data. A “Potentially Real”
        label is not a guarantee of accuracy, and a “Potentially Fake” label is
        not proof of a lie. Use it to decide what deserves a closer look.
      </div>
    </section>
  );
}
