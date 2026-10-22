import type { ReactNode } from "react";

export function SourceFootnote({ children }: { children: ReactNode }) {
  return <p className="text-[14px] leading-relaxed text-soft">{children}</p>;
}
