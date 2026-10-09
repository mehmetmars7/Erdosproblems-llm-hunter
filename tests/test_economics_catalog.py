"""Protect Economics coverage, exact source matching and permanent identity."""

import csv
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.economics_catalog import (BASE_DIR, REGISTRY_PATH, RANKINGS_PATH,
                                      build_economics_data, extract_statement,
                                      generate_economics_data, load_registry,
                                      read_ranking_csv)
from scripts.import_economics import import_economics, parse_source
from scripts.update_economics_ranks import update_economics_ranks


def source_fixture():
    first = (r'\section*{Source mathematical conventions}' + '\nAtlas context.\n'
             + '% MERGED_PROBLEM: {"id":"OP-0010","source":"atlas","jel":"C73"}\n'
             + r'\section{First problem}' + '\n'
             + r'\ProblemClassification{OP-0010}{C73}{Atlas}{M1}' + '\n'
             + r'\label{C73}\label{problem:OP-0010}\label{difficulty-rank:3}' + '\n'
             + r'\subsection*{Definitions and assumptions}' + '\n'
             + r'Preserved $x\in\R$ and {nested {braces}}.' + '\n'
             + r'\subsection*{References}' + '\nFirst exact source.\n')
    second = (r'\section*{Source mathematical conventions}' + '\nGame context.\n'
              + r'\section{Second problem}' + '\n'
              + r'\ProblemClassification{OP-0050}{C72}{Supplement}{Merged}' + '\n'
              + r'\label{C72}\label{problem:OP-0050}\label{difficulty-rank:1}' + '\n'
              + r'\subsection*{Definitions and assumptions}' + '\nSecond body.\n'
              + '% MERGED_PROBLEM: {"id":"OP-0050","source":"game","jel":"C72"}\n'
              + r'\section{Third problem}' + '\n'
              + r'\ProblemClassification{OP-0050}{C72}{Game theory}{GT-2}' + '\n'
              + r'\label{C72}\label{problem:OP-0050}\label{difficulty-rank:2}' + '\n'
              + r'\subsection*{Definitions and assumptions}' + '\nThird body.\n')
    trailing_contexts = ''.join(
        r'\section*{' + title + '}\n' + text + '\n'
        for title, text in [
            ('Source mathematical conventions', 'Definition context.'),
            ('Source mathematical conventions', 'Beyond context.'),
            ('BSDE conventions for SC-01--SC-06', 'BSDE context.'),
            ('Control and stopping conventions for SC-07--SC-08', 'Control context.'),
            ('Additional-source status and mathematical conventions', 'Audited context.'),
        ])
    return (r'\documentclass{article}' + '\n' + r'\begin{document}' + '\n'
            + first + second + trailing_contexts + r'\appendix' + '\n'
            + r'\section{Appendix excluded}' + '\n' + r'\end{document}' + '\n')


def csv_text(rows):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['New rank', 'Problem title', 'JEL code', 'Problem ID'])
    writer.writerows(rows)
    return stream.getvalue()


class EconomicsCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tex = self.root / 'source.tex'
        self.tex.write_text(source_fixture(), encoding='utf-8')
        self.csv = self.root / 'original.csv'
        self.csv.write_text(csv_text([
            [1, 'First problem', 'C73', 'OP-0010'],
            [2, 'Second problem', 'C72', 'OP-0050'],
            [3, 'Third problem', 'C72', 'OP-0050'],
        ]), encoding='utf-8')

    def imported(self):
        return import_economics(self.tex, self.csv, self.root)

    def write_ranks(self, text):
        path = self.root / 'revision.csv'
        path.write_text(text, encoding='utf-8')
        return path

    def test_actual_sections_not_missing_stale_or_duplicate_markers_own_identity(self):
        entries = parse_source(source_fixture())
        self.assertEqual(len(entries), 3)
        self.assertEqual([entry['source_id'] for entry in entries],
                         ['OP-0010', 'OP-0050', 'OP-0050'])
        self.assertEqual(entries[1]['source_metadata'], {})
        self.assertIn('Preserved $x\\in\\R$ and {nested {braces}}.', entries[0]['body'])
        self.assertIn('Atlas context.', entries[0]['body'])
        self.assertNotIn('Game context.', entries[0]['body'])
        self.assertIn('Game context.', entries[2]['body'])
        self.assertNotIn('Definition context.', entries[2]['body'])
        self.assertNotIn('difficulty-rank:', ''.join(entry['body'] for entry in entries))
        self.assertNotIn('Appendix excluded', ''.join(entry['body'] for entry in entries))

    def test_import_freezes_ids_and_creates_local_downloads_without_attempts(self):
        registry = self.imported()
        self.assertEqual([record['id'] for record in registry['problems']],
                         ['C73-1', 'C72-2', 'C72-3'])
        data = build_economics_data(self.root)
        for problem_id, record in data.items():
            self.assertEqual(record['attacks'], [])
            self.assertEqual(record['entry_kind'], 'statement_only')
            canonical = (self.root / record['definitionFile']).read_bytes()
            public = (self.root / 'docs' / record['statement_url']).read_bytes()
            self.assertEqual(canonical, public)
            self.assertEqual(record['definition_tex'], extract_statement(canonical.decode()))
        self.assertIn('window.ECONOMICS_DATA = ',
                      (self.root / 'docs/data/economics_data.js').read_text())

    def test_stale_source_comment_cannot_replace_authoritative_provenance(self):
        stale = source_fixture().replace('"id":"OP-0010"', '"id":"OP-0009"')
        entry = parse_source(stale)[0]
        self.assertEqual(entry['source_id'], 'OP-0010')
        self.assertEqual(entry['source_metadata'], {})
        self.assertEqual(entry['source_comment_metadata']['id'], 'OP-0009')

    def test_reimport_refuses_before_any_identity_or_statement_changes(self):
        self.imported()
        registry = (self.root / REGISTRY_PATH).read_bytes()
        with self.assertRaisesRegex(ValueError, 'permanent IDs cannot be regenerated'):
            import_economics(self.root / 'missing.tex', self.root / 'missing.csv', self.root)
        self.assertEqual((self.root / REGISTRY_PATH).read_bytes(), registry)

    def test_rerank_changes_order_and_preserves_registry_ids_and_statement_files(self):
        registry = self.imported()
        original_registry = (self.root / REGISTRY_PATH).read_bytes()
        files = {record['id']: (self.root / record['statement_file']).read_bytes()
                 for record in registry['problems']}
        revision = self.write_ranks('Problem ID,New rank\nC73-1,3\nC72-2,1\nC72-3,2\n')
        update_economics_ranks(revision, self.root)
        data = build_economics_data(self.root)
        self.assertEqual(list(data), ['C72-2', 'C72-3', 'C73-1'])
        self.assertEqual(data['C73-1']['rank'], 3)
        self.assertEqual((self.root / REGISTRY_PATH).read_bytes(), original_registry)
        self.assertEqual(set(data), set(files))
        for record in registry['problems']:
            self.assertEqual((self.root / record['statement_file']).read_bytes(), files[record['id']])

    def test_legacy_source_ids_need_title_and_jel_for_reused_ids(self):
        self.imported()
        update_economics_ranks(self.csv, self.root, allow_source_ids=True, check_only=True)
        revision = self.write_ranks('Problem ID,New rank\nOP-0010,1\nOP-0050,2\nOP-0050,3\n')
        with self.assertRaisesRegex(ValueError, 'ambiguous source Problem ID'):
            update_economics_ranks(revision, self.root, allow_source_ids=True)
        with self.assertRaisesRegex(ValueError, 'unknown Problem ID'):
            update_economics_ranks(self.csv, self.root)

    def test_invalid_rankings_fail_without_mutation(self):
        self.imported()
        before = (self.root / RANKINGS_PATH).read_bytes()
        bad_csvs = [
            ('Problem ID,New rank\nC73-1,1\nC72-2,1\nC72-3,3\n', 'unique'),
            ('Problem ID,New rank\nC73-1,1\nC72-2,2\nC72-3,4\n', 'contiguous'),
            ('Problem ID,New rank\nC73-1,1\nC72-2,2\n', 'coverage'),
            ('Problem ID,New rank\nC73-1,1\nC72-2,2\nC72-2,3\n', 'duplicate Problem ID'),
            ('Problem ID,New rank\nC73-1,1\nC72-2,2\nC72-3,2.5\n', 'positive integer'),
            ('Problem ID,New rank\nC73-1,1\nC72-2,2\nX00-3,3\n', 'unknown Problem ID'),
            ('Problem ID,New rank,JEL code\nC73-1,1,C72\nC72-2,2,C72\nC72-3,3,C72\n', 'JEL code mismatch'),
            ('Problem ID,New rank,Problem title\nC73-1,1,Wrong title\nC72-2,2,Second problem\nC72-3,3,Third problem\n', 'title mismatch'),
        ]
        for text, error in bad_csvs:
            with self.subTest(error=error):
                with self.assertRaisesRegex(ValueError, error):
                    update_economics_ranks(self.write_ranks(text), self.root)
                self.assertEqual((self.root / RANKINGS_PATH).read_bytes(), before)

    def test_initial_csv_mismatch_produces_no_registry_or_statements(self):
        self.csv.write_text(self.csv.read_text().replace('Third problem', 'Different problem'))
        with self.assertRaisesRegex(ValueError, 'no exact OP/title/JEL source match'):
            self.imported()
        self.assertFalse((self.root / REGISTRY_PATH).exists())
        self.assertFalse((self.root / 'attacks').exists())

    def test_check_mode_leaves_all_rank_outputs_unchanged(self):
        self.imported()
        before = (self.root / RANKINGS_PATH).read_bytes()
        javascript = (self.root / 'docs/data/economics_data.js').read_bytes()
        revision = self.write_ranks('Problem ID,New rank\nC73-1,3\nC72-2,1\nC72-3,2\n')
        update_economics_ranks(revision, self.root, check_only=True)
        self.assertEqual((self.root / RANKINGS_PATH).read_bytes(), before)
        self.assertEqual((self.root / 'docs/data/economics_data.js').read_bytes(), javascript)


