import { useState, useRef } from 'react'
import './CheckInScreen.css'
import { useState, useRef, useEffect } from 'react'

const MOODS = [
  { label: 'Radiant', color: '#4ade80', glow: '#4ade8050' },
  { label: 'Steady',  color: '#4a9eff', glow: '#4a9eff50' },
  { label: 'Tired',   color: '#e8714a', glow: '#e8714a50' },
  { label: 'Heavy',   color: '#818cf8', glow: '#818cf850' },
]

export default function CheckInScreen({ api, userId, onForecast, onInsights }) {
  const [selected, setSelected]   = useState(null)
  const [rotation, setRotation]   = useState(0)
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)
  const dragging  = useRef(false)
  const lastAngle = useRef(0)
  const wheelRef  = useRef(null)
  useEffect(() => {
    fetch(`${api}/rhythm/${userId}?year=${new Date().getFullYear()}&month=${new Date().getMonth()+1}`)
      .then(r => r.json())
      .then(data => {
        if (data.history?.length > 0) {
          const last = data.history[data.history.length - 1]
          const match = MOODS.find(m => m.label.toLowerCase() === last.mood_label.toLowerCase())
          if (match) setSelected(match)
        }
      }).catch(() => {})
  }, [])

  function centerAngle(e) {
    const el   = wheelRef.current
    const rect = el.getBoundingClientRect()
    const cx   = rect.left + rect.width  / 2
    const cy   = rect.top  + rect.height / 2
    const px   = e.touches ? e.touches[0].clientX : e.clientX
    const py   = e.touches ? e.touches[0].clientY : e.clientY
    return Math.atan2(py - cy, px - cx) * (180 / Math.PI)
  }

  function onDown(e) {
    dragging.current  = true
    lastAngle.current = centerAngle(e)
    e.currentTarget.setPointerCapture(e.pointerId)
  }

  function onMove(e) {
    if (!dragging.current) return
    const a     = centerAngle(e)
    const delta = a - lastAngle.current
    lastAngle.current = a
    setRotation(r => Math.max(-135, Math.min(135, r + delta)))
  }

  function onUp() {
    if (!dragging.current) return
    dragging.current = false
    const step       = 360 / MOODS.length
    const snapped    = Math.round(rotation / step) * step
    setRotation(snapped)
    const norm       = ((snapped % 360) + 360) % 360
    const idx        = ((Math.round(norm / step) % MOODS.length) + MOODS.length) % MOODS.length
    const chosenMood = MOODS[idx]
    setSelected(chosenMood)
    logMood(chosenMood)
  }

  async function logMood(mood) {
    if (!mood) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${api}/mood/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mood_label: mood.label })
      })
      if (!res.ok) throw new Error()
      setSubmitted(true)
    } catch {
      setError('Could not reach backend.')
    } finally {
      setLoading(false)
    }
  }

  if (submitted && selected) return (
    <div className="ci-done">
      <div className="done-orb" style={{ background: selected.glow, boxShadow: `0 0 120px ${selected.color}40` }} />
      <h2 className="serif done-word" style={{ color: selected.color }}>{selected.label}</h2>
      <p className="done-sub">logged for today</p>
      <button className="done-again" onClick={() => { setSubmitted(false); setSelected(null); setRotation(0) }}>
        log again
      </button>
    </div>
  )

  return (
    <div className="ci-screen">
      <div className="ci-nav">
        <button className="nav-pill blue"   onClick={onForecast}>Forecast +</button>
        <button className="nav-pill orange" onClick={onInsights}>Insights ›</button>
      </div>

      <div className="ci-heading">
        <h1 className="serif ci-title">
          {selected ? `Feeling ${selected.label}` : 'How are you feeling?'}
        </h1>
      </div>

      <div className="wheel-anchor">
        <div
          className="wheel-ring"
          ref={wheelRef}
          onPointerDown={onDown}
          onPointerMove={onMove}
          onPointerUp={onUp}
          onPointerCancel={onUp}
          style={{ transform: `rotate(${rotation}deg)` }}
        >
          {MOODS.map((mood, i) => {
            const deg = (i / MOODS.length) * 360
            const rad = (deg - 90) * (Math.PI / 180)
            const R   = 38
            const x   = 50 + R * Math.cos(rad)
            const y   = 50 + R * Math.sin(rad)
            return (
              <div
                key={mood.label}
                className={`mn ${selected?.label === mood.label ? 'mn-on' : ''}`}
                style={{
                  left: `${x}%`, top: `${y}%`,
                  '--mc': mood.color, '--mg': mood.glow,
                  transform: `translate(-50%,-50%) rotate(${-rotation}deg)`,
                }}
                onClick={() => { setSelected(mood); logMood(mood) }}
              >
                {selected?.label === mood.label
                  ? <span className="mn-word" style={{ color: mood.color }}>{mood.label}</span>
                  : null
                }
              </div>
            )
          })}
          <div className="wheel-hub" />
        </div>
      </div>

      {loading && <p className="ci-loading">Saving...</p>}
      {error   && <p className="ci-err">{error}</p>}
    </div>
  )
}
