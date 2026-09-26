import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Navigation, 
  MapPin, 
  Clock, 
  Bike, 
  Footprints, 
  Car, 
  ArrowRight, 
  AlertTriangle, 
  CheckCircle, 
  Info, 
  ShieldAlert, 
  ChevronRight,
  TrendingDown,
  Gauge
} from 'lucide-react'
import { optimizeCommute } from '../utils/api'

// Preset popular commuter corridors across Delhi NCR
const CORRIDOR_PRESETS = [
  {
    name: 'Connaught Place → Cyber City, Gurugram',
    origin: { name: 'Connaught Place', lat: 28.6315, lon: 77.2167 },
    destination: { name: 'Cyber City, Gurugram', lat: 28.4950, lon: 77.0895 },
    defaultMode: 'motorized'
  },
  {
    name: 'Noida Sec 62 → AIIMS / South Ext',
    origin: { name: 'Noida Sector 62', lat: 28.6271, lon: 77.3619 },
    destination: { name: 'AIIMS / South Extension', lat: 28.5672, lon: 77.2100 },
    defaultMode: 'cycling'
  },
  {
    name: 'Anand Vihar ISBT → Dwarka Sec 21',
    origin: { name: 'Anand Vihar ISBT', lat: 28.6469, lon: 77.3160 },
    destination: { name: 'Dwarka Sector 21', lat: 28.5523, lon: 77.0583 },
    defaultMode: 'motorized'
  },
  {
    name: 'Rohini Sec 16 → Nehru Place',
    origin: { name: 'Rohini Sector 16', lat: 28.7325, lon: 77.1189 },
    destination: { name: 'Nehru Place', lat: 28.5492, lon: 77.2533 },
    defaultMode: 'motorized'
  }
]

const MODES = [
  { id: 'cycling', label: 'Cycling', speed: '15 km/h', ventilation: '2.1 m³/h', icon: Bike },
  { id: 'walking', label: 'Walking', speed: '5 km/h', ventilation: '1.3 m³/h', icon: Footprints },
  { id: 'motorized', label: 'Motorized', speed: '30 km/h', ventilation: '0.6 m³/h', icon: Car },
]

