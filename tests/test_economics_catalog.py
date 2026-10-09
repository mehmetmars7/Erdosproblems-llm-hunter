"""Protect Economics coverage, exact source matching and permanent identity."""

import csv
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.economics_catalog import (BASE_DIR, REGISTRY_PATH, RANKINGS_PATH,
                                      build_economics_data, extract_statement,
                                      generate_economics_data, load_registry,
                                      read_ranking_csv)
from scripts.import_economics import import_economics, parse_source
from scripts.update_economics_ranks import update_economics_ranks


# Permanent identities of the research batch selected at ranks 11--50 on
# 2026-10-09. Future reranking must not move these attempts to different problems.
ULTRA_BATCH_IDS = set('''
C73-11 C71-12 C79-13 C72-14 C73-15 D81-16 C73-17 C61-18 C73-19 C73-20
D86-21 D63-22 O33-23 C73-24 C73-25 C65-26 C73-27 C73-28 C65-29 C73-30
C72-31 C73-32 C65-33 D44-34 C63-35 C72-36 C65-37 C73-38 D63-39 C73-40
C73-41 C90-42 C73-43 E52-44 C65-45 D82-46 C63-47 C62-48 C73-49 C14-50
'''.split())


def source_fixture():
    first = (r'\section*{Source mathematical conventions}' + '\nAtlas context.\n'
             + '% MERGED_PROBLEM: {"id":"OP-0010","source":"atlas","jel":"C73"}\n'
             + r'\section{First problem}' + '\n'
             + r'\ProblemClassification{OP-0010}{C73}{Atlas}{M1}' + '\n'
             + r'\label{C73}\label{problem:OP-0010}\label{difficulty-rank:3}' + '\n'
             + r'\subsection*{Definitions and assumptions}' + '\n'
             + r'Preserved $x\in\R$ and {nested {braces}}.' + '\n'
             + r'\subsection*{References}' + '\nFirst exact source.\n')
    second = (r'\section*{Source mathematical conventions}' + '\nGame context.\n'
              + r'\section{Second problem}' + '\n'
              + r'\ProblemClassification{OP-0050}{C72}{Supplement}{Merged}' + '\n'
              + r'\label{C72}\label{problem:OP-0050}\label{difficulty-rank:1}' + '\n'
              + r'\subsection*{Definitions and assumptions}' + '\nSecond body.\n'
              + '% MERGED_PROBLEM: {"id":"OP-0050","source":"game","jel":"C72"}\n'
              + r'\section{Third problem}' + '\n'
              + r'\ProblemClassification{OP-0050}{C72}{Game theory}{GT-2}' + '\n'
              + r'\label{C72}\label{problem:OP-0050}\label{difficulty-rank:2}' + '\n'
              + r'\subsection*{Definitions and assumptions}' + '\nThird body.\n')
    trailing_contexts = ''.join(
        r'\section*{' + title + '}\n' + text + '\n'
        for title, text in [
            ('Source mathematical conventions', 'Definition context.'),
            ('Source mathematical conventions', 'Beyond context.'),
            ('BSDE conventions for SC-01--SC-06', 'BSDE context.'),
            ('Control and stopping conventions for SC-07--SC-08', 'Control context.'),
            ('Additional-source status and mathematical conventions', 'Audited context.'),
        ])
    return (r'\documentclass{article}' + '\n' + r'\begin{document}' + '\n'
            + first + second + trailing_contexts + r'\appendix' + '\n'
            + r'\section{Appendix excluded}' + '\n' + r'\end{document}' + '\n')


def csv_text(rows):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['New rank', 'Problem title', 'JEL code', 'Problem ID'])
    writer.writerows(rows)
    return stream.getvalue()


class EconomicsCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        classification = self.root / 'lists/economics/jel_codes.json'
        classification.parent.mkdir(parents=True)
        classification.write_bytes((BASE_DIR / 'lists/economics/jel_codes.json').read_bytes())
        self.tex = self.root / 'source.tex'
        self.tex.write_text(source_fixture(), encoding='utf-8')
        self.csv = self.root / 'original.csv'
        self.csv.write_text(csv_text([
            [1, 'First problem', 'C73', 'OP-0010'],
            [2, 'Second problem', 'C72', 'OP-0050'],
            [3, 'Third problem', 'C72', 'OP-0050'],
        ]), encoding='utf-8')

    def imported(self):
        return import_economics(self.tex, self.csv, self.root)

    def write_ranks(self, text):
        path = self.root / 'revision.csv'
        path.write_text(text, encoding='utf-8')
        return path

    def test_actual_sections_not_missing_stale_or_duplicate_markers_own_identity(self):
        entries = parse_source(source_fixture())
        self.assertEqual(len(entries), 3)
        self.assertEqual([entry['source_id'] for entry in entries],
                         ['OP-0010', 'OP-0050', 'OP-0050'])
        self.assertEqual(entries[1]['source_metadata'], {})
        self.assertIn('Preserved $x\\in\\R$ and {nested {braces}}.', entries[0]['body'])
        self.assertIn('Atlas context.', entries[0]['body'])
        self.assertNotIn('Game context.', entries[0]['body'])
        self.assertIn('Game context.', entries[2]['body'])
        self.assertNotIn('Definition context.', entries[2]['body'])
        self.assertNotIn('difficulty-rank:', ''.join(entry['body'] for entry in entries))
        self.assertNotIn('Appendix excluded', ''.join(entry['body'] for entry in entries))

    def test_import_freezes_ids_and_creates_local_downloads_without_attempts(self):
        registry = self.imported()
        self.assertEqual([record['id'] for record in registry['problems']],
                         ['C73-1', 'C72-2', 'C72-3'])
        data = build_economics_data(self.root)
        for problem_id, record in data.items():
            self.assertEqual(record['attacks'], [])
            self.assertEqual(record['entry_kind'], 'statement_only')
            canonical = (self.root / record['definitionFile']).read_bytes()
            public = (self.root / 'docs' / record['statement_url']).read_bytes()
            self.assertEqual(canonical, public)
            self.assertEqual(record['definition_tex'], extract_statement(canonical.decode()))
        self.assertIn('window.ECONOMICS_DATA = ',
                      (self.root / 'docs/data/economics_data.js').read_text())

    def test_stale_source_comment_cannot_replace_authoritative_provenance(self):
        stale = source_fixture().replace('"id":"OP-0010"', '"id":"OP-0009"')
        entry = parse_source(stale)[0]
        self.assertEqual(entry['source_id'], 'OP-0010')
        self.assertEqual(entry['source_metadata'], {})
        self.assertEqual(entry['source_comment_metadata']['id'], 'OP-0009')

    def test_reimport_refuses_before_any_identity_or_statement_changes(self):
        self.imported()
        registry = (self.root / REGISTRY_PATH).read_bytes()
        with self.assertRaisesRegex(ValueError, 'permanent IDs cannot be regenerated'):
            import_economics(self.root / 'missing.tex', self.root / 'missing.csv', self.root)
        self.assertEqual((self.root / REGISTRY_PATH).read_bytes(), registry)

    def test_rerank_changes_order_and_preserves_registry_ids_and_statement_files(self):
        registry = self.imported()
        original_registry = (self.root / REGISTRY_PATH).read_bytes()
        files = {record['id']: (self.root / record['statement_file']).read_bytes()
                 for record in registry['problems']}
        revision = self.write_ranks('Problem ID,New rank\nC73-1,3\nC72-2,1\nC72-3,2\n')
        update_economics_ranks(revision, self.root)
        data = build_economics_data(self.root)
        self.assertEqual(list(data), ['C72-2', 'C72-3', 'C73-1'])
        self.assertEqual(data['C73-1']['rank'], 3)
        self.assertEqual((self.root / REGISTRY_PATH).read_bytes(), original_registry)
        self.assertEqual(set(data), set(files))
        for record in registry['problems']:
            self.assertEqual((self.root / record['statement_file']).read_bytes(), files[record['id']])

    def test_legacy_source_ids_need_title_and_jel_for_reused_ids(self):
        self.imported()
        update_economics_ranks(self.csv, self.root, allow_source_ids=True, check_only=True)
        revision = self.write_ranks('Problem ID,New rank\nOP-0010,1\nOP-0050,2\nOP-0050,3\n')
        with self.assertRaisesRegex(ValueError, 'ambiguous source Problem ID'):
            update_economics_ranks(revision, self.root, allow_source_ids=True)
        with self.assertRaisesRegex(ValueError, 'unknown Problem ID'):
            update_economics_ranks(self.csv, self.root)

    def test_invalid_rankings_fail_without_mutation(self):
        self.imported()
        before = (self.root / RANKINGS_PATH).read_bytes()
        bad_csvs = [
            ('Problem ID,New rank\nC73-1,1\nC72-2,1\nC72-3,3\n', 'unique'),
            ('Problem ID,New rank\nC73-1,1\nC72-2,2\nC72-3,4\n', 'contiguous'),
            ('Problem ID,New rank\nC73-1,1\nC72-2,2\n', 'coverage'),
            ('Problem ID,New rank\nC73-1,1\nC72-2,2\nC72-2,3\n', 'duplicate Problem ID'),
            ('Problem ID,New rank\nC73-1,1\nC72-2,2\nC72-3,2.5\n', 'positive integer'),
            ('Problem ID,New rank\nC73-1,1\nC72-2,2\nX00-3,3\n', 'unknown Problem ID'),
            ('Problem ID,New rank,JEL code\nC73-1,1,C72\nC72-2,2,C72\nC72-3,3,C72\n', 'JEL code mismatch'),
            ('Problem ID,New rank,Problem title\nC73-1,1,Wrong title\nC72-2,2,Second problem\nC72-3,3,Third problem\n', 'title mismatch'),
        ]
        for text, error in bad_csvs:
            with self.subTest(error=error):
                with self.assertRaisesRegex(ValueError, error):
                    update_economics_ranks(self.write_ranks(text), self.root)
                self.assertEqual((self.root / RANKINGS_PATH).read_bytes(), before)

    def test_initial_csv_mismatch_produces_no_registry_or_statements(self):
        self.csv.write_text(self.csv.read_text().replace('Third problem', 'Different problem'))
        with self.assertRaisesRegex(ValueError, 'no exact OP/title/JEL source match'):
            self.imported()
        self.assertFalse((self.root / REGISTRY_PATH).exists())
        self.assertFalse((self.root / 'attacks').exists())

    def test_check_mode_leaves_all_rank_outputs_unchanged(self):
        self.imported()
        before = (self.root / RANKINGS_PATH).read_bytes()
        javascript = (self.root / 'docs/data/economics_data.js').read_bytes()
        revision = self.write_ranks('Problem ID,New rank\nC73-1,3\nC72-2,1\nC72-3,2\n')
        update_economics_ranks(revision, self.root, check_only=True)
        self.assertEqual((self.root / RANKINGS_PATH).read_bytes(), before)
        self.assertEqual((self.root / 'docs/data/economics_data.js').read_bytes(), javascript)

    def write_attempt(self, record, version=1, notation=r'\mathbb R'):
        filename = record['id'] + (f'_v{version}' if version > 1 else '') + '.tex'
        path = self.root / 'attacks/open_problems/economics/gpt_6_astra_pro' / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {key: record[key] for key in ('id', 'title', 'jel_code', 'source_id')}
        path.write_text('% ECONOMICS_PROBLEM: ' + json.dumps(metadata) + '\n'
                        '% FIRST_POSTED: 2026-10-09\n% ATTEMPT_STATUS: unresolved\n'
                        + r'\documentclass{article}' + '\n'
                        + r'\newcommand{\Local}{' + notation + '}\n'
                        + r'\begin{document}' + '\n'
                        + r'\section{Claimed lemma, not the entire problem}' + '\n'
                        + r'$x\in\Local$ with \label{eq:shared}\ref{eq:shared}.' + '\n'
                        + r'\end{document}' + '\n', encoding='utf-8')
        return path

    def test_attempt_versions_have_independent_notation_and_exact_downloads(self):
        registry = self.imported()
        target = registry['problems'][1]
        first = self.write_attempt(target)
        second = self.write_attempt(target, 2, r'\Delta')
        before = (self.root / target['statement_file']).read_bytes()
        data = generate_economics_data(self.root)
        attacks = data[target['id']]['attacks']
        self.assertEqual([attack['version'] for attack in attacks], [1, 2])
        self.assertEqual([attack['model'] for attack in attacks], ['GPT 6 Astra Pro'] * 2)
        self.assertEqual([attack['status'] for attack in attacks], ['unresolved'] * 2)
        self.assertIn(r'\mathbb{R}', attacks[0]['raw'])
        self.assertNotIn(r'\Delta', attacks[0]['raw'])
        self.assertIn(r'\Delta', attacks[1]['raw'])
        for attack, source in zip(attacks, [first, second]):
            self.assertEqual((self.root / 'docs' / attack['download_url']).read_bytes(), source.read_bytes())
        self.assertEqual(data[target['id']]['llm_status'], 'unresolved')
        # The other problem reuses the same source OP ID; it must receive no attack.
        self.assertEqual(data[registry['problems'][2]['id']]['attacks'], [])
        self.assertEqual((self.root / target['statement_file']).read_bytes(), before)
        update_economics_ranks(self.write_ranks('Problem ID,New rank\nC73-1,3\nC72-2,2\nC72-3,1\n'), self.root)
        self.assertEqual(len(build_economics_data(self.root)[target['id']]['attacks']), 2)

    def test_pdf_title_layout_does_not_leak_into_public_attempt_heading(self):
        target = self.imported()['problems'][0]
        path = self.write_attempt(target)
        source = path.read_text().replace(
            r'\begin{document}',
            r'\title{\textbf{Research note}\\[5pt]' + '\n'
            + r'\large Complete proof and remaining gap}' + '\n'
            + r'\begin{document}\maketitle')
        path.write_text(source)
        attempt = generate_economics_data(self.root)[target['id']]['attacks'][0]
        self.assertIn(r'\section*{\textbf{Research note} Complete proof and remaining gap}',
                      attempt['raw'])
        self.assertNotIn(r'\\[5pt]', attempt['raw'])
        self.assertNotIn(r'\large', attempt['raw'])
        self.assertEqual((self.root / 'docs' / attempt['download_url']).read_text(), source)

    def test_completion_uses_highest_tex_estimate_across_models_and_versions(self):
        records = self.imported()['problems']
        target = records[0]
        sources = [self.write_attempt(target), self.write_attempt(target, 2)]
        third = sources[0].parent.parent / 'gpt6_astra_ultra' / sources[0].name
        third.parent.mkdir()
        third.write_bytes(sources[0].read_bytes())
        sources.append(third)
        for source, estimate in zip(sources, [r'45.5\%', r'20\%', '0.35']):
            source.write_text(source.read_text().replace(
                r'\end{document}', r'\section{Completion Estimate}' + '\n'
                + estimate + '\n' + r'\end{document}'))
        data = generate_economics_data(self.root)
        problem = data[target['id']]
        self.assertEqual([attack['completion'] for attack in problem['attacks']],
                         [45.5, 20, 35])
        self.assertEqual(problem['completion'], 45.5)
        self.assertEqual(problem['completion_source'], 'llm')
        self.assertEqual(problem['status'], 'open')
        self.assertEqual(problem['llm_status'], 'unresolved')
        published = (self.root / 'docs/data/economics_data.js').read_text()
        self.assertIn('"completion": 45.5', published)
        self.assertNotIn('completion', data[records[1]['id']])
        for attack, source in zip(problem['attacks'], sources):
            self.assertEqual((self.root / 'docs' / attack['download_url']).read_bytes(),
                             source.read_bytes())

    def test_zero_completion_is_preserved_and_missing_estimates_stay_unset(self):
        records = self.imported()['problems']
        zero = self.write_attempt(records[0])
        zero.write_text(zero.read_text().replace(
            r'\end{document}', r'\section*{Completion Estimate}' + '\n0\\%\n'
            + r'\end{document}'))
        solved_without_estimate = self.write_attempt(records[1])
        solved_without_estimate.write_text(solved_without_estimate.read_text().replace(
            '% ATTEMPT_STATUS: unresolved', '% ATTEMPT_STATUS: solved'))
        data = build_economics_data(self.root)
        self.assertEqual(data[records[0]['id']]['completion'], 0)
        self.assertEqual(data[records[0]['id']]['attacks'][0]['completion'], 0)
        solved = data[records[1]['id']]
        self.assertEqual(solved['completion'], 100)
        self.assertEqual(solved['attacks'][0]['completion'], 100)
        self.assertEqual(solved['completion_source'], 'llm_claim')
        self.assertEqual(solved['status'], 'solved')
        self.assertEqual(solved['source_status'], 'open')
        self.assertNotIn('completion', data[records[2]['id']])
        self.assertNotIn('completion_source', data[records[2]['id']])

    def test_solved_claim_overrides_lower_estimates_across_models_and_versions(self):
        target = self.imported()['problems'][0]
        solved = self.write_attempt(target)
        solved.write_text(solved.read_text().replace(
            '% ATTEMPT_STATUS: unresolved', '% ATTEMPT_STATUS: solved').replace(
            r'\end{document}', r'\section{Completion Estimate}' + '\n15\\%\n'
            + r'\end{document}'))
        newer = self.write_attempt(target, 2)
        newer.write_text(newer.read_text().replace(
            r'\end{document}', r'\section{Completion Estimate}' + '\n45\\%\n'
            + r'\end{document}'))
        other_model = solved.parent.parent / 'gpt_6_astra_ultra' / solved.name
        other_model.parent.mkdir()
        other_model.write_bytes(newer.read_bytes())
        data = generate_economics_data(self.root)
        problem = data[target['id']]
        self.assertEqual(problem['llm_status'], 'solved')
        self.assertEqual(problem['status'], 'solved')
        self.assertEqual(problem['status_source'], 'llm_claim')
        self.assertEqual(problem['source_status'], 'open')
        self.assertEqual(problem['completion'], 100)
        self.assertEqual(problem['completion_source'], 'llm_claim')
        self.assertEqual([a['status'] for a in problem['attacks']],
                         ['solved', 'unresolved', 'unresolved'])
        self.assertEqual([a['completion'] for a in problem['attacks']], [100, 45, 45])
        for attack in problem['attacks']:
            self.assertEqual((self.root / 'docs' / attack['download_url']).read_bytes(),
                             (self.root / attack['file_path']).read_bytes())

    def test_attempt_identity_and_explicit_status_are_required(self):
        target = self.imported()['problems'][0]
        path = self.write_attempt(target)
        original = path.read_text()
        for content, error in [
            (original.replace('"id": "C73-1"', '"id": "C72-2"'), 'id mismatch'),
            (original.replace('"jel_code": "C73"', '"jel_code": "C72"'), 'jel_code mismatch'),
            (original.replace('% ATTEMPT_STATUS: unresolved\n', ''), 'ATTEMPT_STATUS'),
            (original.replace(r'\end{document}', ''), 'complete Economics attempt'),
        ]:
            with self.subTest(error=error):
                path.write_text(content)
                with self.assertRaisesRegex(ValueError, error):
                    build_economics_data(self.root)
        path.write_text(original)


