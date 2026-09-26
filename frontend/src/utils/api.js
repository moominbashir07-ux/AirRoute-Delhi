import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Request failed'
    console.error('[API Error]', msg)
    return Promise.reject(new Error(msg))
  }
)

export const predictAQI = (data) => api.post('/predict', data)
export const trainModel = () => api.post('/train')
export const getHistory = (days = 30) => api.get(`/aqi-history?days=${days}`)
export const getForecast = (days = 7) => api.get(`/forecast?days=${days}`)
export const getMetrics = () => api.get('/metrics')
export const getHealth = () => api.get('/health')

// Commuter Exposure & Stations APIs
export const optimizeCommute = (data) => api.post('/commute/optimize', data)
export const getDelhiStations = () => api.get('/stations/delhi')

// Auth APIs
export const sendOTP = (email, name) => api.post('/auth/send-otp', { email, name })
export const verifyOTP = (email, otp, name) => api.post('/auth/verify-otp', { email, otp, name })
export const signupUser = (name, email, password, otp) => api.post('/auth/signup', { name, email, password, otp })
export const loginUser = (email, password) => api.post('/auth/login', { email, password })

export default api

