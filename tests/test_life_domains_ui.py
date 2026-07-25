from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_domain_experiences_expose_accessible_safety_and_attention_controls():
    html = (ROOT / "src/web/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/web/lifeDomains.js").read_text(encoding="utf-8")
    for identifier in ("householdAttentionRefresh", "healthTimelineRefresh", "financeAttentionRefresh",
                       "lifeAttentionRefresh", "lifeAttentionStatus"):
        assert f'id="{identifier}"' in html
    assert "never diagnose" not in html.lower()
    assert "does not diagnose" in html.lower()
    assert "move money" in html.lower() and "physical device" in html.lower()
    assert 'role="status" aria-live="polite"' in html
    assert "replaceChildren" in script


def test_sensitive_values_are_not_spoken_or_rendered_by_default():
    script = (ROOT / "src/web/lifeDomains.js").read_text(encoding="utf-8")
    assert "speechSynthesis" not in script
    assert "account_identifier" not in script
    assert "medication" not in script
