# Contributing to Problem Hunting with LLMs

Thank you for your interest in contributing to this project. This document outlines the guidelines for submitting new LLM attempts or improvements.

## Accepted LLM Models

Only contributions featuring attempts from the most advanced frontier LLMs are accepted:

- **GPT Pro** 
- **GPT** 
- **GPT Codex**
- **Gemini Deep Think** 
- **Opus**
- Other comparable frontier models with demonstrated mathematical reasoning capabilities such as Aristotle from Harmonic.

We focus on frontier models because they have shown the most promise in making meaningful progress on open mathematical problems.

## Submission Guidelines

### For Erdos Problem Attempts

1. **File Location**: Place your TeX file in `attacks/open_problems/erdos/<MODEL_NAME>/`.
2. **File Naming**: Use the problem number as the filename (e.g., `x.tex`). If it already exists, use `x_v2.tex`.
3. **Recommended Content Format**: If possible, follow the structure used in existing attempts:
   - Formal statement
   - Literature/context check
   - Attack plan
   - Work (the actual attempt)
   - Verification
   - Final status (SOLVED, UNRESOLVED, or PARTIAL)

### For Top Open Problems Attempts

1. **Choose the Target**: Use the numbered definition in `attacks/open_problems/top_problems/definitions/<unsolvedmath_id>.tex`, preserving its mathematical scope and cited sources. The `TOP_PROBLEM` comment provides the numerical `id` used by URLs and reviews. Display rank is independent of this ID.
2. **File Location**: Place your TeX file in `attacks/open_problems/top_problems/<MODEL_NAME>/`.
3. **File Naming**: Use `<unsolvedmath_id>.tex`, for example `1.tex` for P versus NP. Further versions use `1_v2.tex`, `1_v3.tex`, and so on. Keep the root definition file separate from model attempts.
4. **Mathematical Content**: Include a precise statement, definitions and conventions, a literature check, the actual mathematical attempt, verification, and a final status. Cite relevant sources for the definition and concepts as well as theorems, reductions, or prior work used during the attempt. Use identifiable bibliographic references and source URLs; do not invent citations.
5. **Honest Scope**: Identify what is proved, what is known, and the first remaining gap. An unresolved attempt is welcome. Do not present a statement, generic plan, untested idea, or restatement of known results as a new solution.

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
a partial match is partially solved (OpenAI claim), unless the source catalogue
already records a solution. Community review is independent of these claim labels.
An existing record that covers a different mathematical target may be corrected
to `match: related`; it keeps `ATTEMPT_STATUS: unresolved` and does not change
the displayed Problem Status. New imports still exclude related-only matches.

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

### For the MathOverflow Subset

1. **File Location**: Place your TeX file in `attacks/open_problems/mo/<MODEL_NAME>/`.
2. **File Naming**: Preserve the existing convention `<question_id>-<title-slug>.tex` (and version suffixes where used).
3. **Add to List**: If it is a new problem, add an entry to `lists/mo_problems.csv`.
4. **Content**: Follow the same statement, definition, citation, mathematical work, and verification requirements as ranked open-problem attempts.

The website groups ranked problems and MathOverflow records under **Top Open Problems**.
The numbered definitions contain stable IDs for existing problem links and reviews. Keep the number-to-ID mapping consistent with any numbered model attempts.
MathOverflow entries retain their numeric source IDs and existing links.

### Lean Code Contributions

Submit a short `.tex` description using the same problem directory, model folder,
and filename/version convention as a normal LLM attempt above. It will appear as
an attempt on that problem's page. Keep the Lean source in an external repository;
submit only the description here, so contributors and readers do not need to
download `.lean` files into this website repository.

The description must include:

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
% ATTEMPT_STATUS: unresolved
\begin{document}
\section*{Lean formalization of Erdos problem 5}
Model and process: [model/version, prompting, and human contributions].

