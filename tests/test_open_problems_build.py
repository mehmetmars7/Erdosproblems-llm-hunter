"""Protect catalog identity, dated status, and moved attempt/review links."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import build_site


def catalog_record(problem_id=1):
    return {
        'id': problem_id,
        'problem_number': f'TEST-{problem_id}',
        'title': 'An example question',
        'exactTarget': 'Determine whether every example has the stated property.',
        'category': {'id': 3, 'name': 'number_theory', 'display_name': 'Number theory'},
        'status': 'open_disputed_claim',
        'statusStatement': 'open',
        'statusQualification': 'The cited claim remains disputed.',
        'statusReviewedAt': '2026-09-22',
        'sources': [{'citation': 'Original statement', 'url': 'https://example.org/statement'}],
        'external_url': f'https://www.unsolvedmath.com/problems/{problem_id}',
    }


def catalog():
    return {
        'records': [catalog_record(), catalog_record(20000601)],
        'recordCount': 2,
        'displayOrder': [1, 20000601],
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

    def test_external_code_routes_and_legacy_aliases_preserve_identity(self):
        snapshot = catalog()
        first, second = snapshot['records']
        first.update(problem_number='MPP-001', legacy_ids=['problem.p-versus-np'],
                     external_url='https://www.unsolvedmath.com/problems/MPP-001')
        self.load(snapshot)
        for bad_url in ['https://www.unsolvedmath.com/problems/MPP-006',
                        'https://www.unsolvedmath.com.evil/problems/MPP-001',
                        'javascript:alert(1)']:
            with self.subTest(url=bad_url), patch.dict(first, external_url=bad_url):
                with self.assertRaisesRegex(ValueError, 'external URL'):
                    self.load(snapshot)
        second['legacy_ids'] = ['problem.p-versus-np']
        with self.assertRaisesRegex(ValueError, 'Duplicate legacy ID'):
            self.load(snapshot)
        second['legacy_ids'] = ['../1']
        with self.assertRaisesRegex(ValueError, 'Invalid legacy ID'):
            self.load(snapshot)

    def test_shipped_catalog_has_unique_canonical_ids_and_complete_display_order(self):
        snapshot = build_site.load_open_problems_catalog()
        registry = json.loads(build_site.UNSOLVEDMATH_PATH.read_text())
        self.assertEqual(snapshot['recordCount'], len(registry))
        self.assertTrue(all(r['definitionTeX'] and r['definitionFile'].endswith('.tex') for r in snapshot['records']))
        self.assertEqual(len(set(snapshot['displayOrder'])), snapshot['recordCount'])
        self.assertEqual(snapshot['displayOrder'][3], 6)
        self.assertEqual(len({r['id'] for r in snapshot['records']}), snapshot['recordCount'])

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

    def test_registry_titles_categories_and_sparse_order_are_authoritative(self):
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            registry = [catalog_record(6), catalog_record(20000601)]
            registry[0].update(title='Hodge Conjecture', statement='UPSTREAM TEXT MUST NOT BE COPIED')
            registry[1]['external_url'] = None
            (folder / 'problems.json').write_text(json.dumps(registry))
            (folder / 'display_order.json').write_text('[20000601, 6]')
            for record in registry:
                text = ('% TOP_PROBLEM: ' + json.dumps({'id': record['id'], 'title': 'Old title'})
                        + '\n' + r'''\begin{document}
\section{Own exposition}
\subsection{Definitions and mathematical statement}
Our independently authored mathematical statement.
\subsection{Short English statement}
Our own summary.
\subsection{Sources}
\begin{itemize}
\item[S1] Primary source. \url{https://example.org/statement}
\item[P1] Printed source with no public URL.
\end{itemize}
\end{document}
''')
                (folder / f"{record['id']}.tex").write_text(text)
            with patch.object(build_site, 'OPEN_PROBLEMS_PATH', folder), \
                    patch.object(build_site, 'UNSOLVEDMATH_PATH', folder / 'problems.json'), \
                    patch.object(build_site, 'DISPLAY_ORDER_PATH', folder / 'display_order.json'), \
                    patch.object(build_site, 'ATTACKS_DIR', folder / 'absent'):
                snapshot = build_site.load_open_problems_catalog()
                result = build_site.build_open_problems_data({}, snapshot)
            self.assertEqual(list(result), ['20000601', '6'])
            self.assertEqual(result['6']['id'], 6)
            self.assertEqual(result['6']['rank'], 2)
            self.assertEqual(result['6']['title'], 'Hodge Conjecture')
            self.assertEqual(result['6']['domain'], 'number_theory')
            self.assertEqual(result['6']['definition_file'], 'attacks/open_problems/top_problems/6.tex')
            self.assertNotIn('UPSTREAM TEXT', json.dumps(result))
            self.assertIsNone(result['20000601']['external_url'])
            self.assertIsNone(result['6']['sources'][1]['url'])
            self.assertIn('Printed source', result['6']['sources'][1]['citation'])

    def test_verbatim_notebook_definitions_sources_and_research_are_separate(self):
        source = (build_site.OPEN_PROBLEMS_PATH / 'gpt_6_astra_ultra' / '1.tex').read_text()
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
        source = (build_site.OPEN_PROBLEMS_PATH / '1.tex').read_text()
        source = source.replace(r'\subsection{Short English statement}',
                                r'$\A_k,\E_{x},\Q,\Re,\Gamma$' + '\n'
                                + r'\subsection{Short English statement}')
        record = build_site.parse_numbered_problem_tex(source)
        self.assertIn(r'{\mathbb{A}}_k,{\mathbb{E}}_{x},{\mathbb{Q}},\Re,\Gamma',
                      record['definitionTeX'])

    def test_hodge_source_notation_survives_preamble_removal(self):
        source = (build_site.OPEN_PROBLEMS_PATH / 'gpt_6_astra_pro' / '6.tex').read_text()
        record = build_site.parse_numbered_problem_tex(source, require_source_urls=False)
        for field in ('definitionTeX', 'researchTeX', 'documentTeX'):
            self.assertNotRegex(record[field], r'\\(?:cl|CH|Res|PD|Tr)\b')
            self.assertIn(r'\operatorname{cl}', record[field])
            self.assertIn(r'\operatorname{CH}', record[field])
        self.assertIn(r'\boxed{', record['definitionTeX'])
        self.assertIn(r'\operatorname{Hdg}^{2p}(X)', record['definitionTeX'])

    def test_local_notation_handles_nested_aliases_and_operator_declarations(self):
        macros = build_site.tex_notation_macros(r'''
% \newcommand{\ignored}{wrong}
\newcommand*{\field}{\mathbb Q}
\newcommand\closure{\overline{\field}}
\DeclareMathOperator{\cycle}{cl}
\DeclareMathOperator*{\limitop}{lim}
\renewcommand{\field}{\mathbb C} % source definition wins
\providecommand{\field}{wrong}
\newcommand{\parameterized}[1]{#1}
''', {})
        rendered = build_site.expand_tex_notation(
            r'\cycle(\closure)_p + \field + \cycleLong + \parameterized{x}', macros)
        self.assertIn(r'{\operatorname{cl}}', rendered)
        self.assertIn(r'\overline{{\mathbb{C}}}', rendered)
        self.assertNotIn(r'\mathbb{Q}', rendered)
        self.assertIn(r'\cycleLong', rendered)
        self.assertIn(r'\parameterized{x}', rendered)
        self.assertNotIn('ignored', macros)
        self.assertIn(r'\operatorname*{lim}', macros['limitop'])
        self.assertEqual(build_site.tex_notation_macros('', {}), {})
        self.assertEqual(build_site.tex_notation_macros(
            r'\providecommand{\R}{\mathcal{R}}', {'R': r'{\mathbb{R}}'})['R'],
            r'{\mathcal{R}}')

    def test_notation_preserves_code_escaped_commands_and_detects_cycles(self):
        macros = build_site.tex_notation_macros(r'\newcommand{\CH}{\operatorname{CH}}', {})
        source = r'''\verb|\CH| \\CH
\begin{Code}
literal = "\CH"
\end{Code}
$\CH^p(X)$'''
        rendered = build_site.expand_tex_notation(source, macros)
        self.assertIn(r'\verb|\CH| \\CH', rendered)
        self.assertIn('literal = "\\CH"', rendered)
        self.assertIn(r'${\operatorname{CH}}^p(X)$', rendered)
        with self.assertRaisesRegex(ValueError, 'Recursive'):
            build_site.tex_notation_macros(r'\newcommand{\aa}{\bb}\newcommand{\bb}{\aa}', {})

    def test_attempt_with_trailing_comments_and_print_only_reference(self):
        source = r'''\begin{document}
\section{Example}
\subsection{Definitions and mathematical statement}
The target statement.
\subsection{Short English statement}
Does it hold?
\subsection{Research attempt: a restricted case}
Partial progress using \eref{1}{1}; the general case is unresolved.
Additional provenance: \srcref{A1}. Statement: \src{S1}.
\subsection{Sources}
\begin{itemize}
\item[S1] Statement. \url{https://example.org/statement}
\item[E1] A printed theorem, Journal 12 (1983), 1--10.
\item[A1] An offline computation transcript.
\end{itemize}
\end{document}
% Archived material follows, including literal \end{document} text.
% This comment must not appear on the website.
'''
        with self.assertRaisesRegex(ValueError, 'Missing URL for source E1'):
            build_site.parse_numbered_problem_tex(source)
        record = build_site.parse_numbered_problem_tex(source, require_source_urls=False)
        self.assertIn('Research attempt: a restricted case', record['researchTeX'])
        self.assertIn('Partial progress using [E1]', record['researchTeX'])
        self.assertIn('Additional provenance: [A1]', record['researchTeX'])
        self.assertIn(r'Statement: \href{https://example.org/statement}{[S1]}', record['researchTeX'])
        self.assertIsNone(record['sources'][1]['url'])
        self.assertNotIn('Archived material', record['documentTeX'])
        self.assertNotIn('Partial progress', record['definitionTeX'])
        with self.assertRaisesRegex(ValueError, 'Missing local source E2'):
            build_site.parse_numbered_problem_tex(source.replace(r'\eref{1}{1}', r'\eref{1}{2}'),
                                                 require_source_urls=False)

    def test_numbered_definitions_have_no_embedded_research_attempts(self):
        snapshot = build_site.load_open_problems_catalog()
        self.assertTrue(all(r['researchTeX'] is None for r in snapshot['records']))

    def test_catalogue_quotation_with_nested_and_escaped_braces_is_omitted(self):
        source = (build_site.OPEN_PROBLEMS_PATH / '1.tex').read_text()
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

    def test_duplicate_ids_and_display_entries_fail_instead_of_overwriting(self):
        snapshot = catalog()
        snapshot['records'][1]['id'] = 1
        with self.assertRaisesRegex(ValueError, 'Duplicate open problem ID'):
            self.load(snapshot)
        snapshot = catalog()
        snapshot['displayOrder'] = [1, 1]
        with self.assertRaisesRegex(ValueError, 'Duplicate open problem ID in display order'):
            self.load(snapshot)

    def test_invalid_ids_sources_and_record_counts_fail_explicitly(self):
        cases = [('id', '../outside'), ('id', 'mo:1'), ('id', ''), ('id', True),
                 ('id', '1'), ('id', 0), ('id', 2**53), ('sources', []), ('exactTarget', '')]
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
        for order in [[1], [1, 9], [1, True], [1, '20000601']]:
            snapshot = catalog()
            snapshot['displayOrder'] = order
            with self.subTest(order=order), self.assertRaises(ValueError):
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
        self.write('attacks/open_problems/Example_Model/1_v2.tex',
                   'UNRESOLVED\nCOMPLETION ESTIMATE: 25%')
        self.write('attacks/open_problems/Example_Model/1.tex',
                   'FULL SOLUTION\nCOMPLETION ESTIMATE: 70%')
        self.write('reviews/open_problems/1.json', '{"status": "incorrect"}')
        snapshot = catalog()
        result = build_site.build_open_problems_data({}, snapshot)['1']
        self.assertEqual(result['status'], 'open_disputed_claim')
        self.assertEqual(result['llm_status'], 'unresolved')
        self.assertEqual(result['completion'], 70)
        self.assertEqual([a['version'] for a in result['attacks']], [1, 2])
        self.assertEqual(result['attacks'][1]['file_path'],
                         'attacks/open_problems/Example_Model/1_v2.tex')
        self.assertEqual(result['review']['status'], 'incorrect')
        self.assertNotIn('catalog_record', result)
        self.assertEqual(result['link'], 'https://www.unsolvedmath.com/problems/1')
        self.assertNotIn('edition_date', result)
        self.assertEqual(result['status_reviewed_at'], '2026-09-22')

    def test_numbered_definitions_are_not_attempts_but_model_writeups_are(self):
        self.write('attacks/open_problems/top_problems/1.tex', 'Definition only')
        self.write('attacks/open_problems/top_problems/Example_Model/1_v2.tex',
                   'UNRESOLVED\nCOMPLETION ESTIMATE: 15%')
        self.write('attacks/open_problems/erdos/Example_Model/1.tex', 'UNRESOLVED')
        result = build_site.build_open_problems_data({}, catalog())
        self.assertEqual(len(result['1']['attacks']), 1)
        self.assertEqual(result['1']['attacks'][0]['version'], 2)
        self.assertEqual(result['1']['completion'], 15)
        self.assertEqual(result['20000601']['attacks'], [])
        self.assertEqual(result['20000601']['llm_status'], 'none')

    def test_misfiled_attempt_metadata_cannot_attach_to_another_problem(self):
        self.write('attacks/open_problems/top_problems/Model/1.tex',
                   '% TOP_PROBLEM: {"id": 20000601}\nUNRESOLVED')
        with self.assertRaisesRegex(ValueError, 'Attempt filename must match its canonical ID'):
            build_site.build_open_problems_data({}, catalog())

    def test_unknown_numbered_attempt_fails_explicitly(self):
        self.write('attacks/open_problems/top_problems/Model/501.tex', 'UNRESOLVED')
        with self.assertRaisesRegex(ValueError, 'Unknown ranked'):
            build_site.build_open_problems_data({}, catalog())

    def test_lowercase_astra_folders_preserve_model_paths_and_exclude_unlisted_files(self):
        for model in ['gpt_6_astra_ultra', 'gpt_6_astra_pro']:
            self.write(f'attacks/open_problems/top_problems/{model}/1.tex', 'UNRESOLVED')
        self.write('attacks/open_problems/top_problems/gpt_6_astra_pro/unlisted/501.tex',
                   'Outside the ranked catalogue')
        result = build_site.build_open_problems_data({}, catalog())['1']
        self.assertEqual({a['model'] for a in result['attacks']},
                         {'gpt 6 astra ultra', 'gpt 6 astra pro'})
        self.assertEqual({a['file_path'] for a in result['attacks']},
                         {'attacks/open_problems/top_problems/gpt_6_astra_ultra/1.tex',
                          'attacks/open_problems/top_problems/gpt_6_astra_pro/1.tex'})

    def test_numbered_attempt_keeps_declared_partial_status_after_display_conversion(self):
        content = r'''% ATTEMPT_STATUS: partial
\begin{document}
\section{Example formalization}
\subsection{Definitions and mathematical statement}
An exact statement.
\subsection{Short English statement}
Does the statement hold?
\subsection{Research attempt}
A checked restricted case, with the general case missing.
\subsection{Sources}
\begin{itemize}
\item[S1] Complete Lean source. \url{https://example.org/Main.lean}
\end{itemize}
\end{document}
'''
        self.write('attacks/open_problems/top_problems/Model/1.tex', content)
        problem = build_site.build_open_problems_data({}, catalog())['1']
        attack = problem['attacks'][0]
        self.assertNotIn('ATTEMPT_STATUS', attack['raw'])
        self.assertEqual(attack['status'], 'unresolved')
        self.assertEqual(problem['llm_status'], 'unresolved')
        self.assertEqual(problem['status'], 'open_disputed_claim')

    def test_research_from_numbered_tex_is_shown_as_an_unresolved_notebook(self):
        snapshot = catalog()
        snapshot['records'][0].update({
            'researchTeX': r'\subsection{Research attempt} Conditional reduction.',
            'definitionFile': 'attacks/open_problems/top_problems/1.tex',
        })
        result = build_site.build_open_problems_data({}, snapshot)['1']
        self.assertEqual(result['llm_status'], 'unresolved')
        self.assertEqual(len(result['attacks']), 1)
        self.assertEqual(result['attacks'][0]['model'], 'Research notebook')
        self.assertEqual(result['attacks'][0]['file_path'], snapshot['records'][0]['definitionFile'])
        self.assertNotIn('completion', result)

    def test_statement_only_records_and_no_attempts_have_no_claim_or_completion(self):
        self.write('attacks/open_problems/Statement_Model/1.tex', self.statement_only())
        snapshot = catalog()
        snapshot['records'][0]['statusReviewedAt'] = ''
        result = build_site.build_open_problems_data({}, snapshot)
        for problem in result.values():
            self.assertEqual(problem['llm_status'], 'none')
            self.assertNotIn('completion', problem)
        self.assertIsNone(result['1']['status_reviewed_at'])
        self.assertEqual(result['1']['attacks'][0]['entry_kind'], 'statement_only')

    def test_sparse_ids_work_and_display_order_does_not_identify_attempts(self):
        self.write('attacks/open_problems/Model/20000601.tex', 'UNRESOLVED')
        snapshot = catalog()
        snapshot['displayOrder'].reverse()
        result = build_site.build_open_problems_data({}, snapshot)
        self.assertEqual(list(result), ['20000601', '1'])
        self.assertEqual(len(result['20000601']['attacks']), 1)
        self.assertEqual(result['1']['attacks'], [])

    def test_reordering_changes_only_rank_not_attempts_urls_or_detail_filenames(self):
        self.write('attacks/open_problems/top_problems/Model/20000601.tex',
                   '% FIRST_POSTED: 2026-01-09\nUNRESOLVED')
        snapshot = catalog()
        original = build_site.build_open_problems_data({}, snapshot)
        snapshot['displayOrder'].reverse()
        reordered = build_site.build_open_problems_data({}, snapshot)
        for key in original:
            before, after = dict(original[key]), dict(reordered[key])
            self.assertNotEqual(before.pop('rank'), after.pop('rank'))
            self.assertEqual(before, after)
        self.assertEqual(reordered['20000601']['attacks'][0]['date_posted'], '2026-01-09')
        self.write('docs/data/top_problems/99.json', '{}')
        with patch.object(build_site, 'load_erdos_status', return_value={'problems': {}}):
            build_site.generate_js_data({}, {}, reordered, snapshot)
        self.assertTrue((build_site.DATA_DIR / 'top_problems/20000601.json').is_file())
        self.assertFalse((build_site.DATA_DIR / 'top_problems/99.json').exists())

    def test_explicit_unknown_posting_date_and_statement_only_survive_migration(self):
        self.write('attacks/open_problems/top_problems/Model/1.tex',
                   '% FIRST_POSTED: null\n% ENTRY_KIND: statement_only\nFULL SOLUTION')
        problem = build_site.build_open_problems_data({}, catalog())['1']
        self.assertNotIn('date_posted', problem['attacks'][0])
        self.assertEqual(problem['attacks'][0]['entry_kind'], 'statement_only')
        self.assertEqual(problem['llm_status'], 'none')

    def test_unknown_and_invalid_ranked_tex_filenames_fail_instead_of_disappearing(self):
        for filename in ['2.tex', 'problem.unknown.tex', '1_v0.tex',
                         '1_title.tex']:
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
        self.assertEqual(set(result), {'1', '20000601', 'mo:1'})
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
        self.write('attacks/open_problems/Statement_Model/1.tex', self.statement_only())
        self.write('attacks/open_problems/Actual_Model/20000601.tex', 'UNRESOLVED')
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
            self.assertEqual(record, problems['1'])
            build_site.generate_js_data({}, {}, problems, snapshot)
            self.assertEqual(first, (self.root / 'docs/problem.html').read_text())
            problems['1']['definition_tex'] = 'Revised definition'
            build_site.generate_js_data({}, {}, problems, snapshot)
            self.assertNotEqual(first, (self.root / 'docs/problem.html').read_text())

    def test_frontend_script_url_changes_when_routing_code_changes(self):
        self.write('docs/problem.html', '<script src="app.js"></script>')
        self.write('docs/app.js', 'var revision = 1;')
        snapshot = catalog()
        problems = build_site.build_open_problems_data({}, snapshot)
        with patch.object(build_site, 'load_erdos_status', return_value={'problems': {}}):
            build_site.generate_js_data({}, {}, problems, snapshot)
            first = (self.root / 'docs/problem.html').read_text()
            self.assertRegex(first, r'app\.js\?v=[0-9a-f]{16}')
            self.write('docs/app.js', 'var revision = 2;')
            build_site.generate_js_data({}, {}, problems, snapshot)
            self.assertNotEqual(first, (self.root / 'docs/problem.html').read_text())


class RepositoryMigrationTests(unittest.TestCase):
    def test_real_catalog_preserves_all_legacy_mo_links_and_namespaces(self):
        with patch.object(build_site, 'get_file_date', return_value='2026-09-24'):
            mo = build_site.build_mo_data()
            problems = build_site.build_open_problems_data(mo)
        self.assertEqual(len(mo), 100)
        self.assertEqual(len(problems), len(mo) + len(build_site.load_open_problems_catalog()['records']))
        self.assertEqual(sum(p['collection'] == 'ranked' for p in problems.values()),
                         build_site.load_open_problems_catalog()['recordCount'])
        self.assertEqual(sum(bool(p['attacks']) for p in mo.values()), 93)
        for qid, problem in mo.items():
            self.assertEqual(problem['attacks'], problems[f'mo:{qid}']['attacks'])
            self.assertIsNone(problems[f'mo:{qid}']['rank'])
            for attack in problem['attacks']:
                self.assertTrue(attack['file_path'].startswith('attacks/open_problems/mo/'))
                self.assertTrue((build_site.BASE_DIR / attack['file_path']).is_file())


if __name__ == '__main__':
    unittest.main()
