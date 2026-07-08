import state


def test_roundtrip_and_missing_file(tmp_path):
    p = tmp_path / "processed_ids.json"
    assert state.load_seen(str(p)) == set()          # missing file -> empty
    state.save_seen(str(p), {"a", "b"})
    assert state.load_seen(str(p)) == {"a", "b"}
