from pathlib import Path

from exam_helper.utils.cache import cache_key, get_cached, set_cached
from exam_helper.utils.hash import hash_files_on_disk


def test_cache_key_stability():
    key1 = cache_key(["a", "b", "c"])
    key2 = cache_key(["a", "b", "c"])
    assert key1 == key2


def test_cache_roundtrip(tmp_path):
    path = tmp_path / "cache.json"
    set_cached(path, "k", {"x": 1})
    assert get_cached(path, "k") == {"x": 1}


def test_hash_files_on_disk_deterministic(tmp_path):
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("alpha", encoding="utf-8")
    f2.write_text("beta", encoding="utf-8")

    h1 = hash_files_on_disk([f1, f2])
    h2 = hash_files_on_disk([f2, f1])
    assert h1 == h2
