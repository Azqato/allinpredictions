import Link from "next/link";
import type { Metadata } from "next";
import { STATUS_DESCRIPTIONS } from "../../lib/const";

export const metadata: Metadata = {
  title: "About | All-In Predictions",
  description: "Background on the All-In Predictions project.",
};

export default function AboutPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold text-white">About</h1>
        <Link
          prefetch={false}
          href="/"
          className="text-sm text-white/70 underline-offset-4 hover:text-white"
        >
          ← Back home
        </Link>
      </div>
      <div className="space-y-4 text-white/80 leading-relaxed">
        <p>
          This project is an unofficial experiment exploring how AI can be used for automated fact-checking of predictions. Podcasts are full of forward-looking statements, and with modern tools we can build an end-to-end pipeline that transcribes episodes, extracts predictions, and evaluates whether they ultimately came true using automated web research.
        </p>
        <p>
          Here we evaluate the All-In podcast, which offers a large archive of episodes and hosts who frequently make predictions about the future. This underlying code could be forked and modified to evaluate other podcasts with minor modifications.
        </p>
        <div className="mt-6 rounded-lg border border-white/10 bg-white/5 p-4">
          <p className="text-sm font-semibold text-white">Prediction classification descriptions</p>
          <ul className="mt-2 space-y-2 text-sm text-white/80">
            <li>
              <span className="inline-flex items-center gap-2">
                <span className="rounded px-2 py-1 text-xs font-semibold bg-emerald-500/20 text-emerald-100">
                  Right
                </span>
                <span>{STATUS_DESCRIPTIONS.right}</span>
              </span>
            </li>
            <li>
              <span className="inline-flex items-center gap-2">
                <span className="rounded px-2 py-1 text-xs font-semibold bg-rose-500/20 text-rose-100">
                  Wrong
                </span>
                <span>{STATUS_DESCRIPTIONS.wrong}</span>
              </span>
            </li>
            <li>
              <span className="inline-flex items-center gap-2">
                <span className="rounded px-2 py-1 text-xs font-semibold bg-amber-500/20 text-amber-100">
                  Ambiguous
                </span>
                <span>{STATUS_DESCRIPTIONS.ambiguous}</span>
              </span>
            </li>
            <li>
              <span className="inline-flex items-center gap-2">
                <span className="rounded px-2 py-1 text-xs font-semibold bg-gray-500/20 text-gray-100">
                  Inconclusive
                </span>
                <span>{STATUS_DESCRIPTIONS.inconclusive}</span>
              </span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
