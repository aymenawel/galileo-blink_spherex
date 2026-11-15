/** A bar of known length on the sky, so sizes in the picture mean something. */
import { chooseScaleBar } from "../../lib/geometry";

interface ScaleBarProps {
  /** Width of the view in SPHEREx pixels. */
  n: number;
  pixelArcsec: number;
}

export function ScaleBar({ n, pixelArcsec }: ScaleBarProps) {
  const bar = chooseScaleBar(n, pixelArcsec);
  const label = bar.arcminutes === 1 ? "1 arcminute" : `${bar.arcminutes} arcminutes`;
  return (
    <div className="scale-bar" style={{ width: `${bar.fraction * 100}%` }}>
      <span className="scale-bar__line" aria-hidden="true" />
      <span className="scale-bar__label">{label}</span>
    </div>
  );
}
