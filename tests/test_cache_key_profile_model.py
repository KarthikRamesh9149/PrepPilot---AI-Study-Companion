from exam_helper.utils.cache import cache_key


def test_cache_key_profile_model():
    k1 = cache_key(["v2", "module", "plan", "2026-02-24", "2026-03-01", "modelA", "{'hours':2}"])
    k2 = cache_key(["v2", "module", "plan", "2026-02-24", "2026-03-01", "modelB", "{'hours':2}"])
    k3 = cache_key(["v2", "module", "plan", "2026-02-24", "2026-03-01", "modelA", "{'hours':4}"])
    assert k1 != k2
    assert k1 != k3
