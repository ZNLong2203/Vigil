"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * Overview first, because a reader arriving cold needs to be told what this is
 * before being shown any of it. Then two caregiver surfaces, one decision
 * surface, and two operator surfaces.
 */
const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/timeline/", label: "Timeline" },
  { href: "/intake/", label: "Intake" },
  { href: "/approvals/", label: "Approvals" },
  { href: "/fleet/", label: "Fleet" },
  { href: "/trace/", label: "Trace" },
] as const;

export function Nav() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-0.5" aria-label="Primary">
      {LINKS.map(({ href, label }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className="px-2.5 py-1 rounded-md text-sm transition-colors"
            style={{
              color: active ? "var(--text-0)" : "var(--text-2)",
              background: active ? "var(--bg-2)" : "transparent",
            }}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
