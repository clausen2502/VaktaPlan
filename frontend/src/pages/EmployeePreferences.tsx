import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../config'

type Org = {
  id: number
  name: string
}

type Employee = {
  id: number
  display_name: string
}

type Preference = {
  id: number
  employee_id: number
  weekday: number
  start_time: string
  end_time: string
  location_id: number | null
  weight: number | null
  do_not_schedule: boolean
  notes: string | null
  active_start: string | null
  active_end: string | null
}

type Unavailability = {
  id: number
  employee_id: number
  start_at: string
  end_at: string
  reason: string | null
}

const weekdayLabels = ['Mán.', 'Þri.', 'Mið.', 'Fim.', 'Fös.', 'Lau.', 'Sun.']

function formatTime(hms: string | null | undefined) {
  if (!hms) return ''
  // "09:00:00" -> "09:00"
  return hms.slice(0, 5)
}

function formatDateTime(iso: string | null | undefined) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  const hours = String(d.getHours()).padStart(2, '0')
  const mins = String(d.getMinutes()).padStart(2, '0')
  return `${day}.${month}.${year} ${hours}:${mins}`
}

export default function EmployeePreferences() {
  const [org, setOrg] = useState<Org | null>(null)
  const [employees, setEmployees] = useState<Employee[]>([])
  const [preferences, setPreferences] = useState<Preference[]>([])
  const [unavailability, setUnavailability] = useState<Unavailability[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

        const headers = { Authorization: `Bearer ${token}` }

        const [orgRes, empRes, prefRes, unavailRes] = await Promise.all([
          fetch(`${API_BASE_URL}/organizations/me`, { headers }),
          fetch(`${API_BASE_URL}/employees`, { headers }),
          fetch(`${API_BASE_URL}/preferences`, { headers }),
          fetch(`${API_BASE_URL}/unavailability`, { headers }),
        ])

        if (!orgRes.ok) throw new Error(await orgRes.text())
        if (!empRes.ok) throw new Error(await empRes.text())
        if (!prefRes.ok) throw new Error(await prefRes.text())
        if (!unavailRes.ok) throw new Error(await unavailRes.text())

        setOrg((await orgRes.json()) as Org)
        setEmployees((await empRes.json()) as Employee[])
        setPreferences((await prefRes.json()) as Preference[])
        setUnavailability((await unavailRes.json()) as Unavailability[])
      } catch (err) {
        console.error(err)
        setError(
          err instanceof Error ? err.message : 'Eitthvað klikkaði við að sækja gögn.',
        )
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  function getTokenOrThrow() {
    const token = localStorage.getItem('vakta_token')
    if (!token) {
      throw new Error('No token found. Please log in again.')
    }
    return token
  }

  // ---------- PREFERENCES CRUD ---------------------------------------

  async function handleCreatePreference(emp: Employee) {
    const weekdayStr = window.prompt(
      `Vikudagur (0=Mán, 1=Þri, ..., 6=Sun) fyrir ${emp.display_name}?`,
      '0',
    )
    if (weekdayStr === null) return
    const weekday = Number(weekdayStr)
    if (Number.isNaN(weekday) || weekday < 0 || weekday > 6) {
      window.alert('Ógildur vikudagur.')
      return
    }

    const startTime = window.prompt('Upphafstími (HH:MM, t.d. 09:00):', '09:00')
    if (!startTime) return
    const endTime = window.prompt('Lok (HH:MM, t.d. 17:00):', '17:00')
    if (!endTime) return

    const doNot = window.confirm('Á þetta að vera harður blokk (má EKKI setja á vakt)?')
    const weightStr = doNot
      ? null
      : window.prompt('Vægi (0–5, tómt ef ekkert sérstakt):', '3')
    const notes = window.prompt('Athugasemd (má vera tómt):', '')

    const payload: any = {
      employee_id: emp.id,
      weekday,
      start_time: `${startTime}:00`,
      end_time: `${endTime}:00`,
      do_not_schedule: doNot,
      notes: notes && notes.trim() ? notes.trim() : null,
    }

    if (!doNot && weightStr && weightStr.trim() !== '') {
      payload.weight = Number(weightStr)
    }

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/preferences`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(await res.text())
      const created = (await res.json()) as Preference
      setPreferences((prev) => [...prev, created])
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að búa til ósk.')
    }
  }

  async function handleEditPreference(pref: Preference) {
    const baseLabel = `${weekdayLabels[pref.weekday]} ${formatTime(
      pref.start_time,
    )}-${formatTime(pref.end_time)}`

    const weightStr = window.prompt(
      `Nýtt vægi fyrir "${baseLabel}" (tómt = engin breyting):`,
      pref.weight !== null && pref.weight !== undefined
        ? String(pref.weight)
        : '',
    )
    const notes = window.prompt(
      `Ný athugasemd (tómt = engin breyting):`,
      pref.notes ?? '',
    )
    const toggleHard = window.confirm(
      'Viltu breyta hvort þetta sé harður blokk? (OK = víxla, Cancel = halda óbreyttu)',
    )

    const patch: any = {}

    if (weightStr !== null && weightStr.trim() !== '') {
      patch.weight = Number(weightStr)
    }
    if (notes !== null && notes !== pref.notes) {
      patch.notes = notes.trim() === '' ? null : notes.trim()
    }
    if (toggleHard) {
      patch.do_not_schedule = !pref.do_not_schedule
      if (patch.do_not_schedule) {
        patch.weight = null
      }
    }

    if (Object.keys(patch).length === 0) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/preferences/${pref.id}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(patch),
      })
      if (!res.ok) throw new Error(await res.text())
      const updated = (await res.json()) as Preference
      setPreferences((prev) =>
        prev.map((p) => (p.id === updated.id ? updated : p)),
      )
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að uppfæra ósk.')
    }
  }

  async function handleDeletePreference(pref: Preference) {
    const ok = window.confirm('Eyða þessari ósk?')
    if (!ok) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/preferences/${pref.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(await res.text())
      setPreferences((prev) => prev.filter((p) => p.id !== pref.id))
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að eyða ósk.')
    }
  }

  // ---------- UNAVAILABILITY CRUD -----------------------------------

  async function handleCreateUnavailability(emp: Employee) {
    const start = window.prompt(
      `Upphaf (ISO: 2025-10-22T09:00:00Z) fyrir ${emp.display_name}?`,
    )
    if (!start) return
    const end = window.prompt(
      'Lok (ISO: 2025-10-22T11:00:00Z):',
    )
    if (!end) return
    const reason = window.prompt('Ástæða (t.d. "Tannlæknir"):', '')

    const payload = {
      employee_id: emp.id,
      start_at: start,
      end_at: end,
      reason: reason && reason.trim() ? reason.trim() : null,
    }

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/unavailability`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(await res.text())
      const created = (await res.json()) as Unavailability
      setUnavailability((prev) => [...prev, created])
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að búa til ófáanleika.')
    }
  }

  async function handleEditUnavailability(item: Unavailability) {
    const start = window.prompt(
      'Nýtt upphaf (tómt = óbreytt):',
      item.start_at,
    )
    const end = window.prompt('Nýtt lok (tómt = óbreytt):', item.end_at)
    const reason = window.prompt(
      'Ný ástæða (tómt = óbreytt):',
      item.reason ?? '',
    )

    const patch: any = {}
    if (start !== null && start.trim() !== '' && start !== item.start_at) {
      patch.start_at = start
    }
    if (end !== null && end.trim() !== '' && end !== item.end_at) {
      patch.end_at = end
    }
    if (reason !== null && reason !== item.reason) {
      patch.reason = reason.trim() === '' ? null : reason.trim()
    }
    if (Object.keys(patch).length === 0) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(
        `${API_BASE_URL}/unavailability/${item.id}`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(patch),
        },
      )
      if (!res.ok) throw new Error(await res.text())
      const updated = (await res.json()) as Unavailability
      setUnavailability((prev) =>
        prev.map((u) => (u.id === updated.id ? updated : u)),
      )
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að uppfæra ófáanleika.')
    }
  }

  async function handleDeleteUnavailability(item: Unavailability) {
    const ok = window.confirm('Eyða þessum ófáanleika?')
    if (!ok) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(
        `${API_BASE_URL}/unavailability/${item.id}`,
        {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        },
      )
      if (!res.ok) throw new Error(await res.text())
      setUnavailability((prev) => prev.filter((u) => u.id !== item.id))
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að eyða ófáanleika.')
    }
  }

  // ---------- RENDER -------------------------------------------------

  if (loading) return <p>Sæki gögn…</p>
  if (error) return <p className="whitespace-pre-wrap text-red-400">{error}</p>

  return (
    <div className="org-page">
      {/* top header: org name + centered title */}
      <div className="org-page-top">
        <h1 className="org-org-name">{org?.name ?? 'Vinnustaðurinn minn'}</h1>
        <h2 className="org-page-title">Stillingar starfsmanna</h2>
        <div style={{ width: '120px' }} />
      </div>

      <section className="org-section">
        <div className="org-section-title-row">
          <h3 className="org-section-title">Starfsmenn, preferences og unavailabilities</h3>
          {/* (optional) could link to OrgOverview to add employees */}
        </div>

        {employees.length === 0 ? (
          <p className="text-sm text-slate-600">
            Engir starfsmenn skráðir ennþá.
          </p>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {employees.map((emp) => {
              const empPrefs = preferences.filter(
                (p) => p.employee_id === emp.id,
              )
              const empUnavail = unavailability.filter(
                (u) => u.employee_id === emp.id,
              )

              return (
                <div key={emp.id} className="text-sm">
                  <p className="org-item-name mb-2">{emp.display_name}</p>

                  {/* Preferences */}
                  <div className="mb-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-xs">
                        wishes / cl
                      </span>
                      <button
                        type="button"
                        className="org-add-link"
                        onClick={() => handleCreatePreference(emp)}
                      >
                        Bæta við ósk
                      </button>
                    </div>

                    {empPrefs.length === 0 ? (
                      <p className="text-xs text-slate-500">
                        Engar óskir skráðar.
                      </p>
                    ) : (
                      <ul className="space-y-1">
                        {empPrefs.map((pref) => {
                          const label = `${weekdayLabels[pref.weekday]} ${formatTime(
                            pref.start_time,
                          )}-${formatTime(pref.end_time)}`
                          return (
                            <li key={pref.id}>
                              <span>
                                {label}{' '}
                                {pref.do_not_schedule
                                  ? '(harður blokk)'
                                  : pref.weight != null
                                    ? `(vægi ${pref.weight})`
                                    : ''}
                                {pref.notes ? ` – ${pref.notes}` : ''}
                              </span>
                              <span className="org-item-actions space-x-3 ml-2">
                                <button
                                  type="button"
                                  className="hover:underline"
                                  onClick={() => handleEditPreference(pref)}
                                >
                                  Uppfæra
                                </button>
                                <button
                                  type="button"
                                  className="hover:underline"
                                  onClick={() =>
                                    handleDeletePreference(pref)
                                  }
                                >
                                  Eyða
                                </button>
                              </span>
                            </li>
                          )
                        })}
                      </ul>
                    )}
                  </div>

                  {/* Unavailability */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-xs">
                        Ófáanleiki
                      </span>
                      <button
                        type="button"
                        className="org-add-link"
                        onClick={() => handleCreateUnavailability(emp)}
                      >
                        Bæta við ófáanleika
                      </button>
                    </div>

                    {empUnavail.length === 0 ? (
                      <p className="text-xs text-slate-500">
                        Engin ófáanleiki skráður.
                      </p>
                    ) : (
                      <ul className="space-y-1">
                        {empUnavail.map((u) => (
                          <li key={u.id}>
                            <span>
                              {formatDateTime(u.start_at)} –{' '}
                              {formatDateTime(u.end_at)}
                              {u.reason ? ` (${u.reason})` : ''}
                            </span>
                            <span className="org-item-actions space-x-3 ml-2">
                              <button
                                type="button"
                                className="hover:underline"
                                onClick={() => handleEditUnavailability(u)}
                              >
                                Uppfæra
                              </button>
                              <button
                                type="button"
                                className="hover:underline"
                                onClick={() =>
                                  handleDeleteUnavailability(u)
                                }
                              >
                                Eyða
                              </button>
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
