"""Build the views of NASA's five test targets, so the site opens them instantly.

    python scripts/prebuild_targets.py              # all five, into the cache
    python scripts/prebuild_targets.py barnard      # just one
    python scripts/prebuild_targets.py --ship       # also copy them into prebuilt/ (committed)

Run it again after a new SPHEREx data release to refresh them.
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from galileo_blink.engine.looks.build import build_view, target_request, view_dir  # noqa: E402
from galileo_blink.engine.sky import targets  # noqa: E402

PREBUILT = Path(__file__).resolve().parents[1] / "prebuilt"


def main(argv: list[str]) -> int:
    ship = "--ship" in argv
    wanted = [a for a in argv if not a.startswith("--")] or [t.id for t in targets.targets()]
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
        if ship:
            dest = PREBUILT / req.key
            shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(view_dir(req.key), dest)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
