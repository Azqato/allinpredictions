"use client";
import { useState } from "react";

type Props = {
  children: React.ReactNode;
  collapsedHeight?: number;
};

export function Collapsible({ children, collapsedHeight = 150 }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="relative">
      <div
        className="overflow-hidden"
        style={expanded ? {paddingBottom: 25} : { maxHeight: collapsedHeight }}
      >
        {children}
      </div>
      {!expanded && (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-gradient-to-b from-transparent to-[#080d0b]" />
      )}
      <button
        type="button"
        className="mt-2 text-xs font-semibold text-white/80 underline-offset-4 hover:text-white absolute bottom-0"
        onClick={() => setExpanded((v) => !v)}
      >
        {expanded ? "Hide more" : "Show more"}
      </button>
    </div>
  );
}
