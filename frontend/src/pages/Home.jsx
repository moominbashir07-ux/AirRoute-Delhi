import React, { useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Navigation, ArrowRight, ShieldCheck, MapPin, Gauge, Wind, Clock, Activity, BarChart2 } from 'lucide-react'

export default function Home() {
  const { hash } = useLocation()

  useEffect(() => {
    if (hash) {
      const element = document.querySelector(hash)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' })
      }
    }
  }, [hash])

  return (
    <div className="min-h-screen pt-20 pb-20 bg-slate-950 text-slate-100">
      {/* Hero Section */}
      <section className="relative px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto pt-12 pb-20">
        <div className="max-w-4xl mx-auto text-center space-y-6">
          {/* Status Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-mono bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span>DELHI/NCR OPERATIONAL CORRIDOR ENGINE</span>
          </div>

          {/* Primary Launch Headline */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-bold tracking-tight text-white leading-tight">
            Plan your commute around forecasted PM2.5 exposure.
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
            AirRoute Delhi evaluates time-dependent particulate matter across Delhi/NCR transit corridors using continuous monitoring observations, multi-horizon PM2.5 forecasting, and deterministic inhalation exposure modeling.
          </p>

          {/* Single Prominent Primary CTA */}
          <div className="pt-4 flex justify-center">
            <Link
              to="/commute"
              className="inline-flex items-center gap-2.5 px-8 py-3.5 rounded-lg text-sm font-semibold uppercase tracking-wider text-slate-950 bg-cyan-400 hover:bg-cyan-300 transition-all shadow-[0_0_25px_rgba(34,211,238,0.25)]"
            >
              <Navigation className="w-4 h-4" />
              <span>Check My Commute</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Link>
          </div>
          <p className="text-[11px] font-mono text-slate-500">
            No registration required. Evaluates walking, cycling, and motorized transit up to 6 hours ahead.
          </p>
        </div>
      </section>

      {/* Corridor Benchmark Snapshot */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto mb-20">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 sm:p-8 backdrop-blur-xl">
          <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800/80 gap-4">
            <div>
              <div className="text-xs font-mono text-cyan-400 uppercase tracking-wider mb-1">
                Representative Corridor Trace
              </div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <span>Connaught Place to Cyber City, Gurugram</span>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  28.4 km Geodesic
                </span>
              </h2>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Modeled Lead Times: t+1h to t+6h
            </div>
          </div>

          {/* Environmental Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-6">
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">CAAQM Stations</div>
              <div className="text-2xl font-bold font-mono text-white mt-1">42</div>
              <div className="text-[11px] text-slate-500 mt-1">CPCB / DPCC monitoring network</div>
            </div>
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Forecast Horizon</div>
              <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">6 Hours</div>
              <div className="text-[11px] text-slate-500 mt-1">Direct multi-horizon models</div>
            </div>
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Ventilation Rates</div>
              <div className="text-2xl font-bold font-mono text-white mt-1">3 Modes</div>
              <div className="text-[11px] text-slate-500 mt-1">Walking, Cycling, Motorized</div>
            </div>
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Coverage Gate</div>
              <div className="text-2xl font-bold font-mono text-white mt-1">80% Min</div>
              <div className="text-[11px] text-slate-500 mt-1">Strict station coverage filter</div>
            </div>
          </div>
        </div>
      </section>

      {/* Methodology Overview */}
      <section id="methodology" className="scroll-mt-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto mb-20">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="text-xs font-mono text-cyan-400 uppercase tracking-wider mb-2">Scientific Methodology</div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white">How Corridor Exposure is Modeled</h2>
          <p className="text-sm text-slate-400 mt-2">
            Deterministic physical exposure calculation connected to multi-horizon statistical machine learning.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-cyan-950/60 border border-cyan-500/20 text-cyan-400 font-mono font-bold text-sm">
              01
            </div>
            <h3 className="text-base font-semibold text-white">Geodesic Discretization</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Your commute corridor is sliced into 1.0 km equidistant segments along WGS84 geodesic arcs. Each segment is mapped to the nearest operational Continuous Ambient Air Quality Monitoring (CAAQM) station within 10 km.
            </p>
          </div>

          <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-cyan-950/60 border border-cyan-500/20 text-cyan-400 font-mono font-bold text-sm">
              02
            </div>
            <h3 className="text-base font-semibold text-white">Station-Conditioned Forecasting</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Direct multi-horizon HistGradientBoostingRegressor models forecast PM2.5 concentrations for lead times h = 1 to 6 hours ahead using historical lags, causal rolling averages, and future NWP weather features.
            </p>
          </div>

          <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-cyan-950/60 border border-cyan-500/20 text-cyan-400 font-mono font-bold text-sm">
              03
            </div>
            <h3 className="text-base font-semibold text-white">Inhaled Dose Optimization</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Inhaled particulate mass is calculated per segment as M = C * V_E * delta_t. Departure candidates across your chosen window are ranked to identify the departure with the lowest modeled inhaled particulate mass.
            </p>
          </div>
        </div>
      </section>

      {/* Scenario Ventilation Rates Section */}
      <section id="rates" className="scroll-mt-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto mb-20">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 sm:p-8">
          <div className="max-w-2xl mb-6">
            <div className="text-xs font-mono text-cyan-400 uppercase tracking-wider mb-1">Physiological Assumptions</div>
            <h2 className="text-xl font-bold text-white">Standardized Scenario Ventilation Rates</h2>
            <p className="text-xs text-slate-400 mt-1">
              Exposure calculations use standard scenario physiological constants rather than clinical individual measurements:
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-white">Walking</span>
                <span className="text-xs font-mono text-cyan-400">1.3 m³/h</span>
              </div>
              <div className="text-xs text-slate-400">Assumed transit speed: 5 km/h</div>
              <div className="text-[11px] text-slate-500 mt-1">Moderate walking exertion rate</div>
            </div>

            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-white">Cycling</span>
                <span className="text-xs font-mono text-cyan-400">2.1 m³/h</span>
              </div>
              <div className="text-xs text-slate-400">Assumed transit speed: 15 km/h</div>
              <div className="text-[11px] text-slate-500 mt-1">Elevated physical respiration rate</div>
            </div>

            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-white">Motorized</span>
                <span className="text-xs font-mono text-cyan-400">0.6 m³/h</span>
              </div>
              <div className="text-xs text-slate-400">Assumed transit speed: 30 km/h</div>
              <div className="text-[11px] text-slate-500 mt-1">Seated vehicle cabin respiration rate</div>
            </div>
          </div>
        </div>
      </section>

      {/* Bottom CTA Block with Single Primary Action */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto text-center">
        <div className="p-10 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl space-y-5">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center bg-cyan-950/60 border border-cyan-500/30 text-cyan-400 mx-auto">
            <Wind className="w-6 h-6" />
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Ready to plan your Delhi commute?
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 max-w-lg mx-auto leading-relaxed">
            Select your corridor endpoints, choose walking, cycling, or motorized transit, and evaluate candidate departure times to identify your lowest modeled exposure.
          </p>
          <div className="pt-2">
            <Link
              to="/commute"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-lg text-xs font-semibold uppercase tracking-wider text-slate-950 bg-cyan-400 hover:bg-cyan-300 transition-all shadow-[0_0_20px_rgba(34,211,238,0.2)]"
            >
              <Navigation className="w-4 h-4" />
              <span>Check My Commute</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
