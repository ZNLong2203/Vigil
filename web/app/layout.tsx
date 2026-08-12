import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { StatusBar } from "@/components/StatusBar";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Vigil — an agent fleet that keeps watch",
  description:
    "Long-running care coordination agents on Gemini and Google Cloud. All data shown is synthetic.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="flex items-center gap-4 px-4 h-12 border-b border-[var(--line-soft)] shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="live-dot" aria-hidden />
            <span className="mono text-sm tracking-[0.18em] uppercase">Vigil</span>
          </div>
          <Nav />
          <div className="ml-auto flex items-center gap-3">
            {/* Non-negotiable, and it stays on screen during filming. */}
            <span className="chip chip-muted">All data synthetic</span>
            <span className="eyebrow hidden sm:inline">care-subject-001</span>
          </div>
        </header>

        <main className="flex-1 min-h-0">{children}</main>

        <StatusBar />
      </body>
    </html>
  );
}
