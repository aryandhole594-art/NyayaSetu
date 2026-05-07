import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import './LegalQuery.css';

function RenderText({ text }) {
  if (text === null || text === undefined) return null;
  const safeText = typeof text === 'string' ? text : JSON.stringify(text, null, 2);
  const lines = safeText.split('\n');
  return (
    <div className="rendered-text">
      {lines.map((line, i) => {
        if (!line.trim()) return <br key={i} />;
        if (line.startsWith('# ')) return <h2 key={i}>{line.slice(2)}</h2>;
        if (line.startsWith('## ')) return <h3 key={i}>{line.slice(3)}</h3>;
        if (line.startsWith('### ')) return <h4 key={i}>{line.slice(4)}</h4>;
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return <li key={i}>{renderInline(line.slice(2))}</li>;
        }
        return <p key={i}>{renderInline(line)}</p>;
      })}
    </div>
  );
}

function renderInline(text) {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, i) =>
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : part
  );
}

function normalizeTimelineTimeframe(step, index) {
  const raw = String(step?.timeframe || '').trim();
  if (!raw || raw.toLowerCase() === 'next' || raw.toLowerCase() === 'day 0') {
    return `Day ${index + 1}-${index + 2}`;
  }
  return raw;
}

function UrgencyBadge({ urgency }) {
  if (!urgency) return null;
  return (
    <div className={`urgency-banner ${urgency.level?.toLowerCase() || ''}`} style={{ borderColor: urgency.color }}>
      <span className="urgency-level">{urgency.level}</span>
      <span className="urgency-msg">{urgency.message}</span>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="typing-indicator" aria-label="AI is thinking">
      <div className="avatar ai" style={{ fontSize: '1.2rem' }}>AI</div>
      <div className="typing-bubble">
        <span className="dot" /><span className="dot" /><span className="dot" />
      </div>
      <span className="typing-label">Analyzing your legal scenario...</span>
    </div>
  );
}

const QUICK_SCENARIOS = [
  { label: 'Road Accident', text: 'I was injured in a road accident caused by another driver. What are my legal rights and how do I claim compensation?' },
  { label: 'Unlawful Arrest', text: 'Police arrested me without showing a warrant and are refusing to let me call my lawyer. What are my rights?' },
  { label: 'Illegal Eviction', text: 'My landlord is forcefully evicting me without giving proper notice. What legal protection do I have?' },
  { label: 'Salary Not Paid', text: 'My employer has not paid my salary for 3 months and is threatening to fire me. What can I do legally?' },
  { label: 'Consumer Fraud', text: 'I bought a product online that was defective and the seller is refusing to refund me. What are my rights?' },
  { label: 'School Denied Admission', text: 'A private school refused to admit my child citing caste. Is this legal? What action can I take?' },
];

function ArticleCard({ article, index }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="article-card" style={{ animationDelay: `${index * 80}ms` }}>
      <button className="article-card-header" onClick={() => setExpanded(e => !e)} aria-expanded={expanded}>
        <div className="article-number-badge">{article.number || 'Article'}</div>
        <div className="article-card-meta">
          <div className="article-card-title">{article.title}</div>
          {article.relevance && !expanded && (
            <div className="article-card-preview">{article.relevance.slice(0, 92)}...</div>
          )}
        </div>
        <span className="expand-btn" aria-hidden="true">{expanded ? 'Hide' : 'View'}</span>
      </button>
      {expanded && (
        <div className="article-card-body">
          <p>{article.relevance}</p>
        </div>
      )}
    </div>
  );
}

