"""Posting dates survive revisions, migration, and reset filesystem timestamps."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import build_site

class PostedDatesTests(unittest.TestCase):
    def test_lowercase_astra_rename_preserves_first_posting_without_changing_models(self):
        base = build_site.BASE_DIR
        prefix = 'attacks/open_problems/top_problems/'
        dates = {
            prefix + 'GPT_6_Astra_Ultra/1.tex': '2026-09-20',
            prefix + 'gpt_6_astra_ultra/1.tex': '2026-09-27',
            prefix + 'gpt_6_astra_pro/1.tex': '2026-09-26',
        }
        with patch.object(build_site, 'load_first_posted_dates', return_value=dates):
            self.assertEqual(build_site.get_file_date(base / prefix / 'gpt_6_astra_ultra/1.tex'),
                             '2026-09-20')
            self.assertEqual(build_site.get_file_date(base / prefix / 'gpt_6_astra_pro/1.tex'),
                             '2026-09-26')
            self.assertIsNone(build_site.get_file_date(base / prefix / 'gpt_6_astra_ultra/1_v2.tex'))

    def test_history_survives_rewrite_and_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args, date=None):
                env = os.environ.copy()
                if date:
                    env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
                return subprocess.run(['git', *args], cwd=root, env=env,
                                      capture_output=True, text=True, check=True)
            git('init'); git('config', 'user.email', 'test@example.invalid')
            git('config', 'user.name', 'Date test')
            old = root/'attacks/erdos/model/1.tex'
            old.parent.mkdir(parents=True); old.write_text('original\n')
            git('add', '.'); git('commit', '-m', 'First posting', date='2026-01-17T12:00:00+00:00')
            old.write_text('revised\n'); git('add', '.')
            git('commit', '-m', 'Revision', date='2026-03-04T12:00:00+00:00')
            new = root/'attacks/open_problems/erdos/model/1.tex'
            new.parent.mkdir(parents=True); old.unlink(); new.write_text('entirely different proof\n')
            version = new.with_name('1_v2.tex'); version.write_text('separate version\n')
            git('add', '.'); git('commit', '-m', 'Move and add version', date='2026-09-25T12:00:00+00:00')
            os.utime(new, (2000000000, 2000000000))
            untracked = new.with_name('2.tex'); untracked.write_text('not posted\n')
            build_site.load_first_posted_dates.cache_clear()
            with patch.object(build_site, 'BASE_DIR', root):
                self.assertEqual(build_site.get_file_date(new), '2026-01-17')
                self.assertEqual(build_site.get_file_date(version), '2026-09-25')
                self.assertIsNone(build_site.get_file_date(untracked))

    def test_export_without_git_does_not_invent_a_date(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'attacks/model/1.tex'
            source.parent.mkdir(parents=True); source.write_text('attempt\n')
            build_site.load_first_posted_dates.cache_clear()
            with patch.object(build_site, 'BASE_DIR', root):
                self.assertIsNone(build_site.get_file_date(source))

if __name__ == '__main__':
    unittest.main()
