import { useState, useEffect } from 'react'
import './ForecastScreen.css'

const CM = { green: '#4ade80', blue: '#4a9eff', gray: '#94a3b8', red: '#f87171' }

export default function ForecastScreen({ api, userId, onBack, onRhythm }) {
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    fetch(`${api}/forecast/${userId}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(setData)
      .catch(() => setError('Backend not reachable.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="fc-screen">
      <div className="fc-nav">
        <button className="nav-pill blue"   onClick={onBack}>← Today</button>
        <button className="nav-pill orange" onClick={onRhythm}>Rhythm ›</button>
      </div>

      {loading && (
        <div className="fc-loading">
          <div className="fc-pulse" />
          <p>Running forecast…</p>
        </div>
      )}

      {error && <div className="fc-error">⚠ {error}</div>}

      {data && <>
        <h2 className="serif fc-title">The Week Ahead</h2>
        {data.alert && <div className="alert-pill">⚡ Anomaly in your baseline</div>}

        <div className="day-strip">
          {data.week.map((d, i) => {
            const c = CM[d.colour] || '#94a3b8'
            return (
              <div key={d.date} className="day-card" style={{ '--dc': c, animationDelay: `${i * 55}ms` }}>
                <span className="day-name">{d.day}</span>
                <div className="day-orb" style={{ border: `1px solid ${c}50`, background: `radial-gradient(circle,${c}25,transparent)` }}>
                  <span className="day-score" style={{ color: c }}>{d.mood_score.toFixed(1)}</span>
                </div>
                <span className="day-lbl">{d.mood_label}</span>
                <span className="day-ci">{d.ci_lower.toFixed(1)}–{d.ci_upper.toFixed(1)}</span>
              </div>
            )
          })}
        </div>

        <div className="insights">
          <Card icon="◈" title="Pattern" body={data.pattern} />
          <Card icon="↗" title="Trend"   body={data.trend}   />
        </div>

        <div className="accordion">
          <button className="acc-btn" onClick={() => setExpanded(!expanded)}>
            <span>🌐 Externally Impacted Forecasts</span>
            <span className={`acc-arrow ${expanded ? 'open' : ''}`}>›</span>
          </button>
          {expanded && (
            <div className="acc-body">
              {[
                ['🌦', 'Environment',       ['Sunlight', 'Temperature', 'UV Index', 'Precipitation']],
                ['👥', 'Social & Schedule', ['Calendar density', 'Social battery', 'Group vs Solo']],
                ['🍎', 'Lifestyle',         ['Caffeine timing', 'Meal patterns', 'Sleep env']],
                ['🏃', 'Activity',          ['Outdoor movement', 'Mindfulness', 'Light exposure']],
              ].map(([icon, label, items]) => (
                <div key={label} className="ext-row">
                  <div className="ext-hd"><span>{icon}</span><span className="ext-lbl">{label}</span></div>
                  <div className="ext-chips">{items.map(it => <span key={it} className="chip">{it}</span>)}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <p className="credits-note">Credits remaining: {data.credits_remaining}</p>
      </>}
    </div>
  )
}

function Card({ icon, title, body }) {
  return (
    <div className="insight-card">
      <span className="ic-icon">{icon}</span>
      <div>
        <p className="ic-title">{title}</p>
        <p className="ic-body">{body}</p>
      </div>
    </div>
  )
}
