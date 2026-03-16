import { useState } from 'react'
import { supabase } from '../supabaseClient'
import './AuthScreen.css'

export default function AuthScreen({ onAuth }) {
  const [email, setEmail]   = useState('')
  const [sent, setSent]     = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState(null)

  async function handleSubmit() {
    if (!email.trim()) return
    setLoading(true)
    setError(null)
    const { error: err } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: {
        emailRedirectTo: window.location.origin,
      }
    })
    setLoading(false)
    if (err) { setError(err.message); return }
    setSent(true)
  }

  if (sent) return (
    <div className="auth-screen">
      <div className="auth-inner">
        <div className="auth-orb" />
        <h1 className="serif auth-title">Check your email</h1>
        <p className="auth-sub">We sent a link to <strong>{email}</strong>.<br />Tap it to sign in.</p>
        <button className="auth-back" onClick={() => setSent(false)}>Use a different email</button>
      </div>
    </div>
  )

  return (
    <div className="auth-screen">
      <div className="auth-inner">
        <div className="auth-orb" />
        <h1 className="serif auth-title">Rude</h1>
        <p className="auth-sub">Behavioural forecasting.<br />Enter your email to continue.</p>
        <div className="auth-field">
          <input
            className="auth-input"
            type="email"
            placeholder="your@email.com"
            value={email}
            onChange={e => setEmail(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            autoFocus
          />
          <button
            className="auth-btn"
            onClick={handleSubmit}
            disabled={loading || !email.trim()}
          >
            {loading ? '…' : 'Continue →'}
          </button>
        </div>
        {error && <p className="auth-err">{error}</p>}
      </div>
    </div>
  )
}
