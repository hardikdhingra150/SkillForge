import unittest
from types import SimpleNamespace
from unittest import mock

from app.services import skill_registry
from app.skills import BUILTIN_SKILLS

SKILL = BUILTIN_SKILLS[0]


def stored(**changes):
    row = dict(origin="builtin", status="validated", source_code=SKILL.source,
               implementation_hash=skill_registry.implementation_hash(SKILL.source, SKILL.contract),
               validation_json={"passed": True, "test_count": 4})
    return SimpleNamespace(**{**row, **changes})


class QuickRestartTests(unittest.TestCase):
    def test_an_identical_registered_skill_is_not_tested_again(self):
        db = mock.Mock()
        db.get.return_value = stored()
        with mock.patch.object(skill_registry, "run_fixture_tests") as tests:
            evidence = skill_registry.register_builtin(db, SKILL)
        tests.assert_not_called()
        db.execute.assert_not_called()
        self.assertIn("skipped", evidence)

    def test_changed_code_is_tested(self):
        db = mock.Mock()
        db.get.return_value = stored(implementation_hash="0" * 64)
        with mock.patch.object(skill_registry, "run_fixture_tests", side_effect=RuntimeError("ran")):
            with self.assertRaisesRegex(RuntimeError, "ran"):
                skill_registry.register_builtin(db, SKILL)
