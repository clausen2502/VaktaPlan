import { useState, type FC } from 'react'
import type { Schedule, Shift } from '../../types/schedule'
import MonthlyView from './MonthlyView'
import WeeklyView from './WeeklyView'
import WeeklyTemplateEditor from './WeeklyTemplateEditor'

type Props = {
  schedule: Schedule
  shifts: Shift[]
  onEditSchedule?: (schedule: Schedule) => void
  onDeleteSchedule?: (schedule: Schedule) => void
  onShiftsUpdated?: (shifts: Shift[]) => void
}

const ScheduleShell: FC<Props> = ({
  schedule,
  shifts,
  onEditSchedule,
  onDeleteSchedule,
  onShiftsUpdated,
}) => {
  const [view, setView] = useState<'month' | 'week'>('month')

  const isMonth = view === 'month'
  const isWeek = view === 'week'

  function handleEditClick() {
    if (onEditSchedule) onEditSchedule(schedule)
    else window.alert('Breyta plani — virkni kemur síðar.')
  }

  function handleDeleteClick() {
    if (onDeleteSchedule) onDeleteSchedule(schedule)
    else window.alert('Eyða plani — virkni kemur síðar.')
  }

  return (
    <div className="min-h-screen bg-white text-black px-6 py-8">
      <header className="flex items-center justify-between mb-6">
        <div className="text-2xl font-bold tracking-tight">VaktaPlan</div>
        <div className="h-8 w-8 rounded-full border border-black" />
      </header>

      {/* Weekly template ABOVE the calendar */}
      <WeeklyTemplateEditor
        scheduleId={schedule.id}
        rangeStart={schedule.range_start}
        rangeEnd={schedule.range_end}
        onShiftsUpdated={onShiftsUpdated}
      />

      <div className="mb-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1 text-center">
            <h2 className="text-2xl font-semibold mb-1">
              {schedule.name ?? 'Vaktaplan'}
            </h2>

            <div className="flex items-center justify-center gap-4 text-sm">
              <button
                type="button"
                onClick={() => setView('month')}
                aria-pressed={isMonth}
                className={`cursor-pointer ${
                  isMonth ? 'font-bold underline' : 'font-normal'
                }`}
              >
                Mánaðaryfirlit
              </button>

              <span>|</span>

              <button
                type="button"
                onClick={() => setView('week')}
                aria-pressed={isWeek}
                className={`cursor-pointer ${
                  isWeek ? 'font-bold underline' : 'font-normal'
                }`}
              >
                Vikuyfirlit
              </button>
            </div>

            <p className="text-sm mt-2">
              {schedule.range_start} – {schedule.range_end}
            </p>
          </div>

          <div className="flex flex-col items-end gap-2 text-sm">
            <button
              type="button"
              onClick={handleEditClick}
              className="underline cursor-pointer"
            >
              Breyta plani
            </button>
            <button
              type="button"
              onClick={handleDeleteClick}
              className="underline cursor-pointer"
            >
              Eyða plani
            </button>
          </div>
        </div>
      </div>

      {isMonth ? (
        <MonthlyView schedule={schedule} shifts={shifts} />
      ) : (
        <WeeklyView schedule={schedule} shifts={shifts} />
      )}
    </div>
  )
}

export default ScheduleShell
