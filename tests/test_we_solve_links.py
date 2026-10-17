"""Navigation mappings must retain identity and reject stale source revisions."""

import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.we_solve_links import attach_we_solve_links, load_mapping


class WeSolveLinksTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = 'attacks/open_problems/top_problems/model/1.tex'
        source = self.root / self.path
        source.parent.mkdir(parents=True)
        source.write_text('Original manuscript with https://github.com/mehmetmars7/Erdosproblems-llm-hunter.\n')
        self.source = source
        self.destination = {
            'alias': 'TOP-1-A2', 'revision': 'r1',
            'url': 'https://we-solve.github.io/contributions/p-versus-np-problem/attempt-2/r1/',
            'source_url': 'https://github.com/we-solve/research/blob/main/problems/8f/problem/contributions/attempt/files/1.tex',
            'local_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        }
        self.mapping = {
            'schema_version': 1,
            'problems': {'open_problems:1': {
                'code': 'WS-100001', 'alias': 'TOP-1',
                'url': 'https://we-solve.github.io/problems/p-versus-np-problem/',
            }},
            'sources': {self.path: self.destination},
        }
        self.mapping_path = self.root / 'lists/we_solve_links.json'
        self.mapping_path.parent.mkdir()
        self.write_mapping()

    def write_mapping(self):
        self.mapping_path.write_text(json.dumps(self.mapping))

    def test_uses_fixed_id_and_source_path_preserving_content(self):
        attack = {'file_path': self.path, 'model': 'model', 'raw': self.source.read_text()}
        records = {'1': {'id': 1, 'rank': 900, 'definition_tex': 'Existing definition', 'attacks': [attack]}}
        original = copy.deepcopy(records)
        attach_we_solve_links(records, 'open_problems', self.root)
        self.assertEqual(records['1']['we_solve']['code'], 'WS-100001')
        self.assertEqual(attack['we_solve']['alias'], 'TOP-1-A2')
        self.assertNotIn('local_sha256', attack['we_solve'])
        del records['1']['we_solve']
        del attack['we_solve']
        self.assertEqual(records, original)

    def test_changed_source_does_not_link_to_old_we_solve_revision(self):
        attack = {'file_path': self.path, 'we_solve': {'url': 'stale'}}
        records = {'1': {'attacks': [attack]}}
        self.source.write_text('A later revision')
        with self.assertWarnsRegex(RuntimeWarning, 'mapping needs updating'):
            attach_we_solve_links(records, 'open_problems', self.root)
        self.assertNotIn('we_solve', attack)
        self.assertEqual(records['1']['we_solve']['code'], 'WS-100001')

    def test_merged_record_retains_its_own_code_independent_of_rank(self):
        self.mapping['problems']['open_problems:3395'] = {
            'record_code': 'WS-100007', 'code': 'WS-100001', 'alias': 'TOP-3395',
            'problem_id': 'original-record', 'canonical_alias': 'TOP-1',
            'canonical_problem_id': 'canonical-record',
            'url': 'https://we-solve.github.io/problems/p-versus-np-problem/',
        }
        self.write_mapping()
        records = {'3395': {'id': 3395, 'rank': 1}}
        attach_we_solve_links(records, 'open_problems', self.root)
        before = records['3395']['we_solve'].copy()
        records['3395']['rank'] = 7000
        attach_we_solve_links(records, 'open_problems', self.root)
        self.assertEqual(records['3395']['we_solve'], before)
        self.assertEqual(before['record_code'], 'WS-100007')
        self.assertEqual(before['code'], 'WS-100001')
        self.assertEqual(before['canonical_alias'], 'TOP-1')

    def test_unmapped_problem_keeps_original_data(self):
        records = {'123': {'attacks': [{'file_path': 'attacks/unknown/123.tex'}]}}
        original = copy.deepcopy(records)
        attach_we_solve_links(records, 'mo', self.root)
        self.assertEqual(records, original)

    def test_mo_routes_share_one_identity(self):
        self.mapping['problems']['mo:123'] = self.mapping['problems'].pop('open_problems:1')
        self.write_mapping()
        direct = {'123': {}}
        combined = {'mo:123': {}}
        attach_we_solve_links(direct, 'mo', self.root)
        attach_we_solve_links(combined, 'open_problems', self.root)
        self.assertEqual(direct['123']['we_solve'], combined['mo:123']['we_solve'])

    def test_rejects_wrong_host_and_path_traversal(self):
        for url in ['https://we-solve.github.io.evil.test/problems/example/',
                    'https://we-solve.github.io/problems/%2e%2e/elsewhere/']:
            with self.subTest(url=url):
                self.mapping['problems']['open_problems:1']['url'] = url
                self.write_mapping()
                with self.assertRaises(ValueError):
                    load_mapping(self.root)


if __name__ == '__main__':
    unittest.main()
