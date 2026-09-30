import "./console.css";

/**
 * Loads Material Symbols (icon font), used only on this section's pages.
 * Geist and JetBrains Mono are brand-wide now and load from the root
 * layout instead. <link> tags rendered anywhere in a Server Component
 * tree are hoisted and deduped into <head> automatically (React 19 /
 * Next.js App Router).
 */
export default function InvestigationsLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap"
      />
      {children}
    </>
  );
}
