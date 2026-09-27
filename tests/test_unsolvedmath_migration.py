"""Regression checks for mathematical identity preservation during import."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    'migrate_unsolvedmath', Path(__file__).parents[1] / 'scripts' / 'migrate_unsolvedmath.py')
migration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migration)


class IdentityMigrationTests(unittest.TestCase):
    def test_later_approval_does_not_shift_existing_allocations(self):
        pinned = {'catalogue-49': None, 'catalogue-50': 30006699}
        new_id, watermark = migration.allocate_pinned_id(pinned, 'catalogue-49', 30006974)
        self.assertEqual(new_id, 30006975)
        old_id, watermark = migration.allocate_pinned_id(pinned, 'catalogue-50', watermark)
        self.assertEqual(old_id, 30006699)
        self.assertEqual(watermark, 30006975)
        self.assertEqual(migration.allocate_pinned_id(pinned, 'catalogue-118', watermark),
                         (30006976, 30006976))

    def record(self, canonical=6):
        return {'id': canonical, 'title': 'Hodge Conjecture', 'category_id': 5,
                'category': {'id': 5, 'name': 'algebraic_geometry',
                             'display_name': 'Algebraic Geometry'}, 'status': 'open'}

    def document(self, body=''):
        return (r'\documentclass{article}' + '\n' + r'\begin{document}' + '\n'
                + r'\section{Original title}\label{4}' + '\n'
                + r'\subsection{Definitions and mathematical statement}' + '\n'
                + '$4+6=10$. ' + body + '\n'
                + r'\subsection{Short English statement}' + '\nA question.\n'
                + r'\subsection{Sources}' + '\n'
                + r'\url{https://example.org/source}' + '\n'
                + r'\end{document}' + '\n')

    def test_reference_to_other_old_id_not_captured_by_new_own_label(self):
        text = self.document(r'Self \ref{4}; other \ref{6}; local \ref{7}. \label{7}')
        changed = migration.transform(text, self.record(), 4, {4: 6, 6: 5}, posted='2026-09-24')
        self.assertIn(r'Self \ref{6}; other \ref{5}; local \ref{7}. \label{7}', changed)
        self.assertIn('$4+6=10$', changed)
        self.assertIn('% FIRST_POSTED: 2026-09-24', changed)
        self.assertNotIn(r'\label{4}', changed)

    def test_destination_label_collision_stops_import(self):
        with self.assertRaisesRegex(ValueError, 'collide with local label'):
            migration.transform(self.document(r'\label{6}'), self.record(), 4, {4: 6})

    def test_definition_recovery_preserves_macros_and_excludes_research(self):
        text = self.document().replace(r'\begin{document}', r'\newcommand{\Q}{\mathbb Q}' + '\n' + r'\begin{document}')
        text = text.replace(r'\subsection{Sources}', r'\subsection{Research attempt}'
                            + '\nA failed approach.\n' + r'\subsection{Sources}')
        recovered = migration.definition_only(text)
        self.assertIn(r'\newcommand{\Q}{\mathbb Q}', recovered)
        self.assertIn('$4+6=10$', recovered)
        self.assertNotIn('A failed approach.', recovered)
        self.assertIn(r'\url{https://example.org/source}', recovered)
        self.assertIn('A failed approach.', text)

    def test_source_anchors_renumber_without_touching_equations(self):
        text = self.document(r'\sref{4}{1}\hypertarget{source:4:1}{} $x^4=6$.')
        changed = migration.transform(text, self.record(30006674), 4, {4: 30006674}, statement_only=True)
        self.assertIn(r'\sref{30006674}{1}\hypertarget{source:30006674:1}{} $x^4=6$', changed)
        self.assertIn('% FIRST_POSTED: null', changed)
        self.assertIn('% ENTRY_KIND: statement_only', changed)

    def test_ambiguous_external_reference_stops_import(self):
        with self.assertRaisesRegex(ValueError, 'Unresolved catalogue cross-reference'):
            migration.transform(self.document(r'\ref{9}'), self.record(), 4, {4: 6, 9: None})


if __name__ == '__main__':
    unittest.main()
