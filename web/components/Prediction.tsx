import { Prediction } from "../lib/data";
import { STATUS_DESCRIPTIONS } from "../lib/const";
import ReactMarkdown, { type Components } from "react-markdown";
import { Collapsible } from "./Collapsible";
import { YoutubeLink } from "./YoutubeLink";
import Link from "next/link";
import { capitalize } from "../lib/utils";

type Props = {
  prediction: Prediction;
  youtube?: string;
  collapsible?: boolean;
  linkTo?: string;
  headerMeta?: {
    episodeId?: string;
    episodeDate?: string;
  };
};

const badgeColor: Record<string, string> = {
  right: "bg-emerald-500/20 text-emerald-100",
  wrong: "bg-rose-500/20 text-rose-100",
  ambiguous: "bg-amber-500/20 text-amber-100",
  inconclusive: "bg-gray-500/20 text-gray-100",
};

const markdownComponents: Components = {
  a: ({ href, children }) => {
    if (!href) return <>{children}</>;
    const isInternal = href.startsWith("/") || href.startsWith("#");
    return (
      <a
        href={href}
        target={isInternal ? undefined : "_blank"}
        rel={isInternal ? undefined : "noopener noreferrer"}
      >
        {children}
      </a>
    );
  },
};
export function PredictionCard({ prediction, youtube, collapsible, linkTo, headerMeta }: Props) {
  const status = prediction.result || "unvalidated";
  const statusClass =
    badgeColor[status] || "bg-slate-700/40 text-slate-200 border border-slate-700";
  const statusTitle = STATUS_DESCRIPTIONS[status] || STATUS_DESCRIPTIONS.unvalidated;
  const linkHref =
    linkTo ||
    `/episodes/${prediction.episode_id}/prediction/${prediction.encoded_id}`;
  const episodeShort = (() => {
    const raw = headerMeta?.episodeId || "";
    const match = raw.match(/E(\d{1,3})/i);
    return match ? `E${match[1]}` : raw;
  })();
  const ts= prediction.timestamp.split(".")[0];
  const headerParts = [
    capitalize(prediction.who),
    headerMeta?.episodeDate,
    episodeShort ? `${episodeShort}@${ts}` : ts,
  ].filter(Boolean);

  const explanationMd = prediction.explanation ? (
    <ReactMarkdown
      className="rmd prose prose-invert prose-sm max-w-none"
      components={markdownComponents}
    >
      {prediction.explanation}
    </ReactMarkdown>
  ) : null;

  return (
    <article className="rounded-lg border border-white/10 bg-[#080d0b] p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-white/70">
        <div className="flex flex-wrap items-center gap-2">
          <Link
            prefetch={false}
            href={linkHref as any}
          >
            <span className="rounded bg-white/10 px-2 py-1 text-xs font-semibold tracking-wide text-white">
              {headerMeta ? headerParts.join(" ") : `${capitalize(prediction.who)} @ ${prediction.timestamp.split(".")[0]}`}
            </span>
          </Link>
          <span
            className={`rounded px-2 py-1 text-xs font-semibold ${statusClass}`}
            title={statusTitle}
          >
            {capitalize(status)}
          </span>
        </div>
        {prediction.tags && prediction.tags.length > 0 ? (
          <div className="flex flex-wrap items-center gap-1 text-xs text-white/70">
            {prediction.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5 text-[11px] uppercase tracking-wide"
              >
                {tag}
              </span>
            ))}
          </div>
        ) : null}
      </div>
      <div className="mt-3 text-sm text-white/80">
        <div>{prediction.prediction}</div>
        <blockquote className="mt-2 border-l-4 border-white/10 pl-4 italic text-white/70">
          {prediction.quote}
          {youtube && (
          <span className="pl-2 text-sm not-italic text-white">
            <YoutubeLink
              label="View on YouTube"
              seconds={prediction.timestamp_seconds}
              youtube={youtube}
            />
          </span>
          )}
        </blockquote>
      </div>
      {explanationMd ? (
        <div className="mt-3 text-sm text-white/80">
          <div className="font-semibold text-white mb-3">Explanation</div>
          {collapsible ? (
              <Collapsible collapsedHeight={100}>{explanationMd}</Collapsible>
          ) : (
            explanationMd
          )}
        </div>
      ) : null}
    </article>
  );
}
