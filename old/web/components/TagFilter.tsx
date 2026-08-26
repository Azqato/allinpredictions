"use client";

import { capitalize } from "../lib/utils";

type Props = {
  value: string;
  options: string[];
  onChange: (value: string) => void;
  allValue?: string;
  allLabel?: string;
  label?: string;
};

export function TagFilter({
  value,
  options,
  onChange,
  allValue = "__all",
  allLabel = "All topics",
  label,
}: Props) {
  return (
    <label className="text-sm text-white/80 flex items-center gap-2">
      {label && <span className="text-white/70">{label}</span>}
      <select
        className="rounded border border-white/30 bg-[#0d1411] px-3 py-1 text-sm text-white shadow-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value={allValue}>{allLabel}</option>
        {options.map((tag) => (
          <option key={tag} value={tag}>
            {tag === 'ai' ? 'AI' : capitalize(tag)}
          </option>
        ))}
      </select>
    </label>
  );
}
