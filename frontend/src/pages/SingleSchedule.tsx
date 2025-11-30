import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { API_BASE_URL } from '../config'
import ScheduleShell from '../components/schedule/ScheduleShell'
import AutoAssignButton from '../components/schedule/AutoAssignButton'
import type { Schedule, Shift } from '../types/schedule'

export default function SingleSchedule() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [schedule, setSchedule] = useState<Schedule | null>(null)
  const [shifts, setShifts] = useState<Shift[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  function getTokenOrThrow() {
    const token = localStorage.getItem('vakta_token')
    if (!token) {
      throw new Error('No token found. Please log in again.')
    }
    return token
  }

  useEffect(() => {
    async function load() {
      try {
        setError(null)
        setLoading(true)

        const token = localStorage.getItem('vakta_token')
        if (!token || !id) {
          setError('No token or schedule id.')
          setLoading(false)
          return
        }

        const headers = { Authorization: `Bearer ${token}` }

        const [schedRes, shiftsRes] = await Promise.all([
          fetch(`${API_BASE_URL}/schedules/${id}`, { headers }),
          fetch(`${API_BASE_URL}/shifts?schedule_id=${id}`, { headers }),
        ])

        if (!schedRes.ok) throw new Error(await schedRes.text())
        if (!shiftsRes.ok) throw new Error(await shiftsRes.text())

        setSchedule((await schedRes.json()) as Schedule)
        setShifts((await shiftsRes.json()) as Shift[])
      } catch (err) {
        console.error(err)
        setError(
          err instanceof Error ? err.message : 'Ekki tókst að sækja plan.',
        )
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [id])

  // ----- EDIT -----------------------------------------------------------
  async function handleEditSchedule(s: Schedule) {
    const newName = window.prompt('Nýtt nafn fyrir planið?', s.name ?? '')
    if (!newName) return
    const trimmed = newName.trim()
    if (trimmed === '' || trimmed === s.name) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/schedules/${s.id}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: trimmed }),
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || `PATCH failed with status ${res.status}`)
      }

      const updated = (await res.json()) as Schedule
      setSchedule(updated)
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að uppfæra planið.')
    }
  }

  // ----- DELETE ---------------------------------------------------------
  async function handleDeleteSchedule(s: Schedule) {
    const ok = window.confirm(`Eyða planinu "${s.name ?? ''}"?`)
    if (!ok) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/schedules/${s.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || `DELETE failed with status ${res.status}`)
      }

      navigate('/schedules')
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að eyða plani.')
    }
  }

  if (loading) return <div>Sæki plan…</div>
  if (error || !schedule) return <div>{error ?? 'Plan fannst ekki.'}</div>

  return (
    <div className="mt-4">
      {/* Header row with auto-assign button */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold">{schedule.name}</h2>
          <p className="text-sm">
            {schedule.range_start} – {schedule.range_end}
          </p>
        </div>

        <AutoAssignButton
          scheduleId={schedule.id}
          rangeStart={schedule.range_start}
          rangeEnd={schedule.range_end}
          onShiftsUpdated={setShifts}
        />
      </div>

      <ScheduleShell
        schedule={schedule}
        shifts={shifts}
        onEditSchedule={handleEditSchedule}
        onDeleteSchedule={handleDeleteSchedule}
      />
    </div>
  )
}
