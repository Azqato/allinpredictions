"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "llm_warning_dismissed";

export function WarningBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const dismissed = window.localStorage.getItem(STORAGE_KEY) === "true";
    setVisible(!dismissed);
  }, []);

  if (!visible) return null;

  const dismiss = () => {
    setVisible(false);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, "true");
    }
  };

  return (
    <div className="border-b border-white/10 bg-white/5">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3 text-sm text-white/90">
        <span>
          Welcome! All predictions were automatically extracted and validated by LLMs, so there may be
          inaccuracies or mistakes.
        </span>
        <button
          type="button"
          onClick={dismiss}
          className="ml-4 rounded border border-white/20 px-3 py-1 text-xs font-semibold text-white hover:bg-white/10"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
