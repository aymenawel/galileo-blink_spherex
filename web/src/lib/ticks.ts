/** Round tick values for a plot axis. */

/** Evenly spaced round numbers covering [low, high], about `target` of them. */
export function niceTicks(low: number, high: number, target = 5): number[] {
  const span = high - low;
  if (!(span > 0)) return [low];
  const rough = span / target;
  const power = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 5, 10].map((m) => m * power).find((s) => s >= rough) ?? 10 * power;
  const ticks: number[] = [];
  for (let value = Math.ceil(low / step - 1e-9) * step; value <= high + step * 1e-9; value += step) {
    ticks.push(Math.abs(value) < step * 1e-9 ? 0 : Number(value.toPrecision(12)));
  }
  return ticks;
}

/** Powers of ten inside [low, high], for a log axis. */
export function decadeTicks(low: number, high: number): number[] {
  const ticks: number[] = [];
  for (let e = Math.ceil(Math.log10(low) - 1e-9); e <= Math.floor(Math.log10(high) + 1e-9); e += 1) {
    ticks.push(10 ** e);
  }
  return ticks;
}
