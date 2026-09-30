/**
 * Support2Fix brand mark. `public/support2fix.png` is the real designed
 * asset (not a recreation) — genuinely transparent (checked its alpha
 * channel directly; the black you see previewing it elsewhere is just
 * whatever background is behind it, not baked into the file), so it
 * composites cleanly on both the light and dark ends of the site's
 * adaptive theme without any light/dark variant needed.
 *
 * Natural size is 1372×1147 (≈1.196:1) — `LogoMark` takes `size` as the
 * rendered width and derives height from that ratio so `next/image`
 * doesn't squash it.
 */

import Image from "next/image";
import logoAsset from "@/public/support2fix.png";

const ASPECT_RATIO = 1372 / 1147;

export function LogoMark({ className, size = 32 }: { className?: string; size?: number }) {
  return (
    <Image
      src={logoAsset}
      alt="Support2Fix"
      width={size}
      height={Math.round(size / ASPECT_RATIO)}
      className={className}
      priority
    />
  );
}

/** Same mark — kept as a separate name since call sites (e.g. the

 * investigation console header) already reference `LogoAppIcon`
 * specifically. The real asset already carries its own glow/backdrop
 * treatment, so it no longer needs the extra colored-square wrapper an
 * earlier hand-drawn version used.
 */
export const LogoAppIcon = LogoMark;

export function Wordmark({
  className,
  colorClassName = "text-brand-ink dark:text-brand-paper",
}: {
  className?: string;
  /** Overridable rather than concatenated: the default assumes a page that
   * follows OS light/dark preference. Pages with a fixed palette regardless
   * of OS theme (e.g. the always-dark investigation console) need to pass
   * their own — relying on two conflicting `text-*` utility classes to
   * resolve via CSS source order is exactly the kind of thing that silently
   * breaks (see the investigations-header bug this was fixing). */
  colorClassName?: string;
}) {
  return (
    <span
      className={`font-[Unbounded] font-extrabold tracking-tight ${colorClassName} ${className ?? ""}`}
    >
      Support<span className="text-brand">2</span>Fix
    </span>
  );
}

export function Tagline({ className }: { className?: string }) {
  return (
    <span
      className={`font-[JetBrains_Mono] text-xs tracking-[0.2em] text-neutral-500 uppercase dark:text-neutral-400 ${className ?? ""}`}
    >
      See · Investigate · Fix · Ship
    </span>
  );
}

/** Icon + wordmark, the "HORIZONTAL LOCKUP / Primary usage" pairing. */
export function Logo({
  className,
  size = 28,
  // A prop default, not a hardcoded class concatenated with the caller's
  // override — text-xl and a caller-supplied text-lg both landing in the
  // same class string leaves the winner up to Tailwind's stylesheet order,
  // not which one appears "later" in the string. Exactly the footgun this
  // project already fixed once in Wordmark's own colorClassName.
  wordmarkClassName = "text-xl",
}: {
  className?: string;
  size?: number;
  wordmarkClassName?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-2 ${className ?? ""}`}>
      <LogoMark size={size} />
      <Wordmark className={wordmarkClassName} />
    </span>
  );
}
