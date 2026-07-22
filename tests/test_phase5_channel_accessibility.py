from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "src" / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (ROOT / "src" / "web" / "remoteAssistant.js").read_text(encoding="utf-8")


def test_remote_channel_flow_has_labels_disclosure_status_and_cancel():
    for control in ("telegramAccountId", "telegramBotId", "telegramBotToken"):
        assert f'for="{control}"' in HTML
        assert f'id="{control}"' in HTML
    assert 'id="telegramOutcome" role="status" aria-live="polite"' in HTML
    assert 'id="telegramCancel"' in HTML
    assert "not end-to-end encrypted" in HTML
    assert "Do not send passwords" in HTML
    assert "trusted local device" in HTML


def test_remote_channel_script_has_denial_recovery_and_secret_cleanup():
    assert "No private record existence is revealed" in SCRIPT
    assert "Strong local authentication is required" in SCRIPT
    assert "BotFather" in SCRIPT
    assert 'byId("telegramBotToken").value = ""' in SCRIPT
    assert "No message was sent" in SCRIPT
