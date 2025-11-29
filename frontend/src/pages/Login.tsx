import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_BASE_URL } from '../config'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('johanna.inga@outlook.com')
  const [password, setPassword] = useState('admin')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const body = new URLSearchParams()
      body.append('username', email)
      body.append('password', password)

      const res = await fetch(`${API_BASE_URL}/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || `Login failed with status ${res.status}`)
      }

      const data: { access_token: string; token_type: string } = await res.json()

      // save token and go to dashboard
      localStorage.setItem('vakta_token', data.access_token)
      navigate('/')
    } catch (err) {
      console.error(err)
      setError(
        err instanceof Error ? err.message : 'Something went wrong while logging in.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-white/5 px-8 py-6 shadow-lg">
        <h1 className="text-2xl font-semibold tracking-tight mb-1">VaktaPlan</h1>
        <p className="text-sm text-slate-300 mb-6">
          Skráðu þig inn með netfangi og lykilorði
        </p>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="block text-sm font-medium" htmlFor="email">
              Netfang
            </label>
            <input
              id="email"
              type="email"
              className="w-full rounded-md border border-white/20 bg-black/30 px-3 py-2 text-sm outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium" htmlFor="password">
              Lykilorð
            </label>
            <input
              id="password"
              type="password"
              className="w-full rounded-md border border-white/20 bg-black/30 px-3 py-2 text-sm outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          {error && (
            <p className="text-xs text-red-400 whitespace-pre-wrap">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-2 inline-flex w-full items-center justify-center rounded-md bg-purple-500 px-3 py-2 text-sm font-medium text-white hover:bg-purple-600 disabled:opacity-60"
          >
            {loading ? 'Skrái inn…' : 'Skrá inn'}
          </button>
        </form>
      </div>
    </div>
  )
}
