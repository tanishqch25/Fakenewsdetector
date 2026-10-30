import { useState } from 'react';

const LINKS = [
  { to: '/', label: 'Home' },
  { to: '/checker', label: 'News Checker' },
  { to: '/dashboard', label: 'Claim Dashboard' },
  { to: '/about', label: 'About Project' },
];

export default function Header({ path }) {
  const [open, setOpen] = useState(false);

  return (
    <header className="site-header">
      <div className="header-inner">
        <a
          className="brand"
          href="#/"
          onClick={() => setOpen(false)}
        >
          <span className="brand-mark">FN</span>
          <span className="brand-text">
            Fake News <em>Analyzer</em>
          </span>
        </a>

        <button
          className="nav-toggle"
          aria-label="Toggle navigation"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          <span />
          <span />
          <span />
        </button>

        <nav className={`site-nav ${open ? 'is-open' : ''}`}>
          {LINKS.map((link) => (
            <a
              key={link.to}
              href={`#${link.to}`}
              className={path === link.to ? 'nav-link active' : 'nav-link'}
              onClick={() => setOpen(false)}
            >
              {link.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  );
}
