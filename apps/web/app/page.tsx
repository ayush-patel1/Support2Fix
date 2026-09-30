import Link from "next/link";
import { LogoMark, Tagline, Wordmark } from "@/components/Logo";
import { TopNav } from "@/components/TopNav";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <TopNav />

      <main className="relative flex flex-1 items-center justify-center overflow-hidden px-6 py-24">
        {/* Background layer only — kept separate from the text below so the
            dot grid's muted `color` (used for `currentcolor`) doesn't
            inherit into the actual copy. */}
        <div
          aria-hidden
          className="bg-dot-grid absolute inset-0 [mask-image:radial-gradient(ellipse_60%_60%_at_50%_40%,black,transparent)]"
        />

        <div className="relative flex max-w-2xl flex-col items-center gap-6 text-center">
          <LogoMark size={56} />
          <div className="flex flex-col items-center gap-2">
            <Wordmark className="text-5xl sm:text-6xl" />
            <Tagline />
          </div>
          <p className="max-w-lg text-lg text-neutral-600 dark:text-neutral-400">
            Turns a customer support issue into an evidence-backed engineering investigation — root
            cause, reproduction, a validated fix, and a human-approved pull request.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <Link
              href="/dashboard"
              className="rounded-md bg-brand px-5 py-2.5 text-sm font-semibold text-brand-ink transition hover:brightness-95"
            >
              Go to dashboard
            </Link>
            <Link
              href="/investigations/2841"
              className="rounded-md border border-neutral-300 px-5 py-2.5 text-sm font-medium text-neutral-700 transition hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-900"
            >
              View investigation console →
            </Link>
          </div>
        </div>
      </main>

      <footer className="border-t border-neutral-200 px-6 py-4 text-center text-xs text-neutral-500 dark:border-neutral-800">
        Phase 2 — authentication and organizations. Tickets, agents and the rest of the workflow
        land in later phases.
      </footer>
    </div>
  );
}
