import { useEffect, useState, type FC } from 'react'
import { API_BASE_URL } from '../../config'
import type { Shift } from '../../types/schedule'

type WeeklyTemplateRow = {
  start_time: string   // "HH:MM:SS"
  end_time: string     // "HH:MM:SS"
  required_staff_count: number
  notes?: string
  location_id?: number | null
  role_id?: number | null
}

type WeeklyTemplateByDay = Record<number, WeeklyTemplateRow[]>

type LocationOption = { id: number; name: string }
type JobRoleOption = { id: number; name: string }

type Props = {
  scheduleId: number
  rangeStart: string   // YYYY-MM-DD
  rangeEnd: string     // YYYY-MM-DD
  onShiftsUpdated?: (shifts: Shift[]) => void
}

const weekdayOptions = [
  { value: 0, label: 'Mán.' },
  { value: 1, label: 'Þri.' },
  { value: 2, label: 'Mið.' },
  { value: 3, label: 'Fim.' },
  { value: 4, label: 'Fös.' },
  { value: 5, label: 'Lau.' },
  { value: 6, label: 'Sun.' },
]

function makeEmptyRow(): WeeklyTemplateRow {
  return {
    start_time: '09:00:00',
    end_time: '17:00:00',
    required_staff_count: 1,
    notes: '',
    location_id: undefined,
    role_id: undefined,
  }
}

function makeEmptyTemplate(): WeeklyTemplateByDay {
  return {
    0: [],
    1: [],
    2: [],
    3: [],
    4: [],
    5: [],
    6: [],
  }
}

