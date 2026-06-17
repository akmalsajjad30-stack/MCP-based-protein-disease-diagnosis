// ResultsDashboard.jsx — ACT 3: Clinical diagnostic artifacts revealed progressively
import { useState, useEffect } from 'react'
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip as ReTooltip,
} from 'recharts'
import {
  Download, RefreshCw, Activity, AlertTriangle, Pill,
  FlaskConical, BookOpen, Lightbulb, Network, Star,
} from 'lucide-react'
import KnowledgeGraph from './KnowledgeGraph'

// ── Field-name bridge: backend uses snake_case schema names, UI uses short aliases ──
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function normalizeResult(raw) {
  if (!raw) return { diagnoses: [], procedures: [], drug_considerations: [], lifestyle: [], evidence_snippets: [], reasoning_summary: '', communities: [], graph_data: { nodes: [], edges: [] }, clinical_trials: [], disclaimer: '' }
  // If already in frontend format (has 'diagnoses'), return as-is
  if (raw.diagnoses) return raw
  // Map backend field names → frontend field names
  return {
    diagnoses: (raw.differential_diagnosis || []).map(d => ({
      rank: d.rank,
      condition: d.condition,
      icd10: d.icd10,
      confidence: typeof d.confidence === 'number'
        ? (d.confidence <= 1 ? Math.round(d.confidence * 100) : d.confidence)
        : 0,
      urgency: (d.confidence >= 0.7 || d.confidence >= 70) ? 'urgent'
        : (d.confidence >= 0.4 || d.confidence >= 40) ? 'moderate' : 'routine',
      rationale: d.reasoning || '',
      evidence_sources: d.evidence_sources || [],
      key_biomarkers: d.key_biomarkers || [],
    })),
    procedures: (raw.diagnostic_tests || []).map(t => ({
      name: t.test,
      priority: t.priority || 'routine',
      note: t.rationale || '',
    })),
    drug_considerations: (raw.drug_review || []).map(d => ({
      name: d.drug,
      class: '',
      indication: '',
      risk: d.risk_level || 'low',
      note: `${d.recommendation || ''}${d.adverse_signals?.length ? ' | Signals: ' + d.adverse_signals.slice(0,3).join(', ') : ''}`,
    })),
    lifestyle: (raw.lifestyle_recommendations || []).map(r => ({
      icon: r.category === 'nutrition' ? '🥗'
        : r.category === 'activity' ? '🏃'
        : r.category === 'sleep' ? '😴'
        : r.category === 'stress' ? '🧘'
        : r.category === 'supplements' ? '💊' : '💡',
      text: `${r.recommendation}${r.evidence ? ' (' + r.evidence + ')' : ''}`,
    })),
    evidence_snippets: (raw.knowledge_graph_highlights || []).map(h => ({
      source: 'Knowledge Graph',
      text: `${h.from_entity} ${h.relationship} ${h.to_entity} (${h.strength})`,
    })),
    reasoning_summary: raw.summary || '',
    communities: [],
    graph_data: { nodes: [], edges: [] },
    clinical_trials: raw.clinical_trials || [],
    disclaimer: raw.disclaimer || '',
  }
}

// ─────────────────────────────────────────────────────────────

function ConfidenceArc({ value }) {
  const r = 28, cx = 36, cy = 36
  const circumference = Math.PI * r
  const offset = circumference * (1 - value / 100)
  const color = value > 70 ? 'var(--accent)' : value > 45 ? 'var(--yellow)' : 'var(--text-muted)'
  return (
    <svg width={72} height={44} style={{ display: 'block' }}>
      <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
        fill="none" stroke="var(--border)" strokeWidth={5} />
      <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
        fill="none" stroke={color} strokeWidth={5}
        strokeDasharray={circumference} strokeDashoffset={offset}
        strokeLinecap="round" style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.34,1.56,0.64,1)' }} />
      <text x={cx} y={cy - 4} textAnchor="middle" fontSize={12} fontWeight={700} fill={color}>
        {value}%
      </text>
    </svg>
  )
}

