"""Build the ready-made views (NASA's five test targets and the asteroid examples), so the
site opens them instantly.

    python scripts/prebuild_targets.py              # everything, into the cache
    python scripts/prebuild_targets.py barnard      # just one target
    python scripts/prebuild_targets.py --ship       # also copy them into prebuilt/ (committed)

Run it again after a new SPHEREx data release to refresh them.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from galileo_blink.engine.looks.build import build_view, target_request, view_dir  # noqa: E402
from galileo_blink.engine.sky import targets  # noqa: E402
from galileo_blink.engine.visit.build import VisitRequest, build_visit  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PREBUILT = ROOT / "prebuilt"
ASTEROIDS = ROOT / "data" / "asteroid_examples.json"


def ship(key: str) -> None:
    dest = PREBUILT / key
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(view_dir(key), dest, ignore=shutil.ignore_patterns("*.tmp"))


def build_asteroids(do_ship: bool) -> int:
    failed = 0
    for e in json.loads(ASTEROIDS.read_text(encoding="utf8")):
        req = VisitRequest(ra=e["ra"], dec=e["dec"], size_deg=e["size_deg"], camera=e["camera"],
                           mjd_start=e["mjd_start"], mjd_end=e["mjd_end"], label=e["name"])
        try:
            view = build_visit(req)
        except Exception as err:                    # noqa: BLE001 - report and carry on
            print(f"{e['id']}: FAILED ({err})")
            failed += 1
            continue
        found = [t["name"] or "unidentified" for t in view["tracks"] if t["confidence"] == "strong"]
        print(f"{e['id']}: {len(view['seasons'])} moments over {view['span_hours']} h; "
              f"strong tracks: {found}; degraded {view['degraded']}")
        if do_ship:
            ship(req.key)
    return failed


def main(argv: list[str]) -> int:
    do_ship = "--ship" in argv
    named = [a for a in argv if not a.startswith("--")]
    wanted = named or [t.id for t in targets.targets()]
    failed = 0
    for target_id in wanted:
        req = target_request(target_id)
        started = time.time()
        try:
            view = build_view(req)
        except Exception as e:                      # noqa: BLE001 - report and carry on
            print(f"{target_id}: FAILED ({e})")
            failed += 1
            continue
        m = view.get("motion_combined") or view.get("motion")
        motion = (f"{m['measured']:.2f} +/- {m['error']:.2f} arcsec vs {m['predicted']:.2f} predicted"
                  if m else f"not measured ({view.get('motion_reason')})")
        print(f"{target_id}: {len(view['seasons'])} seasons, {view['stats']['photos_used']} photos, "
              f"{time.time() - started:.0f} s; motion {motion}; degraded {view['degraded']}")
        if do_ship:
            ship(req.key)
    if not named:
        failed += build_asteroids(do_ship)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
