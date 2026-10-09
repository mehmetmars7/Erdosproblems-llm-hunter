"""Completion coverage for the fixed Economics batch selected on 2026-10-09."""

import json
import re
import unittest

from build_site import extract_completion
from scripts.economics_catalog import BASE_DIR, load_registry


class EconomicsCompletionSectionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initial ranks mint permanent IDs. A later rerank must retain this
        # batch's estimates rather than transfer them to different problems.
        cls.ids = {record['id'] for record in load_registry()['problems']
                   if 201 <= record['initial_rank'] <= 657}
        cls.sources = []
        for path in sorted((BASE_DIR / 'attacks/open_problems/economics').glob('*/*.tex')):
            if path.parent.name in {'statements', 'definitions'}:
                continue
            match = re.fullmatch(r'([A-Z]\d{2}-\d+)(?:_v\d+)?\.tex', path.name)
            if match and match[1] in cls.ids:
                cls.sources.append((match[1], path, path.read_text(encoding='utf-8')))

    @staticmethod
    def stated_estimate(content):
        sections = list(re.finditer(r'\\section\*?\s*\{Completion Estimate\}', content))
        if len(sections) != 1:
            raise AssertionError('Expected one Completion Estimate section')
        section = sections[0]
        first_line = content[section.end():].lstrip('\r\n').splitlines()[0].strip()
        value = re.fullmatch(r'(-?\d+(?:\.\d+)?)\\%', first_line)
        if not value:
            raise AssertionError('Expected a percentage immediately below the section')
        return section.start(), float(value[1])

    def test_each_attempt_has_a_valid_extractable_estimate_before_references(self):
        self.assertEqual({problem_id for problem_id, _, _ in self.sources}, self.ids)
        bibliography = re.compile(r'\\begin\{thebibliography\}|\\(?:bibliography|printbibliography)\b')
        heading = re.compile(r'\\(?:section|subsection|subsubsection)\*?\s*\{([^}\n]*)\}')
        for _, path, content in self.sources:
            with self.subTest(path=path.relative_to(BASE_DIR)):
                section, value = self.stated_estimate(content)
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, 100)
                self.assertEqual(extract_completion(content), value)
                references = [match.start() for match in bibliography.finditer(content)]
                if not references:
                    last_heading = list(heading.finditer(content))[-1]
                    # Scientific reference populations and reference games
                    # can occur earlier; only the terminal source block is
                    # a bibliographic heading.
                    if re.search(r'\b(?:references?|sources?|bibliography)\b',
                                 last_heading[1], re.IGNORECASE):
                        references.append(last_heading.start())
                if references:
                    self.assertLess(section, min(references))
                else:
                    # Some writeups cite their final source paragraph without
                    # a bibliography or reference heading.
                    self.assertGreater(content.rfind(r'\url{'), section)

    def test_published_estimates_and_downloads_match_the_tex_sources(self):
        text = (BASE_DIR / 'docs/data/economics_data.js').read_text(encoding='utf-8')
        published = json.loads(text.split('window.ECONOMICS_DATA = ', 1)[1].split(';\n', 1)[0])
        expected = {}
        for problem_id, path, content in self.sources:
            with self.subTest(path=path.relative_to(BASE_DIR)):
                _, value = self.stated_estimate(content)
                expected[problem_id] = max(expected.get(problem_id, 0), value)
                attack = next(attack for attack in published[problem_id]['attacks']
                              if attack['file_path'] == path.relative_to(BASE_DIR).as_posix())
                self.assertEqual(attack['completion'], value)
                self.assertEqual((BASE_DIR / 'docs' / attack['download_url']).read_bytes(),
                                 path.read_bytes())
        for problem_id, value in expected.items():
            with self.subTest(problem_id=problem_id):
                # The existing Erdos-style rule gives solved LLM claims
                # full completion, independently of the source estimates.
                solved = published[problem_id]['llm_status'] == 'solved'
                self.assertEqual(published[problem_id]['completion'], 100 if solved else value)
                self.assertEqual(published[problem_id]['completion_source'],
                                 'llm_claim' if solved else 'llm')


if __name__ == '__main__':
    unittest.main()
