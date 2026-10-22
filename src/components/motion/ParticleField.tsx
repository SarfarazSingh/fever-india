import { useEffect, useRef } from "react";
import { usePresentation } from "../../app/state/PresentationContext";

type Particle = { x: number; y: number; r: number; a: number; s: number; drift: number };

export function ParticleField({
  parallax = { x: 0, y: 0 },
  count = 42,
}: {
  parallax?: { x: number; y: number };
  count?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const parallaxRef = useRef(parallax);
  const { reducedMotion } = usePresentation();
  parallaxRef.current = parallax;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;
    const particles: Particle[] = Array.from({ length: count }, () => ({
      x: Math.random(),
      y: Math.random(),
      r: 0.8 + Math.random() * 2.4,
      a: 0.15 + Math.random() * 0.45,
      s: 0.00012 + Math.random() * 0.00035,
      drift: (Math.random() - 0.5) * 0.00015,
    }));

    let width = 0;
    let height = 0;
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width;
      height = rect.height;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);

    let frame = 0;
    const draw = () => {
      context.clearRect(0, 0, width, height);
      const shift = parallaxRef.current;
      for (const particle of particles) {
        if (!reducedMotion) {
          particle.y -= particle.s;
          particle.x += particle.drift;
          if (particle.y < -0.02) particle.y = 1.02;
          if (particle.x < -0.02) particle.x = 1.02;
          if (particle.x > 1.02) particle.x = -0.02;
        }
        context.beginPath();
        context.fillStyle = `rgba(233, 188, 112, ${particle.a})`;
        context.arc(particle.x * width + shift.x * 18, particle.y * height + shift.y * 12, particle.r, 0, Math.PI * 2);
        context.fill();
      }
      if (!reducedMotion) frame = requestAnimationFrame(draw);
    };
    draw();
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [count, reducedMotion]);

  return <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true" />;
}
