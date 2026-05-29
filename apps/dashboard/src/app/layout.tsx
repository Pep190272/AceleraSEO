import type { Metadata } from "next";

import { LanguageProvider } from "@/lib/i18n";

import "./globals.css";

export const metadata: Metadata = {
  title: "AceleraSEO — Panel",
  description: "El estratega SEO autónomo de código abierto. Decisiones, no montañas de datos.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  );
}
