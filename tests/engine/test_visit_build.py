"""Choosing a visit, grouping its moments, and reading NASA's moving-object answers."""
from galileo_blink.engine.archive.photos import PhotoRef
from galileo_blink.engine.sky.asteroids import Sighting, best_visit, parse_most
from galileo_blink.engine.visit.build import choose_visit, moments_of, thin


def refs(camera, mjds):
    return [PhotoRef(file=f"c{camera}_{m:.4f}.fits", path="x", camera=camera, mjd=m, collection="s")
            for m in mjds]


def test_a_burst_of_photos_is_one_moment():
    mjds = [100.000, 100.002, 100.004, 100.300, 100.301, 101.000]
    assert moments_of(mjds) == [[0, 1, 2], [3, 4], [5]]


def test_the_visit_with_the_most_separate_moments_is_chosen():
    photos = (refs(2, [100.0, 100.001, 100.002, 100.003])            # 4 photos, but one moment
              + refs(3, [200.0, 200.3, 200.6, 200.9, 201.2])         # 5 moments
              + refs(3, [400.0, 400.3]))                             # a later, shorter visit
    camera, chosen = choose_visit(photos, None, None, None)
    assert camera == 3 and [p.mjd for p in chosen] == [200.0, 200.3, 200.6, 200.9, 201.2]


def test_continuous_coverage_is_narrowed_to_ten_days():
    photos = refs(1, [500.0 + 0.5 * i for i in range(200)])          # 100 days without a gap
    _, chosen = choose_visit(photos, 1, None, None)
    assert chosen[-1].mjd - chosen[0].mjd <= 10.0
    assert chosen[-1].mjd == 599.5                                   # the most recent stretch
    assert len(moments_of([p.mjd for p in chosen])) >= 12            # with plenty of moments


def test_an_asked_for_window_is_respected():
    photos = refs(4, [10.0, 10.2, 10.4, 50.0, 50.2, 50.4, 50.6])
    camera, chosen = choose_visit(photos, 4, 9.9, 10.5)
    assert camera == 4 and [p.mjd for p in chosen] == [10.0, 10.2, 10.4]


def test_thinning_keeps_every_moment():
    photos = refs(1, [k + 0.001 * j for k in range(6) for j in range(10)])   # 6 moments x 10
    kept = thin(photos, 18)
    assert len(kept) == 18 and len(moments_of([p.mjd for p in kept])) == 6


MOST_ANSWER = """\\catalog = "spherex"
\\object_name = "324 Bamberga (A892 DA)"
|    ra_obj|   dec_obj|sun_dist|geo_dist|  dist_ctr|   phase|  vmag|match|proposal_id|target_name|target_moving|observationid|planeid|productid|instrument|start_date|end_date|mjd_start|mjd_end|
 199.274149 -22.877859   3.3971   2.6339     0.9548  12.8278  12.86     1  null  SPS_112615_S12  0  2025W23_1C_0309_1  01A0D1EF-43E7  D6  SPHEREx  2025-06-03 17:02:18.157  2025-06-03 17:04:13.275  60829.709932384  60829.711264763  113.5826
 199.274018 -22.877604   3.3971   2.6340     0.8144  12.8282  12.86     1  null  SPS_112616_S12  0  2025W23_1C_0310_1  01A0D1EF-43E8  D3  SPHEREx  2025-06-03 17:05:18.157  2025-06-03 17:07:13.275  60829.712015384  60829.713347763  113.5826
"""


def test_nasas_moving_object_answer_is_read():
    name, sightings = parse_most(MOST_ANSWER)
    assert name == "324 Bamberga (A892 DA)" and len(sightings) == 2
    s = sightings[0]
    assert (s.camera, s.obs_id, s.vmag) == (6, "2025W23_1C_0309_1", 12.86)
    assert abs(s.mjd - 60829.709932384) < 1e-9 and abs(s.ra - 199.274149) < 1e-9


def test_the_best_asteroid_visit_needs_three_moments_and_fits_one_view():
    def s(mjd, ra, cam=3):
        return Sighting(mjd=mjd, camera=cam, obs_id="x", ra=ra, dec=0.0, vmag=13.0)
    # camera 3: five moments, the asteroid moving 0.05 deg between them
    sightings = [s(100 + 0.25 * k, 10.0 + 0.05 * k) for k in range(5)] + [s(100.0, 10.0, cam=2)]
    visit = best_visit("Test", sightings)
    assert visit.camera == 3 and visit.n_moments == 5
    assert abs(visit.ra - 10.1) < 0.01 and 0.3 < visit.size_deg <= 0.5
