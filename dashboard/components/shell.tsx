'use client'
import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Sidebar from './sidebar'

export default function Shell({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [ready, setReady] = useState(() => {
    if (typeof window === 'undefined') return false
    return !!sessionStorage.getItem('ns_master_key')
  })

  useEffect(() => {
    if (pathname === '/login') return
    const key = sessionStorage.getItem('ns_master_key')
    if (!key) {
      router.replace('/login')
    } else if (!ready) {
      setReady(true)
    }
  }, [pathname, router, ready])

  if (pathname === '/login') return <>{children}</>
  if (!ready) return (
    <div className="flex h-screen items-center justify-center bg-[#0d1117]">
      <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  return (
    <div className="flex h-screen bg-[#0d1117] text-[#e6edf3] overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
