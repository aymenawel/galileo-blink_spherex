/**
 * One switch for every self-running preview on a page: anything that blinks by itself can
 * be stopped by the visitor, and started again.
 */
import { useSyncExternalStore } from "react";

let paused = false;
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Stop or restart every preview. */
export function setPreviewsPaused(next: boolean): void {
  paused = next;
  listeners.forEach((listener) => listener());
}

/** True while the visitor has the previews stopped. */
export function usePreviewsPaused(): boolean {
  return useSyncExternalStore(subscribe, () => paused);
}
