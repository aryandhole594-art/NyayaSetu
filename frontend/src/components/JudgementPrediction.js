import React, { useState } from 'react';
import './JudgementPrediction.css';

const SAMPLE_FACTS = [
  {
    label: 'Consumer warranty dispute',
    text: 'My refrigerator stopped working within 3 months of purchase. The company has ignored repeated service requests and refused refund or replacement despite warranty coverage.',
  },
  {
    label: 'Anticipatory bail',
    text: 'A false criminal complaint has been filed after a business dispute. Police may arrest me, but I have cooperated and there is no recovery or custodial interrogation needed.',
  },
  {
    label: 'Service termination',
    text: 'I was terminated from a government service post without proper notice or departmental enquiry, despite having completed several years of continuous work.',
  },
];

function outcomeClass(outcome) {
  return String(outcome || 'uncertain').toLowerCase();
}

function JudgementPrediction() {
  const [facts, setFacts] = useState('');
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const runPrediction = async () => {
    if (!facts.trim()) {
      setError('Describe the material facts before running prediction.');
      return;
    }
    setLoading(true);
    setError('');
    setPrediction(null);
    try {
      const response = await fetch('http://127.0.0.1:5555/judgement-prediction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ facts }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Prediction failed.');
      }
      setPrediction(data);
    } catch (err) {
      setError(err.message || 'Cannot connect to judgement prediction backend.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="jp-root">
      <section className="jp-hero">
        <div className="jp-hero-copy">
          <span className="jp-kicker">Judgement Predictor Module</span>
          <h1>Compare your scenario with similar <span className="jp-highlight">court hearings</span></h1>
          <p>
            Share the facts and NyayaSetu surfaces comparable rulings and patterns to guide your next steps.
          </p>
        </div>
        <div className="jp-module-card">
          <span className="jp-section-label">What you get</span>
          <strong>{prediction ? `Outcome snapshot: ${prediction.predicted_outcome}` : ''}</strong>
          <p>
            {prediction
              ? `${prediction.success_probability}% likelihood based on similar hearings.`
              : 'Submit your facts to see outcome trends, risks, and next steps.'}
          </p>
          <ul className="jp-module-list">
            <li>Similar hearing highlights and outcomes</li>
            <li>Do / avoid guidance grounded in precedents</li>
            <li>Evidence checklist to strengthen your position</li>
          </ul>
        </div>
      </section>

      <section className="jp-workbench">
        <div className="jp-input-panel">
          <div className="jp-panel-head">
            <div>
              <span className="jp-section-label">Case Facts</span>
              <h2>Describe the dispute</h2>
            </div>
            <span className="jp-live-pill">Local precedents</span>
          </div>
          <textarea
            value={facts}
            onChange={(event) => setFacts(event.target.value)}
            placeholder="Example: I bought a washing machine under warranty. It failed within four months, the company ignored service requests, and I want refund or replacement..."
          />
          <div className="jp-actions">
            <button type="button" onClick={runPrediction} disabled={loading}>
              {loading ? 'Predicting...' : 'Predict Judgement'}
            </button>
            <button type="button" className="jp-clear" onClick={() => { setFacts(''); setPrediction(null); }}>
              Clear
            </button>
          </div>
          <div className="jp-samples">
            {SAMPLE_FACTS.map(sample => (
              <button key={sample.label} type="button" onClick={() => setFacts(sample.text)}>
                {sample.label}
              </button>
            ))}
          </div>
          {error && <div className="jp-error">{error}</div>}
        </div>

        <div className="jp-status-panel">
          {loading ? (
            <div className="jp-loader">
              <div className="jp-loader-ring" />
              <h3>Reading precedents</h3>
              <p>Retrieving similar hearings and comparing outcomes.</p>
            </div>
          ) : prediction ? (
            <PredictionResult prediction={prediction} />
          ) : (
            <div className="jp-empty">
              <span>01</span>
              <h3>Awaiting facts</h3>
              <p>The prediction will show similar cases, do and avoid guidance, misconceptions, and corpus stats.</p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

function PredictionResult({ prediction }) {
  const doItems = prediction.do_this?.length ? prediction.do_this : prediction.recommended_actions;
  const avoidItems = prediction.avoid_this?.length ? prediction.avoid_this : prediction.risk_factors;

  return (
    <div className="jp-result">
      <div className={`jp-outcome ${outcomeClass(prediction.predicted_outcome)}`}>
        <span>Predicted outcome</span>
        <strong>{prediction.predicted_outcome}</strong>
        <p>{prediction.issue_identified}</p>
      </div>

      <div className="jp-metrics">
        <Metric label="Success probability" value={`${prediction.success_probability}%`} />
        <Metric label="Confidence" value={`${prediction.confidence}%`} />
        <Metric label="Cases searched" value={prediction.corpus_stats?.cases_loaded || '0'} />
      </div>

      <section className="jp-note full">
        <span className="jp-section-label">Plain English</span>
        <p>{prediction.plain_english}</p>
      </section>

      <SimilarCases cases={prediction.similar_cases || []} />

      <section className="jp-decision-grid full">
        <ListCard title="Do this" items={doItems} tone="green" />
        <ListCard title="Avoid this" items={avoidItems} tone="red" />
      </section>

      <Misconceptions items={prediction.misconceptions || []} />

      {prediction.ratio_analysis?.length > 0 && (
        <section className="jp-note full">
          <span className="jp-section-label">Ratio Comparison</span>
          <div className="jp-ratio-list">
            {prediction.ratio_analysis.map((item, index) => (
              <div key={`${item.source_file}-${index}`} className="jp-ratio-item">
                <div>
                  <strong>{item.source_file}</strong>
                  <span>{item.leans}</span>
                </div>
                <p>{item.principle}</p>
                <small>{item.comparison}</small>
              </div>
            ))}
          </div>
        </section>
      )}

      <ListCard title="Evidence Needed" items={prediction.evidence_needed} tone="blue" />
      <StatsStrip prediction={prediction} />
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="jp-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ListCard({ title, items = [], tone }) {
  return (
    <section className={`jp-note jp-list-card ${tone || ''}`}>
      <span className="jp-section-label">{title}</span>
      <ul>
        {(items.length ? items : ['No items returned.']).map((item, index) => (
          <li key={`${item}-${index}`}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function SimilarCases({ cases }) {
  return (
    <section className="jp-note full">
      <span className="jp-section-label">Similar cases decided by courts</span>
      <div className="jp-cases">
        {cases.map((item, index) => {
          const percent = Math.round((item.similarity || 0) * 100);
          return (
            <article key={`${item.source_file}-${index}`} className="jp-case-card">
              <div className="jp-case-top">
                <span>{item.topic}</span>
                <strong>{percent}%</strong>
              </div>
              {item.case_verdict && (
                <div className={`jp-case-verdict ${String(item.case_verdict).toLowerCase()}`}>
                  Case verdict: {item.case_verdict}
                </div>
              )}
              <h4>{item.title}</h4>
              <p>{item.why_similar}</p>
              <div className="jp-match-track">
                <span style={{ width: `${Math.max(8, percent)}%` }} />
              </div>
              <small>{percent}% similar to your situation</small>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function Misconceptions({ items }) {
  if (!items.length) {
    return null;
  }
  return (
    <section className="jp-note full">
      <span className="jp-section-label">Common misconceptions - click to reveal</span>
      <div className="jp-misconceptions">
        {items.map((item, index) => (
          <details key={`${item.statement}-${index}`} className="jp-misconception">
            <summary>
              <span>"{item.statement}"</span>
              <strong>{item.verdict}</strong>
            </summary>
            <p>Check this against the retrieved precedents and the applicable statute before acting.</p>
          </details>
        ))}
      </div>
    </section>
  );
}

function StatsStrip({ prediction }) {
  const stats = [
    ['Corpus used', prediction.corpus_stats?.source || 'Local corpus'],
    ['Chunks retrieved', `${prediction.corpus_stats?.cases_retrieved || 0} / ${prediction.corpus_stats?.cases_loaded || 0}`],
    ['Confidence', `${prediction.confidence}%`],
    ['Limitation period', prediction.limitation_period || 'Verify'],
  ];
  return (
    <section className="jp-stats-strip full">
      {stats.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </section>
  );
}

export default JudgementPrediction;
