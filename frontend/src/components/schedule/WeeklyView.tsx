import { useState, type FC } from 'react'
import type { Schedule, Shift } from '../../types/schedule'

type WeeklyViewProps = {
  schedule: Schedule
  shifts: Shift[]
}

// YYYY-MM-DD from ISO
function toYMD(iso: string): string {
  return iso.slice(0, 10)
}

// YYYY-MM-DD from Date
function dateToYMD(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// get Monday of the week for given date
function getMonday(d: Date): Date {
  const copy = new Date(d)
  const jsDay = copy.getDay() // 0=Sun,1=Mon,...
  const offset = (jsDay + 6) % 7 // Mon=0, Tue=1, ..., Sun=6
  copy.setDate(copy.getDate() - offset)
  return copy
}

// get Sunday of the week for given date
function getSunday(d: Date): Date {
  const copy = new Date(d)
  const jsDay = copy.getDay() // 0=Sun,1=Mon,...
  const offset = (7 - jsDay) % 7 // Sun -> 0, Mon -> 6, etc.
  copy.setDate(copy.getDate() + offset)
  return copy
}

const weekdayLabels = ['Mán.', 'Þri.', 'Mið.', 'Fim.', 'Fös.', 'Lau.', 'Sun.']

const WeeklyView: FC<WeeklyViewProps> = ({ schedule, shifts }) => {
  const schedStart = new Date(schedule.range_start)
  const schedEnd = new Date(schedule.range_end)

  // Calendar span: full weeks from first Monday to last Sunday
  const firstMonday = getMonday(schedStart)
  const lastSunday = getSunday(schedEnd)

  const msPerDay = 24 * 60 * 60 * 1000
  const totalDays =
    Math.round((lastSunday.getTime() - firstMonday.getTime()) / msPerDay) + 1
  const totalWeeks = Math.max(1, Math.ceil(totalDays / 7))

  const [weekIndex, setWeekIndex] = useState(0)

  // Build the 7 days for the current week (Mon–Sun)
  const currentWeekStart = new Date(firstMonday)
  currentWeekStart.setDate(firstMonday.getDate() + weekIndex * 7)

  const currentWeekDays: string[] = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(currentWeekStart)
    d.setDate(currentWeekStart.getDate() + i)
    currentWeekDays.push(dateToYMD(d))
  }

  // group shifts per day
  const shiftsByDay: Record<string, Shift[]> = {}
  for (const shift of shifts) {
    const dayKey = toYMD(shift.start_at)
    if (!shiftsByDay[dayKey]) shiftsByDay[dayKey] = []
    shiftsByDay[dayKey].push(shift)
  }

  const canPrev = weekIndex > 0
  const canNext = weekIndex < totalWeeks - 1

  const weekLabel = `${currentWeekDays[0]} – ${
    currentWeekDays[currentWeekDays.length - 1]
  }`

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
          Vika {weekIndex + 1} ({weekLabel})
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

      {/* header row with weekdays (always Mon–Sun) */}
      <div className="grid grid-cols-7 border-b border-black text-xs font-medium">
        {weekdayLabels.map((lbl) => (
          <div
            key={lbl}
            className="px-2 py-1 border-r border-black last:border-r-0"
          >
            {lbl}
          </div>
        ))}
      </div>

      {/* day columns */}
      <div className="grid grid-cols-7 text-xs">
        {currentWeekDays.map((day) => {
          const dayShifts = shiftsByDay[day] ?? []
          const dateObj = new Date(day)
          const dayNumber = dateObj.getDate()

          // grey out days outside the schedule range
          const inSchedule =
            day >= schedule.range_start && day <= schedule.range_end
          const dateClass = inSchedule ? 'text-[11px] font-medium mb-1'
            : 'text-[11px] font-medium mb-1 text-neutral-500'

          return (
            <div
              key={day}
              className="min-h-[120px] border-r border-black px-2 py-1 last:border-r-0"
            >
              <div className={dateClass}>{dayNumber}</div>

              {inSchedule &&
                dayShifts.map((sh) => {
                  const start = sh.start_at.slice(11, 16)
                  const end = sh.end_at.slice(11, 16)

                  return (
                    <div
                      key={sh.id}
                      className="mb-1 rounded border border-black px-1 py-[2px]"
                    >
                      {/* times */}
                      <div className="text-[11px] font-semibold">
                        {start}–{end}
                      </div>

                      {/* later: employees when assigned */}
                      {sh.employee_name && (
                        <div className="text-[11px]">{sh.employee_name}</div>
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
