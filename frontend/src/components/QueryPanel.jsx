import React, { useState } from 'react';
import { queryDocument } from '../api/client';

export default function QueryPanel({ fileId }) {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const ask = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const res = await queryDocument(fileId, question.trim());
      setAnswer(res);
    } catch (e) {
      setError(e?.response?.data?.error || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h3>Ask a question</h3>
      <div className="row">
        <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Your question" />
        <button onClick={ask} disabled={loading}>Ask</button>
      </div>
      {loading && <div>Querying…</div>}
      {error && <div className="error">{error}</div>}
      {answer && (
        <div className="answer">
          <div><strong>Answer:</strong> {answer.answer}</div>
          {typeof answer.confidence === 'number' && (
            <div><strong>Confidence:</strong> {Math.round(answer.confidence * 100)}%</div>
          )}
        </div>
      )}
    </div>
  );
}
