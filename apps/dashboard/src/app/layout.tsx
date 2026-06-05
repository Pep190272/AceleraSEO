import type { Metadata } from "next";

import { LanguageProvider } from "@/lib/i18n";

import "./globals.css";

export const metadata: Metadata = {
  title: "AceleraSEO — Panel",
  description: "El estratega SEO autónomo de código abierto. Decisiones, no montañas de datos.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // lang="es" is the documented server-side default. The LanguageProvider reads
  // localStorage on the client and calls document.documentElement.lang = lang
  // on every lang change, keeping the attribute in sync after hydration.
  //
  // Why not derive lang server-side? localStorage is unavailable during SSR.
  // Alternatives (cookies, server actions) would add infra complexity for a
  // cosmetic attribute. The chosen approach avoids a React hydration warning:
  // the server and client both emit "es" on first render; the client-side
  // effect then updates the attribute if the stored preference differs.
  return (
    <html lang="es">
      <body>
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  );
}
