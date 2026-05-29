import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "AceleraSEO — Dashboard",
  description: "The open-source autonomous SEO strategist. Decisions, not data dumps.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
