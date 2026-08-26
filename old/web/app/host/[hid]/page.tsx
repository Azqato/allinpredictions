import { notFound } from "next/navigation";
import { HostPredictionsList } from "../../../components/HostPredictionsList";
import { collectTags } from "../../../lib/stats";
import {
  loadAllEpisodes,
  loadPredictionsForHost,
  type HostPredictionEntry,
} from "../../../lib/data";
import Link from "next/link";

export async function generateStaticParams() {
  const hosts = new Set<string>();
  for (const ep of loadAllEpisodes()) {
    for (const p of ep.predictions) {
      hosts.add(p.who);
    }
  }
  return Array.from(hosts).map((hid) => ({ hid }));
}

export default function HostPage({ params }: { params: { hid: string } }) {
  const host = (params.hid || "").toLowerCase();
  if (!host) return notFound();

  const entries = loadPredictionsForHost(host);
  if (entries.length === 0) return notFound();

  const episodes = loadAllEpisodes();
  const tags = collectTags(
    episodes.map((ep) => ({
      ...ep,
      predictions: ep.predictions.filter((p) => p.who === host),
    }))
  );

  const items = entries.map((entry: HostPredictionEntry) => ({
    prediction: entry.prediction,
    episodeTitle: entry.episode.title,
    episodePublished: entry.episode.published_iso || entry.episode.published,
    episodeId: entry.episode.id,
    youtube: entry.episode.youtube,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold text-white">
          {host.charAt(0).toUpperCase() + host.slice(1)}
        </h1>
        <Link
          prefetch={false}
          href="/"
          className="text-sm text-white/70 underline-offset-4 hover:text-white"
        >
          ← Back home
        </Link>
      </div>
      <HostPredictionsList host={host} tags={tags} items={items} />
    </div>
  );
}
