/**
 * NASA's flagged pixels, tinted on top of the picture. The server sends a white-on-clear
 * mask; here it becomes a stencil for a block of colour.
 */
interface FlagsOverlayProps {
  /** Address of the mask picture. */
  mask: string;
}

export function FlagsOverlay({ mask }: FlagsOverlayProps) {
  const stencil = `url("${mask}")`;
  return <div className="flags-overlay" style={{ maskImage: stencil, WebkitMaskImage: stencil }} aria-hidden="true" />;
}
