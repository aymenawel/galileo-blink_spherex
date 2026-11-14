/** Checks of the arithmetic that places markers on pictures and reads sky positions off them. */
import assert from "node:assert/strict";
import { test } from "node:test";
import { formatDec, formatRa } from "../src/lib/format.ts";
import { chooseScaleBar, fractionToPixel, pixelToFraction, pixelToSky } from "../src/lib/geometry.ts";

const N = 89;

test("a pixel centre maps to the middle of its cell, with y pointing up", () => {
  assert.deepEqual(pixelToFraction(0, 0, N), { left: 0.5 / N, top: (N - 0.5) / N });
  assert.deepEqual(pixelToFraction(N - 1, N - 1, N), { left: (N - 0.5) / N, top: 0.5 / N });
  assert.deepEqual(pixelToFraction(44, 44, N), { left: 0.5, top: 0.5 });
});

test("screen fraction and pixel position are inverses", () => {
  const { left, top } = pixelToFraction(44.11, 43.2, N);
  const back = fractionToPixel(left, top, N);
  assert.ok(Math.abs(back.x - 44.11) < 1e-9 && Math.abs(back.y - 43.2) < 1e-9);
});

test("the centre pixel is the view's own position; east is to the left", () => {
  const view = { ra: 269.4464, dec: 4.7686, n: N, pixel_arcsec: 6.15 };
  const centre = pixelToSky(44, 44, view);
  assert.ok(Math.abs(centre.ra - view.ra) < 1e-9 && Math.abs(centre.dec - view.dec) < 1e-9);
  assert.ok(pixelToSky(34, 44, view).ra > view.ra, "left of centre is east: larger right ascension");
  assert.ok(pixelToSky(44, 54, view).dec > view.dec, "above centre is north");
  assert.ok(Math.abs(pixelToSky(44, 54, view).dec - view.dec - 61.5 / 3600) < 1e-9);
});

test("the scale bar is one arcminute on a small view", () => {
  const bar = chooseScaleBar(N, 6.15);
  assert.equal(bar.arcminutes, 1);
  assert.ok(Math.abs(bar.fraction - 60 / 6.15 / N) < 1e-12);
});

test("coordinates are printed the way catalogues print them", () => {
  assert.equal(formatRa(269.4464), "17h 57m 47.1s");
  assert.equal(formatDec(4.7686), "+04° 46′ 07″");
  assert.equal(formatDec(-7.2422), "−07° 14′ 32″");
});
