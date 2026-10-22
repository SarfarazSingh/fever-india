import { useEffect, useId, useState, type ReactNode } from "react";
import { usePresentation } from "../../app/state/PresentationContext";

export function MetricTooltip({
  tip,
  children,
}: {
  tip: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const tipId = useId();
  const { notesOpen, sourcesOpen, exploreOpen } = usePresentation();

  useEffect(() => {
    setOpen(false);
  }, [notesOpen, sourcesOpen, exploreOpen]);

  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [open]);

  return (
    <div className="relative" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        className="focus-ring w-full rounded-2xl text-left"
        aria-describedby={open ? tipId : undefined}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {children}
      </button>
      {open && (
        <div
          id={tipId}
          role="tooltip"
          className="absolute top-[calc(100%+8px)] right-0 z-30 w-[min(320px,70vw)] rounded-xl border border-white/15 bg-ink p-3 text-[15px] leading-snug text-light shadow-2xl"
        >
          {tip}
        </div>
      )}
    </div>
  );
}
