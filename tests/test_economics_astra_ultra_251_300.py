"""Freeze the selected research identities and protect public attempt wiring."""
import unittest
from scripts.economics_catalog import BASE_DIR, build_economics_data

# Rank selection on 2026-10-09. These identities survive subsequent reranking.
BATCH_IDS = ('C23-251', 'C73-252', 'J52-253', 'G13-254', 'G14-255', 'C73-256', 'D86-257', 'G21-258', 'C13-259', 'J15-260', 'E52-261', 'G21-262', 'I18-263', 'D71-264', 'F12-265', 'C21-266', 'F12-267', 'C78-268', 'L15-269', 'G12-270', 'C79-271', 'C62-272', 'Q58-273', 'O14-274', 'D82-275', 'J13-276', 'F16-277', 'H22-278', 'G14-279', 'D82-280', 'G23-281', 'C31-282', 'G28-283', 'C90-284', 'C72-285', 'O33-286', 'R58-287', 'C61-288', 'C31-289', 'G12-290', 'E25-291', 'Q57-292', 'C78-293', 'D63-294', 'C21-295', 'F44-296', 'O18-297', 'O33-298', 'C71-299', 'H11-300')

class EconomicsAstraUltra251To300Tests(unittest.TestCase):
    def test_reviewed_attempts_have_exact_identities_status_and_downloads(self):
        self.assertEqual(len(set(BATCH_IDS)), 50)
        data = build_economics_data()
        for problem_id in BATCH_IDS:
            with self.subTest(problem_id=problem_id):
                record = data[problem_id]
                attempts = [a for a in record['attacks']
                            if a['model'] == 'GPT 6 Astra Ultra' and a['version'] == 1]
                self.assertEqual(len(attempts), 1)
                attempt = attempts[0]
                self.assertEqual(attempt['status'], 'unresolved')
                self.assertEqual(attempt['entry_kind'], 'research_attempt')
                self.assertEqual(attempt['date_posted'], '2026-10-09')
                # Later attempts may solve the aggregate; the frozen attempt stays unresolved.
                aggregate = 'solved' if any(a['status'] == 'solved' for a in record['attacks']) else 'open'
                self.assertEqual(record['status'], aggregate)
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
