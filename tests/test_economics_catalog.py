"""Protect Economics provenance and pre-existing catalogue identities."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

import build_site
from scripts.import_economics_statements import (definition_tex, import_records,
                                                status_for, validate_record)

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
      separators=(',', ':')).encode()).hexdigest()


class EconomicsCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT/'lists/economics/manifest.json').read_text())

    def test_preserves_all_original_entries_and_all_existing_identities_and_ranks(self):
        manifest = self.manifest
        records = manifest['records']
        self.assertEqual(sorted(r['original_id'] for r in records), list(range(1, 251)))
        ids = {r['id'] for r in records}
        self.assertEqual(len(ids), 250)
        registry = json.loads((ROOT/'lists/unsolvedmath/problems.json').read_text())
        old = [r for r in registry if r['id'] not in ids]
        self.assertEqual(len(old), manifest['previous_record_count'])
        self.assertEqual(digest(old), manifest['previous_catalogue_semantic_sha256'])
        order = json.loads((ROOT/'lists/unsolvedmath/display_order.json').read_text())
        self.assertEqual(digest(order[:len(old)]), manifest['previous_display_order_semantic_sha256'])
        self.assertEqual(set(order[len(old):]), ids)
        self.assertGreater(min(ids), max(r['id'] for r in old))
        imported = [r for r in registry if r['id'] in ids]
        self.assertTrue(all(r['category']['name'] == 'economics' and
                            r['external_url'] is None and r['published'] is False for r in imported))

    def test_every_definition_is_standalone_attributed_and_has_no_research_attempt(self):
        for record in self.manifest['records']:
            with self.subTest(original_id=record['original_id']):
                validate_record(record)
                text = definition_tex(record, self.manifest['category'], self.manifest['prepared_at'])
                path = ROOT/'attacks/open_problems/top_problems/definitions'/f'{record["id"]}.tex'
                self.assertEqual(path.read_text(), text)
                self.assertIn('% ENTRY_KIND: statement_only', text)
                parsed = build_site.parse_numbered_problem_tex(text)
                self.assertFalse(parsed['researchTeX'])
                self.assertTrue(parsed['definitionTeX'])
                self.assertEqual(parsed['sources'][0]['url'], record['references'][0]['url'])
                first = record.get('earliest_verified_reference')
                if first:
                    self.assertEqual(parsed['sources'][0]['url'], first['url'])
                if record['source_status'] in {'not_verified', 'resolved_or_misstated'}:
                    self.assertIsNone(first)
                    self.assertEqual(status_for(record), 'provenance_pending')
                    self.assertIn('must not be treated as a first listing', text)
                elif record['formalization_basis'] != 'source_statement':
                    self.assertEqual(status_for(record), 'research_question')

    def test_cannot_promote_a_supporting_reference_to_a_source_authored_open_statement(self):
        row = copy.deepcopy(next(r for r in self.manifest['records'] if r['source_status'] == 'not_verified'))
        row['formalization_basis'] = 'source_statement'
        with self.assertRaisesRegex(ValueError, 'published mathematical statement'):
            validate_record(row)
        row['formalization_basis'] = 'proposed_specification'
        row['priority_status'] = 'verified_original'
        with self.assertRaisesRegex(ValueError, 'Priority evidence'):
            validate_record(row)

    def test_source_order_reservation_and_idempotence(self):
        row = copy.deepcopy(next(r for r in self.manifest['records'] if r['earliest_verified_reference']))
        row['references'][0]['url'] = 'https://example.org/unrelated'
        with self.assertRaisesRegex(ValueError, 'listed first'):
            validate_record(row)
        before = (ROOT/'lists/unsolvedmath/problems.json').read_bytes()
        result = import_records(self.manifest, check=True)
        self.assertEqual(result, dict(validated=250, new_records=0, wrote=False))
        self.assertEqual((ROOT/'lists/unsolvedmath/problems.json').read_bytes(), before)
        bad = copy.deepcopy(self.manifest)
        bad['records'][0]['id'] += 10000
        with self.assertRaisesRegex(ValueError, 'reservation report'):
            import_records(bad, check=True)


if __name__ == '__main__':
    unittest.main()
