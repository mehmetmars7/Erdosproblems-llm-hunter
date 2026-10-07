"""Retrieval/parser edge cases; no OpenAI source files or extra deps needed."""
import importlib.util
from pathlib import Path
import unittest
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inventory = load_script("openai_inventory", "inventory_openai_math.py")
candidates = load_script("openai_candidates", "match_openai_math_candidates.py")


class InventoryParserTests(unittest.TestCase):
    def test_parentheses_folder_and_nested_label_preserve_full_path(self):
        links = inventory.markdown_links(
            "&emsp;[Sharp [integral] fillings in CAT(0)]"
            "(preprints/Sharp-integral-fillings-in-CAT(0)-spaces-September-23-2026/paper.pdf)"
        )
        self.assertEqual(links, [
            ("Sharp [integral] fillings in CAT(0)",
             "preprints/Sharp-integral-fillings-in-CAT(0)-spaces-September-23-2026/paper.pdf")
        ])

    def test_unbalanced_link_fails_instead_of_truncating_path(self):
        with self.assertRaisesRegex(ValueError, "Unbalanced"):
            inventory.markdown_links("[Paper](preprints/CAT(0)/paper.pdf")

    def test_custom_pdf_name_and_escaped_parentheses(self):
        self.assertEqual(
            inventory.markdown_links(r"[Paper](preprints/CAT\(0\)/exact-bsd-low-selmer-corank.pdf)")[0][1],
            "preprints/CAT(0)/exact-bsd-low-selmer-corank.pdf",
        )

    def test_nested_tex_braces_do_not_cut_summary(self):
        source = r"{for $\mathbb{Q}$ and \textbf{all {fields}}}{next}"
        first, offset = inventory.braced(source, 0)
        second, _ = inventory.braced(source, offset)
        self.assertEqual(first, r"for $\mathbb{Q}$ and \textbf{all {fields}}")
        self.assertEqual(second, "next")

    def test_both_date_suffix_formats(self):
        self.assertEqual(inventory.date_from_dir("A-paper-September-3-2026"), "2026-09-03")
        self.assertEqual(inventory.date_from_dir("Tangent-flow-uniqueness-2026-09-24"), "2026-09-24")

    def test_citation_title_does_not_use_index_disambiguation(self):
        readme = '# [Index alias](paper2.pdf)\n\ntitle = {{The Quasi-Riemann Hypothesis}},\n'
        self.assertEqual(inventory.manuscript_title(readme), 'The Quasi-Riemann Hypothesis')

    def test_citation_math_is_plain_metadata_and_subtitles_are_retained(self):
        readme = r'title = {{An $L^3$ bound: a construction over $\mathbb{C}^4$}},'
        self.assertEqual(inventory.manuscript_title(readme), 'An L³ bound: a construction over ℂ⁴')

    def test_relative_scope_links_resolve_at_checkout_root(self):
        self.assertEqual(
            inventory.repo_path("../../preprints/Paper/paper.pdf", "lean/docs"),
            "preprints/Paper/paper.pdf",
        )
        self.assertEqual(
            inventory.repo_path("../ComparatorChallenges/Test.lean", "lean/docs"),
            "lean/ComparatorChallenges/Test.lean",
        )
        with self.assertRaises(ValueError):
            inventory.repo_path("../../../outside", "lean/docs")


class CandidateNormalisationTests(unittest.TestCase):
    def test_diacritic_dash_and_conjunction_equivalence(self):
        expected = "erdos gallai"
        for text in ("Erdős–Gallai", "Erdos-Gallai", "Erdős and Gallai"):
            self.assertEqual(candidates.normalise(text), expected)

    def test_neighbourhood_and_possessives_agree(self):
        self.assertEqual(
            candidates.normalise("Seymour’s Second-Neighborhood Conjecture"),
            candidates.normalise("Seymour's Second Neighbourhood Conjecture"),
        )

    def test_exact_eponym_hits_preserve_named_targets(self):
        self.assertIn("kaplansky", candidates.eponyms("Kaplansky's Direct Finiteness Conjecture"))
        self.assertIn("erdos gallai", candidates.eponyms("Erdős–Gallai Conjecture"))
        self.assertNotIn("linear", candidates.eponyms("Linear Conjecture"))

    def test_numbered_erdos_sources_include_bibliography_but_ignore_companions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "preprints/Paper/build"
            (source / "companions").mkdir(parents=True)
            (source / "references.bib").write_text("url={https://www.erdosproblems.com/304}")
            (source / "intro.tex").write_text("See https://www.erdosproblems.com/293")
            (source / "companions/other.tex").write_text("https://www.erdosproblems.com/1150")
            self.assertEqual(candidates.source_erdos_references(root, "preprints/Paper/build"), {
                293: ["preprints/Paper/build/intro.tex"],
                304: ["preprints/Paper/build/references.bib"],
            })


if __name__ == "__main__":
    unittest.main()
