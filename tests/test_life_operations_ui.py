from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_private_source_and_connection_controls_are_accessible():
    html = (ROOT / "src/web/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/web/lifeOperations.js").read_text(encoding="utf-8")
    assert 'id="lifeSourceFiles"' in html and 'multiple accept=' in html
    assert 'id="lifeCameraPages"' in html and 'capture="environment"' in html
    assert 'role="status" aria-live="polite"' in html
    assert "document instructions are treated as untrusted content" in html.lower()
    assert "read-only scopes" in html
    assert ".focus()" in script


def test_browser_never_collects_provider_credentials():
    html = (ROOT / "src/web/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/web/lifeOperations.js").read_text(encoding="utf-8")
    assert 'id="lifeProviderToken"' not in html
    assert "authorization_code" not in script
