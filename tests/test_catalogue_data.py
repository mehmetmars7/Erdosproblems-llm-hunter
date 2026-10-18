import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.catalogue_data import write_catalogue_data


class CatalogueDataTests(unittest.TestCase):
    def test_keeps_search_and_identity_metadata_without_changing_full_records(self):
        records = {'7': {
            'id': 7, 'rank': 2, 'definition_tex': 'Searchable statement </script>',
            'we_solve': {'code': 'WS-100007', 'url': 'https://we-solve.github.io/problems/example/'},
            'attacks': [{'status': 'unresolved', 'raw': 'Full manuscript', 'sections': {'A': 'Full manuscript'},
                         'model': 'GPT', 'entry_kind': 'external_claim', 'openai': {'match': 'partial'},
                         'provenance': {'source_model': 'gpt_pro'}}],
        }}
        before = copy.deepcopy(records)
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'catalogue.js'
            write_catalogue_data(path, records, 'var problems', 'window.DATA = problems;')
            script = path.read_text()
        result = json.JSONDecoder().raw_decode(script.split(' = ', 1)[1])[0]
        self.assertEqual(records, before)
        self.assertEqual(result['7']['definition_tex'], before['7']['definition_tex'])
        self.assertEqual(result['7']['we_solve'], before['7']['we_solve'])
        expected = before['7']['attacks'][0]
        expected.pop('raw')
        expected.pop('sections')
        self.assertEqual(result['7']['attacks'][0], expected)
        self.assertNotIn('</script>', script)
        self.assertTrue(script.endswith('window.DATA = problems;\n'))

    def test_preserves_legacy_text_needed_to_infer_claim(self):
        records = {'1': {'attacks': [{'raw': 'The problem remains open.', 'sections': {}}]}}
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'catalogue.js'
            write_catalogue_data(path, records, 'window.DATA')
            result = json.JSONDecoder().raw_decode(path.read_text().split(' = ', 1)[1])[0]
        self.assertEqual(result['1']['attacks'][0]['raw'], 'The problem remains open.')
        self.assertNotIn('sections', result['1']['attacks'][0])
