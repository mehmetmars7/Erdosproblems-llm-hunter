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

1. **Choose the Target**: Use the numbered definition in `attacks/open_problems/top_problems/<number>.tex`, preserving its mathematical scope and cited sources. The `TOP_PROBLEM` comment provides the stable ID used by URLs and reviews.
2. **File Location**: Place your TeX file in `attacks/open_problems/top_problems/<MODEL_NAME>/`.
3. **File Naming**: Use `<number>.tex`, for example `1.tex` for P versus NP. Further versions use `1_v2.tex`, `1_v3.tex`, and so on. Keep the root definition file separate from model attempts. Existing stable-ID filenames in `attacks/open_problems/<MODEL_NAME>/` remain supported.
4. **Mathematical Content**: Include a precise statement, definitions and conventions, a literature check, the actual mathematical attempt, verification, and a final status. Cite relevant sources for the definition and concepts as well as theorems, reductions, or prior work used during the attempt. Use identifiable bibliographic references and source URLs; do not invent citations.
5. **Honest Scope**: Identify what is proved, what is known, and the first remaining gap. An unresolved attempt is welcome. Do not present a statement, generic plan, untested idea, or restatement of known results as a new solution.

For catalogue-style research batches, use the importer from the repository root:

```bash
python3 scripts/import_top_problem_attempts.py --model gpt_6_astra_ultra /path/to/research_batch_101_103.tex
python3 build_site.py
```

You can supply multiple batch paths in one command. Each batch must be a complete
TeX document, including `\begin{document}` and `\end{document}`. Each problem
section starts with the catalogue's `% problemId: ...` and
`% source releaseRank: N; ...` comments and contains a `\section` with
`\label{N}`. An imported section must contain nonempty `Definitions and
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

An identical section already present is left alone, including when its document
wrapper differs. A changed section never overwrites an existing attempt: pass
`--version 2` (or another unused positive version) to create `N_v2.tex`. Conflicting
sections in the same import fail before any files are written. After building,
check both the problem statement and the model attempt on the detail page.

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
for a ranked record and copy its stable ID (such as `problem.p-versus-np`) from the
detail page. Select **MO** and its numeric question ID for the MathOverflow subset,
or **Erdos** and its numeric problem number. An accepted review requires a citation
and an explanation. Review changes pass through a pull request before publication.
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
