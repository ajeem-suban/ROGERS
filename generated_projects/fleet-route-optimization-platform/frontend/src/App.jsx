import React, { useState, useEffect } from 'react';

export default function App() {
  const [info, setInfo] = useState(null);

  useEffect(() => {
    fetch('/api/info')
      .then(res => res.json())
      .then(data => setInfo(data))
      .catch(() => {});
  }, []);

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: '#f8fafc', padding: '2rem', fontFamily: 'sans-serif' }}>
      <header style={{ maxWidth: '800px', margin: '0 auto', borderBottom: '1px solid #334155', paddingBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold' }}>Fleet Route Optimization Platform</h1>
        <p style={{ color: '#94a3b8', marginTop: '0.5rem' }}>Fleet Route Optimization Platform is a real-time fleet telematics and route optimization system designed for delivery operations. It aggregates live vehicle GPS telemetry, analyzes battery consumption and topography, computes dynamic multi-stop routes, and surfaces driver dispatch metrics through a responsive web and mobile operations console.</p>
      </header>
      <main style={{ maxWidth: '800px', margin: '2rem auto' }}>
        <div style={{ background: '#1e293b', borderRadius: '0.75rem', padding: '1.5rem', border: '1px solid #334155' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem' }}>System Status</h2>
          <p>Frontend: <strong>Active</strong></p>
          <p>Backend API Connected: <strong>{info ? 'Yes' : 'Checking...'}</strong></p>
        </div>
      </main>
    </div>
  );
}
