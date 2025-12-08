import Link from "next/link";
import { listEpisodes, loadEpisode } from "../../lib/data";

export async function generateStaticParams() {
  return [];
}

export default function EpisodesPage() {
  const ids = listEpisodes();
  const episodes = ids
    .map((id) => loadEpisode(id))
    .filter(
      (ep): ep is NonNullable<typeof ep> => Boolean(ep) && (ep?.predictions?.length || 0) > 0
    );
  episodes.sort((a, b) => {
    const ad = a.published_iso || a.published || "";
    const bd = b.published_iso || b.published || "";
    const da = ad ? new Date(ad) : null;
    const db = bd ? new Date(bd) : null;
    if (da && db) return da.getTime() - db.getTime();
    return 0;
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">Episodes</h1>
      <div className="grid gap-3 sm:grid-cols-2">
        {episodes.map((ep) => (
          <Link
            prefetch={false}
            key={ep.id}
            href={`/episodes/${ep.id}`}
            className="rounded-lg border border-white/10 p-4 hover:border-white/20"
          >
            <div className="text-lg font-semibold text-white">
              {ep.title || ep.id}
            </div>
            <div className="text-sm text-white/60">
              {ep.published || "Unknown date"}
            </div>
            <div className="mt-1 text-sm text-white/80">
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
    </div>
  );
}
