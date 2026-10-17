import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/import_we_solve_links.py"
SPEC = importlib.util.spec_from_file_location("import_we_solve_links", SCRIPT)
importer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(importer)


class ImportWeSolveLinksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "erdos"
        self.site = self.base / "site"
        self.research = self.base / "research"
        self.statement = "attacks/open_problems/top_problems/definitions/3395.tex"
        self.attempt = "attacks/open_problems/top_problems/model/3395.tex"
        self.mo_attempt = "attacks/open_problems/mo/model/18264.tex"
        self.aliases = {
            "problems": {
                "TOP-1": {"id": "canonical", "path": "problems/canonical", "statement_revision_id": "stm1"},
                "TOP-3395": {"id": "original", "path": "problems/original", "statement_revision_id": "stm2"},
            },
            "contributions": {
                "TOP-3395-A7": {"id": "con1", "path": "problems/original/contributions/con1", "revision_id": "rev1"},
            },
        }
        self.write(self.root / self.statement, "Original statement\n")
        self.write(self.root / self.attempt, "% FIRST_POSTED: 2026-01-01\nManuscript\n")
        self.write(self.root / self.mo_attempt, "MO manuscript\n")
        self.write(self.research / "problems/original/statement.tex", "Original statement\n")
        self.exported = self.research / "problems/original/contributions/con1/files/3395.tex"
        self.write(self.exported, "Manuscript\n")
        self.write_json(self.research / "browse/aliases.json", self.aliases)
        self.write(self.root / "docs/data/erdos_data.js", "var erdosProblems = {};")
        self.write(self.root / "docs/data/mo_data.js", 'var moProblems = ' + json.dumps({
            "18264": {"attacks": [{"file_path": self.mo_attempt}]},
        }) + ";")
        self.write(self.root / "docs/data/economics_data.js", "window.ECONOMICS_DATA = [];")
        self.write(self.root / "docs/data/open_problems_data.js", "var openProblems = " + json.dumps({
            "3395": {"rank": 18, "definition_file": self.statement, "attacks": [{"file_path": self.attempt}]},
            "mo:18264": {"attacks": [{"file_path": self.mo_attempt}]},
        }) + ";")
        self.problem_api = {
            "alias": "TOP-3395", "canonical_alias": "TOP-1", "canonical_problem_id": "canonical",
            "number": 100001, "url": "/problems/p-versus-np/",
            "record": {"problem_id": "original", "statement_revision_id": "stm2", "statement_artifact": {"path": "statement.tex"}},
        }
        self.write(self.site / "problems/p-versus-np/index.html", "<h1>P versus NP</h1>")
        self.contribution = {
            "alias": "TOP-3395-A7", "revision": "r1", "url": "/contributions/p-versus-np/attempt-7/r1/",
            "record": {"contribution_id": "con1", "revision_id": "rev1",
                       "artifacts": [{"location": "in_repository", "role": "manuscript_source", "path": "files/3395.tex"}]},
        }
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "-qm", "Fixture"], check=True)
        self.original_revision = subprocess.check_output(["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True).strip()
        self.problem_api["record"]["sources"] = [{"snapshot": {
            "repository_url": "https://github.com/mehmetmars7/Erdosproblems-llm-hunter",
            "commit": self.original_revision, "path": "lists/problems.json"}}]
        self.write_json(self.site / "api/v1/problems/TOP-3395.json", self.problem_api)
        self.write_json(self.site / "api/v1/problems/WS-100007.json", self.problem_api)
        canonical_api = json.loads(json.dumps(self.problem_api))
        canonical_api["alias"] = "TOP-1"
        canonical_api["record"].update(problem_id="canonical", statement_revision_id="stm1")
        self.write_json(self.site / "api/v1/problems/WS-100001.json", canonical_api)
        self.write_contribution(self.contribution)

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    def write_json(self, path, value):
        self.write(path, json.dumps(value))

    def write_contribution(self, record):
        self.write_json(self.site / "api/v1/contributions" / record["alias"] / "r1.json", record)
        self.write(self.site / record["url"].strip("/") / "index.html",
                   '<a href="https://github.com/mehmetmars7/Erdosproblems-llm-hunter/blob/main/other.tex">Citation</a>'
                   f'<a href="https://github.com/mehmetmars7/Erdosproblems-llm-hunter/blob/{self.original_revision}/{self.attempt}">Original source</a>')

    def build(self):
        return importer.build_manifest(self.root, self.site, self.research)

    def test_merged_identity_keeps_original_statement_and_exact_attempt(self):
        manifest = self.build()
        problem = manifest["problems"]["open_problems:3395"]
        self.assertEqual(problem["code"], "WS-100001")
        self.assertEqual(problem["record_code"], "WS-100007")
        self.assertEqual(problem["problem_id"], "original")
        self.assertEqual(problem["canonical_problem_id"], "canonical")
        self.assertEqual(problem["canonical_alias"], "TOP-1")
        self.assertEqual(problem["alias"], "TOP-3395")
        self.assertEqual(problem["url"], "https://we-solve.github.io/problems/p-versus-np/")
        self.assertTrue(problem["source_url"].endswith("problems/original/statement.tex"))
        attempt = manifest["sources"][self.attempt]
        self.assertEqual(attempt["alias"], "TOP-3395-A7")
        self.assertTrue(attempt["url"].endswith("attempt-7/r1/"))
        self.assertNotEqual(attempt["local_sha256"], attempt["exported_sha256"])
        self.assertNotIn("other.tex", manifest["sources"])

    def test_missing_mathoverflow_is_explicit_and_not_guessed(self):
        manifest = self.build()
        self.assertEqual(manifest["audit"]["unmapped_problems"], ["mo:18264"])
        self.assertEqual(manifest["audit"]["unmapped_sources"], [self.mo_attempt])
        self.assertNotIn("mo:18264", manifest["problems"])

    def test_missing_export_preserves_revision_link_but_omits_source_redirect(self):
        self.exported.unlink()
        manifest = self.build()
        self.assertNotIn("source_url", manifest["sources"][self.attempt])
        self.assertIn("url", manifest["sources"][self.attempt])
        self.assertIn(self.attempt, manifest["audit"]["unavailable_source_files"])

    def test_ambiguous_original_path_is_rejected(self):
        self.aliases["contributions"]["TOP-3395-A8"] = {
            "id": "con2", "path": "problems/original/contributions/con2", "revision_id": "rev2"}
        self.write_json(self.research / "browse/aliases.json", self.aliases)
        other = json.loads(json.dumps(self.contribution))
        other.update(alias="TOP-3395-A8", url="/contributions/p-versus-np/attempt-8/r1/")
        other["record"].update(contribution_id="con2", revision_id="rev2")
        self.write_contribution(other)
        with self.assertRaisesRegex(importer.MappingError, "Ambiguous Original source"):
            self.build()

    def test_record_identity_mismatch_is_rejected(self):
        self.contribution["record"]["contribution_id"] = "wrong"
        self.write_contribution(self.contribution)
        with self.assertRaisesRegex(importer.MappingError, "Contribution identity mismatch"):
            self.build()

    def test_unsafe_original_source_is_rejected(self):
        with self.assertRaises(importer.MappingError):
            importer.original_paths('<a href="https://github.com/mehmetmars7/Erdosproblems-llm-hunter/blob/main/%2e%2e/private">Original source</a>')

    def test_output_is_deterministic(self):
        self.assertEqual(self.build(), self.build())

    def test_ranking_changes_do_not_change_any_identity_or_destination(self):
        initial = self.build()
        path = self.root / "docs/data/open_problems_data.js"
        self.write(path, path.read_text().replace('"rank": 18', '"rank": 9999'))
        self.assertEqual(initial, self.build())

    def test_existing_permanent_binding_cannot_change_on_reimport(self):
        previous = self.build()
        previous["problems"]["open_problems:3395"]["record_code"] = "WS-100999"
        self.write_json(self.root / "lists/we_solve_links.json", previous)
        with self.assertRaisesRegex(importer.MappingError, "Permanent problem binding changed"):
            self.build()

    def test_duplicate_permanent_codes_for_record_are_rejected(self):
        self.write_json(self.site / "api/v1/problems/WS-100999.json", self.problem_api)
        with self.assertRaisesRegex(importer.MappingError, "Multiple permanent codes"):
            self.build()

    def test_canonical_change_needs_opt_in_and_published_merge_evidence(self):
        previous = {"problems": {"open_problems:3395": {
            "alias": "TOP-3395", "record_code": "WS-100007", "problem_id": "original",
            "code": "WS-100007", "canonical_problem_id": "original", "canonical_alias": "TOP-3395"}}}
        current = self.build()["problems"]
        evidence = {"WS-100007": self.problem_api}
        with self.assertRaisesRegex(importer.MappingError, "Canonical problem binding changed"):
            importer.validate_existing_bindings(previous, current, evidence, False)
        importer.validate_existing_bindings(previous, current, evidence, True)
        with self.assertRaisesRegex(importer.MappingError, "Canonical problem binding changed"):
            importer.validate_existing_bindings(previous, current, {}, True)

    def test_changed_local_content_cannot_be_blessed_by_refreshing_manifest(self):
        self.write(self.root / self.attempt, "A newer manuscript\n")
        self.write(self.root / self.statement, "A newer statement\n")
        manifest = self.build()
        self.assertNotIn(self.attempt, manifest["sources"])
        self.assertNotIn("source_url", manifest["problems"]["open_problems:3395"])
        self.assertEqual(set(manifest["audit"]["stale_source_files"]), {self.statement, self.attempt})

    def test_unknown_pinned_git_object_is_not_guessed(self):
        self.original_revision = "0" * 40
        self.write_contribution(self.contribution)
        manifest = self.build()
        self.assertNotIn(self.attempt, manifest["sources"])
        self.assertIn(self.attempt, manifest["audit"]["unverified_source_files"])


if __name__ == "__main__":
    unittest.main()
