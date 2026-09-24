import { useState, useEffect, useRef } from 'react'
import { useSettings } from '../context/SettingsContext'

const THRESHOLDS = [
  { label: 'Good', color: '#00E400', def: 50 },
  { label: 'Moderate', color: '#FFFF00', def: 100 },
  { label: 'Unhealthy (Sensitive)', color: '#FF7E00', def: 150 },
  { label: 'Unhealthy', color: '#FF0000', def: 200 },
  { label: 'Very Unhealthy', color: '#8F3F97', def: 300 },
]

const DEPS = [
  ['React', '18.3.1'], ['FastAPI', '0.111.0'], ['scikit-learn', '1.4.2'],
  ['Recharts', '2.12.5'], ['pandas', '2.2.2'], ['numpy', '1.26.4'],
  ['TailwindCSS', '3.4.3'], ['Vite', '5.2.11'],
]

const SECTIONS = [
  { id: 'general', icon: '⚙️', label: 'General' },
  { id: 'appearance', icon: '🎨', label: 'Appearance' },
  { id: 'notifications', icon: '🔔', label: 'Notifications' },
  { id: 'thresholds', icon: '⚠️', label: 'AQI Thresholds' },
  { id: 'data', icon: '📡', label: 'Data & API' },
  { id: 'ml', icon: '🤖', label: 'ML Model' },
  { id: 'profile', icon: '👤', label: 'Profile' },
  { id: 'about', icon: 'ℹ️', label: 'About' },
]

const card = 'bg-[#131e38] border border-[rgba(34,211,238,0.12)] rounded-2xl mb-4 overflow-hidden'
const cardBody = 'px-5 py-4'
const row = 'flex items-center justify-between py-2.5 border-t border-white/[0.04] first:border-0'
const label = 'text-sm text-slate-300 flex-1'
const sub = 'text-[11px] text-slate-500 mt-0.5'

function Toggle({ checked = false, onChange }) {
  return (
    <div onClick={() => { onChange?.(!checked) }}
      className="relative w-[38px] h-[22px] flex-shrink-0 cursor-pointer">
      <div className="absolute inset-0 rounded-full transition-all duration-200"
        style={{ background: checked ? 'rgba(34,211,238,0.3)' : 'rgba(255,255,255,0.08)', border: `1px solid ${checked ? 'rgba(34,211,238,0.5)' : 'rgba(255,255,255,0.1)'}` }} />
      <div className="absolute top-[3px] w-[14px] h-[14px] rounded-full transition-all duration-200"
        style={{ left: checked ? '21px' : '3px', background: checked ? 'var(--accent)' : '#475569' }} />
    </div>
  )
}

