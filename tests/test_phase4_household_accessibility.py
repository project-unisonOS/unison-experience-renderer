from pathlib import Path


HTML = (Path(__file__).resolve().parents[1] / "src" / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (Path(__file__).resolve().parents[1] / "src" / "web" / "householdProof.js").read_text(encoding="utf-8")


def test_household_controls_have_semantic_labels_status_and_cancel_paths():
    for control in (
        "householdInvitationMinutes", "householdRemovePerson", "householdId",
        "householdSpaceId", "householdCalendarTitle", "householdCalendarStart",
        "householdCalendarEnd", "householdGroceryItem", "householdGroceryQuantity",
    ):
        assert f'for="{control}"' in HTML
        assert f'id="{control}"' in HTML
    assert 'id="householdOutcome" role="status" aria-live="polite"' in HTML
    assert 'id="householdCancel"' in HTML
    assert "cannot read another adult's private" in HTML


def test_household_script_exposes_denial_and_recovery_without_private_values():
    assert "No private record existence was revealed" in SCRIPT
    assert "Private audit events remain hidden" in SCRIPT
    assert "task content is not included" in SCRIPT.lower()
    assert "householdRecoveryReview" in SCRIPT
