import { LogoAppIcon, Wordmark } from "@/components/Logo";

/**
 * Investigation console — static design preview.
 *
 * This renders fixed mock content (the Phase 24 demo scenario: a coupon
 * that zeroes an order total and deadlocks the payment retry loop) rather
 * than a real investigation. There is no investigation backend yet —
 * that's Phase 9 onward (see docs/architecture/agent-architecture.md).
 * The banner below says so on the page itself, since presenting fabricated
 * investigation results as real is exactly what this project's own rules
 * (system-design.md, "never fabricate investigation results") guard
 * against — a clearly labelled UI mockup is a different, legitimate thing.
 *
 * `id` is threaded through the couple of places a real case number would
 * show; the rest of the narrative is fixed demo content regardless of it.
 */
export default async function InvestigationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  return (
    <div className="min-h-screen bg-background font-body-md text-on-surface antialiased">
      {/* DESIGN PREVIEW NOTICE — see file header comment. Deliberately NOT
          sticky/fixed: it sits in normal flow above the sticky header so
          the header/sidebar/main offsets below can stay locked to the
          header's own h-14, instead of a hand-guessed pixel height for
          this banner (which drifted once web fonts swapped in — that was
          the cause of the layout jump/shift previously here). */}
      <div className="z-[60] flex items-center justify-center gap-2 bg-primary-container px-space-md py-1 font-label-sm text-label-sm font-semibold tracking-wider text-on-primary-container uppercase">
        <span className="material-symbols-outlined text-[14px]">visibility</span>
        Design preview — static mock data, not a real investigation. Live data lands in later
        phases.
      </div>

      <header className="sticky top-0 left-0 right-0 z-50 h-14 bg-surface-container-lowest border-b border-surface-container-highest">
        <div className="h-14 w-full px-margin flex items-center justify-between gap-space-md">
          <div className="flex items-center gap-space-md min-w-max">
            <LogoAppIcon size={32} />
            <div className="flex items-center gap-space-sm pl-space-xs border-l border-surface-container-highest">
              <Wordmark className="text-lg" colorClassName="text-primary" />
              <span className="font-label-sm text-label-sm text-outline px-space-xs py-0.5 bg-surface-container-low border border-surface-container-high">
                S2F / CASE / {id}
              </span>
              <span className="font-label-sm text-label-sm text-on-surface-variant font-code-stream">
                14:36:08 UTC+00:00
              </span>
            </div>
          </div>
          <div className="hidden lg:flex items-center gap-space-lg px-space-md py-1 bg-surface-container-low border border-surface-container">
            <div className="flex items-center gap-space-xs">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-container opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-container" />
              </span>
              <span className="font-label-sm text-label-sm text-primary-container font-semibold uppercase tracking-wider">
                [● INVESTIGATING]
              </span>
            </div>
            <div className="h-3 w-px bg-surface-container-highest" />
            <div className="flex items-center gap-space-sm font-label-sm text-label-sm">
              <span className="text-error font-medium">47 ERRORS</span>
              <span className="text-outline">/</span>
              <span className="text-secondary-container font-medium">1 DEPLOY CORRELATED</span>
            </div>
          </div>
          <div className="flex items-center gap-space-md">
            <nav className="flex items-center border border-surface-container-highest bg-surface-container-lowest">
              <a
                aria-current="page"
                className="px-space-sm py-1 transition-colors bg-primary-container text-on-primary-container font-bold"
                href="#case-wall"
              >
                CASE WALL
              </a>
              <a
                className="font-label-sm text-label-sm px-space-sm py-1 text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors border-l border-surface-container-highest"
                href="#repro-dock"
              >
                REPRO
              </a>
              <a
                className="font-label-sm text-label-sm px-space-sm py-1 text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors border-l border-surface-container-highest"
                href="#code-patch"
              >
                PATCH
              </a>
            </nav>
            <div className="hidden md:flex flex-col text-right">
              <span className="font-label-sm text-label-sm text-on-surface tracking-wider font-semibold">
                AYUSH R.
              </span>
              <span className="font-label-sm text-label-sm text-outline text-[10px]">
                LEAD FORENSIC ENG
              </span>
            </div>
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
              <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
            </div>
          </div>
        </div>
      </header>

      {/* Global nav rail — only on genuinely wide screens (xl+). Below
          that, the 3-column layout kicks in at `lg` on its own (see the
          `xl:flex-row` note below), and this rail would otherwise be
          nearly a quarter of the window taken up by a nav that duplicates
          the header's own tabs and the case-metadata column's quick-nav
          grid. Was previously always-on regardless of viewport, which
          combined with a too-high 3-column breakpoint (xl) to squash
          everything into one long, narrow, stacked column below 1280px —
          the "more vertical, less width" issue. */}
      <aside className="hidden xl:flex fixed left-0 top-14 bottom-0 w-56 bg-surface-container-lowest border-r border-surface-container-highest z-40 flex-col justify-between py-space-sm">
        <div className="px-space-sm">
          <div className="px-space-sm py-space-xs mb-space-sm font-label-sm text-label-sm text-outline uppercase tracking-widest border-b border-surface-container-highest">
            TELEMETRY RAIL
          </div>
          <nav className="flex flex-col gap-space-xs">
            <a
              aria-current="page"
              className="px-space-sm py-space-xs flex items-center justify-between bg-primary-container text-on-primary-container font-bold"
              href="#case-wall"
            >
              <span>SYS // OVERVIEW</span>
              <span className="text-outline text-[10px]">0x01</span>
            </a>
            <a
              className="font-label-md text-label-md px-space-sm py-space-xs text-on-surface-variant hover:bg-surface-container hover:text-on-surface flex items-center justify-between"
              href="#repro-dock"
            >
              <span>HEX // REPRO RUNNER</span>
              <span className="text-error text-[10px]">CRIT</span>
            </a>
            <a
              className="font-label-md text-label-md px-space-sm py-space-xs text-on-surface-variant hover:bg-surface-container hover:text-on-surface flex items-center justify-between"
              href="#trace-inspector"
            >
              <span>KERNEL TRACE STREAM</span>
              <span className="text-primary-container text-[10px]">SYNC</span>
            </a>
            <a
              className="font-label-md text-label-md px-space-sm py-space-xs text-on-surface-variant hover:bg-surface-container hover:text-on-surface flex items-center justify-between"
              href="#code-patch"
            >
              <span>PATCH DIFF MATRIX</span>
              <span className="text-secondary text-[10px]">STAGED</span>
            </a>
            <a
              className="font-label-md text-label-md px-space-sm py-space-xs text-on-surface-variant hover:bg-surface-container hover:text-on-surface flex items-center justify-between"
              href="#telemetry-feed"
            >
              <span>TELEMETRY TIMELINE</span>
              <span className="text-outline text-[10px]">PAUSED</span>
            </a>
          </nav>
        </div>
        <div className="px-space-sm">
          <div className="p-space-xs bg-surface-container-low border border-surface-container-highest font-code-stream text-body-sm text-outline">
            <div className="flex justify-between text-on-surface font-label-sm text-label-sm mb-1">
              <span>DAEMON</span>
              <span className="text-secondary">ONLINE</span>
            </div>
            <div className="text-[11px] leading-tight text-on-surface-variant">MEM_LOAD: 78.4%</div>
            <div className="text-[11px] leading-tight text-on-surface-variant">LATENCY: 12ms</div>
          </div>
        </div>
      </aside>

      <div className="xl:pl-56">
        {/* No pt-14 here: the header above is `sticky`, not `fixed`, so it
            already occupies its own 56px in normal document flow — adding
            padding-top on top of that double-counted the offset, pushing
            all content down by an extra header-height worth of empty gap.
            (The fixed global nav rail's own `top-14` is unrelated and
            correct: a `fixed` element genuinely needs that offset since it
            IS removed from flow.) */}
        <main className="relative bg-background min-h-screen">
          <div className="flex flex-col w-full">
            {/* PRIMARY INVESTIGATION CONSOLE SHELL */}
            {/* lg (1024px), not xl (1280px): the old threshold meant every
                window narrower than 1280px got one long stacked column
                instead of three side-by-side ones — see the nav-rail note
                above for the other half of that fix. */}
            <div className="flex flex-col lg:flex-row w-full bg-surface text-on-surface select-text font-body-md min-h-[calc(100vh-3.5rem)]">
              {/* 1. LEFT COLUMN: CASE METADATA RAIL */}
              {/* lg:sticky + lg:self-start (row mode only): without self-start,
                  the flex row's default `align-items: stretch` gives this
                  aside the SAME height as the much taller center column but
                  leaves its own short content sitting at the top — sticky
                  positioning can't do anything with that, since the box
                  already spans the full scrollable height. self-start lets
                  it size to its own content instead, so sticky can actually
                  keep it in view while the center column scrolls past. */}
              <aside className="w-full lg:sticky lg:top-14 lg:w-[260px] lg:max-h-[calc(100vh-3.5rem)] lg:self-start lg:overflow-y-auto shrink-0 bg-surface-container-lowest border-r border-outline-variant/30 flex flex-col justify-between p-space-md space-y-space-lg">
                <div className="space-y-space-lg">
                  <div className="space-y-space-xs pb-space-md border-b border-outline-variant/20">
                    <div className="flex items-center justify-between">
                      <span className="font-label-sm text-label-sm tracking-widest text-outline uppercase">
                        CASE REGISTRY
                      </span>
                      <span className="font-label-sm text-[10px] text-primary-container px-1 py-0.2 bg-surface-container-low border border-outline-variant/40">
                        NODE-01
                      </span>
                    </div>
                    <div className="flex items-baseline gap-space-xs">
                      <span className="font-label-sm text-label-sm text-outline font-code-stream">
                        #
                      </span>
                      <h1 className="font-label-lg text-4xl xl:text-5xl font-bold tracking-tight text-primary leading-none">
                        {id}
                      </h1>
                    </div>
                    <div className="pt-space-xs font-label-sm text-label-sm text-outline flex items-center justify-between">
                      <span>S2F-KERNEL-CORE</span>
                      <span className="text-secondary-container">SHA: 8a92c1f</span>
                    </div>
                  </div>
                  <div className="space-y-space-sm font-label-sm text-label-sm">
                    <div className="flex justify-between items-center py-0.5 border-b border-outline-variant/10">
                      <span className="text-outline uppercase tracking-wider">STATUS</span>
                      <span className="text-primary-container font-semibold tracking-wider flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full bg-primary-container animate-pulse" />
                        ● INVESTIGATING
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-0.5 border-b border-outline-variant/10">
                      <span className="text-outline uppercase tracking-wider">SEVERITY</span>
                      <span className="text-error font-semibold bg-error-container/20 px-1 py-0.5 text-[10px] tracking-widest">
                        CRITICAL / P0
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-0.5 border-b border-outline-variant/10">
                      <span className="text-outline uppercase tracking-wider">CUSTOMER</span>
                      <span className="text-on-surface font-medium truncate max-w-[140px] text-right">
                        ACME COMMERCE
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-0.5 border-b border-outline-variant/10">
                      <span className="text-outline uppercase tracking-wider">SERVICE</span>
                      <span className="text-on-surface-variant font-code-stream truncate max-w-[145px] text-right">
                        CHECKOUT / PAY-SVC
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-0.5 border-b border-outline-variant/10">
                      <span className="text-outline uppercase tracking-wider">CLUSTER</span>
                      <span className="text-on-surface-variant">SRE-EU-WEST-4</span>
                    </div>
                    <div className="flex justify-between items-center py-0.5">
                      <span className="text-outline uppercase tracking-wider">ELAPSED</span>
                      <span className="text-primary-container font-code-stream">
                        04m 12s [T+252s]
                      </span>
                    </div>
                  </div>
                  <div className="space-y-space-xs pt-space-xs">
                    <div className="font-label-sm text-[10px] text-outline tracking-widest uppercase pb-1 border-b border-outline-variant/30 flex justify-between">
                      <span>INDEX RUNNERS</span>
                      <span>04 ZONES</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1 font-label-sm text-[11px]">
                      <a
                        className="p-1.5 bg-surface-container-low hover:bg-surface-container hover:text-primary text-on-surface-variant transition-colors flex items-center justify-between"
                        href="#case-wall"
                      >
                        <span>01 WALL</span>
                        <span className="text-[9px] text-outline">LOC</span>
                      </a>
                      <a
                        className="p-1.5 bg-surface-container-low hover:bg-surface-container hover:text-primary text-on-surface-variant transition-colors flex items-center justify-between"
                        href="#repro-dock"
                      >
                        <span>02 REPRO</span>
                        <span className="text-[9px] text-error font-mono">FAIL</span>
                      </a>
                      <a
                        className="p-1.5 bg-surface-container-low hover:bg-surface-container hover:text-primary text-on-surface-variant transition-colors flex items-center justify-between"
                        href="#code-patch"
                      >
                        <span>03 PATCH</span>
                        <span className="text-[9px] text-secondary font-mono">+6/-2</span>
                      </a>
                      <a
                        className="p-1.5 bg-surface-container-low hover:bg-surface-container hover:text-primary text-on-surface-variant transition-colors flex items-center justify-between"
                        href="#telemetry-feed"
                      >
                        <span>04 STREAM</span>
                        <span className="text-[9px] text-primary-container font-mono">LIVE</span>
                      </a>
                    </div>
                  </div>
                  <div className="space-y-space-xs pt-space-sm">
                    <div className="font-label-sm text-[10px] text-outline tracking-widest uppercase pb-1 border-b border-outline-variant/30 flex justify-between">
                      <span>VECTOR MATCHES</span>
                      <span>03 PRIOR</span>
                    </div>
                    <div className="space-y-1 font-label-sm text-label-sm">
                      <div className="p-space-xs bg-surface-container-low/70 border-l-2 border-outline hover:border-primary-container transition-all">
                        <div className="flex justify-between text-[11px] font-medium text-on-surface">
                          <span>INC-2837</span>
                          <span className="text-outline text-[10px]">MED · 9d ago</span>
                        </div>
                        <p className="text-[10px] text-on-surface-variant truncate font-body-sm mt-0.5">
                          Duplicate zero invoice bypass in ledger
                        </p>
                      </div>
                      <div className="p-space-xs bg-surface-container-low/70 border-l-2 border-error hover:border-error transition-all">
                        <div className="flex justify-between text-[11px] font-medium text-on-surface">
                          <span>INC-2791</span>
                          <span className="text-error text-[10px]">HIGH · 21d ago</span>
                        </div>
                        <p className="text-[10px] text-on-surface-variant truncate font-body-sm mt-0.5">
                          Coupon race condition cart deadlock
                        </p>
                      </div>
                      <div className="p-space-xs bg-surface-container-low/70 border-l-2 border-outline hover:border-primary-container transition-all">
                        <div className="flex justify-between text-[11px] font-medium text-on-surface">
                          <span>INC-2618</span>
                          <span className="text-outline text-[10px]">HIGH · 42d ago</span>
                        </div>
                        <p className="text-[10px] text-on-surface-variant truncate font-body-sm mt-0.5">
                          Infinite payment worker loop thread 11
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="pt-space-md border-t border-outline-variant/20 font-label-sm text-[10px] text-outline space-y-1">
                  <div className="flex justify-between">
                    <span>ISOLATION WORKER</span>
                    <span className="text-secondary font-code-stream">ACTIVE: w-04</span>
                  </div>
                  <div className="flex justify-between">
                    <span>HEAP DUMP CAPTURE</span>
                    <span className="text-on-surface">422MB [RAW]</span>
                  </div>
                </div>
              </aside>

              {/* 2. CENTER COLUMN: INVESTIGATION CANVAS */}
              <section className="flex-1 min-w-0 bg-surface flex flex-col p-space-md lg:p-space-xl space-y-space-xl overflow-x-hidden">
                <div className="space-y-space-xs pb-space-sm border-b border-outline-variant/20">
                  <div className="flex items-center gap-space-sm font-label-sm text-label-sm text-outline">
                    <span className="text-primary-container font-semibold">
                      [TARGET_CRASH_VECTOR]
                    </span>
                    <span>{"//"}</span>
                    <span>CHECKOUT_SUBSYSTEM</span>
                    <span>{"//"}</span>
                    <span>FAULT_OFFSET: 0x884F</span>
                  </div>
                  <h2 className="font-display-lg text-display-lg text-primary tracking-tight uppercase max-w-4xl">
                    CHECKOUT FREEZES AFTER COUPON APPLICATION
                  </h2>
                  <p className="font-body-lg text-on-surface-variant text-body-lg max-w-3xl leading-relaxed">
                    Zero-balance order state machine fails to complete gateway session, triggering
                    recursive retry loop in{" "}
                    <span className="font-code-stream text-primary bg-surface-container-high px-1 py-0.5">
                      PaymentService.ts:142
                    </span>{" "}
                    under concurrent user sessions.
                  </p>
                </div>

                <div className="space-y-space-xs">
                  <div className="flex items-center justify-between font-label-sm text-label-sm text-outline">
                    <span className="uppercase tracking-widest">CHRONO-CORRELATION TIMELINE</span>
                    <span className="font-code-stream text-[10px] text-secondary">
                      WINDOW: 14:20:00 — 14:36:00 UTC
                    </span>
                  </div>
                  <div className="bg-surface-container-lowest p-space-md border border-outline-variant/30 space-y-space-md">
                    <div className="relative w-full h-7 flex items-end justify-between border-b border-outline-variant/40 px-2 font-label-sm text-[10px] text-outline select-none">
                      <span className="relative pb-1">| 14:20:00</span>
                      <span className="relative pb-1">| 14:25:00</span>
                      <span className="relative pb-1">| 14:30:00</span>
                      <span className="relative pb-1 text-primary-container">▲ 14:32:00</span>
                      <span className="relative pb-1">| 14:35:00</span>
                      <span className="relative pb-1">| 14:36:00</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-space-xs font-label-sm">
                      <div className="p-space-xs bg-surface-container-low border-l-2 border-outline-variant space-y-0.5">
                        <div className="text-[10px] text-outline font-code-stream">
                          14:21:04 UTC
                        </div>
                        <div className="text-[11px] font-semibold text-primary">DEPLOY v2.8.1</div>
                        <p className="text-[10px] text-on-surface-variant font-body-sm leading-tight">
                          Tag pushed by dev@acme.com
                        </p>
                      </div>
                      <div className="p-space-xs bg-surface-container-low border-l-2 border-primary-container space-y-0.5">
                        <div className="text-[10px] text-primary-container font-code-stream">
                          14:30:11 UTC
                        </div>
                        <div className="text-[11px] font-semibold text-primary">CLIENT SIGNAL</div>
                        <p className="text-[10px] text-on-surface-variant font-body-sm leading-tight">
                          Checkout hangs after SAVE100
                        </p>
                      </div>
                      <div className="p-space-xs bg-surface-container-low border-l-2 border-error space-y-0.5">
                        <div className="text-[10px] text-error font-code-stream">14:32:19 UTC</div>
                        <div className="text-[11px] font-semibold text-error">ERROR ×47 SPIKE</div>
                        <p className="text-[10px] text-on-surface-variant font-body-sm leading-tight">
                          PaymentRequestPending loop
                        </p>
                      </div>
                      <div className="p-space-xs bg-surface-container-low border-l-2 border-secondary-container space-y-0.5">
                        <div className="text-[10px] text-secondary font-code-stream">
                          14:35:41 UTC
                        </div>
                        <div className="text-[11px] font-semibold text-secondary">
                          RCA SYNTHESIZED
                        </div>
                        <p className="text-[10px] text-on-surface-variant font-body-sm leading-tight">
                          Zero-dollar bypass missing (91%)
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* EVIDENCE TOPOLOGY GRAPH */}
                <div className="space-y-space-sm" id="case-wall">
                  <div className="flex items-center justify-between font-label-sm text-label-sm text-outline">
                    <span className="uppercase tracking-widest">
                      EVIDENCE TOPOLOGY GRAPH // RELATIONAL FLOW
                    </span>
                    <span className="text-[10px] text-primary-container font-code-stream">
                      NODES: 05 / EDGES: 04
                    </span>
                  </div>
                  <div className="p-space-md bg-surface-container-lowest border border-outline-variant/30 space-y-space-md">
                    <div className="flex flex-col items-center">
                      <div className="w-full bg-surface-container-low border-l-2 border-primary-container p-space-sm font-label-sm">
                        <div className="flex items-center justify-between text-[11px] text-outline mb-1">
                          <span className="font-bold text-primary-container">
                            [01 // TELEMETRY ROOT TRIGGER]
                          </span>
                          <span className="font-code-stream">SESSION: acme_2841</span>
                        </div>
                        <div className="text-body-md text-on-surface font-mono text-[12px] bg-surface-container-lowest p-2 border border-outline-variant/20">
                          cart.total: ₹80.00 → coupon: &apos;SAVE100&apos; (Net Total: ₹0.00) → UI
                          spinner freezes indefinitely
                        </div>
                      </div>
                      <div className="flex flex-col items-center py-1">
                        <div className="h-6 w-px bg-outline-variant/60" />
                        <span className="font-label-sm text-[9px] uppercase tracking-widest text-outline bg-surface-container px-2 py-0.5 border border-outline-variant/30">
                          TRIGGERS GATEWAY INIT
                        </span>
                        <div className="h-6 w-px bg-outline-variant/60" />
                      </div>
                      <div className="w-full bg-surface-container p-space-sm border border-outline-variant/40">
                        <div className="flex justify-between items-center font-label-sm text-[11px] mb-1">
                          <span className="text-primary font-bold">
                            [02 // CHECKOUT SUBSYSTEM v2.8.1]
                          </span>
                          <span className="text-outline font-code-stream">TRACE: tr-99214a72d</span>
                        </div>
                        <p className="font-body-sm text-on-surface-variant text-[12px]">
                          Worker thread initialized checkout pipeline. Received coupon deduction,
                          evaluated order subtotal to 0, dispatched session request to Stripe
                          wrapper daemon.
                        </p>
                      </div>
                      <div className="w-full grid grid-cols-2 relative py-2">
                        <div className="flex flex-col items-center">
                          <div className="h-4 w-px bg-outline-variant/60" />
                          <span className="font-label-sm text-[9px] tracking-widest uppercase text-secondary bg-surface-container-low px-1.5 py-0.5 border border-outline-variant/30">
                            11 MIN PRIOR
                          </span>
                          <div className="h-4 w-px bg-outline-variant/60" />
                        </div>
                        <div className="flex flex-col items-center">
                          <div className="h-4 w-px bg-outline-variant/60" />
                          <span className="font-label-sm text-[9px] tracking-widest uppercase text-error bg-surface-container-low px-1.5 py-0.5 border border-outline-variant/30">
                            47 LOG SPIKES
                          </span>
                          <div className="h-4 w-px bg-outline-variant/60" />
                        </div>
                      </div>
                      <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-space-sm">
                        <div className="bg-surface-container-low p-space-sm border border-outline-variant/20 font-label-sm">
                          <div className="text-[10px] text-outline uppercase tracking-wider mb-1">
                            [COMMIT: 8a92c1]
                          </div>
                          <div className="text-[12px] font-semibold text-primary font-code-stream">
                            &quot;Optimize coupon validation&quot;
                          </div>
                          <div className="text-[10px] text-on-surface-variant font-body-sm mt-1">
                            Author: j.miller@acme.com · Removed redundant 0-dollar gateway check
                            wrapper.
                          </div>
                        </div>
                        <div className="bg-surface-container-low p-space-sm border border-outline-variant/20 font-label-sm">
                          <div className="text-[10px] text-error uppercase tracking-wider mb-1">
                            [SYSLOG INCIDENT TELEMETRY]
                          </div>
                          <div className="text-[12px] font-semibold text-error font-code-stream">
                            PaymentRequestPending ×47
                          </div>
                          <div className="text-[10px] text-on-surface-variant font-body-sm mt-1">
                            Burst in 22 seconds across 14 threads in worker-04. CPU pegged to 99.4%.
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col items-center py-2">
                        <div className="h-6 w-px bg-primary-container" />
                        <span className="font-label-sm text-[9px] uppercase tracking-widest text-primary-container bg-surface-container-low px-2 py-0.5 border border-primary-container/40">
                          SAME CODE PATH CONVERGENCE
                        </span>
                        <div className="h-6 w-px bg-primary-container" />
                      </div>
                      <div className="w-full bg-surface-container-high border-2 border-primary-container p-space-md space-y-space-xs shadow-xl relative">
                        <div className="flex items-center justify-between font-label-sm text-label-sm border-b border-outline-variant/40 pb-1">
                          <span className="text-primary-container font-bold tracking-widest">
                            [● ROOT CAUSE SYNTHESIS]
                          </span>
                          <span className="text-primary font-mono text-[11px] bg-primary-container/20 px-2 py-0.5">
                            CONFIDENCE: 91%
                          </span>
                        </div>
                        <div className="font-label-sm text-sm text-primary font-bold tracking-tight">
                          PAYMENT RETRY DEADLOCK: while (!paymentCompleted) in PaymentService.ts:142
                        </div>
                        <p className="font-code-stream text-body-sm text-on-surface-variant leading-relaxed">
                          When <span className="text-primary font-semibold">cartTotal === 0</span>,
                          the upstream payment intent is never generated (it is{" "}
                          <span className="text-error font-semibold">null</span>). The loop spins
                          unchecked attempting to poll status on a null transaction pointer until
                          hard 30,000ms gateway timeout aborts the socket.
                        </p>
                        <div className="flex items-center justify-between text-[10px] font-label-sm text-outline pt-1">
                          <span>IMPACTED SESSIONS: 14 LIVE USERS</span>
                          <span className="text-secondary">
                            ISOLATION: PASSIVE LOGGING IN EFFECT
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* REPRODUCTION WORKSPACE */}
                <div className="space-y-space-xs" id="repro-dock">
                  <div className="flex items-center justify-between font-label-sm text-label-sm text-outline">
                    <span className="uppercase tracking-widest">
                      DOCK // DETERMINISTIC SANDBOX REPRO RUNNER
                    </span>
                    <span className="text-[10px] text-outline font-code-stream">
                      CONTAINER: s2f-box-{id} (ephemeral)
                    </span>
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-3 border border-outline-variant/30 bg-surface-container-lowest divide-y lg:divide-y-0 lg:divide-x divide-outline-variant/30 font-label-sm">
                    <div className="p-space-md space-y-space-sm bg-surface-container-lowest">
                      <div className="flex justify-between items-center text-[10px] text-outline uppercase pb-1 border-b border-outline-variant/20">
                        <span className="font-semibold text-on-surface">01 // REPRO PAYLOAD</span>
                        <span className="text-primary-container">MOCK_ORDER</span>
                      </div>
                      <pre className="font-code-stream text-[11px] text-on-surface-variant leading-relaxed overflow-x-auto p-space-xs bg-surface-container-low border border-outline-variant/10">
                        <code>{`{
  "orderId": "ord_88192a",
  "cartTotal": 80.00,
  "discountCode": "SAVE100",
  "netPayable": 0.00,
  "customer": "acme_2841",
  "paymentIntent": null,
  "isZeroOrder": true
}`}</code>
                      </pre>
                      <div className="font-label-sm text-[10px] text-outline">
                        PAYLOAD MATCH:{" "}
                        <span className="text-secondary font-mono">100% BIT-FOR-BIT</span>
                      </div>
                    </div>
                    <div className="p-space-md space-y-space-sm bg-surface-container-lowest">
                      <div className="flex justify-between items-center text-[10px] text-outline uppercase pb-1 border-b border-outline-variant/20">
                        <span className="font-semibold text-on-surface">
                          02 // TEST RUNNER HARNESS
                        </span>
                        <span className="text-outline">SANDBOX</span>
                      </div>
                      <div className="p-space-xs bg-surface-container-low border border-outline-variant/10 font-code-stream text-[11px] text-on-surface leading-tight space-y-1">
                        <div className="text-outline">$ cd /workspace/checkout</div>
                        <div className="text-outline">$ export NODE_ENV=test</div>
                        <div className="text-primary-container font-semibold">
                          $ npm test -- test/checkout/coupon.test.ts
                        </div>
                        <div className="text-outline text-[10px] pt-1">
                          runner: jest-harness-isolated (v29.7)
                        </div>
                      </div>
                      <div className="font-label-sm text-[10px] text-outline flex justify-between">
                        <span>TIMEOUT BUDGET: 3000ms</span>
                        <span className="text-error font-mono">SIGNAL: SIGABRT</span>
                      </div>
                    </div>
                    <div className="p-space-md space-y-space-sm bg-surface-container-lowest">
                      <div className="flex justify-between items-center text-[10px] text-outline uppercase pb-1 border-b border-outline-variant/20">
                        <span className="font-semibold text-error">03 // EXECUTION RESULT</span>
                        <span className="text-error font-mono bg-error-container/20 px-1">
                          FAIL [1/3]
                        </span>
                      </div>
                      <div className="p-space-xs bg-surface-container-low border border-outline-variant/10 font-code-stream text-[10.5px] leading-tight space-y-1">
                        <div className="text-error font-semibold">
                          ● [FAIL] zero-balance checkout path
                        </div>
                        <div className="text-on-surface-variant text-[10px]">
                          Error: PaymentService retry loop exceeded safety threshold: 50 iterations
                          reached without state resolution.
                        </div>
                        <div className="text-outline text-[10px]">
                          at PaymentService.processOrder (PaymentService.ts:142:13)
                        </div>
                        <div className="text-on-surface text-[10px] pt-1">
                          Tests: <span className="text-error font-bold">1 failed</span>, 2 passed, 3
                          total
                        </div>
                      </div>
                      <div className="font-label-sm text-[10px] text-error flex items-center justify-between">
                        <span>EXIT CODE: 1</span>
                        <span className="font-mono uppercase">REPRODUCED DETERMINISTICALLY</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* CODE REVIEW & PATCH */}
                <div className="space-y-space-xs" id="code-patch">
                  <div className="flex items-center justify-between font-label-sm text-label-sm text-outline">
                    <span className="uppercase tracking-widest">
                      SYNTHESIZED AUTONOMOUS PATCH // DIFF MATRIX
                    </span>
                    <span className="text-secondary font-code-stream text-[11px]">
                      +6 lines / -2 lines
                    </span>
                  </div>
                  <div className="bg-surface-container-lowest border border-outline-variant/30 font-code-stream">
                    <div className="bg-surface-container-low px-space-md py-1.5 border-b border-outline-variant/20 flex items-center justify-between text-[11px] font-label-sm">
                      <div className="flex items-center gap-space-sm">
                        <span className="text-outline">FILE:</span>
                        <span className="text-primary font-bold">
                          src/checkout/PaymentService.ts
                        </span>
                        <span className="text-outline">lines 138-149</span>
                      </div>
                      <span className="text-[10px] text-secondary-container bg-surface-container px-1.5 py-0.5 border border-outline-variant/40">
                        SYNTHESIS: READY_FOR_REVIEW
                      </span>
                    </div>
                    <div className="text-[12px] leading-relaxed select-text overflow-x-auto divide-y divide-outline-variant/10">
                      <div className="px-space-md py-1 text-outline bg-surface-container-lowest flex items-center gap-4">
                        <span className="w-8 shrink-0 text-right select-none text-[10px]">138</span>
                        <span className="text-on-surface-variant">
                          const order = await this.getOrderContext(orderId);
                        </span>
                      </div>
                      <div className="px-space-md py-1 text-outline bg-surface-container-lowest flex items-center gap-4">
                        <span className="w-8 shrink-0 text-right select-none text-[10px]">139</span>
                        <span className="text-on-surface-variant">let attempt = 0;</span>
                      </div>
                      <div className="px-space-md py-1 bg-error-container/10 text-error flex items-center gap-4">
                        <span className="w-8 shrink-0 text-right select-none text-[10px] text-error/70">
                          140
                        </span>
                        <span>- while (!paymentCompleted) {"{"}</span>
                      </div>
                      <div className="px-space-md py-1 bg-error-container/10 text-error flex items-center gap-4">
                        <span className="w-8 shrink-0 text-right select-none text-[10px] text-error/70">
                          141
                        </span>
                        <span>- await this.retryPayment(order.paymentIntentId);</span>
                      </div>
                      <div className="px-space-md py-1 bg-secondary-container/10 text-secondary flex items-center gap-4">
                        <span className="w-8 shrink-0 text-right select-none text-[10px] text-secondary/70">
                          140
                        </span>
                        <span>+ // Bypass gateway auth if discount zeroes total</span>
                      </div>
                      <div className="px-space-md py-1 bg-secondary-container/10 text-secondary flex items-center gap-4">
                        <span className="w-8 shrink-0 text-right select-none text-[10px] text-secondary/70">
                          141
                        </span>
                        <span>+ if (order.total &lt;= 0) {"{"}</span>
                      </div>
                      <div className="px-space-md py-1 bg-secondary-container/10 text-secondary flex items-center gap-4">
                        <span className="w-8 shrink-0 text-right select-none text-[10px] text-secondary/70">
                          142
                        </span>
                        <span>+ return this.completeFreeOrder(order);</span>
                      </div>
                      <div className="px-space-md py-1 bg-secondary-container/10 text-secondary flex items-center gap-4">
                        <span className="w-8 shrink-0 text-right select-none text-[10px] text-secondary/70">
                          143
                        </span>
                        <span>+ {"}"}</span>
                      </div>
                      <div className="px-space-md py-1 bg-secondary-container/10 text-secondary flex items-center gap-4">
                        <span className="w-8 shrink-0 text-right select-none text-[10px] text-secondary/70">
                          144
                        </span>
                        <span>
                          + while (!paymentCompleted &amp;&amp; attempt &lt; MAX_RETRIES) {"{"}
                        </span>
                      </div>
                      <div className="px-space-md py-1 bg-secondary-container/10 text-secondary flex items-center gap-4">
                        <span className="w-8 shrink-0 text-right select-none text-[10px] text-secondary/70">
                          145
                        </span>
                        <span>+ attempt++;</span>
                      </div>
                      <div className="px-space-md py-1 text-outline bg-surface-container-lowest flex items-center gap-4">
                        <span className="w-8 shrink-0 text-right select-none text-[10px]">146</span>
                        <span className="text-on-surface-variant">
                          await this.retryPayment(order.paymentIntentId);
                        </span>
                      </div>
                      <div className="px-space-md py-1 text-outline bg-surface-container-lowest flex items-center gap-4">
                        <span className="w-8 shrink-0 text-right select-none text-[10px]">147</span>
                        <span className="text-on-surface-variant">{"}"}</span>
                      </div>
                    </div>
                    <div className="p-space-md bg-surface-container-low border-t border-outline-variant/30 grid grid-cols-1 md:grid-cols-3 gap-space-sm font-label-sm text-label-sm">
                      <div className="space-y-0.5">
                        <span className="text-outline text-[10px] uppercase">RATIONALE</span>
                        <p className="text-on-surface text-[11px] font-body-sm">
                          Zero-value orders never allocate a gateway intent; direct settlement
                          bypass is mandatory.
                        </p>
                      </div>
                      <div className="space-y-0.5">
                        <span className="text-outline text-[10px] uppercase">
                          REGRESSION RUNNER
                        </span>
                        <p className="text-secondary text-[11px] font-code-stream">
                          coupon.test.ts → PASS (48/48 passed)
                        </p>
                      </div>
                      <div className="space-y-0.5">
                        <span className="text-outline text-[10px] uppercase">RISK SCORE</span>
                        <p className="text-primary-container text-[11px] font-semibold">
                          LOW · ZERO API CONTRACT BREAK
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* APPROVAL ACTION — disabled: no backend behind it yet. */}
                <div className="p-space-md bg-surface-container-low border border-outline-variant/30 flex flex-col md:flex-row items-center justify-between gap-space-md">
                  <div className="space-y-1">
                    <div className="flex items-center gap-space-sm font-label-sm text-label-sm">
                      <span className="text-secondary font-bold">[● READY TO SHIP]</span>
                      <span className="text-outline font-code-stream">
                        STAGE: CANARY_TARGET (worker-04)
                      </span>
                    </div>
                    <p className="font-body-sm text-on-surface-variant text-[12px]">
                      Root cause verified via sandbox-{id}. All 48 regression tests passing. Pull
                      request draft synthesized with automated rollback hooks.
                    </p>
                  </div>
                  <button
                    type="button"
                    disabled
                    title="Design preview only — approvals and PR creation ship with the real agent workflow"
                    className="shrink-0 bg-primary-container text-on-primary-container font-label-lg text-label-lg font-bold uppercase tracking-wider px-space-xl py-space-sm border border-primary-container flex items-center gap-2 cursor-not-allowed opacity-60"
                  >
                    <span className="material-symbols-outlined text-lg">check_circle</span>
                    APPROVE &amp; CREATE PR
                  </button>
                </div>

                {/* TERMINAL COMMAND BAR — display only, not wired to anything. */}
                <div className="bg-surface-container-lowest border border-outline-variant/40 p-space-sm space-y-space-xs font-label-sm">
                  <div className="flex items-center gap-space-sm">
                    <span className="text-primary-container font-mono font-bold">&gt;</span>
                    <input
                      className="w-full bg-transparent border-none text-primary font-code-stream text-body-sm focus:outline-none"
                      readOnly
                      type="text"
                      value={`investigate payment-service --trace-mcp --sandbox ${id} --verify-diff`}
                    />
                    <span className="h-4 w-2 bg-primary-container animate-pulse shrink-0" />
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-1 border-t border-outline-variant/20 font-label-sm text-[10px]">
                    <button
                      type="button"
                      disabled
                      className="px-2 py-0.5 bg-surface-container text-on-surface-variant cursor-not-allowed"
                    >
                      [ trace checkout ]
                    </button>
                    <button
                      type="button"
                      disabled
                      className="px-2 py-0.5 bg-surface-container text-on-surface-variant cursor-not-allowed"
                    >
                      [ inspect deployment v2.8.1 ]
                    </button>
                    <button
                      type="button"
                      disabled
                      className="px-2 py-0.5 bg-surface-container text-on-surface-variant cursor-not-allowed"
                    >
                      [ re-run sandbox repro ]
                    </button>
                    <button
                      type="button"
                      disabled
                      className="px-2 py-0.5 bg-surface-container text-on-surface-variant cursor-not-allowed"
                    >
                      [ diff commits 8a92c1..HEAD ]
                    </button>
                    <button
                      type="button"
                      disabled
                      className="px-2 py-0.5 bg-surface-container text-error/80 cursor-not-allowed"
                    >
                      [ abort sandbox ]
                    </button>
                  </div>
                </div>
              </section>

              {/* 3. RIGHT COLUMN: LIVE CONTEXT INSTRUMENT */}
              <aside className="w-full lg:sticky lg:top-14 lg:w-[300px] lg:max-h-[calc(100vh-3.5rem)] lg:self-start lg:overflow-y-auto shrink-0 bg-surface-container-lowest border-l border-outline-variant/30 p-space-md space-y-space-lg flex flex-col justify-between">
                <div className="space-y-space-lg">
                  <div className="space-y-space-xs pb-space-sm border-b border-outline-variant/20">
                    <div className="font-label-sm text-[10px] text-outline uppercase tracking-widest flex items-center justify-between">
                      <span>ACTIVE INSPECTION FOCUS</span>
                      <span className="text-primary-container">HEX-SEL</span>
                    </div>
                    <div className="font-label-sm text-label-sm text-primary font-bold flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 bg-primary-container rounded-none" />
                      ROOT CAUSE SYNTHESIS #{id}
                    </div>
                    <div className="font-code-stream text-[11px] text-outline">
                      TARGET: PaymentService.ts:142
                    </div>
                  </div>
                  <div className="space-y-space-sm font-label-sm">
                    <div className="flex items-center justify-between text-label-sm">
                      <span className="text-outline uppercase tracking-wider text-[11px]">
                        RCA CONFIDENCE
                      </span>
                      <span className="text-primary-container font-bold text-sm font-mono">
                        91.4%
                      </span>
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-[10px] text-on-surface-variant">
                        <span>EVIDENCE STRENGTH</span>
                        <span className="font-mono text-primary">90%</span>
                      </div>
                      <div className="flex gap-1 h-2">
                        {Array.from({ length: 9 }).map((_, i) => (
                          <div key={i} className="flex-1 bg-primary-container" />
                        ))}
                        <div className="flex-1 bg-surface-container-high" />
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-[10px] text-on-surface-variant">
                        <span>LOG CORRELATION</span>
                        <span className="font-mono text-primary">92%</span>
                      </div>
                      <div className="flex gap-1 h-2">
                        {Array.from({ length: 9 }).map((_, i) => (
                          <div key={i} className="flex-1 bg-secondary-container" />
                        ))}
                        <div className="flex-1 bg-surface-container-high" />
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-[10px] text-on-surface-variant">
                        <span>SANDBOX REPRODUCIBILITY</span>
                        <span className="font-mono text-secondary">100%</span>
                      </div>
                      <div className="flex gap-1 h-2">
                        {Array.from({ length: 10 }).map((_, i) => (
                          <div key={i} className="flex-1 bg-secondary" />
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="p-space-sm bg-surface-container-low border border-outline-variant/30 space-y-space-xs font-label-sm text-[11px]">
                    <div className="text-[10px] text-outline uppercase tracking-wider pb-1 border-b border-outline-variant/20">
                      METADATA DISSECTION
                    </div>
                    <div className="flex justify-between">
                      <span className="text-outline">FILE PATH:</span>
                      <span className="text-on-surface truncate max-w-[150px] font-code-stream">
                        src/checkout/PaymentService.ts
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-outline">TARGET LINE:</span>
                      <span className="text-primary font-code-stream font-bold">142</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-outline">AUTHOR:</span>
                      <span className="text-on-surface font-mono">j.miller@acme.com</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-outline">BLAST RADIUS:</span>
                      <span className="text-error font-mono">14 SESSIONS</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-outline">CONTAINMENT:</span>
                      <span className="text-secondary font-mono">CANARY ISOLATED</span>
                    </div>
                  </div>
                  <div className="space-y-space-xs font-label-sm" id="telemetry-feed">
                    <div className="flex items-center justify-between text-[10px] text-outline uppercase tracking-wider pb-1 border-b border-outline-variant/20">
                      <span>MCP AGENT PIPELINE FEED</span>
                      <span className="text-secondary flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-ping" />
                        STREAMING
                      </span>
                    </div>
                    <div className="bg-surface-container-lowest p-space-xs border border-outline-variant/20 space-y-1.5 font-code-stream text-[10.5px]">
                      <div className="flex items-start gap-1.5 text-on-surface-variant">
                        <span className="text-outline shrink-0">14:33:12</span>
                        <span className="text-primary-container shrink-0">[LOGS]</span>
                        <span className="truncate">searched 4,182 logs (47 matches)</span>
                      </div>
                      <div className="flex items-start gap-1.5 text-on-surface-variant">
                        <span className="text-outline shrink-0">14:33:19</span>
                        <span className="text-secondary shrink-0">[GIT]</span>
                        <span className="truncate">inspected 7 commits acme/checkout</span>
                      </div>
                      <div className="flex items-start gap-1.5 text-on-surface-variant">
                        <span className="text-outline shrink-0">14:33:44</span>
                        <span className="text-primary-container shrink-0">[RCA]</span>
                        <span className="truncate">correlation matched v2.8.1 bump</span>
                      </div>
                      <div className="flex items-start gap-1.5 text-on-surface-variant">
                        <span className="text-outline shrink-0">14:34:01</span>
                        <span className="text-secondary shrink-0">[SANDBOX]</span>
                        <span className="truncate">isolated docker container {id}</span>
                      </div>
                      <div className="flex items-start gap-1.5 text-on-surface-variant">
                        <span className="text-outline shrink-0">14:35:22</span>
                        <span className="text-primary-container shrink-0">[SYNTH]</span>
                        <span className="truncate">patch generated (+6, -2 lines)</span>
                      </div>
                      <div className="flex items-start gap-1.5 text-on-surface-variant">
                        <span className="text-outline shrink-0">14:36:01</span>
                        <span className="text-secondary shrink-0">[RUNNER]</span>
                        <span className="truncate">48/48 regression tests passed</span>
                      </div>
                      <div className="flex items-start gap-1.5 text-primary">
                        <span className="text-outline shrink-0">14:36:18</span>
                        <span className="text-primary-container shrink-0">[GATE]</span>
                        <span className="truncate">awaiting forensic operator signoff</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="pt-space-md border-t border-outline-variant/20 font-label-sm text-[10px] space-y-1">
                  <div className="flex justify-between text-outline">
                    <span>FORENSIC PROTOCOL</span>
                    <span className="text-on-surface font-mono">v4.1.0-STRICT</span>
                  </div>
                  <div className="flex justify-between text-outline">
                    <span>SOCKET CONNECTION</span>
                    <span className="text-secondary font-mono">WSS://S2F-LIVE:443</span>
                  </div>
                </div>
              </aside>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
