import React from 'react'
import { Link } from 'react-router-dom'
import { Wind, ArrowRight } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="border-t border-slate-800/80 bg-slate-950 text-slate-400 text-sm">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
          {/* Brand Column */}
          <div className="md:col-span-2 space-y-4">
            <Link to="/" className="flex items-center gap-2.5 text-white font-bold text-lg tracking-tight">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">
                <Wind size={15} />
              </div>
              <span>AirRoute <span className="text-cyan-400">Delhi</span></span>
            </Link>
            <p className="text-xs text-slate-400 max-w-sm leading-relaxed">
              Plan your commute around forecasted PM2.5 exposure. Evaluates Delhi/NCR transit corridors using continuous monitoring observations, multi-horizon forecasting, and deterministic inhalation exposure modeling.
            </p>
            <div className="pt-1">
              <Link
                to="/commute"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 transition-all"
              >
                <span>Check My Commute</span>
                <ArrowRight size={13} />
              </Link>
            </div>
          </div>

          {/* Core Tools */}
          <div className="space-y-3">
            <div className="text-xs font-mono uppercase tracking-wider text-slate-200">System</div>
            <ul className="space-y-2 text-xs">
              <li>
                <Link to="/commute" className="hover:text-cyan-400 transition-colors">
                  Commute Exposure Advisor
                </Link>
              </li>
              <li>
                <a href="/#methodology" className="hover:text-cyan-400 transition-colors">
                  Scientific Methodology
                </a>
              </li>
              <li>
                <a href="/#rates" className="hover:text-cyan-400 transition-colors">
                  Physiological Assumptions
                </a>
              </li>
            </ul>
          </div>

          {/* Governance & Contact */}
          <div className="space-y-3">
            <div className="text-xs font-mono uppercase tracking-wider text-slate-200">Legal & Transparency</div>
            <ul className="space-y-2 text-xs">
              <li>
                <Link to="/privacy" className="hover:text-cyan-400 transition-colors">
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link to="/terms" className="hover:text-cyan-400 transition-colors">
                  Terms & Conditions
                </Link>
              </li>
              <li className="pt-2 text-slate-500">
                Contact: <a href="mailto:moominbrather@gmail.com" className="text-slate-400 hover:text-cyan-400 transition-colors">moominbrather@gmail.com</a>
              </li>
            </ul>
          </div>
        </div>

        {/* Environmental Limitation Notice */}
        <div className="pt-8 border-t border-slate-900 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-[11px] text-slate-500">
          <p className="max-w-2xl leading-normal">
            Environmental estimates are informational and are not medical advice or a guarantee of route safety. Predictions rely on ambient monitoring stations and numerical weather forecasts.
          </p>
          <p className="font-mono whitespace-nowrap">
            AirRoute Delhi &copy; 2026
          </p>
        </div>
      </div>
    </footer>
  )
}
