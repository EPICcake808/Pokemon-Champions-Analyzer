"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";

type Props = {
  value: string;
  options: string[];
  onChange: (value: string) => void;
  placeholder?: string;
};

// Bounds how many options render at once. Set well above the full eligible-species + Mega
// count (a few hundred) so the unfiltered list is fully scrollable — previously a cap of 60
// hid every Pokemon past the first 60 (e.g. the newer-regulation additions appended at the end).
const MAX_VISIBLE = 1000;

export function SpeciesCombobox({ value, options, onChange, placeholder = "Search species…" }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const listboxId = useId();

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const matches = q ? options.filter((option) => option.toLowerCase().includes(q)) : options;
    // Alphabetical so the long list is navigable by scroll regardless of the source order
    // (eligible species followed by Mega forms).
    return [...matches].sort((a, b) => a.localeCompare(b)).slice(0, MAX_VISIBLE);
  }, [query, options]);

  useEffect(() => {
    function onDocClick(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  function commit(option: string) {
    onChange(option);
    setQuery("");
    setOpen(false);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (!open && (event.key === "ArrowDown" || event.key === "Enter")) {
      setOpen(true);
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlight((index) => Math.min(index + 1, filtered.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlight((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter") {
      if (open && filtered[highlight]) {
        event.preventDefault();
        commit(filtered[highlight]);
      }
    } else if (event.key === "Escape") {
      setOpen(false);
      setQuery("");
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <input
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-autocomplete="list"
        value={open ? query : value}
        placeholder={value ? value : placeholder}
        onFocus={() => {
          setOpen(true);
          setHighlight(0);
        }}
        onChange={(event) => {
          setQuery(event.target.value);
          setHighlight(0);
          setOpen(true);
        }}
        onKeyDown={onKeyDown}
        className="w-full border border-[var(--line)] bg-black/20 px-3 py-3 text-sm text-white/88 outline-none transition focus:border-white/45"
      />
      {open ? (
        <ul
          id={listboxId}
          role="listbox"
          className="absolute z-30 mt-1 max-h-64 w-full overflow-auto rounded border border-[var(--line)] bg-[#090b10] py-1 shadow-xl"
        >
          {filtered.length === 0 ? (
            <li className="px-3 py-2 text-sm text-white/40">No matches</li>
          ) : (
            filtered.map((option, index) => (
              <li
                key={option}
                role="option"
                aria-selected={option === value}
                onMouseEnter={() => setHighlight(index)}
                onMouseDown={(event) => {
                  event.preventDefault();
                  commit(option);
                }}
                className={`cursor-pointer px-3 py-2 text-sm ${
                  index === highlight ? "bg-white/10 text-white" : "text-white/80"
                } ${option === value ? "font-medium" : ""}`}
              >
                {option}
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}
