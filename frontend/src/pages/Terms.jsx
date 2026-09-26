import React from 'react'
import { FileText, AlertTriangle, ShieldAlert, CheckSquare, Clock, Globe } from 'lucide-react'

export default function Terms() {
  return (
    <div className="pt-24 pb-20 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto min-h-screen text-slate-200">
      <div className="mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono mb-3 bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">
          <FileText className="w-3.5 h-3.5 text-cyan-400" />
          <span>LEGAL AGREEMENT & USE CONDITIONS</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-3">
          Terms & Conditions
        </h1>
        <p className="text-sm text-slate-400">
          Effective Date: September 26, 2026 | Last Updated: September 26, 2026
        </p>
      </div>

      {/* Critical Disclaimer Alert */}
      <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-950/20 mb-8 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs text-amber-200/90 leading-relaxed">
          <span className="font-semibold text-white">Essential Environmental Disclaimer:</span> AirRoute Delhi is an experimental environmental exposure estimation tool. It does not provide medical advice, individual health risk predictions, or guarantees that any departure time or route is safe, healthy, or free of particulate hazards.
        </div>
      </div>

      <div className="space-y-8 text-sm leading-relaxed text-slate-300">
        {/* Section 1 */}
        <section className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <CheckSquare className="w-4 h-4 text-cyan-400" />
            1. Acceptance and Permitted Use
          </h2>
          <p>
            By accessing or using AirRoute Delhi, you agree to these Terms & Conditions. You may use this service solely for personal, non-commercial, informational purposes to review modeled environmental particulate estimates along Delhi/NCR travel corridors.
          </p>
          <p className="text-xs text-slate-400">
            You agree not to: (a) submit automated, scripted, or abusive request volumes designed to bypass rate limits; (b) attempt to decompile, disrupt, or introduce malicious payloads to our API endpoints; (c) portray AirRoute Delhi outputs as official government air quality advisories or certified medical evaluations.
          </p>
        </section>

        {/* Section 2 */}
        <section className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" />
            2. Scientific Methodology and Forecast Constraints
          </h2>
          <p>Users must understand the specific technical boundaries governing all calculations:</p>
          <ul className="list-disc pl-5 space-y-2 text-xs text-slate-400">
            <li>
              <strong className="text-slate-200">Six-Hour Horizon Limit:</strong> Machine learning forecasts are strictly validated up to 6 hours ahead of the analysis time. The platform will reject transit queries requiring forecast lead times exceeding 6.0 hours.
            </li>
            <li>
              <strong className="text-slate-200">Nearest-Station Proxy:</strong> Corridor segments are matched to the nearest official Continuous Ambient Air Quality Monitoring (CAAQM) station within a 10.0 km radius. Ambient background station measurements do not represent micro-scale street-canyon dynamics, vehicular exhaust plumes, or localized construction dust.
            </li>
            <li>
              <strong className="text-slate-200">Geodesic Corridor Geometry:</strong> Travel paths are discretized along mathematical WGS84 geodesic lines and do not account for dynamic traffic congestion, turn-by-turn road topography, or physical detours.
            </li>
            <li>
              <strong className="text-slate-200">Scenario Ventilation Assumptions:</strong> Inhaled particulate mass is calculated using standardized physiological rates (walking: 1.3 m³/h, cycling: 2.1 m³/h, motorized: 0.6 m³/h). These are population scenario constants, not personal biometric measurements.
            </li>
            <li>
              <strong className="text-slate-200">NWP Weather Dependencies:</strong> Forecasting models depend on external Numerical Weather Prediction (NWP) meteorological cycles. Atmospheric prediction uncertainties propagate into PM2.5 forecasts.
            </li>
          </ul>
        </section>

        {/* Section 3 */}
        <section className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Globe className="w-4 h-4 text-cyan-400" />
            3. Third-Party Data Dependencies and Availability
          </h2>
          <p className="text-xs text-slate-400">
            AirRoute Delhi integrates external data provided by third parties, including the Open-Meteo weather API and CAAQM station telemetry aggregated by the XKDR platform. We do not control these services and do not warrant continuous uptime, uninterrupted network availability, or the accuracy of third-party sensor feeds.
          </p>
        </section>

        {/* Section 4 */}
        <section className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-cyan-400" />
            4. Limitation of Liability and "As-Is" Provision
          </h2>
          <p className="text-xs text-slate-400">
            THE SERVICE AND ALL MODEL OUTPUTS ARE PROVIDED ON AN "AS IS" AND "AS AVAILABLE" BASIS WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED. TO THE MAXIMUM EXTENT PERMITTED BY LAW, AIRROUTE DELHI AND ITS OPERATORS DISCLAIM ALL LIABILITY FOR ANY DIRECT, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING OUT OF YOUR USE OF THE SERVICE, RELIANCE ON ENVIRONMENTAL ESTIMATES, TRAVEL DECISIONS, OR HEALTH OUTCOMES.
          </p>
        </section>

        {/* Section 5 */}
        <section className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
          <h2 className="text-base font-semibold text-white">5. Modifications and Contact</h2>
          <p className="text-xs text-slate-400">
            We reserve the right to modify these Terms at any time. Continued use of the platform after updates constitutes acceptance of revised terms. For inquiries regarding these terms, contact:
          </p>
          <div className="font-mono text-xs text-cyan-400 pt-1">
            Email: <a href="mailto:moominbrather@gmail.com" className="underline hover:text-cyan-300">moominbrather@gmail.com</a>
          </div>
        </section>
      </div>
    </div>
  )
}
