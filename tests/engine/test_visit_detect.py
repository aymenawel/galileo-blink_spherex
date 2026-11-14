"""Finding movers within one visit by image subtraction."""
import numpy as np

from galileo_blink.engine.visit.detect import find_movers

from .synth import star_image

N = 89


def field(seed, n_stars=40):
    rng = np.random.default_rng(seed)
    sky = np.zeros((N, N))
    for _ in range(n_stars):
        sky += star_image((N, N), rng.uniform(3, N - 3), rng.uniform(3, N - 3), rng.uniform(0.3, 30))
    return sky, rng


def visit(seed, mover=None, n_moments=5, hours=6.0, noise=0.02, colour_flicker=0.15, n_stars=40):
    """Moments of one field. `mover` = (x0, y0, vx_px_per_day, vy_px_per_day, flux)."""
    sky, rng = field(seed, n_stars)
    days = [k * hours / 24.0 for k in range(n_moments)]
    moments = []
    for t in days:
        # every moment sees the stars at a slightly different wavelength: they flicker together
        img = sky * (1.0 + rng.uniform(-colour_flicker, colour_flicker)) + rng.normal(0, noise, (N, N))
        if mover:
            x0, y0, vx, vy, flux = mover
            img += star_image((N, N), x0 + vx * t, y0 + vy * t, flux)
        moments.append(img)
    return moments, days, sky


def test_an_asteroid_is_found_with_its_speed_and_direction():
    moments, days, _ = visit(1, mover=(20.0, 30.0, 40.0, 12.0, 1.2))
    tracks, _, _ = find_movers(moments, days)
    assert len(tracks) == 1
    t = tracks[0]
    assert t.confidence == "strong" and len(t.detections) == 5
    assert abs(t.vx - 40.0) < 2 and abs(t.vy - 12.0) < 2
    assert abs(t.speed_arcsec_per_hour - np.hypot(40, 12) * 6.15 / 24) < 0.6
    assert t.rms_px < 0.5


def test_empty_fields_give_no_tracks():
    found = 0
    for seed in range(20):
        moments, days, _ = visit(seed)
        tracks, _, _ = find_movers(moments, days)
        found += sum(1 for t in tracks if t.confidence == "strong")
    assert found == 0


def test_a_cosmic_ray_in_one_moment_is_not_a_mover():
    moments, days, _ = visit(3)
    moments[2][40, 50] += 5.0
    tracks, _, _ = find_movers(moments, days)
    assert not tracks


def test_an_asteroid_crossing_a_star_is_still_found():
    # the mover passes right over a bright static star at the third moment
    moments, days, _ = visit(4, n_stars=0, mover=(30.0, 40.0, 24.0, 0.0, 1.0))
    star = star_image((N, N), 30.0 + 24.0 * days[2], 40.0, 6.0)
    moments = [m + star * (1.0 + 0.05 * k) for k, m in enumerate(moments)]
    tracks, _, _ = find_movers(moments, days)
    assert len(tracks) == 1 and len(tracks[0].detections) >= 4
    assert tracks[0].confidence == "strong"


def test_three_sightings_alone_are_only_possible():
    moments, days, _ = visit(5, n_moments=3, mover=(20.0, 30.0, 60.0, 20.0, 1.5))
    tracks, _, _ = find_movers(moments, days)
    assert [t.confidence for t in tracks] in (["possible"], [])


def test_two_moments_cannot_show_a_mover_at_all():
    moments, days, _ = visit(6, n_moments=2, mover=(20.0, 30.0, 60.0, 20.0, 5.0))
    assert find_movers(moments, days)[0] == []
