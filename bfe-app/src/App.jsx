import { useState } from 'react'
import CheckInScreen from './components/CheckInScreen'
import ForecastScreen from './components/ForecastScreen'
import RhythmScreen from './components/RhythmScreen'
import './index.css'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const USER_ID = 'local_user'

export default function App() {
  const [screen, setScreen] = useState('checkin')

  return (
    <div className="app-shell">
      <div className="titlebar" />
      <div className="screen">
        {screen === 'checkin'  && (
          <CheckInScreen
            api={API} userId={USER_ID}
            onForecast={() => setScreen('forecast')}
            onInsights={() => setScreen('rhythm')}
          />
        )}
        {screen === 'forecast' && (
          <ForecastScreen
            api={API} userId={USER_ID}
            onBack={() => setScreen('checkin')}
            onRhythm={() => setScreen('rhythm')}
          />
        )}
        {screen === 'rhythm' && (
          <RhythmScreen
            api={API} userId={USER_ID}
            onBack={() => setScreen('checkin')}
            onForecast={() => setScreen('forecast')}
          />
        )}
      </div>
    </div>
  )
}
