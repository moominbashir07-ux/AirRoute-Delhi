import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './pages/Home'
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
          {/* Prevent accidental judge/public access to legacy experimental routes by redirecting to /commute */}
          <Route path="/predictor" element={<Navigate to="/commute" replace />} />
          <Route path="/forecast" element={<Navigate to="/commute" replace />} />
          <Route path="/analytics" element={<Navigate to="/commute" replace />} />
          <Route path="/settings" element={<Navigate to="/commute" replace />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
