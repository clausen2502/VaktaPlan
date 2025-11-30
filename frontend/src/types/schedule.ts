export type AssignedEmployee = {
  id: number
  display_name: string
}

export type Shift = {
  id: number
  schedule_id: number
  start_at: string
  end_at: string
  required_staff_count: number
  notes?: string | null

  // new (optional): many employees
  employees?: AssignedEmployee[]

  // keep old field for backwards-compat
  employee_name?: string | null
  assignments?: ShiftAssignment[] 
}

export type Schedule = {
  id: number
  name: string
  range_start: string
  range_end: string
  status: string
}

export type ShiftAssignment = {
  employee_id: number
  employee_name: string
  // preference_score?: number | null   // if you want it later
}