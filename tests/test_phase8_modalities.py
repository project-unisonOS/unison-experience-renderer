import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_modality_negotiation_preserves_actions_and_caption_fallback():
    module = (ROOT / "src/web/modalityNegotiation.js").as_uri()
    script = f"""
      import {{ negotiateModalities }} from {module!r};
      const result = negotiateModalities({{
        available: ["visual", "captions", "keyboard"],
        required: ["braille"],
        avoided: ["speech"]
      }});
      if (result.status !== "needs-fallback") process.exit(1);
      if (result.selected[0] !== "captions") process.exit(2);
      if (result.semanticActionsPreserved !== true) process.exit(3);
    """
    subprocess.run(["node", "--input-type=module", "-e", script], check=True)


def test_adaptive_surface_has_caption_keyboard_and_preference_controls():
    html = (ROOT / "src/web/index.html").read_text()
    app = (ROOT / "src/web/app.js").read_text()
    preferences = (ROOT / "src/web/preferences.js").read_text()
    assert 'id="liveCaption"' in html
    assert 'aria-live="polite"' in html
    assert 'id="cancelSpeechAction"' in html
    assert "applyAdaptivePreferences" in app
    assert "highContrast" in preferences
    assert "simplifiedLanguage" in preferences
    assert "requiredModalities" in preferences
