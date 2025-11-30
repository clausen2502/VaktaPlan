import { useState, type FC } from 'react'
import type { Shift, Schedule } from '../../types/schedule'

type MonthlyViewProps = {
  schedule: Schedule
  shifts: Shift[]
}

// helper: get YYYY-MM-DD from ISO
function toYMD(iso: string): string {
  return iso.slice(0, 10)
}

// build all days in [start, end]
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

// 2026-01-01 -> 2026.01.01
function formatYmdDots(ymd: string): string {
  const [y, m, d] = ymd.split('-')
  return `${y}.${m}.${d}`
}

// Icelandic labels
const weekdayLabels = ['Mán.', 'Þri.', 'Mið.', 'Fim.', 'Fös.', 'Lau.', 'Sun.']
const monthLabels = [
  'jan',
  'feb',
  'mar',
  'apr',
  'maí',
  'jún',
  'júl',
  'ágú',
  'sep',
  'okt',
  'nóv',
  'des',
]

const PAGE_DAYS = 28 // 4 weeks * 7 days

const MonthlyView: FC<MonthlyViewProps> = ({ schedule, shifts }) => {
  const days = buildDayRange(schedule.range_start, schedule.range_end)

  // group shifts per day (key = YYYY-MM-DD)
  const shiftsByDay: Record<string, Shift[]> = {}
  for (const shift of shifts) {
    const dayKey = toYMD(shift.start_at)
    if (!shiftsByDay[dayKey]) shiftsByDay[dayKey] = []
    shiftsByDay[dayKey].push(shift)
  }

  const [page, setPage] = useState(0)
  const totalPages = Math.max(1, Math.ceil(days.length / PAGE_DAYS))
  const safePage = Math.min(page, totalPages - 1)

  const pageStartIndex = safePage * PAGE_DAYS
  const pageDays = days.slice(pageStartIndex, pageStartIndex + PAGE_DAYS)

  const pageStartLabel = formatYmdDots(pageDays[0] ?? days[0])
  const pageEndLabel = formatYmdDots(
    pageDays[pageDays.length - 1] ?? days[days.length - 1],
  )

  // Build 28 display days aligned to Monday → Sunday
  const displayDays: string[] = []
  if (pageDays.length > 0) {
    const first = new Date(pageDays[0])

    // jsDay: 0=Sun,1=Mon,... -> we want Monday=0
    const jsDay = first.getDay()
    const mondayOffset = (jsDay + 6) % 7 // Mon=0, Tue=1, ..., Sun=6

    const start = new Date(first)
    start.setDate(start.getDate() - mondayOffset)

    for (let i = 0; i < PAGE_DAYS; i++) {
      const d = new Date(start)
      d.setDate(start.getDate() + i)
      const y = d.getFullYear()
      const m = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      displayDays.push(`${y}-${m}-${day}`)
    }
  }

  function handlePrev() {
    if (safePage > 0) setPage(safePage - 1)
  }

  function handleNext() {
    if (safePage < totalPages - 1) setPage(safePage + 1)
  }

  return (
    <div className="mt-6 border border-black rounded-xl overflow-hidden">
      {/* 28-day range + arrows */}
      <div className="flex items-center justify-center gap-3 border-b border-black px-3 py-2 text-xs">
        <button
          type="button"
          onClick={handlePrev}
          disabled={safePage === 0}
          className="border border-black px-2 py-1 disabled:opacity-40"
        >
          ‹
        </button>

        <span className="font-medium">
          {pageStartLabel} – {pageEndLabel}
        </span>

        <span className="text-[10px] text-neutral-400">
          Síða {safePage + 1} af {totalPages}
        </span>

        <button
          type="button"
          onClick={handleNext}
          disabled={safePage === totalPages - 1}
          className="border border-black px-2 py-1 disabled:opacity-40"
        >
          ›
        </button>
      </div>

      {/* Weekday header Mon–Sun */}
      <div className="grid grid-cols-7 border-b border-black text-[11px] font-medium">
        {weekdayLabels.map((lbl) => (
          <div
            key={lbl}
            className="px-2 py-1 border-r border-black last:border-r-0"
          >
            {lbl}
          </div>
        ))}
      </div>

      {/* 4x7 grid = 28 days, aligned Monday→Sunday */}
      <div className="grid grid-cols-7 text-xs">
        {Array.from({ length: PAGE_DAYS }).map((_, idx) => {
          const dayStr = displayDays[idx]

          if (!dayStr) {
            return (
              <div
                key={`empty-${idx}`}
                className="min-h-[80px] border-r border-b border-black px-2 py-1"
              />
            )
          }

          const dateObj = new Date(dayStr)
          const dayNumber = dateObj.getDate()
          const monthLabel = monthLabels[dateObj.getMonth()]

          const dayShifts = shiftsByDay[dayStr] ?? []

          return (
            <div
              key={dayStr}
              className="min-h-[80px] border-r border-b border-black px-2 py-1"
            >
              {/* only date here, weekday is in the header */}
              <div className="text-[11px] font-medium mb-1">
                {dayNumber}. {monthLabel}
              </div>

              {dayShifts.map((sh) => (
                <div
                  key={sh.id}
                  className="mb-1 rounded border border-black px-1 py-[2px]"
                >
                  {/* Only show times for now; employees will come later */}
                  <div className="text-[11px]">
                    {sh.start_at.slice(11, 16)}–{sh.end_at.slice(11, 16)}
                  </div>
                </div>
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default MonthlyView
