"""Exercise issue-to-review writes for ranked problems and legacy collections."""

import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import update_review_from_issue as reviews


class OpenProblemReviewTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.lists = self.root / "lists"
        self.output = self.root / "reviews"
        self.lists.mkdir()
        self.definitions = self.root / "attacks/open_problems/top_problems"
        self.definitions.mkdir(parents=True)
        for number, problem_id in enumerate([1, 20000601], 1):
            (self.definitions / f"{number}.tex").write_text(
                '% TOP_PROBLEM: ' + json.dumps({"id": problem_id}) + '\n', encoding="utf-8")
        (self.lists / "erdos_problems.csv").write_text("number\n665\n", encoding="utf-8")
        (self.lists / "erdos_status.json").write_text(
            json.dumps({"problems": {"665": {}, "1221": {}}}), encoding="utf-8")
        (self.lists / "mo_problems.csv").write_text("question_id\n123\n", encoding="utf-8")
        for name, value in [("LISTS_DIR", self.lists), ("REVIEWS_DIR", self.output), ("TOP_PROBLEMS_DIR", self.definitions)]:
            patcher = patch.object(reviews, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def submit(self, problem_type="Open Problems", problem_id="1",
               verdict="partial", citations="", explanation="The restricted case follows; the general case remains open."):
        fields = {
            "Problem type": problem_type,
            "Problem ID": problem_id,
            "Verdict": verdict,
            "Explanation": explanation,
            "Citation links (required for accepted)": citations,
        }
        body = "\n\n".join(f"### {label}\n\n{value}" for label, value in fields.items())
        with patch.dict("os.environ", {
            "ISSUE_BODY": body, "ISSUE_NUMBER": "42", "ISSUE_AUTHOR": "author",
            "REVIEW_LABELER": "reviewer", "ISSUE_URL": "https://example.org/issues/42",
            "ISSUE_CREATED_AT": "2026-09-24T10:00:00Z",
        }, clear=True), contextlib.redirect_stdout(io.StringIO()):
            reviews.main()

    def test_ranked_review_written_with_stable_id_and_issue_attribution(self):
        self.submit()
        saved = json.loads((self.output / "open_problems/1.json").read_text())
        self.assertEqual(saved["status"], "partial")
        self.assertEqual(saved["reviewed_by"], "reviewer")
        self.assertEqual(saved["reviewed_at"], "2026-09-24")
        self.assertEqual(saved["issue_number"], "42")

    def test_sparse_canonical_ids_and_normalized_type_are_supported(self):
        self.submit(problem_type="open_problems", problem_id="20000601")
        self.assertTrue((self.output / "open_problems/20000601.json").is_file())

    def test_legacy_review_paths_and_combined_listing_mo_ids(self):
        for problem_type, problem_id, expected in [
            ("Erdos", "665", "erdos/665.json"),
            ("MO", "123", "mo/123.json"),
            ("Open Problems", "mo:123", "mo/123.json"),
        ]:
            with self.subTest(problem_type=problem_type):
                self.submit(problem_type=problem_type, problem_id=problem_id)
                self.assertTrue((self.output / expected).is_file())

    def test_unknown_or_historical_ids_are_not_published_reviews(self):
        for problem_id in ["20000602", "999", "mo:456"]:
            with self.subTest(problem_id=problem_id), self.assertRaisesRegex(SystemExit, "not found"):
                self.submit(problem_id=problem_id)
        self.assertFalse(self.output.exists())

    def test_erdos_review_accepts_published_snapshot_ids_missing_from_old_csv(self):
        self.submit(problem_type="Erdos", problem_id="1221")
        self.assertTrue((self.output / "erdos/1221.json").is_file())
        with self.assertRaisesRegex(SystemExit, "not found"):
            self.submit(problem_type="Erdos", problem_id="1222")

    def test_unsafe_ids_are_rejected_even_if_the_catalog_contains_them(self):
        for problem_id in ["../../outside", "problem../outside", "problem.bad\\path",
                           "/tmp/outside", "1\nignored", "problem..dots"]:
            with self.subTest(problem_id=problem_id), \
                    patch.object(reviews, "load_problem_ids", return_value={problem_id}), \
                    self.assertRaisesRegex(SystemExit, "Invalid problem id"):
                self.submit(problem_id=problem_id)
        self.assertFalse(self.output.exists())

    def test_unsupported_collection_cannot_become_a_directory(self):
        with self.assertRaisesRegex(SystemExit, "Unknown problem type"):
            self.submit(problem_type="../outside")
        self.assertFalse(self.output.exists())

    def test_accepted_review_requires_citation_and_substantial_explanation(self):
        with self.assertRaisesRegex(SystemExit, "citation link"):
            self.submit(verdict="accepted")
        with self.assertRaisesRegex(SystemExit, "20\\+ characters"):
            self.submit(verdict="accepted", citations="https://example.org/proof", explanation="Checked.")
        self.assertFalse(self.output.exists())
        self.submit(verdict="accepted", citations="https://example.org/proof")
        saved = json.loads((self.output / "open_problems/1.json").read_text())
        self.assertEqual(saved["citations"], ["https://example.org/proof"])


if __name__ == "__main__":
    unittest.main()
