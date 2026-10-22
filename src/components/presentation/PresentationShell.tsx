import { lazy, Suspense, useEffect, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, Maximize2, Minimize2 } from "lucide-react";
import { SLIDES } from "../../data/slides";
import { usePresentation } from "../../app/state/PresentationContext";
import { PresenterNotes } from "./PresenterNotes";
import { SourcesDrawer } from "./SourcesDrawer";

const SCENES = [
  lazy(() => import("../../scenes/Scene01Opening").then((module) => ({ default: module.Scene01Opening }))),
  lazy(() => import("../../scenes/Scene02Opportunity").then((module) => ({ default: module.Scene02Opportunity }))),
  lazy(() => import("../../scenes/Scene03GrowthEngine").then((module) => ({ default: module.Scene03GrowthEngine }))),
  lazy(() => import("../../scenes/Scene04Localization").then((module) => ({ default: module.Scene04Localization }))),
  lazy(() => import("../../scenes/Scene05WhatsApp").then((module) => ({ default: module.Scene05WhatsApp }))),
  lazy(() => import("../../scenes/Scene06Expansion").then((module) => ({ default: module.Scene06Expansion }))),
  lazy(() => import("../../scenes/Scene07Partnerships").then((module) => ({ default: module.Scene07Partnerships }))),
  lazy(() => import("../../scenes/Scene08Originals").then((module) => ({ default: module.Scene08Originals }))),
  lazy(() => import("../../scenes/Scene09Retention").then((module) => ({ default: module.Scene09Retention }))),
  lazy(() => import("../../scenes/Scene10Simulator").then((module) => ({ default: module.Scene10Simulator }))),
  lazy(() => import("../../scenes/Scene11Roadmap").then((module) => ({ default: module.Scene11Roadmap }))),
  lazy(() => import("../../scenes/Scene12Closing").then((module) => ({ default: module.Scene12Closing }))),
  lazy(() => import("../../appendix/CityMethodology").then((module) => ({ default: module.CityMethodology }))),
  lazy(() => import("../../appendix/ExperimentFramework").then((module) => ({ default: module.ExperimentFramework }))),
  lazy(() => import("../../appendix/Sources").then((module) => ({ default: module.Sources }))),
];

