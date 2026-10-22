import { SOURCES } from "../../data/evidence";
import { usePresentation } from "../../app/state/PresentationContext";

export function SourcesDrawer() {
  const { sourcesOpen, setSourcesOpen } = usePresentation();
  if (!sourcesOpen) return null;
  return (
    <aside className="absolute top-0 right-0 z-50 flex h-full w-[min(440px,100%)] flex-col border-l border-white/10 bg-ink/96 shadow-2xl">
      <div className="flex items-center justify-between px-5 py-4">
        <h2 className="font-display text-2xl">Sources</h2>
        <button type="button" className="focus-ring rounded-full border border-white/15 px-3 py-1 text-[14px]" onClick={() => setSourcesOpen(false)}>
          Close
        </button>
      </div>
      <div className="scene-scroll space-y-3 overflow-y-auto px-5 pb-8">
        {SOURCES.map((source) => (
          <article key={source.id} className="rounded-2xl border border-white/10 p-3">
            <p className={`text-[12px] tracking-[0.14em] uppercase ${source.group === "evidence" ? "text-fever" : "text-gold"}`}>
              {source.group === "evidence" ? "Public evidence" : "Illustrative hypothesis"} · {source.date}
            </p>
            <h3 className="mt-1 font-display text-[18px]">{source.title}</h3>
            <p className="mt-1 text-[15px] leading-snug text-soft">{source.detail}</p>
            {source.href && (
              <a className="mt-2 inline-block text-[15px] text-link underline" href={source.href} target="_blank" rel="noreferrer">
                Open source
              </a>
            )}
          </article>
        ))}
      </div>
    </aside>
  );
}
