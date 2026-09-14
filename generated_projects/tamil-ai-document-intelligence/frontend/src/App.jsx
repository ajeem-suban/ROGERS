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
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold' }}>Tamil AI Document Intelligence</h1>
        <p style={{ color: '#94a3b8', marginTop: '0.5rem' }}>Tamil AI Document Intelligence is an intelligent Tamil-language document processing and retrieval platform. It ingests scanned documents and PDFs, extracts high-accuracy Tamil and English text using specialized OCR, indexes textual chunks into a semantic vector store, and enables users to perform natural language question answering grounded directly in document context via Retrieval-Augmented Generation (RAG). Note: add more tech stack</p>
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
