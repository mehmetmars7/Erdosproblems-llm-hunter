# Contributing to Problem Hunting with LLMs

This is the authoritative contribution policy for research attempts and catalogue
statements. Partial progress and honest unresolved attempts are welcome. Formatting,
a successful build, an LLM self-review, and a community submission record do not
establish mathematical correctness or novelty.

These stronger requirements apply prospectively to new or changed mathematical
submissions. Unchanged historical manuscripts, completion estimates, attribution,
model folders, IDs, links, source statuses, and review records remain intact.
Prefer a new `_v2` or `_v3` manuscript for substantive revisions; preserve original
outputs and disclose corrections. Do not rewrite historical research to satisfy
these rules. Specialist external claims and human contributions have the explicit
exceptions described below.

## Accepted frontier models and exact identification

We prioritize advanced frontier systems with demonstrated mathematical reasoning:
GPT Astra Pro/Ultra (with exact GPT generation), advanced GPT Codex reasoning
configurations, Gemini Deep Think, Claude Opus high-reasoning configurations,
Harmonic Aristotle, and comparable mathematical reasoning systems. No model is
permanently designated the most advanced; explain a comparable system's suitability
in the PR. Historical folder spellings continue to work and must not be renamed.

Identify the provider, actual model/version, reasoning configuration where exposed,
generation date, other models materially used to draft/revise/check the mathematics,
and external computation or theorem-proving tools. Generic “GPT”, “ChatGPT”,
“Claude”, or “Gemini” alone is insufficient unless the platform truly does not expose
the underlying version: explicitly record that uncertainty, never invent a version.
The model folder and GitHub submitter are not sufficient attribution.

## Mathematical research manuscripts

Submit the complete mathematical output as repository-compatible LaTeX. A standalone
article is recommended; Erdős and MO fragments remain supported. Preserve the
original target, permanent ID, source, references, and original mathematical meaning.
Include the following information in clearly identifiable sections (mathematically
appropriate titles are allowed; only the Completion Estimate heading is exact):

- Original problem and source; exact statement investigated, definitions, conventions,
  assumptions, quantifiers, parameter ranges, and boundary cases.
- Literature/context check, actual results, proofs or explicit counterexamples,
  verification undertaken, and the first remaining gaps.
- Scope comparison with the entire original target; final status and completion
  estimate; References or standard bibliography.
- Actual LLM identity/version and process; human mathematical contributions, edits,
  independent verification, and model-assisted checking, with their scopes.

Keep a modified, restricted, or strengthened formulation separate from the original.
For example, continuous and Borel payoffs, finite and infinite horizons, one prior
and all priors, necessary and sufficient conditions, an equivalence and an effective
algorithm, restricted parameter ranges and the full range, and conditional and
unconditional results are different targets. Explain whether the result covers the
complete original problem. Do not silently repair ambiguities or redefine success.
A generic plan or a restatement of known results alone is not a new research result;
identify known material and any actual progress honestly.

## Full-solution claims and status

`ATTEMPT_STATUS` accepts `solved`, `partial`, or `unresolved`. `solved`, SOLVED,
and FULL SOLUTION may describe the original problem only when the manuscript claims
to settle **all** its quantifiers, assumptions, ranges, boundary cases, and bundled
questions by proof or disproof. A special case, improved bound, necessary condition,
auxiliary counterexample, or conditional theorem does not settle the original target.
A “complete characterization” in a title does not automatically make a result solved;
a tautological reformulation may not provide the requested substantive characterization.
Use `partial` for proved progress with remaining gaps, or `unresolved` when the target
remains unresolved without a substantiated progress claim. Make title, abstract,
status, conclusion, and estimate consistent. Quotations of rejected solved claims
must be explicitly identified as such.

Every new solved attempt needs a full-solution scope declaration stating the exact
original target, theorem/counterexample, coverage of all cases and quantifiers,
every significant external dependency, whether independent human proof checking
occurred, unverified portions, and whether novelty was checked. Supply it in the
manuscript and in the `FULL_SOLUTION_SCOPE` header below. This declaration is a claim,
not evidence that the proof is correct.

