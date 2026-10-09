import React, { useState } from 'react'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Copy,
  KeyRound,
  Layers,
  Lock,
  Mail,
  Phone,
  ShieldCheck,
  Smartphone,
  Sprout,
  AlertCircle
} from 'lucide-react'
import { useAuth } from './AuthContext'

interface LoginPageProps {
  onSuccess: () => void
  onBack: () => void
}

export function LoginPage({ onSuccess, onBack }: LoginPageProps) {
  const { loginWithPassword, sendOtp, verifyOtp } = useAuth()

  // Tab: 'institutional' | 'farmer'
  const [tab, setTab] = useState<'institutional' | 'farmer'>('institutional')

  // Institutional form state
  const [email, setEmail] = useState('officer@bank.demo')
  const [password, setPassword] = useState('password123')

  // Farmer OTP form state
  const [phone, setPhone] = useState('9876543210')
  const [otpSent, setOtpSent] = useState(false)
  const [otp, setOtp] = useState('')
  const [demoOtpHint, setDemoOtpHint] = useState('')

  // UI status
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [toast, setToast] = useState<string | null>(null)
  const [copiedPill, setCopiedPill] = useState<string | null>(null)

  const showToast = (msg: string) => {
    setToast(msg)
    window.setTimeout(() => setToast(null), 2500)
  }

  const handleCopyAndFill = (type: 'bank' | 'insurance' | 'farmer1' | 'farmer2') => {
    setError('')
    setSuccessMsg('')
    setCopiedPill(type)
    window.setTimeout(() => setCopiedPill(null), 1500)

    if (type === 'bank') {
      setTab('institutional')
      setEmail('officer@bank.demo')
      setPassword('password123')
      navigator.clipboard?.writeText('Email: officer@bank.demo\nPassword: password123')
      showToast('Copied Bank Officer credentials & filled form')
    } else if (type === 'insurance') {
      setTab('institutional')
      setEmail('agent@insurance.demo')
      setPassword('password123')
      navigator.clipboard?.writeText('Email: agent@insurance.demo\nPassword: password123')
      showToast('Copied Insurance Underwriter credentials & filled form')
    } else if (type === 'farmer1') {
      setTab('farmer')
      setPhone('9876543210')
      setOtpSent(true)
      setDemoOtpHint('654321')
      setOtp('654321')
      navigator.clipboard?.writeText('Phone: 9876543210\nOTP: 654321')
      showToast('Copied Farmer (Nashik) credentials & filled OTP')
    } else if (type === 'farmer2') {
      setTab('farmer')
      setPhone('9876543211')
      setOtpSent(true)
      setDemoOtpHint('789123')
      setOtp('789123')
      navigator.clipboard?.writeText('Phone: 9876543211\nOTP: 789123')
      showToast('Copied Farmer (Pune) credentials & filled OTP')
    }
  }

  const handleInstitutionalSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await loginWithPassword(email, password)
      onSuccess()
    } catch (err: any) {
      setError(err.message || 'Invalid credentials. Please verify.')
    } finally {
      setLoading(false)
    }
  }

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccessMsg('')
    setLoading(true)
    try {
      const res = await sendOtp(phone)
      setOtpSent(true)
      setDemoOtpHint(res.otp)
      setOtp(res.otp)
      setSuccessMsg(res.message || 'OTP generated!')
      showToast(`Demo OTP: ${res.otp}`)
    } catch (err: any) {
      setError(err.message || 'Could not send OTP. Check mobile number.')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await verifyOtp(phone, otp)
      onSuccess()
    } catch (err: any) {
      setError(err.message || 'Invalid or expired OTP.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-hero-viewport">
      {/* Background Atmosphere Layers */}
      <div className="auth-hero-backdrop" />
      <div className="auth-hero-gradient" />

      {/* Centered Apple-Style Floating Navbar */}
      <header className="hero-nav-wrapper">
        <nav className="hero-apple-navbar" aria-label="Main Navigation">
          <div
            className="hero-brand"
            onClick={onBack}
            role="button"
            tabIndex={0}
            title="PhenoCredit Home"
          >
            <div className="hero-brand-icon">
              <Layers size={18} strokeWidth={2.4} />
            </div>
            <span className="hero-brand-name">PhenoCredit</span>
          </div>

          <div className="hero-nav-divider" />

          <div className="hero-nav-links">
            <button className="hero-nav-link" onClick={onBack}>
              Home
            </button>
            <button className="hero-nav-link active">
              Sign In
            </button>
          </div>

          <div className="hero-nav-divider" />

          <div className="hero-nav-actions">
            <button className="hero-apple-cta" onClick={onBack}>
              <ArrowLeft size={13} strokeWidth={2.4} />
              <span>Back</span>
            </button>
          </div>
        </nav>
      </header>

      {/* Floating Big Glass Rectangle Center Stage */}
      <main className="auth-center-stage">
        <div className="auth-glass-box">
          {/* Header */}
          <div className="auth-header-block">
            <div className="auth-badge-pill">
              <span className="pulse-dot" />
              <span>AUTHENTICATION PORTAL</span>
            </div>
            <h1 className="auth-main-title">Access PhenoCredit</h1>
            <p className="auth-main-subtitle">
              Climate-aware agricultural credit risk intelligence & portfolio workspace.
            </p>
          </div>

          {/* Segmented Control Tabs */}
          <div className="auth-segmented-control" role="tablist">
            <button
              type="button"
              className={`auth-seg-btn ${tab === 'institutional' ? 'active' : ''}`}
              onClick={() => {
                setTab('institutional')
                setError('')
              }}
            >
              <Lock size={15} /> Institutional (Email)
            </button>
            <button
              type="button"
              className={`auth-seg-btn ${tab === 'farmer' ? 'active' : ''}`}
              onClick={() => {
                setTab('farmer')
                setError('')
              }}
            >
              <Smartphone size={15} /> Farmer (Mobile OTP)
            </button>
          </div>

          {/* Error / Success Alerts */}
          {error && (
            <div className="auth-alert-error" style={{ marginBottom: '1rem' }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="auth-alert-success" style={{ marginBottom: '1rem' }}>
              <CheckCircle2 size={16} />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Form Body */}
          {tab === 'institutional' ? (
            /* Institutional Email & Password Form */
            <form onSubmit={handleInstitutionalSubmit} className="auth-form-body">
              <div className="auth-input-group">
                <label>
                  <span>Institutional Email</span>
                  <span className="sub-hint">Bank or Insurance</span>
                </label>
                <div className="auth-input-field-wrap">
                  <Mail size={17} className="auth-field-icon" />
                  <input
                    type="email"
                    className="auth-hero-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="officer@bank.demo"
                    required
                  />
                </div>
              </div>

              <div className="auth-input-group">
                <label>
                  <span>Password</span>
                  <span className="sub-hint">Default: password123</span>
                </label>
                <div className="auth-input-field-wrap">
                  <Lock size={17} className="auth-field-icon" />
                  <input
                    type="password"
                    className="auth-hero-input"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                className="auth-hero-cta"
                disabled={loading}
              >
                <span>{loading ? 'Authenticating…' : 'Sign In to Workspace'}</span>
                <ArrowRight size={16} />
              </button>
            </form>
          ) : (
            /* Farmer Mobile OTP Flow */
            <div className="auth-form-body">
              {!otpSent ? (
                <form onSubmit={handleSendOtp} className="auth-form-body">
                  <div className="auth-input-group">
                    <label>
                      <span>Farmer 10-Digit Mobile Number</span>
                      <span className="sub-hint">OTP Login</span>
                    </label>
                    <div className="auth-input-field-wrap">
                      <Phone size={17} className="auth-field-icon" />
                      <input
                        type="tel"
                        className="auth-hero-input"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        placeholder="9876543210"
                        pattern="[0-9]{10}"
                        required
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="auth-hero-cta"
                    disabled={loading}
                  >
                    <span>{loading ? 'Sending OTP…' : 'Send 6-Digit OTP Code'}</span>
                    <Smartphone size={16} />
                  </button>

                </form>

              ) : (
                <form onSubmit={handleVerifyOtp} className="auth-form-body">
                  <div className="auth-input-group">
                    <label>
                      <span>Mobile Number</span>
                      <button
                        type="button"
                        onClick={() => {
                          setOtpSent(false)
                          setOtp('')
                        }}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#059669',
                          fontWeight: 600,
                          fontSize: '0.75rem',
                          cursor: 'pointer',
                          textDecoration: 'underline',
                        }}
                      >
                        Change
                      </button>
                    </label>
                    <div className="auth-input-field-wrap">
                      <Phone size={17} className="auth-field-icon" />
                      <input
                        type="tel"
                        className="auth-hero-input"
                        value={phone}
                        disabled
                        style={{ opacity: 0.7 }}
                      />
                    </div>
                  </div>

                  <div className="auth-input-group">
                    <label>
                      <span>Enter 6-Digit OTP</span>
                      <span className="sub-hint">Your code: <b>{demoOtpHint || '------'}</b></span>
                    </label>
                    <div className="auth-input-field-wrap">
                      <KeyRound size={17} className="auth-field-icon" />
                      <input
                        type="text"
                        className="auth-hero-input"
                        value={otp}
                        onChange={(e) => setOtp(e.target.value)}
                        placeholder="654321"
                        maxLength={6}
                        required
                        style={{ letterSpacing: '0.2em', fontWeight: 700 }}
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="auth-hero-cta"
                    disabled={loading || otp.length < 6}
                  >
                    <span>{loading ? 'Verifying…' : 'Verify & Enter Farmer Portal'}</span>
                    <CheckCircle2 size={16} />
                  </button>
                </form>
              )}
            </div>
          )}

          {/* Quick Copy-to-Fill Credentials Bar */}
          <div className="auth-copy-bar">
            <div className="auth-copy-header">
              <span>Quick Demo Credentials (Click to Copy & Fill)</span>
              <small>Ready to test</small>
            </div>

            <div className="auth-copy-pills">
              <div
                className="auth-copy-pill"
                onClick={() => handleCopyAndFill('bank')}
                title="Click to copy & fill Bank Officer credentials"
              >
                <div className="auth-copy-pill-text">
                  <span className="auth-copy-pill-role">🏦 Bank Officer</span>
                  <span className="auth-copy-pill-val">officer@bank.demo</span>
                </div>
                <div className="auth-copy-icon-btn">
                  {copiedPill === 'bank' ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                </div>
              </div>

              <div
                className="auth-copy-pill"
                onClick={() => handleCopyAndFill('insurance')}
                title="Click to copy & fill Insurer credentials"
              >
                <div className="auth-copy-pill-text">
                  <span className="auth-copy-pill-role">🛡️ Agri Insurer</span>
                  <span className="auth-copy-pill-val">agent@insurance.demo</span>
                </div>
                <div className="auth-copy-icon-btn">
                  {copiedPill === 'insurance' ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                </div>
              </div>

              <div
                className="auth-copy-pill"
                onClick={() => handleCopyAndFill('farmer1')}
                title="Click to copy & fill Farmer Ramesh Patil (Nashik) OTP"
              >
                <div className="auth-copy-pill-text">
                  <span className="auth-copy-pill-role">🌾 Farmer (Nashik)</span>
                  <span className="auth-copy-pill-val">+91 9876543210</span>
                </div>
                <div className="auth-copy-icon-btn">
                  {copiedPill === 'farmer1' ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                </div>
              </div>

              <div
                className="auth-copy-pill"
                onClick={() => handleCopyAndFill('farmer2')}
                title="Click to copy & fill Farmer Sunita Bai (Pune) OTP"
              >
                <div className="auth-copy-pill-text">
                  <span className="auth-copy-pill-role">🌾 Farmer (Pune)</span>
                  <span className="auth-copy-pill-val">+91 9876543211</span>
                </div>
                <div className="auth-copy-icon-btn">
                  {copiedPill === 'farmer2' ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Floating Toast notification */}
      {toast && (
        <div className="auth-toast">
          <Check size={16} color="#34d399" />
          <span>{toast}</span>
        </div>
      )}
    </div>
  )
}
