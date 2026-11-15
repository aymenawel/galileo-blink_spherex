"""NASA's quality flags in plain words."""
from galileo_blink.engine import flags


def test_a_streak_is_described_as_something_in_orbit():
    assert flags.FLAG_INFO[25] == ("STREAK", "A trail from a satellite or space debris")