The build currently normalizes `partial` to `unresolved` for ordinary attempt
aggregation; the literal TeX status preserves the finer distinction. Source-catalogue
status, LLM claim status, and community-review verdict are separate. Economics
may show **solved (LLM claim)** and `source_status` separately; OpenAI external claims
use their scoped rules below. Erdős LLM column labels include a saved-database display
rule, not newly verified mathematics. Do not change source status or review metadata
to agree with a model claim. Never call a build or LLM self-assessment independent
proof verification.

## Completion estimates

Every new or changed research attempt must include the exact LaTeX heading and a
numeric declaration immediately below it (within the next three lines):

```tex
\section{Completion Estimate}
\noindent\textbf{COMPLETION: 25\%}
Proved [precise result]; [precise original-target gaps] remain.
```

Use one value between 0 and 100, including decimal percentages, and briefly justify
it mathematically. The existing `build_site.extract_completion` reads this syntax.
Keep confidence discussions and other percentages out of those first four lines.
This is subjective progress toward the **original problem**, not confidence in the
proof, probability of success, independent verification, length, or lemma count.
Only a full-solution claim may use 100%; partial/unresolved work must use less.
Legacy estimates are preserved. Statement-only catalogue documentation requires
neither this heading nor an estimate; complete documentation is not a solved problem.

## Model attribution and human authorship

An LLM-generated manuscript primarily identifies the actual LLM/version generating
its mathematics. Credit all material models and human contributions accurately.
Prompting, copying output, submitting files, formatting, compilation, a site build,
a superficial reading, or asking another model to check a proof does not by itself
justify human mathematical authorship.

A human may be an author for significant intellectual work, substantial development
of results, correction of a major proof, or rigorous checking of significant portions.
Describe that scope. Limited checking belongs in verification/contributions/
acknowledgments rather than automatically conferring authorship. For example:
“Jane Doe independently checked Lemma 3 and the hypotheses of Theorem 5. The remaining
proofs were generated by GPT-6 Astra Ultra and have not been independently verified
by a human.” Distinguish mathematical authorship, prompting/submission, editing,
verification, repository maintenance, and community review. Model-assisted checking
is not independent human checking. Use an explicit contributor declaration; automated
checks cannot infer intellectual significance from a person's name. Do not remove
historical names or infer authorship from a GitHub account.

## References and mathematical dependencies

