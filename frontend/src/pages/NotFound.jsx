import React from 'react'
import { Link } from 'react-router-dom'
import { Navigation, ArrowLeft, Wind } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="pt-32 pb-24 px-4 sm:px-6 lg:px-8 max-w-2xl mx-auto min-h-[80vh] flex flex-col items-center justify-center text-center text-slate-200">
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center bg-cyan-950/60 border border-cyan-500/30 text-cyan-400 mb-6 shadow-[0_0_25px_rgba(34,211,238,0.15)]">
        <Wind className="w-7 h-7" />
      </div>

      <div className="font-mono text-xs uppercase tracking-widest text-cyan-400 mb-2">
        Error 404 - Page Not Found
      </div>

      <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-4">
        Out of Covered Airspace
      </h1>

      <p className="text-sm text-slate-400 mb-8 max-w-md leading-relaxed">
        The corridor or resource you requested does not exist or has moved. Return to the main portal to analyze Delhi/NCR commute exposure.
      </p>

      <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
        <Link
          to="/commute"
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg text-xs font-semibold uppercase tracking-wider text-slate-950 bg-cyan-400 hover:bg-cyan-300 transition-all shadow-[0_0_20px_rgba(34,211,238,0.2)]"
        >
          <Navigation className="w-4 h-4" />
          <span>Check My Commute</span>
        </Link>
        <Link
          to="/"
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg text-xs font-medium text-slate-300 bg-slate-900 border border-slate-800 hover:bg-slate-800 hover:text-white transition-all"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Home</span>
        </Link>
      </div>
    </div>
  )
}
