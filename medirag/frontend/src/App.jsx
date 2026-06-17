// App.jsx — Main orchestrator for the 3-Act Clinical Intelligence Oracle
import { useState, useRef, useCallback } from 'react'
import { AlertTriangle } from 'lucide-react'
import './App.css'
import IntakeForm from './IntakeForm'
import ReasoningTheater from './ReasoningTheater'
import ResultsDashboard from './ResultsDashboard'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const WS_BASE  = import.meta.env.VITE_WS_BASE  || 'ws://localhost:8000'

// Steps: 0 = intake, 1 = theater, 2 = results
function StepDot({ step, current, label }) {
  const status = step < current ? 'done' : step === current ? 'active' : 'pending'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div className={`step-dot ${status}`}>{step < current ? '✓' : step + 1}</div>
      <span style={{ fontSize: '0.78rem', color: status === 'active' ? 'var(--text-primary)' : 'var(--text-muted)', fontWeight: status === 'active' ? 600 : 400 }}>
        {label}
      </span>
    </div>
  )
}

export default function App() {
  const [act, setAct]           = useState(0)   // 0=intake, 1=theater, 2=results
  const [events, setEvents]     = useState([])
  const [currentPhase, setPhase]= useState(null)
  const [isComplete, setIsComplete] = useState(false)
  const [finalResult, setFinalResult] = useState(null)
  const [communities, setCommunities] = useState([])
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] })
  const [sessionId, setSessionId]    = useState(null)
  const [patient, setPatient]        = useState(null)
  const [toast, setToast]            = useState(null)
  const wsRef = useRef(null)
  const isCompleteRef = useRef(false)

  const showToast = useCallback((msg, timeout = 4000) => {
    setToast(msg)
    setTimeout(() => setToast(null), timeout)
  }, [])

  // Demo mode — simulate events when backend is offline
  const simulateDemoMode = useCallback((formData) => {
    const phases = ['db_fetch', 'graph', 'community', 'retrieve', 'reasoning', 'report']
    const thinkTokens = [
      'Analyzing patient profile: ' + (formData.chief_complaint || 'presenting symptoms') + '\n',
      'Reviewing comorbidities: ' + (formData.comorbidities?.join(', ') || 'none reported') + '\n',
      'Cross-referencing PubMed literature for symptom cluster...\n',
      'Found 47 relevant studies. Key finding: fatigue + polyuria pattern matches T2DM with 87% specificity.\n',
      'Querying ClinVar for genetic variants associated with identified conditions...\n',
      'TCF7L2 rs7903146 identified — strongest T2DM risk variant. OR = 1.37 per allele.\n',
      'Running Leiden community detection on knowledge graph...\n',
      'Identified 3 disease communities: Metabolic, Cardiovascular, Thyroid.\n',
      'Hybrid retrieval: vector score 0.91, graph traversal 12 hops, community confidence 0.88\n',
      'Compiling differential diagnosis with confidence calibration...\n',
      'Primary: T2DM (87%), Metabolic Syndrome (71%), Hypothyroidism (42%)\n',
      'Generating evidence-backed rationale and clinical recommendations...\n',
    ]

    let phaseIdx = 0
    let tokenIdx = 0

    const phaseTimer = setInterval(() => {
      if (phaseIdx >= phases.length) { clearInterval(phaseTimer); return }
      setPhase(phases[phaseIdx])
      setEvents(prev => [...prev, { type: 'phase', phase: phases[phaseIdx], text: `Phase: ${phases[phaseIdx]}` }])

      if (phases[phaseIdx] === 'db_fetch') {
        ['search_pubmed', 'get_protein_info', 'query_clinvar', 'get_drug_interactions', 'check_fda_adverse_events'].forEach((tool, i) => {
          setTimeout(() => {
            setEvents(prev => [...prev, { type: 'tool_call', tool, status: 'running' }])
            setTimeout(() => setEvents(prev => [...prev, { type: 'tool_call', tool, status: 'done' }]), 1200)
          }, i * 300)
        })
      }
      if (phases[phaseIdx] === 'retrieve') {
        ['hybrid_search', 'query_graph', 'get_community_summary'].forEach((tool, i) => {
          setTimeout(() => {
            setEvents(prev => [...prev, { type: 'tool_call', tool, status: 'running' }])
            setTimeout(() => setEvents(prev => [...prev, { type: 'tool_call', tool, status: 'done' }]), 800)
          }, i * 400)
        })
      }

      phaseIdx++
    }, 2200)

    const tokenTimer = setInterval(() => {
      if (tokenIdx >= thinkTokens.length) { clearInterval(tokenTimer); return }
      setEvents(prev => [...prev, { type: 'reasoning', text: thinkTokens[tokenIdx] }])
      tokenIdx++
    }, 1400)

    setTimeout(() => {
      clearInterval(phaseTimer)
      clearInterval(tokenTimer)
      setIsComplete(true)
      isCompleteRef.current = true
      setPhase('done')
      setEvents(prev => [...prev, { type: 'final_answer', data: null }])
      setTimeout(() => setAct(2), 1800)
    }, phases.length * 2200 + 1000)
  }, [])

  const handleIntakeSubmit = useCallback(async (formData, file) => {
    setPatient(formData)
    setAct(1)
    setEvents([])
    setPhase('db_fetch')
    setIsComplete(false)
    isCompleteRef.current = false
    setFinalResult(null)

    try {
      const fd = new FormData()
      fd.append('patient_data', JSON.stringify(formData))
      if (file) fd.append('file', file)

      const resp = await fetch(`${API_BASE}/oracle/start`, { method: 'POST', body: fd })
      if (!resp.ok) throw new Error('Backend returned ' + resp.status)
      const { session_id } = await resp.json()
      setSessionId(session_id)

      const ws = new WebSocket(`${WS_BASE}/ws/${session_id}`)
      wsRef.current = ws

      ws.onmessage = (msg) => {
        const event = JSON.parse(msg.data)
        setEvents(prev => [...prev, event])

        if (event.type === 'phase')        setPhase(event.phase)
        if (event.type === 'communities')  setCommunities(event.data)
        if (event.type === 'graph_data')   setGraphData(event.data)
        if (event.type === 'final_answer') {
          setFinalResult(event.data)
          setIsComplete(true)
          isCompleteRef.current = true
          setPhase('done')
          setTimeout(() => setAct(2), 1800)
        }
        if (event.type === 'error') {
          showToast('⚠️ ' + event.text)
          setIsComplete(true)
          isCompleteRef.current = true
        }
      }
      ws.onerror = () => {
        showToast('WebSocket error — please check backend server.')
        setIsComplete(true)
        isCompleteRef.current = true
        setPhase('error')
      }
      ws.onclose = () => {
        if (!isCompleteRef.current) setIsComplete(true)
      }
    } catch (err) {
      console.warn('Backend unavailable:', err)
      showToast('🔌 Backend offline or API failed. Please check backend server and API keys.', 6000)
      setIsComplete(true)
      isCompleteRef.current = true
      setPhase('error')
    }
  }, [showToast])

  const handleReset = () => {
    if (wsRef.current) wsRef.current.close()
    isCompleteRef.current = false
    setAct(0)
    setEvents([])
    setPhase(null)
    setIsComplete(false)
    setFinalResult(null)
    setCommunities([])
    setGraphData({ nodes: [], edges: [] })
    setSessionId(null)
    setPatient(null)
  }

  const STEP_LABELS = ['Patient Intake', 'Oracle Reasoning', 'Diagnostic Artifacts']

  return (
    <div className="app-wrapper gradient-bg">
      {/* Navigation */}
      <nav className="top-nav">
        <div className="nav-brand">
          <div className="nav-logo-icon">⚕️</div>
          <div>
            <div className="nav-title">Medi<span>RAG</span></div>
            <div className="nav-subtitle">Clinical Intelligence Oracle</div>
          </div>
        </div>

        {/* Step tracker */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {STEP_LABELS.map((label, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
              <StepDot step={i} current={act} label={label} />
              {i < STEP_LABELS.length - 1 && (
                <div className={`step-connector ${act > i ? 'active' : ''}`} style={{ margin: '0 8px' }} />
              )}
            </div>
          ))}
        </div>

        <div className="nav-badge">
          <AlertTriangle size={10} style={{ display: 'inline', marginRight: 4 }} />
          Not a Diagnosis
        </div>
      </nav>

      {/* Acts */}
      {act === 0 && <IntakeForm onSubmit={handleIntakeSubmit} />}
      {act === 1 && (
        <ReasoningTheater
          events={events}
          currentPhase={currentPhase}
          isComplete={isComplete}
        />
      )}
      {act === 2 && (
        <ResultsDashboard
          result={finalResult}
          communities={communities}
          graphData={graphData}
          patient={patient}
          sessionId={sessionId}
          onReset={handleReset}
        />
      )}

      {/* Toast */}
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
