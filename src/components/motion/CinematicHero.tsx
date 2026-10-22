import { useState, type ReactNode } from "react";
import { ParticleField } from "./ParticleField";

export function CinematicHero({
  children,
  calm = false,
}: {
  children: ReactNode;
  calm?: boolean;
}) {
  const [shift, setShift] = useState({ x: 0, y: 0 });

  return (
    <div
      className="relative h-full overflow-hidden"
      onMouseMove={(event) => {
        const rect = event.currentTarget.getBoundingClientRect();
        setShift({
          x: (event.clientX - rect.left) / rect.width - 0.5,
          y: (event.clientY - rect.top) / rect.height - 0.5,
        });
      }}
    >
      <div className="absolute inset-0 bg-deep" />
      <div
        className="absolute inset-x-0 bottom-0 h-[62%] bg-[radial-gradient(ellipse_at_bottom,rgba(233,188,112,0.38),rgba(255,218,149,0.08)_42%,transparent_70%)]"
        style={{ transform: `translate3d(${shift.x * -16}px, ${shift.y * -8}px, 0)` }}
        aria-hidden="true"
      />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_40%,rgba(111,65,215,0.16),transparent_32%)]" aria-hidden="true" />
      <div className="noise absolute inset-0 opacity-40" aria-hidden="true" />
      {Array.from({ length: calm ? 7 : 14 }).map((_, index) => (
        <span
          key={index}
          aria-hidden="true"
          className="pointer-events-none absolute bottom-[8%] rounded-full blur-md"
          style={{
            left: `${8 + ((index * 17) % 84)}%`,
            width: 10 + (index % 4) * 6,
            height: 22 + (index % 5) * 10,
            background: "linear-gradient(to top, rgba(233,188,112,0.85), rgba(255,218,149,0.05))",
            transform: `translate3d(${shift.x * (8 + index)}px, ${shift.y * 6}px, 0)`,
            opacity: calm ? 0.45 : 0.8,
          }}
        />
      ))}
      <ParticleField parallax={shift} count={calm ? 18 : 46} />
      <p className="sr-only">Abstract candlelit stage illustration. This is not a photograph of a Fever event.</p>
      <div className="relative z-10 h-full">{children}</div>
    </div>
  );
}
