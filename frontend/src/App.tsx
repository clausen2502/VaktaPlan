// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Schedules from './pages/Schedules'
import Schedule from './pages/SingleSchedule'
import OrgOverview from './pages/OrgOverview'
import AppShell from './components/layout/AppShell'
import EmployeePreferences from './pages/EmployeePreferences'


export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public login */}
        <Route path="/login" element={<Login />} />

        {/* All logged-in pages share AppShell */}
        <Route path="/" element={<AppShell />}>
          <Route index element={<Dashboard />} />
          <Route path="schedules" element={<Schedules />} />
          <Route path="schedules/:id" element={<Schedule />} />
          <Route path="org" element={<OrgOverview />} />
          <Route path="preferences" element={<EmployeePreferences />} />
        </Route>

        {/* anything else -> login */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
