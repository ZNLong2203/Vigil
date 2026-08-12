import type { ReactNode } from "react";

/**
 * The line every screen carries saying what it is for.
 *
 * The first version of this UI opened each screen straight into data, which
 * works for someone who already knows the system and fails for everyone else —
 * a reader landing cold has to reverse-engineer the purpose from the contents.
 * "Fleet registry" means nothing until you know why a registry matters here.
 *
 * So: what this screen is, and — the part usually left out — **what to look
 * for**. A title says where you are. Only the second sentence tells you what you
 * are supposed to notice.
 */
export function ScreenIntro({
  title,
  children,
  aside,
}: {
  title: string;
  children: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <header className="mb-5">
      <div className="flex items-baseline justify-between gap-4 flex-wrap">
        <h1 className="text-[1.15rem] font-medium tracking-tight">{title}</h1>
        {aside && <div className="flex items-center gap-2">{aside}</div>}
      </div>
      <p className="screen-intro mt-1.5">{children}</p>
    </header>
  );
}

/** Points at the one thing on a screen a cold reader would scroll past. */
export function Callout({
  tone = "info",
  children,
}: {
  tone?: "info" | "deny" | "ok" | "wait";
  children: ReactNode;
}) {
  const cls =
    tone === "deny"
      ? "callout callout-deny"
      : tone === "ok"
        ? "callout callout-ok"
        : tone === "wait"
          ? "callout"
          : "callout callout-info";

  return (
    <div className={cls}>
      <span aria-hidden className="shrink-0 mt-0.5">
        ↳
      </span>
      <span>{children}</span>
    </div>
  );
}
