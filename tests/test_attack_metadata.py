"""Keep quoted, rejected solution claims out of the site's attempt metadata."""

import unittest

from build_site import extract_completion, parse_attack


class AttackMetadataTests(unittest.TestCase):
    def test_correction_review_is_unresolved_without_a_completion_claim(self):
        content = r'''
\section{Review and correction of the claimed ``disproof''}
\textbf{``FULL SOLUTION --- COUNTEREXAMPLE / DISPROOF''}
\textbf{``COMPLETION: 100\%''}
are incorrect for the original open problem.
\item The completion estimate ``100\%'' is false for the original problem.
\item The original strengthening remains open in general.
'''
        attack = parse_attack(content, 'gpt pro 5.4')
        self.assertEqual(attack['status'], 'unresolved')
        self.assertNotIn('completion', attack)
        self.assertEqual(attack['raw'], content)

    def test_rejected_value_does_not_hide_a_corrected_estimate(self):
        for content in [
            r"The completion estimate ``100\%'' is false; the corrected estimate is 35\%.",
            r"COMPLETION ESTIMATE: 35\%, not 100\%.",
            r"COMPLETION ESTIMATE: 35\%; the earlier 100\% is incorrect.",
        ]:
            with self.subTest(content=content):
                self.assertEqual(extract_completion(content), 35)

    def test_ordinary_percentages_and_fractions_are_preserved(self):
        for content, expected in [
            (r'COMPLETION ESTIMATE: 0\%', 0),
            (r'COMPLETION ESTIMATE: 35\%', 35),
            (r'COMPLETION ESTIMATE: 100\%', 100),
            ('COMPLETION ESTIMATE\n0.25', 25),
        ]:
            with self.subTest(content=content):
                self.assertEqual(extract_completion(content), expected)

    def test_completion_rate_estimate_heading_used_by_astra_attempts(self):
        content = r'\textbf{Completion rate estimate: 40\%.}'
        self.assertEqual(extract_completion(content), 40)

    def test_rejected_decimal_is_not_reinterpreted_as_a_fraction(self):
        for content in [
            r'COMPLETION ESTIMATE: 0.50\% is false.',
            'COMPLETION ESTIMATE: 0.50 is incorrect.',
        ]:
            with self.subTest(content=content):
                self.assertIsNone(extract_completion(content))

    def test_latest_valid_block_wins_and_confidence_is_ignored(self):
        content = '\n\n\n\n'.join([
            r'COMPLETION ESTIMATE: 20\%',
            r'COMPLETION ESTIMATE: 45\%',
            r"The completion estimate ``100\%'' is false.",
            r'COMPLETION ESTIMATE: confidence 95\%',
        ])
        self.assertEqual(extract_completion(content), 45)

    def test_status_keeps_explicit_solved_and_unresolved_cases(self):
        for content, expected in [
            ('FULL SOLUTION', 'solved'),
            ('UNRESOLVED', 'unresolved'),
            ('The conjecture remains\nopen.', 'unresolved'),
        ]:
            with self.subTest(content=content):
                self.assertEqual(parse_attack(content, 'test')['status'], expected)

    def test_partial_statuses_and_formalizations_are_unresolved(self):
        for content in [
            '6) FINAL STATUS: PARTIAL\nA checked reduction; the general proof is missing.',
            r'\section*{Final status}' + '\n' + r'\textbf{PARTIAL}.',
            r'\textbf{Status: Partial (conditional formalization)}',
            'PARTIAL formalization of the original problem.',
            r'\noindent\textbf{LABEL: PARTIAL}',
        ]:
            with self.subTest(content=content):
                self.assertEqual(parse_attack(content, 'test')['status'], 'unresolved')

    def test_partial_mathematical_prose_does_not_override_full_solution(self):
        for content in [
            'The partial results of earlier work are strengthened here.\nFULL SOLUTION',
            'Partial sums converge.\nFULL SOLUTION',
            r'\[\partial f / \partial x = 0\]' + '\nFULL SOLUTION',
        ]:
            with self.subTest(content=content):
                self.assertEqual(parse_attack(content, 'test')['status'], 'solved')

    def test_conditional_and_candidate_outcomes_are_not_full_solutions(self):
        for outcome in ['Conditional reduction', 'Counterexample candidate',
                        'New partial result / lemma candidate']:
            with self.subTest(outcome=outcome):
                content = r'\textbf{Outcome: ' + outcome + '.}'
                self.assertEqual(parse_attack(content, 'test')['status'], 'unresolved')

    def test_status_marker_controls_short_descriptions_without_status_prose(self):
        for value, expected in [('unresolved', 'unresolved'), ('PARTIAL', 'unresolved'),
                                ('solved', 'solved')]:
            content = (f'% ATTEMPT_STATUS: {value}\n'
                       + r'\href{https://github.com/example/proof/blob/commit/Main.lean}{Lean source}')
            with self.subTest(value=value):
                self.assertEqual(parse_attack(content, 'test')['status'], expected)

    def test_invalid_and_conflicting_status_markers_fail_explicitly(self):
        for content in ['% ATTEMPT_STATUS: unknown',
                        '% ATTEMPT_STATUS: solved\n% ATTEMPT_STATUS: partial']:
            with self.subTest(content=content), self.assertRaisesRegex(ValueError, 'ATTEMPT_STATUS'):
                parse_attack(content, 'test')


if __name__ == '__main__':
    unittest.main()
