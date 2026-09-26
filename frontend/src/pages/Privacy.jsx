import React from 'react'
import { ShieldCheck, Mail, AlertCircle, Database, Lock, EyeOff } from 'lucide-react'

export default function Privacy() {
  return (
    <div className="pt-24 pb-20 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto min-h-screen text-slate-200">
      <div className="mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono mb-3 bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          <span>DATA TRANSPARENCY & PRIVACY</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-3">
          Privacy Policy
        </h1>
        <p className="text-sm text-slate-400">
          Effective Date: September 26, 2026 | Last Updated: September 26, 2026
        </p>
      </div>

      {/* Medical / Environmental Disclaimer Banner */}
      <div className="p-4 rounded-xl border border-cyan-500/20 bg-cyan-950/20 mb-8 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 leading-relaxed">
          <span className="font-semibold text-white">Notice on Environmental Estimates:</span> AirRoute Delhi provides modeled environmental particulate exposure calculations for comparative transit planning. These outputs are informational estimates and do not constitute clinical exposure assessments, medical diagnoses, or personal health guarantees.
        </div>
      </div>

      <div className="space-y-8 text-sm leading-relaxed text-slate-300">
        {/* Section 1 */}
        <section className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Database className="w-4 h-4 text-cyan-400" />
            1. Information Collected and Processed
          </h2>
          <p>
            AirRoute Delhi is designed as an open-access commuter decision support system. We do not require an account or registration to evaluate corridor exposure.
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-xs text-slate-400">
            <li>
              <strong className="text-slate-200">Transit Coordinates:</strong> When you submit origin and destination coordinates, they are processed transiently in memory to discretize the geodesic corridor and query nearby monitoring stations. Journey coordinates are not linked to personal identifiers or permanently saved to user databases.
            </li>
            <li>
              <strong className="text-slate-200">Server Logs:</strong> Our application server automatically generates operational logs containing timestamps, HTTP method, endpoint accessed, execution duration in milliseconds, response status code, and an ephemeral request identifier (X-Request-ID).
            </li>
            <li>
              <strong className="text-slate-200">IP Addresses:</strong> Client IP addresses are evaluated transiently in memory via a sliding-window rate limiter (60 requests per minute) to protect backend computing resources against automated abuse. IP records are automatically pruned after 60 seconds and are not sold or shared.
            </li>
          </ul>
        </section>

        {/* Section 2 */}
        <section className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <EyeOff className="w-4 h-4 text-cyan-400" />
            2. Cookies, Local Storage, and Analytics
          </h2>
          <ul className="list-disc pl-5 space-y-1.5 text-xs text-slate-400">
            <li>
              <strong className="text-slate-200">Zero Non-Essential Cookies:</strong> AirRoute Delhi does not use marketing, advertising, cross-site profiling, or tracking cookies.
            </li>
            <li>
              <strong className="text-slate-200">Local Storage:</strong> We use your browser's local storage solely for non-tracking, functional user interface preferences:
              <ul className="list-circle pl-5 mt-1 space-y-1">
                <li><code className="text-cyan-400 font-mono">recent_searches</code>: Stores your recent location queries locally on your device for quick autocomplete.</li>
                <li><code className="text-cyan-400 font-mono">aqi_site_settings</code>: Stores UI preferences such as temperature unit displays and alert thresholds.</li>
                <li><code className="text-cyan-400 font-mono">aqi_logged_in_user</code>: Retains client-side session information if you use optional account login features.</li>
              </ul>
              You can clear these values at any time using your browser settings.
            </li>
            <li>
              <strong className="text-slate-200">Analytics Status:</strong> Analytics are not installed. We do not embed Google Analytics, Meta Pixel, PostHog, or third-party user telemetry scripts.
            </li>
          </ul>
        </section>

        {/* Section 3 */}
        <section className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Lock className="w-4 h-4 text-cyan-400" />
            3. Third-Party Integrations
          </h2>
          <p className="text-xs text-slate-400">
            To generate forward environmental forecasts, our backend interfaces with the following open scientific data providers:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-xs text-slate-400">
            <li>
              <strong className="text-slate-200">Open-Meteo API:</strong> We query live Numerical Weather Prediction (NWP) weather forecasts (temperature, wind, boundary layer height) server-side. No user PII is transmitted to Open-Meteo.
            </li>
            <li>
              <strong className="text-slate-200">XKDR Platform:</strong> Station observational historical benchmarks are cached locally on our backend from publicly available CPCB and DPCC Continuous Ambient Air Quality Monitoring (CAAQM) stations.
            </li>
          </ul>
        </section>

        {/* Section 4 */}
        <section className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            4. Data Retention and Security
          </h2>
          <p className="text-xs text-slate-400">
            We employ HTTPS encryption for all browser-to-server communications, strict parameter boundary validation on all inputs, in-memory abuse throttling, sanitized error handling preventing internal stack exposure, and automated cryptographic SHA-256 verification of all machine learning model artifacts. Transient transit query data is discarded upon request completion.
          </p>
        </section>

        {/* Section 5 */}
        <section className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Mail className="w-4 h-4 text-cyan-400" />
            5. User Rights and Contact Information
          </h2>
          <p className="text-xs text-slate-400">
            If you have questions regarding this Privacy Policy, technical data processing, or wish to inquire about operational telemetry practices, please contact:
          </p>
          <div className="pt-2 font-mono text-xs text-cyan-400">
            Email: <a href="mailto:moominbrather@gmail.com" className="underline hover:text-cyan-300">moominbrather@gmail.com</a>
          </div>
        </section>
      </div>
    </div>
  )
}
