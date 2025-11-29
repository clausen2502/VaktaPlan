import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../config'
import Hero from '../components/dashboard/Hero'

type Org = {
  id: number
  name: string
  timezone: string | null
}

type Schedule = {
  id: number
  range_start: string
  range_end: string
  status: string
}

export default function Dashboard() {
  const [org, setOrg] = useState<Org | null>(null)
  const [schedules, setSchedules] = useState<Schedule[]>([])
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

        const orgRes = await fetch(`${API_BASE_URL}/organizations/me`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!orgRes.ok) throw new Error(await orgRes.text())
        const orgData: Org = await orgRes.json()
        setOrg(orgData)

        const schedRes = await fetch(`${API_BASE_URL}/schedules`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!schedRes.ok) throw new Error(await schedRes.text())
        const schedData: Schedule[] = await schedRes.json()
        setSchedules(schedData)
      } catch (err) {
        console.error(err)
        setError(
          err instanceof Error
            ? err.message
            : 'Eitthvað klikkaði við að sækja gögn.',
        )
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  return (
    <Hero
      org={org}
      schedules={schedules}
      loading={loading}
      error={error}
    />
  )
}
