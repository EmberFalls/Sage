import React, { createContext, useContext, useEffect, useState } from 'react'

export type UserRole = 'bank_officer' | 'branch_lead' | 'insurance_agent' | 'farmer' | 'admin'

export interface User {
  id: string
  role: UserRole
  name: string
  email?: string | null
  phone?: string | null
  linked_borrower_id?: string | null
  branch_id?: string | null
  is_active: boolean
  created_at: string
}

export interface DemoAccount {
  role: UserRole
  role_label: string
  name: string
  email?: string
  phone?: string
  password?: string
  linked_borrower_id?: string
  description: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  role: UserRole | null
  isLoading: boolean
  loginWithPassword: (email: string, password: string) => Promise<User>
  sendOtp: (phone: string) => Promise<{ status: string; message: string; otp: string; expires_in_seconds: number }>
  verifyOtp: (phone: string, otp: string, name?: string, linkedBorrowerId?: string) => Promise<User>
  registerUser: (data: { role: UserRole; name: string; email?: string; phone?: string; password?: string; linked_borrower_id?: string }) => Promise<User>
  quickLoginDemo: (account: DemoAccount) => Promise<User>
  logout: () => void
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('sage_token'))
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('sage_user')
    if (saved) {
      try {
        return JSON.parse(saved)
      } catch {
        return null
      }
    }
    return null
  })
  const [isLoading, setIsLoading] = useState<boolean>(true)

  const saveAuth = (newToken: string, newUser: User) => {
    setToken(newToken)
    setUser(newUser)
    localStorage.setItem('sage_token', newToken)
    localStorage.setItem('sage_user', JSON.stringify(newUser))
  }

  const logout = () => {
    const activeToken = token
    if (activeToken) fetch(`${API_BASE}/api/auth/logout`, { method: 'POST', headers: { Authorization: `Bearer ${activeToken}` } }).catch(() => {})
    setToken(null)
    setUser(null)
    localStorage.removeItem('sage_token')
    localStorage.removeItem('sage_user')
  }

  // Validate token on mount
  useEffect(() => {
    if (!token) {
      setIsLoading(false)
      return
    }
    let cancelled = false
    const controller = new AbortController()
    setIsLoading(true)
    fetch(`${API_BASE}/api/auth/me`, {
      signal: controller.signal,
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error('Token expired')
        return res.json()
      })
      .then((me: User) => {
        if (cancelled) return
        setUser(me)
        localStorage.setItem('sage_user', JSON.stringify(me))
      })
      .catch(() => {
        if (!cancelled) logout()
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => { cancelled = true; controller.abort() }
  }, [token])

  const loginWithPassword = async (email: string, password: string): Promise<User> => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.detail || 'Login failed')
    }
    saveAuth(data.access_token, data.user)
    return data.user
  }

  const sendOtp = async (phone: string) => {
    const res = await fetch(`${API_BASE}/api/auth/otp/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone }),
    })
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.detail || 'Could not send OTP')
    }
    return data
  }

  const verifyOtp = async (phone: string, otp: string, name?: string, linkedBorrowerId?: string): Promise<User> => {
    const res = await fetch(`${API_BASE}/api/auth/otp/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        phone,
        otp,
        name,
        linked_borrower_id: linkedBorrowerId,
      }),
    })
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.detail || 'OTP verification failed')
    }
    saveAuth(data.access_token, data.user)
    return data.user
  }

  const registerUser = async (data: {
    role: UserRole
    name: string
    email?: string
    phone?: string
    password?: string
    linked_borrower_id?: string
  }): Promise<User> => {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    const resData = await res.json()
    if (!res.ok) {
      throw new Error(resData.detail || 'Registration failed')
    }
    saveAuth(resData.access_token, resData.user)
    return resData.user
  }

  const quickLoginDemo = async (account: DemoAccount): Promise<User> => {
    if (account.role === 'farmer' && account.phone) {
      // Send OTP then verify with the demo OTP
      const otpRes = await sendOtp(account.phone)
      return verifyOtp(account.phone, otpRes.otp, account.name, account.linked_borrower_id)
    } else if (account.email && account.password) {
      return loginWithPassword(account.email, account.password)
    }
    throw new Error('Invalid demo account credentials')
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        role: user?.role || null,
        isLoading,
        loginWithPassword,
        sendOtp,
        verifyOtp,
        registerUser,
        quickLoginDemo,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