export default function Commute() {
  const [originLat, setOriginLat] = useState('28.6315')
  const [originLon, setOriginLon] = useState('77.2167')
  const [destLat, setDestLat] = useState('28.5672')
  const [destLon, setDestLon] = useState('77.2100')
  const [mode, setMode] = useState('cycling')
  const [intervalMins, setIntervalMins] = useState(15)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [activeTab, setActiveTab] = useState('summary')

  const handleApplyPreset = (preset) => {
    setOriginLat(preset.origin.lat.toString())
    setOriginLon(preset.origin.lon.toString())
    setDestLat(preset.destination.lat.toString())
    setDestLon(preset.destination.lon.toString())
    setMode(preset.defaultMode)
    setError(null)
  }

  const handleAnalyze = async () => {
    setLoading(true)
    setError(null)

    // Compute departure window: start in 15 mins, window span 1.5 hours
    const now = new Date()
    const startTime = new Date(now.getTime() + 15 * 60000)
    const endTime = new Date(startTime.getTime() + 90 * 60000)

    const payload = {
      origin: {
        latitude: parseFloat(originLat),
        longitude: parseFloat(originLon)
      },
      destination: {
        latitude: parseFloat(destLat),
        longitude: parseFloat(destLon)
      },
      mode: mode,
      departure_window: {
        start: startTime.toISOString(),
        end: endTime.toISOString(),
        interval_minutes: parseInt(intervalMins)
      }
    }

    try {
      const res = await optimizeCommute(payload)
      setResult(res)
    } catch (err) {
      setError(err.message || 'Failed to optimize commute exposure.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="pt-24 pb-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto min-h-screen text-slate-100">
      {/* Header */}
      <div className="mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono mb-3 bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">
          <Navigation className="w-3.5 h-3.5 text-cyan-400" />
          <span>PRODUCTION COMMUTE ENGINE</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white flex items-center gap-3">
          Commuter Environmental Exposure Advisor
        </h1>
        <p className="text-slate-400 mt-2 max-w-3xl text-sm sm:text-base">
          Evaluate time-dependent particulate exposure along Delhi/NCR transit corridors. Matches your route with 
          audited CAAQM continuous monitoring stations and Phase 3D multi-horizon PM2.5 forecasting to identify 
          the departure window with lowest modeled inhaled particulate mass.
        </p>
      </div>

      {/* Preset Quick Selectors */}
      <div className="mb-6">
        <div className="text-xs font-mono text-slate-400 mb-2 uppercase tracking-wider">Benchmark Delhi/NCR Corridors</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          {CORRIDOR_PRESETS.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handleApplyPreset(p)}
              className="text-left px-3.5 py-2.5 rounded-lg border border-slate-800 bg-slate-900/40 hover:bg-slate-800/60 hover:border-cyan-500/30 transition-all text-xs"
            >
              <div className="font-semibold text-slate-200 truncate">{p.name}</div>
              <div className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-1">
                <span>{p.origin.name}</span>
                <ArrowRight className="w-3 h-3 text-cyan-400 inline" />
                <span>{p.destination.name}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Control Panel Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Origin & Destination */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-xl space-y-4">
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-cyan-400" />
            <span>Geographic Coordinates (WGS84)</span>
          </h2>

          <div className="space-y-3">
            <div>
              <label htmlFor="origin-lat" className="text-xs font-mono text-slate-400 block mb-1">Origin Latitude / Longitude</label>
              <div className="grid grid-cols-2 gap-2">
                <input
                  id="origin-lat"
                  name="origin-lat"
                  aria-label="Origin Latitude"
                  type="number"
                  step="0.0001"
                  value={originLat}
                  onChange={(e) => setOriginLat(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-slate-950/70 border border-slate-700 text-xs font-mono text-white focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-cyan-500"
                  placeholder="28.6315"
                />
                <input
                  id="origin-lon"
                  name="origin-lon"
                  aria-label="Origin Longitude"
                  type="number"
                  step="0.0001"
                  value={originLon}
                  onChange={(e) => setOriginLon(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-slate-950/70 border border-slate-700 text-xs font-mono text-white focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-cyan-500"
                  placeholder="77.2167"
                />
              </div>
            </div>

            <div>
              <label htmlFor="dest-lat" className="text-xs font-mono text-slate-400 block mb-1">Destination Latitude / Longitude</label>
              <div className="grid grid-cols-2 gap-2">
                <input
                  id="dest-lat"
                  name="dest-lat"
                  aria-label="Destination Latitude"
                  type="number"
                  step="0.0001"
                  value={destLat}
                  onChange={(e) => setDestLat(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-slate-950/70 border border-slate-700 text-xs font-mono text-white focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-cyan-500"
                  placeholder="28.5672"
                />
                <input
                  id="dest-lon"
                  name="dest-lon"
                  aria-label="Destination Longitude"
                  type="number"
                  step="0.0001"
                  value={destLon}
                  onChange={(e) => setDestLon(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-slate-950/70 border border-slate-700 text-xs font-mono text-white focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-cyan-500"
                  placeholder="77.2100"
                />
              </div>
            </div>
            <div className="text-[11px] text-slate-500 font-mono">
              * Bound: Delhi NCR [28.20 to 28.95 N, 76.80 to 77.55 E]
            </div>
          </div>
        </div>

        {/* Transit Mode Selection */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-xl space-y-4">
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Gauge className="w-4 h-4 text-cyan-400" />
            <span>Transit Mode & Ventilation Scenario</span>
          </h2>

          <div className="grid grid-cols-1 gap-2.5">
            {MODES.map((m) => {
              const Icon = m.icon
              const isSelected = mode === m.id
              return (
                <button
                  key={m.id}
                  onClick={() => setMode(m.id)}
                  className={`flex items-center justify-between p-3 rounded-xl border text-left transition-all ${
                    isSelected
                      ? 'border-cyan-500 bg-cyan-950/40 text-white shadow-[0_0_15px_rgba(34,211,238,0.15)]'
                      : 'border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${isSelected ? 'bg-cyan-500/20 text-cyan-400' : 'bg-slate-800 text-slate-400'}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-semibold">{m.label}</div>
                      <div className="text-[11px] text-slate-400">Speed: {m.speed}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[11px] font-mono text-cyan-400">{m.ventilation}</div>
                    <div className="text-[10px] text-slate-400">ventilation rate</div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Departure Window & Action */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-xl flex flex-col justify-between space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2 mb-3">
              <Clock className="w-4 h-4 text-cyan-400" />
              <span>Departure Analysis Window</span>
            </h2>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-mono text-slate-400 block mb-1">Departure Candidates Window</label>
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 text-xs text-slate-300">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-slate-400">Horizon Span:</span>
                    <span className="font-mono text-cyan-400">Next 90 Minutes</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Interval:</span>
                    <select
                      value={intervalMins}
                      onChange={(e) => setIntervalMins(e.target.value)}
                      className="bg-slate-900 border border-slate-700 rounded px-2 py-0.5 text-xs text-white focus:outline-none"
                    >
                      <option value="15">Every 15 mins</option>
                      <option value="30">Every 30 mins</option>
                    </select>
                  </div>
                </div>
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                * Validated lead-time constraint: Max 6.0 hours from prediction time
              </div>
            </div>
          </div>

          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl font-semibold text-xs tracking-wider uppercase transition-all duration-300 flex items-center justify-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold shadow-[0_0_20px_rgba(34,211,238,0.2)] disabled:opacity-50"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                <span>Computing Multi-Horizon Exposure...</span>
              </>
            ) : (
              <>
                <Navigation className="w-4 h-4" />
                <span>Analyze Commute Exposure</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 p-4 rounded-xl bg-red-950/40 border border-red-500/30 flex items-start gap-3 text-red-200 text-xs"
        >
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-red-400 mb-0.5">Optimization Request Error</div>
            <div>{error}</div>
          </div>
        </motion.div>
      )}

      {/* Results Section */}
      {result && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Recommendation Hero Banner */}
          {result.recommended_departure && (
            <div className="p-6 rounded-2xl border border-cyan-500/40 bg-gradient-to-br from-cyan-950/40 via-slate-900/60 to-slate-950/80 backdrop-blur-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
                <div>
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 mb-2">
                    <CheckCircle className="w-3.5 h-3.5" />
                    <span>RECOMMENDED DEPARTURE WINDOW</span>
                  </div>
                  <h3 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                    Depart at {result.recommended_departure.departure_time_ist.slice(11, 16)} IST
                  </h3>
                  <p className="text-slate-300 text-xs sm:text-sm mt-1 max-w-2xl leading-relaxed">
                    {result.recommended_departure.recommendation_statement}
                  </p>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                    <div className="text-[11px] text-slate-400 uppercase font-mono">Inhaled PM2.5</div>
                    <div className="text-lg font-bold text-cyan-400 mt-0.5">
                      {result.recommended_departure.estimated_inhaled_pm25_ug} <span className="text-xs font-normal text-slate-400">µg</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                    <div className="text-[11px] text-slate-400 uppercase font-mono">Avg Exposure</div>
                    <div className="text-lg font-bold text-cyan-400 mt-0.5">
                      {result.recommended_departure.time_weighted_pm25_ug_m3} <span className="text-xs font-normal text-slate-400">µg/m³</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                    <div className="text-[11px] text-slate-400 uppercase font-mono">Duration</div>
                    <div className="text-lg font-bold text-white mt-0.5">
                      {result.recommended_departure.journey_duration_minutes} <span className="text-xs font-normal text-slate-400">min</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                    <div className="text-[11px] text-slate-400 uppercase font-mono">Reduction</div>
                    <div className="text-lg font-bold text-emerald-400 mt-0.5 flex items-center justify-center gap-1">
                      <TrendingDown className="w-4 h-4 inline" />
                      <span>{result.recommended_departure.modeled_exposure_reduction_percent}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Navigation Tabs */}
          <div className="flex border-b border-slate-800 text-xs font-mono">
            <button
              onClick={() => setActiveTab('summary')}
              className={`pb-3 px-4 font-semibold transition-all ${
                activeTab === 'summary'
                  ? 'text-cyan-400 border-b-2 border-cyan-400'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Departure Comparison ({result.departure_candidates?.length || 0})
            </button>
            <button
              onClick={() => setActiveTab('segments')}
              className={`pb-3 px-4 font-semibold transition-all ${
                activeTab === 'segments'
                  ? 'text-cyan-400 border-b-2 border-cyan-400'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Corridor Segment Trace ({result.segment_breakdown?.length || 0})
            </button>
          </div>

          {/* Tab 1: Departure Comparison */}
          {activeTab === 'summary' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {result.departure_candidates?.map((cand, idx) => (
                <div
                  key={idx}
                  className={`p-4 rounded-xl border transition-all ${
                    cand.is_recommended
                      ? 'border-cyan-500 bg-cyan-950/20 shadow-[0_0_15px_rgba(34,211,238,0.1)]'
                      : 'border-slate-800 bg-slate-900/30'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-slate-400">
                      {cand.departure_time_ist.slice(11, 16)} IST
                    </span>
                    {cand.is_recommended && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40">
                        OPTIMAL
                      </span>
                    )}
                  </div>
                  <div className="text-xl font-bold text-white">
                    {cand.estimated_inhaled_pm25_ug} <span className="text-xs font-normal text-slate-400">µg PM2.5</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1 flex items-center justify-between">
                    <span>Mean Conc:</span>
                    <span className="font-mono text-slate-300">{cand.time_weighted_pm25_ug_m3} µg/m³</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5 flex items-center justify-between">
                    <span>Coverage:</span>
                    <span className="font-mono text-emerald-400">{cand.coverage_percent}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Tab 2: Segment Breakdown */}
          {activeTab === 'segments' && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/80 text-slate-400 font-mono uppercase text-[11px] border-b border-slate-800">
                    <tr>
                      <th className="p-3">Seg</th>
                      <th className="p-3">Length</th>
                      <th className="p-3">Transit Time</th>
                      <th className="p-3">Governing Monitor</th>
                      <th className="p-3">Station Dist</th>
                      <th className="p-3">Forecast Lead</th>
                      <th className="p-3">Modeled PM2.5</th>
                      <th className="p-3">Inhaled Dose</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {result.segment_breakdown?.map((seg) => (
                      <tr key={seg.segment_index} className="hover:bg-slate-800/30 transition-colors">
                        <td className="p-3 text-cyan-400">#{seg.segment_index}</td>
                        <td className="p-3">{seg.length_km} km</td>
                        <td className="p-3 text-slate-300">{seg.travel_time_minutes} min</td>
                        <td className="p-3 text-slate-200 font-sans font-medium">
                          {seg.station_name || seg.mapped_station_id}
                        </td>
                        <td className="p-3 text-slate-400">{seg.station_distance_km?.toFixed(2)} km</td>
                        <td className="p-3 text-slate-300">t + {seg.forecast_horizon_h}h</td>
                        <td className="p-3 font-semibold text-white">{seg.forecasted_pm25_ug_m3} µg/m³</td>
                        <td className="p-3 text-cyan-300 font-bold">{seg.segment_inhaled_dose_ug} µg</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Scientific Limitations & Disclaimers Banner */}
          <div className="p-5 rounded-2xl border border-slate-800 bg-slate-950/60 text-xs space-y-3">
            <div className="flex items-center gap-2 text-slate-300 font-semibold uppercase tracking-wider text-[11px] font-mono">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <span>Scientific Methodology & Operational Limitations</span>
            </div>
            <ul className="space-y-1.5 text-slate-400 list-disc list-inside leading-relaxed text-[11px]">
              {result.limitations?.map((lim, i) => (
                <li key={i}>{lim}</li>
              ))}
            </ul>
            <div className="pt-2 border-t border-slate-800/60 text-[11px] text-slate-500 italic">
              {result.scientific_disclaimer}
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}
