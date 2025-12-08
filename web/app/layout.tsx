import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import { WarningBanner } from "../components/WarningBanner";

const LAST_UPDATED_TEXT = "Last updated Nov 29, 2025";

export const metadata: Metadata = {
  title: "All-In Predictions",
  description: "Validating every prediction made on the All-In Podcast with AI",
  openGraph: {
    title: "All-In Predictions",
    description: "Validating every prediction made on the All-In Podcast with AI",
    images: [
      {
        url: "https://allin-predictions.pages.dev/og.png",
        width: 1682,
        height: 1098,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "All-In Predictions",
    description: "Validating every prediction made on the All-In Podcast with AI",
    images: ["https://allin-predictions.pages.dev/og.png"],
  }
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#080d0b] text-white">
        <header className="border-b border-white/10 backdrop-blur">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4 gap-4">
            <div className="flex items-center gap-4">
              <Link prefetch={false} href="/" className="text-lg text-white">
                <strong>ALL IN</strong><span className="pl-3">Predictions</span>
              </Link>
              <nav className="flex items-center gap-3 text-sm text-white/70">
                <Link prefetch={false} href="/episodes" className="hover:text-white">
                  Episodes
                </Link>
                <Link prefetch={false} href="/about" className="hover:text-white">
                  About
                </Link>
                <a
                  href="https://github.com/schnerd/podcast-predictions"
                  className="hover:text-white"
                  target="_blank"
                  rel="noreferrer"
                >
                  GitHub
                </a>
              </nav>
            </div>
            <div className="text-xs max-md:hidden text-white/60">{LAST_UPDATED_TEXT}</div>
          </div>
        </header>
        <WarningBanner />
        <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
        <footer>
          <div className="mx-auto max-w-2xl px-6 pb-6 pt-4 text-center text-xs text-white/50">
            Disclaimer: Unofficial project; data is generated automatically via transcription, speaker-matching, and
            LLM-driven prediction extraction/validation (with web search). It’s best-effort and may
            contain errors, omissions, or misattributions. {LAST_UPDATED_TEXT}.
          </div>
        </footer>
      </body>
    </html>
  );
}
