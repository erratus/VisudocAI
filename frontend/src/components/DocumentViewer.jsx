import React, { useEffect, useState } from 'react';
import { analyzeDocument } from '../api/client';

export default function DocumentViewer({ fileId, onAnalysisComplete, initialData }) {
  const [data, setData] = useState(initialData || null);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (initialData) return;
      setLoading(true);
      setError(null);
      try {
        const res = await analyzeDocument(fileId);
        if (!cancelled) {
          setData(res);
          onAnalysisComplete?.(res);
        }
      } catch (e) {
        if (!cancelled) setError(e?.response?.data?.error || e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => { cancelled = true; };
  }, [fileId]);

  if (loading) return <div className="card">Analyzing document…</div>;
  if (error) return <div className="card error">{error}</div>;
  if (!data) return null;

  return (
    <div className="card viewer">
      <div className="meta">
        <span className={`badge`}>{data.document_type} ({Math.round((data.confidence || 0) * 100)}%)</span>
      </div>
      <pre className="text">{data.extracted_text}</pre>
    </div>
  );
}
