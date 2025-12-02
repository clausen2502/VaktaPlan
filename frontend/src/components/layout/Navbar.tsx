import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement | null>(null)

  function toggleMenu() {
    setOpen((prev) => !prev)
  }

  function handleLogout() {
    localStorage.clear()
    window.location.href = '/login'
  }

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }

    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-brand">VaktaPlan</Link>

        <div className="navbar-right">
          <div className="navbar-links">
            <Link to="/" className="navbar-link">
              Yfirlit
            </Link>
            <Link to="/org" className="navbar-link">
              Minn vinnustaður
            </Link>
            <Link to="/preferences" className="navbar-link">
              Minir starfsmenn
            </Link>
            <Link to="/schedules" className="navbar-link">
              Mín Vaktaplön
            </Link>
          </div>

          <div className="navbar-profile-wrapper" ref={menuRef}>
            <button
              type="button"
              className="navbar-profile"
              aria-label="Notendastillingar"
              onClick={toggleMenu}
            >
              <span className="navbar-profile-icon" />
            </button>

            {open && (
              <div className="navbar-profile-menu">
                <button
                  type="button"
                  className="navbar-profile-menu-item"
                  onClick={handleLogout}
                >
                  Skrá út
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
