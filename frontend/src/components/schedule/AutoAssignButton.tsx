// src/components/schedule/AutoAssignButton.tsx
import { useState, type FC } from 'react'
import { API_BASE_URL } from '../../config'
import type { Shift } from '../../types/schedule'

type Props = {
  scheduleId: number
  rangeStart: string   // YYYY-MM-DD
  rangeEnd: string     // YYYY-MM-DD
  onShiftsUpdated?: (shifts: Shift[]) => void
}

const AutoAssignButton: FC<Props> = ({
  scheduleId,
  rangeStart,
  rangeEnd,
  onShiftsUpdated,
}) => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)

  async function handleClick() {
    try {
      setLoading(true)
      setError(null)
      setInfo(null)

      const token = localStorage.getItem('vakta_token')
      if (!token) {
        setError('Enginn token fannst, vinsamlegast skráðu þig inn aftur.')
        return
      }

      // 1) call auto-assign service
      const res = await fetch(
        `${API_BASE_URL}/assignments/auto-assign`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            schedule_id: scheduleId,
            start_date: rangeStart,
            end_date: rangeEnd,
            policy: 'reassign_all', // or "fill_missing" if you prefer
            dry_run: false,
          }),
        },
      )

      if (!res.ok) {
        const text = await res.text()
        throw new Error(
          text || `Villa við að úthluta vöktum (${res.status})`,
        )
      }

      const result = await res.json()

      // small summary text, works even if some fields are missing
      const parts: string[] = []
      if (typeof result.assigned === 'number') {
        parts.push(`${result.assigned} vaktasætum úthlutað`)
      }
      if (typeof result.skipped_full === 'number') {
        parts.push(`${result.skipped_full} sætum sleppt (fullar vaktir)`)
      }
      if (typeof result.skipped_no_candidates === 'number') {
        parts.push(
          `${result.skipped_no_candidates} sætum sleppt (engin kandídöt)`,
        )
      }

      setInfo(
        parts.length > 0
          ? parts.join(', ')
          : 'Sjálfvirk úthlutun kláraðist.',
      )

      // 2) refetch shifts so Weekly/Monthly show assigned employees
      const shiftsRes = await fetch(
        `${API_BASE_URL}/shifts?schedule_id=${scheduleId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      )

      if (!shiftsRes.ok) {
        const text = await shiftsRes.text()
        throw new Error(
          text || 'Vaktir voru úthlutaðar en ekki tókst að sækja þær.',
        )
      }

      const newShifts = (await shiftsRes.json()) as Shift[]
      if (onShiftsUpdated) onShiftsUpdated(newShifts)
    } catch (err) {
      console.error(err)
      setError(
        err instanceof Error
          ? err.message
          : 'Ekki tókst að úthluta starfsmönnum.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        className="border border-black px-3 py-1 text-sm disabled:opacity-60"
      >
        {loading ? 'Úthluta vöktum…' : 'Sjálfvirk úthlutun starfsmanna'}
      </button>

      {error && (
        <p className="text-xs text-red-600 whitespace-pre-wrap">{error}</p>
      )}
      {info && !error && (
        <p className="text-xs text-green-700 whitespace-pre-wrap">
          {info}
        </p>
      )}
    </div>
  )
}

export default AutoAssignButton