export default function ResultsDashboard({ result, communities, graphData, sessionId, onReset }) {
  const [revealed, setRevealed] = useState(0)
  const data = normalizeResult(result)
  
  if (communities && communities.length) {
    data.communities = communities
  }
  if (graphData && graphData.nodes && graphData.nodes.length) {
    data.graph_data = graphData
  }

  // Progressive reveal — stagger panels
  useEffect(() => {
    const timer = setInterval(() => {
      setRevealed(r => {
        if (r >= 8) { clearInterval(timer); return r }
        return r + 1
      })
    }, 250)
    return () => clearInterval(timer)
  }, [])

  const radarData = data.diagnoses.map(d => ({
    condition: d.condition.split(' ').slice(0, 2).join(' '),
    confidence: d.confidence,
    fullMark: 100,
  }))

  const urgencyBadge = (u) => {
    const map = { urgent: 'badge-urgent', moderate: 'badge-moderate', routine: 'badge-low' }
    return map[u] || 'badge-routine'
  }

  const downloadReport = () => {
    if (sessionId) {
      window.open(`${API_BASE}/report/${sessionId}`, '_blank')
    } else {
      alert('No backend session — run the backend server to enable PDF download.')
    }
  }

  return (
    <div className="page gradient-bg" style={{ marginTop: 64 }}>
      {/* Header */}
      <div className="results-header fade-up">
        <div className="results-title-block">
          <h1>🔬 Diagnostic Artifacts</h1>
          <p>Oracle analysis complete · Graph RAG + Clinical AI Reasoner · {new Date().toLocaleString()}</p>
        </div>
        <div className="results-actions">
          <button className="btn-ghost" onClick={onReset} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <RefreshCw size={14} /> New Intake
          </button>
          <button className="btn-primary" onClick={downloadReport} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Download size={14} /> PDF Report
          </button>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="disclaimer-banner fade-up" style={{ marginBottom: 28 }}>
        <AlertTriangle size={14} />
        <strong>Clinical Advisory:</strong>&nbsp;These findings are AI-generated suggestions for informational purposes only.
        All diagnoses must be confirmed by a licensed physician. Do not initiate treatment based solely on this report.
      </div>

      {/* JSON Parse Fallback View */}
      {result?.parse_error && (
        <div className="card fade-up" style={{ borderColor: '#ef4444', marginBottom: 28, background: 'rgba(239, 68, 68, 0.05)', animationDelay: '0.05s' }}>
          <div className="card-title" style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertTriangle size={16} /> Failed to parse Structured JSON Artifacts
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '8px 0' }}>
            The AI Reasoner completed the analysis, but the final response could not be parsed into the structured dashboard format (Error: {result.parse_error}).
            This usually happens if the model output was truncated or formatted incorrectly. You can view the raw unstructured medical analysis below:
          </p>
          <pre style={{
            padding: '12px 16px',
            background: 'rgba(0, 0, 0, 0.2)',
            borderRadius: 'var(--radius)',
            fontSize: '0.78rem',
            color: 'var(--text-primary)',
            overflowX: 'auto',
            whiteSpace: 'pre-wrap',
            maxHeight: 400,
            border: '1px solid var(--border)',
            fontFamily: 'var(--font-mono)',
            lineHeight: 1.5
          }}>
            {result.raw_text}
          </pre>
        </div>
      )}

      {/* PANEL 1 — Radar + Diagnoses */}
      {revealed >= 1 && (
        <div className="results-grid fade-up" style={{ animationDelay: '0s' }}>
          {/* Radar chart */}
          <div className="card">
            <div className="card-title"><Activity size={14} /> Diagnostic Probability Radar</div>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={260}>
                <RadarChart data={radarData} cx="50%" cy="50%" outerRadius={90}>
                  <PolarGrid stroke="var(--border)" />
                  <PolarAngleAxis dataKey="condition" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 9 }} />
                  <Radar name="Confidence" dataKey="confidence"
                    stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.2}
                    strokeWidth={2} />
                  <ReTooltip
                    contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
                    itemStyle={{ color: 'var(--text-primary)' }}
                    formatter={(v) => [`${v}%`, 'Confidence']}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            {/* Communities */}
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Leiden Disease Clusters
              </div>
              {data.communities?.map(c => (
                <span key={c} className="community-pill">🌐 {c}</span>
              ))}
            </div>
          </div>

          {/* Diagnoses */}
          <div className="card">
            <div className="card-title"><Star size={14} /> Differential Diagnoses</div>
            {data.diagnoses.map(d => (
              <div key={d.rank} className="diag-card">
                <div className="diag-card-header">
                  <div className="diag-rank">#{d.rank}</div>
                  <div className="diag-name">{d.condition}</div>
                  <span className={`badge ${urgencyBadge(d.urgency)}`}>{d.urgency}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                  <ConfidenceArc value={d.confidence} />
                  <div style={{ flex: 1 }}>
                    <div className="confidence-bar">
                      <div className="confidence-fill" style={{ width: `${d.confidence}%` }} />
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>
                      ICD-10: {d.icd10}
                    </div>
                  </div>
                </div>
                <div className="diag-rationale">{d.rationale}</div>
                <div className="diag-evidence">
                  📎 {d.evidence_sources?.join(' · ')}
                </div>
                {d.key_biomarkers && (
                  <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {d.key_biomarkers.map(b => (
                      <span key={b} style={{
                        fontSize: '0.7rem', padding: '2px 8px',
                        background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.2)',
                        borderRadius: 4, color: 'var(--blue)',
                      }}>{b}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* PANEL 2 — Knowledge Graph + Evidence */}
      {revealed >= 2 && (
        <div className="results-grid fade-up" style={{ animationDelay: '0.1s', marginTop: 0 }}>
          <div className="card">
            <div className="card-title"><Network size={14} /> Knowledge Graph <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>(drag to explore)</span></div>
            <KnowledgeGraph graphData={data.graph_data} />
          </div>
          <div className="card">
            <div className="card-title"><BookOpen size={14} /> Evidence Board</div>
            <div>
              {data.evidence_snippets?.map((ev, i) => (
                <div key={i} className="evidence-item">
                  <div className="evidence-source">{ev.source}</div>
                  <div className="evidence-text">{ev.text}</div>
                </div>
              ))}
            </div>
            {data.reasoning_summary && (
              <div style={{
                marginTop: 16, padding: '14px', background: 'var(--accent-dim)',
                borderRadius: 'var(--radius)', border: '1px solid rgba(110,231,183,0.2)',
              }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--accent)', fontWeight: 700, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  🧠 Oracle Summary
                </div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  {data.reasoning_summary}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* PANEL 3 — Procedures + Drugs */}
      {revealed >= 3 && (
        <div className="results-grid fade-up" style={{ animationDelay: '0.2s', marginTop: 0 }}>
          {/* Diagnostic Procedures */}
          <div className="card">
            <div className="card-title"><FlaskConical size={14} /> Recommended Investigations</div>
            <div className="proc-item" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 8, marginBottom: 4 }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', gap: 16, width: '100%' }}>
                <span>TEST</span><span>PRIORITY</span><span>RATIONALE</span>
              </div>
            </div>
            {data.procedures?.map((p, i) => (
              <div key={i} className="proc-item">
                <div className="proc-bullet" style={{
                  background: p.priority === 'urgent' ? 'var(--red)'
                    : p.priority === 'routine' ? 'var(--accent)' : 'var(--text-muted)',
                }} />
                <div className="proc-content">
                  <div className="proc-name">
                    {p.name}
                    <span className={`badge ${p.priority === 'urgent' ? 'badge-urgent' : p.priority === 'routine' ? 'badge-low' : 'badge-optional'}`}
                      style={{ marginLeft: 8 }}>{p.priority}</span>
                  </div>
                  <div className="proc-note">{p.note}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Drug Considerations */}
          <div className="card">
            <div className="card-title"><Pill size={14} /> Drug Considerations</div>
            <div className="disclaimer-banner" style={{ marginBottom: 16 }}>
              <AlertTriangle size={12} /> Requires physician prescription and monitoring.
            </div>
            {data.drug_considerations?.map((drug, i) => (
              <div key={i} className="drug-card">
                <div className="drug-header">
                  <div>
                    <div className="drug-name">{drug.name}</div>
                    <div className="drug-detail">{drug.class} · {drug.indication}</div>
                  </div>
                  <span className={`badge ${drug.risk === 'low' ? 'badge-low' : drug.risk === 'moderate' ? 'badge-moderate' : 'badge-high'}`}>
                    {drug.risk} risk
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', gap: 6, alignItems: 'flex-start' }}>
                  <span>⚠️</span>{drug.note}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* PANEL 4 — Lifestyle */}
      {revealed >= 4 && (
        <div className="card fade-up" style={{ animationDelay: '0.3s' }}>
          <div className="card-title"><Lightbulb size={14} /> Lifestyle &amp; Preventive Amendments</div>
          <div className="lifestyle-grid">
            {data.lifestyle?.map((item, i) => (
              <div key={i} className="lifestyle-item">
                <div className="lifestyle-icon">{item.icon}</div>
                <div className="lifestyle-text">{item.text}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      {revealed >= 5 && (
        <div className="disclaimer-footer fade-up">
          ⚕️ <strong>MediRAG Clinical Intelligence Oracle v3.0</strong> — Generated {new Date().toLocaleString()} ·
          This report was produced by an AI system using Graph RAG + Clinical AI Reasoner.
          It is NOT a medical diagnosis. All findings must be reviewed and confirmed by a qualified healthcare professional
          before any clinical decision is made. The developers accept no liability for clinical use of this output.
        </div>
      )}
    </div>
  )
}
