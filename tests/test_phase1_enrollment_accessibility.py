from pathlib import Path


WEB = Path(__file__).resolve().parents[1] / "src" / "web"


def test_first_person_enrollment_has_labels_status_confirmation_and_cancel():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for control in (
        "bootstrapDisplayName",
        "bootstrapHousehold",
        "bootstrapUser",
        "bootstrapEmail",
        "bootstrapPassword",
        "bootstrapToken",
    ):
        assert f'for="{control}"' in html
        assert f'id="{control}"' in html
    assert 'id="actionNote"' in html and 'role="status"' in html
    assert 'id="bootstrapConfirmed"' in html
    assert 'id="bootstrapCancel"' in html
    assert "voice alone is never accepted" in html
    for control in ("loginHandle", "loginPassword"):
        assert f'for="{control}"' in html
        assert f'id="{control}"' in html
    for action in ("loginAction", "logoutAction", "lockAction", "recoveryAction", "recoveryCancel"):
        assert f'id="{action}"' in html
    assert "Voice alone cannot recover or unlock" in html


def test_enrollment_script_exposes_semantic_cancellation_and_recovery_status():
    script = (WEB / "app.js").read_text(encoding="utf-8")
    assert "Enrollment cancelled. No identity was created." in script
    assert "explicit confirmation are required" in script
    assert "Sign in to continue setup" in script
    assert "This session was revoked." in script
    assert "Your assistant is locked and its sessions are revoked." in script
    assert "Recovery cancelled. No account change was made." in script
