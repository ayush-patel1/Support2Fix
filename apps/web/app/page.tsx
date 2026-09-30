import Link from "next/link";
import { LogoMark, Tagline, Wordmark } from "@/components/Logo";
import { TopNav } from "@/components/TopNav";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <TopNav />

      <main className="relative flex flex-1 items-center justify-center overflow-hidden px-6 py-24">
        {/* Background layers only — kept separate from the text below so
            nothing here inherits into the actual copy. */}
        <div
          aria-hidden
          className="bg-blueprint-grid absolute inset-0 [mask-image:radial-gradient(ellipse_70%_70%_at_50%_40%,black,transparent)]"
        />
        <div
          aria-hidden
          className="absolute top-1/2 left-1/2 h-[420px] w-[420px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand opacity-[0.08] blur-[100px]"
        />

        {/* Corner brackets + caption tags — the "technical schematic" frame
            from the brand board, so the hero reads as designed rather than
            a bare centered block on a plain background. */}
        <span
          aria-hidden
          className="absolute top-6 left-6 h-6 w-6 border-t border-l border-neutral-300 dark:border-neutral-700"
        />
        <span
          aria-hidden
          className="absolute top-6 right-6 h-6 w-6 border-t border-r border-neutral-300 dark:border-neutral-700"
        />
        <span
          aria-hidden
          className="absolute bottom-6 left-6 h-6 w-6 border-b border-l border-neutral-300 dark:border-neutral-700"
        />
        <span
          aria-hidden
          className="absolute right-6 bottom-6 h-6 w-6 border-r border-b border-neutral-300 dark:border-neutral-700"
        />
        <span className="absolute top-9 left-14 hidden font-[JetBrains_Mono] text-[10px] tracking-[0.15em] text-neutral-400 uppercase sm:block dark:text-neutral-600">
          Support2Fix / Platform
        </span>
        <span className="absolute right-14 bottom-9 hidden font-[JetBrains_Mono] text-[10px] tracking-[0.15em] text-neutral-400 uppercase sm:block dark:text-neutral-600">
          Faster diagnosis · Clearer context · Real fixes
        </span>

        <div className="relative flex max-w-2xl flex-col items-center gap-6 text-center">
          <LogoMark size={160} />
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
        Support2Fix is in early development — some features are still being built.
      </footer>
    </div>
  );
}
