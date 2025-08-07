import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Toaster } from 'react-hot-toast'
import './globals.css'

// Force dynamic rendering to avoid build-time static generation errors
export const dynamic = 'force-dynamic'
export const revalidate = 0

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'UmaDex - Educational Assignment App',
  description: 'Manage your educational assignments with ease',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        {children}
        <Toaster 
          position="top-right" 
          toastOptions={{
            duration: 5000,
            style: {
              maxWidth: '500px',
            },
            error: {
              duration: 6000,
            },
          }}
        />
      </body>
    </html>
  )
}