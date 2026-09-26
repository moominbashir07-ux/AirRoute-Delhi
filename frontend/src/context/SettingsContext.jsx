import React, { createContext, useContext, useState, useEffect } from 'react'

const SettingsContext = createContext(null)

const DEFAULT_SETTINGS = {
  // General
  defaultCity: 'New Delhi',
  autoDetect: false,
  timezone: 'Auto (Browser)',
  tempUnit: '°C — Celsius',
  windSpeedUnit: 'km/h',
  aqiStandard: 'US EPA',
  dateFormat: 'MM/DD/YYYY',
  defaultForecastRange: '7 Days',
  showConfidenceScore: true,
  autoRefreshInterval: '30 min',

  // Appearance
  theme: 'Dark',
  accent: '#22d3ee',
  displayDensity: 'Comfortable',
  showAnimations: true,
  compactCityList: false,
  showMapOnForecast: true,
  defaultChartType: 'Area',
  showReferenceLines: true,

  // Notifications
  browserNotifications: false,
  emailAlerts: true,
  inAppAlerts: true,
  alertAqiAbove: 100,
  hazardousAlert: true,
  dailyForecastDigest: true,
  alertCooldown: '1 hour',

  // AQI Thresholds
  vals: [50, 100, 150, 200, 300], // US EPA defaults
  pm25Limit: 25,
  pm10Limit: 50,
  no2Limit: 40,
  so2Limit: 20,
  co2Limit: 450,

  // Data & API
  dataSource: 'ML Model (Local)',
  fallbackToML: true,
  cacheDuration: '15 min',
  openaqApiKey: '',
  iqairApiKey: '',
  apiBaseUrl: import.meta.env.VITE_API_URL || '/api',
  requestTimeout: '30s',

  // ML Model
  currentModel: 'Linear Regression',
  autoSelectBestModel: true,
  forceModel: 'Auto (Best R²)',
  trainingSplit: 80,
  randomForestTrees: 100,
  maxTreeDepth: 10,
  randomSeed: 42,
  autoRetrain: false,

  // Profile
  displayName: 'AQI User',
  email: 'user@aqipredictor.app',
  sensitiveGroup: false,
  activityLevel: 'Moderate',
  stricterThresholds: false,
}

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(() => {
    try {
      const saved = localStorage.getItem('aqi_site_settings')
      if (saved) {
        const parsed = JSON.parse(saved)
        // Merge with defaults in case of missing keys
        return { ...DEFAULT_SETTINGS, ...parsed }
      }
    } catch (e) {
      console.error('Error loading settings:', e)
    }
    return DEFAULT_SETTINGS
  })

  // Save settings on change
  useEffect(() => {
    try {
      localStorage.setItem('aqi_site_settings', JSON.stringify(settings))
    } catch (e) {
      console.error('Error saving settings:', e)
    }
  }, [settings])

  // Apply theme classes to root
  useEffect(() => {
    const root = document.documentElement
    root.classList.remove('theme-dark', 'theme-midnight', 'theme-light', 'theme-forest')
    
    let activeTheme = settings.theme
    if (activeTheme === 'System') {
      activeTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'Dark' : 'Light'
    }
    
    root.classList.add(`theme-${activeTheme.toLowerCase()}`)
  }, [settings.theme])

  // Apply custom accent color styling variable
  useEffect(() => {
    if (settings.accent) {
      const root = document.documentElement
      root.style.setProperty('--accent', settings.accent)
      
      // Calculate rgb components for --accent-dim
      const hex = settings.accent.replace('#', '')
      const r = parseInt(hex.substring(0, 2), 16)
      const g = parseInt(hex.substring(2, 4), 16)
      const b = parseInt(hex.substring(4, 6), 16)
      root.style.setProperty('--accent-dim', `rgba(${r}, ${g}, ${b}, 0.2)`)
    }
  }, [settings.accent])

  const updateSetting = (key, value) => {
    setSettings((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  const resetToDefaults = () => {
    setSettings(DEFAULT_SETTINGS)
  }

  return (
    <SettingsContext.Provider value={{ settings, updateSetting, resetToDefaults }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider')
  }
  return context
}
