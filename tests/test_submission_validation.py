"""Prospective submission checks must preserve historical research and identity."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

import build_site
from scripts.validate_submissions import (ROOT, classify, load_catalogs, scan_tex,
                                          validate, validate_file)


RESEARCH_PATH = 'attacks/open_problems/erdos/model/5.tex'


def research(status='partial', percentage=25, category='erdos', identifier='5'):
    declaration = {
        'kind': 'research_attempt', 'category': category, 'problem_id': identifier,
        'model': {'provider': 'OpenAI', 'version': 'GPT-6', 'reasoning': 'Astra Ultra',
                  'generated_on': '2026-10-10'},
        'other_models': 'None', 'tools': 'None', 'target': 'The entire original target.',
        'scope': 'A specified special case is proved; the full problem remains open.',
        'human_contributions': 'None; prompting only.',
        'verification': 'Model self-audit only; no independent human checking.',
        'reproducibility': 'Prompts A/B; artifacts not available.',
    }
    full = {'target': 'Original statement', 'result': 'Theorem 1', 'coverage': 'All cases',
            'dependencies': 'None', 'human_verification': 'None',
            'unverified': 'All proofs', 'novelty': 'Not checked'}
    headers = '% SUBMISSION: ' + json.dumps(declaration) + '\n'
    headers += '% ATTEMPT_STATUS: ' + status + '\n'
    if status == 'solved':
        headers += '% FULL_SOLUTION_SCOPE: ' + json.dumps(full) + '\n'
    return headers + r'''\documentclass{article}
\author{GPT-6 Astra Ultra}
\begin{document}
\section{Original target and scope}
Original problem and precise target; a special case is considered.
\section{Results}
An actual lemma and its proof, with remaining gaps described.
\section{Completion Estimate}
\noindent\textbf{COMPLETION: ''' + str(percentage) + r'''\%}
Proved the stated special case; the general quantifiers remain open.
\section*{References}
Original problem source, https://www.erdosproblems.com/5.
\end{document}
'''


def replace_header(content, key, transform):
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if line.startswith('% ' + key + ': '):
            value = json.loads(line.split(': ', 1)[1])
            transform(value)
            lines[index] = '% ' + key + ': ' + json.dumps(value)
    return '\n'.join(lines) + '\n'


def statement_header(category='top_problems', identifier='1', proposal='established'):
    declaration = {'kind': 'statement_only', 'category': category, 'problem_id': identifier,
                   'proposal_type': proposal, 'source': 'Primary source and URL',
                   'status_evidence': 'Source status checked; limitations disclosed',
                   'status_checked_on': '2026-10-10',
                   'duplicate_check': 'Repository, source, literature and equivalence checked',
                   'attribution': 'Original proposer; LLM preparation disclosed'}
    if proposal == 'new_conjecture':
        declaration.update({key: 'Actual evidence or limitations stated' for key in
                            ('proposer', 'motivation', 'related_problems', 'boundary_tests',
                             'counterexample_search', 'nontriviality', 'novelty_disclosure')})
    return '% SUBMISSION: ' + json.dumps(declaration) + '\n'


class SubmissionValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        top = json.loads((ROOT / 'lists/unsolvedmath/problems.json').read_text())[0]
        econ = json.loads((ROOT / 'lists/economics/problems.json').read_text())
        econ['problems'] = [econ['problems'][0]]
        econ['problem_count'] = 1
        self.top = top
        self.econ = econ['problems'][0]
        self.write('lists/unsolvedmath/problems.json', json.dumps([top]))
        self.write('lists/unsolvedmath/display_order.json', '[1]')
        self.write('lists/economics/problems.json', json.dumps(econ))
        self.write('lists/economics/rankings.csv', 'Problem ID,New rank\nC73-1,1\n')
        self.write('lists/erdos_problems.csv', 'number,status,problem_url\n5,open,https://www.erdosproblems.com/5\n')
        self.write('lists/erdos_status.json', '{"problems":{"5":{}}}')
        self.write('lists/mo_problems.csv', 'question_id,title,link\n123,Example,https://mathoverflow.net/questions/123/example\n')
        self.top_path = 'attacks/open_problems/top_problems/definitions/1.tex'
        self.econ_path = 'attacks/open_problems/economics/statements/C73-1.tex'
        self.write(self.top_path, (ROOT / self.top_path).read_text())
        self.write(self.econ_path, (ROOT / self.econ_path).read_text())
        self.catalogs = load_catalogs(self.root)

    def write(self, path, content):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)

    def check(self, content, path=RESEARCH_PATH):
        self.write(path, content)
        return validate_file(self.root, path, self.catalogs)

    def reject(self, content, message, path=RESEARCH_PATH):
        with self.assertRaisesRegex(ValueError, message):
            self.check(content, path)

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout

    def init_baseline(self):
        self.git('init', '-q')
        self.git('add', '.')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                 'commit', '-qm', 'legacy baseline')

    def test_valid_research_and_build_compatible_syntax(self):
        self.assertIn('research declaration', self.check(research()))
        self.assertEqual(build_site.extract_completion(research()), 25)
        self.assertEqual(build_site.parse_attack(research(), 'model')['status'], 'unresolved')

    def test_missing_completion(self):
        self.reject(research().replace(r'\section{Completion Estimate}', r'\section{Progress}'), 'Completion Estimate')

    def test_invalid_completion_percentage(self):
        for number in (-1, 101, 'NaN', 'quarter'):
            with self.subTest(number=number):
                self.reject(research(percentage=number), 'numeric COMPLETION')

    def test_partial_and_unresolved_cannot_be_100(self):
        for status in ('partial', 'unresolved'):
            self.reject(research(status, 100), 'cannot claim 100')

    def test_solved_requires_full_scope(self):
        tex = research('solved', 100)
        tex = '\n'.join(line for line in tex.splitlines() if not line.startswith('% FULL_SOLUTION_SCOPE:'))
        self.reject(tex, 'FULL_SOLUTION_SCOPE')

    def test_valid_solved_and_each_scope_field_required(self):
        self.check(research('solved', 100))
        for field in ('target', 'result', 'coverage', 'dependencies', 'human_verification', 'unverified', 'novelty'):
            with self.subTest(field=field):
                tex = replace_header(research('solved', 100), 'FULL_SOLUTION_SCOPE', lambda obj: obj.pop(field))
                self.reject(tex, field)

    def test_missing_model_and_human_declarations(self):
        self.reject(replace_header(research(), 'SUBMISSION', lambda obj: obj.pop('model')), 'model attribution')
        self.reject(replace_header(research(), 'SUBMISSION', lambda obj: obj.pop('human_contributions')), 'human_contributions')

    def test_generic_model_requires_honest_version_uncertainty(self):
        tex = replace_header(research(), 'SUBMISSION', lambda obj: obj['model'].update(version='ChatGPT'))
        self.reject(tex, 'version_uncertainty')
        tex = replace_header(tex, 'SUBMISSION', lambda obj: obj['model'].update(version_uncertainty='Interface did not expose version'))
        self.check(tex)

    def test_missing_references(self):
        self.reject(research().replace(r'\section*{References}', r'\section*{Notes}'), 'References')

    def test_standard_bibliographies(self):
        for bibliography in (r'\begin{thebibliography}{9}\bibitem{original}Source.\end{thebibliography}',
                             r'\bibliography{original}', r'\printbibliography'):
            tex = research().split(r'\section*{References}')[0] + bibliography + '\n' + r'\end{document}'
            self.check(tex)

    def test_completion_parser_window_and_justification(self):
        tex = research().replace(r'\noindent\textbf{COMPLETION:', '\n\n\n' + r'\noindent\textbf{COMPLETION:')
        self.reject(tex, 'site parser')
        self.reject(research().replace('Proved the stated special case; the general quantifiers remain open.', ''), 'justification')

    def test_other_headings_are_flexible(self):
        self.check(research().replace('Original target and scope', 'Framework').replace('Results', 'Lemmas'))

    def test_valid_top_statement_no_completion(self):
        tex = statement_header() + (ROOT / self.top_path).read_text()
        self.assertIn('statement-only', self.check(tex, self.top_path))
        self.assertIsNone(build_site.extract_completion(tex))

    def test_top_statement_source_structure_and_headings(self):
        tex = statement_header() + (ROOT / self.top_path).read_text()
        self.reject(tex.replace(r'\subsection{Sources}', r'\subsection{Notes}'), 'sources', self.top_path)
        self.reject(tex.replace(r'\subsection{Short English statement}', '% ' + r'\subsection{Short English statement}'), 'summary', self.top_path)

    def test_statement_rejects_research_metadata(self):
        tex = statement_header() + (ROOT / self.top_path).read_text()
        for header in ('% ATTEMPT_STATUS: unresolved\n', '% FULL_SOLUTION_SCOPE: {}\n'):
            self.reject(header + tex, 'research status', self.top_path)
        tex = replace_header(tex, 'SUBMISSION', lambda obj: obj.update(model={'version': 'GPT-6'}))
        self.reject(tex, 'research-attempt fields', self.top_path)

    def test_statement_rejects_completion(self):
        tex = statement_header() + (ROOT / self.top_path).read_text()
        tex = tex.replace(r'\end{document}', r'\section{Completion Estimate} 100\%' + '\n' + r'\end{document}')
        self.reject(tex, 'completion estimates', self.top_path)

    def test_new_conjecture_declarations(self):
        tex = statement_header(proposal='new_conjecture') + (ROOT / self.top_path).read_text()
        self.check(tex, self.top_path)
        self.reject(replace_header(tex, 'SUBMISSION', lambda obj: obj.pop('novelty_disclosure')), 'novelty_disclosure', self.top_path)

    def test_valid_economics_statement_and_boundaries(self):
        tex = statement_header('economics', 'C73-1') + (ROOT / self.econ_path).read_text()
        self.check(tex, self.econ_path)
        self.reject(tex.replace('% BEGIN ECONOMICS STATEMENT', '% OTHER'), 'boundary pair', self.econ_path)
        # A literal example is not a real boundary, even if the real pair is absent.
        fake = tex.replace('% BEGIN ECONOMICS STATEMENT', '\\begin{verbatim}\n% BEGIN ECONOMICS STATEMENT\n\\end{verbatim}')
        self.reject(fake, 'boundary pair', self.econ_path)

    def test_new_economics_statement_requires_registration(self):
        tex = statement_header('economics', 'C73-2') + (ROOT / self.econ_path).read_text()
        self.reject(tex, 'Unregistered economics', 'attacks/open_problems/economics/statements/C73-2.tex')

    def test_valid_economics_attempt_metadata(self):
        tex = '% ECONOMICS_PROBLEM: ' + json.dumps({key: self.econ[key] for key in ('id', 'title', 'jel_code', 'source_id')}) + '\n'
        tex += '% FIRST_POSTED: 2026-10-10\n' + research(category='economics', identifier='C73-1')
        path = 'attacks/open_problems/economics/model/C73-1.tex'
        self.check(tex, path)
        self.reject(tex.replace('OP-0590', 'OP-9999'), 'source_id', path)
        self.reject(tex.replace('FIRST_POSTED: 2026-10-10', 'FIRST_POSTED: 2026-02-30'), 'day is out of range', path)

    def test_top_attempt_requires_matching_header(self):
        header = '% TOP_PROBLEM: ' + json.dumps({key: self.top[key] for key in ('id', 'title', 'category_id', 'status')}) + '\n'
        tex = header + research(category='top_problems', identifier='1')
        path = 'attacks/open_problems/top_problems/model/1.tex'
        self.check(tex, path)
        self.reject(tex.replace('"id": 1', '"id": 2'), 'id does not match', path)

    def test_mo_filename_and_identity(self):
        self.check(research(category='mo', identifier='123'), 'attacks/open_problems/mo/model/123-title_v2.tex')
        self.reject(research(category='mo', identifier='123'), 'category filename', 'attacks/open_problems/mo/model/123.tex')

    def test_invalid_category_ids_locations_and_versions(self):
        for path in ('attacks/open_problems/erdos/model/0.tex',
                     'attacks/open_problems/economics/model/8.tex',
                     'attacks/open_problems/top_problems/definitions/1_v2.tex',
                     'attacks/open_problems/erdos/statements/5.tex',
                     'attacks/open_problems/erdos/model/5_v1.tex',
                     'attacks/open_problems/unknown/model/5.tex'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                classify(path)
        self.reject(research(), 'Unregistered', 'attacks/open_problems/erdos/model/99999.tex')
        self.reject(research().replace('"problem_id": "5"', '"problem_id": "6"'), 'file identity')

    def test_valid_v2_v3(self):
        for version in (2, 3):
            self.check(research(), f'attacks/open_problems/erdos/model/5_v{version}.tex')

    def test_commented_and_verbatim_headings_do_not_count(self):
        for substitute in ('% ' + r'\section{Completion Estimate}',
                           r'\verb|\section{Completion Estimate}|',
                           '\\begin{verbatim}\n\\section{Completion Estimate}\n\\end{verbatim}',
                           '\\begin{lstlisting}\n\\section{Completion Estimate}\n\\end{lstlisting}'):
            with self.subTest(substitute=substitute):
                self.reject(research().replace(r'\section{Completion Estimate}', substitute), 'Completion Estimate')
        self.reject(research().replace(r'\section*{References}', '% ' + r'\section*{References}'), 'References')

    def test_literal_metadata_and_escaped_comment_handling(self):
        tex = research()
        line, rest = tex.split('\n', 1)
        self.reject('\\begin{verbatim}\n' + line + '\n\\end{verbatim}\n' + rest, 'SUBMISSION')
        active, _ = scan_tex('Visible \\% retained. % hidden\n\\\\% hidden too\n')
        self.assertIn(r'\%', active)
        self.assertNotIn('hidden', active)

    def test_conflicting_status_and_entry_kind(self):
        self.reject('% ATTEMPT_STATUS: solved\n' + research(), 'exactly one')
        self.reject('% ENTRY_KIND: statement_only\n' + research(), 'ENTRY_KIND')
        tex = research().replace(r'\section{Results}', '\\section{Final status}\nSOLVED\n\\section{Results}')
        self.reject(tex, 'Final status conflicts')

    def test_duplicate_registry_ids_and_inconsistent_order(self):
        self.write('lists/unsolvedmath/problems.json', json.dumps([self.top, self.top]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            load_catalogs(self.root)
        self.write('lists/unsolvedmath/problems.json', json.dumps([self.top]))
        self.write('lists/unsolvedmath/display_order.json', '[1,1]')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            load_catalogs(self.root)

    def test_duplicate_economics_ids(self):
        registry = json.loads((self.root / 'lists/economics/problems.json').read_text())
        registry['problems'].append(copy.deepcopy(self.econ))
        registry['problem_count'] = 2
        self.write('lists/economics/problems.json', json.dumps(registry))
        with self.assertRaisesRegex(ValueError, 'Duplicate permanent'):
            load_catalogs(self.root)

    def test_mo_url_identity_and_duplicate_csv(self):
        self.write('lists/mo_problems.csv', 'question_id,title,link\n123,Example,https://mathoverflow.net/questions/124/example\n')
        with self.assertRaisesRegex(ValueError, 'source URL'):
            load_catalogs(self.root)
        self.write('lists/mo_problems.csv', 'question_id,title,link\n123,A,x\n123,B,y\n')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            load_catalogs(self.root)

    def test_unchanged_legacy_skipped_changed_file_strict(self):
        self.write(RESEARCH_PATH, 'Historical fragment without modern sections.\n')
        self.init_baseline()
        checked, _, errors = validate(self.root, [RESEARCH_PATH], base='HEAD')
        self.assertEqual((checked, errors), ([], []))
        self.write(RESEARCH_PATH, 'Historical fragment with a new edit.\n')
        self.assertTrue(validate(self.root, base='HEAD')[2])
        self.write(RESEARCH_PATH, research())
        self.assertEqual(validate(self.root, base='HEAD')[0], [RESEARCH_PATH])
        self.assertFalse(validate(self.root, base='HEAD')[2])

    def test_untracked_submissions_checked_and_invalid_base_fails(self):
        self.init_baseline()
        self.write(RESEARCH_PATH, research())
        self.assertEqual(validate(self.root, base='HEAD')[0], [RESEARCH_PATH])
        self.assertTrue(validate(self.root, base='no-such-ref')[2])

    def test_deleting_or_renaming_legacy_submission_rejected(self):
        self.write(RESEARCH_PATH, 'Legacy work')
        self.init_baseline()
        (self.root / RESEARCH_PATH).unlink()
        self.assertTrue(any('historical submission links' in error for error in validate(self.root, base='HEAD')[2]))
        self.write(RESEARCH_PATH.replace('5.tex', '5_v2.tex'), 'Legacy work')
        self.git('add', '-A')
        self.assertTrue(any('historical submission links' in error for error in validate(self.root, base='HEAD')[2]))

    def test_baseline_catalogue_code_link_and_alias_preservation(self):
        self.init_baseline()
        changed = copy.deepcopy(self.top)
        changed['problem_number'] = 'OTHER'
        changed['external_url'] = 'https://www.unsolvedmath.com/problems/OTHER'
        self.write('lists/unsolvedmath/problems.json', json.dumps([changed]))
        self.assertTrue(any('permanent' in error for error in validate(self.root, base='HEAD')[2]))
        changed = copy.deepcopy(self.top)
        changed['legacy_ids'] = []
        self.write('lists/unsolvedmath/problems.json', json.dumps([changed]))
        self.assertTrue(any('legacy identity' in error for error in validate(self.root, base='HEAD')[2]))

    def test_human_contribution_exception_does_not_invent_a_model(self):
        tex = '% TOP_PROBLEM: ' + json.dumps({key: self.top[key] for key in ('id', 'title', 'category_id', 'status')}) + '\n'
        tex += '% ENTRY_KIND: human_contribution\n\\section{References}\nOriginal source.\n'
        self.assertIn('human contribution', self.check(tex, 'attacks/open_problems/top_problems/Human_Contribution/1.tex'))

    def test_cli_representative_valid_and_invalid_fixtures(self):
        self.write(RESEARCH_PATH, research())
        command = [sys.executable, str(ROOT / 'scripts/validate_submissions.py'), '--root', str(self.root), RESEARCH_PATH]
        valid = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertIn('not verified', valid.stdout)
        self.write(RESEARCH_PATH, research(percentage=100))
        invalid = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 1)
        self.assertIn('cannot claim 100', invalid.stderr)
        wrong_location = subprocess.run(command[:-1] + ['elsewhere.tex'], capture_output=True, text=True)
        self.assertEqual(wrong_location.returncode, 1)

    def test_grandfathered_mo_duplicates_are_bounded_and_identical(self):
        header = 'question_id,title,link\n'
        row = '339137,Legacy,https://mathoverflow.net/questions/339137/legacy\n'
        self.write('lists/mo_problems.csv', header + row * 2)
        self.assertEqual(len(load_catalogs(self.root)['mo']), 1)
        self.write('lists/mo_problems.csv', header + row * 3)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            load_catalogs(self.root)
        self.write('lists/mo_problems.csv', header + row + row.replace('Legacy', 'Different'))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            load_catalogs(self.root)

    def test_duplicate_json_fields_fail_in_declarations(self):
        tex = research().replace('"problem_id": "5"', '"problem_id": "5", "problem_id": "6"')
        self.reject(tex, 'Duplicate JSON field')

    def test_economics_header_syntax_agrees_with_builder(self):
        header = '% ECONOMICS_PROBLEM: ' + json.dumps({key: self.econ[key] for key in ('id', 'title', 'jel_code', 'source_id')}) + '\n'
        tex = header + '% FIRST_POSTED: 2026-10-10\n' + research(category='economics', identifier='C73-1')
        path = 'attacks/open_problems/economics/model/C73-1.tex'
        for key in ('ECONOMICS_PROBLEM', 'FIRST_POSTED', 'ATTEMPT_STATUS'):
            with self.subTest(key=key):
                self.reject(tex.replace('% ' + key + ':', '  % ' + key + ':'), 'exact builder header', path)
        self.reject(tex + '% trailing comment\n', 'no trailing', path)

    def test_literal_extra_economics_boundaries_do_not_duplicate_real_pair(self):
        tex = statement_header('economics', 'C73-1') + (ROOT / self.econ_path).read_text()
        tex = tex.replace(r'\end{document}', '\\begin{verbatim}\n% BEGIN ECONOMICS STATEMENT\n% END ECONOMICS STATEMENT\n\\end{verbatim}\n\\end{document}')
        self.check(tex, self.econ_path)

    def test_baseline_economics_identity_and_source_links_protected(self):
        self.init_baseline()
        registry = json.loads((self.root / 'lists/economics/problems.json').read_text())
        registry['problems'][0]['source_id'] = 'OP-9999'
        self.write('lists/economics/problems.json', json.dumps(registry))
        self.assertTrue(any('source_id' in error for error in validate(self.root, base='HEAD')[2]))
        registry['problems'][0]['source_id'] = self.econ['source_id']
        self.write('lists/economics/problems.json', json.dumps(registry))
        self.write('lists/erdos_problems.csv', 'number,status,problem_url\n5,open,https://example.org/5\n')
        self.assertTrue(any('identity/link' in error for error in validate(self.root, base='HEAD')[2]))

    def test_erdos_database_identity_removal_rejected(self):
        self.write('lists/erdos_status.json', '{"problems":{"5":{},"6":{}}}')
        self.init_baseline()
        self.write('lists/erdos_status.json', '{"problems":{"5":{}}}')
        self.assertTrue(any('source-database identities' in error for error in validate(self.root, base='HEAD')[2]))

    def test_specialist_openai_claims_use_existing_validation(self):
        # Exercise a real pinned record against the validator without imposing
        # new research-manuscript fields on a historical external claim.
        from scripts.validate_submissions import scan_tex
        paths = sorted((ROOT / 'attacks/open_problems/top_problems/openai').glob('*.tex'))
        self.assertTrue(paths)
        raw = paths[0].read_text()
        _, headers = scan_tex(raw)
        metadata = json.loads(headers['TOP_PROBLEM'][0])
        self.write('lists/openai_math/manifest.json', (ROOT / 'lists/openai_math/manifest.json').read_text())
        path = paths[0].relative_to(ROOT).as_posix()
        self.write(path, raw)
        catalogs = {'top_problems': {str(metadata['id']): metadata}}
        self.assertIn('external claim', validate_file(self.root, path, catalogs))

    def test_no_implicit_retroactive_scan(self):
        self.assertTrue(validate(self.root)[2])


if __name__ == '__main__':
    unittest.main()
