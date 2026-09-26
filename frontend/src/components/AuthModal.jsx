import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Mail, Lock, User, RefreshCw, AlertCircle, CheckCircle, ShieldCheck } from 'lucide-react'
import { sendOTP, verifyOTP, loginUser } from '../utils/api'
import clsx from 'clsx'

export default function AuthModal({ isOpen, onClose, onLoginSuccess }) {
  // Modes: 'otp_request' (Step 1) | 'otp_verify' (Step 2) | 'password' (Alternative login)
  const [mode, setMode] = useState('otp_request')
  
  // Input fields
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [otpInput, setOtpInput] = useState('')
  
  // Anti-automation visual captcha
  const [captchaText, setCaptchaText] = useState('')
  const [captchaInput, setCaptchaInput] = useState('')
  const canvasRef = useRef(null)
  
  // Cooldown & Status
  const [resendTimer, setResendTimer] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)

  // Generate visual captcha (alphanumeric excluding ambiguous characters)
  const generateCaptcha = () => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    let result = ''
    for (let i = 0; i < 6; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length))
    }
    setCaptchaText(result)
    setCaptchaInput('')
  }

  // Draw Captcha on Canvas (Clean Cyan & Slate aesthetic - no purple gradients)
  useEffect(() => {
    if ((mode === 'otp_request' || mode === 'password') && canvasRef.current && captchaText) {
      const ctx = canvasRef.current.getContext('2d')
      ctx.clearRect(0, 0, 150, 44)
      
      // Background
      ctx.fillStyle = '#0f172a' // Slate-900
      ctx.fillRect(0, 0, 150, 44)
      
      // Subtle background grid
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.15)'
      ctx.lineWidth = 1
      for (let i = 0; i < 4; i++) {
        ctx.beginPath()
        ctx.moveTo(Math.random() * 150, Math.random() * 44)
        ctx.lineTo(Math.random() * 150, Math.random() * 44)
        ctx.stroke()
      }
      
      // Captcha characters
      ctx.font = 'bold 20px "JetBrains Mono", monospace'
      ctx.textBaseline = 'middle'
      
      for (let i = 0; i < captchaText.length; i++) {
        const char = captchaText[i]
        ctx.fillStyle = '#38bdf8' // Cyan-400
        
        ctx.save()
        const x = 14 + i * 21 + Math.random() * 3
        const y = 22 + (Math.random() * 6 - 3)
        ctx.translate(x, y)
        const angle = (Math.random() * 26 - 13) * (Math.PI / 180)
        ctx.rotate(angle)
        ctx.fillText(char, 0, 0)
        ctx.restore()
      }
    }
  }, [captchaText, mode, isOpen])

  // Reset states upon opening modal
  useEffect(() => {
    if (isOpen) {
      generateCaptcha()
      setError(null)
      setSuccessMsg(null)
    }
  }, [isOpen, mode])

  // Resend countdown timer
  useEffect(() => {
    if (resendTimer > 0) {
      const interval = setInterval(() => {
        setResendTimer(prev => prev - 1)
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [resendTimer])

  if (!isOpen) return null

  // Step 1 -> 2: Request OTP
  const handleRequestOTP = async (e) => {
    e.preventDefault()
    setError(null)

    const cleanEmail = email.trim().toLowerCase()
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setError('Please enter a valid email address.')
      return
    }

    // Validate visual captcha
    if (captchaInput.trim().toUpperCase() !== captchaText) {
      setError('Incorrect verification text. Please try again.')
      generateCaptcha()
      return
    }

    setLoading(true)
    try {
      const res = await sendOTP(cleanEmail, name.trim())
      if (res.status === 'success') {
        setMode('otp_verify')
        setResendTimer(res.cooldown || 60)
        setSuccessMsg('OTP sent to your email.')
        setOtpInput('')
      }
    } catch (err) {
      setError(err.message || 'Failed to dispatch verification email. Please try again.')
      generateCaptcha()
    } finally {
      setLoading(false)
    }
  }

  // Step 5 -> 7: Verify OTP and Authenticate
  const handleVerifyOTP = async (e) => {
    e.preventDefault()
    setError(null)

    const cleanOtp = otpInput.replace(/[^0-9]/g, '')
    if (cleanOtp.length !== 6) {
      setError('Please enter a valid 6-digit numeric code.')
      return
    }

    setLoading(true)
    try {
      const res = await verifyOTP(email.trim().toLowerCase(), cleanOtp, name.trim())
      if (res.status === 'success' && res.user) {
        localStorage.setItem('aqi_logged_in_user', JSON.stringify(res.user))
        setSuccessMsg(`Welcome, ${res.user.name || 'User'}! Authentication successful.`)
        setTimeout(() => {
          onLoginSuccess(res.user)
          onClose()
        }, 1200)
      }
    } catch (err) {
      setError(err.message || 'Verification failed. Please check the code and try again.')
    } finally {
      setLoading(false)
    }
  }

  // Resend OTP handler with cooldown protection
  const handleResendOTP = async () => {
    if (resendTimer > 0) return
    setError(null)
    setLoading(true)
    try {
      const res = await sendOTP(email.trim().toLowerCase(), name.trim())
      if (res.status === 'success') {
        setResendTimer(res.cooldown || 60)
        setSuccessMsg('A new verification code has been dispatched to your email.')
        setTimeout(() => setSuccessMsg(null), 4000)
      }
    } catch (err) {
      setError(err.message || 'Could not resend verification code. Please wait before retrying.')
    } finally {
      setLoading(false)
    }
  }

  // Password Sign In Handler
  const handlePasswordLogin = async (e) => {
    e.preventDefault()
    setError(null)

    if (captchaInput.trim().toUpperCase() !== captchaText) {
      setError('Incorrect verification text. Please try again.')
      generateCaptcha()
      return
    }

    setLoading(true)
    try {
      const res = await loginUser(email.trim().toLowerCase(), password)
      if (res.status === 'success' && res.user) {
        localStorage.setItem('aqi_logged_in_user', JSON.stringify(res.user))
        setSuccessMsg(`Welcome back, ${res.user.name}!`)
        setTimeout(() => {
          onLoginSuccess(res.user)
          onClose()
        }, 1200)
      }
    } catch (err) {
      setError(err.message || 'Login failed. Please verify credentials.')
      generateCaptcha()
    } finally {
      setLoading(false)
    }
  }

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        />

        {/* Modal Dialog */}
        <motion.div
          initial={{ scale: 0.96, y: 10, opacity: 0 }}
          animate={{ scale: 1, y: 0, opacity: 1 }}
          exit={{ scale: 0.96, y: 10, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="relative w-full max-w-md bg-[#0b1324] border border-cyan-500/20 rounded-2xl p-6 sm:p-8 max-h-[92vh] overflow-y-auto shadow-2xl z-10"
        >
          {/* Close button */}
          <button
            onClick={onClose}
            aria-label="Close authentication modal"
            className="absolute top-5 right-5 text-slate-400 hover:text-white transition-colors p-1"
          >
            <X size={18} />
          </button>

          {/* Header */}
          <div className="flex flex-col items-center mb-6">
            <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-3 bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">
              <ShieldCheck size={22} />
            </div>
            <h2 className="font-display text-xl font-bold text-white tracking-tight">
              {mode === 'otp_verify' ? 'Verify Code' : 'AirRoute Delhi Access'}
            </h2>
            <p className="text-xs text-slate-400 mt-1 text-center max-w-[300px]">
              {mode === 'otp_verify'
                ? `Enter the 6-digit verification code dispatched to ${email}.`
                : 'Sign in using a one-time verification code sent directly to your email.'}
            </p>
          </div>

          {/* Error and Success Notices */}
          {error && (
            <div className="mb-4 flex items-start gap-2 p-3 rounded-lg bg-red-950/40 border border-red-500/30 text-xs text-red-300">
              <AlertCircle size={15} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="mb-4 flex items-start gap-2 p-3 rounded-lg bg-cyan-950/40 border border-cyan-500/30 text-xs text-cyan-300">
              <CheckCircle size={15} className="shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Mode Switcher Tabs (Only when not in active OTP verification step) */}
          {mode !== 'otp_verify' && (
            <div className="flex border-b border-slate-800 mb-6">
              <button
                type="button"
                onClick={() => { setMode('otp_request'); setError(null); }}
                className={clsx(
                  'flex-1 pb-2.5 text-xs font-semibold tracking-wide transition-all border-b-2 text-center',
                  mode === 'otp_request'
                    ? 'text-cyan-400 border-cyan-400'
                    : 'text-slate-400 border-transparent hover:text-slate-200'
                )}
              >
                Email Code (OTP)
              </button>
              <button
                type="button"
                onClick={() => { setMode('password'); setError(null); }}
                className={clsx(
                  'flex-1 pb-2.5 text-xs font-semibold tracking-wide transition-all border-b-2 text-center',
                  mode === 'password'
                    ? 'text-cyan-400 border-cyan-400'
                    : 'text-slate-400 border-transparent hover:text-slate-200'
                )}
              >
                Password Sign In
              </button>
            </div>
          )}

          {/* STEP 1: Enter Email & Request OTP */}
          {mode === 'otp_request' && (
            <form onSubmit={handleRequestOTP} className="space-y-4">
              <div>
                <label htmlFor="auth-email-input" className="block text-xs font-medium text-slate-300 mb-1.5">
                  Email Address <span className="text-cyan-400">*</span>
                </label>
                <div className="relative">
                  <Mail size={16} className="absolute left-3.5 top-3.5 text-slate-500" />
                  <input
                    id="auth-email-input"
                    type="email"
                    required
                    autoComplete="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    className="w-full bg-slate-900/90 border border-slate-700/80 rounded-lg pl-10 pr-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition-all font-sans"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="auth-name-input" className="block text-xs font-medium text-slate-300 mb-1.5">
                  Full Name <span className="text-slate-500">(Optional)</span>
                </label>
                <div className="relative">
                  <User size={16} className="absolute left-3.5 top-3.5 text-slate-500" />
                  <input
                    id="auth-name-input"
                    type="text"
                    autoComplete="name"
                    placeholder="Your name"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    className="w-full bg-slate-900/90 border border-slate-700/80 rounded-lg pl-10 pr-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition-all font-sans"
                  />
                </div>
              </div>

              {/* Bot Protection Visual Captcha */}
              <div className="space-y-1.5 pt-1">
                <label htmlFor="auth-captcha-input" className="block text-xs font-medium text-slate-300">
                  Verification Code <span className="text-cyan-400">*</span>
                </label>
                <div className="flex gap-2 items-center">
                  <canvas
                    ref={canvasRef}
                    width={150}
                    height={44}
                    aria-label="Anti-bot captcha text"
                    className="rounded-lg border border-slate-700 bg-slate-900 select-none shrink-0"
                  />
                  <button
                    type="button"
                    onClick={generateCaptcha}
                    className="p-2.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-400 hover:text-white transition-colors"
                    title="Generate new verification text"
                  >
                    <RefreshCw size={15} />
                  </button>
                  <input
                    id="auth-captcha-input"
                    type="text"
                    required
                    maxLength={6}
                    placeholder="Enter code"
                    value={captchaInput}
                    onChange={e => setCaptchaInput(e.target.value)}
                    className="w-full bg-slate-900/90 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 font-mono uppercase tracking-wider focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400"
                  />
                </div>
              </div>

              {/* Primary Action Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-3 rounded-lg font-semibold text-slate-950 text-sm bg-cyan-400 hover:bg-cyan-300 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loading ? <RefreshCw size={16} className="animate-spin" /> : 'Send OTP'}
              </button>
            </form>
          )}

          {/* STEP 4 & 5: Enter 6-digit OTP & Verify */}
          {mode === 'otp_verify' && (
            <form onSubmit={handleVerifyOTP} className="space-y-5">
              <div className="p-3.5 bg-slate-900/80 border border-slate-800 rounded-lg text-xs text-slate-300">
                <p className="font-semibold text-cyan-400 mb-0.5">OTP sent to your email.</p>
                <p className="text-slate-400">
                  Please check your inbox at <span className="text-slate-200 font-mono">{email}</span>. The code is valid for 5 minutes.
                </p>
              </div>

              <div>
                <label htmlFor="auth-otp-input" className="block text-center text-xs font-medium text-slate-300 mb-2">
                  Enter 6-Digit Verification Code
                </label>
                <div className="flex justify-center">
                  <input
                    id="auth-otp-input"
                    type="text"
                    required
                    autoFocus
                    maxLength={6}
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    placeholder="000000"
                    value={otpInput}
                    onChange={e => setOtpInput(e.target.value.replace(/[^0-9]/g, ''))}
                    className="w-44 bg-slate-900 border border-cyan-500/40 rounded-lg py-2.5 text-center text-2xl font-bold font-mono tracking-widest text-cyan-400 placeholder-slate-700 focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20"
                  />
                </div>
              </div>

              {/* Cooldown & Resend Option */}
              <div className="text-center text-xs">
                {resendTimer > 0 ? (
                  <span className="text-slate-400">
                    Resend code in <strong className="text-cyan-400 font-mono">{resendTimer}s</strong>
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={handleResendOTP}
                    disabled={loading}
                    className="text-cyan-400 hover:text-cyan-300 font-medium underline underline-offset-4 transition-colors disabled:opacity-50"
                  >
                    Resend OTP
                  </button>
                )}
              </div>

              {/* Verify Button */}
              <button
                type="submit"
                disabled={loading || otpInput.length !== 6}
                className="w-full py-3 rounded-lg font-semibold text-slate-950 text-sm bg-cyan-400 hover:bg-cyan-300 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loading ? <RefreshCw size={16} className="animate-spin" /> : 'Verify OTP'}
              </button>

              <button
                type="button"
                onClick={() => { setMode('otp_request'); setError(null); }}
                className="w-full text-center text-xs text-slate-400 hover:text-slate-200 transition-colors pt-1"
              >
                ← Change email address
              </button>
            </form>
          )}

          {/* Alternative: Password Login */}
          {mode === 'password' && (
            <form onSubmit={handlePasswordLogin} className="space-y-4">
              <div>
                <label htmlFor="auth-pwd-email" className="block text-xs font-medium text-slate-300 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail size={16} className="absolute left-3.5 top-3.5 text-slate-500" />
                  <input
                    id="auth-pwd-email"
                    type="email"
                    required
                    autoComplete="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    className="w-full bg-slate-900/90 border border-slate-700/80 rounded-lg pl-10 pr-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition-all font-sans"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="auth-pwd-password" className="block text-xs font-medium text-slate-300 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock size={16} className="absolute left-3.5 top-3.5 text-slate-500" />
                  <input
                    id="auth-pwd-password"
                    type="password"
                    required
                    autoComplete="current-password"
                    placeholder="Enter your account password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    className="w-full bg-slate-900/90 border border-slate-700/80 rounded-lg pl-10 pr-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition-all font-sans"
                  />
                </div>
              </div>

              {/* Bot Protection Captcha */}
              <div className="space-y-1.5 pt-1">
                <label htmlFor="auth-pwd-captcha" className="block text-xs font-medium text-slate-300">
                  Verification Code
                </label>
                <div className="flex gap-2 items-center">
                  <canvas
                    ref={canvasRef}
                    width={150}
                    height={44}
                    aria-label="Anti-bot captcha text"
                    className="rounded-lg border border-slate-700 bg-slate-900 select-none shrink-0"
                  />
                  <button
                    type="button"
                    onClick={generateCaptcha}
                    className="p-2.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-400 hover:text-white transition-colors"
                    title="Generate new verification text"
                  >
                    <RefreshCw size={15} />
                  </button>
                  <input
                    id="auth-pwd-captcha"
                    type="text"
                    required
                    maxLength={6}
                    placeholder="Enter code"
                    value={captchaInput}
                    onChange={e => setCaptchaInput(e.target.value)}
                    className="w-full bg-slate-900/90 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 font-mono uppercase tracking-wider focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-3 rounded-lg font-semibold text-slate-950 text-sm bg-cyan-400 hover:bg-cyan-300 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loading ? <RefreshCw size={16} className="animate-spin" /> : 'Sign In'}
              </button>
            </form>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
