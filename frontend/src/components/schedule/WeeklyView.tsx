import { useState, type FC } from 'react'
import type { Schedule, Shift } from '../../types/schedule'

type WeeklyViewProps = {
  schedule: Schedule
  shifts: Shift[]
}

// helper: get YYYY-MM-DD from ISO
function toYMD(iso: string): string {
  return iso.slice(0, 10)
}

// helper: build all days in [start, end]
function buildDayRange(startIso: string, endIso: string): string[] {
  const days: string[] = []
  const start = new Date(startIso)
  const end = new Date(endIso)

  let d = new Date(start.getFullYear(), start.getMonth(), start.getDate())

  while (d <= end) {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    days.push(`${y}-${m}-${day}`)
    d.setDate(d.getDate() + 1)
  }

  return days
}

const weekdayLabels = ['Mán.', 'Þri.', 'Mið.', 'Fim.', 'Fös.', 'Lau.', 'Sun.']

const WeeklyView: FC<WeeklyViewProps> = ({ schedule, shifts }) => {
  const allDays = buildDayRange(schedule.range_start, schedule.range_end)

  // chunk into weeks of max 7 days
  const weeks: string[][] = []
  for (let i = 0; i < allDays.length; i += 7) {
    weeks.push(allDays.slice(i, i + 7))
  }

  const [weekIndex, setWeekIndex] = useState(0)
  const currentWeek = weeks[weekIndex] ?? []

  // group shifts per day
  const shiftsByDay: Record<string, Shift[]> = {}
  for (const shift of shifts) {
    const dayKey = toYMD(shift.start_at)
    if (!shiftsByDay[dayKey]) shiftsByDay[dayKey] = []
    shiftsByDay[dayKey].push(shift)
  }

  const canPrev = weekIndex > 0
  const canNext = weekIndex < weeks.length - 1

  const weekLabel =
    currentWeek.length > 0
      ? `${currentWeek[0]} – ${currentWeek[currentWeek.length - 1]}`
      : ''

  return (
    <div className="mt-6 border border-black rounded-xl">
      {/* week controls */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-black text-sm">
        <button
          type="button"
          disabled={!canPrev}
          className="px-2 py-1 border border-black disabled:opacity-40"
          onClick={() => canPrev && setWeekIndex((i) => i - 1)}
        >
          Fyrri vika
        </button>

        <div className="text-sm font-medium">
          Vika {weekIndex + 1} {weekLabel && `(${weekLabel})`}
        </div>

        <button
          type="button"
          disabled={!canNext}
          className="px-2 py-1 border border-black disabled:opacity-40"
          onClick={() => canNext && setWeekIndex((i) => i + 1)}
        >
          Næsta vika
        </button>
      </div>

      {/* header row with weekdays */}
      <div className="grid grid-cols-7 border-b border-black text-xs font-medium">
        {currentWeek.map((day, idx) => (
          <div
            key={day}
            className="px-2 py-1 border-r border-black last:border-r-0"
          >
            <div>{weekdayLabels[idx % 7]}</div>
          </div>
        ))}
      </div>

      {/* day columns */}
      <div className="grid grid-cols-7 text-xs">
        {currentWeek.map((day) => {
          const dayShifts = shiftsByDay[day] ?? []
          const dateObj = new Date(day)
          const dayNumber = dateObj.getDate()

          return (
            <div
              key={day}
              className="min-h-[120px] border-r border-black px-2 py-1 last:border-r-0"
            >
              <div className="text-[11px] font-medium mb-1">{dayNumber}</div>

              {dayShifts.map((sh) => {
                const start = sh.start_at.slice(11, 16)
                const end = sh.end_at.slice(11, 16)

                return (
                  <div
                    key={sh.id}
                    className="mb-1 rounded border border-black px-1 py-[2px]"
                  >
                    {/* MAIN: always time */}
                    <div className="text-[11px] font-semibold">
                      {start}–{end}
                    </div>

                    {/* Assigned employees */}
                    {sh.assignments && sh.assignments.length > 0 && (
                      <ul className="mt-[1px] space-y-[1px]">
                        {sh.assignments.map((a) => (
                          <li
                            key={a.employee_id}
                            className="text-[11px]"
                          >
                            • {a.employee_name}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )
              })}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default WeeklyView
