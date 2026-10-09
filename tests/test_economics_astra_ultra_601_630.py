"""Freeze the selected research identities and protect public attempt wiring."""
import unittest
from scripts.economics_catalog import BASE_DIR, build_economics_data

# Rank selection on 2026-10-09. These identities survive subsequent reranking.
BATCH_IDS = ('I25-601', 'Q54-602', 'I14-603', 'C90-604', 'L41-605', 'C73-606', 'I26-607', 'H26-608', 'D91-609', 'I18-610', 'J41-611', 'O17-612', 'L41-613', 'O32-614', 'I21-615', 'L40-616', 'H22-617', 'I11-618', 'C78-619', 'C72-620', 'I13-621', 'D44-622', 'J44-623', 'I21-624', 'G11-625', 'O31-626', 'D91-627', 'I11-628', 'D73-629', 'D91-630')

class EconomicsAstraUltra601To630Tests(unittest.TestCase):
    def test_reviewed_attempts_have_exact_identities_status_and_downloads(self):
        self.assertEqual(len(set(BATCH_IDS)), 30)
        data = build_economics_data()
        for problem_id in BATCH_IDS:
            with self.subTest(problem_id=problem_id):
                record = data[problem_id]
                attempts = [a for a in record['attacks']
                            if a['model'] == 'GPT 6 Astra Ultra' and a['version'] == 1]
                self.assertEqual(len(attempts), 1)
                attempt = attempts[0]
                self.assertEqual(attempt['status'], 'solved' if problem_id == 'C78-619' else 'unresolved')
                self.assertEqual(attempt['entry_kind'], 'research_attempt')
                self.assertEqual(attempt['date_posted'], '2026-10-09')
                self.assertEqual(record['status'], 'open')
                if problem_id == 'C78-619':
                    self.assertEqual(record['llm_status'], 'solved')
                source = BASE_DIR / attempt['file_path']
                self.assertEqual(source.name, problem_id + '.tex')
                self.assertEqual(source.read_bytes(), (BASE_DIR/'docs'/attempt['download_url']).read_bytes())
                text = source.read_text()
                canonical = (BASE_DIR/record['definitionFile']).read_text()
                self.assertEqual(text.splitlines()[0], canonical.splitlines()[0])
                self.assertEqual(text.count('% ECONOMICS_PROBLEM:'), 1)
                self.assertIn(r'\begin{proof}', text)
                self.assertRegex(text, r'\\begin\{(?:theorem|lemma|proposition|corollary)\}')
                self.assertRegex(text, r'\\(?:url|href)\{https://')
                self.assertNotRegex(text, r'/Users/|/private/tmp/|/mnt/data|TODO|proof omitted|MERGED_PROBLEM')

if __name__ == '__main__':
    unittest.main()
