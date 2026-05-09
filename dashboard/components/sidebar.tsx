'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { LayoutDashboard, FileText, BarChart2, Settings, LogOut, Shield } from 'lucide-react'
import { clearCredentials } from '@/lib/api'

const NAV = [
  { href: '/',           label: 'Overview',  icon: LayoutDashboard },
  { href: '/logs',       label: 'Logs',       icon: FileText },
  { href: '/analytics',  label: 'Analytics',  icon: BarChart2 },
  { href: '/settings',   label: 'Settings',   icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()

  function logout() {
    clearCredentials()
    router.replace('/login')
  }

  return (
    <aside className="w-56 shrink-0 flex flex-col bg-[#0d1117] border-r border-[#30363d]">
      <div className="flex items-center gap-2 px-5 py-5 border-b border-[#30363d]">
        <Shield size={18} className="text-blue-400" />
        <span className="font-semibold text-sm tracking-wide text-[#e6edf3]">NoviSentinel</span>
      </div>

      <nav className="flex-1 p-3 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                active
                  ? 'bg-[#21262d] text-[#e6edf3]'
                  : 'text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#161b22]'
              }`}
            >
              <Icon size={15} />
              {label}
            </Link>
          )
        })}
      </nav>

      <div className="p-3 border-t border-[#30363d]">
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-md text-sm text-[#8b949e] hover:text-red-400 hover:bg-red-500/10 transition-colors"
        >
          <LogOut size={15} />
          Logout
        </button>
      </div>
    </aside>
  )
}
