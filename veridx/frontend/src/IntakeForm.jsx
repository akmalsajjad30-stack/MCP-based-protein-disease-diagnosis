// IntakeForm.jsx — ACT 1: Patient intake (clinical kiosk, not a chatbot)
import { useState, useRef } from 'react'
import { Upload, ChevronRight, Activity, AlertTriangle } from 'lucide-react'

const SYMPTOM_OPTIONS = [
  'Fatigue', 'Fever', 'Cough', 'Shortness of Breath', 'Chest Pain',
  'Headache', 'Dizziness', 'Nausea', 'Joint Pain', 'Muscle Weakness',
  'Weight Loss', 'Night Sweats', 'Abdominal Pain', 'Swelling', 'Palpitations',
  'Vision Changes', 'Skin Rash', 'Back Pain', 'Confusion', 'Frequent Urination',
]

const COMORBIDITY_OPTIONS = [
  'Hypertension', 'Type 2 Diabetes', 'Type 1 Diabetes', 'Asthma', 'COPD',
  'Coronary Artery Disease', 'Heart Failure', 'CKD', 'Hypothyroidism',
  'Hyperthyroidism', 'Obesity', 'Depression', 'Anxiety', 'Rheumatoid Arthritis',
  'Lupus', 'HIV', 'Hepatitis B', 'Hepatitis C', 'Cancer (remission)', 'Epilepsy',
]