Scope: [precise lemma or statement formalized and remaining gaps].
Lean source and original output:
\href{https://github.com/OWNER/REPO/blob/COMMIT/erdos/5/Main.lean}{Lean source}.

Reproduction: [Lean version and Mathlib commit, or Lean Web project].
Checking outcome: [actual result, warnings, or not tested].
Additional assumptions or placeholders: [list, or none].

\section*{Final status}
PARTIAL formalization; the original problem remains UNRESOLVED.
\end{document}
```

## Pull Request Process

1. **Fork the Repository**: Create your own fork of the project
2. **Create a Branch**: Use a descriptive branch name (e.g., `add-opus45-erdos-352`)
3. **Add Your Files**: Place the attempt files in the correct directories
4. **Check the Build**: Run `python3 build_site.py`, `python3 -m unittest discover -s tests`, and `for test_file in tests/test_*.js; do node "$test_file"; done`. Confirm the problem statement, references, and actual attempt render on the detail page.
5. **Submit PR**: Create a pull request with a clear description

### PR Description Template

```markdown
## Summary
- Problem Type: [Erdos/Top Open Problems/MathOverflow subset]
- Problem Number/ID:
- LLM Model Used:
- Claimed Status: [Solved/Partial/Unresolved]

## Notes
[Any additional context about the attempt]
```

## Quality Standards

- **Reproducibility**: Include information about the prompt strategy used and if possible a public link
- **Completeness**: Include the full LLM output, not just excerpts. For Lean contributions, the short TeX description may link to the complete original output and Lean source hosted externally.
- **Formatting**: Use proper LaTeX formatting for mathematical content
- **Sources**: Cite primary sources for the target and definitions, and cite the results used in the mathematical argument. Check cited statements and explain how their hypotheses apply.
- **Substance**: Include actual mathematical reasoning or a checked construction. Keep catalogs and statement-only records separate from attempts.
- **Status**: State unresolved gaps plainly. Completion estimates are the author's estimates, not external verification.

## Community Reviews

Use the repository's **Review an LLM claim** issue form. Select **Open Problems**
for a ranked record and copy its canonical UnsolvedMath ID (such as `6`) from the
detail page. Select **MO** and its numeric question ID for the MathOverflow subset,
or **Erdos** and its numeric problem number. An accepted review requires a citation
and an explanation. Review changes pass through a pull request before publication.
Use `submitted` to record a contribution awaiting independent review. Submission
records attribute `submitted_by`, rather than crediting the submitter as a reviewer.
For a contribution by its authors, `submission_role: authors` displays
**submitted by authors** with their GitHub handles. This does not accept the proof
or independently review another contribution on the same problem page.
Maintainers use the `ready-for-pr` label to create that pull request. Its required
`build` check must pass before merging; if GitHub displays an **Approve workflows
to run** banner, a maintainer must review and approve the workflow run first.

## Important Reminders

1. **No Verification Claims**: Do not claim a problem is definitively solved. All claims are subject to expert review.
2. **Original Output**: Submit the actual LLM output, not human-edited versions. For Lean contributions, the short TeX summary may be written by the contributor; preserve the original generated output at the external source link and disclose any subsequent human edits separately.
3. **Disclosure**: If you used any special prompting techniques, document them.

## Code of Conduct

- Acknowledge that LLM outputs require verification
- Credit original problem sources appropriately

## Questions?

For questions about contributing, use [GitHub Discussions](https://github.com/mehmetmars7/Erdosproblems-llm-hunter/discussions). The issue form is reserved for reviews of specific attempts.

## Recommended prompt:
ROLE
You are in “research mathematician + adversarial proof checker mode.

MISSION
Given the open problem below, work toward one of the following:
(A) produce a COMPLETE, gap-free PROOF of the statement as written, or
(B) produce an EXPLICIT COUNTEREXAMPLE and a rigorous DISPROOF.
If neither is achieved, report UNRESOLVED with checked partial results and exact remaining gaps. No handwaving. No unstated assumptions. No “it is clear”. Every nontrivial step must be justified.

If the statement is ambiguous/misstated, do not ask me questions: instead
1) identify the ambiguity/misstatement precisely,
2) give the *minimal* corrected statement consistent with standard conventions,
3) then either prove the corrected statement or give a counterexample to the literal statement (or both),
clearly separating “literal statement” vs “corrected statement”.

TOOLS / CONSTRAINTS (fill these in)
- Web browsing available? [YES]
- Computation available (Python/Sage/Mathematica)? [YES]

PROBLEM

OUTPUT FORMAT (you must follow)
1) “FORMAL RESTATEMENT” (quantifiers explicit; all terms defined; edge cases stated)
2) “QUICK LITERATURE/CONTEXT CHECK” (only if browsing is available; otherwise: what you recall + uncertainty)
3) “ATTACK PLAN” (1–3 proof strategies + 1–3 disproof/construction strategies; pick the best path)
4) “WORK” (lemmas + proofs or explicit counterexample + verification)
5) “VERIFICATION” (attempt to break your own proof/counterexample; boundary cases; quantifier checks)
6) FINAL (select the label supported by the work):
  LABEL: **FULL SOLUTION**
   SUBLABEL:
   - **FULL PROOF** (clean theorem statement + complete proof)
   - **COUNTEREXAMPLE/DISPROOF** (explicit object(s) + step-by-step verification + conclusion)
  Or LABEL: **UNRESOLVED**, followed by the strongest checked partial result and exact remaining gap.

WORKFLOW (do this, tightly and efficiently)
PHASE 0 — HYGIENE (must do)
- Rewrite the statement with explicit quantifiers (∀, ∃, “for infinitely many”, etc.).
- List definitions and conventions (e.g., ℕ starts at 0 or 1; graphs simple?; logs base e?).
- Identify the “stress points”: extreme parameters, degenerate cases, hidden dependencies.

PHASE 1 — FAST REALITY CHECK (must do)
- Test tiny cases by hand (n=1,2,3; smallest nontrivial instances).
- Actively try to falsify the claim with small constructions.
- If computation is available, write minimal pseudocode to search small cases and report what it finds.

PHASE 2 — LANDSCAPE (must do)
- Classify the problem type: extremal / probabilistic / additive number theory / analytic / Ramsey / etc.
- List 5–10 likely tools, each with a one-line “why relevant” (e.g., pigeonhole, double counting,
  energy/Cauchy–Schwarz, container method, dependent random choice, Fourier, sieve, PNT, etc.).
- Look for equivalent formulations, monotonicity, reduction to “minimal counterexample”, or scaling.

PHASE 3 — DUAL-TRACK SOLVE (must do)
Run both tracks in parallel; stop as soon as one succeeds.

(A) PROOF TRACK
- Propose a concrete proof outline with named lemmas in dependency order.
- Prove each lemma fully; after each lemma, state exactly what it gives and how it will be used.
- Avoid “standard” leaps: if using a known theorem, state it precisely and verify hypotheses.

(B) DISPROOF TRACK
- Try to build a counterexample systematically:
  • extremal constructions (balanced/unbalanced, structured/random),
  • known families (AP-free sets, Sidon sets, Behrend-type, projective planes, etc.),
  • parameter pushing (largest/smallest density, tightness cases),
  • “cheap” technicality checks (misstated quantifiers, missing constraints).
- Keep the smallest/cleanest candidate counterexample.
- If you find one, verify every condition line-by-line and conclude disproof.

PHASE 4 — ADVERSARIAL VERIFICATION (must do)
Before finalizing, attempt to refute your own solution:
- Check boundary cases and quantifiers again.
- Check any hidden use of choice/compactness/limit arguments.
- Try to find a counterexample to each lemma.
- Ensure constants/ranges are correct and not circular.
If anything breaks: fix and re-run verification.

RULES (non-negotiable)
- Do NOT fabricate references, prior results, or “known facts”. If unsure, say so.
- Do NOT present an argument with gaps as a full solution.
- If the literal statement is false, prefer an explicit counterexample over “it seems false”.

FAIL-SAFE (only if genuinely unavoidable)
If you cannot reach FULL PROOF or COUNTEREXAMPLE after exhausting the workflow, output:
**UNRESOLVED**
and include:
(i) the strongest fully proved partial result you *did* obtain,
(ii) the exact first gap (a single crisp statement you could not prove),
(iii) the top 3 next moves (specific lemmas to target or constructions to test),
(iv) what a minimal counterexample would likely look like (structure/parameters).

BEGIN NOW.
