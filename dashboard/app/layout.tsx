import type { Metadata } from 'next'
import './globals.css'
import Shell from '@/components/shell'

export const metadata: Metadata = {
  title: 'NoviSentinel Dashboard',
  description: 'AI Safety & PII Firewall — Admin Dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  )
}
