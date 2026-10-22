import { SLIDES } from "../../data/slides";
import { usePresentation } from "../../app/state/PresentationContext";

export function PresenterNotes() {
  const { notesOpen, setNotesOpen, index } = usePresentation();
  if (!notesOpen) return null;
  return (
    <aside className="absolute inset-x-0 bottom-16 z-50 mx-auto w-[min(920px,calc(100%-2rem))] rounded-2xl border border-gold/30 bg-ink/95 p-4 shadow-2xl">
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-[13px] tracking-[0.16em] text-gold uppercase">Presenter notes · {SLIDES[index].number}</p>
        <button type="button" className="focus-ring text-[14px] text-soft" onClick={() => setNotesOpen(false)}>
          Hide (S)
        </button>
      </div>
      <p className="text-[18px] leading-snug">{SLIDES[index].notes}</p>
    </aside>
  );
}
