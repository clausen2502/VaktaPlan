import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'

export default function AppShell() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-50">
      <Navbar />
      <main className="mx-auto max-w-6xl px-6 py-6">
        <Outlet />
      </main>
    </div>
  )
}
