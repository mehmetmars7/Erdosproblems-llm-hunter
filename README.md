# Problem Hunting with LLMs

A collection of attempts by advanced Large Language Models (LLMs), mostly by GPT Pro 5.2, to solve open mathematical problems from the [Erdos Problems](https://www.erdosproblems.com/) collection and [MathOverflow](https://mathoverflow.net/).


**Live Site:** [mehmetmars7.github.io/Erdosproblems-llm-hunter](https://mehmetmars7.github.io/Erdosproblems-llm-hunter)

## Overview

This project documents and tracks LLM attempts to solve challenging open mathematical problems. The website automatically updates when new TeX files are added to the repository.

### Problem Sources

- **Erdos Problems**: Open problems posed by Paul Erdos, one of the most prolific mathematicians in history
  - Problem statements: [erdosproblems.com](https://www.erdosproblems.com/)
  - Database: [Terry Tao's Erdos Problems Database](https://teorth.github.io/erdosproblems/)

- **MathOverflow**: Open problems from the professional mathematics Q&A site
  - Source: [mathoverflow.net](https://mathoverflow.net/)

### Featured LLM Models

Only the most advanced frontier LLMs with demonstrated mathematical reasoning capabilities are featured:

- GPT Pro (OpenAI)
- GPT 5.2 (OpenAI)
- GPT Codex 5.2 (OpenAI)
- Gemini Deep Think (Google)
- Opus 4.5 (Anthropic)

## Repository Structure

```
Erdosproblems-llm-hunter/
├── Problems/               # Local reference only (not published)
│   ├── Erdos_Problems/     # Problem statements link to erdosproblems.com
│   └── MO_problems/        # Problem statements link to MathOverflow
├── Attacks/
│   ├── Erdos_problems/     # LLM attempts organized by model
│   └── MO_problems/        # LLM attempts for MO problems
├── Lists/
│   ├── Erdos_Problems.csv  # Erdos problem metadata with URLs
│   └── MO_problems.csv     # MO problem metadata with URLs
├── data/                   # Generated JSON data (auto-generated)
├── .github/workflows/      # GitHub Actions for auto-deployment
├── index.html              # Main page
├── erdos.html              # Erdos problems listing
├── mo.html                 # MathOverflow problems listing
├── problem.html            # Individual problem view
├── about.html              # About page
├── build_site.py           # Build script
├── styles.css              # Styling
├── app.js                  # Frontend JavaScript
├── CONTRIBUTING.md         # Contribution guidelines
└── LICENSE                 # Apache 2.0 License
```

## How It Works

1. **Problem Statements**: Not hosted locally - users are directed to external sources:
   - Erdos problems: [erdosproblems.com/X](https://www.erdosproblems.com/) for problem X
   - MO problems: Original MathOverflow question links
2. **LLM Attempts**: Stored as TeX files in `Attacks/` directory
3. **Build Process**: `build_site.py` processes attacks and generates JSON data
4. **Auto-Update**: GitHub Actions automatically rebuilds the site when:
   - Files in `Attacks/` are modified
   - Files in `Lists/` are modified
5. **Rendering**: MathJax renders LaTeX mathematics in the browser

## Local Development

```bash
# Run the build script
python3 build_site.py

# Serve locally (Python)
python3 -m http.server 8000
```

Then open `http://localhost:8000` in your browser.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting new LLM attempts.

## Acknowledgments

- **Paata Ivanisvili** - For the idea and name "Problem Hunting with LLMs"
- **Terry Tao** - For the Erdos Problems database
- **Thomas Bloom** - For the erdosproblems.com website

## Disclaimer

**Important:** LLM output is not fully reliable. The attempts documented on this website represent exploratory work by frontier AI models and should not be considered verified mathematical proofs.

Any "solved" status indicates only that the LLM claimed to solve the problem - it does not mean the solution has been verified or accepted by the mathematical community.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
