"use client";

import { useEffect, useMemo, useState } from "react";
import { Doughnut, Bar } from "react-chartjs-2";
import {
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from "chart.js";
import type { EpisodeData } from "../lib/data";
import {
  aggregateHostStats,
  buildYearlyStats,
  buildTopicStats,
  type HostResultKey,
} from "../lib/stats";
import Link from "next/link";
import { TagFilter } from "./TagFilter";
import { capitalize } from "../lib/utils";

ChartJS.register(
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  BarController
);

const RESULT_COLORS: Record<HostResultKey, string> = {
  right: "#22c55e",
  wrong: "#ef4444",
  ambiguous: "#d4c4a8",
  inconclusive: "#6b7280",
  unvalidated: "#94a3b8",
};

type HostStats = Record<string, Record<HostResultKey, number>>;

function DonutChart({
  host,
  stats,
  visibleKeys,
}: {
  host: string;
  stats: HostStats[string];
  visibleKeys: HostResultKey[];
}) {
  const validatedTotal = visibleKeys.reduce((sum, key) => sum + stats[key], 0);
  const pctOrZero = (v: number) => (validatedTotal === 0 ? 0 : (v / validatedTotal) * 100);
  const data = {
    labels: visibleKeys.map((k) => k.charAt(0).toUpperCase() + k.slice(1)),
    datasets: [
      {
        data: visibleKeys.map((k) => pctOrZero(stats[k] || 0)),
        backgroundColor: visibleKeys.map((k) => RESULT_COLORS[k] || "rgba(255,255,255,0.2)"),
        borderWidth: 0,
      },
    ],
  };
  const slices: { key: HostResultKey; label: string; value: number; hidden?: boolean }[] = [
    { key: "right", label: "Right", value: stats.right },
    { key: "wrong", label: "Wrong", value: stats.wrong },
    { key: "ambiguous", label: "Ambiguous", value: stats.ambiguous },
    { key: "inconclusive", label: "Inconclusive", value: stats.inconclusive },
    { key: "unvalidated", label: "Unvalidated", value: stats.unvalidated, hidden: true },
  ];

  return (
    <div className="md:flex md:flex-row-reverse md:justify-end md:items-start mt-4">
      {validatedTotal === 0 ? (
        <div className="text-sm text-white/60">No data</div>
      ) : (
        <div className="h-[150px] md:flex-1 md:mt-[-40px]">
          <Doughnut
            data={data}
            options={{
              maintainAspectRatio: false,
              animation: false,
              plugins: {
                legend: { display: false },
                tooltip: {
                  enabled: true,
                  callbacks: {
                    label: (ctx) => {
                      const val = ctx.raw as number;
                      const label = ctx.label || "";
                      return `${label}: ${val.toFixed(1)}%`;
                    },
                  },
                },
              },
              cutout: "55%",
              responsive: true,
            }}
          />
        </div>
      )}
      <table className="mt-3 md:mt-0 md:flex-0 text-sm text-white/90 border-separate border-spacing-y-1">
        <tbody>
          {slices
            .filter((s) => !s.hidden && visibleKeys.includes(s.key))
            .map((slice) => (
              <tr key={slice.key}>
                <td className="align-middle">
                  <div className="flex items-center gap-2 pr-2">
                    <span
                      className="inline-block h-3 w-3 rounded-full border border-white/20"
                      style={{ backgroundColor: RESULT_COLORS[slice.key] || "rgba(255,255,255,0.2)" }}
                    />
                    {slice.label}
                  </div>
                </td>
                <td className="text-right align-middle text-white/80">
                  {validatedTotal === 0 ? "0%" : `${Math.round((slice.value / validatedTotal) * 100)}%`}
                </td>
                <td className="text-right align-middle text-white/60">({slice.value})</td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}

function StackedBarChart({
  data,
  visibleKeys,
  orderedLabels,
}: {
  data: Record<string, Record<string, Record<HostResultKey, number>>>;
  visibleKeys: HostResultKey[];
  orderedLabels?: string[];
}) {
  const resultKeys = visibleKeys;
  return (
    <div className="space-y-4">
      {Object.entries(data).map(([host, categoryData]) => {
        const labels =
          orderedLabels && orderedLabels.length > 0
            ? orderedLabels
            : Object.keys(categoryData || {}).sort();
        const totalsByLabel: Record<string, number> = {};
        for (const label of labels) {
          const bucket: Record<HostResultKey, number> = categoryData[label] || {
            right: 0,
            wrong: 0,
            ambiguous: 0,
            inconclusive: 0,
            unvalidated: 0,
          };
          totalsByLabel[label] = visibleKeys.reduce(
            (sum, key) => sum + (bucket[key] || 0),
            0
          );
        }

        const datasets = resultKeys.map((result) => ({
          label: result.charAt(0).toUpperCase() + result.slice(1),
          data: labels.map((label) => categoryData[label]?.[result] || 0),
          backgroundColor: RESULT_COLORS[result] || "rgba(255,255,255,0.2)",
          stack: "stack1",
        }));

        const barData = {
          labels,
          datasets: datasets.map((ds, dsIdx) => ({
            ...ds,
            data: labels.map((label, idx) => {
              const total = totalsByLabel[label] || 0;
              const raw = datasets[dsIdx].data[idx] as number;
              return total === 0 ? 0 : Math.round((raw / total) * 100);
            }),
            rawCounts: ds.data,
          })),
        };

        return (
          <Bar
            key={host}
            data={barData}
            options={{
              responsive: true,
              animation: false,
              plugins: {
                legend: { position: "bottom", labels: { color: "#e5e7eb", usePointStyle: true } },
                tooltip: {
                  callbacks: {
                    label: (ctx) => {
                      const label = ctx.dataset.label || "";
                      const val = ctx.raw as number;
                      const rawCounts = (ctx.dataset as any).rawCounts as number[] | undefined;
                      const count = rawCounts ? rawCounts[ctx.dataIndex] : undefined;
                      const countText = typeof count === "number" ? ` (${count})` : "";
                      return `${label}: ${val.toFixed(1)}%${countText}`;
                    },
                  },
                },
              },
              scales: {
                x: {
                  stacked: true,
                  ticks: { color: "#cbd5e1" },
                  grid: { color: "rgba(255,255,255,0.05)" },
                },
                y: {
                  stacked: true,
                  ticks: { color: "#cbd5e1" },
                  grid: { color: "rgba(255,255,255,0.05)" },
                  suggestedMax: 100,
                  max: 100,
                },
              },
            }}
          />
        );
      })}
    </div>
  );
}

type Props = {
  episodes: EpisodeData[];
  tags: string[];
};

const ALL_TAG = "__all";

export function HostCharts({ episodes, tags }: Props) {
  const [view, setView] = useState<"donut" | "stacked" | "topic">("donut");
  const [resolvedOnly, setResolvedOnly] = useState(true);
  const [selectedTag, setSelectedTag] = useState<string>(ALL_TAG);
  const visibleKeys = useMemo<HostResultKey[]>(
    () => (resolvedOnly ? ["right", "wrong"] : ["right", "wrong", "ambiguous", "inconclusive"]),
    [resolvedOnly]
  );
  const tagValue = selectedTag === ALL_TAG ? null : selectedTag;
  const hostStats = useMemo(
    () => aggregateHostStats(episodes, tagValue),
    [episodes, tagValue]
  );
  const yearlyStats = useMemo(
    () => buildYearlyStats(episodes, tagValue),
    [episodes, tagValue]
  );
  const topicStats = useMemo(
    () => buildTopicStats(episodes, tagValue, tags),
    [episodes, tagValue, tags]
  );
  const tagOptions = tags;

  useEffect(() => {
    if (view === "topic" && selectedTag !== ALL_TAG) {
      setSelectedTag(ALL_TAG);
    }
  }, [view, selectedTag]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-2xl font-semibold text-white">Host Accuracy</div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-5">
          <label className="flex items-center gap-2 text-sm text-white/80">
            <input
              type="checkbox"
              checked={resolvedOnly}
              onChange={(e) => setResolvedOnly(e.target.checked)}
              className="h-4 w-4 rounded border-white/40 bg-transparent text-white focus:ring-white"
            />
            Resolved only
          </label>
          <TagFilter
            value={selectedTag}
            options={tagOptions}
            onChange={(val) => setSelectedTag(val)}
            allValue={ALL_TAG}
            allLabel="All topics"
          />
          <div className="inline-flex rounded md:justify-start border border-white/20 bg-white/5 overflow-hidden min-w-[240px]">
            <button
              type="button"
              onClick={() => setView("donut")}
              className={`px-3 py-1 text-sm rounded-l flex-1 text-center ${
                view === "donut" ? "bg-white text-black" : "text-white/80"
              }`}
            >
              Total
            </button>
            <button
              type="button"
              onClick={() => setView("stacked")}
              className={`px-3 py-1 text-sm flex-1 text-center ${
                view === "stacked" ? "bg-white text-black" : "text-white/80"
              }`}
            >
              By Year
            </button>
            <button
              type="button"
              onClick={() => {
                setSelectedTag(ALL_TAG);
                setView("topic");
              }}
              className={`px-3 py-1 text-sm rounded-r flex-1 text-center ${
                view === "topic" ? "bg-white text-black" : "text-white/80"
              }`}
            >
              By Topic
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {Object.entries(hostStats).map(([who, s]) => {
          const total = visibleKeys.reduce((sum, key) => sum + (s[key] || 0), 0);
          return (
            <div key={who} className="rounded-lg border border-white/10 p-4">
              <div className="text-lg font-semibold text-white">
                <Link prefetch={false} href={`/host/${who}`} className="hover:underline">
                  {capitalize(who)}
                </Link>
              </div>
              <div className="text-sm text-white/60">
                Total predictions: {total}
              </div>
              {view === "donut" ? (
                <DonutChart host={who} stats={s} visibleKeys={visibleKeys} />
              ) : view === "stacked" ? (
                <StackedBarChart
                  data={{ [who]: yearlyStats[who] || {} }}
                  visibleKeys={visibleKeys}
                />
              ) : (
                <StackedBarChart
                  data={{ [who]: topicStats[who] || {} }}
                  visibleKeys={visibleKeys}
                  orderedLabels={tags}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
