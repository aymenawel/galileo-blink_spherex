"""Registration against field stars, and measured-versus-predicted motion."""
import math

import numpy as np

from galileo_blink.engine.image.measure import measure
from galileo_blink.engine.looks import astrometry as A
from galileo_blink.engine.sky.motion import Mover, predict

from .synth import make_photo, offset_sky

CENTRE = (180.0, 0.0)
EPOCH = 61000.0


def star(name, east, north, pmra=0.0, pmdec=0.0, gmag=13.0):
    ra, dec = offset_sky(*CENTRE, east, north)
    return Mover(name, "Gaia DR3", name, ra, dec, EPOCH, pmra=pmra, pmdec=pmdec, gmag=gmag)


FIELD = [star(f"ref{i}", e, n) for i, (e, n) in enumerate(
    [(150, 120), (-170, 90), (120, -160), (-140, -150), (200, -30), (-60, 210), (30, -220), (-220, 20)])]


def photo_at(mjd, movers, shift=(0.0, 0.0), seed=0, flux=60.0, noise=0.01, target_flux=None,
             camera=6):
    stars = []
    for m in movers:
        f = target_flux if (target_flux is not None and m.name == "target") else flux
        stars.append((*predict(m, mjd), f))
    return make_photo(*CENTRE, stars=stars, mjd=mjd, shift_arcsec=shift, seed=seed, noise=noise,
                      camera=camera, roll_deg=24.0 if seed % 2 else 204.0)


def run(target, truth, shifts, target_flux=None, seasons=(EPOCH, EPOCH + 365.25), per_look=4):
    """Build sightings for `truth` (what is really in the sky), measured against `target`
    (what the catalogue says)."""
    sightings, reg_err, ref_s = [], {}, {}
    k = 0
    for s, mjd in enumerate(seasons):
        errs = []
        for j in range(per_look):
            p = photo_at(mjd + 0.01 * j, FIELD + [truth], shift=shifts[k % len(shifts)], seed=k,
                         target_flux=target_flux)
            k += 1
            reg, refs = A.register(p, FIELD)
            errs.append(reg.error)
            sightings.append(A.corrected(measure(p, *predict(target, p.mjd)), reg, s))
            for i, m in refs.items():
                ref_s.setdefault(i, {}).setdefault(s, []).append(A.corrected(m, reg, s))
        reg_err[(6, s)] = float(np.median(errs)) / math.sqrt(per_look)
    ref_looks = {6: {i: {s: A.look_position(g, reg_err[(6, s)]) for s, g in per.items()}
                     for i, per in ref_s.items()}}
    return A.measure_motion(target, sightings, reg_err, ref_looks)


SHIFTS = [(0.9, -0.6), (-0.7, 0.8), (0.4, 1.0), (-1.1, -0.3), (0.2, -0.9), (1.0, 0.5), (-0.5, 0.6), (0.6, -1.0)]


def test_registration_recovers_a_photos_astrometric_error():
    p = photo_at(EPOCH, FIELD, shift=(0.9, -0.6))
    reg, refs = A.register(p, FIELD)
    assert reg.n_stars >= 6
    assert abs(reg.east - 0.9) < 0.15 and abs(reg.north + 0.6) < 0.15
    assert reg.error < 0.2


def test_a_fast_star_is_measured_despite_arcsecond_errors_in_every_photo():
    target = Mover("target", "Gaia DR3", "t", *CENTRE, EPOCH, pmra=-0.8, pmdec=10.36, gmag=9.0)
    best, per_cam, reason, _ = run(target, target, SHIFTS)
    assert reason is None and best.agrees and best.same_time_of_year
    assert abs(best.predicted - 10.39) < 0.02
    assert abs(best.measured - best.predicted) < 0.4
    assert best.error < 0.5                                 # far tighter than the 1" raw floor
    assert best.n_reference_stars >= 6 and best.floor < 0.4


def test_motion_in_the_wrong_direction_is_not_called_agreement():
    catalogue = Mover("target", "Gaia DR3", "t", *CENTRE, EPOCH, pmra=0.0, pmdec=1.2, gmag=9.0)
    truth = Mover("target", "Gaia DR3", "t", *CENTRE, EPOCH, pmra=0.0, pmdec=-1.2, gmag=9.0)
    best, _, reason, _ = run(catalogue, truth, SHIFTS)
    assert reason is None
    assert abs(best.measured - best.predicted) < 0.5        # the LENGTHS agree...
    assert best.residual > 2 and not best.agrees            # ...the arrows do not


def test_a_star_that_does_not_move_is_consistent_with_zero():
    target = Mover("target", "Gaia DR3", "t", *CENTRE, EPOCH, pmra=0.0, pmdec=0.0, gmag=9.0)
    best, _, _, _ = run(target, target, SHIFTS)
    assert best.agrees and best.measured < 3 * best.error


def test_a_static_neighbour_is_not_reported_as_the_moving_target():
    # the catalogue says the target moves 8"/yr; what is really there stays put
    catalogue = Mover("target", "CatWISE2020", "t", *CENTRE, EPOCH, pmra=-8.0, pmdec=0.5)
    neighbour = Mover("target", "x", "t", *CENTRE, EPOCH, pmra=0.0, pmdec=0.0)
    best, _, reason, _ = run(catalogue, neighbour, SHIFTS)
    assert best is None and reason == "off_track"


def test_pure_noise_is_too_faint_not_a_measurement():
    target = Mover("target", "CatWISE2020", "t", *CENTRE, EPOCH, pmra=-8.0, pmdec=0.5)
    best, _, reason, _ = run(target, target, SHIFTS, target_flux=0.0)
    assert best is None and reason == "too_faint"


def test_one_season_cannot_show_motion():
    target = Mover("target", "Gaia DR3", "t", *CENTRE, EPOCH, pmra=0.0, pmdec=5.0)
    best, _, reason, _ = run(target, target, SHIFTS, seasons=(EPOCH,))
    assert best is None and reason == "one_season"


def test_reference_stars_avoid_the_target_and_crowded_pairs():
    target = star("target", 0, 0, gmag=9.0)
    close_pair = [star("a", 100, 100, gmag=12.0), star("b", 108, 100, gmag=12.5)]
    faint = star("faint", -100, -100, gmag=19.0)
    near_target = star("near", 8, 0, gmag=12.0)
    good = star("good", -150, 150, gmag=12.0)
    picked = A.pick_reference_stars([target, *close_pair, faint, near_target, good], [target], EPOCH)
    assert [s.name for s in picked] == ["good"]


def test_cameras_combine_into_one_tighter_measurement():
    def m(cam, east, north, error):
        return A.Motion(camera=cam, first_season=0, last_season=2, years=1.0, same_time_of_year=True,
                        measured=math.hypot(east, north), measured_east=east, measured_north=north,
                        predicted=10.0, predicted_east=0.0, predicted_north=10.0, error=error,
                        residual=math.hypot(east, north - 10.0), agrees=True, floor=0.2,
                        n_reference_stars=8)
    both = A.combine_cameras({5: m(5, 0.4, 10.6, 0.6), 6: m(6, -0.4, 9.4, 0.6)})
    assert both["n_cameras"] == 2 and abs(both["measured"] - 10.0) < 1e-6
    assert abs(both["error"] - 0.6 / math.sqrt(2)) < 1e-3 and both["agrees"]
    assert A.combine_cameras({6: m(6, 0, 10, 0.5)}) is None
