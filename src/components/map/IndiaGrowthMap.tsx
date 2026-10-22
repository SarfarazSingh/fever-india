import { geoMercator, geoPath, type GeoPermissibleObjects } from "d3-geo";
import { useEffect, useMemo, useRef, useState } from "react";
import indiaGeo from "../../assets/geography/india.json";
import { usePresentation } from "../../app/state/PresentationContext";
import type { City } from "../../types";

const geography = indiaGeo as unknown as GeoPermissibleObjects;

export function IndiaSilhouette() {
  const width = 420;
  const height = 520;
  const projection = geoMercator().fitExtent(
    [
      [12, 12],
      [width - 12, height - 12],
    ],
    geography,
  );
  const path = geoPath(projection);
  const places = [
    ["Delhi", 77.21, 28.61],
    ["Mumbai", 72.88, 19.08],
    ["Bengaluru", 77.59, 12.97],
    ["Chennai", 80.27, 13.08],
    ["Jaipur", 75.79, 26.91],
  ] as const;
  const points = places.map(([name, lon, lat]) => ({
    name,
    point: projection([lon, lat]) ?? [0, 0],
  }));
  const links = [
    [0, 1],
    [0, 4],
    [1, 2],
    [2, 3],
  ];
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full" aria-hidden="true">
      <path d={path(geography) ?? ""} fill="rgba(233,188,112,0.05)" stroke="#E9BC70" strokeWidth="1.25" />
      {links.map(([from, to]) => (
        <line
          key={`${from}-${to}`}
          x1={points[from].point[0]}
          y1={points[from].point[1]}
          x2={points[to].point[0]}
          y2={points[to].point[1]}
          stroke="#FFDA95"
          strokeWidth="0.8"
          opacity="0.75"
        />
      ))}
      {points.map((place) => (
        <circle key={place.name} cx={place.point[0]} cy={place.point[1]} r="3.2" fill="#FFDA95" />
      ))}
    </svg>
  );
}

const PIN: Record<City["classification"], string> = {
  baseline: "#0079CA",
  candidate: "#E9BC70",
  "scale-up": "#6F41D7",
};

export function IndiaGrowthMap({
  cities,
  selectedId,
  onSelect,
}: {
  cities: City[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const frame = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 640, height: 680 });
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const [hover, setHover] = useState<string | null>(null);
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);
  const moved = useRef(false);
  const { reducedMotion } = usePresentation();

  useEffect(() => {
    const element = frame.current;
    if (!element) return;
    const observer = new ResizeObserver(() => {
      setSize({ width: element.clientWidth, height: element.clientHeight });
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const element = frame.current;
    if (!element) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      setView((current) => ({
        ...current,
        k: Math.min(5, Math.max(1, current.k * (event.deltaY < 0 ? 1.08 : 0.92))),
      }));
    };
    element.addEventListener("wheel", onWheel, { passive: false });
    return () => element.removeEventListener("wheel", onWheel);
  }, []);

  const layout = useMemo(() => {
    const projection = geoMercator().fitExtent(
      [
        [28, 24],
        [size.width - 28, size.height - 24],
      ],
      geography,
    );
    const path = geoPath(projection);
    return {
      d: path(geography) ?? "",
      points: cities.map((city) => {
        const point = projection([city.lon, city.lat]);
        return { city, x: point?.[0] ?? 0, y: point?.[1] ?? 0 };
      }),
    };
  }, [cities, size.height, size.width]);

  const hovered = layout.points.find((point) => point.city.id === hover);

  return (
    <div ref={frame} className="relative h-full min-h-0 overflow-hidden rounded-3xl border border-white/10 bg-[#071820]">
      <svg
        className="h-full w-full touch-none"
        role="img"
        aria-label="Map of India with programming examples and cities under evaluation"
        onPointerDown={(event) => {
          moved.current = false;
          drag.current = { x: event.clientX, y: event.clientY, vx: view.x, vy: view.y };
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          if (!drag.current) return;
          const dx = event.clientX - drag.current.x;
          const dy = event.clientY - drag.current.y;
          if (Math.hypot(dx, dy) > 4) moved.current = true;
          setView((current) => ({ ...current, x: drag.current!.vx + dx, y: drag.current!.vy + dy }));
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
      >
        <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
          <path d={layout.d} fill="#102838" stroke="#7CC4EA" strokeWidth={1.1 / view.k} />
          {layout.points.map(({ city, x, y }) => {
            const selected = city.id === selectedId;
            return (
              <g key={city.id} transform={`translate(${x} ${y})`}>
                <circle r={selected ? 11 : 7} fill={PIN[city.classification]} opacity={0.22} />
                <circle
                  r={selected ? 5.5 : 3.6}
                  fill={PIN[city.classification]}
                  className={selected && !reducedMotion ? "pin-pulse" : undefined}
                  stroke="#F8FAFC"
                  strokeWidth={selected ? 1.4 : 0}
                />
                <circle
                  r={16}
                  fill="transparent"
                  className="cursor-pointer"
                  onMouseEnter={() => setHover(city.id)}
                  onMouseLeave={() => setHover((current) => (current === city.id ? null : current))}
                  onClick={() => {
                    if (moved.current) return;
                    onSelect(city.id);
                  }}
                >
                  <title>{city.name}</title>
                </circle>
              </g>
            );
          })}
        </g>
      </svg>
      {hovered && (
        <div
          className="pointer-events-none absolute z-10 max-w-[220px] rounded-xl border border-white/15 bg-ink/95 px-3 py-2 text-[14px] shadow-xl"
          style={{
            left: Math.min(size.width - 230, hovered.x * view.k + view.x + 14),
            top: Math.max(8, hovered.y * view.k + view.y - 8),
          }}
        >
          <p className="font-display text-[15px]">{hovered.city.name}</p>
          <p className="text-soft capitalize">{hovered.city.classification}</p>
          <p className="text-gold">Research required</p>
        </div>
      )}
      <div className="absolute bottom-3 left-3 flex max-w-[90%] flex-wrap gap-2 rounded-2xl bg-ink/80 px-3 py-2 text-[13px] text-soft">
        <span className="flex items-center gap-1.5"><i className="inline-block h-2.5 w-2.5 rounded-full bg-fever" /> Documented example</span>
        <span className="flex items-center gap-1.5"><i className="inline-block h-2.5 w-2.5 rounded-full bg-gold" /> Candidate</span>
        <span className="flex items-center gap-1.5"><i className="inline-block h-2.5 w-2.5 rounded-full bg-violet" /> Scale-up assessment</span>
      </div>
      <p className="absolute top-3 right-3 text-[13px] text-soft">Drag to pan · scroll to zoom</p>
    </div>
  );
}
