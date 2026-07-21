from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_decision_exposes_semantic_consequences_and_options():
    html = (ROOT / "src/web/index.html").read_text(encoding="utf-8")
    for phrase in ("<dl>", "Action", "Recipients", "Information used", "Consequence", "Can it be undone?", "Maximum cost", "Confirm this exact action", "Use less information", "Cancel"):
        assert phrase in html
    assert 'role="status"' in html and 'aria-live="polite"' in html


def test_text_speech_keyboard_and_reduced_motion_parity():
    html = (ROOT / "src/web/index.html").read_text(encoding="utf-8")
    js = (ROOT / "src/web/trustDecision.js").read_text(encoding="utf-8")
    assert "You can say" in html
    assert "type=\"button\"" in html
    assert "prefers-reduced-motion" in html
    assert ".focus()" in js
    assert "Nothing was sent" in js
