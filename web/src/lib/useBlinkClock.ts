/** A counter that advances at a steady beat: the heartbeat of a blinking preview. */
import { useEffect, useState } from "react";

/**
 * Counts 0, 1, … `steps - 1` and around again, one step every `milliseconds`, while
 * `running` is true. Stays at 0 when there is nothing to step through.
 */
export function useBlinkClock(steps: number, milliseconds: number, running: boolean): number {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!running || steps < 2) return;
    const timer = window.setInterval(() => setStep((current) => (current + 1) % steps), milliseconds);
    return () => window.clearInterval(timer);
  }, [steps, milliseconds, running]);

  return steps > 0 ? step % steps : 0;
}
