import type { FC } from 'react'
import type { Schedule, Shift } from '../../types/schedule'
import MonthlyView from './MonthlyView'
import AutoAssignButton from './AutoAssignButton'

type Props = {
  schedule: Schedule
  shifts: Shift[]
  onEditSchedule: (s: Schedule) => void
  onDeleteSchedule: (s: Schedule) => void
  onReloadSchedule?: () => void  // auto-assign finished
  onPublishSchedule?: (s: Schedule) => void
}

const ScheduleShell: FC<Props> = ({
  schedule,
  shifts,
  onEditSchedule,
  onDeleteSchedule,
  onReloadSchedule,
  onPublishSchedule,
}) => {
  const rangeLabel = `${schedule.range_start} – ${schedule.range_end}`
  const statusLabel =
    schedule.status === 'published' ? 'Birt plan' : 'Drög'
  const statusClass =
    schedule.status === 'published'
      ? 'text-emerald-300'
      : 'text-yellow-300'

  return (
    <main className="p-4">
      {/* header */}
      <div className="mb-4 flex flex-col gap-2">
        {/* title + status centered */}
        <div className="flex justify-center items-baseline gap-3">
          <h1 className="text-3xl font-semibold text-center">
            {schedule.name}
          </h1>
          <span className={`text-sm ${statusClass}`}>{statusLabel}</span>
        </div>

        {/* date range centered under title */}
        <div className="text-xs text-neutral-400 text-center">
          {rangeLabel}
        </div>

        {/* action buttons aligned to the right */}
        <div className="mt-2 flex justify-end gap-2">
          <AutoAssignButton
            scheduleId={schedule.id}
            rangeStart={schedule.range_start}
            rangeEnd={schedule.range_end}
            onDone={onReloadSchedule}
          />

          {onPublishSchedule && (
            <button
              type="button"
              onClick={() => onPublishSchedule(schedule)}
              className="border border-black px-3 py-1 text-sm"
            >
              Birta plan
            </button>
          )}

          <button
            type="button"
            onClick={() => onEditSchedule(schedule)}
            className="border border-black px-3 py-1 text-sm"
          >
            Breyta plani
          </button>

          <button
            type="button"
            onClick={() => onDeleteSchedule(schedule)}
            className="border border-black px-3 py-1 text-sm"
          >
            Eyða plani
          </button>
        </div>
      </div>

      {/* body */}
      <MonthlyView schedule={schedule} shifts={shifts} />
      {/* <WeeklyView schedule={schedule} shifts={shifts} /> if you add tabs later */}
    </main>
  )
}

export default ScheduleShell
