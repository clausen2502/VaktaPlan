// src/pages/OrgOverviewPage.tsx
import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../config'

type Employee = {
  id: number
  display_name: string
}

type JobRole = {
  id: number
  name: string
}

type Location = {
  id: number
  name: string
}

type Org = {
  id: number
  name: string
}

export default function OrgOverview() {
  const [org, setOrg] = useState<Org | null>(null)
  const [employees, setEmployees] = useState<Employee[]>([])
  const [jobroles, setJobroles] = useState<JobRole[]>([])
  const [locations, setLocations] = useState<Location[]>([])
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

        const [empRes, roleRes, locRes, orgRes] = await Promise.all([
          fetch(`${API_BASE_URL}/employees`, { headers }),
          fetch(`${API_BASE_URL}/jobroles`, { headers }),
          fetch(`${API_BASE_URL}/locations`, { headers }),
          fetch(`${API_BASE_URL}/organizations/me`, { headers }),
        ])

        if (!empRes.ok) throw new Error(await empRes.text())
        if (!roleRes.ok) throw new Error(await roleRes.text())
        if (!locRes.ok) throw new Error(await locRes.text())
        if (!orgRes.ok) throw new Error(await orgRes.text())

        setEmployees((await empRes.json()) as Employee[])
        setJobroles((await roleRes.json()) as JobRole[])
        setLocations((await locRes.json()) as Location[])
        setOrg((await orgRes.json()) as Org)
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

  // ----- CREATE ---------------------------------------------------------

  async function handleCreateLocation() {
    const name = window.prompt('Nafn á nýjum vinnustað?')
    if (!name || !name.trim()) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/locations`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: name.trim() }),
      })
      if (!res.ok) throw new Error(await res.text())
      const created = (await res.json()) as Location
      setLocations((prev) => [...prev, created])
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að búa til vinnustað.')
    }
  }

  async function handleCreateRole() {
    const name = window.prompt('Nafn á nýju starfshlutverki?')
    if (!name || !name.trim()) return

    const capInput = window.prompt(
      'Vikulegur hámarksstundafjöldi (má vera tómt, t.d. 40):',
      '40',
    )
    const weeklyCap =
      capInput && capInput.trim() !== '' ? Number(capInput.trim()) : null

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/jobroles`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: name.trim(),
          weekly_hours_cap: weeklyCap,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const created = (await res.json()) as JobRole
      setJobroles((prev) => [...prev, created])
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að búa til starfshlutverk.')
    }
  }

  async function handleCreateEmployee() {
    const name = window.prompt('Nafn á nýjum starfsmanni?')
    if (!name || !name.trim()) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/employees`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ display_name: name.trim() }),
      })
      if (!res.ok) throw new Error(await res.text())
      const created = (await res.json()) as Employee
      setEmployees((prev) => [...prev, created])
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að búa til starfsmann.')
    }
  }

  // ----- EDIT / DELETE --------------------------------------------------

  async function handleEditLocation(loc: Location) {
    const newName = window.prompt('Nýtt nafn fyrir vinnustað:', loc.name)
    if (!newName || newName.trim() === loc.name) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/locations/${loc.id}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: newName.trim() }),
      })
      if (!res.ok) throw new Error(await res.text())

      setLocations((prev) =>
        prev.map((l) => (l.id === loc.id ? { ...l, name: newName.trim() } : l)),
      )
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að uppfæra vinnustað.')
    }
  }

  async function handleDeleteLocation(loc: Location) {
    const ok = window.confirm(`Eyða vinnustaðnum "${loc.name}"?`)
    if (!ok) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/locations/${loc.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(await res.text())

      setLocations((prev) => prev.filter((l) => l.id !== loc.id))
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að eyða vinnustað.')
    }
  }

  async function handleEditRole(role: JobRole) {
    const newName = window.prompt('Nýtt nafn fyrir starfshlutverk:', role.name)
    if (!newName || newName.trim() === role.name) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/jobroles/${role.id}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: newName.trim() }),
      })
      if (!res.ok) throw new Error(await res.text())

      setJobroles((prev) =>
        prev.map((r) => (r.id === role.id ? { ...r, name: newName.trim() } : r)),
      )
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að uppfæra starfshlutverk.')
    }
  }

  async function handleDeleteRole(role: JobRole) {
    const ok = window.confirm(`Eyða starfshlutverki "${role.name}"?`)
    if (!ok) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/jobroles/${role.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(await res.text())

      setJobroles((prev) => prev.filter((r) => r.id !== role.id))
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að eyða starfshlutverki.')
    }
  }

  async function handleEditEmployee(emp: Employee) {
    const newName = window.prompt('Nýtt nafn fyrir starfsmann:', emp.display_name)
    if (!newName || newName.trim() === emp.display_name) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/employees/${emp.id}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ display_name: newName.trim() }),
      })
      if (!res.ok) throw new Error(await res.text())

      setEmployees((prev) =>
        prev.map((e) =>
          e.id === emp.id ? { ...e, display_name: newName.trim() } : e,
        ),
      )
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að uppfæra starfsmann.')
    }
  }

  async function handleDeleteEmployee(emp: Employee) {
    const ok = window.confirm(`Eyða starfsmanni "${emp.display_name}"?`)
    if (!ok) return

    try {
      const token = getTokenOrThrow()
      const res = await fetch(`${API_BASE_URL}/employees/${emp.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(await res.text())

      setEmployees((prev) => prev.filter((e) => e.id !== emp.id))
    } catch (err) {
      console.error(err)
      window.alert('Tókst ekki að eyða starfsmanni.')
    }
  }

  // ----- RENDER ---------------------------------------------------------

  if (loading) return <p>Sæki vinnustaðagögn…</p>
  if (error) return <p className="whitespace-pre-wrap text-red-400">{error}</p>

  return (
    <div className="org-page">
      {/* top: org name on the left, page title centered */}
      <div className="org-page-top">
        <h1 className="org-org-name">{org?.name ?? 'Vinnustaðurinn minn'}</h1>
        <h2 className="org-page-title">Minn vinnustaður</h2>
        {/* empty div just to balance the flex so title stays centered */}
        <div style={{ width: '120px' }} />
      </div>

      {/* two columns */}
      <div className="org-page-columns">
        {/* LEFT: locations + job roles */}
        <div className="org-col-left">
          {/* Vinnustaðir */}
          <section className="org-section">
            <div className="org-section-title-row">
              <h3 className="org-section-title">Vinnustaðir</h3>
              <button
                type="button"
                className="org-add-link"
                onClick={handleCreateLocation}
              >
                Bæta við vinnustað
              </button>
            </div>

            {locations.length === 0 ? (
              <p className="text-sm text-slate-600">
                Engir vinnustaðir skráðir ennþá.
              </p>
            ) : (
              <div className="grid gap-6 md:grid-cols-3">
                {locations.map((loc) => (
                  <div key={loc.id} className="text-sm">
                    <p className="org-item-name">{loc.name}</p>
                    <div className="org-item-actions space-x-3">
                      <button
                        type="button"
                        className="hover:underline"
                        onClick={() => handleEditLocation(loc)}
                      >
                        Uppfæra
                      </button>
                      <button
                        type="button"
                        className="hover:underline"
                        onClick={() => handleDeleteLocation(loc)}
                      >
                        Eyða
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Starfshlutverk */}
          <section className="org-section">
            <div className="org-section-title-row">
              <h3 className="org-section-title">Starfshlutverk</h3>
              <button
                type="button"
                className="org-add-link"
                onClick={handleCreateRole}
              >
                Bæta við starfshlutverki
              </button>
            </div>

            {jobroles.length === 0 ? (
              <p className="text-sm text-slate-600">
                Engin starfshlutverk skráð ennþá.
              </p>
            ) : (
              <div className="grid gap-6 md:grid-cols-2">
                {jobroles.map((role) => (
                  <div key={role.id} className="text-sm">
                    <p className="org-item-name">{role.name}</p>
                    <div className="org-item-actions space-x-3">
                      <button
                        type="button"
                        className="hover:underline"
                        onClick={() => handleEditRole(role)}
                      >
                        Uppfæra
                      </button>
                      <button
                        type="button"
                        className="hover:underline"
                        onClick={() => handleDeleteRole(role)}
                      >
                        Eyða
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        {/* RIGHT: employees */}
        <div className="org-col-right">
          <section className="org-section">
            <div className="org-section-title-row">
              <h3 className="org-section-title">Starfsmenn</h3>
              <button
                type="button"
                className="org-add-link"
                onClick={handleCreateEmployee}
              >
                Bæta við starfsmanni
              </button>
            </div>

            {employees.length === 0 ? (
              <p className="text-sm text-slate-600">
                Engir starfsmenn skráðir ennþá.
              </p>
            ) : (
              <div className="grid gap-6 md:grid-cols-3">
                {employees.map((emp) => (
                  <div key={emp.id} className="text-sm">
                    <p className="org-item-name">{emp.display_name}</p>
                    <div className="org-item-actions mt-1 space-x-3">
                      <button
                        type="button"
                        className="hover:underline"
                        onClick={() => handleEditEmployee(emp)}
                      >
                        Uppfæra
                      </button>
                      <button
                        type="button"
                        className="hover:underline"
                        onClick={() => handleDeleteEmployee(emp)}
                      >
                        Eyða
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
