import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import './LegalQuery.css';

// ─── Markdown-lite renderer ──────────────────────────────────────────────────
function RenderText({ text }) {
  if (!text) return null;
  const lines = text.split('\n');
  return (
    <div className="rendered-text">
      {lines.map((line, i) => {
        if (!line.trim()) return <br key={i} />;
        if (line.startsWith('# '))  return <h2 key={i}>{line.slice(2)}</h2>;
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

// ─── Urgency Badge ───────────────────────────────────────────────────────────
function UrgencyBadge({ urgency }) {
  if (!urgency) return null;
  const icons = { CRITICAL: '🚨', HIGH: '⚠️', MEDIUM: 'ℹ️', STANDARD: '✅' };
  return (
    <div className="urgency-badge" style={{ borderColor: urgency.color, color: urgency.color }}>
      <span className="urgency-icon">{icons[urgency.level] || 'ℹ️'}</span>
      <div>
        <span className="urgency-level">{urgency.level}</span>
        <span className="urgency-msg">{urgency.message}</span>
      </div>
    </div>
  );
}

// ─── Typing dots ─────────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="typing-indicator" aria-label="AI is thinking">
      <div className="typing-avatar">⚖️</div>
      <div className="typing-bubble">
        <span className="dot" /><span className="dot" /><span className="dot" />
      </div>
      <span className="typing-label">Legal AI is analyzing your scenario…</span>
    </div>
  );
}

// ─── Quick scenario chips ────────────────────────────────────────────────────
const QUICK_SCENARIOS = [
  { label: '🚗 Road Accident', text: 'I was injured in a road accident caused by another driver. What are my legal rights and how do I claim compensation?' },
  { label: '👮 Unlawful Arrest', text: 'Police arrested me without showing a warrant and are refusing to let me call my lawyer. What are my rights?' },
  { label: '🏠 Illegal Eviction', text: 'My landlord is forcefully evicting me without giving proper notice. What legal protection do I have?' },
  { label: '👷 Salary Not Paid', text: 'My employer has not paid my salary for 3 months and is threatening to fire me. What can I do legally?' },
  { label: '🛒 Consumer Fraud', text: 'I bought a product online that was defective and the seller is refusing to refund me. What are my rights?' },
  { label: '📚 School Denied Admission', text: 'A private school refused to admit my child citing caste. Is this legal? What action can I take?' },
];

// ─── Article Citation Card ───────────────────────────────────────────────────
function ArticleCard({ article, index }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="article-card" style={{ animationDelay: `${index * 80}ms` }}>
      <div className="article-card-header" onClick={() => setExpanded(e => !e)}>
        <div className="article-number-badge">{article.number || 'Article'}</div>
        <div className="article-card-meta">
          <div className="article-card-title">{article.title}</div>
          {article.relevance && !expanded && (
            <div className="article-card-preview">{article.relevance.slice(0, 80)}…</div>
          )}
        </div>
        <button className="expand-btn" aria-label="Toggle details">
          {expanded ? '▲' : '▼'}
        </button>
      </div>
      {expanded && (
        <div className="article-card-body">
          <p>{article.relevance}</p>
        </div>
      )}
    </div>
  );
}

// ─── Retrieved Section Card ───────────────────────────────────────────────────
function SectionCard({ section, index }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="section-card" style={{ animationDelay: `${index * 80}ms` }}>
      <div className="section-card-header" onClick={() => setExpanded(e => !e)}>
        <div>
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
        </div>
        <button className="expand-btn">{expanded ? '▲' : '▼'}</button>
      </div>
      {expanded && (
        <div className="section-card-body">
          <pre className="constitution-text">{section.excerpt}</pre>
        </div>
      )}
    </div>
  );
}

// ─── Step Card ───────────────────────────────────────────────────────────────
function StepCard({ step, index }) {
  return (
    <div className="step-card" style={{ animationDelay: `${index * 60}ms` }}>
      <div className="step-number">{index + 1}</div>
      <div className="step-text">{step}</div>
    </div>
  );
}

// ─── Right Item ──────────────────────────────────────────────────────────────
function RightItem({ right, index }) {
  return (
    <div className="right-item" style={{ animationDelay: `${index * 60}ms` }}>
      <span className="right-icon">⚖️</span>
      <span className="right-text">{right}</span>
    </div>
  );
}

// ─── Result Panel (tabbed) ────────────────────────────────────────────────────
function ResultPanel({ result }) {
  const [activeTab, setActiveTab] = useState('analysis');

  const tabs = [
    { id: 'analysis',  label: '📋 Analysis',        count: null },
    { id: 'articles',  label: '📜 Articles',         count: result.articles_cited?.length || result.retrieved_sections?.length },
    { id: 'rights',    label: '🛡️ Your Rights',      count: result.your_rights?.length },
    { id: 'steps',     label: '🚀 Next Steps',        count: result.next_steps?.length },
    { id: 'sources',   label: '📂 Source Sections',  count: result.retrieved_sections?.length },
  ];

  const copyText = useCallback(async () => {
    const text = [
      `LEGAL ANALYSIS — ${result.case_type}`,
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
      {/* Header */}
      <div className="result-header">
        <div className="result-title-row">
          <div>
            <div className="case-type-tag">{result.case_type}</div>
            <h2 className="result-title">Legal Analysis</h2>
          </div>
          <div className="result-header-actions">
            {!result.ai_powered && (
              <span className="fallback-badge">📚 Document Mode</span>
            )}
            {result.ai_powered && (
              <span className="ai-badge">✨ AI Powered</span>
            )}
            <button className="icon-btn" onClick={copyText} title="Copy full analysis">
              📋 Copy
            </button>
          </div>
        </div>

        <UrgencyBadge urgency={result.urgency} />

        {result.summary && (
          <div className="result-summary">
            <strong>Summary: </strong>{result.summary}
          </div>
        )}

        {result.legal_topics?.length > 0 && (
          <div className="topics-row">
            {result.legal_topics.map(t => (
              <span key={t} className="topic-chip">{t}</span>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="tab-bar" role="tablist">
        {tabs.map(tab => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
            {tab.count > 0 && <span className="tab-count">{tab.count}</span>}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="tab-content">

        {activeTab === 'analysis' && (
          <div className="tab-pane">
            {result.key_points?.length > 0 && (
              <div className="key-points-box">
                <h4>🔑 Key Legal Points</h4>
                <ul>
                  {result.key_points.map((pt, i) => <li key={i}>{pt}</li>)}
                </ul>
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
                <p className="tab-intro">Constitutional articles directly relevant to your case:</p>
                <div className="articles-list">
                  {result.articles_cited.map((a, i) => (
                    <ArticleCard key={i} article={a} index={i} />
                  ))}
                </div>
              </>
            ) : (
              <p className="empty-state">No specific articles were extracted by the AI. See Source Sections tab for retrieved constitutional text.</p>
            )}
          </div>
        )}

        {activeTab === 'rights' && (
          <div className="tab-pane">
            <p className="tab-intro">Based on your situation, you have the following rights under Indian law:</p>
            <div className="rights-list">
              {(result.your_rights || []).map((r, i) => (
                <RightItem key={i} right={r} index={i} />
              ))}
            </div>
            <div className="legal-aid-box">
              <h4>🆘 Need Free Legal Help?</h4>
              <p>Contact the <strong>District Legal Services Authority (DLSA)</strong> for free legal aid.</p>
              <p>📞 <strong>Tele-Law Helpline: 15100</strong> (Free, available in regional languages)</p>
              <p>🌐 <strong>nalsa.gov.in</strong> — National Legal Services Authority</p>
            </div>
          </div>
        )}

        {activeTab === 'steps' && (
          <div className="tab-pane">
            <p className="tab-intro">Recommended immediate actions for your situation:</p>
            <div className="steps-list">
              {(result.next_steps || []).map((s, i) => (
                <StepCard key={i} step={s} index={i} />
              ))}
            </div>
            <div className="disclaimer-box">
              <span>⚠️</span>
              <p>{result.disclaimer}</p>
            </div>
          </div>
        )}

        {activeTab === 'sources' && (
          <div className="tab-pane">
            <p className="tab-intro">These sections were retrieved from the Constitution of India using the hybrid RAG engine (BM25 + TF-IDF):</p>
            <div className="sections-list">
              {(result.retrieved_sections || []).map((s, i) => (
                <SectionCard key={i} section={s} index={i} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Message bubble ───────────────────────────────────────────────────────────
function UserBubble({ text }) {
  return (
    <div className="user-bubble">
      <div className="user-avatar">👤</div>
      <div className="user-bubble-text">{text}</div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
function LegalQuery() {
  const [query, setQuery] = useState('');
  const [conversation, setConversation] = useState([]); // [{role, text, result?}]
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [fadeIn, setFadeIn] = useState(false);
  const [backendStatus, setBackendStatus] = useState(null);

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);
  const location = useLocation();

  const initialQuery = location.state?.query || '';
  const initialAdvice = location.state?.advice || '';

  useEffect(() => {
    setTimeout(() => setFadeIn(true), 100);
    if (initialQuery && initialAdvice && conversation.length === 0) {
      setConversation([
        { role: 'user', text: initialQuery },
        { role: 'assistant', text: initialAdvice, result: null },
      ]);
    }
    // Health check
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

  return (
    <div className={`lq-root ${fadeIn ? 'fade-in' : ''}`}>
      {/* Sidebar */}
      <aside className="lq-sidebar">
        <div className="sidebar-header">
          <h2>⚖️ LegalAI</h2>
          <p>Your AI-powered Constitutional guide</p>
        </div>

        {backendStatus && (
          <div className="backend-status">
            <span className={`status-dot ${backendStatus.gemini_available ? 'green' : 'yellow'}`} />
            <span>{backendStatus.gemini_available ? 'AI + RAG Active' : 'RAG Mode (No AI)'}</span>
            <span className="status-chunks">{backendStatus.index_chunks} chunks indexed</span>
          </div>
        )}

        <div className="sidebar-section">
          <h3>Quick Scenarios</h3>
          <div className="quick-scenarios">
            {QUICK_SCENARIOS.map((s, i) => (
              <button
                key={i}
                className="scenario-chip"
                onClick={() => handleChipClick(s.text)}
                disabled={loading}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {hasConversation && (
          <button className="new-chat-btn" onClick={handleNewChat}>
            ✚ New Consultation
          </button>
        )}

        <div className="sidebar-footer">
          <p>🔒 Your queries are private</p>
          <p>📖 Based on Constitution of India</p>
          <p>📞 Tele-Law: <strong>15100</strong></p>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="lq-main">
        {/* Chat History */}
        <div className="lq-chat-area">
          {!hasConversation && !loading && (
            <div className="lq-welcome">
              <div className="welcome-icon">⚖️</div>
              <h1>Legal AI Consultation</h1>
              <p>Describe your legal situation in plain language. I'll analyze it against the Constitution of India and guide you on your rights and next steps.</p>
              <div className="welcome-features">
                <div className="welcome-feat">📜 Constitutional Analysis</div>
                <div className="welcome-feat">🛡️ Know Your Rights</div>
                <div className="welcome-feat">🚀 Actionable Steps</div>
                <div className="welcome-feat">📂 Source Citations</div>
              </div>
            </div>
          )}

          {conversation.map((msg, index) => (
            <div key={index} className="chat-entry">
              {msg.role === 'user' ? (
                <UserBubble text={msg.text} />
              ) : (
                msg.result
                  ? <ResultPanel result={msg.result} />
                  : (
                    <div className="result-panel">
                      <div className="tab-content">
                        <div className="tab-pane">
                          <RenderText text={msg.text} />
                        </div>
                      </div>
                    </div>
                  )
              )}
            </div>
          ))}

          {loading && <TypingIndicator />}
          <div ref={chatEndRef} />
        </div>

        {/* Input Bar */}
        <div className="lq-input-bar">
          {error && (
            <div className="lq-error" role="alert">
              <span>⚠️</span> {error}
            </div>
          )}
          <form onSubmit={handleSubmit} className="lq-form">
            <textarea
              ref={inputRef}
              id="legal-query-input"
              className="lq-textarea"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder="Describe your legal situation… (e.g. 'Police arrested me without a warrant at 2am')"
              disabled={loading}
              rows={2}
              aria-label="Enter your legal scenario"
            />
            <button
              type="submit"
              className="lq-submit-btn"
              disabled={loading || !query.trim()}
              id="submit-legal-query"
            >
              {loading ? (
                <span className="btn-spinner" />
              ) : (
                <>
                  <span>Ask</span>
                  <span className="send-arrow">➤</span>
                </>
              )}
            </button>
          </form>
          <p className="input-hint">Press <kbd>Enter</kbd> to submit · <kbd>Shift+Enter</kbd> for new line</p>
        </div>
      </main>
    </div>
  );
}

export default LegalQuery;