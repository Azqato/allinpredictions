import fs from "fs";
import path from "path";
import { base62Encode } from "./base62";

export type Prediction = {
  id: string;
  encoded_id: string;
  episode_id: string;
  who: string;
  quote: string;
  timestamp: string;
  timestamp_seconds?: number;
  prediction: string;
  result?: string;
  explanation?: string;
  sources?: any;
  tags?: string[];
  episode_title?: string;
  episode_published?: string;
};

export type EpisodeData = {
  id: string;
  title?: string;
  published?: string;
  published_iso?: string;
  youtube?: string;
  predictions: Prediction[];
  meta?: {
    prediction_count?: number;
    count_by_who?: Record<string, number>;
    validation_count?: number;
    count_by_result?: Record<string, number>;
  };
};

const TRANSCRIPTS_ROOT = path.join(
  process.cwd(),
  "..",
  "data",
  "processed",
  "transcripts_speechmatics"
);

const VALID_SPEAKERS = new Set(["jason", "chamath", "friedberg", "sacks"]);

let EPISODE_CACHE: EpisodeData[] | null = null;
let PREDICTION_INDEX: Map<string, HostPredictionEntry> | null = null;

function safeReadJSON(filePath: string): any | null {
  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function listEpisodes(): string[] {
  if (!fs.existsSync(TRANSCRIPTS_ROOT)) return [];
  return fs
    .readdirSync(TRANSCRIPTS_ROOT, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .sort();
}

export function loadEpisode(id: string): EpisodeData | null {
  const episodeDir = path.join(TRANSCRIPTS_ROOT, id);
  if (!fs.existsSync(episodeDir)) return null;

  const meta = safeReadJSON(path.join(episodeDir, "metadata.json")) || {};
  let youtubeUrl = meta.youtube_url;
  if (!youtubeUrl) {
    const episodesIndex =
      (safeReadJSON(
        path.join(process.cwd(), "..", "data", "processed", "all_in_episodes.json")
      ) as any[]) || [];
    const metaIndexMatch =
      episodesIndex.find((e) => e?.episode_id === id) ||
      episodesIndex.find((e) => (e?.audio_filename || "").startsWith(id));
    youtubeUrl = metaIndexMatch?.youtube_url || youtubeUrl;
  }
  const published_iso = meta.published_iso || meta.published_iso8601 || null;

  const predRaw = safeReadJSON(path.join(episodeDir, "predictions.json")) || {};
  const preds: Prediction[] = predRaw.predictions || [];
  const checks =
    safeReadJSON(path.join(episodeDir, "predictions_check.json")) || {};
  const checkMap: Record<string, any> = {};
  for (const item of checks.predictions || []) {
    if (item.id) checkMap[item.id] = item;
  }

  const merged: Prediction[] = [];
  for (const p of preds) {
    const whoNorm = (p.who || "").toLowerCase();
    if (!VALID_SPEAKERS.has(whoNorm)) continue;
    const check = checkMap[p.id];
    const mergedPred: Prediction = {
      ...p,
      who: whoNorm,
      encoded_id: base62Encode(p.id),
      episode_id: id,
      ...(check
        ? {
            result: check.result,
            explanation: check.explanation,
          }
        : {}),
    };
    // parse timestamp to seconds for deep links
    const tsMatch = (p.timestamp || "").match(
      /(?:(\d+):)?(\d{2}):(\d{2})(?:\.(\d{3}))?/
    );
    if (tsMatch) {
      const hours = parseInt(tsMatch[1] || "0", 10);
      const minutes = parseInt(tsMatch[2] || "0", 10);
      const seconds = parseInt(tsMatch[3] || "0", 10);
      mergedPred.timestamp_seconds = hours * 3600 + minutes * 60 + seconds;
    }
    merged.push(mergedPred);
  }

  const countByWho: Record<string, number> = {};
  for (const p of merged) {
    countByWho[p.who] = (countByWho[p.who] || 0) + 1;
  }
  const countByResult: Record<string, number> = {};
  for (const p of merged) {
    const key = p.result || "unvalidated";
    countByResult[key] = (countByResult[key] || 0) + 1;
  }

  return {
    id,
    title: meta.title,
    published: meta.published,
    published_iso,
    predictions: merged,
    youtube: youtubeUrl,
    meta: {
      prediction_count: merged.length,
      count_by_who: countByWho,
      validation_count: merged.filter((p) => p.result).length,
      count_by_result: countByResult,
    },
  };
}

export function loadAllEpisodes(opts?: { useCache?: boolean }): EpisodeData[] {
  const useCache = opts?.useCache ?? true;
  if (useCache && EPISODE_CACHE) return EPISODE_CACHE;
  const episodes = listEpisodes()
    .map((id) => loadEpisode(id))
    .filter((e): e is EpisodeData => Boolean(e));
  if (useCache) {
    EPISODE_CACHE = episodes;
  }
  // reset index if episodes change
  PREDICTION_INDEX = null;
  return episodes;
}

export type HostPredictionEntry = {
  prediction: Prediction;
  episode: EpisodeData;
};

function ensurePredictionIndex(): Map<string, HostPredictionEntry> {
  if (PREDICTION_INDEX) return PREDICTION_INDEX;
  const index = new Map<string, HostPredictionEntry>();
  for (const ep of loadAllEpisodes()) {
    for (const p of ep.predictions) {
      const key = `${p.who}::${p.encoded_id}`;
      index.set(key, { prediction: p, episode: ep });
    }
  }
  PREDICTION_INDEX = index;
  return index;
}

export function loadPredictionsForHost(host: string): HostPredictionEntry[] {
  const normalized = host.toLowerCase();
  const entries: HostPredictionEntry[] = [];
  const index = ensurePredictionIndex();
  for (const [key, entry] of index.entries()) {
    if (key.startsWith(`${normalized}::`)) {
      entries.push(entry);
    }
  }
  return entries;
}

export function findPredictionByHostAndEncoded(
  host: string,
  encodedId: string
): HostPredictionEntry | null {
  const normalized = host.toLowerCase();
  const index = ensurePredictionIndex();
  return index.get(`${normalized}::${encodedId}`) || null;
}

export function aggregateBySpeaker(episodes: EpisodeData[]) {
  const stats: Record<
    string,
    {
      right: number;
      wrong: number;
      ambiguous: number;
      inconclusive: number;
      unvalidated: number;
    }
  > = {};
  const ensure = (who: string) => {
    stats[who] ||= {
      right: 0,
      wrong: 0,
      ambiguous: 0,
      inconclusive: 0,
      unvalidated: 0,
    };
    return stats[who];
  };

  for (const ep of episodes) {
    for (const p of ep.predictions) {
      const bucket = ensure(p.who);
      switch (p.result) {
        case "right":
          bucket.right += 1;
          break;
        case "wrong":
          bucket.wrong += 1;
          break;
        case "ambiguous":
          bucket.ambiguous += 1;
          break;
        case "inconclusive":
          bucket.inconclusive += 1;
          break;
        default:
          bucket.unvalidated += 1;
      }
    }
  }
  return stats;
}
