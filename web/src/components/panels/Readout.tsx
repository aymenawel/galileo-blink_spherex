/** An instrument readout: a small label over a large number. */
import type { ReactNode } from "react";

interface ReadoutProps {
  label: string;
  value: ReactNode;
  /** Smaller text after the value, such as an error bar or a unit. */
  suffix?: ReactNode;
  tone?: "plain" | "ember" | "ice";
  size?: "large" | "small";
}

export function Readout({ label, value, suffix, tone = "plain", size = "small" }: ReadoutProps) {
  return (
    <div className={`readout readout--${tone} readout--${size}`}>
      <dt className="eyebrow">{label}</dt>
      <dd className="readout__value mono">
        {value}
        {suffix && <span className="readout__suffix">{suffix}</span>}
      </dd>
    </div>
  );
}
