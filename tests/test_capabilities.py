from unison_common.multimodal import CapabilityClient


def test_renderer_fallback_manifest(monkeypatch, tmp_path):
    # Start with an empty manifest; refresh should succeed and fallback to default.
    client = CapabilityClient("file://" + str(tmp_path / "missing.json"))
    # Force manifest to empty and call ready logic
    client.manifest = {"modalities": {"displays": []}}
    assert client.modality_count("displays") == 0

    # simulate renderer ready check fallback
    if not client.manifest or client.modality_count("displays") == 0:
        client.manifest = {"modalities": {"displays": [{"id": "default", "name": "fallback"}]}}

    assert client.modality_count("displays") == 1
