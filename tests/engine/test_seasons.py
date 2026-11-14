"""Grouping photos into looks and seasons."""
from galileo_blink.engine.archive.photos import PhotoRef
from galileo_blink.engine.looks.seasons import camera_looks, choose, group_seasons, spread


def refs(camera, mjds):
    return [PhotoRef(file=f"c{camera}_{m:.3f}.fits", path="x", camera=camera, mjd=m, collection="s")
            for m in mjds]


def test_a_gap_of_more_than_30_days_starts_a_new_look():
    looks = camera_looks(refs(6, [100, 101, 103, 300, 301, 480]))
    assert [len(l) for l, _ in looks] == [3, 2, 1]
    assert all(month is None for _, month in looks)


def test_continuous_coverage_is_cut_by_calendar_month():
    # near the ecliptic poles photos never stop: one photo every 2 days for 4 months
    looks = camera_looks(refs(3, [61000 + 2 * i for i in range(60)]))
    assert 4 <= len(looks) <= 5
    assert all(l[-1].mjd - l[0].mjd <= 31 and month for l, month in looks)


def test_cameras_with_different_dates_share_seasons():
    # cameras 1 and 4 looked in October, the others in November: still one season
    photos = (refs(1, [60960, 60961]) + refs(4, [60962]) + refs(2, [60985, 60986])
              + refs(5, [60987]) + refs(2, [61170, 61171]) + refs(5, [61172]))
    seasons = group_seasons(photos)
    assert len(seasons) == 2
    assert set(seasons[0].by_camera) == {1, 2, 4, 5}
    assert set(seasons[1].by_camera) == {2, 5}            # cameras 1 and 4: no photos this season
    assert seasons[0].label == "Nov 2025" or seasons[0].label == "Oct 2025"


def test_continuous_coverage_steps_month_by_month_across_cameras():
    photos = []
    for cam in (1, 3, 6):
        photos += refs(cam, [61000 + 3 * i + cam for i in range(50)])   # five months, continuous
    photos += refs(2, [61040, 61041])                     # a camera with one ordinary look
    seasons = group_seasons(photos)
    assert 5 <= len(seasons) <= 6
    assert len({s.label for s in seasons}) == len(seasons)             # one season per month
    assert sum(1 for s in seasons if 2 in s.by_camera) == 1            # joined a month, no duplicate
    for s in seasons:
        dates = [p.mjd for ps in s.by_camera.values() for p in ps]
        assert max(dates) - min(dates) <= 31


def test_spread_keeps_the_ends():
    r = refs(6, range(10))
    picked = spread(r, 4)
    assert picked[0] is r[0] and picked[-1] is r[-1] and len(picked) == 4
    assert spread(r[:2], 4) == r[:2]


def test_choose_keeps_first_and_last_seasons_within_the_limits():
    photos = []
    for k in range(10):                                   # ten seasons, six cameras, 8 photos each
        for cam in range(1, 7):
            photos += refs(cam, [60000 + 180 * k + 0.01 * i for i in range(8)])
    seasons = group_seasons(photos)
    chosen, left_out = choose(seasons, per_look=4, max_seasons=8, max_photos=96)
    assert len(chosen) == 4 and left_out == 6             # 4 seasons x 6 cameras x 4 photos = 96
    assert chosen[0].mjd == seasons[0].mjd and chosen[-1].mjd == seasons[-1].mjd
    assert [s.index for s in chosen] == [0, 1, 2, 3]
    assert all(len(ps) == 4 for s in chosen for ps in s.by_camera.values())