Every attempt needs an identifiable References section (section/subsection,
starred or unstarred), `thebibliography`, `\bibliography{...}`, or
`\printbibliography`. A Sources subsection also counts for catalogue-style batches.
At minimum cite the original problem source. For every external theorem used, give
an identifiable bibliographic source, state the mathematical content precisely,
check hypotheses in the application, and explain its role. Disclose source uncertainty
and what was actually consulted. Do not invent citations, theorem numbers, publication
facts, novelty, or assertions that a source was verified. Prefer primary sources,
permanent links, DOI and arXiv records. Preserve third-party attribution, licence terms,
and change notices from [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Verification and reproducibility

Describe boundary/counterexample checks, proof audits, computation, and external
theorem-hypothesis checks with actual outcomes, failures, or “not performed”. Name
who checked which portions and whether checking was human independent or LLM-assisted.
Identify prompts/process, dates, material revisions, public scripts/input/output links
where available, software versions, seeds, dependencies, and theorem prover settings.
Do not publish private transcripts or secrets. Disclose missing artifacts and inaccessible
sources. Computation may support a proof without replacing it. Explain the scope of
formalization, extra axioms, `sorry`/`admit`, and what has not been checked.

## Adding New Open Problem Statements

This is a separate process from submitting research attempts. A statement is not a
solution and belongs in a category's catalogue mechanism, not a model folder merely
to increase attempt counts. Catalogue size alone is not a reason to accept conjectures.

### Established open problems

Supply a mathematical title, primary source and original proposer attribution, exact
original formulation, assumptions and quantifiers, definitions/notation, short English
explanation, known partial results, accurate references, current-status evidence and
date checked, and duplicate/related-problem checks. Use credible literature, preprints,
research databases, or appropriate scholarly sources; do not treat a model's recollection
as status evidence. Explain discrepancies with older source statuses instead of silently
changing them.

### Newly formulated conjectures

Additionally identify the proposer and every LLM's role, mathematical motivation,
relationship to known questions, elementary/boundary tests, counterexample search,
literature and duplicate checks, and why the question is nontrivial. Explicitly disclose
that model generation alone establishes neither novelty nor open status. Unsupported
LLM conjectures must not be presented as established literature problems.

### Identity and duplicate review

Before acceptance, compare repository statements, authoritative source databases,
relevant literature, equivalent formulations, already solved variants, permanent IDs,
and parent/subproblem relationships. Normally reuse an existing identity for the same
question. A restricted variant needs mathematical justification and maintainer-approved
identity review. IDs must never come from display ranks or be invented by an LLM.
Include the evidence and approval/allocation reference in the PR; automation cannot
detect mathematical equivalence or establish open status.

## Category-specific locations and catalogue requirements

| Category | Research attempts | Statement/identity authority |
| --- | --- | --- |
| Erdős | `attacks/open_problems/erdos/<model>/<number>[_vN].tex` | Authoritative Erdős number; `lists/erdos_status.json` and `lists/erdos_problems.csv`; source statement is linked externally |
| Top Open Problems | `attacks/open_problems/top_problems/<model>/<id>[_vN].tex` | `definitions/<id>.tex`, `lists/unsolvedmath/problems.json`, `display_order.json` |
| MathOverflow | `attacks/open_problems/mo/<model>/<question_id>-<title-slug>[_vN].tex` | Original question ID and verified `link` in `lists/mo_problems.csv` |
| Economics | `attacks/open_problems/economics/<model>/<permanent-id>[_vN].tex` | `statements/<permanent-id>.tex`, `lists/economics/problems.json`, `rankings.csv` |

`N` is an unused integer at least 2; existing versions must not be overwritten or
renamed. Use existing folder spellings. The website groups ranked and MO records under
Top Open Problems while retaining their separate identities and review paths.

### Erdős and MathOverflow

Never invent an Erdős number. Review/register an authoritative new number in the saved
source catalogue before adding attempts; preserve database status provenance and use
`scripts/sync_erdos_status.py` for source refreshes. Do not turn a new local conjecture
into an Erdős problem. MO proposals must retain the original numeric question ID and
verified `https://mathoverflow.net/questions/<id>/...` URL; check accepted answers,
edits, and recent evidence before calling it open. Add the corresponding CSV entry
without removing or changing existing identities. These catalogues link to source
statements; they have no generic new statement-only TeX importer. Record source,
status, duplicate, and attribution review in the PR rather than creating an unsupported
statement directory. Newly formulated local conjectures go through a reviewed local
Top Open Problems identity, not a fabricated MO question.

### Top Open Problems

Use canonical UnsolvedMath IDs, never display positions or public-code guesses.
Statement-only files preserve a matching `TOP_PROBLEM` JSON header,
`% ENTRY_KIND: statement_only`, and these nonempty subsections:

```tex
\subsection{Definitions and mathematical statement}
\subsection{Short English statement}
\subsection{Sources}
```

Keep source links/citations and relevant source licences. The portable registry,
definition metadata (`id`, `title`, `category_id`, `status`), and display order must
agree. Use the existing statement importer
`scripts/import_unsolvedmath_statements.py` with its full upstream registry and
labelled source input; it verifies identity and extends both site registry and order.
Inspect `--help` and review intended changes. Do not run migration scripts as an
append tool. New standalone outputs also need the prospective declaration below.

For genuinely new local targets, maintainers review provenance, duplicates, and scope
first. Allocate above all full-registry IDs and the external `id_registry.json`
watermark, retain an allocation report, use `LOCAL-<id>`, `published: false`, no
upstream URL, and parent IDs for a justified subcase. The specialized
`scripts/allocate_openai_problem_ids.py` can produce/reserve IDs from identity-reviewed
proposals against a **complete external registry and watermark**; it is not a universal
allocator, source-status reviewer, or page writer. Its OpenAI adjudication requirements
remain in force for that workflow. Commit the reviewed site registry, definition, and
order together; preserve legacy URL aliases.

### Economics

Use the registered permanent ID, not current rank or the sometimes reused source OP
ID. Every research attempt is a complete standalone document with exactly one matching
`ECONOMICS_PROBLEM` JSON header (`id`, `title`, `jel_code`, `source_id`),
`FIRST_POSTED: YYYY-MM-DD`, and explicit `ATTEMPT_STATUS`. Statement-only files use
that identity header and exactly one `% BEGIN ECONOMICS STATEMENT` / `% END ECONOMICS
STATEMENT` boundary pair enclosing substantive subsections. No research status or
completion belongs in a statement. Preserve source labels and shared conventions.

The original importer is deliberately one-time; it refuses to rebuild an existing
registry. **Do not rerun it or simply append a statement.** A new Economics proposal
requires maintainer source/scope/duplicate review and registration in `problems.json`
with provenance, statement path, count, and a fresh unused initial identity slot above
all previous `initial_rank` values. Freeze the resulting JEL/initial-slot ID forever;
the slot is an identity allocation, not a current difficulty rank. Add a ranking row
and preserve existing ranks (append initially); the registry's initial slots and current
ranks must each remain contiguous. Review the complete registry/statement/ranking diff
and run `scripts/economics_catalog.py` and the validator before acceptance. No generic
Economics allocator is introduced here. A future alternative ID namespace needs a
separate schema migration. See [Economics catalogue](lists/economics/README.md) for rank
updates, imported-source history, and the original importer.

## Prospective machine-readable declarations

These comment headers support submission checks; they are **documentation-only** and
do not change site status, authorship, or proof validity. Use one single-line JSON
object per header, before the document (or at the start of an Erdős/MO fragment).
All named text fields must be nonempty; use honest “None” / “Not performed” / uncertainty
statements when applicable. Also include these facts in the readable manuscript.

A research attempt needs `SUBMISSION` plus exactly one `% ATTEMPT_STATUS: ...`:

```tex
% SUBMISSION: {"kind":"research_attempt","category":"erdos","problem_id":"5","model":{"provider":"OpenAI","version":"GPT-6","reasoning":"Astra Ultra","generated_on":"2026-10-10"},"other_models":"None","tools":"None","target":"Exact original target, including all quantifiers","scope":"Theorem proved and comparison with the original target","human_contributions":"None; submitter supplied prompts only","verification":"Model self-audit only; no independent human proof verification","reproducibility":"Prompt A then B; public artifacts or unavailable artifacts disclosed"}
% ATTEMPT_STATUS: partial
```

Use category `erdos`, `top_problems`, `mo`, or `economics`; `problem_id` is the canonical
string ID. If model version is unavailable, include a nonempty `version_uncertainty`
inside `model` explaining why. Set `reasoning` to “Not exposed” when necessary. Do not
copy the example's version or date as if it described your model. Top attempts also
copy their definition's `TOP_PROBLEM` header; Economics uses its matching header and
FIRST_POSTED above. New attempts in all categories require source attribution,
References and Completion Estimate in active LaTeX.

For `solved`, also add this single-line JSON header and readable scope declaration:

```tex
% FULL_SOLUTION_SCOPE: {"target":"Entire original statement","result":"Theorem/counterexample with locator","coverage":"Explanation covering all cases and quantifiers","dependencies":"All significant external results, or none","human_verification":"Who independently checked what, or none","unverified":"Portions not independently checked","novelty":"Search undertaken and result, or not checked"}
```

A Top/Economics statement needs this different declaration (no model required):

```tex
% SUBMISSION: {"kind":"statement_only","category":"top_problems","problem_id":"1","proposal_type":"established","source":"Primary citation and permanent URL","status_evidence":"Evidence of current status and limitations","status_checked_on":"2026-10-10","duplicate_check":"Repository/source/literature/equivalence checks and related IDs","attribution":"Original proposer and any preparation assistance"}
```

For `proposal_type: new_conjecture`, additionally supply nonempty text fields
`proposer`, `motivation`, `related_problems`, `boundary_tests`, `counterexample_search`,
`nontriviality`, and `novelty_disclosure` (including the unestablished novelty/open-status
caveat). Top definitions require ENTRY_KIND; Economics is identified by its statements
path (ENTRY_KIND statement_only may also be supplied). Do not add `ATTEMPT_STATUS`,
`FULL_SOLUTION_SCOPE`, model/research fields, or completion to statement-only files.

## Mandatory initial and final LLM prompts

Use [the four complete copy-ready prompts](docs/contribution_prompts.md): **A** before
research and **B** after a proposed result; **C** before statement preparation and
**D** before submitting a statement. Fill in actual model, tools, source, canonical ID,
and category. If a tool/source is unavailable, disclose that fact and arrange a source
check rather than pretending it was consulted. Retain prompt/audit provenance in the
submission's reproducibility notes. Self-audits improve quality but are not independent
human verification. Human-only contributions use the corresponding scope/source review
checklists without falsely claiming an LLM was used.

## Specialist research batch imports

For catalogue-style research batches, use the importer from the repository root:

```bash
python3 scripts/import_top_problem_attempts.py --model gpt_6_astra_ultra /path/to/research_batch_101_103.tex
python3 build_site.py
```

You can supply multiple batch paths in one command. Each batch must be a complete
TeX document, including `\begin{document}` and `\end{document}`. Each problem
section starts with `% problemId: N`, where `N` is its canonical UnsolvedMath
ID, and contains a `\section` with `\label{N}`. An imported section must contain nonempty `Definitions and
mathematical statement`, `Short English statement`, `Research attempt`, and
`Sources` subsections. Definition-only sections are skipped. Local source
references must resolve to the section's source list.

The importer validates every intended output before writing, checks the stable ID
against the numbered root definition, and preserves the original preamble and
entire problem section word for word. It adds a standalone document wrapper and
`% ATTEMPT_STATUS: unresolved`; importing a batch does not establish a solution.
Original batches and root definitions remain unchanged. The build expands
supported catalogue macros and source links only in browser data, retaining the
original TeX for download.

For Top Open Problems, the build also reads argument-free notation declared in
the document preamble with `\newcommand`, `\renewcommand`, `\providecommand`, or
`\DeclareMathOperator`. For example, `\newcommand{\CH}{\operatorname{CH}}` renders
as the upright operator CH. Definitions remain local to that document; nested
aliases are expanded, while verbatim/code examples are preserved. Arbitrary
TeX package code and custom commands with arguments are not interpreted by this
notation converter; use browser-supported notation for those cases.

An identical section already present is left alone, including when its document
wrapper differs. A changed section never overwrites an existing attempt: pass
`--version 2` (or another unused positive version) to create `N_v2.tex`. Conflicting
sections in the same import fail before any files are written. After building,
check both the problem statement and the model attempt on the detail page.

### OpenAI external-claim records

Use `attacks/open_problems/top_problems/openai/<id>.tex` for summaries of
claims in [openai/math](https://github.com/openai/math). Preserve the exact
`TOP_PROBLEM` identity from the numbered definition. Records carry
`FIRST_POSTED`, `ATTEMPT_STATUS`, and a strict `OPENAI_CLAIM` JSON header,
with the pinned source commit, paper-level scope, result classification,
and manuscript and formalization paths from `lists/openai_math/manifest.json`.
The build rejects inconsistent statuses, unknown paths, and invalid metadata.
Each manuscript may also supply `statement_sources`, an array of
`{"path": "preprints/<manuscript>/build/source.tex", "line": 1, "label": "Theorem 1.1"}`
objects. Use an eligible TeX file from that manuscript's build directory and
the actual source line and theorem label. These produce pinned links directly
to the mathematical statement; they cannot point to another manuscript.

Match the paper's main theorem to the complete problem statement, including
quantifiers, hypotheses, parameters, and bundled questions. Only full or stronger
matches use `ATTEMPT_STATUS: solved`; partial matches remain unresolved.
A separate reviewer must check every proposed full or stronger match without
seeing the first verdict, and the user must confirm the proposed solved labels
before importing records. Scope review does not verify the proof itself:
`independently_reviewed` remains false. Never change the catalogue source status,
existing GPT attempts, reviews, numerical IDs, or existing display positions.
The build keeps the original catalogue status in `source_status`. A full or
stronger match sets the displayed Problem Status to solved (OpenAI claim);
a partial match displays partially solved in the LLM claim and retains the
source-catalogue Problem Status. Community review is independent of these claim labels.
An existing record that covers a different mathematical target may be corrected
to `match: related`; it keeps `ATTEMPT_STATUS: unresolved` and does not change
the displayed Problem Status. New imports still exclude related-only matches.
An attributed withdrawal notice may use a new version with `match: related`,
`resolution: withdrawn`, and `ATTEMPT_STATUS: unresolved`. Retain the archived
manuscript's pinned metadata and link the current notice in its short TeX text.
Withdrawal records are displayed separately and do not count as mathematical progress.

The generator `scripts/import_openai_math.py` reads the pinned inventory and
approved adjudication plus per-ID summary sections. Validate with its dry-run
mode first. Repeating identical input is safe; changed records require
`--version N`. Its `--diff` mode compares a later source revision without
changing existing records. Keep downloaded OpenAI PDFs, TeX, Lean code, full
inventories, and adjudication reports outside this repository.

Rebuild the source inventory and candidate packets with the research tools below.
The inventory needs PyYAML and candidate retrieval needs scikit-learn; install
these optional dependencies in a separate research environment. They are not
required for the site build. The OpenAI checkout must already be at the manifest's
exact commit, and the full registry is separate from the site's smaller registry.

```sh
python3 scripts/inventory_openai_math.py \
  --repo /path/to/openai-math-checkout \
  --output /path/to/local-research \
  --manifest lists/openai_math/manifest.json
python3 scripts/match_openai_math_candidates.py \
  --local /path/to/local-research \
  --site . \
  --registry /path/to/full-unsolvedmath/problems.json
```

Adjust the external paths for your workspace. Candidate scores identify pairs
to inspect; they never authorize a solved label.

Write the claim, mathematical statement, argument outline, scope comparison,
formal-verification scope, and status caveat in original TeX. The
`mathematical_statement` section must give the manuscript's hypotheses,
quantifiers, parameter range, and conclusion, including its theorem reference;
distinguish the theorem proved for a subcase from the complete catalogue problem.
Legacy inputs without this section remain readable by the generator.
Link each paper's GitHub PDF page, direct
PDF download, README citation page, and latest version. Include pinned Lean
scope, Comparator files, and reasoning summaries where available. The no-copy
8-gram check must pass. This site does not run linked Lean code, and a scope
document must not be described as verification beyond its stated coverage.

For a genuinely new target or a distinct subcase, first compare the precise
statement with the full local UnsolvedMath registry and check its original
sources. Preserve an existing identity whenever it already describes that target.
New local identities must exceed both every existing ID and `id_registry.json`'s
watermark. `scripts/allocate_openai_problem_ids.py` makes a deterministic
allocation report from identity-reviewed proposals; `--reserve` advances the
local watermark under a lock. It does not approve claims or write pages. New
records use `LOCAL-<id>` and `published: false`, and a subcase records its parent
identities without changing the parent's scope or claim. Newly formulated local
targets use adjudication pool C and require the same independent scope review
and solved-label confirmation as existing records. Keep allocation reports and
full local registries outside the site repository.

## Lean formalizations

Submit a short `.tex` description using the same problem directory, model folder,
and filename/version convention as a normal LLM attempt above. It will appear as
an attempt on that problem's page. Keep the Lean source in an external repository;
submit only the description here, so contributors and readers do not need to
download `.lean` files into this website repository.

These descriptions follow the research declaration, References, and Completion Estimate rules below,
with a link to the complete external output instead of embedding the entire proof.
The description must also include:

- **Lean source**: A public HTTPS link to the complete Lean code, such as a GitHub
  file or repository. Prefer a link pinned to a commit, and identify the relevant
  file and theorem when linking a larger project. Include the link in the TeX
  text using `\href{https://...}{Lean source}` or `\url{https://...}`.
- **Scope**: The precise statement formalized, its relationship to the original
  problem, and what remains open. Disclose `sorry`/`admit`, additional axioms,
  assumptions, and other gaps. A partial formalization is welcome; successful
  checking alone does not establish that the original problem is solved.
- **Attribution**: The LLM model used, prompting/process, and any human
  contributions or edits. Link to the complete original generated output.
- **Reproduction**: The Lean version and Mathlib version/commit (if used), or the
  Lean Web project used to test the example. Identify other dependencies and
  report the actual checking outcome, including warnings, failures, or "not
  tested". Do not imply that repository maintainers verified the result.

**Lean code submitted or linked here is not manually reviewed for correctness or
safety. Do not run untrusted submitted Lean code locally**, including through an
editor's automatic Lean checking. The website publishes descriptions and links;
it does not run the linked Lean code.

When possible, also provide a browser-based reproduction using
[Lean Web](https://live.lean-lang.org/). For very small, self-contained examples,
use a Lean Web share link (`code` or `codez`). For larger examples, commit the
`.lean` file to the **external source repository** and link to Lean Web with
`#url=` set to its URL-encoded raw-file HTTPS URL, preferably pinned to a commit,
instead of embedding a large amount of code in a `codez` URL. An optional
`&project=` must name a project already available on that Lean Web server; it
does not load an arbitrary project from GitHub. See the
[Lean Web URL documentation](https://github.com/leanprover-community/lean4web/blob/main/doc/Usage.md).
Test the shared link in the selected project. A project with multiple files or
custom dependencies may not work as a single-file playground example; document
those requirements in the external repository. A Lean Web link is a reproduction
aid, not a correctness or safety certification.

Example description template (replace the placeholders and describe your actual
result; use the appropriate problem/model path):

```tex
\documentclass{article}
\usepackage{hyperref}
% ATTEMPT_STATUS: partial
% Add SUBMISSION JSON as described above; retain category-specific headers.
\begin{document}
\section*{Lean formalization of Erdos problem 5}
Model and process: [model/version, prompting, and human contributions].

Scope: [precise lemma or statement formalized and remaining gaps].
Lean source and original output:
\href{https://github.com/OWNER/REPO/blob/COMMIT/erdos/5/Main.lean}{Lean source}.

Reproduction: [Lean version and Mathlib commit, or Lean Web project].
Checking outcome: [actual result, warnings, or not tested].
Additional assumptions or placeholders: [list, or none].

\section{Completion Estimate}
\noindent\textbf{COMPLETION: 25\%}
[Replace 25 with your actual estimate and explain proved scope and remaining gaps.]
\section*{References}
[Original problem source and formalization dependencies.]
\section*{Final status}
PARTIAL formalization; the original problem remains UNRESOLVED.
\end{document}
```

## Pull requests and checks

Fork, create a descriptive branch, add/version files in the correct locations, and
complete the [mathematical PR template](.github/pull_request_template.md). Research PRs
state category/ID, exact models/configuration/date, status/percentage, theorem, original
scope comparison, dependencies, contributions, verification, gaps, and reproducibility.
Statement PRs give source/formulation, status evidence/search date, duplicate checks,
attribution, proposal type, identity approval, and registry/order changes.

Run from the repository root (substitute your actual base branch/reference):

```sh
python3 scripts/validate_submissions.py --base origin/main
python3 -m unittest discover -s tests
for test_file in tests/test_*.js; do node "$test_file"; done
python3 build_site.py
```

Inspect the final diff and rendered statements, references, attempts, downloads and
review links. Do not commit generated site data unless the contribution needs it.
Report exact results; a successful build is not proof checking. Review issue forms
remain available independently of mathematical submission PRs.

## Automated validation and limitations

`python3 scripts/validate_submissions.py PATH.tex ...` explicitly checks prospective
requirements. `--base REF` instead checks only added/modified submissions against
that Git commit, including working-tree changes and untracked TeX files; unchanged
historical files are skipped even if supplied explicitly. Missing/invalid base refs
fail, not silently fall back to checking every historical file. PR CI uses the PR base
SHA and full history. Push builds retain their historical build validation without
retroactive manuscript linting.

The validator checks location/filename/version, registered identity and matching
headers, declarations, exact completion heading and build-compatible percentage,
partial/unresolved versus 100%, solved scope fields, references/bibliography, Top
statement headings, Economics boundaries, registry duplicates/order/rank consistency,
and removal/rename of stable files/identities relative to the base. The three existing
identical MO CSV repetitions (339137, 377545, 185834) are grandfathered at their current
two-row counts; new duplicates and conflicting rows fail. Comments and literal
code cannot satisfy body requirements. It handles ordinary LaTeX, not arbitrary macro
execution, conditionals, included files, or TeX package code; unusual valid structures
need maintainer review rather than a fabricated success. It checks declaration
presence, not truth, authorship significance, citation accuracy, novelty, mathematical
equivalence, proof completeness, or correctness. Human mathematical judgment remains
required for those questions.

**Exceptions:** `top_problems/openai` is a scoped external-claim summary, not a new
LLM-generated proof: it keeps the strict OPENAI_CLAIM/manifest/no-copy/adjudication
workflow and build checks, rather than research percentage/model declarations.
`top_problems/Human_Contribution` is a human mathematical contribution, not an LLM
attempt: preserve its dedicated identity/entry convention and accurately disclose
human authorship, source, scope, references, and checking in the PR; prospective LLM
checks do not infer a model for it. Historical reused-writeup and statement-only
collection provenance remains readable; new statement proposals use the catalogue
routes above. Lean descriptions use the research declarations/estimate/references
but may link the full external output. Batch importers preserve TeX word for word;
prepare new batch sections with accurate scope and attribution. After importing,
add declaration headers and a standalone Completion Estimate section outside the
preserved problem section; its Sources subsection supplies references. The importer
expects one problem section and cannot itself import a second completion section.
Do not change old batches or definitions. Import success alone does not
satisfy prospective checks.

## Community Reviews

Use the repository's **Review an LLM claim** issue form. Select **Open Problems**
for a ranked record and copy its canonical UnsolvedMath ID (such as `6`) from the
detail page. Select **MO** and its numeric question ID for the MathOverflow subset,
or **Erdos** and its numeric problem number. An accepted review requires a citation
and an explanation. Review changes pass through a pull request before publication.
Use `submitted` to record a contribution awaiting independent review. Submission
records attribute `submitted_by`, rather than crediting the submitter as a reviewer.
For a contribution by its authors, retain `submission_role: authors`; the page displays
**submitted** with their GitHub handles. This does not accept the proof
or independently review another contribution on the same problem page.
Maintainers use the `ready-for-pr` label to create that pull request. Its required
`build` check must pass before merging; if GitHub displays an **Approve workflows
to run** banner, a maintainer must review and approve the workflow run first.

## Conduct and questions

Credit sources and contributions accurately, respect source licences, and describe
uncertainty plainly. For contribution questions use
[GitHub Discussions](https://github.com/mehmetmars7/Erdosproblems-llm-hunter/discussions).
The review issue form is reserved for reviews of specific attempts; Economics reviews
currently need a manual maintainer workflow because that form has no Economics option.
