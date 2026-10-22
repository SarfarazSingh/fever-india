import { useRef, type KeyboardEvent, type MouseEvent, type ReactNode } from "react";
import { usePresentation } from "../../app/state/PresentationContext";
import { cn } from "../../lib/cn";
import { SceneMark } from "./SceneMark";

export function InteractiveCard({
  eyebrow,
  title,
  line,
  image,
  mark,
  action = "Open",
  onClick,
  className,
  children,
}: {
  eyebrow: string;
  title: string;
  line?: string;
  image: string;
  mark: string;
  action?: string;
  onClick: () => void;
  className?: string;
  children?: ReactNode;
}) {
  const card = useRef<HTMLButtonElement>(null);
  const { reducedMotion } = usePresentation();

  const tilt = (event: MouseEvent<HTMLButtonElement>) => {
    if (reducedMotion) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    event.currentTarget.style.setProperty("--rx", `${(-y * 7).toFixed(2)}deg`);
    event.currentTarget.style.setProperty("--ry", `${(x * 9).toFixed(2)}deg`);
    event.currentTarget.style.setProperty("--lift", "-10px");
  };

  const reset = (event: MouseEvent<HTMLButtonElement>) => {
    event.currentTarget.style.setProperty("--rx", "0deg");
    event.currentTarget.style.setProperty("--ry", "0deg");
    event.currentTarget.style.setProperty("--lift", "0px");
  };

  const onKey = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick();
    }
  };

  return (
    <button
      ref={card}
      type="button"
      onClick={onClick}
      onKeyDown={onKey}
      onMouseMove={tilt}
      onMouseLeave={reset}
      className={cn("interactive-card focus-ring group relative flex h-full min-h-0 flex-col overflow-hidden rounded-[28px] text-left", className)}
    >
      <span className="absolute inset-0">
        <img src={image} alt="" className="card-art h-full w-full object-cover" decoding="async" />
        <span className="absolute inset-0 bg-gradient-to-t from-ink via-ink/55 to-ink/10" />
      </span>
      <span className="relative flex h-full min-h-0 flex-col p-4 md:p-5">
        <span className="flex items-center justify-between">
          <span className="text-[13px] tracking-[0.16em] text-gold uppercase">{eyebrow}</span>
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/15 bg-ink/40 text-glow backdrop-blur-sm">
            <SceneMark name={mark} />
          </span>
        </span>
        <span className="mt-auto">
          <span className="mt-6 block font-display text-[clamp(24px,2.4vw,34px)] leading-[0.95]">{title}</span>
          {line && <span className="mt-2 block text-[15px] leading-snug text-soft">{line}</span>}
          {children}
          <span className="card-action mt-4 inline-flex items-center gap-2 rounded-full bg-fever px-3.5 py-1.5 text-[14px] text-white">
            {action}
            <span aria-hidden="true">→</span>
          </span>
        </span>
      </span>
    </button>
  );
}

export function DetailFrame({
  title,
  eyebrow,
  image,
  onClose,
  children,
}: {
  title: string;
  eyebrow?: string;
  image?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <article className="detail-frame absolute inset-0 z-20 overflow-hidden rounded-[28px] border border-white/10 bg-deep">
      {image && (
        <div className="pointer-events-none absolute inset-y-0 right-0 hidden w-[38%] lg:block">
          <img src={image} alt="" className="h-full w-full object-cover opacity-70" />
          <div className="absolute inset-0 bg-gradient-to-l from-transparent to-deep" />
        </div>
      )}
      <div className="relative flex h-full flex-col p-6 md:p-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            {eyebrow && <p className="text-[13px] tracking-[0.14em] text-gold uppercase">{eyebrow}</p>}
            <h3 className="mt-1 font-display text-[clamp(32px,4vw,48px)] leading-none">{title}</h3>
          </div>
          <button type="button" className="focus-ring rounded-full border border-white/15 bg-ink/60 px-4 py-2 text-[15px]" onClick={onClose}>
            Back
          </button>
        </div>
        <div className="mt-6 max-w-3xl">{children}</div>
      </div>
    </article>
  );
}
