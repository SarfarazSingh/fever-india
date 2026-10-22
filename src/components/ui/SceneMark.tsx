import { cn } from "../../lib/cn";

const PATHS: Record<string, string> = {
  discover: "M12 3.5A8.5 8.5 0 1 1 3.5 12 H6.2 A5.8 5.8 0 1 0 12 6.2 V3.5 Z M12 8.2 L15.6 12 12 15.8 8.4 12 Z",
  convert: "M5 7.2 h14 a1.2 1.2 0 0 1 1.2 1.2 v7.2 a1.2 1.2 0 0 1-1.2 1.2 H5 A1.2 1.2 0 0 1 3.8 15.6 V8.4 A1.2 1.2 0 0 1 5 7.2 Z M8 10.2 h8 M8 13.2 h5",
  return: "M7 8.2 A5.4 5.4 0 1 1 6.6 14.8 L5 16.4 M7 8.2 H4.4 V5.6",
  expand: "M12 5.2 L16.8 8.2 16.8 14.2 12 17.2 7.2 14.2 7.2 8.2 Z M12 9.4 v5.2 M9.6 11.2 h4.8",
  hotels: "M6.4 18.4 V7.2 L12 4.6 17.6 7.2 v11.2 M9.2 18.4 V12 h5.6 v6.4",
  banks: "M4.8 9.2 h14.4 v7.2 H4.8 Z M7.2 11.8 h3.2 M7.2 14.2 h6.4",
  corporates: "M5.2 18.2 V9.4 h4.4 V18.2 M10.8 18.2 V5.6 h8 v12.6 M13 8.4 h3.2 M13 11.2 h3.2 M13 14 h3.2",
  occasions: "M12 4.8 c2.8 3.2 5.6 5.6 5.6 8.6 A5.6 5.6 0 1 1 6.4 13.4 C6.4 10.4 9.2 8 12 4.8 Z",
  measure: "M12 4.6 v3.2 M12 16.2 v3.2 M4.6 12 h3.2 M16.2 12 h3.2 M8.4 8.4 l2 2 M13.6 13.6 l2 2 M15.6 8.4 l-2 2 M10.4 13.6 l-2 2",
  diagnose: "M10.4 10.4 m-4.6 0 a4.6 4.6 0 1 0 9.2 0 a4.6 4.6 0 1 0 -9.2 0 M13.8 13.8 L18 18",
  experiment: "M9 4.8 h6 M10.2 4.8 v4.2 L7.4 17.4 h9.2 L13.8 9 V4.8",
  scale: "M6 17.4 H18 M7.2 17.4 V13 h3.2 v4.4 M11.4 17.4 V9.2 h3.2 V17.4 M15.4 17.4 V6.4 H18",
  decide: "M6 17.4 H18 M7.2 17.4 V13 h3.2 v4.4 M11.4 17.4 V9.2 h3.2 V17.4 M15.4 17.4 V6.4 H18",
  builder: "M7.2 16.8 L12 6.4 16.8 16.8 Z M12 10.8 v3.6",
  data: "M6 16.6 V11.2 h3.2 V16.6 Z M10.4 16.6 V7.2 h3.2 V16.6 Z M14.8 16.6 V9.4 H18 V16.6 Z",
  navy: "M12 5.2 l1.4 3.2 H17 l-2.8 2 1.1 3.4 L12 11.8 8.7 13.8 9.8 10.4 7 8.4 h3.6 Z M6.4 17.2 h11.2",
  first: "M8.4 16.8 V7.2 h3.4 a3.2 3.2 0 0 1 0 6.4 H8.4",
  intent: "M6.4 12 a5.6 5.6 0 1 0 5.6-5.6 M12 8.8 v3.6 l2.4 1.6",
  programme: "M7.2 16.4 V7.6 l4.8 2.2 4.8-2.2 v8.8 l-4.8 2.2 Z",
};

export function SceneMark({
  name,
  className,
}: {
  name: string;
  className?: string;
}) {
  return (
    <svg viewBox="0 0 24 24" className={cn("h-11 w-11", className)} aria-hidden="true">
      <path d={PATHS[name] ?? PATHS.discover} fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
