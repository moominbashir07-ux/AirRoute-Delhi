import React from 'react'
import { Link } from 'react-router-dom'
import { Wind, Activity, TrendingUp, BarChart3, ArrowRight, Cpu, Database, Shield } from 'lucide-react'
import { AQI_CATEGORIES } from '../utils/aqi'
import { SparklesCore } from '../components/ui/sparkles'
import { LiquidButton } from '../components/ui/liquid-glass-button'
import { ContainerScroll } from '../components/ui/container-scroll-animation'

const FEATURES = [
  {
    icon: Cpu,
    title: 'ML-Powered Predictions',
    desc: 'Random Forest, Decision Tree & Linear Regression models compete — the best model wins automatically.',
  },
  {
    icon: TrendingUp,
    title: '7-Day Forecast',
    desc: 'Predict AQI trends up to a week ahead using time-series environmental data.',
  },
  {
    icon: BarChart3,
    title: 'Rich Analytics',
    desc: 'Feature importance, prediction vs actual charts, and pollution trend visualizations.',
  },
  {
    icon: Database,
    title: 'Historical Data',
    desc: 'Track historical AQI patterns with interactive timeline charts.',
  },
  {
    icon: Shield,
    title: 'Health Guidance',
    desc: 'Actionable health recommendations based on WHO and EPA AQI standards.',
  },
  {
    icon: Activity,
    title: 'Real-Time Input',
    desc: 'Enter live sensor readings and get instant AQI predictions.',
  },
]

const STATS = [
  { value: '3', label: 'ML Models' },
  { value: '8', label: 'Parameters' },
  { value: '7', label: 'Day Forecast' },
  { value: '6', label: 'AQI Categories' },
]

