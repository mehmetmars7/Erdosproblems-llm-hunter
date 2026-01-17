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
Most current attempts are by GPT Pro 5.2.

## Submission Guidelines

### For Erdos Problem Attempts

1. **File Location**: Place your TeX file in `Attacks/Erdos_problems/<MODEL_NAME>/`
2. **File Naming**: Use the problem number as the filename (e.g., `352.tex`)
3. **Content Format**: Follow the structure used in existing attempts:
   - Problem statement (link to erdosproblems.com)
   - Formal restatement
   - Literature/context check
   - Attack plan
   - Work (the actual attempt)
   - Verification
   - Final status (SOLVED, UNRESOLVED, or PARTIAL)

### For MathOverflow Problem Attempts

1. **File Location**: Place your TeX file in `Attacks/MO_problems/<MODEL_NAME>/`
2. **File Naming**: Use the format `<question_id>-<title-slug>.tex`
3. **Add to List**: If it's a new problem, add an entry to `Lists/MO_problems.csv`

## Pull Request Process

1. **Fork the Repository**: Create your own fork of the project
2. **Create a Branch**: Use a descriptive branch name (e.g., `add-opus45-erdos-352`)
3. **Add Your Files**: Place the attempt files in the correct directories
4. **Update CSV Lists**: If adding new problems, update the relevant CSV file
5. **Submit PR**: Create a pull request with a clear description

### PR Description Template

```markdown
## Summary
- Problem Type: [Erdos/MathOverflow]
- Problem Number/ID:
- LLM Model Used:
- Claimed Status: [Solved/Partial/Unresolved]

## Notes
[Any additional context about the attempt]
```

## Quality Standards

- **Reproducibility**: Include information about the prompt strategy used
- **Completeness**: Include the full LLM output, not just excerpts
- **Honesty**: Accurately report the claimed status from the LLM output
- **Formatting**: Use proper LaTeX formatting for mathematical content

## Important Reminders

1. **No Verification Claims**: Do not claim a problem is definitively solved. All claims are subject to expert review.
2. **Original Output**: Submit the actual LLM output, not human-edited versions.
3. **Disclosure**: If you used any special prompting techniques, document them.

## Code of Conduct

- Be respectful in all interactions
- Focus on the mathematics, not personal opinions
- Acknowledge that LLM outputs require verification
- Credit original problem sources appropriately

## Questions?

If you have questions about contributing, please open an issue on the GitHub repository.

## Feel free to use this prompt
ROLE
You are in “research mathematician + adversarial proof checker mode.

MISSION
Given the open problem below, you must do ONE of the following:
(A) produce a COMPLETE, gap-free PROOF of the statement as written, or
(B) produce an EXPLICIT COUNTEREXAMPLE and a rigorous DISPROOF.
No handwaving. No unstated assumptions. No “it is clear”. Every nontrivial step must be justified.

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
6) FINAL (exactly ONE label and ONE sub-label):
  LABEL: **FULL SOLUTION**
   SUBLABEL:
   - **FULL PROOF** (clean theorem statement + complete proof)
   - **COUNTEREXAMPLE/DISPROOF** (explicit object(s) + step-by-step verification + conclusion)

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