function SectionCard({ section, index }) {
  const [expanded, setExpanded] = useState(false);
  const breakdown = section.score_breakdown;
  const showBreakdown = breakdown && Number.isFinite(breakdown.bm25) && Number.isFinite(breakdown.cosine);
  const bm25Part = showBreakdown ? breakdown.bm25 * 0.6 : 0;
  const cosinePart = showBreakdown ? breakdown.cosine * 0.4 * 10 : 0;
  const titlePart = showBreakdown ? breakdown.title_boost : 0;
  const total = bm25Part + cosinePart + titlePart;
  const parts = [
    { key: 'bm25', label: 'BM25', value: bm25Part },
    { key: 'cosine', label: 'Cosine', value: cosinePart },
    { key: 'title', label: 'Title', value: titlePart },
  ];

  return (
    <div className="section-card" style={{ animationDelay: `${index * 80}ms` }}>
      <button className="section-card-header" onClick={() => setExpanded(e => !e)} aria-expanded={expanded}>
        <div className="section-card-primary">
          <div className="section-title">{section.title}</div>
          {section.article_numbers?.length > 0 && (
            <div className="section-articles">
              {section.article_numbers.map(n => (
                <span key={n} className="article-tag">Art. {n}</span>
              ))}
            </div>
          )}
        </div>
        <div className="section-score-wrap">
          <div className="relevance-bar">
            <div
              className="relevance-fill"
              style={{ width: `${Math.min(100, section.score * 8)}%` }}
            />
          </div>
          <span className="relevance-label">Relevance</span>
          {showBreakdown && (
            <div className="score-breakdown">
              <div className="breakdown-bar">
                {parts.map(p => (
                  <div
                    key={p.key}
                    className={`breakdown-seg ${p.key}`}
                    style={{ width: `${total ? (p.value / total) * 100 : 0}%` }}
                  />
                ))}
              </div>
              <div className="breakdown-legend">
                {parts.map(p => (
                  <span key={p.key} className={`legend-item ${p.key}`}>
                    <span className="legend-swatch" />
                    {p.label}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
        <span className="expand-btn" aria-hidden="true">{expanded ? 'Hide' : 'Open'}</span>
      </button>
      {expanded && (
        <div className="section-card-body">
          {breakdown?.matched_terms?.length > 0 && (
            <div className="matched-terms">
              <span className="matched-label">Matched terms</span>
              <div className="matched-tags">
                {breakdown.matched_terms.map(t => (
                  <span key={t} className="matched-tag">{t}</span>
                ))}
              </div>
            </div>
          )}
          <pre className="constitution-text">{section.excerpt}</pre>
        </div>
      )}
    </div>
  );
}

function StructuredPanel({ structured, urgency, result, onFollowup }) {
  if (!structured) {
    return <p className="empty-state">No structured brief available.</p>;
  }

  const meta = structured.meta || {};
  const summary = structured.summary || {};
  const plain = structured.plain_words || {};
  const parties = structured.parties || {};
  const laws = structured.applicable_laws || [];
  const rights = structured.rights_vs_limits?.rights || [];
  const limits = structured.rights_vs_limits?.limits || [];
  const steps = structured.steps || [];
  const forum = structured.forum_comparison || {};
  const relief = structured.relief_spectrum || [];
  const strength = structured.case_strength || [];
  const costBenefit = structured.cost_benefit || {};
  const clauseRisks = structured.clause_risks || [];
  const evidence = structured.evidence_checklist || [];
  const doList = structured.do_and_avoid?.do || [];
  const avoidList = structured.do_and_avoid?.avoid || [];
  const misconceptions = structured.misconceptions || [];
  const similar = structured.similar_cases || [];
  const followups = structured.followups || [];
  const snapshotRows = [
    ['Domain', meta.domain || 'General legal query'],
    ['Confidence', typeof meta.confidence === 'number' ? `${meta.confidence}%` : 'Unknown'],
    ['Likely forum', parties.forum || 'To be confirmed'],
    ['Provider', meta.llm_provider || 'AI assisted'],
    ['Urgency', urgency?.level || 'Standard'],
    ['Corpus fit', meta.in_scope === false ? 'Out of corpus' : 'In constitutional scope'],
  ];

  return (
    <div className="brief-wrap">
      <section className="brief-hero-card">
        <div className="brief-hero-copy">
          <span className="brief-kicker">Strategic brief</span>
          <h3 className="brief-title">{meta.case_type || 'Legal Brief'}</h3>
          <p className="brief-summary-line">{summary.one_line || 'Structured guidance prepared from the legal context available.'}</p>
          {plain.short_explanation && <p className="brief-plain">{plain.short_explanation}</p>}
        </div>
        <div className="brief-hero-side">
          {summary.signal && <span className="signal-chip">{summary.signal}</span>}
          {urgency?.level && <span className={`urgency-pill ${urgency.level.toLowerCase()}`}>{urgency.level}</span>}
          <div className="brief-meta">
            {meta.domain && <span className="meta-chip">Domain: {meta.domain}</span>}
            {typeof meta.confidence === 'number' && <span className="meta-chip">Confidence: {meta.confidence}%</span>}
            {meta.in_scope === false && <span className="meta-chip warning">Out of corpus</span>}
          </div>
        </div>
      </section>

      <div className="brief-grid brief-grid-top">
        <section className="brief-card brief-card-spotlight">
          <div className="section-heading">
            <h4>Case Snapshot</h4>
            <span className="section-caption">Quick facts at a glance</span>
          </div>
          <div className="snapshot-table-wrap">
            <table className="snapshot-table">
              <tbody>
                {snapshotRows.map(([label, value]) => (
                  <tr key={label}>
                    <th>{label}</th>
                    <td>{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="brief-card">
          <div className="section-heading">
            <h4>Entity Map</h4>
            <span className="section-caption">Who is involved and where this likely goes</span>
          </div>
          <div className="entity-flow">
            <div className="entity-node">
              <span className="entity-label">Complainant</span>
              <strong>{parties.complainant || 'You'}</strong>
            </div>
            <div className="entity-connector" />
            <div className="entity-node">
              <span className="entity-label">Opposite party</span>
              <strong>{parties.opposite_party || 'Respondent'}</strong>
            </div>
            <div className="entity-connector" />
            <div className="entity-node">
              <span className="entity-label">Forum</span>
              <strong>{parties.forum || 'Authority'}</strong>
            </div>
          </div>
          <div className="entity-subject-panel">
            <span className="entity-label">Subject</span>
            <p>{parties.subject || result.query || 'Legal issue summary unavailable.'}</p>
          </div>
        </section>
      </div>

      {structured.compliance_checklist?.length > 0 && (
        <section className="brief-card">
          <div className="section-heading">
            <h4>Compliance Checklist</h4>
            <span className="section-caption">Requirements based on business type and employee count</span>
          </div>
          <div className="checklist-grid">
            {structured.compliance_checklist.map((item, i) => (
              <div key={`${item.act}-${i}`} className={`check-card ${item.status || ''}`} style={{ borderColor: item.status === 'applicable' ? 'var(--lq-success)' : 'var(--lq-amber)' }}>
                <strong>{item.status_symbol || '-'} {item.act}</strong>
                <p style={{ marginTop: '8px', color: 'var(--lq-text-soft)' }}>{item.requirement_summary}</p>
                {item.sources?.length > 0 && (
                  <div style={{ marginTop: '12px' }}>
                    <span className="meta-chip" style={{ fontSize: '0.75rem' }}>Sources: {item.sources.join(', ')}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="brief-card">
        <div className="section-heading">
          <h4>Action Timeline</h4>
          <span className="section-caption">A clear sequence of what to do next</span>
        </div>
        {steps.length > 0 ? (
          <div className="timeline-horizontal">
            <div className="timeline-rail" />
            {steps.map((s, i) => (
              <div key={`${s.action || 'step'}-${i}`} className="timeline-stop">
                <div className="timeline-marker">
                  <span className="timeline-index">{i + 1}</span>
                </div>
                <div className="timeline-time">{normalizeTimelineTimeframe(s, i)}</div>
                <div className="timeline-card">
                  <div className="timeline-title">{s.action || 'Step'}</div>
                  <div className="timeline-meta">Action</div>
                  {s.why && <p className="timeline-note">{s.why}</p>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-state">No steps available.</p>
        )}
      </section>

      <div className="brief-grid">
        <section className="brief-card">
          <div className="section-heading">
            <h4>Applicable Laws</h4>
            <span className="section-caption">Primary laws supporting this scenario</span>
          </div>
          {laws.length > 0 ? (
            <div className="law-grid">
              {laws.map((law, i) => (
                <div key={`${law.name}-${i}`} className="law-card">
                  <div className="law-card-head">
                    <strong>{law.name}</strong>
                    {law.type && <span className="law-type">{law.type}</span>}
                  </div>
                  {law.why_it_applies && <p>{law.why_it_applies}</p>}
                  {law.citations?.length > 0 && (
                    <div className="law-citations">
                      {law.citations.map(c => (
                        <span key={c} className="law-chip">{c}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-state">No laws extracted for this query.</p>
          )}
        </section>

        <section className="brief-card">
          <div className="section-heading">
            <h4>Case Strength</h4>
            <span className="section-caption">Signals that can help or weaken the matter</span>
          </div>
          <div className="strength-grid">
            {strength.length > 0 ? strength.map((s, i) => (
              <div key={`${s.label}-${i}`} className="strength-item">
                <div className="strength-label">
                  <span>{s.label}</span>
                  <span className="strength-value">{Math.min(100, s.score || 0)}%</span>
                </div>
                <div className="strength-bar">
                  <div className="strength-fill" style={{ width: `${Math.min(100, s.score || 0)}%` }} />
                </div>
                <div className="strength-note">{s.note || 'No note available.'}</div>
              </div>
            )) : (
              <div className="strength-empty">
                <span className="empty-number">01</span>
                <p>No strength signals available yet. Evidence and documents will shape this most.</p>
              </div>
            )}
          </div>
        </section>
      </div>

      <div className="brief-grid">
        <section className="brief-card">
          <div className="section-heading">
            <h4>Rights You Can Claim</h4>
            <span className="section-caption">The strongest rights visible from the current facts</span>
          </div>
          <div className="pill-list">
            {rights.length > 0 ? rights.map((item, i) => (
              <div key={`${item}-${i}`} className="info-pill positive">{item}</div>
            )) : <p className="empty-state">No rights extracted.</p>}
          </div>
        </section>

        <section className="brief-card">
          <div className="section-heading">
            <h4>Limits and Watchouts</h4>
            <span className="section-caption">Things that can narrow the claim or require caution</span>
          </div>
          <div className="pill-list">
            {limits.length > 0 ? limits.map((item, i) => (
              <div key={`${item}-${i}`} className="info-pill caution">{item}</div>
            )) : <p className="empty-state">No limitations extracted.</p>}
          </div>
        </section>
      </div>

      <div className="brief-grid">
        <section className="brief-card">
          <div className="section-heading">
            <h4>Evidence Checklist</h4>
            <span className="section-caption">Documents and records worth gathering now</span>
          </div>
          <div className="checklist-grid">
            {evidence.length > 0 ? evidence.map((item, i) => (
              <div key={`${item}-${i}`} className="check-card">{item}</div>
            )) : <p className="empty-state">No evidence checklist available.</p>}
          </div>
        </section>

        <section className="brief-card">
          <div className="section-heading">
            <h4>Do and Avoid</h4>
            <span className="section-caption">Practical moves that improve the position</span>
          </div>
          <div className="dual-callout">
            <div className="callout-panel do-panel">
              <span className="callout-label">Do this</span>
              <div className="stack-list">
                {doList.length > 0 ? doList.map((item, i) => (
                  <div key={`${item}-${i}`} className="stack-item">{item}</div>
                )) : <div className="stack-item muted">No action items listed.</div>}
              </div>
            </div>
            <div className="callout-panel avoid-panel">
              <span className="callout-label">Avoid this</span>
              <div className="stack-list">
                {avoidList.length > 0 ? avoidList.map((item, i) => (
                  <div key={`${item}-${i}`} className="stack-item">{item}</div>
                )) : <div className="stack-item muted">No avoid items listed.</div>}
              </div>
            </div>
          </div>
        </section>
      </div>

      {forum.rows?.length > 0 && (
        <section className="brief-card">
          <div className="section-heading">
            <h4>Forum Comparison</h4>
            <span className="section-caption">Compare where the matter can be taken</span>
          </div>
          <div className="forum-table-wrap">
            <table className="forum-table">
              <thead>
                <tr>
                  <th>Factor</th>
                  {(forum.forums || []).map(f => <th key={f}>{f}</th>)}
                </tr>
              </thead>
              <tbody>
                {forum.rows.map((row, i) => (
                  <tr key={`${row.factor}-${i}`}>
                    <td>{row.factor}</td>
                    {(row.values || []).map((v, idx) => <td key={`${row.factor}-${idx}`}>{v}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {(relief.length > 0 || costBenefit.invest?.length > 0 || costBenefit.recover?.length > 0) && (
        <div className="brief-grid">
          {relief.length > 0 && (
            <section className="brief-card">
              <div className="section-heading">
                <h4>Relief Spectrum</h4>
                <span className="section-caption">Typical outcomes to aim for</span>
              </div>
              <div className="relief-list">
                {relief.map((r, i) => (
                  <div key={`${r.label}-${i}`} className="relief-item">
                    <div className="relief-copy">
                      <div className="relief-label">{r.label}</div>
                      <div className="relief-range">{r.range}</div>
                    </div>
                    <div className={`relief-bar ${r.level || ''}`}>
                      <div style={{ width: `${Math.min(100, r.likelihood || 0)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {(costBenefit.invest?.length > 0 || costBenefit.recover?.length > 0) && (
            <section className="brief-card">
              <div className="section-heading">
                <h4>Cost and Recovery</h4>
                <span className="section-caption">Likely inputs versus possible returns</span>
              </div>
              <div className="cost-benefit">
                <div className="cost-panel">
                  <h5>What you invest</h5>
                  {(costBenefit.invest || []).map((item, i) => (
                    <div key={`${item.item}-${i}`} className="cost-row">
                      <span>{item.item}</span>
                      <strong>{item.amount}</strong>
                    </div>
                  ))}
                </div>
                <div className="benefit-panel">
                  <h5>What you can recover</h5>
                  {(costBenefit.recover || []).map((item, i) => (
                    <div key={`${item.item}-${i}`} className="cost-row">
                      <span>{item.item}</span>
                      <strong>{item.amount}</strong>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}
        </div>
      )}

      {clauseRisks.length > 0 && (
        <section className="brief-card">
          <div className="section-heading">
            <h4>Clause Risk Scanner</h4>
            <span className="section-caption">Terms that may need revision or caution</span>
          </div>
          <div className="risk-list">
            {clauseRisks.map((c, i) => (
              <div key={`${c.clause}-${i}`} className={`risk-item ${c.risk_level || 'medium'}`}>
                <div className="risk-head">
                  <strong>{c.clause}</strong>
                  <span className="risk-level">{c.risk_level}</span>
                </div>
                <p>{c.issue}</p>
                {c.fix && <div className="risk-fix">Fix: {c.fix}</div>}
              </div>
            ))}
          </div>
        </section>
      )}

      {(misconceptions.length > 0 || similar.length > 0) && (
        <div className="brief-grid">
          {misconceptions.length > 0 && (
            <section className="brief-card">
              <div className="section-heading">
                <h4>Common Misconceptions</h4>
                <span className="section-caption">Quick legal corrections worth knowing</span>
              </div>
              <div className="misconceptions">
                {misconceptions.map((m, i) => (
                  <div key={`${m.claim}-${i}`} className="misconception-item">
                    <div className="misconception-claim">{m.claim}</div>
                    <div className="misconception-truth">{m.truth}</div>
                    {m.explanation && <div className="misconception-note">{m.explanation}</div>}
                  </div>
                ))}
              </div>
            </section>
          )}

          {similar.length > 0 && (
            <section className="brief-card">
              <div className="section-heading">
                <h4>Similar Precedents</h4>
                <span className="section-caption">Comparable court outcomes</span>
              </div>
              <div className="precedent-row">
                {similar.map((c, i) => (
                  <div key={`${c.case_name}-${i}`} className="precedent-card">
                    <div className="precedent-title">{c.case_name}</div>
                    <div className="precedent-meta">{c.court} / {c.year}</div>
                    <div className="precedent-outcome">{c.outcome}</div>
                    {c.similarity && (
                      <div className="precedent-bar">
                        <div style={{ width: `${c.similarity.replace('%', '')}%` }} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {followups.length > 0 && (
        <section className="brief-card">
          <div className="section-heading">
            <h4>Useful Follow Ups</h4>
            <span className="section-caption">Questions worth asking next</span>
          </div>
          <div className="followup-list">
            {followups.map((f, i) => (
              <button
                key={`${f}-${i}`}
                type="button"
                className="followup-chip followup-btn"
                onClick={() => onFollowup?.(f)}
              >
                {f}
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function StepCard({ step, index }) {
  return (
    <div className="step-card" style={{ animationDelay: `${index * 60}ms` }}>
      <div className="step-number">{index + 1}</div>
      <div className="step-copy">
        <div className="step-title">{step}</div>
        <div className="step-subtitle">Immediate action item</div>
      </div>
    </div>
  );
}

function RightItem({ right, index }) {
  return (
    <div className="right-item" style={{ animationDelay: `${index * 60}ms` }}>
      <span className="right-text">{right}</span>
    </div>
  );
}

function ResultPanel({ result, onFollowup }) {
  const [activeTab, setActiveTab] = useState('brief');

  const tabs = [
    { id: 'brief', label: 'Brief', count: null, note: 'Executive summary and strategy' },
    { id: 'analysis', label: 'Analysis', count: result.key_points?.length || null, note: 'Narrative legal reasoning' },
    { id: 'articles', label: 'Articles', count: result.articles_cited?.length || result.retrieved_sections?.length, note: 'Core citations and references' },
    { id: 'rights', label: 'Rights', count: result.your_rights?.length, note: 'Rights triggered by the facts' },
    { id: 'steps', label: 'Next Steps', count: result.next_steps?.length, note: 'Practical actions to take' },
    { id: 'sources', label: 'Source Sections', count: result.retrieved_sections?.length, note: 'Retrieved constitutional text' },
    { id: 'explain', label: 'Explainability', count: null, note: 'Domain detection and insights' },
  ];

  const activeTabMeta = tabs.find(tab => tab.id === activeTab) || tabs[0];

  const copyText = useCallback(async () => {
    const text = [
      `LEGAL ANALYSIS - ${result.case_type}`,
      `Query: ${result.query}`,
      '',
      'SUMMARY:',
      result.summary,
      '',
      'ANALYSIS:',
      result.analysis,
      '',
      'YOUR RIGHTS:',
      ...(result.your_rights || []).map((r, i) => `${i + 1}. ${r}`),
      '',
      'NEXT STEPS:',
      ...(result.next_steps || []).map((s, i) => `${i + 1}. ${s}`),
      '',
      result.disclaimer,
    ].join('\n');
    await navigator.clipboard.writeText(text);
  }, [result]);

  return (
    <div className="result-panel">
      <div className="result-header">
        <div className="result-header-top">
          <div className="result-title-section">
            <p className="result-eyebrow">{result.case_type}</p>
            <h2 className="result-title">Legal Analysis</h2>
            <p className="result-summary">{result.summary}</p>
          </div>
          <div className="result-badges">
            <span className={`badge ${result.ai_powered ? 'ai' : ''}`}>{result.ai_powered ? 'AI Powered' : 'Document Mode'}</span>
            <button className="icon-btn" onClick={copyText} title="Copy full analysis">
              Copy Brief
            </button>
          </div>
        </div>

        <UrgencyBadge urgency={result.urgency} />

        {result.legal_topics?.length > 0 && (
          <div className="topics-row">
            {result.legal_topics.map(t => (
              <span key={t} className="topic-chip">{t}</span>
            ))}
          </div>
        )}
      </div>

      <div className="result-shell">
        <aside className="result-sidebar">
          <div className="sidebar-card">
            <span className="sidebar-label">Consultation flow</span>
            <h3>{activeTabMeta.label}</h3>
            <p>{activeTabMeta.note}</p>
          </div>

          <nav className="sidebar-nav" aria-label="Result sections">
            {tabs.map(tab => (
              <button
                key={tab.id}
                type="button"
                className={`sidebar-tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <span className="sidebar-tab-copy">
                  <span className="sidebar-tab-label">{tab.label}</span>
                  <span className="sidebar-tab-note">{tab.note}</span>
                </span>
                {tab.count > 0 && <span className="tab-count">{tab.count}</span>}
              </button>
            ))}
          </nav>

          <div className="sidebar-card sidebar-card-muted">
            <span className="sidebar-label">Working query</span>
            <p>{result.query}</p>
          </div>
        </aside>

        <div className="result-main">
          <div className="tab-content">
            {activeTab === 'brief' && (
              <div className="tab-pane">
                <StructuredPanel
                  structured={result.structured}
                  urgency={result.urgency}
                  result={result}
                  onFollowup={onFollowup}
                />
              </div>
            )}

            {activeTab === 'analysis' && (
              <div className="tab-pane">
                {result.key_points?.length > 0 && (
                  <div className="key-points-box">
                    <div className="section-heading">
                      <h4>Key Legal Points</h4>
                      <span className="section-caption">Fast scan of the most important takeaways</span>
                    </div>
                    <div className="key-points-grid">
                      {result.key_points.map((pt, i) => <div key={`${pt}-${i}`} className="key-point-card">{pt}</div>)}
                    </div>
                  </div>
                )}
                <div className="analysis-body">
                  <RenderText text={result.analysis} />
                </div>
              </div>
            )}

            {activeTab === 'articles' && (
              <div className="tab-pane">
                {result.articles_cited?.length > 0 ? (
                  <>
                    <p className="tab-intro">Constitutional articles directly relevant to your case.</p>
                    <div className="articles-list">
                      {result.articles_cited.map((a, i) => (
                        <ArticleCard key={`${a.number || a.title}-${i}`} article={a} index={i} />
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="empty-state">No specific articles were extracted by the AI. Use Source Sections to inspect the retrieved constitutional text.</p>
                )}
              </div>
            )}

            {activeTab === 'rights' && (
              <div className="tab-pane">
                <p className="tab-intro">Based on your situation, these rights appear most relevant under Indian law.</p>
                <div className="rights-list">
                  {(result.your_rights || []).map((r, i) => (
                    <RightItem key={`${r}-${i}`} right={r} index={i} />
                  ))}
                </div>
                <div className="legal-aid-box">
                  <h4>Free legal support</h4>
                  <p>Contact the <strong>District Legal Services Authority (DLSA)</strong> for free legal aid.</p>
                  <p><strong>Tele-Law Helpline:</strong> 15100</p>
                  <p><strong>National Legal Services Authority:</strong> nalsa.gov.in</p>
                </div>
              </div>
            )}

            {activeTab === 'steps' && (
              <div className="tab-pane">
                <p className="tab-intro">Action items for your situation.</p>
                <div className="steps-list">
                  {(result.next_steps || []).map((s, i) => (
                    <StepCard key={`${s}-${i}`} step={s} index={i} />
                  ))}
                </div>
                <div className="disclaimer-box">
                  <span className="disclaimer-label">Important</span>
                  <p>{result.disclaimer}</p>
                </div>
              </div>
            )}

            {activeTab === 'sources' && (
              <div className="tab-pane">
                <p className="tab-intro">These sections were retrieved from the Constitution of India using the hybrid RAG engine.</p>
                <div className="sections-list">
                  {(result.retrieved_sections || []).map((s, i) => (
                    <SectionCard key={`${s.title}-${i}`} section={s} index={i} />
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'explain' && result.explainability && (
              <div className="tab-pane">
                <p className="tab-intro">Insights into how the AI selected the legal corpus and retrieved sections.</p>
                
                <div className="brief-card">
                  <div className="section-heading">
                    <h4>Situation-to-Law Mapper</h4>
                    <span className="section-caption">Automatic domain selection</span>
                  </div>
                  <div className="snapshot-table-wrap">
                    <table className="snapshot-table">
                      <tbody>
                        <tr>
                          <th>Detected Domain</th>
                          <td><strong>{result.explainability.detected_domain || 'Unknown'}</strong></td>
                        </tr>
                        <tr>
                          <th>Confidence</th>
                          <td>{result.explainability.confidence || 'N/A'}%</td>
                        </tr>
                        <tr>
                          <th>Matched Keywords</th>
                          <td>{(result.explainability.matched_keywords || []).join(', ') || 'None'}</td>
                        </tr>
                        <tr>
                          <th>Explanation</th>
                          <td>{result.explainability.short_explanation}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="brief-card" style={{ marginTop: '20px' }}>
                  <div className="section-heading">
                    <h4>Corpus Retrieval</h4>
                    <span className="section-caption">Documents sourced for this query</span>
                  </div>
                  <div className="pill-list">
                    {result.explainability.source_documents?.map((doc, i) => (
                      <div key={i} className="info-pill">{doc}</div>
                    ))}
                  </div>
                  <p style={{ marginTop: '10px', color: 'var(--lq-text-soft)', fontSize: '0.9rem' }}>
                    Number of chunks used: {result.explainability.number_of_chunks_used}
                  </p>
                </div>
              </div>
            )}

            {activeTab === 'explain' && !result.explainability && (
              <div className="tab-pane">
                <p className="empty-state">No explainability insights available for this query.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function UserBubble({ text }) {
  return (
    <div className="chat-entry user">
      <div className="avatar user" style={{ fontSize: '1.2rem' }}>U</div>
      <div className="bubble">{text}</div>
    </div>
  );
}

function LegalQuery() {
  const [query, setQuery] = useState('');
  const [conversation, setConversation] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [fadeIn, setFadeIn] = useState(false);
  const [backendStatus, setBackendStatus] = useState(null);

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);
  const autoSubmittedRef = useRef(false);
  const location = useLocation();

  const initialQuery = location.state?.query || '';

  useEffect(() => {
    setTimeout(() => setFadeIn(true), 100);
    fetch('http://127.0.0.1:5555/health')
      .then(r => r.json())
      .then(d => setBackendStatus(d))
      .catch(() => setBackendStatus(null));
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation, loading]);

  const submitQuery = useCallback(async (queryText) => {
    if (!queryText.trim()) {
      setError('Please enter a legal scenario or question.');
      return;
    }
    const currentQuery = queryText.trim();
    setError('');
    setQuery('');

    const historyForAPI = conversation.map(m => ({ role: m.role, text: m.text }));
    const updatedConversation = [...conversation, { role: 'user', text: currentQuery }];
    setConversation(updatedConversation);
    setLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:5555/legal-help', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: currentQuery, chat_history: historyForAPI }),
      });

      const data = await response.json();
      if (response.ok) {
        setConversation([
          ...updatedConversation,
          { role: 'assistant', text: data.summary || data.analysis || '', result: data },
        ]);
      } else {
        setError(data.error || 'Something went wrong. Please try again.');
        setConversation(conversation);
      }
    } catch (err) {
      console.error('Fetch error:', err);
      setError('Cannot connect to the backend server. Make sure the Flask server is running on port 5555.');
      setConversation(conversation);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [conversation]);

  useEffect(() => {
    if (!autoSubmittedRef.current && initialQuery && conversation.length === 0) {
      autoSubmittedRef.current = true;
      submitQuery(initialQuery);
    }
  }, [initialQuery, conversation.length, submitQuery]);

  const handleSubmit = (e) => {
    e.preventDefault();
    submitQuery(query);
  };

  const handleChipClick = (text) => {
    submitQuery(text);
  };

  const handleNewChat = () => {
    setConversation([]);
    setQuery('');
    setError('');
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const hasConversation = conversation.length > 0;
  const lastAssistantResult = [...conversation].reverse().find(msg => msg.role === 'assistant' && msg.result)?.result || null;
  const hasOutput = Boolean(lastAssistantResult) || loading;

  return (
    <div className={`lq-root ${fadeIn ? 'fade-in' : ''}`}>
      {!hasConversation && !loading && (
        <section className="lq-welcome">
          <div className="welcome-hero-panel">
            <div className="welcome-copy">
              <span className="welcome-kicker">Premium legal workspace</span>
              <h1>Ask About Your Rights</h1>
              <p>Structured constitutional guidance with sharper design, clearer hierarchy, and action-first legal briefings.</p>
            </div>
            <div className="welcome-stat-grid">
              <div className="welcome-stat-card">
                <span className="welcome-stat-number">2130+</span>
                <span className="welcome-stat-label">Constitution chunks indexed</span>
              </div>
              <div className="welcome-stat-card">
                <span className="welcome-stat-number">RAG</span>
                <span className="welcome-stat-label">Grounded retrieval pipeline</span>
              </div>
              <div className="welcome-stat-card">
                <span className="welcome-stat-number">AI</span>
                <span className="welcome-stat-label">Structured brief generation</span>
              </div>
            </div>
          </div>

          <div className="quick-scenarios-grid">
            {QUICK_SCENARIOS.map((s, i) => (
              <button
                key={i}
                className="scenario-card"
                onClick={() => handleChipClick(s.text)}
                disabled={loading}
              >
                <span className="scenario-card-label">{s.label}</span>
                <span className="scenario-card-text">{s.text}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {backendStatus && hasConversation && (
        <div className="status-card">
          <div className="status-indicator">
            <div className="status-dot" />
            <div className="status-text">
              {backendStatus.ai_available ? 'RAG + AI' : 'RAG only'} / Provider: {backendStatus.llm_provider || 'unknown'} / {backendStatus.index_chunks} chunks
            </div>
          </div>
        </div>
      )}

      <div className="lq-chat-area">
        {conversation.map((msg, index) => (
          <div key={index}>
            {msg.role === 'user' ? (
              <UserBubble text={msg.text} />
            ) : (
              msg.result ? (
                <ResultPanel result={msg.result} onFollowup={handleChipClick} />
              ) : (
                <div className="chat-entry ai">
                  <div className="avatar ai" style={{ fontSize: '1.2rem' }}>AI</div>
                  <div className="bubble">
                    <RenderText text={msg.text} />
                  </div>
                </div>
              )
            )}
          </div>
        ))}
        {loading && <TypingIndicator />}
        <div ref={chatEndRef} />
      </div>

      <div className={`query-compose ${hasOutput ? 'is-collapsed' : 'is-expanded'}`}>
        {error && (
          <div className="inline-error">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="query-form">
          <div className="lq-input-bar">
            <textarea
              ref={inputRef}
              id="legal-query-input"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder="Describe your legal situation... for example: Police arrested me without showing a warrant."
              disabled={loading}
              rows={2}
              aria-label="Enter your legal scenario"
            />
            <button
              type="submit"
              className="submit-btn"
              disabled={loading || !query.trim()}
              id="submit-legal-query"
            >
              {loading ? 'Analyzing...' : 'Ask'}
            </button>
          </div>
        </form>
        {hasConversation && (
          <button
            className="submit-btn secondary-btn"
            onClick={handleNewChat}
          >
            New
          </button>
        )}
      </div>
    </div>
  );
}

export default LegalQuery;