export function PresentationShell() {
  const presentation = usePresentation();
  const slide = SLIDES[presentation.index];
  const Scene = SCENES[presentation.index];
  const quiet = presentation.mode === "presentation";

  useEffect(() => {
    void SCENES[Math.min(presentation.index + 1, SCENES.length - 1)];
  }, [presentation.index]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const editing = Boolean(target?.closest("input, textarea, select, [contenteditable='true']"));
      if (event.key === "Escape") {
        presentation.closeOverlays();
        return;
      }
      if (editing || presentation.exploreOpen || presentation.sourcesOpen) return;
      if (event.key === "ArrowRight") {
        event.preventDefault();
        presentation.next();
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        presentation.prev();
      } else if (event.key === " ") {
        if (target?.closest("button, a")) return;
        event.preventDefault();
        presentation.next();
      } else if (event.key.toLowerCase() === "f") {
        presentation.toggleFullscreen();
      } else if (event.key.toLowerCase() === "s") {
        presentation.setNotesOpen(!presentation.notesOpen);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [presentation]);

  return (
    <div className="relative h-dvh overflow-hidden bg-deep text-light">
      <div className="absolute inset-x-0 top-0 z-40 h-1 bg-white/10">
        <div
          className="h-full origin-left bg-gradient-to-r from-gold via-fever to-violet"
          style={{ width: `${((presentation.index + 1) / SLIDES.length) * 100}%` }}
        />
      </div>
      <header
        className={`absolute inset-x-0 top-0 z-50 flex items-center justify-between gap-3 px-4 py-3 transition-opacity ${quiet ? "opacity-0 hover:opacity-100 focus-within:opacity-100" : "opacity-100"}`}
      >
        <p className="hidden text-[13px] tracking-[0.16em] text-soft uppercase sm:block">
          Independent proposal · Not a Fever product
        </p>
        <div className="ml-auto flex flex-wrap justify-end gap-1.5">
          <MenuButton onClick={() => presentation.setMode(quiet ? "explore" : "presentation")}>
            {quiet ? "Presentation" : "Explore"}
          </MenuButton>
          <MenuButton onClick={() => presentation.setExploreOpen(true)}>Chapters</MenuButton>
          <MenuButton onClick={() => presentation.setSourcesOpen(true)}>Sources</MenuButton>
          <MenuButton onClick={presentation.cycleMotion}>
            {presentation.reducedMotion ? "Motion off" : "Motion on"}
          </MenuButton>
          <MenuButton onClick={presentation.toggleFullscreen}>
            {presentation.fullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            <span className="sr-only">Fullscreen</span>
          </MenuButton>
        </div>
      </header>
      <nav
        aria-label="Chapters"
        className={`absolute top-16 bottom-20 left-0 z-30 hidden w-14 flex-col items-center gap-1 overflow-y-auto py-2 lg:flex ${quiet ? "opacity-0 hover:opacity-100 focus-within:opacity-100" : "opacity-100"}`}
      >
        {SLIDES.map((item, index) => (
          <button
            key={item.id}
            type="button"
            className={`focus-ring h-7 w-9 rounded-md text-[12px] ${index === presentation.index ? "bg-fever text-white" : "text-soft hover:text-light"}`}
            aria-label={`${item.number} ${item.title}`}
            aria-current={index === presentation.index ? "page" : undefined}
            onClick={() => presentation.go(index)}
          >
            {item.number}
          </button>
        ))}
      </nav>
      <p className="sr-only" aria-live="polite">
        Scene {slide.number}, {slide.title}
      </p>
      <main key={slide.id} className="absolute inset-0">
        <Suspense fallback={<div className="h-full bg-deep" />}>
          <Scene />
        </Suspense>
      </main>
      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-50 flex items-end justify-between px-4 pb-3">
        <div className={`pointer-events-auto flex gap-2 ${quiet ? "opacity-40 hover:opacity-100 focus-within:opacity-100" : ""}`}>
          <IconButton label="Previous scene" onClick={presentation.prev} disabled={presentation.index === 0}>
            <ChevronLeft />
          </IconButton>
          <IconButton label="Next scene" onClick={presentation.next} disabled={presentation.index === SLIDES.length - 1}>
            <ChevronRight />
          </IconButton>
        </div>
        <p className="pointer-events-none min-w-24 text-right text-[14px] text-soft">
          <span className="text-light">{slide.number}</span>
          <span> / {String(SLIDES.length).padStart(2, "0")}</span>
          <span className="mt-0.5 block text-[12px] tracking-[0.14em] uppercase">{slide.nav}</span>
        </p>
      </div>
      <PresenterNotes />
      <SourcesDrawer />
      {presentation.exploreOpen && (
        <div className="absolute inset-0 z-50 overflow-y-auto bg-deep p-6 pt-16">
          <div className="mx-auto max-w-5xl">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="font-display text-3xl">Chapters</h2>
              <button type="button" className="focus-ring rounded-full border border-white/15 px-4 py-2" onClick={() => presentation.setExploreOpen(false)}>
                Close
              </button>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {SLIDES.map((item, index) => (
                <button
                  key={item.id}
                  type="button"
                  className="focus-ring rounded-2xl border border-white/10 bg-surface p-4 text-left hover:-translate-y-0.5"
                  onClick={() => presentation.go(index)}
                >
                  <span className="text-[13px] text-gold">{item.appendix ? "Appendix" : "Scene"} {item.number}</span>
                  <span className="mt-1 block font-display text-[22px] leading-tight">{item.title}</span>
                </button>
              ))}
            </div>
            <p className="mt-6 text-[15px] text-soft">Arrow keys move scenes. Space advances. F is fullscreen. S shows presenter notes. Escape closes this panel.</p>
          </div>
        </div>
      )}
    </div>
  );
}

function MenuButton({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <button type="button" className="focus-ring inline-flex items-center gap-1 rounded-full border border-white/15 bg-ink/70 px-3 py-1.5 text-[14px]" onClick={onClick}>
      {children}
    </button>
  );
}

function IconButton({
  children,
  label,
  onClick,
  disabled,
}: {
  children: ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      className="focus-ring grid h-11 w-11 place-items-center rounded-full border border-white/15 bg-ink/80 disabled:opacity-30"
      onClick={onClick}
    >
      {children}
    </button>
  );
}
