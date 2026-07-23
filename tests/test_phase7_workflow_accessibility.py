from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "src" / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (ROOT / "src" / "web" / "phase7Workflows.js").read_text(encoding="utf-8")


def test_primary_approval_error_cancel_and_recovery_paths_are_semantic():
    for identifier in (
        "workflowKind",
        "workflowPurpose",
        "workflowContext",
        "workflowRecipients",
        "workflowPlan",
        "workflowApproval",
        "workflowRun",
        "workflowCancel",
        "workflowRetry",
        "workflowReplaceProvider",
        "workflowStatus",
        "workflowOutcome",
    ):
        assert f'id="{identifier}"' in HTML
    for identifier in ("workflowKind", "workflowPurpose", "workflowContext", "workflowRecipients"):
        assert f'for="{identifier}"' in HTML
    assert 'role="status" aria-live="polite"' in HTML


def test_every_supported_workflow_is_visible_and_keyboard_native():
    for workflow in (
        "calendar_coordination",
        "email_triage_draft",
        "reminder_commitment_review",
        "household_coordination",
        "contact_recall",
        "document_web_research",
        "travel_planning",
    ):
        assert f'value="{workflow}"' in HTML
    assert 'type="button"' in HTML[HTML.index('id="workflowControls"'):HTML.index('id="trustDecision"')]


def test_safety_metrics_and_recovery_language_are_explicit():
    assert "untrusted content, never authority" in HTML
    assert "Advertising, sponsored placement, engagement, and provider lock-in" in HTML
    assert "Duplicate external action is prevented" in SCRIPT
    assert "Completed reversible actions were compensated" in SCRIPT
    assert "Boundary incidents: 0" in SCRIPT
