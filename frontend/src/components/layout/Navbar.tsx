import { Link } from 'react-router-dom'

export default function Navbar() {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        {/* Left: brand (not clickable) */}
        <span className="navbar-brand">VaktaPlan</span>

        {/* Right: links + profile icon */}
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

          <button
            type="button"
            className="navbar-profile"
            aria-label="Notendastillingar"
          >
            <span className="navbar-profile-icon" />
          </button>
        </div>
      </div>
    </header>
  )
}
