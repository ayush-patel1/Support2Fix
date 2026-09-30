/**
 * Support2Fix brand mark, built from the visual identity board (moodboard
 * image, not a source vector file) — two overlapping arrow/flag shapes
 * (ink, then lime, offset down-right) with a small precision-cross accent
 * at the seam, plus the "Support[2]Fix" wordmark with the "2" in lime.
 *
 * This is a clean SVG *recreation* of that mark, not a pixel trace of the
 * mockup photo — swap `<LogoMark>`'s paths for the real vector export if
 * one exists, and everything downstream (favicon, headers) keeps working.
 */

const BRAND_INK = "#0a0a0a";
const BRAND_LIME = "#cdf200";

export function LogoMark({
  className,
  size = 32,
  ink = BRAND_INK,
  lime = BRAND_LIME,
}: {
  className?: string;
  size?: number;
  ink?: string;
  lime?: string;
}) {
  return (
    <svg
      viewBox="0 0 44 48"
      width={size}
      height={size}
      className={className}
      role="img"
      aria-label="Support2Fix"
    >
      {/* Two overlapping chevron/flag shapes + a precision-cross accent at
          the seam — both polygons kept fully inside the viewBox (a
          previous version had points outside it, so the tips were
          clipped flush against the edges at small render sizes). */}
      <polygon points="6,8 30,8 22,22 2,22" fill={ink} />
      <polygon points="18,26 42,26 34,40 14,40" fill={lime} />
      <g stroke={ink} strokeWidth="2.5" strokeLinecap="round">
        <line x1="18" y1="17" x2="18" y2="31" />
        <line x1="12" y1="24" x2="24" y2="24" />
      </g>
    </svg>
  );
}

/** The mark on a rounded lime square — matches the "APP ICON" lockup.

 * `lime` is overridden to a translucent ink instead of the default solid
 * lime: LogoMark's second shape would otherwise be lime-on-lime against
 * this background and effectively disappear.
 */
export function LogoAppIcon({ className, size = 32 }: { className?: string; size?: number }) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-lg bg-brand ${className ?? ""}`}
      style={{ width: size, height: size }}
    >
      <LogoMark size={size * 0.6} lime={`${BRAND_INK}8c`} />
    </div>
  );
}

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
  wordmarkClassName,
}: {
  className?: string;
  size?: number;
  wordmarkClassName?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-2 ${className ?? ""}`}>
      <LogoMark size={size} />
      <Wordmark className={`text-xl ${wordmarkClassName ?? ""}`} />
    </span>
  );
}
