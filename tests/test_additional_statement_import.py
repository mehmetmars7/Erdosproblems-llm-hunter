"""Check identity, preservation, and standalone meaning when importing statements."""

import hashlib
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from build_site import parse_numbered_problem_tex
from scripts.import_unsolvedmath_statements import apply_import, prepare_import


PREAMBLE = (r'\documentclass{article}' + '\n'
            r'\usepackage{amsmath,amssymb,hyperref}' + '\n'
            r'\newcommand{\N}{\mathbb{N}}' + '\n'
            r'\newcommand{\sref}[2]{\hyperlink{source:#1:#2}{[S#2]}}' + '\n'
            r'\newcommand{\cataloguescope}[1]{\paragraph{Recorded target.}#1}' + '\n')
NOTATION = (r'\textbf{Notation.} Unless a section says otherwise, '
            r'$\N=\{1,2,\ldots\}$ and $\log$ is the natural logarithm.')
TARGET = r'Is $\{n\in\N:n>2\}$ infinite?'


def record(problem_id, code, title, category_id, name, display):
    return {'id': problem_id, 'problem_number': code, 'title': title,
            'category_id': category_id,
            'category': {'id': category_id, 'name': name, 'display_name': display},
            'status': 'open', 'statement': TARGET,
            'external_url': f'https://www.unsolvedmath.com/problems/{code}',
            'legacy_ids': []}


def section(row, title=None):
    problem_id, code = row['id'], row['problem_number']
    display = row['category']['display_name']
    title = title or row['title']
    return (f'% UnsolvedMath ID {problem_id}; source catalogue code {code}\n'
            + rf'\setcounter{{section}}{{{problem_id - 1}}}' + '\n'
            + rf'\section{{{title}}}\label{{{problem_id}}}' + '\n'
            + rf'{{\small\sffamily UnsolvedMath ID {problem_id} · {display}}}' + '\n'
            + r'\subsection{Definitions and mathematical statement}' + '\n'
            + r'The set uses the shared convention for $\N$.' + '\n'
            + rf'\cataloguescope{{{TARGET} \sref{{{problem_id}}}{{1}}}}' + '\n'
            + r'\subsection{Short English statement}' + '\n'
            + 'Does the specified set contain infinitely many elements?\n'
            + r'\subsection{Sources}' + '\n'
            + r'{\small\begin{itemize}' + '\n'
            + rf'\item[\hypertarget{{source:{problem_id}:1}}{{[S1]}}] '
            + rf'ULAM.AI, supplied \texttt{{problems.json}}, record {problem_id} ({code}). '
            + r'\url{https://example.org/catalogue}.' + '\n'
            + r'\end{itemize}}' + '\n'
            + rf'\label{{end:{problem_id}}}' + '\n'
            + r'\clearpage' + '\n')


def batch(*parts):
    return (PREAMBLE + r'\begin{document}' + '\n'
            + r'\section*{Scope, sources, and conventions}' + '\n'
            + NOTATION + '\n\n'
            + r'\textbf{Attribution.} Supplied archive.' + '\n'
            + ''.join(parts) + r'\end{document}' + '\n')


def existing_document(row):
    """Use valid existing content that deliberately differs from the new batch."""
    return ('% TOP_PROBLEM: ' + json.dumps(row, ensure_ascii=False) + '\n'
            + PREAMBLE + r'\begin{document}' + '\n'
            + rf'\section{{{row["title"]}}}\label{{{row["id"]}}}' + '\n'
            + r'\subsection{Definitions and mathematical statement}' + '\n'
            + 'Previously curated statement; preserve this exact wording.\n'
            + r'\subsection{Short English statement}' + '\n'
            + 'The existing independent summary.\n'
            + r'\subsection{Sources}' + '\n'
            + r'\begin{itemize}' + '\n'
            + r'\item[S1] Existing source. \url{https://example.org/existing}' + '\n'
            + r'\end{itemize}' + '\n'
            + r'\end{document}' + '\n')


class AdditionalStatementImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.catalog = self.folder / 'top_problems'
        self.export = self.folder / 'portable'
        self.catalog.mkdir()
        self.export.mkdir()
        self.rows = {
            1: record(1, 'MPP-001', 'Existing one', 15, 'computer_science', 'Computer Science'),
            6: record(6, 'MPP-006', 'Existing six', 5, 'algebraic_geometry', 'Algebraic Geometry'),
            19: record(19, 'GEO-002', 'Canonical nineteen', 3, 'geometry', 'Geometry'),
            28: record(28, 'NT-009', 'Canonical twenty-eight', 1, 'number_theory', 'Number Theory'),
        }
        self.registry = self.folder / 'full_problems.json'
        self.registry.write_text(json.dumps(list(self.rows.values())), encoding='utf-8')
        self.portable = self.export / 'problems.json'
        self.order = self.export / 'display_order.json'
        self.portable.write_text(json.dumps([self.rows[6], self.rows[1]]), encoding='utf-8')
        self.order.write_text(json.dumps([6, 1]), encoding='utf-8')
        for problem_id in (1, 6):
            (self.catalog / f'{problem_id}.tex').write_text(
                existing_document(self.rows[problem_id]), encoding='utf-8')

    def source(self, *parts):
        path = self.folder / 'additional.tex'
        path.write_text(batch(*parts), encoding='utf-8')
        return path

    def prepare(self, source):
        return prepare_import(source, self.registry, self.catalog, self.export)

    def snapshot(self):
        return {str(path.relative_to(self.folder)): path.read_bytes()
                for path in self.folder.rglob('*') if path.is_file()}

    def test_late_identity_mismatches_abort_without_writes(self):
        valid = section(self.rows[28])
        mismatches = [
            (r'\label{28}', r'\label{29}'),
            (r'\label{end:28}', r'\label{end:29}'),
            (r'\setcounter{section}{27}', r'\setcounter{section}{28}'),
            ('source catalogue code NT-009', 'source catalogue code WRONG-009'),
            ('UnsolvedMath ID 28 · Number Theory', 'UnsolvedMath ID 29 · Number Theory'),
            ('UnsolvedMath ID 28 · Number Theory', 'UnsolvedMath ID 28 · Geometry'),
            ('record 28 (NT-009)', 'record 29 (NT-009)'),
        ]
        for before, after in mismatches:
            with self.subTest(mismatch=after):
                source = self.source(section(self.rows[19]), valid.replace(before, after))
                original = self.snapshot()
                with self.assertRaises(ValueError):
                    self.prepare(source)
                self.assertEqual(self.snapshot(), original)

    def test_existing_numeric_file_is_reported_and_never_replaced(self):
        source = self.source(section(self.rows[1], 'Different batch wording'), section(self.rows[19]))
        existing = self.catalog / '1.tex'
        original = existing.read_bytes()
        full_registry = self.registry.read_bytes()
        plan = self.prepare(source)
        self.assertEqual(set(plan['documents']), {19})
        self.assertEqual([item['id'] for item in plan['duplicates']], [1])
        self.assertTrue(plan['duplicates'][0]['title'])
        apply_import(plan)
        self.assertEqual(existing.read_bytes(), original)
        self.assertEqual(self.registry.read_bytes(), full_registry)
        self.assertTrue((self.catalog / '19.tex').is_file())

    def test_repeated_source_id_is_rejected_before_mutation(self):
        source = self.source(section(self.rows[19]), section(self.rows[19]))
        original = self.snapshot()
        with self.assertRaises(ValueError):
            self.prepare(source)
        self.assertEqual(self.snapshot(), original)

    def test_standalone_target_shared_notation_and_source_link_survive_parser(self):
        source = self.source(section(self.rows[19], 'A paraphrased section title'))
        original = self.snapshot()
        plan = self.prepare(source)
        self.assertEqual(self.snapshot(), original)
        document = plan['documents'][19]
        self.assertIn(PREAMBLE, document)
        self.assertIn(TARGET, document)
        self.assertIn(NOTATION.split(r'\textbf{Notation.} ', 1)[1], document)
        self.assertIn(r'\label{19}', document)
        self.assertNotIn(r'\label{28}', document)
        parsed = parse_numbered_problem_tex(document, require_source_urls=False)
        self.assertIn('Is $', parsed['definitionTeX'])
        self.assertIn('n>2', parsed['definitionTeX'])
        self.assertIn('natural logarithm', parsed['definitionTeX'])
        self.assertIn(r'\mathbb{N}', parsed['definitionTeX'])
        self.assertIn(r'\href{https://example.org/catalogue}{[S1]}', parsed['definitionTeX'])
        self.assertEqual(len(parsed['sources']), 1)
        self.assertEqual(parsed['sources'][0]['url'], 'https://example.org/catalogue')
        self.assertEqual(plan['source_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())

    def test_second_import_has_no_new_files_and_keeps_existing_documents(self):
        source = self.source(section(self.rows[19]), section(self.rows[28]))
        apply_import(self.prepare(source))
        first = self.snapshot()
        repeated = self.prepare(source)
        self.assertEqual(repeated['documents'], {})
        self.assertEqual({item['id'] for item in repeated['duplicates']}, {19, 28})
        apply_import(repeated)
        self.assertEqual(self.snapshot(), first)

    def test_canonical_metadata_is_retained_without_renumbering_display_order(self):
        source = self.source(section(self.rows[28], 'Paraphrase twenty-eight'),
                             section(self.rows[19], 'Paraphrase nineteen'))
        original_registry = self.registry.read_bytes()
        plan = self.prepare(source)
        self.assertEqual(plan['order'], [6, 1, 28, 19])
        by_id = {row['id']: row for row in plan['records']}
        self.assertEqual(set(by_id), {1, 6, 19, 28})
        for problem_id in (19, 28):
            for key in ('id', 'title', 'problem_number', 'category_id', 'category'):
                self.assertEqual(by_id[problem_id][key], self.rows[problem_id][key])
            header = re.search(r'^% TOP_PROBLEM: (.+)$', plan['documents'][problem_id], re.MULTILINE)
            self.assertIsNotNone(header)
            metadata = json.loads(header[1])
            self.assertEqual(metadata['id'], problem_id)
            self.assertEqual(metadata['category'], self.rows[problem_id]['category'])
        apply_import(plan)
        self.assertEqual(json.loads(self.order.read_text()), [6, 1, 28, 19])
        self.assertEqual(self.registry.read_bytes(), original_registry)


if __name__ == '__main__':
    unittest.main()
