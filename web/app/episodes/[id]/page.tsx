import { notFound } from "next/navigation";
import Link from "next/link";
import { PredictionCard } from "../../../components/Prediction";
import { listEpisodes, loadEpisode } from "../../../lib/data";

type Params = {
  params: { id: string };
};

export async function generateStaticParams() {
  const episodes = listEpisodes();
  return episodes.map((episode) => ({
    id: episode,
  }))
}

export default function EpisodeDetail({ params }: Params) {
  const episode = loadEpisode(params.id);
  if (!episode) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">
            {episode.title || episode.id}
          </h1>
          <div className="text-sm text-slate-400">
            {episode.published || "Unknown date"}
          </div>
        </div>
        <Link
          prefetch={false}
          href="/episodes"
          className="text-sm text-white/80 underline-offset-4 hover:text-white"
        >
          Back to episodes
        </Link>
      </div>

      <div className="space-y-3">
        {episode.predictions.map((p) => (
          <PredictionCard
            key={p.id}
            prediction={p}
            youtube={episode.youtube}
            collapsible
          />
        ))}
        {episode.predictions.length === 0 && (
          <div className="rounded border border-white/10 p-4 text-sm text-white/80">
            No predictions found for this episode.
          </div>
        )}
      </div>
    </div>
  );
}
