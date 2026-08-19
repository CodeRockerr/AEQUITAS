import { useEffect, useRef, useState } from "react";

/** Animates a number from its previous value to `target` on change (ease-out cubic). */
export function useCountUp(target: number | null, durationMs = 700): number | null {
  const [value, setValue] = useState<number | null>(target);
  const prevTarget = useRef<number | null>(target);

  useEffect(() => {
    if (target == null) {
      setValue(null);
      prevTarget.current = null;
      return;
    }
    const start = prevTarget.current ?? 0;
    const end = target;
    prevTarget.current = target;
    if (start === end) {
      setValue(end);
      return;
    }

    let raf: number;
    const t0 = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / durationMs);
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(start + (end - start) * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, durationMs]);

  return value;
}
