import { notFound } from "next/navigation";
import Link from "next/link";
import { listEpisodes, loadEpisode } from "../../../../../lib/data";
import { base62Decode } from "../../../../../lib/base62";
import { PredictionCard } from "../../../../../components/Prediction";

type Params = {
  params: { id: string; pid: string };
};

export async function generateStaticParams() {
  const episodes = listEpisodes();
  return episodes.flatMap((episodeId) => {
    const episode = loadEpisode(episodeId);
    if (!episode) return [];
    return episode.predictions.map((p) => ({
      id: episodeId,
      pid: p.encoded_id
    }));
  });
}

export default function PredictionDetail({ params }: Params) {
  const episode = loadEpisode(params.id);
  if (!episode) {
    notFound();
  }

  let decodedId = "";
  try {
    decodedId = base62Decode(params.pid);
  } catch {
    decodedId = "";
  }
  const prediction = episode.predictions.find(
    (p) => p.encoded_id === params.pid || p.id === decodedId
  );
  if (!prediction) {
    notFound();
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-white/70">
          <Link prefetch={false} href="/episodes" className="hover:underline">
            Episodes
          </Link>{" "}
          /{" "}
          <Link prefetch={false} href={`/episodes/${episode.id}`} className="hover:underline">
            {episode.title || episode.id}
          </Link>
        </div>
        <Link
          prefetch={false}
          href={`/episodes/${episode.id}`}
          className="text-sm text-white/80 underline-offset-4 hover:text-white"
        >
          Back
        </Link>
      </div>
      <PredictionCard prediction={prediction} youtube={episode.youtube} />
    </div>
  );
}
