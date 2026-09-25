"""Protect catalog identity, dated status, and moved attempt/review links."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import build_site


def catalog_record(problem_id='problem.example', rank=1):
    return {
        'problemId': problem_id,
        'canonicalTitle': 'An example question',
        'exactTarget': 'Determine whether every example has the stated property.',
        'primaryDomain': 'number_theory',
        'primaryDomainLabel': 'Number theory',
        'releaseRank': rank,
        'releaseStatus': 'open',
        'displayStatus': 'open_disputed_claim',
        'statusStatement': 'open',
        'statusQualification': 'The cited claim remains disputed.',
        'statusReviewedAt': '2026-09-22',
        'sources': [{'citation': 'Original statement', 'url': 'https://example.org/statement'}],
        'formalStatementSource': {'citation': 'Formal definition', 'url': 'https://example.org/formal'},
        'rankingEvidence': {'rankBand90': [1, 2]},
    }


def catalog():
    return {
        'records': [catalog_record(), catalog_record('problem.example.second', 2)],
        'recordCount': 2,
        'publicationId': 'example.v22',
        'releaseVersion': 22,
        'editionDate': '2026-09-22',
        'publicBoundary': 'Ranks are editorial importance, not proof evidence.',
    }


def mo_info():
    return {
        'title': 'Question &quot;one&quot;', 'score': 3, 'tags': ['example'],
        'creation_date': '2010-01-01', 'link': 'https://mathoverflow.net/questions/1',
    }


class OpenCatalogValidationTests(unittest.TestCase):
    def load(self, snapshot):
        build_site.validate_open_problems_catalog(snapshot)
        return snapshot

    def test_shipped_catalog_has_500_unique_stable_ids_and_complete_ranks(self):
        snapshot = build_site.load_open_problems_catalog()
        self.assertEqual(snapshot['recordCount'], 500)
        self.assertTrue(all(r['definitionTeX'] and r['definitionFile'].endswith('.tex') for r in snapshot['records']))
        self.assertEqual({r['releaseRank'] for r in snapshot['records']}, set(range(1, 501)))
        self.assertEqual(len({r['problemId'] for r in snapshot['records']}), 500)

    def test_missing_definitions_mismatched_numbers_and_incomplete_documents_fail(self):
        original = (build_site.OPEN_PROBLEMS_PATH / '1.tex').read_text()
        for content, filename in [(original.replace('TOP_PROBLEM:', 'OTHER:'), '1.tex'),
                                  (original, '2.tex'),
                                  (original.replace('\\subsection{Definitions', '\\subsection{Missing'), '1.tex'),
                                  (original.replace('\\end{document}', ''), '1.tex')]:
            with self.subTest(filename=filename), TemporaryDirectory() as directory:
                folder = Path(directory)
                (folder / filename).write_text(content)
                with patch.object(build_site, 'OPEN_PROBLEMS_PATH', folder), self.assertRaises(ValueError):
                    build_site.load_open_problems_catalog()

    def test_verbatim_notebook_definitions_sources_and_research_are_separate(self):
        source = (build_site.OPEN_PROBLEMS_PATH / 'GPT_6_Astra_Ultra' / '1.tex').read_text()
        record = build_site.parse_numbered_problem_tex(source)
        self.assertIn('A language is a set $L', record['definitionTeX'])
        self.assertIn(r'\exists y\in\{0,1\}^{\le p(|x|)}', record['definitionTeX'])
        self.assertNotIn('cataloguescope', record['definitionTeX'])
        self.assertNotIn('Research attempt', record['definitionTeX'])
        self.assertNotIn('Current frontier', record['exactTarget'])
        self.assertEqual(record['exactTarget'],
                         'Does an efficient way to check a proposed yes-answer always imply an efficient way to decide whether the answer is yes?')
        self.assertIn('Current frontier and source audit', record['researchTeX'])
        self.assertIn('Exploratory approach with unresolved gap', record['researchTeX'])
        self.assertGreater(len(record['sources']), 4)
        self.assertEqual(record['sources'][0]['url'], 'https://www.claymath.org/library/monographs/MPPc.pdf')
        self.assertIn(r'\href{https://www.claymath.org/library/monographs/MPPc.pdf}{[S1]}', record['definitionTeX'])
        self.assertNotRegex(record['definitionTeX'] + record['researchTeX'],
                            r'\\(?:sref|eref|hypertarget|needspace|raggedright)\b')

    def test_custom_math_macros_expand_before_subscripts_and_keep_longer_commands(self):
        source = (build_site.OPEN_PROBLEMS_PATH / '151.tex').read_text()
        source = source.replace(r'\subsection{Short English statement}',
                                r'$\A_k,\E_{x},\Q,\Re,\Gamma$' + '\n'
                                + r'\subsection{Short English statement}')
        record = build_site.parse_numbered_problem_tex(source)
        self.assertIn(r'{\mathbb{A}}_k,{\mathbb{E}}_{x},{\mathbb{Q}},\Re,\Gamma',
                      record['definitionTeX'])

    def test_numbered_definitions_have_no_embedded_research_attempts(self):
        snapshot = build_site.load_open_problems_catalog()
        self.assertTrue(all(r['researchTeX'] is None for r in snapshot['records']))

    def test_catalogue_quotation_with_nested_and_escaped_braces_is_omitted(self):
        source = (build_site.OPEN_PROBLEMS_PATH / '15.tex').read_text()
        source = source.replace(r'\subsection{Short English statement}',
                                r'\cataloguescope{Hidden {nested} quotation with \{escaped\} sets.}'
                                '\n' + r'\subsection{Short English statement}')
        record = build_site.parse_numbered_problem_tex(source)
        self.assertNotIn('Hidden', record['definitionTeX'])
        self.assertIn('Short English statement', record['definitionTeX'])
        self.assertIsNone(record['researchTeX'])

    def test_empty_review_date_is_preserved_without_inventing_evidence(self):
        snapshot = catalog()
        snapshot['records'][0]['statusReviewedAt'] = ''
        self.assertEqual(self.load(snapshot), snapshot)

    def test_duplicate_ids_and_ranks_fail_instead_of_overwriting_records(self):
        for key, expected in [('problemId', 'Duplicate open problem ID'),
                              ('releaseRank', 'Duplicate open problem rank')]:
            snapshot = catalog()
            snapshot['records'][1][key] = snapshot['records'][0][key]
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, expected):
                self.load(snapshot)

    def test_invalid_ranks_ids_sources_and_record_counts_fail_explicitly(self):
        cases = [
            ('problemId', '../outside'), ('problemId', 'mo:1'), ('problemId', ''),
            ('releaseRank', True), ('releaseRank', '1'), ('releaseRank', 0),
            ('releaseRank', 3), ('sources', []), ('exactTarget', ''),
        ]
        for key, value in cases:
            snapshot = catalog()
            snapshot['records'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.load(snapshot)
        for count in [1, True, '2']:
            snapshot = catalog()
            snapshot['recordCount'] = count
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, 'recordCount'):
                self.load(snapshot)


class OpenProblemsBuildTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.patchers = [
            patch.object(build_site, 'BASE_DIR', self.root),
            patch.object(build_site, 'ATTACKS_DIR', self.root / 'attacks'),
            patch.object(build_site, 'REVIEWS_DIR', self.root / 'reviews'),
            patch.object(build_site, 'DATA_DIR', self.root / 'docs' / 'data'),
            patch.object(build_site, 'get_file_date', return_value='2026-09-24'),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        return target

    def statement_only(self):
        return '% COLLECTION_METADATA: ' + json.dumps({
            'schema_version': 1, 'kind': 'statement_only',
            'source_urls': ['https://example.org/formal'],
            'independently_reviewed': False,
        }) + '\nFULL SOLUTION\nCOMPLETION ESTIMATE: 100%'

    def test_stable_ids_load_versioned_attempts_without_overwriting_snapshot_status(self):
        self.write('attacks/open_problems/Example_Model/problem.example_v2.tex',
                   'UNRESOLVED\nCOMPLETION ESTIMATE: 25%')
        self.write('attacks/open_problems/Example_Model/problem.example.tex',
                   'FULL SOLUTION\nCOMPLETION ESTIMATE: 70%')
        self.write('reviews/open_problems/problem.example.json', '{"status": "incorrect"}')
        snapshot = catalog()
        result = build_site.build_open_problems_data({}, snapshot)['problem.example']
        self.assertEqual(result['status'], 'open_disputed_claim')
        self.assertEqual(result['release_status'], 'open')
        self.assertEqual(result['llm_status'], 'unresolved')
        self.assertEqual(result['completion'], 70)
        self.assertEqual([a['version'] for a in result['attacks']], [1, 2])
        self.assertEqual(result['attacks'][1]['file_path'],
                         'attacks/open_problems/Example_Model/problem.example_v2.tex')
        self.assertEqual(result['review']['status'], 'incorrect')
        self.assertNotIn('catalog_record', result)
        self.assertEqual(result['link'], 'https://example.org/formal')
        self.assertNotIn('edition_date', result)
        self.assertEqual(result['status_reviewed_at'], '2026-09-22')

    def test_numbered_definitions_are_not_attempts_but_model_writeups_are(self):
        self.write('attacks/open_problems/top_problems/1.tex', 'Definition only')
        self.write('attacks/open_problems/top_problems/Example_Model/1_v2.tex',
                   'UNRESOLVED\nCOMPLETION ESTIMATE: 15%')
        self.write('attacks/open_problems/erdos/Example_Model/1.tex', 'UNRESOLVED')
        result = build_site.build_open_problems_data({}, catalog())
        self.assertEqual(len(result['problem.example']['attacks']), 1)
        self.assertEqual(result['problem.example']['attacks'][0]['version'], 2)
        self.assertEqual(result['problem.example']['completion'], 15)
        self.assertEqual(result['problem.example.second']['attacks'], [])
        self.assertEqual(result['problem.example.second']['llm_status'], 'none')

    def test_unknown_numbered_attempt_fails_explicitly(self):
        self.write('attacks/open_problems/top_problems/Model/501.tex', 'UNRESOLVED')
        with self.assertRaisesRegex(ValueError, 'Unknown ranked'):
            build_site.build_open_problems_data({}, catalog())

    def test_research_from_numbered_tex_is_shown_as_an_unresolved_notebook(self):
        snapshot = catalog()
        snapshot['records'][0].update({
            'researchTeX': r'\subsection{Research attempt} Conditional reduction.',
            'definitionFile': 'attacks/open_problems/top_problems/1.tex',
        })
        result = build_site.build_open_problems_data({}, snapshot)['problem.example']
        self.assertEqual(result['llm_status'], 'unresolved')
        self.assertEqual(len(result['attacks']), 1)
        self.assertEqual(result['attacks'][0]['model'], 'Research notebook')
        self.assertEqual(result['attacks'][0]['file_path'], snapshot['records'][0]['definitionFile'])
        self.assertNotIn('completion', result)

    def test_statement_only_records_and_no_attempts_have_no_claim_or_completion(self):
        self.write('attacks/open_problems/Statement_Model/problem.example.tex', self.statement_only())
        snapshot = catalog()
        snapshot['records'][0]['statusReviewedAt'] = ''
        result = build_site.build_open_problems_data({}, snapshot)
        for problem in result.values():
            self.assertEqual(problem['llm_status'], 'none')
            self.assertNotIn('completion', problem)
        self.assertIsNone(result['problem.example']['status_reviewed_at'])
        self.assertEqual(result['problem.example']['attacks'][0]['entry_kind'], 'statement_only')

    def test_ids_with_internal_periods_work_and_ranks_do_not_identify_attempts(self):
        self.write('attacks/open_problems/Model/problem.example.second.tex', 'UNRESOLVED')
        snapshot = catalog()
        snapshot['records'][0]['releaseRank'], snapshot['records'][1]['releaseRank'] = 2, 1
        result = build_site.build_open_problems_data({}, snapshot)
        self.assertEqual(list(result), ['problem.example.second', 'problem.example'])
        self.assertEqual(len(result['problem.example.second']['attacks']), 1)
        self.assertEqual(result['problem.example']['attacks'], [])

    def test_unknown_and_invalid_ranked_tex_filenames_fail_instead_of_disappearing(self):
        for filename in ['1.tex', 'problem.unknown.tex', 'problem.example_v0.tex',
                         'problem.example_title.tex']:
            path = self.write(f'attacks/open_problems/Model/{filename}', 'UNRESOLVED')
            with self.subTest(filename=filename), self.assertRaisesRegex(ValueError, 'Unknown ranked'):
                build_site.build_open_problems_data({}, catalog())
            path.unlink()

    def test_moved_mo_paths_and_legacy_review_remain_usable(self):
        self.write('attacks/open_problems/mo/Example_Model/1-question_v2.tex',
                   'UNRESOLVED\nCOMPLETION ESTIMATE: 12%')
        self.write('attacks/mo/Example_Model/1-obsolete.tex', 'FULL SOLUTION')
        self.write('reviews/mo/1.json', '{"status": "incorrect"}')
        with patch.object(build_site, 'load_mo_problems_list', return_value={'1': mo_info()}):
            mo = build_site.build_mo_data()
        self.assertEqual(len(mo['1']['attacks']), 1)
        self.assertEqual(mo['1']['attacks'][0]['file_path'],
                         'attacks/open_problems/mo/Example_Model/1-question_v2.tex')
        self.assertEqual(mo['1']['review']['status'], 'incorrect')
        result = build_site.build_open_problems_data(mo, catalog())
        self.assertEqual(set(result), {'problem.example', 'problem.example.second', 'mo:1'})
        self.assertEqual(result['mo:1']['mo_id'], '1')
        self.assertEqual(result['mo:1']['title'], 'Question "one"')
        self.assertIsNone(result['mo:1']['rank'])
        self.assertEqual(result['mo:1']['status'], 'unreviewed')
        self.assertEqual(result['mo:1']['llm_status'], 'unresolved')
        self.assertEqual(result['mo:1']['review'], mo['1']['review'])
        self.assertEqual(mo['1']['id'], '1')
        self.assertEqual(mo['1']['status'], 'unresolved')

    def test_new_mo_review_location_takes_precedence(self):
        self.write('reviews/mo/1.json', '{"status": "incorrect"}')
        self.write('reviews/open_problems/mo/1.json', '{"status": "incomplete"}')
        with patch.object(build_site, 'load_mo_problems_list', return_value={'1': mo_info()}):
            mo = build_site.build_mo_data()
        self.assertEqual(mo['1']['review']['status'], 'incomplete')

    def test_stats_and_js_exports_count_actual_attempts_across_both_collections(self):
        self.write('attacks/open_problems/Statement_Model/problem.example.tex', self.statement_only())
        self.write('attacks/open_problems/Actual_Model/problem.example.second.tex', 'UNRESOLVED')
        mo = {'1': {'id': '1', **mo_info(), 'attacks': [{
            'model': 'MO model', 'status': 'unresolved', 'completion': 30,
        }]}, '2': {'id': '2', **mo_info(), 'attacks': [{
            'model': 'Statement model', 'status': 'unresolved', 'completion': 0,
            'entry_kind': 'statement_only',
        }]}}
        snapshot = catalog()
        problems = build_site.build_open_problems_data(mo, snapshot)
        with patch.object(build_site, 'load_erdos_status', return_value={'problems': {}}):
            build_site.generate_js_data({}, mo, problems, snapshot)
        stats_js = (build_site.DATA_DIR / 'stats.js').read_text(encoding='utf-8')
        stats = json.loads(stats_js.removeprefix('var siteStats = ').removesuffix(';\n'))
        self.assertEqual(stats['open_problems'], {
            'total_problems': 4, 'ranked_total': 2, 'mo_total': 2,
            'with_attacks': 2, 'ranked_with_attacks': 1, 'models': ['Actual Model', 'MO model'],
        })
        self.assertEqual(stats['mo']['with_attacks'], 1)
        self.assertEqual(stats['mo']['models'], ['MO model'])
        js = (build_site.DATA_DIR / 'open_problems_data.js').read_text(encoding='utf-8')
        self.assertIn('window.OPEN_PROBLEMS_DATA = openProblems;', js)
        self.assertIn('window.OPEN_PROBLEMS_CATALOG = openProblemsCatalog;', js)
        exported = json.loads(js.removeprefix('var openProblems = ').split(';\n', 1)[0])
        self.assertEqual(exported, problems)
        self.assertTrue((build_site.DATA_DIR / 'mo_data.js').is_file())

    def test_detail_json_matches_index_and_html_data_urls_follow_content_changes(self):
        self.write('docs/problem.html', '<script src="data/open_problems_data.js"></script>')
        self.write('docs/index.html', '<script src="data/open_problems_data.js?v=old"></script>')
        snapshot = catalog()
        snapshot['records'][0]['definitionTeX'] = 'Definition with $x^2$'
        problems = build_site.build_open_problems_data({}, snapshot)
        with patch.object(build_site, 'load_erdos_status', return_value={'problems': {}}):
            build_site.generate_js_data({}, {}, problems, snapshot)
            first = (self.root / 'docs/problem.html').read_text()
            self.assertEqual(first, (self.root / 'docs/index.html').read_text())
            self.assertRegex(first, r'open_problems_data\.js\?v=[0-9a-f]{16}')
            record = json.loads((build_site.DATA_DIR / 'top_problems/1.json').read_text())
            self.assertEqual(record, problems['problem.example'])
            build_site.generate_js_data({}, {}, problems, snapshot)
            self.assertEqual(first, (self.root / 'docs/problem.html').read_text())
            problems['problem.example']['definition_tex'] = 'Revised definition'
            build_site.generate_js_data({}, {}, problems, snapshot)
            self.assertNotEqual(first, (self.root / 'docs/problem.html').read_text())


class RepositoryMigrationTests(unittest.TestCase):
    def test_real_catalog_preserves_all_legacy_mo_links_and_namespaces(self):
        with patch.object(build_site, 'get_file_date', return_value='2026-09-24'):
            mo = build_site.build_mo_data()
            problems = build_site.build_open_problems_data(mo)
        self.assertEqual(len(mo), 100)
        self.assertEqual(len(problems), 600)
        self.assertEqual(sum(p['collection'] == 'ranked' for p in problems.values()), 500)
        self.assertEqual(sum(bool(p['attacks']) for p in mo.values()), 93)
        for qid, problem in mo.items():
            self.assertEqual(problem['attacks'], problems[f'mo:{qid}']['attacks'])
            self.assertIsNone(problems[f'mo:{qid}']['rank'])
            for attack in problem['attacks']:
                self.assertTrue(attack['file_path'].startswith('attacks/open_problems/mo/'))
                self.assertTrue((build_site.BASE_DIR / attack['file_path']).is_file())


if __name__ == '__main__':
    unittest.main()