export default function IntakeForm({ onSubmit }) {
  const [form, setForm] = useState({
    age: '', sex: '', weight_kg: '', height_cm: '',
    chief_complaint: '', symptoms: [],
    duration_days: '', comorbidities: [],
    current_medications: '', allergies: '',
    family_history: '', smoking: 'never', alcohol: 'none',
    lab_notes: '', extra_context: '',
    use_reasoner: true,
  })
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const fileRef = useRef()

  const toggle = (field, value) => {
    setForm(f => ({
      ...f,
      [field]: f[field].includes(value)
        ? f[field].filter(x => x !== value)
        : [...f[field], value],
    }))
  }

  const handleFile = (e) => {
    const f = e.target.files?.[0] || e.dataTransfer?.files?.[0]
    if (f) setFile(f)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!form.age || !form.chief_complaint || form.symptoms.length === 0) {
      alert('Please fill in Age, Chief Complaint, and select at least one symptom.')
      return
    }
    onSubmit(form, file)
  }

  return (
    <div className="page gradient-bg" style={{ marginTop: 64 }}>
      <div className="intake-hero fade-up">
        <h1>Clinical Patient Intake</h1>
        <p>Complete the structured profile. The Oracle will analyze it without back-and-forth conversation.</p>
        <div className="disclaimer-banner" style={{ maxWidth: 600, margin: '0 auto' }}>
          <AlertTriangle size={14} />
          For informational use only. Not a substitute for professional medical advice.
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        {/* ── DEMOGRAPHICS ── */}
        <div className="form-section fade-up fade-up-delay-1">
          <div className="form-section-title">
            <Activity size={14} /> Patient Demographics
          </div>
          <div className="form-grid">
            <div>
              <label className="input-label">Age (years) *</label>
              <input className="input-field" type="number" min={1} max={120} placeholder="e.g. 45"
                value={form.age} onChange={e => setForm(f => ({...f, age: e.target.value}))} required />
            </div>
            <div>
              <label className="input-label">Biological Sex *</label>
              <select className="input-field" value={form.sex}
                onChange={e => setForm(f => ({...f, sex: e.target.value}))} required>
                <option value="">Select…</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other / Non-binary</option>
              </select>
            </div>
            <div>
              <label className="input-label">Weight (kg)</label>
              <input className="input-field" type="number" min={1} placeholder="e.g. 75"
                value={form.weight_kg} onChange={e => setForm(f => ({...f, weight_kg: e.target.value}))} />
            </div>
            <div>
              <label className="input-label">Height (cm)</label>
              <input className="input-field" type="number" min={50} placeholder="e.g. 170"
                value={form.height_cm} onChange={e => setForm(f => ({...f, height_cm: e.target.value}))} />
            </div>
          </div>
          <div className="form-grid-3">
            <div>
              <label className="input-label">Smoking Status</label>
              <select className="input-field" value={form.smoking}
                onChange={e => setForm(f => ({...f, smoking: e.target.value}))}>
                <option value="never">Never</option>
                <option value="former">Former</option>
                <option value="current">Current</option>
              </select>
            </div>
            <div>
              <label className="input-label">Alcohol Use</label>
              <select className="input-field" value={form.alcohol}
                onChange={e => setForm(f => ({...f, alcohol: e.target.value}))}>
                <option value="none">None</option>
                <option value="social">Social</option>
                <option value="moderate">Moderate</option>
                <option value="heavy">Heavy</option>
              </select>
            </div>
            <div>
              <label className="input-label">Symptom Duration (days)</label>
              <input className="input-field" type="number" min={1} placeholder="e.g. 14"
                value={form.duration_days} onChange={e => setForm(f => ({...f, duration_days: e.target.value}))} />
            </div>
          </div>
        </div>

        {/* ── CHIEF COMPLAINT ── */}
        <div className="form-section fade-up fade-up-delay-1">
          <div className="form-section-title">🩺 Presenting Complaint</div>
          <div>
            <label className="input-label">Chief Complaint *</label>
            <textarea className="input-field" rows={3}
              placeholder="Describe the primary reason for consultation in the patient's own words…"
              value={form.chief_complaint}
              onChange={e => setForm(f => ({...f, chief_complaint: e.target.value}))} required />
          </div>
        </div>

        {/* ── SYMPTOMS ── */}
        <div className="form-section fade-up fade-up-delay-2">
          <div className="form-section-title">⚡ Symptom Checklist * (select all that apply)</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {SYMPTOM_OPTIONS.map(s => (
              <button type="button" key={s}
                onClick={() => toggle('symptoms', s)}
                style={{
                  padding: '6px 14px', borderRadius: 99, fontSize: '0.82rem',
                  fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s',
                  background: form.symptoms.includes(s) ? 'var(--accent)' : 'var(--bg-elevated)',
                  color: form.symptoms.includes(s) ? '#020817' : 'var(--text-secondary)',
                  border: form.symptoms.includes(s)
                    ? '1px solid var(--accent)'
                    : '1px solid var(--border-bright)',
                }}>
                {s}
              </button>
            ))}
          </div>
          <div style={{ marginTop: 12 }}>
            <label className="input-label">Additional Symptoms (free text)</label>
            <input className="input-field" placeholder="Any other symptoms not listed above…"
              value={form.lab_notes}
              onChange={e => setForm(f => ({...f, lab_notes: e.target.value}))} />
          </div>
        </div>

        {/* ── COMORBIDITIES ── */}
        <div className="form-section fade-up fade-up-delay-2">
          <div className="form-section-title">🏥 Known Comorbidities &amp; Medical History</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
            {COMORBIDITY_OPTIONS.map(c => (
              <button type="button" key={c}
                onClick={() => toggle('comorbidities', c)}
                style={{
                  padding: '6px 14px', borderRadius: 99, fontSize: '0.82rem',
                  fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s',
                  background: form.comorbidities.includes(c) ? 'rgba(167,139,250,0.2)' : 'var(--bg-elevated)',
                  color: form.comorbidities.includes(c) ? 'var(--purple)' : 'var(--text-secondary)',
                  border: form.comorbidities.includes(c)
                    ? '1px solid var(--purple)'
                    : '1px solid var(--border-bright)',
                }}>
                {c}
              </button>
            ))}
          </div>
          <div className="form-grid">
            <div>
              <label className="input-label">Current Medications</label>
              <textarea className="input-field" rows={2}
                placeholder="List with dosages, e.g. Metformin 500mg BID, Lisinopril 10mg QD…"
                value={form.current_medications}
                onChange={e => setForm(f => ({...f, current_medications: e.target.value}))} />
            </div>
            <div>
              <label className="input-label">Allergies</label>
              <textarea className="input-field" rows={2}
                placeholder="Drug allergies, food allergies, reaction type…"
                value={form.allergies}
                onChange={e => setForm(f => ({...f, allergies: e.target.value}))} />
            </div>
          </div>
          <div>
            <label className="input-label">Family History</label>
            <input className="input-field" placeholder="Notable first-degree relative diagnoses…"
              value={form.family_history}
              onChange={e => setForm(f => ({...f, family_history: e.target.value}))} />
          </div>
        </div>

        {/* ── LAB UPLOAD ── */}
        <div className="form-section fade-up fade-up-delay-3">
          <div className="form-section-title">📎 Lab Report Upload (optional)</div>
          <div
            className={`file-drop-zone ${dragging ? 'dragging' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => { e.preventDefault(); setDragging(false); handleFile(e) }}
            onClick={() => fileRef.current?.click()}
          >
            <input ref={fileRef} type="file" accept=".pdf,.docx,.png,.jpg,.jpeg"
              onChange={handleFile} style={{ display: 'none' }} />
            {file ? (
              <>
                <div className="file-drop-icon">✅</div>
                <div className="file-attached">{file.name}</div>
                <div className="file-drop-hint">{(file.size / 1024).toFixed(1)} KB — click to replace</div>
              </>
            ) : (
              <>
                <div className="file-drop-icon"><Upload size={32} color="var(--text-muted)" /></div>
                <div className="file-drop-text">Drag &amp; drop or click to upload lab report</div>
                <div className="file-drop-hint">PDF, DOCX, PNG, JPG — max 10MB</div>
              </>
            )}
          </div>
          <div style={{ marginTop: 16 }}>
            <label className="input-label">Additional Context</label>
            <textarea className="input-field" rows={2}
              placeholder="Any additional clinical context, recent procedures, travel history…"
              value={form.extra_context}
              onChange={e => setForm(f => ({...f, extra_context: e.target.value}))} />
          </div>
        </div>

        {/* ── REASONING MODE ── */}
        <div className="form-section fade-up fade-up-delay-3">
          <div className="form-section-title">🧠 Analysis Mode</div>
          <div style={{ display: 'flex', gap: 16 }}>
            <button type="button"
              onClick={() => setForm(f => ({...f, use_reasoner: true}))}
              style={{
                flex: 1, padding: '16px', borderRadius: 'var(--radius)',
                border: form.use_reasoner ? '2px solid var(--accent)' : '1px solid var(--border)',
                background: form.use_reasoner ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                cursor: 'pointer', transition: 'all 0.2s',
              }}>
              <div style={{ fontSize: '1.5rem', marginBottom: 6 }}>🔬</div>
              <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
                Clinical Reasoner
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Deep chain-of-thought reasoning. Slower, more thorough. Recommended.
              </div>
            </button>
            <button type="button"
              onClick={() => setForm(f => ({...f, use_reasoner: false}))}
              style={{
                flex: 1, padding: '16px', borderRadius: 'var(--radius)',
                border: !form.use_reasoner ? '2px solid var(--blue)' : '1px solid var(--border)',
                background: !form.use_reasoner ? 'rgba(96,165,250,0.1)' : 'var(--bg-elevated)',
                cursor: 'pointer', transition: 'all 0.2s',
              }}>
              <div style={{ fontSize: '1.5rem', marginBottom: 6 }}>⚡</div>
              <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
                Standard LLM
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Fast standard analysis. Better for quick consultation.
              </div>
            </button>
          </div>
        </div>

        {/* ── SUBMIT ── */}
        <div className="submit-zone">
          <button type="submit" className="submit-btn">
            <Activity size={20} />
            Invoke the Oracle
            <ChevronRight size={20} />
          </button>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            The Oracle will silently analyze your data, then reveal structured diagnostic artifacts.
          </p>
        </div>
      </form>
    </div>
  )
}
