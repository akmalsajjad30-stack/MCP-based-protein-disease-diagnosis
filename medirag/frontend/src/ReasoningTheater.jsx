// ReasoningTheater.jsx — ACT 2: The Oracle thinks. Live streaming view.
import { useEffect, useRef, useState } from 'react'
import { Brain, Zap, Database, GitBranch, Search, FileText, CheckCircle2 } from 'lucide-react'

const PHASES = [
  { id: 'db_fetch',   icon: <Database size={14} />,    label: 'Querying Biomedical Databases', sub: 'PubMed · UniProt · ClinVar · ChEMBL · FDA' },
  { id: 'graph',      icon: <GitBranch size={14} />,   label: 'Building Knowledge Graph', sub: 'Neo4j · Entity extraction · Relationship mapping' },
  { id: 'community',  icon: <Zap size={14} />,         label: 'Leiden Community Detection', sub: 'Clustering disease networks · Generating summaries' },
  { id: 'retrieve',   icon: <Search size={14} />,      label: 'Hybrid Retrieval (RRF Fusion)', sub: 'Vector + Graph + Community — ranked fusion' },
  { id: 'reasoning',  icon: <Brain size={14} />,       label: 'Clinical Reasoner Active', sub: 'Chain-of-thought clinical inference' },
  { id: 'report',     icon: <FileText size={14} />,    label: 'Compiling Diagnostic Artifacts', sub: 'Structuring results · Building PDF' },
]

const TOOL_CHIPS = [
  { name: 'search_pubmed', emoji: '📚' },
  { name: 'get_protein_info', emoji: '🧬' },
  { name: 'query_clinvar', emoji: '🔬' },
  { name: 'get_drug_interactions', emoji: '💊' },
  { name: 'check_fda_adverse_events', emoji: '⚠️' },
  { name: 'get_clinical_trials', emoji: '🏥' },
  { name: 'query_graph', emoji: '🕸️' },
  { name: 'get_community_summary', emoji: '🌐' },
  { name: 'hybrid_search', emoji: '🔀' },
  { name: 'generate_report', emoji: '📄' },
]

