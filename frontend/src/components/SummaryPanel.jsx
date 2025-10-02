import React, { useState } from 'react';
import { summarizeDocument } from '../api/client';

export default function SummaryPanel({ fileId }) {
  const [summaryType, setSummaryType] = useState('general');
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    setSummary(null);
    try {
      const res = await summarizeDocument(fileId, summaryType);
      setSummary(res.summary);
    } catch (e) {
      setError(e?.response?.data?.error || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h3>Summarize</h3>
      <div className="row">
        <select value={summaryType} onChange={(e) => setSummaryType(e.target.value)}>
          <option value="general">General</option>
          <option value="brief">Brief</option>
          <option value="key_points">Key Points</option>
          <option value="structured">Structured</option>
        </select>
        <button onClick={generate} disabled={loading}>Generate</button>
      </div>
      {loading && <div>Generating…</div>}
      {error && <div className="error">{error}</div>}
      {summary && (
        <pre className="text">{summary}</pre>
      )}
    </div>
  );
}
