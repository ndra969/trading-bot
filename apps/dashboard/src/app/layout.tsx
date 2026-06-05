import type { Metadata } from "next"

import "./globals.css"

export const metadata: Metadata = {
  title: "Trading Bot Dashboard",
  description: "Read-only monitoring + strategy-tuning views.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  )
}
