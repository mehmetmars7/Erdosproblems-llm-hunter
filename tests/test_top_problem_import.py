"""Keep imported research text exact and reject ambiguous or destructive imports."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.import_top_problem_attempts import extract_attempts, import_attempts, read_exact


PREAMBLE = (r'\documentclass[11pt]{article}' + '\n'
            r'\newcommand{\R}{\mathbb{R}}' + '\n'
            r'\newcommand{\sref}[2]{\hyperlink{source:#1:#2}{[S#2]}}' + '\n')


def section(rank, research=True):
    text = (f'% ================================================================\n'
            f'% problemId: problem.example-{rank}\n'
            f'% source releaseRank: {rank}; source releaseStatus: open\n'
            + r'\clearpage' + '\n'
            + rf'\section{{Example {rank}}}\label{{{rank}}}' + '\n'
            + r'\subsection{Definitions and mathematical statement}' + '\n'
            + r'A set $X\subseteq\R$ and its exact {nested} notation.' + '\n'
            + rf'\sref{{{rank}}}{{1}}' + '\n'
            + r'\subsection{Short English statement}' + '\n'
            + 'Does this hold?\n')
    if research:
        text += (r'\subsection{Research attempt}' + '\n\n'
                 + '% Preserve this comment, spacing, and citation.\n'
                 + 'A checked partial result — still unresolved.\n'
                 + r'\[ \forall x\in X,\quad x^2\ge 0. \]' + '\n')
    return (text + r'\subsection{Sources}' + '\n'
            + r'\begin{itemize}' + '\n'
            + r'\item[S1] An exact source title. \url{https://example.org/source}' + '\n'
            + r'\end{itemize}' + '\n\n')


def batch(*sections, preamble=PREAMBLE):
    return (preamble + r'\begin{document}' + '\n'
            + r'\section*{Front matter omitted from the attempt}' + '\n'
            + ''.join(sections) + r'\end{document}' + '\n')


class TopProblemImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.catalog = self.folder / 'top_problems'
        self.catalog.mkdir()
        for rank in range(1, 4):
            metadata = {'problemId': f'problem.example-{rank}', 'releaseRank': rank}
            (self.catalog / f'{rank}.tex').write_text(
                '% TOP_PROBLEM: ' + json.dumps(metadata) + '\n', encoding='utf-8')

    def source(self, content, name='batch.tex'):
        path = self.folder / name
        path.write_bytes(content.encode('utf-8'))
        return path

    def test_verbatim_preamble_and_complete_research_section_with_crlf(self):
        original_section = section(2).replace('\n', '\r\n')
        preamble = PREAMBLE.replace('\n', '\r\n')
        source = self.source(batch(section(1, research=False), original_section, preamble=preamble))
        original = source.read_bytes()
        created, unchanged = import_attempts([source], self.catalog)
        self.assertEqual(unchanged, [])
        self.assertEqual([path.name for path in created], ['2.tex'])
        result = read_exact(created[0])
        self.assertIn(preamble, result)
        self.assertIn(original_section, result)
        self.assertIn('% ATTEMPT_STATUS: unresolved\n', result)
        self.assertIn(r'\setcounter{section}{1}', result)
        self.assertNotIn('Front matter omitted', result)
        self.assertEqual(extract_attempts(result)[0].section, original_section)
        self.assertEqual(source.read_bytes(), original)
        self.assertFalse((self.catalog / 'GPT_6_Astra_Ultra' / '1.tex').exists())

    def test_repeat_import_with_different_wrapper_is_idempotent(self):
        source = self.source(batch(section(1)))
        created, _ = import_attempts([source], self.catalog)
        original = created[0].read_bytes()
        repeated = self.source(batch(section(1), preamble=PREAMBLE + '% New wrapper comment\n'), 'repeat.tex')
        new, unchanged = import_attempts([repeated, source], self.catalog)
        self.assertEqual(new, [])
        self.assertEqual(unchanged, created)
        self.assertEqual(created[0].read_bytes(), original)

    def test_indented_catalogue_markers_and_sections_are_preserved(self):
        indented = ''.join('\t' + line for line in section(3).splitlines(keepends=True))
        source = self.source(batch(indented))
        created, _ = import_attempts([source], self.catalog)
        self.assertEqual(extract_attempts(read_exact(created[0]))[0].section, indented)
        self.assertEqual(created[0].name, '3.tex')

    def test_changed_attempt_needs_a_new_version_and_keeps_previous_file(self):
        source = self.source(batch(section(1)))
        created, _ = import_attempts([source], self.catalog)
        original = created[0].read_bytes()
        changed = self.source(batch(section(1).replace('checked partial', 'different partial')), 'changed.tex')
        with self.assertRaisesRegex(ValueError, 'choose a new --version'):
            import_attempts([changed], self.catalog)
        self.assertEqual(created[0].read_bytes(), original)
        new, _ = import_attempts([changed], self.catalog, version=2)
        self.assertEqual(new[0].name, '1_v2.tex')
        self.assertIn('different partial', read_exact(new[0]))

    def test_late_identity_mismatch_creates_no_output(self):
        good = self.source(batch(section(1)))
        wrong = self.source(batch(section(2).replace('problem.example-2', 'problem.wrong')), 'wrong.tex')
        with self.assertRaisesRegex(ValueError, 'Identity mismatch'):
            import_attempts([good, wrong], self.catalog)
        self.assertFalse((self.catalog / 'GPT_6_Astra_Ultra').exists())

    def test_late_collision_creates_no_other_output(self):
        old = self.source(batch(section(2)), 'old.tex')
        existing, _ = import_attempts([old], self.catalog)
        original = existing[0].read_bytes()
        source = self.source(batch(section(1), section(2).replace('checked partial', 'changed partial')))
        with self.assertRaisesRegex(ValueError, 'Existing attempt differs'):
            import_attempts([source], self.catalog)
        self.assertFalse((existing[0].parent / '1.tex').exists())
        self.assertEqual(existing[0].read_bytes(), original)

    def test_conflicting_batches_fail_before_writing(self):
        first = self.source(batch(section(1)))
        second = self.source(batch(section(1).replace('checked partial', 'changed partial')), 'second.tex')
        with self.assertRaisesRegex(ValueError, 'Conflicting input sections'):
            import_attempts([first, second], self.catalog)
        self.assertFalse((self.catalog / 'GPT_6_Astra_Ultra').exists())

    def test_malformed_documents_and_sections_are_rejected(self):
        cases = [
            batch(section(1)).replace(r'\end{document}', ''),
            batch(section(1)).replace('source releaseRank: 1;', 'source releaseRank: wrong;'),
            batch(section(1)).replace(r'\label{1}', r'\label{2}'),
            batch(section(1)).replace('Definitions and mathematical statement', 'Missing definition'),
            batch(section(1)).replace(r'\sref{1}{1}', r'\sref{1}{9}'),
            batch(section(1, research=False)),
        ]
        for content in cases:
            with self.subTest(content=content), self.assertRaises(ValueError):
                extract_attempts(content)

    def test_model_and_version_cannot_change_destination_layout(self):
        source = self.source(batch(section(1)))
        for model in ['../elsewhere', '.', 'a/b']:
            with self.subTest(model=model), self.assertRaises(ValueError):
                import_attempts([source], self.catalog, model=model)
        for version in [0, -1, True]:
            with self.subTest(version=version), self.assertRaises(ValueError):
                import_attempts([source], self.catalog, version=version)


if __name__ == '__main__':
    unittest.main()
