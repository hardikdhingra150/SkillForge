import unittest
from unittest import mock
from uuid import uuid4

from app.security import LOCAL_WORKSPACE_ID
from app.services.skill_registry import owner_for, shareable_change

CHANGE = {
    "strategy": "normalize_amounts", "summary": "Amounts like '$1,200.50' are export-formatted.",
    "request": "Total my private payroll", "diff": "--- a\n+++ b\n",
    "failure": {"code": "BAD_NUMBER", "message": "'$1,200.50' is not a plain number", "details": {"value": "$1,200.50"}},
    "fixtures": [{"name": "proof_amounts", "inputs": {}, "files": {}, "expected": "checks"},
                 {"name": "regression_input_for_v1.1.0", "inputs": {}, "files": {"sales": "c2VjcmV0"}, "expected": "checks"}],
}


class SharingTests(unittest.TestCase):
    def test_every_new_version_is_shared(self):
        self.assertIsNone(owner_for(uuid4()))
        self.assertIsNone(owner_for(LOCAL_WORKSPACE_ID))

    def test_a_visitors_data_is_removed_before_sharing(self):
        with mock.patch("app.security.settings.auth_mode", "browser"):
            clean = shareable_change(CHANGE, uuid4())
        text = repr(clean)
        for private in ("payroll", "1,200.50", "c2VjcmV0", "regression_input"):
            self.assertNotIn(private, text)
        self.assertEqual(clean["failure"], {"code": "BAD_NUMBER"})
        self.assertEqual([f["name"] for f in clean["fixtures"]], ["proof_amounts"])
        self.assertEqual((clean["strategy"], clean["diff"], clean["shared_from_visitor"]),
                         ("normalize_amounts", "--- a\n+++ b\n", True))

    def test_the_owners_records_stay_whole(self):
        with mock.patch("app.security.settings.auth_mode", "browser"):
            self.assertIs(shareable_change(CHANGE, LOCAL_WORKSPACE_ID), CHANGE)
        with mock.patch("app.security.settings.auth_mode", "off"):
            self.assertIs(shareable_change(CHANGE, uuid4()), CHANGE)
