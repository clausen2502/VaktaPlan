export type AssignedEmployee = {
  id: number
  display_name: string
}

export type Schedule = {
  id: number
  name: string
  range_start: string
  range_end: string
  status: string
}

export type Employee = {
  id: number
  display_name: string
}

export type ShiftAssignment = {
  employee_id: number
  employee_name: string
}

export type Shift = {
  id: number
  schedule_id: number
  start_at: string
  end_at: string
  required_staff_count: number
  notes?: string | null

  // NEW: many employees per shift
  assignments?: ShiftAssignment[]

  // old single-field, kept for backwards compat if needed
  employee_name?: string | null
}
