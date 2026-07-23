from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "src" / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (ROOT / "src" / "web" / "backupRecovery.js").read_text(encoding="utf-8")


def test_backup_and_restore_controls_have_semantic_labels_and_live_status():
    for identifier in (
        "backupVerify",
        "backupExport",
        "restoreDryRun",
        "restoreStart",
        "restoreCancel",
        "recoveryCode",
    ):
        assert f'id="{identifier}"' in HTML
    assert 'for="recoveryCode"' in HTML
    assert HTML.count('role="status" aria-live="polite"') >= 2


def test_recovery_never_depends_on_voice_color_or_visual_qr():
    assert "Do not say it aloud" in HTML
    assert "trusted local device" in HTML
    assert "independently held signed checkpoint" in HTML
    assert "QR" not in HTML[HTML.index('id="backupRecoveryControls"'):HTML.index('id="remoteAssistantControls"')]


def test_failure_cancel_and_resume_are_explicit_and_clear_secret_input():
    assert "No backup was deleted or replaced" in SCRIPT
    assert "Restore paused and recovery code cleared" in SCRIPT
    assert "safely resume later" in SCRIPT
    assert 'recoveryCode.value = ""' in SCRIPT


def test_admin_and_provider_limits_are_explained_without_private_values():
    assert "cannot read private backup content" in HTML
    assert "Provider-side physical deletion cannot be guaranteed" in HTML
    assert "storage provider" in HTML
    assert "household administrator" in HTML
