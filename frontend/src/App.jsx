import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import Predictor from './pages/Predictor'
import Forecast from './pages/Forecast'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'
import Commute from './pages/Commute'
import Privacy from './pages/Privacy'
import Terms from './pages/Terms'
import NotFound from './pages/NotFound'
import Footer from './components/Footer'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col justify-between" style={{ background: 'var(--bg-primary)' }}>
      <Navbar />
      <main className="flex-grow">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/commute" element={<Commute />} />
          <Route path="/predictor" element={<Predictor />} />
          <Route path="/forecast" element={<Forecast />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
