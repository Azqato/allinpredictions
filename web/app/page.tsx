import Link from "next/link";
import { loadAllEpisodes } from "../lib/data";
import { HostCharts } from "../components/HostCharts";
import { collectTags } from "../lib/stats";
import { useMemo } from "react";

export default function Home() {
  const episodesFull = loadAllEpisodes();
  const episodes = useMemo(() => episodesFull.map(ep => {
    return {
      ...ep,
      predictions: ep.predictions.map(p => {
        const clone = {...p};
        // Save bandwidth - these aren't used on this page and just bloat
        // the payload (since HostCharts is a client component)
        clone.prediction = '';
        clone.quote = '';
        delete clone.explanation;
        return clone;
      })
    }
  }), [episodesFull]);
  const sortedEpisodes = [...episodes].sort((a, b) => {
    const ad = a.published_iso || a.published || "";
    const bd = b.published_iso || b.published || "";
    const da = ad ? new Date(ad) : null;
    const db = bd ? new Date(bd) : null;
    if (da && db) return da.getTime() - db.getTime();
    return 0;
  });
  const tags = collectTags(episodes);

  return (
    <div className="space-y-8">
      <section>
        <HostCharts episodes={episodes} tags={tags} />
      </section>

      <section className="border-t border-neutral-800 pt-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">Episodes</h2>
          <Link 
            prefetch={false}
            href="/episodes"
            className="text-sm text-white/80 underline-offset-4 hover:text-white"
          >
            View all
          </Link>
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {sortedEpisodes.slice(0, 6).map((ep) => (
            <Link
              prefetch={false}
              key={ep.id}
              href={`/episodes/${ep.id}`}
              className="rounded-lg border border-white/10 p-4 hover:border-white/20"
            >
              <div className="text-lg font-semibold text-white">{ep.title || ep.id}</div>
              <div className="text-sm text-white/60">
                {ep.published || "Unknown date"}
              </div>
              <div className="mt-2 text-sm text-white/80">
                Predictions: {ep.meta?.prediction_count ?? ep.predictions.length}
              </div>
              {ep.meta?.count_by_result ? (
                <div className="mt-1 text-xs text-white/60">
                  Results:{" "}
                  {Object.entries(ep.meta.count_by_result)
                    .map(([k, v]) => `${k}:${v}`)
                    .join(" • ")}
                </div>
              ) : null}
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
