/** A short confirmation that appears at the bottom of the screen and leaves by itself. */
import { useEffect } from "react";

interface ToastProps {
  message: string | null;
  onDone: () => void;
}

const SHOWN_FOR_MS = 2400;

export function Toast({ message, onDone }: ToastProps) {
  useEffect(() => {
    if (!message) return;
    const timer = window.setTimeout(onDone, SHOWN_FOR_MS);
    return () => window.clearTimeout(timer);
  }, [message, onDone]);

  return (
    <div className="toast-region" role="status" aria-live="polite">
      {message && <p className="toast">{message}</p>}
    </div>
  );
}