class CompleteEconomicsImportTests(unittest.TestCase):
    def test_all_657_classified_statements_have_unique_frozen_ids_and_rank_coverage(self):
        registry = load_registry()
        records = registry['problems']
        self.assertEqual(len(records), 657)
        self.assertEqual(len({record['id'] for record in records}), 657)
        self.assertEqual({record['initial_rank'] for record in records}, set(range(1, 658)))
        data = build_economics_data()
        self.assertEqual({record['rank'] for record in data.values()}, set(range(1, 658)))
        self.assertEqual(set(data), {record['id'] for record in records})
        expected = {
            'C73-1': ('OP-0590', 'Equilibrium payoffs in finite multiplayer stochastic games'),
            'C72-4': ('OP-0589', 'Computational complexity of optimin in finite games'),
            'C72-14': ('OP-0589', 'The Catch-Up optimal-draw conjecture for consecutive integers'),
            'D63-39': ('OP-0589', 'EFX existence for three agents with additive chores'),
            'D63-144': ('OP-0590', 'EFX and Pareto optimality for personalized bi-valued goods'),
        }
        for problem_id, (source_id, title) in expected.items():
            self.assertEqual((data[problem_id]['source_id'], data[problem_id]['title']), (source_id, title))
        for record in data.values():
            self.assertTrue(record['definition_tex'].strip())
            self.assertIn('Common conventions:', record['definition_tex'])
            self.assertNotIn('difficulty-rank:', record['definition_tex'])
            self.assertNotIn('\\ProblemClassification', record['definition_tex'])
            self.assertNotIn('Primary JEL index', record['definition_tex'])
            for attack in record['attacks']:
                self.assertTrue(Path(attack['file_path']).stem == record['id'] or
                                Path(attack['file_path']).stem.startswith(record['id'] + '_v'))

    def test_six_public_attacks_cover_five_canonical_problems(self):
        data = build_economics_data()
        imported_files = {'C73-1.tex', 'C73-1_v2.tex', 'C72-4.tex',
                          'C73-10.tex', 'C72-14.tex', 'D44-83.tex'}
        attacked = {
            problem_id: {**record, 'attacks': pro_attacks}
            for problem_id, record in data.items()
            if (pro_attacks := [attack for attack in record['attacks']
                                if attack['model'] == 'GPT 6 Astra Pro'
                                and Path(attack['file_path']).name in imported_files])
        }
        self.assertEqual(set(attacked), {'C73-1', 'C72-4', 'C73-10', 'C72-14', 'D44-83'})
        self.assertEqual(sum(len(record['attacks']) for record in attacked.values()), 6)
        self.assertEqual([attack['version'] for attack in attacked['C73-1']['attacks']], [1, 2])
        self.assertNotIn('D63-97', attacked)  # Reused auction source OP-0592.
        for record in attacked.values():
            self.assertEqual(record['status'], 'open')
            self.assertEqual(record['llm_status'], 'unresolved')
            for attack in record['attacks']:
                public = (BASE_DIR / attack['file_path']).read_text()
                self.assertEqual(attack['status'], 'unresolved')
                self.assertEqual(attack['model'], 'GPT 6 Astra Pro')
                self.assertNotRegex(public, r'/Users/|/home/|/mnt/data|uploaded filename|user-supplied|ProblemClassification|MERGED_PROBLEM')
                self.assertEqual(public.count(r'\begin{document}'), 1)
                self.assertEqual(public.count(r'\end{document}'), 1)
        catchup = (BASE_DIR / attacked['C72-14']['attacks'][0]['file_path']).read_text()
        self.assertNotIn('Exact Counting of Turn-Boundary Positions', catchup)
        self.assertIn(r'\bibitem{isaksen2015}', catchup)
        self.assertIn('small-deficit strategy fails', catchup)

    def test_astra_ultra_rank_51_to_100_batch_has_complete_public_attempts(self):
        # Frozen IDs of the October 2026 batch; ranks may subsequently change.
        expected = '''C73-51 C72-52 C62-53 C14-54 C14-55 D82-56 C21-57 H21-58
            D63-59 F38-60 Q58-61 D78-62 C73-63 D82-64 C44-65 G28-66 D83-67 E10-68
            C33-69 D63-70 C73-71 D63-72 C61-73 L94-74 G28-75 L13-76 C73-77 D82-78
            C14-79 C32-80 G12-81 C73-82 D44-83 D63-84 H21-85 D63-86 C44-87 Q54-88
            L22-89 D63-90 C14-91 D82-92 C61-93 D82-94 D47-95 J65-96 D63-97 C73-98
            C22-99 G18-100'''.split()
        self.assertEqual(len(set(expected)), 50)
        data = build_economics_data()
        for problem_id in expected:
            with self.subTest(problem_id=problem_id):
                attacks = [attack for attack in data[problem_id]['attacks']
                           if attack['model'] == 'GPT 6 Astra Ultra' and attack['version'] == 1]
                self.assertEqual(len(attacks), 1)
                attack = attacks[0]
                self.assertEqual(attack['status'], 'unresolved')
                self.assertEqual(attack['entry_kind'], 'research_attempt')
                public = (BASE_DIR / attack['file_path']).read_text()
                self.assertIn(r'\begin{proof}', public)
                self.assertIn(r'\begin{thebibliography}', public)
                self.assertNotRegex(public, r'/Users/|/private/tmp/|/home/|/mnt/data|MERGED_PROBLEM')

    def test_astra_ultra_rank_101_to_150_batch_preserves_identities_and_claim_statuses(self):
        # Frozen IDs of this batch; later rank changes do not change its identity.
        expected = '''C21-101 D44-102 Q58-103 C31-104 F34-105 C78-106 C73-107
            D44-108 L41-109 D51-110 C14-111 G28-112 C73-113 C55-114 C22-115
            C78-116 C14-117 F33-118 Q55-119 L23-120 C31-121 C78-122 C61-123
            C31-124 C54-125 C12-126 D44-127 C45-128 C31-129 D63-130 C72-131
            D86-132 H87-133 C78-134 C72-135 C78-136 E63-137 C78-138 C32-139
            D62-140 E71-141 C72-142 H26-143 D63-144 C73-145 C31-146 C21-147
            C14-148 C63-149 H63-150'''.split()
        self.assertEqual(len(set(expected)), 50)
        data = build_economics_data()
        for problem_id in expected:
            with self.subTest(problem_id=problem_id):
                attempts = [attack for attack in data[problem_id]['attacks']
                            if attack['model'] == 'GPT 6 Astra Ultra' and attack['version'] == 1]
                self.assertEqual(len(attempts), 1)
                attack = attempts[0]
                claim = 'solved' if problem_id in {'C72-131', 'C78-134'} else 'unresolved'
                self.assertEqual(attack['status'], claim)
                self.assertEqual(data[problem_id]['llm_status'], claim)
                self.assertEqual(data[problem_id]['status'], 'solved' if claim == 'solved' else 'open')
                self.assertEqual(attack['entry_kind'], 'research_attempt')
                self.assertEqual(attack['date_posted'], '2026-10-09')
                source = BASE_DIR / attack['file_path']
                self.assertEqual(source.name, problem_id + '.tex')
                self.assertEqual(source.read_bytes(), (BASE_DIR / 'docs' / attack['download_url']).read_bytes())
                self.assertIn(r'\begin{proof}', source.read_text())
                self.assertNotRegex(source.read_text(), r'/Users/|/private/tmp/|/home/|/mnt/data|TODO|proof omitted')

    def test_opus_rank_351_to_400_batch_preserves_identities_and_downloads(self):
        # Frozen IDs of the ranks 351--400 batch; later rank changes do not change its identity.
        expected = '''J62-351 C78-352 C78-353 G12-354 F33-355 D74-356 D31-357 L13-358
            D43-359 C55-360 R23-361 K42-362 Q51-363 G12-364 I18-365 C72-366 R38-367
            C81-368 C78-369 O25-370 Q54-371 C23-372 C78-373 O17-374 E21-375 O34-376
            H24-377 O31-378 D31-379 R23-380 F12-381 L13-382 C33-383 H24-384 D73-385
            D82-386 C78-387 L94-388 D72-389 C31-390 C73-391 C78-392 I13-393 Q25-394
            E52-395 D63-396 G11-397 Q52-398 F31-399 J23-400'''.split()
        self.assertEqual(len(set(expected)), 50)
        data = build_economics_data()
        opus = {problem_id for problem_id, record in data.items()
                if any(attack['model'] == 'Claude Opus 5.5 High' for attack in record['attacks'])}
        self.assertEqual(opus, set(expected))
        for problem_id in expected:
            with self.subTest(problem_id=problem_id):
                attempts = [attack for attack in data[problem_id]['attacks']
                            if attack['model'] == 'Claude Opus 5.5 High']
                self.assertEqual(len(attempts), 1)
                attack = attempts[0]
                self.assertEqual(attack['version'], 1)
                self.assertEqual(attack['status'], 'unresolved')
                self.assertEqual(attack['entry_kind'], 'research_attempt')
                self.assertEqual(attack['date_posted'], '2026-10-09')
                self.assertEqual(data[problem_id]['status'], 'open')
                source = BASE_DIR / attack['file_path']
                self.assertEqual(source.parent.name, 'opus_5.5_high')
                self.assertEqual(source.name, problem_id + '.tex')
                self.assertEqual(source.read_bytes(), (BASE_DIR / 'docs' / attack['download_url']).read_bytes())
                public = source.read_text()
                self.assertIn(r'\begin{proof}', public)
                self.assertIn(r'\begin{thebibliography}', public)
                self.assertNotRegex(public, r'/Users/|/private/tmp/|/home/|/mnt/data|TODO|proof omitted')

    def test_ultra_batch_preserves_problem_identity_and_public_downloads(self):
        data = build_economics_data()
        ultra = {problem_id: [attack for attack in record['attacks']
                              if attack['file_path'].startswith('attacks/open_problems/economics/gpt6_astra_ultra/')]
                 for problem_id, record in data.items() if problem_id in ULTRA_BATCH_IDS}
        self.assertEqual({problem_id for problem_id, attacks in ultra.items() if attacks}, ULTRA_BATCH_IDS)
        for problem_id in ULTRA_BATCH_IDS:
            with self.subTest(problem_id=problem_id):
                self.assertEqual(len(ultra[problem_id]), 1)
                attack = ultra[problem_id][0]
                expected_claim = 'solved' if problem_id == 'C65-45' else 'unresolved'
                self.assertEqual(attack['version'], 1)
                self.assertEqual(attack['entry_kind'], 'research_attempt')
                self.assertEqual(attack['status'], expected_claim)
                # The Pro manuscript for C71-12 separately claims a full solution.
                aggregate_claim = 'solved' if problem_id in {'C65-45', 'C71-12'} else 'unresolved'
                self.assertEqual(data[problem_id]['llm_status'], aggregate_claim)
                self.assertEqual(data[problem_id]['status'],
                                 'solved' if aggregate_claim == 'solved' else 'open')
                if problem_id == 'C71-12':
                    pro = [a for a in data[problem_id]['attacks'] if a['model'] == 'GPT 6 Astra Pro']
                    self.assertEqual([a['status'] for a in pro], ['solved'])
                    self.assertEqual(data[problem_id]['completion'], 100)
                    self.assertEqual(data[problem_id]['completion_source'], 'llm_claim')
                    self.assertEqual(data[problem_id]['source_status'], 'open')
                    self.assertEqual(pro[0]['completion'], 100)
                    self.assertEqual(attack['completion'], 15)
                self.assertTrue(attack['file_path'].startswith('attacks/open_problems/economics/gpt6_astra_ultra/'))
                self.assertTrue(attack['download_url'].startswith('data/economics/attempts/gpt6_astra_ultra/'))
                source = (BASE_DIR / attack['file_path']).read_bytes()
                self.assertEqual((BASE_DIR / 'docs' / attack['download_url']).read_bytes(), source)
                self.assertNotRegex(source.decode(), r'/Users/|/home/|/mnt/data|/workspace/|uploaded filename')

    def test_astra_ultra_rank_151_to_200_batch_keeps_fixed_ids_and_exact_downloads(self):
        # Freeze the selected identities, so later reranking cannot move manuscripts.
        expected = '''D82-151 E58-152 C72-153 C21-154 O31-155 C12-156 E52-157 D63-158
            C73-159 C21-160 F12-161 D31-162 Q54-163 I18-164 C78-165 L94-166
            E62-167 C31-168 C14-169 D73-170 D44-171 D82-172 C21-173 D47-174
            C78-175 Q54-176 D63-177 C78-178 C21-179 D71-180 C26-181 C62-182
            H24-183 C21-184 J42-185 C44-186 H11-187 C23-188 D82-189 D71-190
            C21-191 Q51-192 G28-193 C21-194 L42-195 D44-196 D72-197 G21-198
            C72-199 C83-200'''.split()
        self.assertEqual(len(set(expected)), 50)
        data = build_economics_data()
        for problem_id in expected:
            with self.subTest(problem_id=problem_id):
                attempts = [attack for attack in data[problem_id]['attacks']
                            if attack['model'] == 'GPT 6 Astra Ultra' and attack['version'] == 1]
                self.assertEqual(len(attempts), 1)
                attack = attempts[0]
                self.assertEqual(attack['status'], 'unresolved')
                self.assertEqual(data[problem_id]['status'], 'open')
                self.assertEqual(attack['entry_kind'], 'research_attempt')
                self.assertEqual(attack['date_posted'], '2026-10-09')
                self.assertEqual(attack['file_path'],
                                 f'attacks/open_problems/economics/gpt6_astra_ultra/{problem_id}.tex')
                self.assertEqual(attack['download_url'],
                                 f'data/economics/attempts/gpt6_astra_ultra/{problem_id}.tex')
                source = (BASE_DIR / attack['file_path']).read_bytes()
                self.assertEqual(source, (BASE_DIR / 'docs' / attack['download_url']).read_bytes())
                text = source.decode()
                self.assertIn(r'\begin{proof}', text)
                self.assertIn(r'\begin{thebibliography}', text)
                self.assertNotRegex(text, r'/Users/|/home/|/mnt/data|/workspace/|TODO|proof omitted')

    def test_astra_ultra_rank_451_to_500_batch_preserves_ids_and_reviewed_claims(self):
        # These permanent IDs identify the batch even after future rank updates.
        expected = '''E32-451 J14-452 C21-453 I38-454 G12-455 E32-456 L95-457 D31-458
            D83-459 D24-460 J16-461 I13-462 E43-463 C78-464 I38-465 G23-466
            E31-467 H22-468 C21-469 E42-470 E32-471 D84-472 D63-473 I15-474
            L41-475 D72-476 G28-477 O33-478 D83-479 D83-480 G12-481 D91-482
            L94-483 I18-484 Q54-485 I11-486 C73-487 C72-488 C72-489 Q16-490
            C31-491 C73-492 F18-493 C21-494 L51-495 C73-496 J62-497 F23-498
            D91-499 Q58-500'''.split()
        self.assertEqual(len(set(expected)), 50)
        data = build_economics_data()
        for problem_id in expected:
            with self.subTest(problem_id=problem_id):
                attempts = [attack for attack in data[problem_id]['attacks']
                            if attack['model'] == 'GPT 6 Astra Ultra' and attack['version'] == 1]
                self.assertEqual(len(attempts), 1)
                attack = attempts[0]
                claim = 'solved' if problem_id in {'C73-487', 'C73-496'} else 'unresolved'
                self.assertEqual(attack['status'], claim)
                self.assertEqual(data[problem_id]['llm_status'], claim)
                self.assertEqual(data[problem_id]['status'], 'solved' if claim == 'solved' else 'open')
                self.assertEqual(attack['entry_kind'], 'research_attempt')
                self.assertEqual(attack['date_posted'], '2026-10-09')
                self.assertEqual(attack['file_path'],
                                 f'attacks/open_problems/economics/gpt6_astra_ultra/{problem_id}.tex')
                self.assertEqual(attack['download_url'],
                                 f'data/economics/attempts/gpt6_astra_ultra/{problem_id}.tex')
                source = (BASE_DIR / attack['file_path']).read_bytes()
                self.assertEqual(source, (BASE_DIR / 'docs' / attack['download_url']).read_bytes())
                text = source.decode()
                self.assertIn(r'\begin{proof}', text)
                self.assertIn(r'\begin{thebibliography}', text)
                self.assertNotRegex(text, r'/Users/|/home/|/mnt/data|/workspace/|TODO|proof omitted')

    def test_astra_ultra_rank_201_to_250_attempts_preserve_problem_identity(self):
        # Fixed IDs of the batch selected on 2026-10-09, independent of reranking.
        expected = set('L52-201 C21-202 C78-203 O34-204 D82-205 C21-206 O31-207 Q54-208 C63-209 C21-210 R42-211 O34-212 C78-213 C31-214 C18-215 D72-216 C78-217 D83-218 C31-219 J12-220 G12-221 F18-222 Q54-223 E42-224 C78-225 C23-226 C78-227 F13-228 D15-229 F13-230 E32-231 C21-232 C83-233 C21-234 G28-235 I18-236 C78-237 D44-238 C44-239 Q41-240 I32-241 D63-242 D83-243 C21-244 H22-245 C61-246 F32-247 C44-248 G12-249 F16-250'.split())
        self.assertEqual(len(expected), 50)
        data = build_economics_data()
        for problem_id in expected:
            with self.subTest(problem_id=problem_id):
                attempts = [a for a in data[problem_id]['attacks']
                            if a['file_path'] ==
                            f'attacks/open_problems/economics/gpt_6_astra_ultra/{problem_id}.tex']
                self.assertEqual(len(attempts), 1)
                attempt = attempts[0]
                self.assertEqual(attempt['model'], 'GPT 6 Astra Ultra')
                self.assertEqual(attempt['entry_kind'], 'research_attempt')
                self.assertEqual(attempt['date_posted'], '2026-10-09')
                self.assertEqual(data[problem_id]['status'], 'open')
                self.assertEqual(attempt['status'], 'unresolved')
                source = BASE_DIR / attempt['file_path']
                self.assertEqual(source.read_bytes(),
                                 (BASE_DIR / 'docs' / attempt['download_url']).read_bytes())
                self.assertIn(r'\begin{proof}', source.read_text())
                self.assertIn(r'\begin{thebibliography}', source.read_text())
                self.assertNotRegex(source.read_text(), r'/Users/|/private/tmp/|/mnt/data/|TODO')

    def test_astra_ultra_rank_551_to_600_attempts_preserve_identity_and_claim_scope(self):
        # Freeze the selected identities, so later reranking cannot reassign proofs.
        expected = set('I11-551 E62-552 C21-553 C78-554 L13-555 E43-556 H41-557 D91-558 D84-559 J13-560 I11-561 J62-562 O41-563 C73-564 F13-565 L11-566 D81-567 I38-568 C21-569 Q23-570 D83-571 E52-572 F37-573 J42-574 F35-575 E31-576 I11-577 D91-578 L94-579 M12-580 C21-581 G14-582 E62-583 G41-584 J24-585 D83-586 D91-587 C73-588 C72-589 J24-590 I21-591 J16-592 O32-593 E37-594 L26-595 O47-596 C73-597 O33-598 M21-599 E58-600'.split())
        self.assertEqual(len(expected), 50)
        data = build_economics_data()
        for problem_id in expected:
            with self.subTest(problem_id=problem_id):
                source_path = f'attacks/open_problems/economics/gpt_6_astra_ultra/{problem_id}.tex'
                attempts = [a for a in data[problem_id]['attacks']
                            if a['file_path'] == source_path]
                self.assertEqual(len(attempts), 1)
                attempt = attempts[0]
                self.assertEqual(attempt['model'], 'GPT 6 Astra Ultra')
                self.assertEqual(attempt['entry_kind'], 'research_attempt')
                self.assertEqual(attempt['date_posted'], '2026-10-09')
                claim = 'solved' if problem_id == 'C78-554' else 'unresolved'
                self.assertEqual(attempt['status'], claim)
                # Keep source status distinct from the displayed LLM claim.
                self.assertEqual(data[problem_id].get('source_status', data[problem_id]['status']), 'open')
                self.assertEqual(data[problem_id]['status'], 'solved' if claim == 'solved' else 'open')
                source = BASE_DIR / source_path
                self.assertEqual(source.read_bytes(),
                                 (BASE_DIR / 'docs' / attempt['download_url']).read_bytes())
                text = source.read_text()
                self.assertIn(r'\begin{proof}', text)
                self.assertIn(r'\begin{thebibliography}', text)
                self.assertNotRegex(text, r'/Users/|/private/tmp/|/mnt/data/|TODO|proof omitted')

    def test_specialized_and_merged_source_conventions_are_present(self):
        data = build_economics_data()
        self.assertIn('BSDE conventions for SC-01--SC-06', data['C65-6']['definition_tex'])
        self.assertIn('Additional-source status and mathematical conventions', data['D63-3']['definition_tex'])
        self.assertIn('Source formulation: Game theory (GT-056)', data['D63-3']['definition_tex'])
        self.assertEqual(data['C73-10']['reference_aliases'], {'problem:OP-0590': 'C73-1'})
        records = load_registry()['problems']
        by_source = {record['source_original_id']: record for record in records
                     if record['source_catalog'] == 'Beyond game theory'}
        for source_id in ('SC-07', 'SC-08'):
            self.assertIn('Control and stopping conventions for SC-07--SC-08',
                          data[by_source[source_id]['id']]['definition_tex'])


if __name__ == '__main__':
    unittest.main()
