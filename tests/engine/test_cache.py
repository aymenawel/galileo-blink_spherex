"""The disk cache: safe writes, tolerant reads, and trimming."""
import os
import time

from galileo_blink.engine.archive import cache


def test_a_corrupt_file_is_removed_and_reads_as_missing(tmp_path):
    path = tmp_path / "x.json"
    path.write_text("{not json")
    assert cache.read_json(path) is None and not path.exists()
    cache.write_json(path, {"a": 1})
    assert cache.read_json(path) == {"a": 1}
    assert not list(tmp_path.glob("*.tmp"))                 # no scratch files left behind


def test_trimming_removes_the_oldest_entries_first(tmp_path):
    for i, name in enumerate(["old", "middle", "new"]):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "data.bin").write_bytes(b"x" * 1000)
        stamp = time.time() - 100 + i
        os.utime(folder, (stamp, stamp))
    assert cache.trim(tmp_path, 2500) == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == ["middle", "new"]
    assert cache.trim(tmp_path, 10_000) == 0
    assert cache.trim(tmp_path / "missing", 10) == 0
