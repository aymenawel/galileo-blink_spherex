/** The width of an element in CSS pixels, kept current as the layout changes. */
import { useEffect, useRef, useState, type RefObject } from "react";

export function useElementWidth<T extends HTMLElement>(fallback: number): [RefObject<T>, number] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new ResizeObserver((entries) => {
      const measured = entries[0]?.contentRect.width;
      if (measured) setWidth(Math.round(measured));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return [ref, width];
}
