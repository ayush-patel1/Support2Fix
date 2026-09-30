import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Support2Fix",
  description: "AI-powered customer issue to engineering fix platform",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
