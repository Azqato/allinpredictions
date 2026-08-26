import { notFound } from "next/navigation";
import Link from "next/link";
import {
  findPredictionByHostAndEncoded,
  loadAllEpisodes,
} from "../../../../../lib/data";
import { PredictionCard } from "../../../../../components/Prediction";
import { capitalize } from "../../../../../lib/utils";

export async function generateStaticParams() {
  const params: { hid: string; pid: string }[] = [];
  for (const ep of loadAllEpisodes()) {
    for (const p of ep.predictions) {
      params.push({ hid: p.who, pid: p.encoded_id });
    }
  }
  return params;
}

export default function HostPredictionPage({
  params,
}: {
  params: { hid: string; pid: string };
}) {
  const host = (params.hid || "").toLowerCase();
  const pid = params.pid;
  if (!host || !pid) return notFound();

  const entry = findPredictionByHostAndEncoded(host, pid);
  if (!entry) return notFound();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-white/60">Prediction</div>
          <div className="text-2xl font-semibold text-white">
            {capitalize(host)}
          </div>
        </div>
        <div className="flex items-center gap-3 text-sm text-white/70">
          <Link prefetch={false} href={`/host/${host}`} className="underline-offset-4 hover:text-white">
            ← Back to host
          </Link>
          <Link
            prefetch={false}
            href={`/episodes/${entry.episode.id}`}
            className="underline-offset-4 hover:text-white"
          >
            Episode
          </Link>
        </div>
      </div>
      <PredictionCard
        prediction={entry.prediction}
        youtube={entry.episode.youtube}
        headerMeta={{
          episodeId: entry.episode.id,
          episodeDate: entry.episode.published
            ? new Date(entry.episode.published).toLocaleDateString()
            : undefined,
        }}
      />
    </div>
  );
}
