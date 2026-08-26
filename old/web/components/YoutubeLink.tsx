"use client";
import { useEffect, useState } from "react";

const STORAGE_KEY = "predict_timestamp_notice_seen";

function formatYoutubeLink(youtube?: string, seconds?: number) {
  if (!youtube) return null;
  if (seconds == null) return youtube;
  const url = new URL(youtube);
  url.searchParams.set("t", `${seconds}`);
  return url.toString();
}

type Props = {
  label: string;
  youtube?: string;
  seconds?: number;
};

export function YoutubeLink({ label, youtube, seconds }: Props) {
  const [seen, setSeen] = useState<boolean>(true);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored !== "1") {
      setSeen(false);
    }
  }, []);

  const youtubeLink = formatYoutubeLink(youtube, seconds);

  const acknowledge = () => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, "1");
    }
    setSeen(true);
    setShowModal(false);
    if (youtubeLink) {
      window.open(youtubeLink, "_blank", "noopener,noreferrer");
    }
  };

  if (!youtubeLink) {
    return (
      <span
        title="Unable to automatically match to youtube video"
      >
        {label}
      </span>
    );
  }

  return (
    <>
      <a
        className="underline-offset-4 hover:underline"
        href={youtubeLink}
        target="_blank"
        rel="noreferrer"
        onClick={(e) => {
          if (!seen) {
            e.preventDefault();
            setShowModal(true);
          }
        }}
      >
        {label}
      </a>
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
          <div className="w-full max-w-md rounded-lg border border-white/20 bg-[#080d0b] p-6 shadow-lg">
            <h2 className="text-lg font-semibold text-white">Heads up</h2>
            <p className="mt-2 text-sm text-white/80">
              Timestamp links are best effort and may be imperfect due to
              mismatches between audio transcript timestamps and YouTube video
              timestamps.
            </p>
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                className="rounded bg-white px-4 py-2 text-sm font-semibold text-black hover:bg-white/90"
                onClick={acknowledge}
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