const WeeklyTemplateEditor: FC<Props> = ({
  scheduleId,
  rangeStart,
  rangeEnd,
  onShiftsUpdated,
}) => {
  const [byDay, setByDay] = useState<WeeklyTemplateByDay>(makeEmptyTemplate)
  const [locations, setLocations] = useState<LocationOption[]>([])
  const [jobRoles, setJobRoles] = useState<JobRoleOption[]>([])

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)

  // default generate range = schedule range, but editable
  const [startDate, setStartDate] = useState(rangeStart)
  const [endDate, setEndDate] = useState(rangeEnd)

  // Load locations + job roles once
  useEffect(() => {
    async function loadLookups() {
      try {
        const token = localStorage.getItem('vakta_token')
        if (!token) return

        const [locRes, roleRes] = await Promise.all([
          fetch(`${API_BASE_URL}/locations`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_BASE_URL}/jobroles`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ])

        if (locRes.ok) {
          const locJson = await locRes.json()
          setLocations(
            Array.isArray(locJson)
              ? locJson
              : Array.isArray(locJson.items)
              ? locJson.items
              : [],
          )
        }

        if (roleRes.ok) {
          const roleJson = await roleRes.json()
          setJobRoles(
            Array.isArray(roleJson)
              ? roleJson
              : Array.isArray(roleJson.items)
              ? roleJson.items
              : [],
          )
        }
      } catch (e) {
        console.error('Failed to load locations / job roles', e)
      }
    }

    loadLookups()
  }, [])

  // Load existing template from API and map into 7 fixed days
  useEffect(() => {
    async function loadTemplate() {
      try {
        setError(null)
        setInfo(null)
        setLoading(true)

        const token = localStorage.getItem('vakta_token')
        if (!token) {
          setError('Enginn token fannst, vinsamlegast skráðu þig inn aftur.')
          setLoading(false)
          return
        }

        const res = await fetch(
          `${API_BASE_URL}/schedules/${scheduleId}/weekly-template`,
          {
            headers: { Authorization: `Bearer ${token}` },
          },
        )

        if (!res.ok) {
          const text = await res.text()
          throw new Error(text || `Villa við að sækja sniðmát (${res.status})`)
        }

        const json = await res.json()
        const rawItems: any[] = Array.isArray(json)
          ? json
          : Array.isArray(json.items)
          ? json.items
          : []

        const initial = makeEmptyTemplate()

        for (const it of rawItems) {
          const weekday: number =
            typeof it.weekday === 'number' ? it.weekday : 0
          if (!(weekday in initial)) continue

          initial[weekday].push({
            start_time: it.start_time ?? '09:00:00',
            end_time: it.end_time ?? '17:00:00',
            required_staff_count:
              typeof it.required_staff_count === 'number'
                ? it.required_staff_count
                : 1,
            notes: it.notes ?? '',
            location_id:
              typeof it.location_id === 'number' ? it.location_id : null,
            role_id: typeof it.role_id === 'number' ? it.role_id : null,
          })
        }

        setByDay(initial)
      } catch (err) {
        console.error(err)
        setError(
          err instanceof Error
            ? err.message
            : 'Ekki tókst að sækja vikulegt sniðmát.',
        )
      } finally {
        setLoading(false)
      }
    }

    loadTemplate()
  }, [scheduleId])

  function updateRow(
    weekday: number,
    rowIndex: number,
    patch: Partial<WeeklyTemplateRow>,
  ) {
    setByDay((prev) => {
      const dayRows = prev[weekday] ?? []
      const nextRows = dayRows.map((row, i) =>
        i === rowIndex ? { ...row, ...patch } : row,
      )
      return { ...prev, [weekday]: nextRows }
    })
  }

  function addRow(weekday: number) {
    setByDay((prev) => {
      const dayRows = prev[weekday] ?? []
      return { ...prev, [weekday]: [...dayRows, makeEmptyRow()] }
    })
  }

  function removeRow(weekday: number, rowIndex: number) {
    setByDay((prev) => {
      const dayRows = prev[weekday] ?? []
      const nextRows = dayRows.filter((_, i) => i !== rowIndex)
      return { ...prev, [weekday]: nextRows }
    })
  }

  function validateTemplateComplete(): boolean {
    for (const [, rows] of Object.entries(byDay)) {
      for (const r of rows) {
        const hasLocation = typeof r.location_id === 'number' && r.location_id > 0
        const hasRole = typeof r.role_id === 'number' && r.role_id > 0
        if (!hasLocation || !hasRole) {
          setError(
            'Allar vaktalínur í sniðmátinu þurfa að hafa bæði staðsetningu og ' +
              'starfsheiti áður en hægt er að vista eða búa til vaktir.',
          )
          return false
        }
      }
    }
    return true
  }

  async function handleSaveTemplate() {
    try {
      setSaving(true)
      setError(null)
      setInfo(null)

      if (!validateTemplateComplete()) {
        return
      }

      const token = localStorage.getItem('vakta_token')
      if (!token) {
        setError('Enginn token fannst, vinsamlegast skráðu þig inn aftur.')
        return
      }

      // Flatten byDay to items[] for backend
      const items = Object.entries(byDay).flatMap(
        ([weekdayStr, rows]): any[] => {
          const weekday = Number(weekdayStr)
          return rows.map((r) => ({
            weekday,
            start_time: r.start_time,
            end_time: r.end_time,
            required_staff_count: r.required_staff_count,
            ...(r.notes ? { notes: r.notes } : {}),
            location_id: r.location_id,
            role_id: r.role_id,
          }))
        },
      )

      const payload = { items }

      const res = await fetch(
        `${API_BASE_URL}/schedules/${scheduleId}/weekly-template`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        },
      )

      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || `Villa við að vista sniðmát (${res.status})`)
      }

      setInfo('Sniðmát vistað.')
    } catch (err) {
      console.error(err)
      setError(
        err instanceof Error
          ? err.message
          : 'Ekki tókst að vista vikulegt sniðmát.',
      )
    } finally {
      setSaving(false)
    }
  }

  async function handleGenerateShifts() {
    try {
      setGenerating(true)
      setError(null)
      setInfo(null)

      if (!validateTemplateComplete()) {
        return
      }

      const token = localStorage.getItem('vakta_token')
      if (!token) {
        setError('Enginn token fannst, vinsamlegast skráðu þig inn aftur.')
        return
      }

      // 1) call generate endpoint
      const res = await fetch(
        `${API_BASE_URL}/schedules/${scheduleId}/weekly-template/generate`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            start_date: startDate,
            end_date: endDate,
            policy: 'replace',
          }),
        },
      )

      if (!res.ok) {
        const text = await res.text()
        throw new Error(
          text || `Villa við að búa til vaktir úr sniðmáti (${res.status})`,
        )
      }

      // 2) fetch updated shifts
      const shiftsRes = await fetch(
        `${API_BASE_URL}/shifts?schedule_id=${scheduleId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      )

      if (!shiftsRes.ok) {
        const text = await shiftsRes.text()
        throw new Error(text || 'Vaktir voru búnar til en ekki tókst að sækja þær.')
      }

      const newShifts = (await shiftsRes.json()) as Shift[]
      if (onShiftsUpdated) onShiftsUpdated(newShifts)

      setInfo('Vaktir búnar til úr sniðmáti.')
    } catch (err) {
      console.error(err)
      setError(
        err instanceof Error
          ? err.message
          : 'Ekki tókst að búa til vaktir úr sniðmáti.',
      )
    } finally {
      setGenerating(false)
    }
  }

  return (
    <section className="mb-6 border border-black rounded-xl p-4">
      <div className="flex items-center justify-between mb-3 gap-4">
        <h3 className="text-lg font-semibold">Vikulegt sniðmát</h3>

        <div className="flex flex-wrap items-center gap-3 text-sm">
          <div className="flex items-center gap-2">
            <label htmlFor="start" className="whitespace-nowrap">
              Byrjar:
            </label>
            <input
              id="start"
              type="date"
              className="border border-black px-2 py-1 text-sm"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="end" className="whitespace-nowrap">
              Endar:
            </label>
            <input
              id="end"
              type="date"
              className="border border-black px-2 py-1 text-sm"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>

          <button
            type="button"
            onClick={handleGenerateShifts}
            disabled={generating || loading}
            className="border border-black px-3 py-1 text-sm disabled:opacity-60"
          >
            {generating ? 'Bý til vaktir…' : 'Búa til vaktir úr sniðmáti'}
          </button>
        </div>
      </div>

      {loading && <p className="text-sm mb-2">Sæki vikulegt sniðmát…</p>}

      {error && (
        <p className="text-sm text-red-600 mb-2 whitespace-pre-wrap">
          {error}
        </p>
      )}

      {info && !error && (
        <p className="text-sm text-green-700 mb-2 whitespace-pre-wrap">
          {info}
        </p>
      )}

      {/* 7 fixed days, each with its own shift rows */}
      {!loading && (
        <div className="grid md:grid-cols-4 lg:grid-cols-7 gap-4 text-sm">
          {weekdayOptions.map((day) => {
            const rows = byDay[day.value] ?? []
            return (
              <div
                key={day.value}
                className="border border-black rounded-lg p-2 flex flex-col"
              >
                <div className="font-semibold mb-2">{day.label}</div>

                {rows.length === 0 && (
                  <p className="text-xs mb-2 text-gray-600">
                    Engar vaktir skilgreindar.
                  </p>
                )}

                {rows.map((row, idx) => (
                  <div
                    key={idx}
                    className="mb-2 border border-black rounded px-1 py-1"
                  >
                    <div className="flex items-center gap-1 mb-1">
                      <input
                        type="time"
                        className="border border-black px-1 py-[2px] text-xs bg-white w-[70px]"
                        value={row.start_time.slice(0, 5)}
                        onChange={(e) =>
                          updateRow(day.value, idx, {
                            start_time: `${e.target.value}:00`,
                          })
                        }
                      />
                      <span className="text-xs">–</span>
                      <input
                        type="time"
                        className="border border-black px-1 py-[2px] text-xs bg-white w-[70px]"
                        value={row.end_time.slice(0, 5)}
                        onChange={(e) =>
                          updateRow(day.value, idx, {
                            end_time: `${e.target.value}:00`,
                          })
                        }
                      />
                    </div>

                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs">Fjöldi:</span>
                      <input
                        type="number"
                        min={1}
                        className="border border-black px-1 py-[2px] text-xs w-16 bg-white"
                        value={row.required_staff_count}
                        onChange={(e) =>
                          updateRow(day.value, idx, {
                            required_staff_count: Number(
                              e.target.value || 1,
                            ),
                          })
                        }
                      />
                    </div>

                    <div className="flex flex-col gap-1 mb-1">
                      <label className="text-xs">Staðsetning</label>
                      <select
                        className="border border-black px-1 py-[2px] text-xs bg-white w-full"
                        value={row.location_id ?? ''}
                        onChange={(e) =>
                          updateRow(day.value, idx, {
                            location_id: e.target.value
                              ? Number(e.target.value)
                              : undefined,
                          })
                        }
                      >
                        <option value="">Velja stað</option>
                        {locations.map((loc) => (
                          <option key={loc.id} value={loc.id}>
                            {loc.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="flex flex-col gap-1 mb-1">
                      <label className="text-xs">Starfsheiti</label>
                      <select
                        className="border border-black px-1 py-[2px] text-xs bg-white w-full"
                        value={row.role_id ?? ''}
                        onChange={(e) =>
                          updateRow(day.value, idx, {
                            role_id: e.target.value
                              ? Number(e.target.value)
                              : undefined,
                          })
                        }
                      >
                        <option value="">Velja hlutverk</option>
                        {jobRoles.map((role) => (
                          <option key={role.id} value={role.id}>
                            {role.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <input
                      type="text"
                      placeholder="Athugasemd"
                      className="border border-black px-1 py-[2px] text-xs w-full bg-white mb-1"
                      value={row.notes ?? ''}
                      onChange={(e) =>
                        updateRow(day.value, idx, { notes: e.target.value })
                      }
                    />

                    <button
                      type="button"
                      onClick={() => removeRow(day.value, idx)}
                      className="text-[11px] underline"
                    >
                      Eyða vakt
                    </button>
                  </div>
                ))}

                <button
                  type="button"
                  onClick={() => addRow(day.value)}
                  className="mt-auto border border-black px-2 py-1 text-xs"
                >
                  Bæta við vakt
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* Save button below the grid */}
      {!loading && (
        <div className="flex justify-end mt-4">
          <button
            type="button"
            onClick={handleSaveTemplate}
            disabled={saving}
            className="border border-black px-3 py-1 text-sm disabled:opacity-60"
          >
            {saving ? 'Vista…' : 'Vista sniðmát'}
          </button>
        </div>
      )}
    </section>
  )
}

export default WeeklyTemplateEditor