export default function Home() {
  return (
    <div className="min-h-screen pt-16 relative overflow-hidden bg-black text-white">
      {/* 3D Sparkles Background */}
      <div className="w-full absolute inset-0 h-full -z-10 pointer-events-none">
        <SparklesCore
          id="tsparticlesfullpage"
          background="transparent"
          minSize={0.6}
          maxSize={1.4}
          particleDensity={80}
          className="w-full h-full"
          particleColor="#FFFFFF"
          speed={0.8}
        />
      </div>

      {/* Hero Container */}
      <section className="relative flex min-h-[90vh] items-center justify-center px-6 pt-12 pb-16">
        <div className="relative border border-[#27272a] p-2 w-full mx-auto max-w-4xl backdrop-blur-md bg-black/40 rounded-3xl glow-border">
          <main className="relative border border-[#27272a] py-16 px-6 overflow-hidden rounded-2xl bg-black/75 text-center">
            <div className="my-2 inline-flex items-center justify-center gap-2 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20 mb-8">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-500 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500"></span>
              </span>
              <p className="text-[10px] uppercase tracking-wider text-green-400 font-mono">API Live & Ready</p>
            </div>

            <h1 className="font-display text-4xl md:text-7xl font-extrabold text-white leading-tight mb-6 tracking-tighter">
              Forecasting is<br />
              <span className="bg-clip-text text-transparent bg-gradient-to-b from-neutral-50 to-neutral-400">
                Everything
              </span>
            </h1>

            <p className="text-sm md:text-base text-neutral-400 max-w-xl mx-auto mb-10 leading-relaxed">
              Machine learning models evaluate 8 key environmental parameters to estimate Air Quality Index
              and deliver preventive environmental health guidance.
            </p>

            <div className="flex flex-wrap gap-4 justify-center">
              <Link to="/predictor">
                <LiquidButton className="text-white border border-[#27272a] rounded-full hover:scale-105 transition duration-300" size="xl">
                  Let's Predict
                </LiquidButton>
              </Link>
              <Link to="/forecast">
                <LiquidButton className="text-white border border-[#27272a] rounded-full hover:scale-105 transition duration-300" size="xl">
                  View Forecast
                </LiquidButton>
              </Link>
            </div>
          </main>
        </div>
      </section>

      {/* 3D Perspective Card Scroll Section */}
      <section className="relative px-6">
        <ContainerScroll
          titleComponent={
            <div className="max-w-3xl mx-auto">
              <h2 className="text-3xl md:text-6xl font-bold text-white tracking-tight leading-none mb-4">
                Explore Premium<br />
                <span className="bg-clip-text text-transparent bg-gradient-to-b from-cyan-400 to-cyan-600 font-display">
                  AQI Analytics
                </span>
              </h2>
              <p className="text-neutral-400 text-sm md:text-base max-w-lg mx-auto mt-4">
                Interactive forecasting, detailed model comparison charts, and real-time parameter tracking components.
              </p>
            </div>
          }
        >
          {/* Authentic AQI Dashboard Preview Card (replacing foreign Linear template mockup) */}
          <div className="w-full h-full rounded-2xl bg-[#0d1529] border border-cyan-400/20 p-6 flex flex-col justify-between overflow-hidden shadow-2xl">
            {/* Top Bar */}
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block" />
                <span className="w-3 h-3 rounded-full bg-yellow-500/80 inline-block" />
                <span className="w-3 h-3 rounded-full bg-green-500/80 inline-block" />
                <span className="ml-3 text-xs font-mono text-slate-400">AQI Predictor — Live Environmental Telemetry</span>
              </div>
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-cyan-400/10 text-cyan-400 border border-cyan-400/20">
                Baseline Model Active
              </span>
            </div>

            {/* Dashboard Content Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 my-6">
              <div className="rounded-xl p-4 bg-[#131e38] border border-cyan-400/15 text-center flex flex-col items-center justify-center">
                <span className="text-xs text-slate-400 uppercase tracking-widest font-mono">Current Index</span>
                <span className="text-5xl font-display font-bold text-yellow-400 my-2">87</span>
                <span className="text-xs font-semibold px-3 py-1 rounded-full bg-yellow-400/10 text-yellow-300 border border-yellow-400/30">
                  Moderate
                </span>
              </div>

              <div className="rounded-xl p-4 bg-[#131e38] border border-cyan-400/15 col-span-2 flex flex-col justify-center">
                <span className="text-xs text-slate-400 uppercase tracking-widest font-mono mb-3">Key Pollutants</span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-black/30 p-2.5 rounded-lg border border-white/5">
                    <span className="text-[10px] text-slate-400 block font-mono">PM2.5</span>
                    <span className="text-lg font-bold text-white font-mono">29.4 <span className="text-[10px] text-slate-500">µg/m³</span></span>
                  </div>
                  <div className="bg-black/30 p-2.5 rounded-lg border border-white/5">
                    <span className="text-[10px] text-slate-400 block font-mono">PM10</span>
                    <span className="text-lg font-bold text-white font-mono">58.1 <span className="text-[10px] text-slate-500">µg/m³</span></span>
                  </div>
                  <div className="bg-black/30 p-2.5 rounded-lg border border-white/5">
                    <span className="text-[10px] text-slate-400 block font-mono">NO₂</span>
                    <span className="text-lg font-bold text-white font-mono">22.0 <span className="text-[10px] text-slate-500">µg/m³</span></span>
                  </div>
                  <div className="bg-black/30 p-2.5 rounded-lg border border-white/5">
                    <span className="text-[10px] text-slate-400 block font-mono">Wind</span>
                    <span className="text-lg font-bold text-white font-mono">12.5 <span className="text-[10px] text-slate-500">km/h</span></span>
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Health Bar */}
            <div className="bg-[#131e38]/70 border border-white/5 rounded-xl p-3 flex items-center justify-between text-xs text-slate-300">
              <span className="flex items-center gap-2">
                <span>🛡️</span>
                <span>Acceptable air quality for most individuals. Unusually sensitive groups should monitor prolonged exertion.</span>
              </span>
              <span className="text-slate-500 font-mono hidden sm:inline">WHO / EPA Standards</span>
            </div>
          </div>
        </ContainerScroll>
      </section>

      {/* Stats */}
      <section className="px-6 py-16 relative z-10">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-4">
          {STATS.map((s) => (
            <div key={s.label} className="text-center border border-[#27272a] rounded-2xl py-8 backdrop-blur-md bg-black/60" style={{ boxShadow: '0 4px 30px rgba(0,0,0,0.4)' }}>
              <div className="font-display text-4xl font-bold text-cyan-400">{s.value}</div>
              <div className="text-xs text-slate-400 mt-2 font-mono uppercase tracking-wider">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* AQI Scale */}
      <section className="px-6 py-16 relative z-10">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-display text-3xl font-bold text-white mb-2 text-center tracking-tight">AQI Scale Reference</h2>
          <p className="text-slate-400 text-center mb-10 text-xs uppercase tracking-wider font-mono">EPA standard ranges for health advisory categories</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {AQI_CATEGORIES.map((cat, i) => (
              <div key={i} className="rounded-2xl p-5 border backdrop-blur-md transition-all duration-300 hover:scale-[1.02]" style={{ background: cat.bg, borderColor: `${cat.color}25` }}>
                <div className="flex items-center justify-between mb-3">
                  <div className="w-3.5 h-3.5 rounded-full" style={{ background: cat.color, boxShadow: `0 0 10px ${cat.color}` }} />
                  <span className="font-mono text-xs font-semibold" style={{ color: cat.color }}>
                    {i === 0 ? '0–50' : i === 1 ? '51–100' : i === 2 ? '101–150' : i === 3 ? '151–200' : i === 4 ? '201–300' : '301+'}
                  </span>
                </div>
                <p className="text-base font-bold text-white">{cat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-16 relative z-10">
        <div className="max-w-5xl mx-auto">
          <h2 className="font-display text-3xl font-bold text-white mb-2 text-center tracking-tight">System Capabilities</h2>
          <p className="text-slate-400 text-center mb-12 text-xs uppercase tracking-wider font-mono">End-to-end ML pipeline from data ingestion to health advisories</p>
          <div className="grid md:grid-cols-3 gap-6">
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="border border-[#27272a] rounded-2xl p-6 backdrop-blur-md bg-black/60 transition-all duration-300 hover:translate-y-[-2px] hover:border-cyan-500/20">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-5"
                  style={{ background: 'rgba(34,211,238,0.06)', border: '1px solid rgba(34,211,238,0.15)' }}>
                  <Icon size={18} className="text-cyan-400" />
                </div>
                <h3 className="font-display font-bold text-lg text-white mb-2">{title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-24 text-center relative z-10">
        <div className="max-w-2xl mx-auto border border-[#27272a] rounded-3xl p-12 backdrop-blur-md bg-black/70">
          <Wind size={44} className="text-cyan-400 mx-auto mb-6 animate-pulse" />
          <h2 className="font-display text-3xl font-bold text-white mb-3 tracking-tight">Ready to Predict?</h2>
          <p className="text-slate-400 text-sm mb-8 max-w-md mx-auto">Enter live local environmental parameters and obtain instantaneous air quality predictions.</p>
          <Link to="/predictor">
            <LiquidButton className="text-white border border-[#27272a] rounded-full hover:scale-105 transition duration-300" size="xl">
              Open Predictor
            </LiquidButton>
          </Link>
        </div>
      </section>
    </div>
  )
}