class CompleteEconomicsImportTests(unittest.TestCase):
    def test_all_657_classified_statements_have_unique_frozen_ids_and_rank_coverage(self):
        registry = load_registry()
        records = registry['problems']
        self.assertEqual(len(records), 657)
        self.assertEqual(len({record['id'] for record in records}), 657)
        self.assertEqual({record['initial_rank'] for record in records}, set(range(1, 658)))
        data = build_economics_data()
        self.assertEqual({record['rank'] for record in data.values()}, set(range(1, 658)))
        self.assertEqual(set(data), {record['id'] for record in records})
        expected = {
            'C73-1': ('OP-0590', 'Equilibrium payoffs in finite multiplayer stochastic games'),
            'C72-4': ('OP-0589', 'Computational complexity of optimin in finite games'),
            'C72-14': ('OP-0589', 'The Catch-Up optimal-draw conjecture for consecutive integers'),
            'D63-39': ('OP-0589', 'EFX existence for three agents with additive chores'),
            'D63-144': ('OP-0590', 'EFX and Pareto optimality for personalized bi-valued goods'),
        }
        for problem_id, (source_id, title) in expected.items():
            self.assertEqual((data[problem_id]['source_id'], data[problem_id]['title']), (source_id, title))
        for record in data.values():
            self.assertTrue(record['definition_tex'].strip())
            self.assertIn('Common conventions:', record['definition_tex'])
            self.assertNotIn('difficulty-rank:', record['definition_tex'])
            self.assertNotIn('\\ProblemClassification', record['definition_tex'])
            self.assertNotIn('Primary JEL index', record['definition_tex'])
            self.assertEqual(record['attacks'], [])

    def test_specialized_and_merged_source_conventions_are_present(self):
        data = build_economics_data()
        self.assertIn('BSDE conventions for SC-01--SC-06', data['C65-6']['definition_tex'])
        self.assertIn('Additional-source status and mathematical conventions', data['D63-3']['definition_tex'])
        self.assertIn('Source formulation: Game theory (GT-056)', data['D63-3']['definition_tex'])
        self.assertEqual(data['C73-10']['reference_aliases'], {'problem:OP-0590': 'C73-1'})
        records = load_registry()['problems']
        by_source = {record['source_original_id']: record for record in records
                     if record['source_catalog'] == 'Beyond game theory'}
        for source_id in ('SC-07', 'SC-08'):
            self.assertIn('Control and stopping conventions for SC-07--SC-08',
                          data[by_source[source_id]['id']]['definition_tex'])


if __name__ == '__main__':
    unittest.main()