function EEGWaveform({ intensity = 1 }) {
  const canvasRef = useRef()
  const frameRef = useRef()
  const offsetRef = useRef(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    canvas.width = canvas.offsetWidth * window.devicePixelRatio
    canvas.height = canvas.offsetHeight * window.devicePixelRatio
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
    const w = canvas.offsetWidth, h = canvas.offsetHeight

    const draw = () => {
      ctx.clearRect(0, 0, w, h)
      ctx.strokeStyle = 'rgba(110,231,183,0.7)'
      ctx.lineWidth = 1.5
      ctx.shadowColor = 'rgba(110,231,183,0.5)'
      ctx.shadowBlur = 6

      ctx.beginPath()
      for (let x = 0; x < w; x++) {
        const t = (x + offsetRef.current) / w
        const y = h / 2
          + Math.sin(t * 12 * Math.PI) * 18 * intensity
          + Math.sin(t * 4 * Math.PI) * 8 * intensity
          + Math.sin(t * 30 * Math.PI) * 3 * intensity
          + (Math.random() - 0.5) * 2 * intensity
        if (x === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.stroke()

      offsetRef.current += 3
      frameRef.current = requestAnimationFrame(draw)
    }
    draw()
    return () => cancelAnimationFrame(frameRef.current)
  }, [intensity])

  return <canvas ref={canvasRef} style={{ width: '100%', height: 80, display: 'block' }} />
}

export default function ReasoningTheater({ events, currentPhase, isComplete }) {
  const streamRef = useRef()
  const [toolStates, setToolStates] = useState({})
  const thoughtChunks = events.filter(e => e.type === 'reasoning').map(e => e.text).join('')
  const toolEvents = events.filter(e => e.type === 'tool_call')

  // Track tool states
  useEffect(() => {
    toolEvents.forEach(ev => {
      setToolStates(prev => ({ ...prev, [ev.tool]: ev.status || 'running' }))
    })
  }, [toolEvents])

  // Auto-scroll thought stream
  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight
    }
  }, [thoughtChunks])

  const activePhaseIndex = PHASES.findIndex(p => p.id === currentPhase)
  const intensity = currentPhase === 'reasoning' ? 2.5 : currentPhase ? 1.2 : 0.3

  const phaseStatus = (phaseId) => {
    const idx = PHASES.findIndex(p => p.id === phaseId)
    if (idx < activePhaseIndex) return 'done'
    if (idx === activePhaseIndex) return 'active'
    return 'pending'
  }

  return (
    <div className="page" style={{ marginTop: 64 }}>
      <div className="theater-header fade-up">
        <div className="oracle-status">
          {isComplete
            ? <CheckCircle2 size={16} color="var(--accent)" />
            : <div className="spinner" />}
          <span className="oracle-status-text">
            {isComplete ? 'ANALYSIS COMPLETE' : 'ORACLE REASONING…'}
          </span>
        </div>
        <h2>The Oracle Is Thinking</h2>
        <p>Querying 7 biomedical databases · Building knowledge graph · Reasoning with AI</p>
      </div>

      <div className="theater">
        {/* LEFT MAIN PANEL */}
        <div className="theater-main">
          {/* EEG */}
          <div className="eeg-panel fade-up">
            <div className="eeg-label">🧠 NEURAL ACTIVITY — REASONING DENSITY</div>
            <div className="eeg-canvas-wrapper">
              <EEGWaveform intensity={intensity} />
            </div>
          </div>

          {/* Phase tracker */}
          <div className="card fade-up fade-up-delay-1">
            <div className="card-title"><Zap size={14} /> Pipeline Execution</div>
            <div className="phase-list">
              {PHASES.map((phase) => {
                const status = phaseStatus(phase.id)
                return (
                  <div key={phase.id} className={`phase-item ${status}`}>
                    <div className="phase-icon">{phase.icon}</div>
                    <div style={{ flex: 1 }}>
                      <div className="phase-name">{phase.label}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>
                        {phase.sub}
                      </div>
                    </div>
                    <div className="phase-status">
                      {status === 'done' && <CheckCircle2 size={14} color="var(--accent)" />}
                      {status === 'active' && <div className="spinner" style={{ width: 14, height: 14 }} />}
                      {status === 'pending' && <span style={{ opacity: 0.4 }}>—</span>}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Thought stream */}
          <div className="thought-panel fade-up fade-up-delay-2">
            <div className="thought-header">
              <div className="thought-title">
                <div className="pulse-dot" />
                AI Chain-of-Thought Stream
              </div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                {thoughtChunks.split(' ').filter(Boolean).length} tokens
              </span>
            </div>
            <div ref={streamRef} className="thought-stream-box">
              {thoughtChunks
                ? thoughtChunks.split('\n').map((line, i) => (
                    <div key={i} className="thought-chunk" style={{ marginBottom: 4 }}>
                      {line || <br />}
                    </div>
                  ))
                : <span style={{ opacity: 0.4 }}>Awaiting reasoning stream…</span>
              }
            </div>
          </div>
        </div>

        {/* RIGHT SIDEBAR */}
        <div className="tools-sidebar">
          {/* MCP Tools */}
          <div className="tools-panel fade-up">
            <div className="tools-panel-title">🔌 MCP Tools</div>
            <div className="tool-grid">
              {TOOL_CHIPS.map(tool => {
                const state = toolStates[tool.name] || 'pending'
                return (
                  <div key={tool.name}
                    className={`tool-chip ${state === 'running' ? 'running' : state === 'done' ? 'done' : ''}`}>
                    <span>{tool.emoji}</span>
                    <span>{tool.name}</span>
                    {state === 'running' && <div className="spinner" style={{ width: 10, height: 10, marginLeft: 'auto' }} />}
                    {state === 'done' && <CheckCircle2 size={10} style={{ marginLeft: 'auto' }} />}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Status events */}
          <div className="tools-panel fade-up fade-up-delay-1">
            <div className="tools-panel-title">📡 Event Log</div>
            <div style={{ maxHeight: 280, overflowY: 'auto', fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
              {events.filter(e => e.type !== 'think_token' && e.type !== 'answer_chunk').slice(-20).map((ev, i) => (
                <div key={i} style={{ marginBottom: 4, lineHeight: 1.5 }}>
                  <span style={{ color: 'var(--accent)', opacity: 0.6 }}>[{ev.type}]</span>{' '}
                  {ev.text || ev.phase || ev.tool || ''}
                </div>
              ))}
              {events.length === 0 && (
                <span style={{ opacity: 0.4 }}>Waiting for events…</span>
              )}
            </div>
          </div>

          {/* DB Sources */}
          <div className="tools-panel fade-up fade-up-delay-2">
            <div className="tools-panel-title">🗄️ Data Sources</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {[
                ['PubMed', '#60a5fa'],
                ['UniProt', '#a78bfa'],
                ['ClinVar', '#f87171'],
                ['ChEMBL', '#fbbf24'],
                ['FDA FAERS', '#f87171'],
                ['ClinTrials', '#6ee7b7'],
                ['OMIM', '#a78bfa'],
              ].map(([name, color]) => (
                <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.78rem' }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0 }} />
                  <span style={{ color: 'var(--text-secondary)' }}>{name}</span>
                  {phaseStatus('db_fetch') !== 'pending' && (
                    <CheckCircle2 size={10} color="var(--accent)" style={{ marginLeft: 'auto' }} />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
