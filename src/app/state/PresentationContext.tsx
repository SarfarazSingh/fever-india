import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { SLIDES } from "../../data/slides";

type MotionPref = "system" | "reduce" | "full";
type Mode = "presentation" | "explore";

type PresentationValue = {
  index: number;
  go: (index: number) => void;
  next: () => void;
  prev: () => void;
  mode: Mode;
  setMode: (mode: Mode) => void;
  notesOpen: boolean;
  setNotesOpen: (open: boolean) => void;
  sourcesOpen: boolean;
  setSourcesOpen: (open: boolean) => void;
  exploreOpen: boolean;
  setExploreOpen: (open: boolean) => void;
  motionPref: MotionPref;
  reducedMotion: boolean;
  cycleMotion: () => void;
  fullscreen: boolean;
  toggleFullscreen: () => void;
  closeOverlays: () => void;
};

const PresentationContext = createContext<PresentationValue | null>(null);

function useSystemReducedMotion() {
  const [reduced, setReduced] = useState(() =>
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setReduced(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return reduced;
}

export function PresentationProvider({ children }: { children: ReactNode }) {
  const [index, setIndex] = useState(0);
  const [mode, setMode] = useState<Mode>("presentation");
  const [notesOpen, setNotesOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [exploreOpen, setExploreOpen] = useState(false);
  const [motionPref, setMotionPref] = useState<MotionPref>("system");
  const [fullscreen, setFullscreen] = useState(false);
  const systemReduced = useSystemReducedMotion();
  const reducedMotion = motionPref === "system" ? systemReduced : motionPref === "reduce";

  const go = useCallback((nextIndex: number) => {
    setIndex(Math.min(SLIDES.length - 1, Math.max(0, nextIndex)));
    setExploreOpen(false);
  }, []);
  const next = useCallback(() => go(index + 1), [go, index]);
  const prev = useCallback(() => go(index - 1), [go, index]);

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      void document.documentElement.requestFullscreen().catch(() => undefined);
    } else {
      void document.exitFullscreen().catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    const sync = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", sync);
    return () => document.removeEventListener("fullscreenchange", sync);
  }, []);

  const closeOverlays = useCallback(() => {
    setNotesOpen(false);
    setSourcesOpen(false);
    setExploreOpen(false);
  }, []);

  const value = useMemo<PresentationValue>(
    () => ({
      index,
      go,
      next,
      prev,
      mode,
      setMode,
      notesOpen,
      setNotesOpen,
      sourcesOpen,
      setSourcesOpen,
      exploreOpen,
      setExploreOpen,
      motionPref,
      reducedMotion,
      cycleMotion: () =>
        setMotionPref((current) =>
          current === "system" ? "reduce" : current === "reduce" ? "full" : "system",
        ),
      fullscreen,
      toggleFullscreen,
      closeOverlays,
    }),
    [
      index,
      go,
      next,
      prev,
      mode,
      notesOpen,
      sourcesOpen,
      exploreOpen,
      motionPref,
      reducedMotion,
      fullscreen,
      toggleFullscreen,
      closeOverlays,
    ],
  );

  return <PresentationContext.Provider value={value}>{children}</PresentationContext.Provider>;
}

export function usePresentation() {
  const value = useContext(PresentationContext);
  if (!value) throw new Error("usePresentation must be used within PresentationProvider");
  return value;
}