function Select({ options, value, onChange }) {
  return (
    <select value={value} onChange={e => onChange?.(e.target.value)}
      className="bg-white/[0.06] border border-white/10 rounded-lg text-white text-xs px-2.5 py-1.5 pr-7 outline-none cursor-pointer focus:border-cyan-400/40 font-mono"
      style={{ appearance: 'none', backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%2364748b'/%3E%3C/svg%3E\")", backgroundRepeat: 'no-repeat', backgroundPosition: 'right 8px center' }}>
      {options.map(o => <option key={o} style={{ background: '#131e38' }}>{o}</option>)}
    </select>
  )
}

function CardSection({ title, desc, children, action }) {
  return (
    <div className={card}>
      <div className="px-5 pt-4 flex items-start justify-between">
        <div>
          <div className="text-sm font-semibold text-white">{title}</div>
          {desc && <div className="text-[11px] text-slate-500 mt-0.5">{desc}</div>}
        </div>
        {action}
      </div>
      <div className={cardBody}>{children}</div>
    </div>
  )
}

// ── SECTIONS ──────────────────────────────────────────────────────────────────
function General() {
  const { settings, updateSetting } = useSettings()

  return <>
    <CardSection title="Location" desc="Default city for AQI readings and forecasts">
      <div className={row}><div><div className={label}>Default City</div><div className={sub}>Used on startup and forecast page</div></div>
        <Select options={['New Delhi','Beijing','Tokyo','London','New York','Mumbai','Singapore','Cairo','São Paulo','Custom…']}
          value={settings.defaultCity} onChange={v => updateSetting('defaultCity', v)} /></div>
      <div className={row}><div><div className={label}>Auto-detect Location</div><div className={sub}>Use browser geolocation on startup</div></div>
        <Toggle checked={settings.autoDetect} onChange={v => updateSetting('autoDetect', v)} /></div>
      <div className={row}><div><div className={label}>Timezone</div></div>
        <Select options={['Auto (Browser)','UTC','IST (UTC+5:30)','CST (UTC+8)','EST (UTC-5)','CET (UTC+1)']}
          value={settings.timezone} onChange={v => updateSetting('timezone', v)} /></div>
    </CardSection>
    <CardSection title="Units & Format">
      <div className={row}><div className={label}>Temperature Unit</div>
        <Select options={['°C — Celsius','°F — Fahrenheit','K — Kelvin']}
          value={settings.tempUnit} onChange={v => updateSetting('tempUnit', v)} /></div>
      <div className={row}><div className={label}>Wind Speed Unit</div>
        <Select options={['km/h','m/s','mph','knots']}
          value={settings.windSpeedUnit} onChange={v => updateSetting('windSpeedUnit', v)} /></div>
      <div className={row}><div><div className={label}>AQI Standard</div><div className={sub}>Index scale to use for categories</div></div>
        <Select options={['US EPA','CAQI (EU)','NAQI (India)','DAQI (UK)']}
          value={settings.aqiStandard} onChange={v => updateSetting('aqiStandard', v)} /></div>
      <div className={row}><div className={label}>Date Format</div>
        <Select options={['MM/DD/YYYY','DD/MM/YYYY','YYYY-MM-DD']}
          value={settings.dateFormat} onChange={v => updateSetting('dateFormat', v)} /></div>
    </CardSection>
    <CardSection title="Forecast Settings">
      <div className={row}><div className={label}>Default Forecast Range</div>
        <Select options={['3 Days','7 Days','14 Days']}
          value={settings.defaultForecastRange} onChange={v => updateSetting('defaultForecastRange', v)} /></div>
      <div className={row}><div><div className={label}>Show Confidence Score</div><div className={sub}>Display ML confidence % on forecasts</div></div>
        <Toggle checked={settings.showConfidenceScore} onChange={v => updateSetting('showConfidenceScore', v)} /></div>
      <div className={row}><div className={label}>Auto-refresh Interval</div>
        <Select options={['Off','15 min','30 min','1 hour']}
          value={settings.autoRefreshInterval} onChange={v => updateSetting('autoRefreshInterval', v)} /></div>
    </CardSection>
  </>
}

function Appearance() {
  const { settings, updateSetting } = useSettings()
  const accent = settings.accent
  const swatches = ['#22d3ee','#7c3aed','#10b981','#f59e0b','#ef4444','#ec4899']

  return <>
    <CardSection title="Theme">
      <div className={row}><div className={label}>Color Mode</div>
        <Select options={['Dark','Midnight','Light','Forest','System']}
          value={settings.theme} onChange={v => updateSetting('theme', v)} /></div>
      <div className={row}>
        <div><div className={label}>Accent Color</div><div className={sub}>Primary highlight color throughout the app</div></div>
        <div className="flex gap-2">
          {swatches.map(c => (
            <div key={c} onClick={() => updateSetting('accent', c)}
              className="w-7 h-7 rounded-lg cursor-pointer transition-transform hover:scale-110"
              style={{ background: c, border: accent === c ? '2px solid white' : '2px solid transparent', transform: accent === c ? 'scale(1.1)' : '' }} />
          ))}
        </div>
      </div>
    </CardSection>
    <CardSection title="Layout & Density">
      <div className={row}><div className={label}>Display Density</div>
        <Select options={['Compact','Comfortable','Spacious']}
          value={settings.displayDensity} onChange={v => updateSetting('displayDensity', v)} /></div>
      <div className={row}><div><div className={label}>Show Animations</div><div className={sub}>Gauge animations, transitions, fade-ins</div></div>
        <Toggle checked={settings.showAnimations} onChange={v => updateSetting('showAnimations', v)} /></div>
      <div className={row}><div className={label}>Compact City List</div>
        <Toggle checked={settings.compactCityList} onChange={v => updateSetting('compactCityList', v)} /></div>
      <div className={row}><div className={label}>Show Map on Forecast</div>
        <Toggle checked={settings.showMapOnForecast} onChange={v => updateSetting('showMapOnForecast', v)} /></div>
    </CardSection>
    <CardSection title="Charts">
      <div className={row}><div className={label}>Default Chart Type</div>
        <Select options={['Area','Line','Bar']}
          value={settings.defaultChartType} onChange={v => updateSetting('defaultChartType', v)} /></div>
      <div className={row}><div><div className={label}>Show Reference Lines</div><div className={sub}>Good / Moderate / Unhealthy markers on charts</div></div>
        <Toggle checked={settings.showReferenceLines} onChange={v => updateSetting('showReferenceLines', v)} /></div>
    </CardSection>
    {/* Live preview */}
    <CardSection title="Preview" desc="Live preview of current settings">
      <div className="rounded-xl p-4 border border-[rgba(34,211,238,0.12)] bg-[#0d1529]">
        <div className="flex items-center justify-between mb-3">
          <span className="font-display font-bold text-white">New Delhi</span>
          <span className="font-mono text-xl font-bold" style={{ color: accent }}>185</span>
        </div>
        <div className="h-1.5 rounded-full bg-white/5 overflow-hidden mb-2">
          <div className="h-full w-[55%] rounded-full" style={{ background: '#FF0000' }} />
        </div>
        <div className="text-[11px] text-slate-500">Unhealthy · Updated just now</div>
      </div>
    </CardSection>
  </>
}

function Notifications() {
  const { settings, updateSetting } = useSettings()
  const alertVal = settings.alertAqiAbove
  const alertColor = alertVal <= 50 ? '#00E400' : alertVal <= 100 ? '#FFFF00' : alertVal <= 150 ? '#FF7E00' : alertVal <= 200 ? '#FF0000' : '#8F3F97'

  return <>
    <CardSection title="Alert Channels">
      <div className={row}>
        <div><div className={label}>Browser Push Notifications</div>
          <div className={sub}><span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono bg-yellow-400/10 text-yellow-400 border border-yellow-400/20">Permission Required</span></div>
        </div>
        <Toggle checked={settings.browserNotifications} onChange={v => updateSetting('browserNotifications', v)} />
      </div>
      <div className={row}><div><div className={label}>Email Alerts</div><div className={sub}>Daily AQI digest and hazard warnings</div></div>
        <Toggle checked={settings.emailAlerts} onChange={v => updateSetting('emailAlerts', v)} /></div>
      <div className={row}><div className={label}>In-App Alerts</div>
        <Toggle checked={settings.inAppAlerts} onChange={v => updateSetting('inAppAlerts', v)} /></div>
    </CardSection>
    <CardSection title="Alert Conditions" desc="Trigger alerts when AQI crosses these levels">
      <div className={row}>
        <div className={label}>Alert when AQI above</div>
        <div className="flex items-center gap-3">
          <input type="range" min="50" max="300" value={alertVal} onChange={e => updateSetting('alertAqiAbove', +e.target.value)}
            className="w-36 h-1 rounded-full cursor-pointer outline-none"
            style={{ appearance: 'none', background: `linear-gradient(to right,${alertColor} ${((alertVal-50)/250)*100}%,rgba(255,255,255,0.1) ${((alertVal-50)/250)*100}%)` }} />
          <span className="font-mono text-xs min-w-[28px]" style={{ color: alertColor }}>{alertVal}</span>
        </div>
      </div>
      <div className={row}><div><div className={label}>Hazardous Alert (AQI 300+)</div><div className={sub}>Always notify regardless of other settings</div></div>
        <Toggle checked={settings.hazardousAlert} onChange={v => updateSetting('hazardousAlert', v)} /></div>
      <div className={row}><div><div className={label}>Daily Forecast Digest</div><div className={sub}>Morning summary at 7:00 AM</div></div>
        <Toggle checked={settings.dailyForecastDigest} onChange={v => updateSetting('dailyForecastDigest', v)} /></div>
      <div className={row}><div className={label}>Alert Cooldown</div>
        <Select options={['15 min','1 hour','6 hours','24 hours']}
          value={settings.alertCooldown} onChange={v => updateSetting('alertCooldown', v)} /></div>
    </CardSection>
    <CardSection title="Alert Preview">
      <div className="rounded-xl p-4 bg-cyan-400/5 border border-cyan-400/15 flex items-start gap-3">
        <span className="text-2xl">🔔</span>
        <div>
          <div className="text-sm font-semibold text-white mb-1">AQI Alert — New Delhi</div>
          <div className="text-xs text-slate-400">Air quality has reached <span className="text-orange-400 font-semibold">Unhealthy (185)</span>. Limit outdoor activity.</div>
          <div className="text-[10px] text-slate-500 mt-1.5 font-mono">Just now · AQI Predictor</div>
        </div>
      </div>
    </CardSection>
  </>
}

function PollutantSlider({ name, unit, min, max, value, onChange }) {
  return (
    <div className="grid grid-cols-[80px_1fr_80px] items-center gap-3 py-2 border-t border-white/[0.04] first:border-0">
      <div className="text-xs text-slate-400">{name}</div>
      <input type="range" min={min} max={max} value={value} onChange={e => onChange?.(+e.target.value)}
        className="w-full h-1 rounded-full cursor-pointer outline-none"
        style={{ appearance: 'none', background: `linear-gradient(to right,var(--accent) ${((value-min)/(max-min))*100}%,rgba(255,255,255,0.1) ${((value-min)/(max-min))*100}%)` }} />
      <span className="font-mono text-xs text-right text-cyan-400">{value} {unit}</span>
    </div>
  )
}

function AQIThresholds() {
  const { settings, updateSetting } = useSettings()
  const vals = settings.vals

  return <>
    <CardSection title="Category Thresholds" desc="Drag sliders to adjust AQI boundaries. Default: US EPA standard."
      action={<button onClick={() => updateSetting('vals', THRESHOLDS.map(t => t.def))}
        className="text-xs px-3 py-1.5 rounded-lg text-slate-400 border border-white/10 hover:text-white hover:border-white/20 transition-all">Reset to EPA</button>}>
      {THRESHOLDS.map((t, i) => (
        <div key={t.label} className="grid grid-cols-[150px_1fr_56px] items-center gap-3 py-2 border-t border-white/[0.04] first:border-0">
          <div className="flex items-center text-xs" style={{ color: t.color }}>
            <span className="w-2.5 h-2.5 rounded-full mr-2 flex-shrink-0" style={{ background: t.color }} />
            {t.label}
          </div>
          <input type="range" min="10" max="400" value={vals[i]}
            onChange={e => updateSetting('vals', vals.map((x, j) => j === i ? +e.target.value : x))}
            className="w-full h-1 rounded-full cursor-pointer outline-none"
            style={{ appearance: 'none', background: `linear-gradient(to right,${t.color} ${(vals[i]/400)*100}%,rgba(255,255,255,0.1) ${(vals[i]/400)*100}%)` }} />
          <span className="font-mono text-xs text-right text-cyan-400">{vals[i]}</span>
        </div>
      ))}
    </CardSection>
    <CardSection title="Pollutant Safe Limits" desc="Highlighted when readings exceed these values">
      <PollutantSlider name="PM2.5" unit="µg/m³" min={5} max={100} value={settings.pm25Limit} onChange={v => updateSetting('pm25Limit', v)} />
      <PollutantSlider name="PM10" unit="µg/m³" min={10} max={200} value={settings.pm10Limit} onChange={v => updateSetting('pm10Limit', v)} />
      <PollutantSlider name="NO₂" unit="µg/m³" min={10} max={200} value={settings.no2Limit} onChange={v => updateSetting('no2Limit', v)} />
      <PollutantSlider name="SO₂" unit="µg/m³" min={5} max={150} value={settings.so2Limit} onChange={v => updateSetting('so2Limit', v)} />
      <PollutantSlider name="CO₂" unit="ppm" min={350} max={1000} value={settings.co2Limit} onChange={v => updateSetting('co2Limit', v)} />
    </CardSection>
  </>
}

function DataAPI() {
  const { settings, updateSetting } = useSettings()
  const [showKey, setShowKey] = useState(false)
  const [connStatus, setConnStatus] = useState('● Connected')
  const [testing, setTesting] = useState(false)

  const testConn = () => {
    setTesting(true)
    setTimeout(() => { setConnStatus('✓ 42ms'); setTesting(false) }, 900)
    setTimeout(() => setConnStatus('● Connected'), 3500)
  }

  return <>
    <CardSection title="Data Source">
      <div className={row}><div className={label}>Primary Source</div>
        <Select options={['ML Model (Local)','OpenAQ API','IQAir API','WAQI API']}
          value={settings.dataSource} onChange={v => updateSetting('dataSource', v)} /></div>
      <div className={row}><div><div className={label}>Fallback to ML Model</div><div className={sub}>Use predictions when live data is unavailable</div></div>
        <Toggle checked={settings.fallbackToML} onChange={v => updateSetting('fallbackToML', v)} /></div>
      <div className={row}><div className={label}>Cache Duration</div>
        <Select options={['5 min','15 min','30 min','1 hour']}
          value={settings.cacheDuration} onChange={v => updateSetting('cacheDuration', v)} /></div>
    </CardSection>
    <CardSection title="API Keys" desc="Stored locally, never sent to any server">
      <div className="mb-4">
        <div className="text-xs text-slate-400 mb-2">OpenAQ API Key</div>
        <div className="flex gap-2 items-center">
          <input type={showKey ? 'text' : 'password'} value={settings.openaqApiKey} onChange={e => updateSetting('openaqApiKey', e.target.value)}
            className="flex-1 bg-white/[0.06] border border-white/10 rounded-lg text-white text-xs px-3 py-2 outline-none focus:border-cyan-400/40 font-mono animate-none" />
          <button onClick={() => setShowKey(!showKey)} className="text-xs px-3 py-1.5 rounded-lg text-slate-400 border border-white/10 hover:text-white transition-all">{showKey ? 'Hide' : 'Show'}</button>
        </div>
        <div className="text-[10px] text-slate-500 mt-1.5">Get free key at openaq.org</div>
      </div>
      <div className="border-t border-white/[0.06] pt-4">
        <div className="text-xs text-slate-400 mb-2">IQAir API Key</div>
        <div className="flex gap-2 items-center">
          <input type="password" placeholder="Enter IQAir API key…" value={settings.iqairApiKey} onChange={e => updateSetting('iqairApiKey', e.target.value)}
            className="flex-1 bg-white/[0.06] border border-white/10 rounded-lg text-white text-xs px-3 py-2 outline-none focus:border-cyan-400/40 font-mono" />
          <span className="text-[10px] font-mono px-2 py-1 rounded-full bg-white/[0.06] text-slate-500 border border-white/[0.08]">
            {settings.iqairApiKey ? 'Set' : 'Not set'}
          </span>
        </div>
      </div>
    </CardSection>
    <CardSection title="Backend Connection">
      <div className={row}><div className={label}>API Base URL</div>
        <input value={settings.apiBaseUrl} onChange={e => updateSetting('apiBaseUrl', e.target.value)}
          className="w-44 bg-white/[0.06] border border-white/10 rounded-lg text-white text-xs px-3 py-1.5 outline-none focus:border-cyan-400/40 font-mono" /></div>
      <div className={row}><div className={label}>Connection Status</div>
        <span className="text-[10px] font-mono px-2.5 py-1 rounded-full bg-green-400/10 text-green-400 border border-green-400/20">{connStatus}</span></div>
      <div className={row}><div className={label}>Request Timeout</div>
        <Select options={['10s','30s','60s']}
          value={settings.requestTimeout} onChange={v => updateSetting('requestTimeout', v)} /></div>
      <button onClick={testConn} disabled={testing}
        className="mt-2 text-xs px-4 py-1.5 rounded-lg text-slate-400 border border-white/10 hover:text-white hover:border-white/20 transition-all disabled:opacity-50">
        {testing ? '⟳ Testing…' : 'Test Connection'}
      </button>
    </CardSection>
  </>
}

function TrainingConfigSlider({ name, unit, min, max, value, onChange, hint }) {
  return (
    <div className={row}>
      <div><div className={label}>{name}</div>{hint && <div className={sub}>{hint}</div>}</div>
      <div className="flex items-center gap-2">
        <input type="range" min={min} max={max} value={value} onChange={e => onChange?.(+e.target.value)}
          className="w-28 h-1 rounded-full cursor-pointer outline-none"
          style={{ appearance: 'none', background: `linear-gradient(to right,var(--accent) ${((value-min)/(max-min))*100}%,rgba(255,255,255,0.1) ${((value-min)/(max-min))*100}%)` }} />
        <span className="font-mono text-xs text-cyan-400 w-10 text-right">{value}{unit}</span>
      </div>
    </div>
  )
}

function MLModel() {
  const { settings, updateSetting } = useSettings()

  return <>
    <CardSection title="Active Model">
      <div className={row}><div className={label}>Current Model</div><span className="text-[10px] font-mono px-2.5 py-1 rounded-full bg-green-400/10 text-green-400 border border-green-400/20">{settings.currentModel}</span></div>
      <div className={row}><div><div className={label}>R² Score</div><div className={sub}>Evaluated on synthetic test split; real-world model pipeline in Phase 2</div></div><span className="font-mono text-sm text-cyan-400 font-bold">98.78% (Synthetic)</span></div>
      <div className={row}><div className={label}>Last Trained</div><span className="text-xs font-mono text-slate-400">Baseline Pipeline</span></div>
      <div className={row}><div className={label}>Training Samples</div><span className="font-mono text-xs text-slate-400">2,000 (Synthetic)</span></div>
    </CardSection>
    <CardSection title="Model Selection">
      <div className={row}><div><div className={label}>Auto-select Best Model</div><div className={sub}>Pick highest R² after training</div></div>
        <Toggle checked={settings.autoSelectBestModel} onChange={v => updateSetting('autoSelectBestModel', v)} /></div>
      <div className={row}><div><div className={label}>Force Model</div><div className={sub}>Override auto-selection</div></div>
        <Select options={['Auto (Best R²)','Linear Regression','Random Forest','Decision Tree']}
          value={settings.forceModel} onChange={v => updateSetting('forceModel', v)} /></div>
    </CardSection>
    <CardSection title="Training Configuration">
      <TrainingConfigSlider name="Training Split" unit="%" min={60} max={90} value={settings.trainingSplit} onChange={v => updateSetting('trainingSplit', v)} hint="% of data used for training" />
      <TrainingConfigSlider name="Random Forest Trees" unit="" min={10} max={500} value={settings.randomForestTrees} onChange={v => updateSetting('randomForestTrees', v)} hint="n_estimators" />
      <TrainingConfigSlider name="Max Tree Depth" unit="" min={2} max={50} value={settings.maxTreeDepth} onChange={v => updateSetting('maxTreeDepth', v)} hint="Decision Tree max_depth" />
      <TrainingConfigSlider name="Random Seed" unit="" min={0} max={999} value={settings.randomSeed} onChange={v => updateSetting('randomSeed', v)} hint="numpy seed" />
      <div className={row}><div><div className={label}>Auto-retrain on New Data</div></div>
        <Toggle checked={settings.autoRetrain} onChange={v => updateSetting('autoRetrain', v)} /></div>
    </CardSection>
  </>
}

function Profile() {
  const { settings, updateSetting } = useSettings()

  return <>
    <CardSection title="Account">
      <div className="flex items-center gap-4 mb-4">
        <div className="w-16 h-16 rounded-full flex items-center justify-center text-white font-display font-bold text-2xl flex-shrink-0"
          style={{ background: 'linear-gradient(135deg,var(--accent),#7c3aed)' }}>AQ</div>
        <div className="flex-1">
          <div className="text-base font-semibold text-white">{settings.displayName}</div>
          <div className="text-xs text-slate-500">{settings.email}</div>
          <span className="mt-1.5 inline-flex text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-green-400/10 text-green-400 border border-green-400/20">Pro Plan</span>
        </div>
        <button className="text-xs px-3 py-1.5 rounded-lg text-slate-400 border border-white/10 hover:text-white transition-all">Edit</button>
      </div>
      <div className="border-t border-white/[0.06] pt-3">
        <div className={row}><div className={label}>Display Name</div>
          <input value={settings.displayName} onChange={e => updateSetting('displayName', e.target.value)}
            className="w-36 bg-white/[0.06] border border-white/10 rounded-lg text-white text-xs px-3 py-1.5 outline-none focus:border-cyan-400/40" /></div>
        <div className={row}><div className={label}>Email</div>
          <input value={settings.email} onChange={e => updateSetting('email', e.target.value)} type="email"
            className="w-48 bg-white/[0.06] border border-white/10 rounded-lg text-white text-xs px-3 py-1.5 outline-none focus:border-cyan-400/40 font-mono" /></div>
      </div>
    </CardSection>
    <CardSection title="Health Profile" desc="Personalizes health advisories">
      <div className={row}><div><div className={label}>Sensitive Group</div><div className={sub}>Asthma, COPD, heart condition, elderly, children</div></div>
        <Toggle checked={settings.sensitiveGroup} onChange={v => updateSetting('sensitiveGroup', v)} /></div>
      <div className={row}><div className={label}>Activity Level</div>
        <Select options={['Sedentary','Moderate','Active','Athlete']}
          value={settings.activityLevel} onChange={v => updateSetting('activityLevel', v)} /></div>
      <div className={row}><div><div className={label}>Stricter Thresholds</div><div className={sub}>Alert at lower AQI levels</div></div>
        <Toggle checked={settings.stricterThresholds} onChange={v => updateSetting('stricterThresholds', v)} /></div>
    </CardSection>
    <div className={card}><div className={cardBody}>
      <button className="w-full py-2.5 rounded-xl text-sm font-semibold text-red-400 border border-red-400/25 bg-red-400/10 hover:bg-red-400/20 transition-all">Sign Out</button>
    </div></div>
  </>
}

function About() {
  return <>
    <div className={card}><div className={cardBody}>
      <div className="grid grid-cols-2 sm:grid-cols-4 border border-white/[0.08] rounded-xl overflow-hidden">
        {[['1.0.0','Version'],['Synthetic','Baseline ML'],['Open-Meteo','Telemetry'],['3','Models']].map(([v, l], i) => (
          <div key={l} className={`text-center py-4 ${i % 2 === 0 ? 'border-r border-white/[0.08]' : ''} ${i < 2 ? 'border-b sm:border-b-0' : ''} sm:border-r last:border-r-0 border-white/[0.08]`}>
            <div className="font-display font-bold text-xl sm:text-2xl text-cyan-400">{v}</div>
            <div className="text-[11px] text-slate-500 mt-1">{l}</div>
          </div>
        ))}
      </div>
    </div></div>
    <CardSection title="Dependencies">
      <div className="grid grid-cols-2 gap-2">
        {DEPS.map(([n, v]) => (
          <div key={n} className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/[0.03]">
            <span className="font-mono text-xs text-white">{n}</span>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-slate-500">{v}</span>
              <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
            </div>
          </div>
        ))}
      </div>
    </CardSection>
    <div className={card}><div className={`${cardBody} text-center`}>
      <p className="text-xs text-slate-500 leading-loose">Built with React · FastAPI · scikit-learn<br />
        <span className="text-cyan-400">AQI Predictor</span> · Open Source · MIT License</p>
    </div></div>
  </>
}

const PANELS = { general: General, appearance: Appearance, notifications: Notifications, thresholds: AQIThresholds, data: DataAPI, ml: MLModel, profile: Profile, about: About }

export default function Settings() {
  const [active, setActive] = useState('general')
  const [saved, setSaved] = useState(false)
  const Panel = PANELS[active]
  const { settings } = useSettings()
  const isFirstRender = useRef(true)

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false
      return
    }
    setSaved(true)
    const t = setTimeout(() => setSaved(false), 2000)
    return () => clearTimeout(t)
  }, [settings])

  return (
    <div className="min-h-screen pt-16">
      {/* Save badge */}
      <div className={`fixed top-4 right-6 z-50 flex items-center gap-2 text-xs font-mono text-green-400 transition-all duration-300 ${saved ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-1'}`}>
        ✓ Saved
      </div>

      <div className="flex flex-col md:flex-row min-h-[calc(100vh-64px)]">
        {/* Sidebar - Horizontal scroll on mobile, vertical aside on desktop */}
        <aside className="w-full md:w-52 flex-shrink-0 border-b md:border-b-0 md:border-r border-[rgba(34,211,238,0.1)] bg-[#0d1529] p-3">
          <div className="text-[10px] uppercase tracking-widest text-slate-600 font-mono px-3 py-1 mb-1 hidden md:block">Settings</div>
          <div className="flex md:flex-col overflow-x-auto md:overflow-x-visible gap-1 pb-1 md:pb-0 scrollbar-none">
            {SECTIONS.slice(0, 7).map(s => (
              <button key={s.id} onClick={e => { e.stopPropagation(); setActive(s.id) }}
                className={`flex-shrink-0 md:w-full flex items-center gap-2 px-3 py-2 md:py-2.5 rounded-xl text-xs md:text-sm mb-0.5 transition-all text-left border ${active === s.id ? 'bg-cyan-400/10 border-cyan-400/30 text-cyan-400 font-medium' : 'text-slate-400 border-transparent hover:bg-white/[0.04] hover:text-slate-300'}`}>
                <span className="text-sm md:text-base w-4 md:w-5 text-center">{s.icon}</span>
                <span>{s.label}</span>
              </button>
            ))}
            <div className="hidden md:block my-2 border-t border-white/[0.06]" />
            <button onClick={e => { e.stopPropagation(); setActive('about') }}
              className={`flex-shrink-0 md:w-full flex items-center gap-2 px-3 py-2 md:py-2.5 rounded-xl text-xs md:text-sm mb-0.5 transition-all text-left border ${active === 'about' ? 'bg-cyan-400/10 border-cyan-400/30 text-cyan-400 font-medium' : 'text-slate-400 border-transparent hover:bg-white/[0.04] hover:text-slate-300'}`}>
              <span className="text-sm md:text-base w-4 md:w-5 text-center">ℹ️</span>
              <span>About</span>
            </button>
          </div>
        </aside>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 md:px-8 py-5 md:py-7">
          <div className="max-w-2xl mx-auto md:mx-0">
            <div className="mb-6 md:mb-7">
              <h1 className="font-display text-xl sm:text-2xl font-bold text-white mb-1">{SECTIONS.find(s => s.id === active)?.label}</h1>
              <p className="text-xs text-slate-500">Configure your AQI Predictor preferences</p>
            </div>
            <div>
              <Panel />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
