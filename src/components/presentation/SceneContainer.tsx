import type { ReactNode } from "react";
import { cn } from "../../lib/cn";
import { SceneAtmosphere } from "../motion/SceneAtmosphere";

export function SceneContainer({
  children,
  className,
  width = "max-w-[1480px]",
  scroll = false,
}: {
  children: ReactNode;
  className?: string;
  width?: string;
  scroll?: boolean;
}) {
  return (
    <div className={cn("relative h-full px-5 pt-14 pb-16 md:px-10 lg:px-14", scroll ? "scene-scroll overflow-y-auto" : "overflow-hidden", className)}>
      <SceneAtmosphere />
      <div className={cn("relative z-10 mx-auto flex h-full min-h-0 flex-col", width)}>{children}</div>
    </div>
  );
}
