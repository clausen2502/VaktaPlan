import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

const API_BASE_URL = 'http://127.0.0.1:8000/api'

type Schedule = {
  id: number
  name: string
  range_start: string
  range_end: string
  status: string
  version: number
}

export default function Schedules() {
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const navigate = useNavigate()

  useEffect(() => {
    async function load() {
      try {
        setError(null)
        setLoading(true)

        const token = localStorage.getItem('vakta_token')
        if (!token) {
          setError('No token found. Please log in again.')
          setLoading(false)
          return
        }

        const res = await fetch(`${API_BASE_URL}/schedules`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (!res.ok) {
          const text = await res.text()
          throw new Error(text || `Failed with status ${res.status}`)
        }

        const data = (await res.json()) as Schedule[]
        setSchedules(data)
      } catch (err) {
        console.error(err)
        setError(
          err instanceof Error ? err.message : 'Failed to fetch schedules.',
        )
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  async function handleCreateSchedule() {
    const name = window.prompt('Nafn á nýju vaktaplani?')
    if (!name || !name.trim()) return

    const rangeStart =
      window.prompt('Upphafsdagsetning (YYYY-MM-DD):', '2025-10-01') ?? ''
    const rangeEnd =
      window.prompt('Lokadagsetning (YYYY-MM-DD):', '2025-10-07') ?? ''

    if (!rangeStart.trim() || !rangeEnd.trim()) return

    try {
      const token = localStorage.getItem('vakta_token')
      if (!token) {
        window.alert('Enginn token fannst, skráðu þig inn aftur.')
        return
      }

      const res = await fetch(`${API_BASE_URL}/schedules`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: name.trim(),
          range_start: rangeStart.trim(),
          range_end: rangeEnd.trim(),
          version: 1,
        }),
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || `Create failed with status ${res.status}`)
      }

      const created = (await res.json()) as Schedule

      // Option 1: go straight into the new plan
      navigate(`/schedules/${created.id}`)

      // Option 2 (if you prefer staying on list and seeing it appear):
      // setSchedules((prev) => [...prev, created])
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að búa til nýtt vaktaplan.')
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 px-6 py-8">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Mín vaktaplön</h1>

        <button
          type="button"
          onClick={handleCreateSchedule}
          className="rounded-md border border-white/20 px-3 py-1.5 text-sm hover:bg-white/10"
        >
          Búa til nýtt vaktaplan
        </button>
      </div>

      {loading && <p className="text-sm text-slate-300">Sæki vaktaplön…</p>}

      {error && (
        <p className="text-sm text-red-400 whitespace-pre-wrap mb-4">
          {error}
        </p>
      )}

      {!loading && !error && schedules.length === 0 && (
        <p className="text-sm text-slate-300">
          Engin vaktaplön fundust. Búðu til plön með
          &nbsp;„Búa til nýtt vaktaplan“.
        </p>
      )}

      {!loading && !error && schedules.length > 0 && (
        <table className="w-full text-sm border border-white/10 border-collapse">
          <thead className="bg-white/5">
            <tr>
              <th className="border border-white/10 px-2 py-1 text-left">ID</th>
              <th className="border border-white/10 px-2 py-1 text-left">
                Nafn
              </th>
              <th className="border border-white/10 px-2 py-1 text-left">
                Tímabil
              </th>
              <th className="border border-white/10 px-2 py-1 text-left">
                Staða
              </th>
              <th className="border border-white/10 px-2 py-1 text-left">
                Útgáfa
              </th>
            </tr>
          </thead>
          <tbody>
            {schedules.map((s) => (
              <tr
                key={s.id}
                className="hover:bg-white/10 cursor-pointer"
                onClick={() => navigate(`/schedules/${s.id}`)}
              >
                <td className="border border-white/10 px-2 py-1">{s.id}</td>
                <td className="border border-white/10 px-2 py-1 font-medium">
                  {s.name}
                </td>
                <td className="border border-white/10 px-2 py-1">
                  {s.range_start} - {s.range_end}
                </td>
                <td className="border border-white/10 px-2 py-1">
                  {s.status}
                </td>
                <td className="border border-white/10 px-2 py-1">
                  {s.version}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
