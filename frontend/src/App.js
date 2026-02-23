import React, { useState } from 'react';
import LoginPage from './LoginPage';
import Dashboard from './Dashboard';
import ResourceLibrary from './ResourceLibrary';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [page, setPage] = useState('dashboard');

  if (!isLoggedIn) {
    return <LoginPage onLoginSuccess={() => setIsLoggedIn(true)} />;
  }

  return (
    <div style={{ backgroundColor: '#0f1729', minHeight: '100vh' }}>
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 9999,
        padding: '12px 24px', backgroundColor: '#0a0f1e',
        borderBottom: '1px solid rgba(45, 212, 191, 0.2)',
        display: 'flex', gap: 24
      }}>
        <button
          onClick={() => setPage('dashboard')}
          style={{ color: page === 'dashboard' ? '#2dd4bf' : '#7b8aad', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 'bold', fontSize: 15 }}>
          Dashboard
        </button>
        <button
          onClick={() => setPage('resources')}
          style={{ color: page === 'resources' ? '#2dd4bf' : '#7b8aad', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 'bold', fontSize: 15 }}>
         Resources
        </button>
      </nav>

      <div style={{ paddingTop: 52 }}>
        {page === 'dashboard' && <Dashboard />}
        {page === 'resources' && <ResourceLibrary />}
      </div>
    </div>
  );
}

export default App;