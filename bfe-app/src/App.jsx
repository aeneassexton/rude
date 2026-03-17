import { useState, useEffect } from 'react'
import { supabase } from './supabaseClient'
import AuthScreen     from './components/AuthScreen'
import CheckInScreen  from './components/CheckInScreen'
import ForecastScreen from './components/ForecastScreen'
import RhythmScreen   from './components/RhythmScreen'
import './App.css'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export default function App() {
  const [session, setSession] = useState(null)
  const [screen, setScreen]   = useState('checkin')
  const [booting, setBooting] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session); setBooting(false)
    })
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session); setBooting(false)
    })
    return () => subscription.unsubscribe()
  }, [])

  if (booting) return <div style={{height:'100vh',display:'flex',alignItems:'center',justifyContent:'center'}}><div style={{width:44,height:44,borderRadius:'50%',border:'1px solid #4a9eff',animation:'pulse 1.2s ease-in-out infinite'}}/></div>

  if (!session) return <AuthScreen />

  const props = { api: API, userId: session.user.id, token: session.access_token }

  return (
    <div className="app">
      {screen === 'checkin'  && <CheckInScreen  {...props} onForecast={() => setScreen('forecast')} onInsights={() => setScreen('rhythm')} />}
      {screen === 'forecast' && <ForecastScreen {...props} onBack={() => setScreen('checkin')} onRhythm={() => setScreen('rhythm')} />}
      {screen === 'rhythm'   && <RhythmScreen   {...props} onBack={() => setScreen('checkin')} onForecast={() => setScreen('forecast')} />}
    </div>
  )
}
