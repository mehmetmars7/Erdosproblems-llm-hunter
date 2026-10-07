"""An import needs explicit review, original prose, and repeatable source links."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import import_openai_math as importer
from scripts.inventory_openai_math import public_comparator_metadata


class OpenAIImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.catalog = self.root / 'top_problems'
        self.export = self.root / 'export'
        self.export.mkdir()
        self.folder = 'Sharp-integral-fillings-in-CAT(0)-spaces-September-23-2026'
        paper = {
            'title': 'Integral fillings in CAT(0) spaces', 'dir': self.folder,
            'pdf_path': f'preprints/{self.folder}/custom_name.pdf',
            'readme_path': f'preprints/{self.folder}/README.md', 'date': '2026-09-23',
            'inputs_md': None, 'source_tex_dir': f'preprints/{self.folder}/build/source',
            'comparators': [{
                'json': 'lean/ComparatorChallenges/Fillings.json',
                'lean': 'lean/ComparatorChallenges/Fillings.lean',
                'theorem_names': ['integral_filling_bound'],
                'solution_module': 'OAI.Fillings', 'declaration': 'OAI.Fillings.bound',
                'file': 'lean/OAI/Fillings.lean',
            }],
        }
        self.inventory = {
            'schema_version': 1, 'source_repo': importer.SOURCE_REPO,
            'source_commit': importer.SOURCE_COMMIT, 'repo_path': str(self.root / 'source'),
            'families': [{
                'family': '001', 'title': 'Metric fillings', 'subject': 'Geometry',
                'lean_doc': 'lean/docs/001.md', 'reasoning_trace': None,
                'manuscripts': [paper],
            }],
        }
        self.row = {
            'family': '001', 'manuscript_dir': self.folder, 'candidate_id': 5,
            'pool': 'A', 'class': 'full', 'resolution': 'proved',
            'openai_theorem_ref': 'Theorem 1.1', 'our_clause': 'Every integral cycle.',
            'justification': 'The bound covers every object specified by the statement.',
            'lean_covers_main_theorem': True, 'second_pass': 'agreed',
        }
        self.approval = {'source_commit': importer.SOURCE_COMMIT, 'approved_solved_ids': [5]}
        self.sections = {
            'claim': 'OpenAI claims the requested estimate for integral fillings.',
            'mathematical_statement': (r'Theorem 1.1: For every integral \(k\)-cycle \(z\), '
                                      r'there is a filling \(b\) with \(\partial b=z\) and '
                                      r'\[\mathbf M(b)\le C_k\mathbf M(z)^{(k+1)/k}.\]'),
            'outline': 'A construction controls the boundary while comparing local pieces.',
            'scope': 'The conclusion includes each cycle specified by this catalogue statement.',
            'formal_verification': 'The documented comparator addresses the main bound. This site has not run Lean.',
            'status_caveat': 'An internal OpenAI model produced the result. Unformalised work may contain errors. Independent review has not been performed here.',
        }
        self.summaries = self.root / 'summaries.json'
        self.summaries.write_text(json.dumps({'5': self.sections}), encoding='utf-8')
        self.definition_header = '% TOP_PROBLEM: ' + json.dumps({'id': 5, 'title': 'Synthetic filling problem'}, separators=(', ', ': '))
        (self.catalog / 'definitions').mkdir(parents=True)
        (self.catalog / 'definitions/5.tex').write_text(self.definition_header + '\nStatement.\n', encoding='utf-8')
        self.write_exports([5])
        self.manifest = deepcopy(self.inventory)
        self.manifest.pop('repo_path')
        self.manifest['eligible_paths'] = ['CONTENTS.md', 'overview.tex', paper['pdf_path'],
                                          paper['readme_path'], 'lean/docs/001.md',
                                          'lean/ComparatorChallenges/Fillings.json',
                                          'lean/ComparatorChallenges/Fillings.lean']

    def write_exports(self, ids):
        (self.export / 'problems.json').write_text(json.dumps([{'id': n} for n in ids]), encoding='utf-8')
        (self.export / 'display_order.json').write_text(json.dumps(ids), encoding='utf-8')

    def prepare(self, **kwargs):
        options = dict(approval=self.approval, manifest=self.manifest, export_dir=self.export)
        options.update(kwargs)
        with patch.object(importer, 'validate_checkout'), patch.object(importer, 'original_texts', return_value=[]):
            return importer.prepare_import(self.inventory, [self.row], self.summaries, self.catalog, **options)

    def test_solved_label_needs_explicit_approval_and_agreed_second_pass(self):
        for approval in (None, {'source_commit': importer.SOURCE_COMMIT, 'approved_solved_ids': []}):
            with self.subTest(approval=approval), self.assertRaisesRegex(ValueError, 'explicit user approval'):
                importer.group_rows([self.row], self.inventory, approval)
        for verdict in (None, 'disagreed', 'pending'):
            row = dict(self.row, second_pass=verdict)
            with self.subTest(verdict=verdict), self.assertRaisesRegex(ValueError, 'independent second pass'):
                importer.group_rows([row], self.inventory, self.approval)
        with self.assertRaisesRegex(ValueError, 'pinned source_commit'):
            importer.group_rows([self.row], self.inventory, dict(self.approval, source_commit='f' * 40))

    def test_public_manifest_preserves_declarations_for_generated_claim_validation(self):
        manifest = deepcopy(self.manifest)
        paper = manifest['families'][0]['manuscripts'][0]
        paper['comparators'] = [public_comparator_metadata(value)
                                for value in paper['comparators']]
        pending, unchanged = self.prepare(manifest=manifest)
        self.assertEqual(len(pending), 1)
        self.assertEqual(unchanged, [])
        self.assertIn('"declarations":["OAI.Fillings.bound"]', next(iter(pending.values())))
        record = next(iter(pending.values()))
        self.assertIn(r'citation key \texttt{OAI:', record)
        self.assertNotIn('\texttt{OAI:', record)

    def test_partial_remains_unresolved_and_related_rows_do_not_generate_records(self):
        row = dict(self.row, **{'class': 'partial', 'resolution': 'partial', 'second_pass': 'n/a'})
        groups = importer.group_rows([row, dict(row, **{'class': 'related', 'candidate_id': 99})], self.inventory)
        self.assertEqual(list(groups), [5])
        metadata = importer.build_metadata(groups[5], self.inventory)
        record = importer.render_record(self.definition_header, metadata, self.sections)
        self.assertEqual(metadata['match'], 'partial')
        self.assertEqual(metadata['second_pass'], 'n/a')
        self.assertIn('% ATTEMPT_STATUS: unresolved\n', record)

    def test_new_local_target_requires_the_same_review_and_approval(self):
        row = dict(self.row, pool='C')
        with self.assertRaisesRegex(ValueError, 'explicit user approval'):
            importer.group_rows([row], self.inventory)
        groups = importer.group_rows([row], self.inventory, self.approval)
        self.assertEqual(list(groups), [5])
        deferred = dict(row, out_of_scope=True, **{'class': None, 'resolution': None})
        self.assertFalse(importer.group_rows([deferred], self.inventory))

    def test_joint_case_coverage_preserves_partial_paper_matches(self):
        inventory = deepcopy(self.inventory)
        second = deepcopy(inventory['families'][0]['manuscripts'][0])
        second['dir'] = 'Complementary-case-September-23-2026'
        for key in ('pdf_path', 'readme_path', 'source_tex_dir'):
            second[key] = second[key].replace(self.folder, second['dir'])
        inventory['families'][0]['manuscripts'].append(second)
        decision = {'match': 'full', 'resolution': 'proved', 'second_pass': 'agreed',
                    'justification': 'One paper handles k=5; the other handles every k>=6.'}
        first = dict(self.row, **{'class': 'partial', 'resolution': 'partial',
                                 'second_pass': 'n/a', 'joint_coverage': decision})
        other = dict(first, manuscript_dir=second['dir'])
        with self.assertRaisesRegex(ValueError, 'explicit user approval'):
            importer.group_rows([first, other], inventory)
        grouped = importer.group_rows([first, other], inventory, self.approval)
        self.assertTrue(all(row['class'] == 'partial' for row in grouped[5]))
        metadata = importer.build_metadata(grouped[5], inventory)
        self.assertEqual((metadata['match'], metadata['resolution'], metadata['second_pass']),
                         ('full', 'proved', 'agreed'))
        unreviewed = dict(decision, second_pass='pending')
        with self.assertRaisesRegex(ValueError, 'independent second pass'):
            importer.group_rows([dict(first, joint_coverage=unreviewed),
                                 dict(other, joint_coverage=unreviewed)], inventory, self.approval)

    def test_headers_sources_and_parentheses_are_deterministic(self):
        metadata = importer.build_metadata([self.row], self.inventory)
        record = importer.render_record(self.definition_header, metadata, self.sections)
        self.assertEqual(record.splitlines()[0], self.definition_header)
        self.assertEqual(record.splitlines()[1:3], ['% FIRST_POSTED: 2026-10-06', '% ATTEMPT_STATUS: solved'])
        self.assertEqual(json.loads(record.splitlines()[3].partition(': ')[2]), metadata)
        self.assertIn(r'CAT\%280\%29-spaces', record)
        self.assertIn(r'custom\_name.pdf', record)
        self.assertIn('/raw/' + importer.SOURCE_COMMIT + '/', record)
        self.assertIn('/blob/main/', record)
        self.assertIn('OAI:' + self.folder, record)
        self.assertIn('Manuscript page and citation', record)
        self.assertIn('Comparator Fillings.lean', record)
        self.assertEqual(record, importer.render_record(self.definition_header, metadata, self.sections))

    def test_statement_source_metadata_and_tex_links_preserve_paper_and_line(self):
        source = {'path': f'preprints/{self.folder}/build/source/main.tex',
                  'line': 57, 'label': 'thm:main_bound'}
        self.row['statement_sources'] = [source]
        self.manifest['eligible_paths'].append(source['path'])
        metadata = importer.build_metadata([self.row], self.inventory)
        self.assertEqual(metadata['families'][0]['manuscripts'][0]['statement_sources'], [source])
        pending, _ = self.prepare()
        record = next(iter(pending.values()))
        self.assertIn('/build/source/main.tex\\#L57}{thm:main\\_bound}', record)
        self.assertIn(r'CAT\%280\%29-spaces', record)
        self.assertIn('Statement source:', record)
        self.assertIn('/blob/' + importer.SOURCE_COMMIT + '/', record)

    def test_statement_source_import_rejects_cross_paper_and_noninteger_lines(self):
        source = {'path': f'preprints/{self.folder}/build/source/main.tex',
                  'line': 57, 'label': 'Theorem 1.1'}
        for invalid in (dict(source, line=True), dict(source, line=0),
                        dict(source, path='preprints/Other/build/main.tex'),
                        dict(source, extra='unknown')):
            row = dict(self.row, statement_sources=[invalid])
            with self.subTest(source=invalid), self.assertRaises(ValueError):
                importer.build_metadata([row], self.inventory)
        # Structural validity is insufficient when the pinned manifest lacks the file.
        self.row['statement_sources'] = [source]
        with self.assertRaisesRegex(ValueError, 'statement source.*manifest'):
            self.prepare()

    def test_mathematical_statement_preserves_tex_and_precedes_argument_outline(self):
        sections = importer.load_sections(self.summaries, 5)
        self.assertEqual(sections['mathematical_statement'], self.sections['mathematical_statement'])
        metadata = importer.build_metadata([self.row], self.inventory)
        record = importer.render_record(self.definition_header, metadata, sections)
        self.assertIn(self.sections['mathematical_statement'], record)
        self.assertLess(record.index(r'\subsection{Mathematical statement of the claimed result}'),
                        record.index(r'\subsection{Outline of the argument}'))
        self.assertIn('Theorem 1.1:', record)

    def test_legacy_summary_inputs_remain_readable(self):
        legacy = {key: value for key, value in self.sections.items()
                  if key != 'mathematical_statement'}
        self.summaries.write_text(json.dumps({'5': legacy}), encoding='utf-8')
        sections = importer.load_sections(self.summaries, 5)
        self.assertEqual(sections, legacy)
        metadata = importer.build_metadata([self.row], self.inventory)
        record = importer.render_record(self.definition_header, metadata, sections)
        self.assertNotIn(r'\subsection{Mathematical statement of the claimed result}', record)
        self.assertIn(r'\subsection{Outline of the argument}', record)

    def test_one_record_groups_papers_but_keeps_paper_theorem_references(self):
        inventory = deepcopy(self.inventory)
        paper = deepcopy(inventory['families'][0]['manuscripts'][0])
        paper.update(dir='Other-September-25-2026', title='Another scope',
                     pdf_path='preprints/Other-September-25-2026/main.pdf',
                     readme_path='preprints/Other-September-25-2026/README.md',
                     source_tex_dir='preprints/Other-September-25-2026/build/source', date='2026-09-25')
        inventory['families'][0]['manuscripts'].append(paper)
        partial = dict(self.row, manuscript_dir=paper['dir'], openai_theorem_ref='Proposition 2.4',
                       lean_covers_main_theorem=False, **{'class': 'partial', 'resolution': 'partial', 'second_pass': 'n/a'})
        groups = importer.group_rows([partial, self.row], inventory, self.approval)
        metadata = importer.build_metadata(groups[5], inventory)
        self.assertEqual(metadata['match'], 'full')
        family = metadata['families'][0]
        self.assertEqual([p['theorem_ref'] for p in family['manuscripts']], ['Proposition 2.4', 'Theorem 1.1'])
        self.assertFalse(family['lean']['covers_main_theorem'])
        self.assertEqual(len(family['lean']['comparators']), 2)

    def test_duplicate_rows_and_conflicting_resolutions_require_review(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate adjudication'):
            importer.group_rows([self.row, self.row], self.inventory, self.approval)
        with self.assertRaisesRegex(ValueError, 'Conflicting proof and disproof'):
            importer.build_metadata([self.row, dict(self.row, resolution='disproved')], self.inventory)

    def test_changed_existing_record_requires_new_version(self):
        pending, unchanged = self.prepare()
        self.assertEqual(unchanged, [])
        destination = self.catalog / 'openai/5.tex'
        self.assertEqual(list(pending), [destination])
        self.assertFalse(destination.exists())
        importer.apply_import(pending)
        pending, unchanged = self.prepare()
        self.assertFalse(pending)
        self.assertEqual(unchanged, [destination])
        before = destination.read_bytes()
        destination.write_bytes(before + b'% local revision\n')
        with self.assertRaisesRegex(ValueError, 'choose a new --version'):
            self.prepare()
        pending, _ = self.prepare(version=2)
        self.assertEqual(list(pending), [self.catalog / 'openai/5_v2.tex'])
        self.assertEqual(destination.read_bytes(), before + b'% local revision\n')

    def test_source_and_registry_failures_prevent_all_writes(self):
        self.write_exports([])
        with self.assertRaisesRegex(ValueError, 'Import missing statements'):
            self.prepare()
        self.assertFalse((self.catalog / 'openai').exists())
        self.write_exports([5])
        (self.export / 'display_order.json').write_text('[]', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'same unique IDs'):
            self.prepare()
        with patch.object(importer, 'git', return_value='f' * 40 + '\n'):
            with self.assertRaisesRegex(ValueError, 'differs from pinned SHA'):
                importer.validate_checkout(self.root, self.inventory)

    def test_summary_cannot_inject_metadata_or_arbitrary_links(self):
        for field in ('claim', 'mathematical_statement'):
            for text in ('% ATTEMPT_STATUS: solved', r'\input{elsewhere.tex}',
                         'See https://example.org/text', r'\subsection{Sources}'):
                sections = dict(self.sections, **{field: text})
                self.summaries.write_text(json.dumps({'5': sections}), encoding='utf-8')
                with self.subTest(field=field, text=text), self.assertRaises(ValueError):
                    importer.load_sections(self.summaries, 5)

    def test_no_copy_detects_paragraphs_while_omitting_metadata_sources_and_math(self):
        borrowed = 'every compact object admits a uniform quantitative filling estimate'
        originals = [('CONTENTS.md', 'We show that ' + borrowed + '.'),
                     ('paper.tex', r'\begin{theorem}' + borrowed + r'\end{theorem}')]
        record = r'\begin{document}\subsection{OpenAI claim}' + borrowed + r'\subsection{Sources}'
        failures = importer.check_no_copy(record, originals)
        self.assertTrue(failures)
        self.assertEqual({f['source'] for f in failures}, {'CONTENTS.md', 'paper.tex'})
        clean = ('% OPENAI_CLAIM: ' + borrowed + '\n' + r'\begin{document}'
                 + 'An original explanation. $' + borrowed + '$ '
                 + r'\subsection{Sources}' + borrowed + r'\end{document}')
        self.assertEqual(importer.check_no_copy(clean, originals), [])

    def test_no_copy_does_not_silently_exempt_paper_titles_or_common_phrases(self):
        title = 'The generalized quantitative form of a famous conjecture'
        originals = [('CONTENTS.md', title)]
        record = r'\begin{document}' + title
        self.assertTrue(importer.check_no_copy(record, originals, titles=[title]))
        exception = {'exceptions': [{'phrase': title, 'kind': 'conjecture_title',
                                     'justification': 'This is the complete catalogue conjecture title.'}]}
        self.assertEqual(importer.check_no_copy(record, originals, exception, [title]), [])
        exception['exceptions'][0]['phrase'] = 'every compact object admits a uniform quantitative filling estimate'
        with self.assertRaisesRegex(ValueError, 'known complete title'):
            importer.check_no_copy(record, originals, exception, [title])
        exception['exceptions'][0]['kind'] = 'proper_name'
        with self.assertRaisesRegex(ValueError, 'names, not ordinary prose'):
            importer.check_no_copy(record, originals, exception, [title])

    def test_pdf_and_root_build_theorems_are_required_originals(self):
        repo = self.root / 'source'
        repo.mkdir()
        (repo / 'CONTENTS.md').write_text('Catalogue prose.', encoding='utf-8')
        (repo / 'overview.tex').write_text('Overview prose.', encoding='utf-8')
        build = repo / f'preprints/{self.folder}/build'
        build.mkdir(parents=True)
        (build / 'paper.tex').write_text(r'\newtheorem{mainclaim}{Main theorem}'
                                       + r'\begin{mainclaim}A root build theorem.\end{mainclaim}', encoding='utf-8')
        metadata = importer.build_metadata([self.row], self.inventory)
        result = subprocess.CompletedProcess(['pdftotext'], 0, b'PDF manuscript prose.', b'')
        source_path = f'preprints/{self.folder}/build/paper.tex'
        blobs = {'CONTENTS.md': 'Catalogue prose.', 'overview.tex': 'Overview prose.',
                 source_path: (build/'paper.tex').read_text(),
                 f'preprints/{self.folder}/custom_name.pdf': b'pinned-pdf-bytes'}
        def pinned_git(repo, *args, binary=False):
            if args[0] == 'ls-tree':
                self.assertIn(importer.SOURCE_COMMIT, args)
                return source_path + '\n'
            self.assertEqual(args[0], 'show')
            self.assertTrue(args[1].startswith(importer.SOURCE_COMMIT + ':'))
            return blobs[args[1].split(':', 1)[1]]
        (build/'untracked.tex').write_text(r'\begin{theorem}Unpinned extra source.\end{theorem}')
        with patch.object(importer, 'git', side_effect=pinned_git), \
                patch.object(importer.subprocess, 'run', return_value=result) as extract:
            originals = importer.original_texts(metadata, self.inventory, repo)
        self.assertEqual(len(originals), 4)
        self.assertEqual(originals[-1][1], 'A root build theorem.')
        self.assertEqual(extract.call_args.kwargs['input'], b'pinned-pdf-bytes')
        self.assertEqual(extract.call_args.args[0][-2:], ['-', '-'])
        with patch.object(importer, 'git', side_effect=pinned_git), \
                patch.object(importer.subprocess, 'run', side_effect=FileNotFoundError):
            with self.assertRaisesRegex(ValueError, 'pdftotext is required'):
                importer.original_texts(metadata, self.inventory, repo)

    def test_title_casing_prose_cannot_bypass_no_copy_check(self):
        prose = 'Every compact object admits a uniform quantitative filling estimate'
        original = [('paper.tex', prose)]
        record = r'\begin{document}' + prose
        self.assertTrue(importer.check_no_copy(record, original))
        exceptions = {'exceptions': [{'phrase': prose.title(), 'kind': 'proper_name',
                                     'justification': 'Capitalization does not make this a proper name.'}]}
        with self.assertRaisesRegex(ValueError, 'names, not ordinary prose'):
            importer.check_no_copy(record, original, exceptions)

    def test_pinned_checkout_rejects_dirty_or_added_source_files(self):
        repo = self.root / 'pinned-source'
        repo.mkdir()
        def command(*args):
            return subprocess.run(['git', '-C', str(repo), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        command('init', '-q')
        command('config', 'user.email', 'fixture@example.org')
        command('config', 'user.name', 'Import test fixture')
        source = repo / 'paper.tex'
        source.write_text('Pinned theorem.')
        command('add', '.')
        command('commit', '-qm', 'Pinned fixture')
        inventory = {'source_commit': command('rev-parse', 'HEAD')}
        self.assertEqual(importer.validate_checkout(repo, inventory), repo)
        source.write_text('Modified theorem.')
        with self.assertRaisesRegex(ValueError, 'working-tree changes'):
            importer.validate_checkout(repo, inventory)
        command('restore', 'paper.tex')
        (repo / 'extra.tex').write_text('Unpinned theorem.')
        with self.assertRaisesRegex(ValueError, 'working-tree changes'):
            importer.validate_checkout(repo, inventory)

    def test_inventory_diff_uses_existing_commits_without_changing_checkout(self):
        repo = self.root / 'diff-source'
        repo.mkdir()

        def command(*args):
            return subprocess.run(['git', '-C', str(repo), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()

        command('init', '-q')
        command('config', 'user.email', 'fixture@example.org')
        command('config', 'user.name', 'Import test fixture')
        source = repo / f'preprints/{self.folder}'
        source.mkdir(parents=True)
        (source / 'README.md').write_text('Original manuscript.\n', encoding='utf-8')
        command('add', '.')
        command('commit', '-qm', 'Original fixture')
        before = command('rev-parse', 'HEAD')
        (source / 'README.md').write_text('Revised manuscript.\n', encoding='utf-8')
        added = repo / 'preprints/Added-manuscript'
        added.mkdir()
        (added / 'README.md').write_text('New manuscript.\n', encoding='utf-8')
        command('add', '.')
        command('commit', '-qm', 'Revision fixture')
        after = command('rev-parse', 'HEAD')
        command('checkout', '--detach', '-q', before)
        inventory = deepcopy(self.inventory)
        inventory['source_commit'] = before
        with patch.object(importer, 'SOURCE_COMMIT', before):
            report = importer.inventory_diff(inventory, repo, after)
        self.assertEqual(report['added'], ['Added-manuscript'])
        self.assertEqual(report['changed'], [self.folder])
        self.assertEqual(report['removed'], [])
        self.assertEqual(command('rev-parse', 'HEAD'), before)
        self.assertEqual(command('status', '--porcelain'), '')
        with self.assertRaisesRegex(ValueError, 'complete lowercase'):
            importer.inventory_diff(self.inventory, repo, '--all')


if __name__ == '__main__':
    unittest.main()
