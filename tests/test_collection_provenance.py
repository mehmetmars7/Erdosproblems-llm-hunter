"""Keep collection imports distinct from independently authored attempts."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from build_site import (
    aggregate_problem_status, apply_erdos_status, build_erdos_data,
    parse_attack, parse_collection_metadata,
)


class CollectionProvenanceTests(unittest.TestCase):
    def reused_metadata(self, **overrides):
        metadata = {
            'schema_version': 1,
            'kind': 'reused_writeup',
            'source_model': 'gpt_pro_5.2',
            'primary_source': 'attacks/erdos/gpt_pro_5.2/51_v2.tex',
            'source_paths': [
                'attacks/erdos/gpt_pro_5.2/51.tex',
                'attacks/erdos/gpt_pro_5.2/51_v2.tex',
            ],
            'source_completion': 35,
            'source_claim': 'unresolved',
            'independently_reviewed': False,
        }
        metadata.update(overrides)
        return metadata

    def record(self, metadata, body):
        return '% COLLECTION_METADATA: ' + json.dumps(metadata) + '\n' + body

    def test_primary_source_claim_and_estimate_override_quoted_versions(self):
        metadata = self.reused_metadata(source_claim='solved')
        body = 'Another version is UNRESOLVED.\nCOMPLETION ESTIMATE: 90%'
        attack = parse_attack(self.record(metadata, body), 'GPT 6 Astra Ultra', '2026-09-23')
        self.assertEqual(attack['status'], 'solved')
        self.assertEqual(attack['completion'], 35)
        self.assertEqual(attack['provenance'], {
            **metadata,
            'primary_source': 'attacks/open_problems/erdos/gpt_pro_5.2/51_v2.tex',
            'source_paths': [
                'attacks/open_problems/erdos/gpt_pro_5.2/51.tex',
                'attacks/open_problems/erdos/gpt_pro_5.2/51_v2.tex',
            ],
        })
        self.assertEqual(attack['entry_kind'], 'reused_writeup')
        self.assertEqual(attack['model'], 'GPT 6 Astra Ultra')
        self.assertEqual(attack['date_posted'], '2026-09-23')

    def test_migrated_source_links_preserve_submitted_metadata_and_other_paths(self):
        metadata = self.reused_metadata(
            primary_source='attacks/mo/model/123-question.tex',
            source_paths=[
                'attacks/erdos/model/5.tex',
                'attacks/mo/model/123-question.tex',
                'attacks/open_problems/erdos/model/5_v2.tex',
                'attacks/another_collection/model/5.tex',
            ],
        )
        body = 'Original attribution and mathematical text are preserved.'
        source = self.record(metadata, body)
        attack = parse_attack(source, 'collection')
        self.assertEqual(attack['provenance'], {
            **metadata,
            'primary_source': 'attacks/open_problems/mo/model/123-question.tex',
            'source_paths': [
                'attacks/open_problems/erdos/model/5.tex',
                'attacks/open_problems/mo/model/123-question.tex',
                'attacks/open_problems/erdos/model/5_v2.tex',
                'attacks/another_collection/model/5.tex',
            ],
        })
        self.assertEqual(parse_collection_metadata(source), (metadata, body))
        self.assertEqual(attack['raw'], body)

    def test_machine_metadata_is_removed_from_display_text_and_sections(self):
        body = 'PROBLEM 51\nAn attributed writeup.'
        attack = parse_attack(self.record(self.reused_metadata(), body), 'collection')
        self.assertEqual(attack['raw'], body)
        self.assertNotIn('COLLECTION_METADATA', json.dumps(attack['sections']))

    def test_unknown_estimate_does_not_become_footer_or_other_version_estimate(self):
        body = (
            'COMPLETION ESTIMATE: 100% in another version.\n\n\n\n'
            'COMPLETION ESTIMATE: Not numerically assessed in the original writeup. '
            'Newly verified progress in this import: 0%; this is an import/review-work measure.'
        )
        attack = parse_attack(self.record(self.reused_metadata(source_completion=None), body), 'collection')
        self.assertNotIn('completion', attack)

    def test_statement_record_cannot_inherit_a_solution_or_completion_claim(self):
        metadata = {
            'schema_version': 1,
            'kind': 'statement_only',
            'source_urls': ['https://www.erdosproblems.com/1137'],
            'independently_reviewed': False,
        }
        attack = parse_attack(self.record(metadata, 'FULL SOLUTION\nCOMPLETION ESTIMATE: 100%'), 'collection')
        self.assertEqual(attack['entry_kind'], 'statement_only')
        self.assertEqual(attack['status'], 'unresolved')
        self.assertEqual(attack['completion'], 0)
        self.assertEqual(attack['provenance'], metadata)

    def test_invalid_json_fails_instead_of_losing_attribution(self):
        with self.assertRaisesRegex(ValueError, 'COLLECTION_METADATA JSON'):
            parse_attack('% COLLECTION_METADATA: {bad json}\nFULL SOLUTION', 'collection')

    def test_invalid_schema_and_invalid_provenance_fail_explicitly(self):
        for overrides in [
            {'schema_version': 2},
            {'kind': 'new_proof'},
            {'source_model': ''},
            {'primary_source': None},
            {'source_paths': []},
            {'source_claim': 'proved'},
            {'source_completion': True},
            {'source_completion': 101},
            {'source_completion': float('nan')},
            {'independently_reviewed': True},
        ]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                parse_attack(self.record(self.reused_metadata(**overrides), 'body'), 'collection')

    def test_unmarked_attempt_remains_compatible(self):
        body = 'UNRESOLVED\nCOMPLETION ESTIMATE: 42%'
        attack = parse_attack(body, 'ordinary model')
        self.assertEqual(attack['raw'], body)
        self.assertEqual(attack['status'], 'unresolved')
        self.assertEqual(attack['completion'], 42)
        self.assertNotIn('entry_kind', attack)
        self.assertNotIn('provenance', attack)

    def test_statement_does_not_change_an_existing_attempt_claim(self):
        problems = {'51': {'attacks': [
            {'entry_kind': 'statement_only', 'status': 'unresolved'},
            {'status': 'solved'},
        ]}}
        self.assertEqual(aggregate_problem_status(problems)['51']['status'], 'solved')

    def test_statement_only_problem_has_no_attempt_claim_and_keeps_database_rule(self):
        problems = {'51': {'attacks': [
            {'entry_kind': 'statement_only', 'status': 'unresolved', 'completion': 0},
        ]}}
        snapshot = {
            'database_url': 'https://teorth.github.io/erdosproblems/',
            'problems': {'51': {
                'status': 'Open',
                'informal_status': 'open',
                'status_updated': '2026-09-23',
                'statement_formalization': {'state': 'none', 'url': None},
                'solution_formalization': {'state': 'none', 'url': None},
            }},
        }
        result = apply_erdos_status(aggregate_problem_status(problems), snapshot)['51']
        self.assertEqual(result['attempt_status'], 'none')
        self.assertEqual(result['llm_status'], 'unresolved')
        self.assertEqual(result['llm_status_source'], 'database_rule')
        self.assertFalse(result['is_solved'])

    def test_full_upstream_catalogue_includes_problems_without_local_attempts(self):
        def upstream(status):
            return {
                'status': status,
                'informal_status': status,
                'status_updated': '2026-09-23',
                'statement_formalization': {'state': 'none', 'url': None},
                'solution_formalization': {'state': 'none', 'url': None},
            }

        snapshot = {
            'database_url': 'https://teorth.github.io/erdosproblems/',
            'problems': {'1': upstream('proved'), '2': upstream('open'), '3': upstream('independent')},
        }
        with TemporaryDirectory() as directory, \
                patch('build_site.ATTACKS_DIR', Path(directory)), \
                patch('build_site.load_erdos_problems_list', return_value={
                    '2': {'problem_url': 'https://www.erdosproblems.com/2#comments'},
                }), \
                patch('build_site.load_review', return_value=None), \
                patch('build_site.load_erdos_status', return_value=snapshot) as load_status:
            problems = build_erdos_data()
        load_status.assert_called_once_with()
        self.assertEqual(set(problems), {'1', '2', '3'})
        self.assertEqual(problems['2']['problem_url'], 'https://www.erdosproblems.com/2#comments')
        for number in ('1', '3'):
            self.assertEqual(problems[number]['completion'], 100)
            self.assertEqual(problems[number]['completion_source'], 'database')
            self.assertEqual(problems[number]['attacks'], [])
            self.assertEqual(problems[number]['attempt_status'], 'none')
            self.assertTrue(problems[number]['is_solved'])


if __name__ == '__main__':
    unittest.main()
