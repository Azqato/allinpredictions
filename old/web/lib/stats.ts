import type { EpisodeData, Prediction } from "./data";

export type HostResultKey =
  | "right"
  | "wrong"
  | "ambiguous"
  | "inconclusive"
  | "unvalidated";

export type HostStats = Record<string, Record<HostResultKey, number>>;

export type BucketedStats = Record<
  string,
  Record<string, Record<HostResultKey, number>>
>;

const EMPTY_BUCKET = {
  right: 0,
  wrong: 0,
  ambiguous: 0,
  inconclusive: 0,
  unvalidated: 0,
};

function ensureHost(stats: HostStats, who: string) {
  stats[who] ||= { ...EMPTY_BUCKET };
  return stats[who];
}

function matchesTag(prediction: Prediction, tag: string | null): boolean {
  if (!tag) return true;
  return Array.isArray(prediction.tags) && prediction.tags.includes(tag);
}

export function aggregateHostStats(
  episodes: EpisodeData[],
  tag: string | null
): HostStats {
  const stats: HostStats = {};
  const hosts = new Set<string>();
  for (const ep of episodes) {
    for (const p of ep.predictions) {
      hosts.add(p.who);
    }
  }
  for (const host of hosts) {
    stats[host] = { ...EMPTY_BUCKET };
  }

  for (const ep of episodes) {
    for (const p of ep.predictions) {
      if (!matchesTag(p, tag)) continue;
      const bucket = ensureHost(stats, p.who);
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

export function buildYearlyStats(
  episodes: EpisodeData[],
  tag: string | null
): BucketedStats {
  const yearly: BucketedStats = {};
  const hosts = new Set<string>();
  for (const ep of episodes) {
    for (const p of ep.predictions) {
      hosts.add(p.who);
    }
  }
  for (const host of hosts) {
    yearly[host] = {};
  }

  for (const ep of episodes) {
    const pub = ep.published_iso || ep.published || "";
    let year = "";
    if (pub) {
      const dt = new Date(pub);
      if (!Number.isNaN(dt.getTime())) {
        year = String(dt.getUTCFullYear());
      }
    }
    if (!year) continue;
    for (const p of ep.predictions) {
      if (!matchesTag(p, tag)) continue;
      const host = p.who;
      yearly[host] ||= {};
      yearly[host][year] ||= { ...EMPTY_BUCKET };
      const bucket = yearly[host][year];
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
  return yearly;
}

export function buildTopicStats(
  episodes: EpisodeData[],
  tag: string | null,
  tagList?: string[]
): BucketedStats {
  const topics: BucketedStats = {};
  const hosts = new Set<string>();
  for (const ep of episodes) {
    for (const p of ep.predictions) {
      hosts.add(p.who);
    }
  }
  for (const host of hosts) {
    topics[host] = {};
  }

  const labels = tagList && tagList.length > 0 ? tagList : collectTags(episodes);

  for (const ep of episodes) {
    for (const p of ep.predictions) {
      if (tag && !(Array.isArray(p.tags) && p.tags.includes(tag))) {
        continue;
      }
      const applicableTags =
        tag && p.tags?.includes(tag) ? [tag] : (p.tags || []);
      for (const tg of applicableTags) {
        if (!tg) continue;
        const host = p.who;
        topics[host] ||= {};
        topics[host][tg] ||= { ...EMPTY_BUCKET };
        const bucket = topics[host][tg];
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
  }

  // Ensure all hosts have all labels present, even if zero.
  if (labels.length > 0) {
    for (const host of Object.keys(topics)) {
      topics[host] ||= {};
      for (const label of labels) {
        topics[host][label] ||= { ...EMPTY_BUCKET };
      }
    }
  }

  return topics;
}

export function collectTags(episodes: EpisodeData[]): string[] {
  const tags = new Set<string>();
  for (const ep of episodes) {
    for (const p of ep.predictions) {
      for (const tag of p.tags || []) {
        if (typeof tag === "string" && tag.trim()) {
          tags.add(tag.trim());
        }
      }
    }
  }
  return Array.from(tags).sort((a, b) => a.localeCompare(b));
}
