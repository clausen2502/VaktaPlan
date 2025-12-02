import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { API_BASE_URL } from '../config'
import ScheduleShell from '../components/schedule/ScheduleShell'
import WeeklyTemplateEditor from '../components/schedule/WeeklyTemplateEditor'
import type {
  Schedule,
  Shift,
  ShiftAssignment,
  Employee,
} from '../types/schedule'

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

  async function loadAllForSchedule(scheduleId: string) {
    try {
      setError(null)
      setLoading(true)

      const token = getTokenOrThrow()
      const headers = { Authorization: `Bearer ${token}` }

      const [schedRes, shiftsRes, assignmentsRes, employeesRes] =
        await Promise.all([
          fetch(`${API_BASE_URL}/schedules/${scheduleId}`, { headers }),
          fetch(`${API_BASE_URL}/shifts?schedule_id=${scheduleId}`, {
            headers,
          }),
          fetch(`${API_BASE_URL}/assignments`, { headers }),
          fetch(`${API_BASE_URL}/employees`, { headers }),
        ])

      if (!schedRes.ok) throw new Error(await schedRes.text())
      if (!shiftsRes.ok) throw new Error(await shiftsRes.text())
      if (!assignmentsRes.ok) throw new Error(await assignmentsRes.text())
      if (!employeesRes.ok) throw new Error(await employeesRes.text())

      const schedJson = (await schedRes.json()) as Schedule
      const shiftsJson = (await shiftsRes.json()) as Shift[]
      const assignmentsJson = (await assignmentsRes.json()) as {
        shift_id: number
        employee_id: number
      }[]
      const employeesJson = (await employeesRes.json()) as Employee[]

      setSchedule(schedJson)

      const employeeNameById: Record<number, string> = {}
      for (const emp of employeesJson) {
        employeeNameById[emp.id] = emp.display_name
      }

      const assignmentsByShiftId: Record<number, ShiftAssignment[]> = {}
      for (const a of assignmentsJson) {
        const name =
          employeeNameById[a.employee_id] ??
          `Starfsmaður #${a.employee_id}`

        if (!assignmentsByShiftId[a.shift_id]) {
          assignmentsByShiftId[a.shift_id] = []
        }
        assignmentsByShiftId[a.shift_id].push({
          employee_id: a.employee_id,
          employee_name: name,
        })
      }

      const shiftsWithAssignments: Shift[] = shiftsJson.map((sh) => ({
        ...sh,
        assignments: assignmentsByShiftId[sh.id] ?? [],
      }))

      setShifts(shiftsWithAssignments)
    } catch (err) {
      console.error(err)
      setError(
        err instanceof Error ? err.message : 'Ekki tókst að sækja plan.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!id) {
      setError('No schedule id.')
      setLoading(false)
      return
    }
    loadAllForSchedule(id)
  }, [id])

  async function handleReloadAfterAutoAssign() {
    if (!id) return
    await loadAllForSchedule(id)
  }

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

  // ----- PUBLISH --------------------------------------------------------
  async function handlePublishSchedule(s: Schedule) {
    const ok = window.confirm(
      `Birta planið "${s.name ?? ''}"?\nStarfsmenn munu sjá þetta sem lokað plan.`,
    )
    if (!ok) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(
        `${API_BASE_URL}/schedules/${s.id}/publish`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        },
      )

      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || `Publish failed with status ${res.status}`)
      }

      const updated = (await res.json()) as Schedule
      setSchedule(updated)
      window.alert('Planið var birt.')
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að birta planið.')
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
    <>
      <WeeklyTemplateEditor
        scheduleId={schedule.id}
        rangeStart={schedule.range_start}
        rangeEnd={schedule.range_end}
        onShiftsUpdated={(_fresh) => {
          if (id) void loadAllForSchedule(id)
        }}
      />

      <ScheduleShell
        schedule={schedule}
        shifts={shifts}
        onEditSchedule={handleEditSchedule}
        onDeleteSchedule={handleDeleteSchedule}
        onReloadSchedule={handleReloadAfterAutoAssign}
        onPublishSchedule={handlePublishSchedule}
      />
    </>
  )
}
