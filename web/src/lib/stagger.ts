/** The staggered entrance: elements with the `rise` class appear one after another. */
import type { CSSProperties } from "react";

/** Style that sets an element's place in the entrance order (0 appears first). */
export function riseOrder(position: number): CSSProperties {
  return { "--i": position } as CSSProperties;
}
