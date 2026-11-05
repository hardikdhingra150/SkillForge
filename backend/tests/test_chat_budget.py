import unittest

from fastapi import HTTPException

from app.api.chat import check_budget


class ChatBudgetTests(unittest.TestCase):
    def test_under_the_budget_is_allowed(self):
        self.assertIsNone(check_budget(199, 200))

    def test_at_the_budget_is_refused_with_429(self):
        with self.assertRaises(HTTPException) as caught:
            check_budget(200, 200)
        self.assertEqual(caught.exception.status_code, 429)
        self.assertIn("CHAT_TURNS_PER_DAY", caught.exception.detail)


if __name__ == "__main__":
    unittest.main()
