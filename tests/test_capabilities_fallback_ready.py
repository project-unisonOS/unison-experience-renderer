from importlib import import_module
import os

# Ensure src is on path for Docker test runs
SERVICE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC_ROOT = os.path.join(SERVICE_ROOT, "src")
import sys
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

main = import_module("main")
ready = main.ready
_capability_client = main._capability_client
from fastapi import Request


class DummyScope:
    def __init__(self):
        self.state = type("State", (), {})()


def test_ready_injects_fallback_manifest(monkeypatch):
    # Force empty manifest
    _capability_client.manifest = {"modalities": {"displays": []}}
    req = Request({"type": "http", "headers": [], "path": "/ready"})
    resp = ready(req)
    assert resp["checks"]["displays"] >= 1
    assert _capability_client.modality_count("displays") >= 1
