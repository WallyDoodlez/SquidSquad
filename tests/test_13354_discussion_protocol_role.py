"""Regression test for #13354 — the composed verifier Discussion Protocol
taught a deprecated `--role qa` form. `_canonicalize_role` in tracker.py
(#6274 D11) treats bare `qa`/`qa-lead` as deprecated input and prints:
"WARNING: --role 'qa' is deprecated and will be rejected after #6274.3
cutover. Use 'verifier' instead." — hit live on the #13335 rejection
transition. `roles/verifier/verification.md` already prescribes
`verifier-lead`; `roles/verifier/discussion-protocol.md` disagreed, teaching
every composed verifier instruction a command that will hard-fail once the
#6274.3 cutover lands.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DISCUSSION_PROTOCOL_FILE = (
    REPO_ROOT / "references" / "sub-skills" / "roles" / "verifier"
    / "discussion-protocol.md"
)


@pytest.fixture
def discussion_protocol_text():
    assert DISCUSSION_PROTOCOL_FILE.exists(), (
        f"verifier discussion-protocol.md missing: {DISCUSSION_PROTOCOL_FILE}"
    )
    return DISCUSSION_PROTOCOL_FILE.read_text(encoding="utf-8")


class TestVerifierDiscussionProtocolRole:
    def test_uses_verifier_lead(self, discussion_protocol_text):
        assert (
            '--role "verifier-lead ($(python references/scripts/config.py '
            'alias qa))"'
        ) in discussion_protocol_text, (
            "must teach the class-based verifier-lead form, matching "
            "verification.md's existing --role verifier-lead usage"
        )

    def test_deprecated_bare_qa_role_gone(self, discussion_protocol_text):
        assert '--role "qa (' not in discussion_protocol_text, (
            "the deprecated bare 'qa' --role prefix must not appear — it "
            "warns today (#6274 D11 dual-aware) and will be a hard reject "
            "after the #6274.3 cutover"
        )

    def test_config_alias_lookup_key_unchanged(self, discussion_protocol_text):
        """config.py alias qa is a config.md lookup key (## Aliases ->
        alias-qa), NOT a tracker --role value — no alias-verifier entry
        exists in config.py's FIELD_MAP, so this part must stay 'qa'."""
        assert "config.py alias qa" in discussion_protocol_text


class TestDeprecatedRoleFormStillMatchesTrackerWarning:
    """Confirms the fixed role string actually avoids tracker.py's live
    #6274 D11 deprecation warning (the bug's original symptom)."""

    def test_verifier_lead_is_not_flagged_deprecated(self):
        import sys

        sys.path.insert(
            0, str(REPO_ROOT / "references" / "scripts")
        )
        import tracker

        # bare "qa" IS the deprecated form tracker.py warns on.
        assert tracker._DUAL_ROLE_PREFIXES_6274.get("qa") == ("qa", True)
        # "verifier" is the new, non-deprecated form.
        assert tracker._DUAL_ROLE_PREFIXES_6274.get("verifier") == ("qa", False)
