import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Support2Fix",
  description: "AI-powered customer issue to engineering fix platform",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f2f1ec" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        {/* Three distinct type roles, on purpose — see components/Logo.tsx:
             - Unbounded (extra-bold/black): the "Support2Fix" wordmark
               ONLY. A chunky, geometric display face with letterforms
               unmistakably unlike the other two — not just "a different
               font in the same style," but a different shape language.
             - Geist: body text / investigation-console headings.
             - JetBrains Mono: taglines and technical/telemetry labels.
            Site-wide, so it lives in the root layout. */}
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Geist:wght@100..900&family=JetBrains+Mono:wght@100..900&family=Unbounded:wght@700..900&display=swap"
        />
      </head>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
