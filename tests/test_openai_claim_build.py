"""Keep scoped OpenAI statuses attributed and preserve the source catalogue."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import build_site


COMMIT = 'adc7f1241b42e322a6451854ab7e4b4c146bf78a'
PDF = 'preprints/Example-in-CAT(0)-spaces-September-23-2026/custom-result.pdf'
README = PDF.rsplit('/', 1)[0] + '/README.md'
STATEMENT = PDF.rsplit('/', 1)[0] + '/build/source/main.tex'
COMPARATORS = ['lean/ComparatorChallenges/Example.lean',
               'lean/ComparatorChallenges/Example.json']
TOP_PROBLEM = {'id': 1, 'title': 'Example conjecture'}


def manifest():
    return {
        'schema_version': 1,
        'source_repo': build_site.OPENAI_SOURCE_REPO,
        'source_commit': COMMIT,
        'families': [{
            'family': '197', 'title': 'An example family', 'subject': 'Algebra',
            'lean_doc': 'lean/docs/197.md', 'reasoning_trace': 'reasoning_traces/example.pdf',
            'manuscripts': [{
                'title': 'An example manuscript', 'dir': PDF.split('/')[1],
                'pdf_path': PDF, 'readme_path': README, 'date': '2026-09-23',
                'comparators': [{'lean': COMPARATORS[0], 'json': COMPARATORS[1],
                                 'declaration': 'Example.main'}],
            }],
        }],
        'eligible_paths': [PDF, README, STATEMENT, *COMPARATORS, 'lean/docs/197.md',
                           'reasoning_traces/example.pdf', 'CONTENTS.md'],
    }


def claim(match='full', resolution=None):
    solved = match in {'full', 'stronger'}
    return {
        'schema_version': 1, 'source_repo': build_site.OPENAI_SOURCE_REPO,
        'source_commit': COMMIT, 'release_date': '2026-10-06', 'match': match,
        'resolution': resolution or ('proved' if solved else 'partial'),
        'independently_reviewed': False, 'second_pass': 'agreed' if solved else 'n/a',
        'families': [{
            'family': '197', 'title': 'An example family', 'subject': 'Algebra',
            'manuscripts': [{
                'title': 'An example manuscript', 'pdf_path': PDF,
                'readme_path': README, 'date': '2026-09-23',
                'theorem_ref': 'Theorem 1.1',
            }],
            'lean': {
                'doc_path': 'lean/docs/197.md', 'comparators': COMPARATORS[:],
                'declarations': ['Example.main'], 'covers_main_theorem': True,
            },
            'reasoning_trace': 'reasoning_traces/example.pdf',
        }],
    }


def record(metadata=None, status=None, top_problem=None, body='Original summary.'):
    metadata = metadata if metadata is not None else claim()
    status = status or ('solved' if metadata['match'] in ('full', 'stronger') else 'unresolved')
    return (
        '% TOP_PROBLEM: ' + json.dumps(top_problem or TOP_PROBLEM) + '\n'
        '% FIRST_POSTED: 2026-10-06\n'
        '% ATTEMPT_STATUS: ' + status + '\n'
        '% OPENAI_CLAIM: ' + json.dumps(metadata) + '\n' + body
    )


class OpenAIClaimMetadataTests(unittest.TestCase):
    def parse(self, metadata=None, **kwargs):
        return build_site.parse_attack(record(metadata, **kwargs), 'openai',
                                       openai_manifest=manifest())

    def test_full_claim_keeps_links_but_removes_header_from_rendered_prose(self):
        result = self.parse()
        self.assertEqual(result['entry_kind'], 'external_claim')
        self.assertEqual(result['claimant'], 'OpenAI')
        self.assertEqual(result['model'], 'OpenAI')
        self.assertEqual(result['openai'], claim())
        self.assertEqual(result['status'], 'solved')
        self.assertEqual(result['completion'], 100)
        self.assertEqual(result['date_posted'], '2026-10-06')
        self.assertEqual(result['raw'], 'Original summary.')
        self.assertNotIn('OPENAI_CLAIM', str(result['sections']))

    def test_main_theorem_coverage_cannot_refer_to_unassigned_comparators(self):
        metadata = claim()
        metadata['families'][0]['lean']['comparators'] = []
        metadata['families'][0]['lean']['declarations'] = []
        with self.assertRaisesRegex(ValueError, 'selected manuscript Comparator'):
            self.parse(metadata)

    def test_stronger_disproof_is_a_solved_claim(self):
        result = self.parse(claim('stronger', 'disproved'))
        self.assertEqual(result['status'], 'solved')
        self.assertEqual(result['openai']['resolution'], 'disproved')

    def test_partial_does_not_inherit_a_completion_number_from_body(self):
        result = self.parse(claim('partial'), body='COMPLETION ESTIMATE: 100%')
        self.assertEqual(result['status'], 'unresolved')
        self.assertNotIn('completion', result)

    def test_optional_statement_sources_accept_exact_pinned_paper_locations(self):
        metadata = claim()
        sources = [{'path': STATEMENT, 'line': 57, 'label': 'thm:main_bound'},
                   {'path': STATEMENT, 'line': 83, 'label': 'Theorem 1.1'}]
        metadata['families'][0]['manuscripts'][0]['statement_sources'] = sources
        self.assertEqual(self.parse(metadata)['openai'], metadata)
        # The extension does not require changing existing schema-1 records.
        self.assertEqual(self.parse()['openai'], claim())

    def test_statement_sources_reject_wrong_shapes_lines_labels_and_duplicates(self):
        source = {'path': STATEMENT, 'line': 57, 'label': 'Theorem 1.1'}
        bad_sources = [None, source, 'not an array', [None], [dict(source, extra='unknown')],
                       [{key: value for key, value in source.items() if key != 'label'}],
                       [source, source]]
        bad_sources.extend([dict(source, line=line)] for line in (True, False, 0, -1, 1.5, '57', None))
        bad_sources.extend([dict(source, label=label)] for label in ('', '   ', 1, None))
        for sources in bad_sources:
            metadata = claim()
            metadata['families'][0]['manuscripts'][0]['statement_sources'] = sources
            with self.subTest(sources=sources), self.assertRaises(ValueError):
                self.parse(metadata)

    def test_statement_sources_cannot_cross_papers_or_escape_build_directory(self):
        for path in ('preprints/Other/build/source/main.tex',
                     PDF.rsplit('/', 1)[0] + '/main.tex',
                     PDF.rsplit('/', 1)[0] + '/build/source/../main.tex',
                     PDF.rsplit('/', 1)[0] + '/build/source/missing.tex', README, PDF):
            inventory = manifest()
            if not path.endswith('missing.tex') and path not in inventory['eligible_paths']:
                inventory['eligible_paths'].append(path)
            metadata = claim()
            metadata['families'][0]['manuscripts'][0]['statement_sources'] = [
                {'path': path, 'line': 57, 'label': 'Theorem 1.1'}]
            with self.subTest(path=path), self.assertRaises(ValueError):
                build_site.parse_openai_claim(record(metadata), inventory)

    def test_family_without_lean_or_reasoning_trace_is_valid(self):
        metadata, inventory = claim(), manifest()
        metadata['families'][0].update(lean=None, reasoning_trace=None)
        inventory['families'][0].update(lean_doc=None, reasoning_trace=None)
        parsed, body = build_site.parse_openai_claim(record(metadata), inventory)
        self.assertIsNone(parsed['families'][0]['lean'])
        self.assertEqual(body, 'Original summary.')

    def test_bad_json_unknown_schema_and_unreviewed_contract_fail(self):
        content = record().replace('% OPENAI_CLAIM: {', '% OPENAI_CLAIM: {bad:')
        with self.assertRaisesRegex(ValueError, 'OPENAI_CLAIM JSON'):
            build_site.parse_openai_claim(content, manifest())
        for key, value in [
            ('schema_version', 2), ('schema_version', True), ('match', 'related'),
            ('match', []), ('resolution', 'solved'), ('resolution', []),
            ('independently_reviewed', True), ('independently_reviewed', 0),
            ('second_pass', 'n/a'), ('release_date', '2026-02-30'),
            ('source_repo', 'https://github.com/openai/math.evil'),
            ('source_commit', 'b' * 40), ('families', []), ('extra', 'unknown'),
        ]:
            metadata = claim()
            metadata[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.parse(metadata)

    def test_match_status_resolution_and_second_pass_must_agree(self):
        for metadata, status in [(claim(), 'unresolved'),
                                 (claim('partial'), 'solved'),
                                 (claim('partial'), 'partial'),
                                 (claim('partial', 'proved'), 'unresolved')]:
            with self.subTest(metadata=metadata, status=status), self.assertRaises(ValueError):
                self.parse(metadata, status=status)
        metadata = claim('partial')
        metadata['second_pass'] = 'agreed'
        with self.assertRaises(ValueError):
            self.parse(metadata)

    def test_missing_misordered_duplicate_or_conflicting_headers_fail(self):
        content = record()
        variants = [
            content.replace('% TOP_PROBLEM:', '% OTHER:'),
            content.replace('% FIRST_POSTED: 2026-10-06', '% FIRST_POSTED: 2026-10-07'),
            '\n' + content,
            content + '\n% OPENAI_CLAIM: {}',
            content + '\n% ATTEMPT_STATUS: solved',
            content + '\n% ENTRY_KIND: statement_only',
            content + '\n% COLLECTION_METADATA: {}',
        ]
        for variant in variants:
            with self.subTest(content=variant), self.assertRaises(ValueError):
                build_site.parse_openai_claim(variant, manifest())

    def test_paper_fields_and_all_link_paths_are_checked_against_manifest(self):
        for key, value in [
            ('pdf_path', 'preprints/missing/paper.pdf'),
            ('pdf_path', '../' + PDF),
            ('readme_path', 'CONTENTS.md'),
            ('date', '2026-09-24'), ('title', 'Another paper'), ('theorem_ref', ''),
        ]:
            metadata = claim()
            metadata['families'][0]['manuscripts'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.parse(metadata)
        for change in [
            {'family': '198'}, {'title': 'Different family'}, {'subject': 'Analysis'},
            {'reasoning_trace': 'CONTENTS.md'}, {'lean': None},
        ]:
            metadata = claim()
            metadata['families'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.parse(metadata)

    def test_paths_from_another_family_cannot_supply_papers_or_comparators(self):
        inventory = manifest()
        other = deepcopy(inventory['families'][0])
        other['family'] = '198'
        other['manuscripts'][0].update(pdf_path='preprints/Other/paper.pdf',
                                        readme_path='preprints/Other/README.md')
        other['manuscripts'][0]['comparators'] = [{
            'lean': 'lean/ComparatorChallenges/Other.lean',
            'json': 'lean/ComparatorChallenges/Other.json',
        }]
        inventory['families'].append(other)
        inventory['eligible_paths'].extend([
            'preprints/Other/paper.pdf', 'preprints/Other/README.md',
            'lean/ComparatorChallenges/Other.lean', 'lean/ComparatorChallenges/Other.json',
        ])
        metadata = claim()
        metadata['families'][0]['manuscripts'][0]['pdf_path'] = 'preprints/Other/paper.pdf'
        with self.assertRaisesRegex(ValueError, 'manifest family'):
            build_site.parse_openai_claim(record(metadata), inventory)
        metadata = claim()
        metadata['families'][0]['lean']['comparators'] = ['lean/ComparatorChallenges/Other.lean']
        with self.assertRaisesRegex(ValueError, 'manifest family'):
            build_site.parse_openai_claim(record(metadata), inventory)

    def test_unlisted_companion_cannot_supply_formalization(self):
        inventory = manifest()
        companion = deepcopy(inventory['families'][0]['manuscripts'][0])
        companion.update(pdf_path='preprints/Companion/paper.pdf',
                         readme_path='preprints/Companion/README.md',
                         comparators=[{'lean': 'lean/ComparatorChallenges/Companion.lean',
                                       'declaration': 'Companion.main'}])
        inventory['families'][0]['manuscripts'].append(companion)
        inventory['eligible_paths'].extend([companion['pdf_path'], companion['readme_path'],
                                          'lean/ComparatorChallenges/Companion.lean'])
        for field, value in [('comparators', ['lean/ComparatorChallenges/Companion.lean']),
                             ('declarations', ['Companion.main'])]:
            metadata = claim()
            metadata['families'][0]['lean'][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'selected manuscript'):
                build_site.parse_openai_claim(record(metadata), inventory)

    def test_duplicate_families_papers_and_invalid_lean_metadata_fail(self):
        for mutate in [
            lambda m: m['families'].append(deepcopy(m['families'][0])),
            lambda m: m['families'][0]['manuscripts'].append(
                deepcopy(m['families'][0]['manuscripts'][0])),
            lambda m: m['families'][0]['lean'].update(covers_main_theorem=1),
            lambda m: m['families'][0]['lean'].update(doc_path='CONTENTS.md'),
            lambda m: m['families'][0]['lean'].update(comparators=['CONTENTS.md']),
            lambda m: m['families'][0]['lean'].update(declarations=['']),
        ]:
            metadata = claim()
            mutate(metadata)
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                self.parse(metadata)

    def test_missing_or_unreadable_manifest_fails_explicitly(self):
        with TemporaryDirectory() as directory, \
                patch.object(build_site, 'OPENAI_MANIFEST_PATH', Path(directory) / 'absent.json'):
            with self.assertRaisesRegex(ValueError, 'OpenAI manifest'):
                build_site.parse_attack(record(), 'openai')


class OpenAIClaimAggregationTests(unittest.TestCase):
    def summarize(self, attacks):
        problem = {'status': 'open', 'attacks': attacks}
        build_site.summarize_open_problem_attempts(problem)
        return problem

    def test_full_or_stronger_overrides_unresolved_gpt_and_preserves_source_status(self):
        for match in ['full', 'stronger']:
            attack = build_site.parse_attack(record(claim(match)), 'openai',
                                              openai_manifest=manifest())
            result = self.summarize([{'model': 'GPT', 'status': 'unresolved', 'completion': 35}, attack])
            self.assertEqual(result['status'], 'solved')
            self.assertEqual(result['source_status'], 'open')
            self.assertEqual(result['status_source'], 'openai_claim')
            self.assertEqual(result['llm_status'], 'solved')
            self.assertEqual(result['llm_status_source'], 'openai_claim')
            self.assertEqual(result['completion'], 100)
            self.assertEqual(result['completion_source'], 'openai_claim')
            self.assertEqual(result['tags'], ['openai'])
            self.assertEqual(result['openai_claim'], 'solved')

    def test_partial_is_visible_without_a_solved_label_or_invented_completion(self):
        attack = build_site.parse_attack(record(claim('partial')), 'openai',
                                          openai_manifest=manifest())
        result = self.summarize([attack])
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['source_status'], 'open')
        self.assertEqual(result['status_source'], 'openai_claim')
        self.assertEqual(result['llm_status'], 'partial')
        self.assertEqual(result['llm_status_source'], 'openai_claim')
        self.assertEqual(result['openai_claim'], 'partial')
        self.assertEqual(result['tags'], ['openai'])
        self.assertNotIn('completion', result)
        result = self.summarize([{'model': 'GPT', 'status': 'unresolved', 'completion': 35}, attack])
        self.assertEqual(result['completion'], 35)
        self.assertEqual(result['completion_source'], 'llm')

    def test_partial_contribution_keeps_a_catalogue_solution_and_human_review(self):
        attack = build_site.parse_attack(record(claim('partial')), 'openai',
                                          openai_manifest=manifest())
        review = {'status': 'unreviewed'}
        problem = {'status': 'solved', 'attacks': [attack], 'review': review}
        build_site.summarize_open_problem_attempts(problem)
        self.assertEqual(problem['status'], 'solved')
        self.assertEqual(problem['source_status'], 'solved')
        self.assertEqual(problem['status_source'], 'source_catalogue')
        self.assertEqual(problem['llm_status'], 'partial')
        self.assertIs(problem['review'], review)

    def test_related_result_does_not_claim_partial_solution_of_a_different_target(self):
        attack = build_site.parse_attack(record(claim('related')), 'openai',
                                         openai_manifest=manifest())
        result = self.summarize([attack])
        self.assertEqual(result['status'], 'open')
        self.assertEqual(result['source_status'], 'open')
        self.assertEqual(result['openai_claim'], 'related')
        self.assertEqual(result['llm_status'], 'related')
        self.assertNotIn('completion', result)

    def test_repeated_aggregation_retains_the_original_source_status(self):
        attack = build_site.parse_attack(record(), 'openai', openai_manifest=manifest())
        result = self.summarize([attack])
        build_site.summarize_open_problem_attempts(result)
        self.assertEqual(result['status'], 'solved')
        self.assertEqual(result['source_status'], 'open')

    def test_published_rh_and_bsd_matches_remain_partial(self):
        for problem_id in ('2', '5'):
            path = build_site.OPEN_PROBLEMS_PATH / 'openai' / f'{problem_id}.tex'
            attack = build_site.parse_attack(path.read_text(encoding='utf-8'), 'openai')
            with self.subTest(problem_id=problem_id):
                self.assertEqual(attack['openai']['match'], 'partial')
                result = self.summarize([{'model': 'GPT', 'status': 'unresolved'}, attack])
                self.assertEqual(result['status'], 'partial')
                self.assertEqual(result['llm_status'], 'partial')
                self.assertNotEqual(result['status'], 'solved')

    def test_absent_openai_keeps_existing_status_precedence_and_estimates(self):
        result = self.summarize([{'model': 'GPT', 'status': 'solved', 'completion': 80},
                                 {'model': 'GPT', 'status': 'unresolved', 'completion': 20}])
        self.assertEqual(result['llm_status'], 'unresolved')
        self.assertEqual(result['completion'], 80)
        self.assertEqual(result['completion_source'], 'llm')
        self.assertNotIn('tags', result)
        self.assertNotIn('openai_claim', result)
        self.assertNotIn('source_status', result)
        self.assertNotIn('status_source', result)
        self.assertEqual(result['status'], 'open')
        self.assertEqual(self.summarize([])['llm_status'], 'none')


class OpenAIClaimSiteIdentityTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.top = self.root / 'attacks/open_problems/top_problems'
        self.top.mkdir(parents=True)
        variables = {
            'BASE_DIR': self.root, 'ATTACKS_DIR': self.root / 'attacks',
            'OPEN_PROBLEMS_PATH': self.top, 'REVIEWS_DIR': self.root / 'reviews',
            'UNSOLVEDMATH_PATH': self.root / 'lists/unsolvedmath/problems.json',
            'DISPLAY_ORDER_PATH': self.root / 'lists/unsolvedmath/display_order.json',
            'OPENAI_MANIFEST_PATH': self.root / 'lists/openai_math/manifest.json',
        }
        for name, value in variables.items():
            patcher = patch.object(build_site, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.write(build_site.OPENAI_MANIFEST_PATH, json.dumps(manifest()))
        self.write(build_site.UNSOLVEDMATH_PATH, json.dumps([{
            'id': 1, 'problem_number': 'TEST-1', 'title': 'Example conjecture',
            'category': {'name': 'algebra', 'display_name': 'Algebra'},
            'status': 'open', 'external_url': None,
        }]))
        self.write(build_site.DISPLAY_ORDER_PATH, '[1]')
        self.definition = self.top / 'definitions/1.tex'
        self.write(self.definition, '% TOP_PROBLEM: ' + json.dumps(TOP_PROBLEM) + '\n' + r'''
\begin{document}
\section{Example conjecture}
\subsection{Definitions and mathematical statement}
Does every example have this property?
\subsection{Short English statement}
Determine whether all examples qualify.
\subsection{Sources}
\begin{itemize}
\item[S1] The original question. \url{https://example.org/question}
\end{itemize}
\end{document}
''')
        self.attempt = self.top / 'openai/1.tex'
        self.write(self.attempt, record())

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def build(self):
        return build_site.build_open_problems_data({})

    def test_real_catalog_join_emits_tagged_external_claim(self):
        self.write(self.top / 'gpt_6_astra_pro/1.tex', '% ATTEMPT_STATUS: unresolved\nIncomplete attempt.')
        result = self.build()['1']
        self.assertEqual(result['tags'], ['openai'])
        self.assertEqual(result['llm_status'], 'solved')
        self.assertEqual(result['status'], 'solved')
        self.assertEqual(result['source_status'], 'open')
        self.assertEqual(result['attacks'][0]['model'], 'OpenAI')
        self.assertEqual(result['attacks'][0]['openai'], claim())

    def test_openai_record_requires_definition_registry_and_display_order(self):
        self.definition.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing definition'):
            self.build()
        self.write(self.definition, '% TOP_PROBLEM: ' + json.dumps(TOP_PROBLEM))
        self.write(build_site.UNSOLVEDMATH_PATH, '[]')
        with self.assertRaises(ValueError):
            self.build()

    def test_incomplete_display_order_cannot_hide_an_openai_record(self):
        self.write(build_site.DISPLAY_ORDER_PATH, '[]')
        with self.assertRaisesRegex(ValueError, 'Display order'):
            self.build()

    def test_same_id_but_changed_definition_header_is_rejected(self):
        self.write(self.attempt, record(top_problem={'id': 1, 'title': 'Another title'}))
        with self.assertRaisesRegex(ValueError, 'match its definition metadata'):
            self.build()

    def test_unmarked_openai_folder_and_claim_in_other_folder_are_rejected(self):
        self.write(self.attempt, '% ATTEMPT_STATUS: solved\nA claim without metadata.')
        with self.assertRaisesRegex(ValueError, 'require top_problems/openai'):
            self.build()
        self.attempt.unlink()
        self.write(self.top / 'another_model/1.tex', record())
        with self.assertRaisesRegex(ValueError, 'require top_problems/openai'):
            self.build()

    def test_metadata_survives_numbered_document_display_conversion(self):
        body = self.definition.read_text().partition('\n')[2]
        self.write(self.attempt, record(body=body))
        result = self.build()['1']['attacks'][0]
        self.assertEqual(result['entry_kind'], 'external_claim')
        self.assertEqual(result['openai'], claim())
        self.assertNotIn('OPENAI_CLAIM', result['raw'])


if __name__ == '__main__':
    unittest.main()
