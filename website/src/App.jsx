import { useEffect, useState } from 'react';
import Header from './components/Header.jsx';
import Footer from './components/Footer.jsx';
import Home from './pages/Home.jsx';
import Checker from './pages/Checker.jsx';
import About from './pages/About.jsx';
import Dashboard from './pages/Dashboard.jsx';

const ROUTES = {
  '/': Home,
  '/checker': Checker,
  '/about': About,
  '/dashboard': Dashboard,
};

function currentPath() {
  const hash = window.location.hash.replace(/^#/, '');
  return hash || '/';
}

export default function App() {
  const [path, setPath] = useState(currentPath());

  useEffect(() => {
    const onHashChange = () => setPath(currentPath());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [path]);

  const Page = ROUTES[path] || Home;

  return (
    <div className="app-shell">
      <Header path={path} />
      <main className="main-content">
        <div className="page-enter" key={path}>
          <Page />
        </div>
      </main>
      <Footer />
    </div>
  );
}
