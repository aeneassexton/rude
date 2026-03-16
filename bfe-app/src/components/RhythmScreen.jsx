import { useState, useEffect } from 'react'
import './RhythmScreen.css'

const CM    = { green: '#4ade80', blue: '#4a9eff', gray: '#94a3b8', red: '#f87171' }
const WDAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']

export default function RhythmScreen({ api, userId, onBack, onForecast }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const today = new Date()

  useEffect(() => {
    fetch(`${api}/rhythm/${userId}?year=${today.getFullYear()}&month=${today.getMonth() + 1}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(setData)
      .catch(() => setData({ history: [], month: 'MARCH 2026' }))
      .finally(() => setLoading(false))
  }, [])

  const year  = today.getFullYear()
  const month = today.getMonth()
  const dim   = new Date(year, month + 1, 0).getDate()
  const off   = (new Date(year, month, 1).getDay() + 6) % 7
  const todayStr = today.toISOString().split('T')[0]

  const logMap = {}
  ;(data?.history || []).forEach(h => { logMap[h.date] = h })

  const cells = [...Array(off).fill(null), ...Array.from({ length: dim }, (_, i) => i + 1)]

  return (
    <div className="rh-screen">
      <div className="rh-nav">
        <button className="nav-pill blue"   onClick={onBack}>← Today</button>
        <button className="nav-pill orange" onClick={onForecast}>Forecast ›</button>
      </div>

      <h2 className="serif rh-title">Your Rhythm</h2>
      <p className="rh-month">{data?.month || `${today.toLocaleString('default', { month: 'long' }).toUpperCase()} ${year}`}</p>

      {loading ? (
        <div className="rh-loading"><div className="rh-pulse" /></div>
      ) : (
        <>
          <div className="cal-grid">
            {WDAYS.map((d, i) => <div key={i} className="cal-hd">{d}</div>)}
            {cells.map((day, i) => {
              if (!day) return <div key={`e${i}`} className="cal-cell empty" />
              const ds    = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
              const log   = logMap[ds]
              const color = log ? (CM[log.colour] || '#94a3b8') : null
              const isToday = ds === todayStr
              return (
                <div
                  key={day}
                  className={`cal-cell ${isToday ? 'is-today' : ''} ${log ? 'has-log' : ''}`}
                  style={color ? { '--cc': color } : {}}
                  title={log ? `${log.mood_label}` : ''}
                >
                  <span className="cal-num">{day}</span>
                  {log && <div className="cal-dot" style={{ background: color }} />}
                </div>
              )
            })}
          </div>

          <div className="rh-legend">
            {Object.entries(CM).map(([name, color]) => (
              <div key={name} className="leg-item">
                <div className="leg-dot" style={{ background: color }} />
                <span>{name}</span>
              </div>
            ))}
          </div>

          {data?.history?.length > 0 && (
            <div className="recent">
              <p className="recent-hd">Recent</p>
              {[...data.history].reverse().slice(0, 5).map(h => (
                <div key={h.date} className="recent-row">
                  <span className="recent-date">{h.date}</span>
                  <span className="recent-mood" style={{ color: CM[h.colour] || '#94a3b8' }}>{h.mood_label}</span>
                  <span className="recent-score">{h.mood_score}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
