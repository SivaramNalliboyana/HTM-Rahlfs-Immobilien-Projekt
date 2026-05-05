import { NavLink } from 'react-router-dom'

const items = [
  { label: 'Dashboard', icon: 'dashboard', to: '/' },
  { label: 'Portfolio', icon: 'location_city', to: '#' },
  { label: 'Tenants', icon: 'groups', to: '#' },
  { label: 'Finance', icon: 'payments', to: '#' },
  { label: 'Maintenance', icon: 'handyman', to: '#' },
  { label: 'Reports', icon: 'assessment', to: '#' },
]

export default function Sidebar() {
  return (
    <nav className="h-screen w-64 fixed left-0 top-0 shadow-xl border-r border-slate-700 bg-[#1a2b4a] text-white flex flex-col py-6 z-50">
      <div className="px-6 mb-8">
        <h1 className="text-h2 font-semibold uppercase tracking-widest text-amber-400">
          Rahlfs Cockpit
        </h1>
        <p className="text-body-sm text-slate-400 mt-1">Property Management</p>
      </div>
      <div className="flex-1 overflow-y-auto">
        <ul className="space-y-1">
          {items.map((item) =>
            item.to.startsWith('#') ? (
              <li key={item.label}>
                <a
                  href={item.to}
                  className="text-slate-400 hover:text-white px-4 py-3 flex items-center gap-3 text-sm font-medium hover:bg-white/5 transition-all duration-150 cursor-pointer"
                >
                  <span className="material-symbols-outlined">{item.icon}</span>
                  {item.label}
                </a>
              </li>
            ) : (
              <li key={item.label}>
                <NavLink
                  to={item.to}
                  end
                  className={({ isActive }) =>
                    `${
                      isActive
                        ? 'bg-white/10 text-white border-l-4 border-amber-500'
                        : 'text-slate-400 hover:text-white hover:bg-white/5'
                    } px-4 py-3 flex items-center gap-3 text-sm font-medium transition-all duration-150 cursor-pointer`
                  }
                >
                  <span className="material-symbols-outlined">{item.icon}</span>
                  {item.label}
                </NavLink>
              </li>
            ),
          )}
        </ul>
      </div>
      <div className="mt-auto px-6 pt-6 border-t border-slate-700/50 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center text-white font-bold border border-slate-600">
          A
        </div>
        <div>
          <p className="text-label-md text-white">Admin User</p>
          <p className="text-label-sm text-slate-400">Settings</p>
        </div>
      </div>
    </nav>
  )
}
