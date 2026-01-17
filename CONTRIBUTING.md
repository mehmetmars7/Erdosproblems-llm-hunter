# Contributing to Problem Hunting with LLMs

Thank you for your interest in contributing to this project. This document outlines the guidelines for submitting new LLM attempts or improvements.

## Accepted LLM Models

Only contributions featuring attempts from the most advanced frontier LLMs are accepted:

- **GPT Pro** 
- **GPT** 
- **GPT Codex**
- **Gemini Deep Think** 
- **Opus**
- Other comparable frontier models with demonstrated mathematical reasoning capabilities

We focus on frontier models because they have shown the most promise in making meaningful progress on open mathematical problems.
Most current attempts are by GPT Pro 5.2.

## Submission Guidelines

### For Erdos Problem Attempts

1. **File Location**: Place your TeX file in `Attacks/Erdos_problems/<MODEL_NAME>/`
2. **File Naming**: Use the problem number as the filename (e.g., `352.tex`)
3. **Content Format**: Follow the structure used in existing attempts:
   - Problem statement (verbatim from erdosproblems.com)
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
