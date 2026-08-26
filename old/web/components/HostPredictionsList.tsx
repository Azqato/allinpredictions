"use client";

import { useEffect, useMemo, useState } from "react";
import type { Prediction } from "../lib/data";
import { TagFilter } from "./TagFilter";
import { PredictionCard } from "./Prediction";
import { capitalize } from "../lib/utils";

const ALL_TAG = "__all";

export type HostPredictionItem = {
  prediction: Prediction;
  episodeTitle?: string;
  episodePublished?: string;
  episodeId?: string;
  youtube?: string;
};

type Props = {
  host: string;
  tags: string[];
  items: HostPredictionItem[];
};

export function HostPredictionsList({ host, tags, items }: Props) {
  const [selectedTag, setSelectedTag] = useState<string>(ALL_TAG);
  const [resolvedOnly, setResolvedOnly] = useState<boolean>(false);

  // Hydrate from URL hash (?tag=foo)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const tagParam = params.get("tag");
    const resolvedParam = params.get("resolved");
    if (tagParam && tags.includes(tagParam)) {
      setSelectedTag(tagParam);
    }
    if (resolvedParam === "1") {
      setResolvedOnly(true);
    }
  }, [tags]);

  // Persist to URL hash
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    if (selectedTag === ALL_TAG) {
      params.delete("tag");
    } else {
      params.set("tag", selectedTag);
    }
    if (resolvedOnly) {
      params.set("resolved", "1");
    } else {
      params.delete("resolved");
    }
    const hash = params.toString();
    const newUrl = `${window.location.pathname}${window.location.search}${
      hash ? `#${hash}` : ""
    }`;
    window.history.replaceState(null, "", newUrl);
  }, [selectedTag, resolvedOnly]);

  const filtered = useMemo(() => {
    let current = items;
    if (selectedTag !== ALL_TAG) {
      current = current.filter((item) =>
        (item.prediction.tags || []).includes(selectedTag)
      );
    }
    if (resolvedOnly) {
      current = current.filter((item) =>
        ["right", "wrong"].includes(
          (item.prediction.result || "").toLowerCase()
        )
      );
    }
    return current;
  }, [items, selectedTag, resolvedOnly]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const ad = a.episodePublished ? new Date(a.episodePublished) : null;
      const bd = b.episodePublished ? new Date(b.episodePublished) : null;
      if (ad && bd) return bd.getTime() - ad.getTime();
      if (ad) return -1;
      if (bd) return 1;
      return 0;
    });
  }, [filtered]);

  return (
    <div className="space-y-4">
      <div className="flex flex-row gap-3 items-center justify-between">
        <div>
          <div className="text-sm text-white/60">
            {sorted.length} prediction{sorted.length === 1 ? "" : "s"}
          </div>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
          <label className="flex items-center gap-2 text-sm text-white/80">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-white/40 bg-transparent text-white focus:ring-white"
              checked={resolvedOnly}
              onChange={(e) => setResolvedOnly(e.target.checked)}
            />
            Resolved only
          </label>
          <TagFilter
            value={selectedTag}
            options={tags}
            onChange={setSelectedTag}
            allValue={ALL_TAG}
            allLabel="All topics"
          />
        </div>
      </div>
      <div className="space-y-3">
        {sorted.map((item) => (
          <PredictionCard
            key={item.prediction.id}
            prediction={item.prediction}
            youtube={item.youtube}
            linkTo={`/host/${host}/predictions/${item.prediction.encoded_id}`}
            headerMeta={{
              episodeId: item.episodeId,
              episodeDate: item.episodePublished
                ? new Date(item.episodePublished).toLocaleDateString()
                : undefined,
            }}
            collapsible
          />
        ))}
        {sorted.length === 0 ? (
          <div className="rounded border border-white/10 bg-white/5 p-4 text-white/70 text-sm">
            No predictions match this filter.
          </div>
        ) : null}
      </div>
    </div>
  );
}
