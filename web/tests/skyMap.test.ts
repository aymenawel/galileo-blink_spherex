/** Checks of the all-sky map's geometry: a click on the oval must open the right place. */
import assert from "node:assert/strict";
import { test } from "node:test";
import { equatorialToGalactic, mapToSky, skyToMap } from "../src/lib/skyMap.ts";

const near = (a: number, b: number, tolerance: number) => Math.abs(a - b) <= tolerance;

/** Separation of two sky positions in degrees. */
function separation(a: { ra: number; dec: number }, b: { ra: number; dec: number }): number {
  const r = Math.PI / 180;
  const cos =
    Math.sin(a.dec * r) * Math.sin(b.dec * r) + Math.cos(a.dec * r) * Math.cos(b.dec * r) * Math.cos((a.ra - b.ra) * r);
  return Math.acos(Math.max(-1, Math.min(1, cos))) / r;
}

/** NASA's five test targets (catalogue positions). */
const TARGETS = [
  { id: "barnard", ra: 269.4485, dec: 4.7394 },
  { id: "epsindib", ra: 331.0765, dec: -56.7938 },
  { id: "wise0855", ra: 133.7948, dec: -7.2451 },
  { id: "rwaur", ra: 76.9561, dec: 30.4012 },
  { id: "rdra", ra: 248.1674, dec: 66.755 },
];

test("the Galactic centre is the middle of the map", () => {
  const p = skyToMap(266.405, -28.936);
  assert.ok(near(p.x, 0.5, 1e-4) && near(p.y, 0.5, 1e-4), JSON.stringify(p));
  const sky = mapToSky(0.5, 0.5);
  assert.ok(sky && separation(sky, { ra: 266.405, dec: -28.936 }) < 0.01, JSON.stringify(sky));
});

test("the north Galactic pole is the top of the map, the south pole the bottom", () => {
  const north = skyToMap(192.859, 27.128);
  assert.ok(near(north.x, 0.5, 1e-3) && near(north.y, 0, 1e-4), JSON.stringify(north));
  const top = mapToSky(0.5, 0);
  assert.ok(top && separation(top, { ra: 192.859, dec: 27.128 }) < 0.01, JSON.stringify(top));
  const south = skyToMap(12.859, -27.128);
  assert.ok(near(south.y, 1, 1e-4), JSON.stringify(south));
});

test("Galactic longitude grows to the left: Cygnus left of centre, the Large Magellanic Cloud right and below", () => {
  const cygnus = skyToMap(305.0, 40.0); // l ≈ 77°
  assert.ok(cygnus.x < 0.5 && near(cygnus.y, 0.5, 0.03), JSON.stringify(cygnus));
  const lmc = skyToMap(80.894, -69.756); // l ≈ 280°, b ≈ −33°
  assert.ok(lmc.x > 0.65 && lmc.y > 0.65, JSON.stringify(lmc));
});

test("the equatorial to Galactic rotation matches the standard values", () => {
  const { l, b } = equatorialToGalactic(80.894, -69.756);
  assert.ok(near(l, 280.465, 1e-3) && near(b, -32.888, 1e-3), `${l} ${b}`);
});

test("sky to map and back returns the same place", () => {
  for (let ra = 0; ra < 360; ra += 23.7) {
    for (let dec = -85; dec <= 85; dec += 17) {
      const p = skyToMap(ra, dec);
      const back = mapToSky(p.x, p.y);
      assert.ok(back, `(${ra}, ${dec}) fell outside the oval`);
      assert.ok(separation(back, { ra, dec }) < 1e-6, `(${ra}, ${dec}) came back as ${JSON.stringify(back)}`);
    }
  }
});

test("map to sky and back returns the same point", () => {
  for (let x = 0.05; x < 1; x += 0.07) {
    for (let y = 0.05; y < 1; y += 0.07) {
      const sky = mapToSky(x, y);
      if (!sky) continue;
      const p = skyToMap(sky.ra, sky.dec);
      assert.ok(near(p.x, x, 1e-7) && near(p.y, y, 1e-7), `(${x}, ${y}) came back as ${JSON.stringify(p)}`);
    }
  }
});

test("outside the oval there is no sky", () => {
  assert.equal(mapToSky(0.02, 0.02), null);
  assert.equal(mapToSky(0.98, 0.98), null);
  assert.equal(mapToSky(0.1, 0.1), null);
  assert.equal(mapToSky(-0.1, 0.5), null);
  assert.equal(mapToSky(0.5, 1.1), null);
  assert.ok(mapToSky(0.01, 0.5), "the left tip of the oval is sky");
});

test("the five test targets land inside the oval", () => {
  for (const t of TARGETS) {
    const p = skyToMap(t.ra, t.dec);
    assert.ok(p.x > 0 && p.x < 1 && p.y > 0 && p.y < 1, `${t.id} at ${JSON.stringify(p)}`);
    const back = mapToSky(p.x, p.y);
    assert.ok(back && separation(back, t) < 1e-6, `${t.id} came back as ${JSON.stringify(back)}`);
  }
});
