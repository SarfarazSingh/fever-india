import type { Variants } from "framer-motion";

export const EASE = [0.22, 1, 0.36, 1] as const;

export function sceneVariants(reduced: boolean): Variants {
  if (reduced) {
    return {
      initial: { opacity: 0 },
      animate: { opacity: 1 },
      exit: { opacity: 0 },
    };
  }
  return {
    initial: { opacity: 0, y: 28, scale: 0.988 },
    animate: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: -20, scale: 0.992 },
  };
}

export const sceneTransition = {
  duration: 0.58,
  ease: EASE,
};
