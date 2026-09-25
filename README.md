# Problem Hunting with LLMs

A collection of attempts by advanced Large Language Models (LLMs) to solve [Erdos Problems](https://www.erdosproblems.com/) and **Top Open Problems** across mathematics and theoretical computer science. MathOverflow is retained as a subset of the open-problems collection.


**Live Site:** [mehmetmars7.github.io/Erdosproblems-llm-hunter](https://mehmetmars7.github.io/Erdosproblems-llm-hunter)

## Overview

This project documents and tracks LLM attempts to solve challenging open mathematical problems. The website automatically updates when new TeX files are added to the repository.

The Erdos index and the [GPT_6_Astra_Ultra collection](attacks/open_problems/erdos/GPT_6_Astra_Ultra/) cover all **1,221 problem numbers** in the saved collaborative database, including resolved problems. New and revised writeups state their proved results, remaining gaps, external theorem dependencies, and numerical completion estimates. The collection still includes attributed imports awaiting individual review; complete file coverage does not imply that every proof claim has been verified. Reused work retains its original model attribution, and reviewed replacements preserve that provenance. Only `.tex` writeups are published from this collection; working notes, manifests, source snapshots, and verification reports are kept outside the repository.

### Problem Sources

- **Erdos Problems**: Open problems posed by Paul Erdos, one of the most prolific mathematicians in history
  - Problem statements: [erdosproblems.com](https://www.erdosproblems.com/)
  - Latest status and formalization links: [Terry Tao's Erdos Problems Database](https://teorth.github.io/erdosproblems/)

- **Top Open Problems**: [500 numbered TeX definitions](attacks/open_problems/top_problems/), each with mathematical definitions, an English summary, and cited sources.
  - The build reads these TeX files and the website displays their mathematical definitions, summaries, and sources, with a link to each original `.tex` file. Research-attempt subsections appear as separate research notebooks. LLM-judged ranking numbers are by [ProofAtlas](https://www.proofatlas.ai/). Stable IDs preserve problem links and reviews; catalog quotations are excluded from the page display.
  - The existing 100 [MathOverflow](https://mathoverflow.net/) problems remain available as a separate source subset within this collection, preserving their attempts and links. The combined listing therefore contains 600 catalog entries; entries from different sources may refer to related mathematical questions.
  - Catalog inclusion does not count as an LLM attempt. A ranked problem with no submitted mathematical writeup is shown without an attempt.

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
├── attacks/
│   └── open_problems/
│       ├── erdos/<model>/  # Numbered Erdos TeX attempts
│       ├── top_problems/   # 1.tex through 500.tex: definitions and sources
│       │   └── <model>/   # Numbered ranked attempts, e.g. 15.tex or 15_v2.tex
│       └── mo/<model>/    # Existing MathOverflow TeX attempts
├── lists/
│   ├── erdos_problems.csv
│   ├── erdos_status.json  # Saved collaborative database status
│   └── mo_problems.csv
├── reviews/               # Community reviews by collection and stable ID
├── docs/                  # Published GitHub Pages site
│   ├── data/              # Generated JSON and JavaScript data
│   ├── index.html
│   ├── erdos.html
│   ├── open_problems.html # Ranked problems and MathOverflow subset
│   ├── mo.html            # Compatible MathOverflow listing
│   ├── problem.html
│   ├── about.html
│   ├── styles.css
│   └── app.js
├── scripts/               # Status synchronization and review processing
├── tests/                 # Python data checks and JavaScript frontend checks
├── .github/workflows/      # GitHub Actions for auto-deployment
├── build_site.py           # Build script
├── CONTRIBUTING.md         # Contribution guidelines
└── LICENSE                 # Apache 2.0 License
```

## How It Works

1. **Problem Statements**: Every new writeup includes the mathematical statement, definitions, and relevant source citations:
   - Erdos problems: [erdosproblems.com/X](https://www.erdosproblems.com/) for problem X
   - Ranked open problems: Definitions and references from `attacks/open_problems/top_problems/<number>.tex`, with primary sources checked when preparing an attempt
   - MathOverflow subset: Original MathOverflow question links
2. **LLM Attempts**: Stored as TeX files in `attacks/`. Ranked writeups use `attacks/open_problems/top_problems/<model>/<number>.tex` (or `<number>_v2.tex`); the imported research batches are in `GPT_6_Astra_Ultra/`. Root numbered files provide definitions and sources separately and do not count as attempts. Legacy stable-ID filenames remain supported. Each attempt contains actual mathematical work, references for definitions and concepts, citations for results used, and an honest account of remaining gaps. A statement or research plan alone is not an attempt.
3. **Build Process**: `build_site.py` processes the catalogs, attempts, and reviews into JSON and JavaScript data in `docs/data/`
4. **Auto-Update**: GitHub Actions automatically rebuilds the site when:
   - Files in `attacks/`, `lists/`, or `reviews/` are modified
   - Site pages, build scripts, or tests are modified
5. **Rendering**: The detail page renders the TeX definition and model attempts in the browser, with MathJax for mathematics. The build normalizes the catalogue's supported macros and source links for display while leaving the downloadable TeX unchanged. TeX document layout and preambles are omitted from the browser view.

## Importing Research Batches

Use the batch importer to copy each complete problem section containing a
`Research attempt` subsection into its model folder:

```bash
python3 scripts/import_top_problem_attempts.py --model GPT_6_Astra_Ultra /path/to/research_batch_101_103.tex
python3 build_site.py
```

The importer checks each section's `problemId` and `releaseRank` against its root
definition. It preserves the original preamble and full section word for word,
adds an explicit unresolved status, and leaves the source batch untouched.
Definition-only sections are skipped. Repeating an import of the same section
does nothing; changed work requires a new version, such as `--version 2`.
See [the contribution guide](CONTRIBUTING.md#for-top-open-problems-attempts)
for the required batch structure and checks.

## Local Development

```bash
# Refresh the status snapshot from Tao's GitHub repository (requires network)
python3 -m pip install -r requirements.txt
python3 scripts/sync_erdos_status.py

# Run the build script (uses the saved snapshot; works offline)
python3 build_site.py

# Serve locally (Python)
python3 -m http.server 8000 --directory docs
```

Then open `http://localhost:8000` in your browser.

Problem statuses are saved in `lists/erdos_status.json`, with the upstream commit
and the time they were checked. Every problem listed in this repository must have
a matching status; the build fails if any are missing. GitHub Actions refreshes
this snapshot before building the published site, using the upstream GitHub data
without scraping individual pages on erdosproblems.com.

The Erdos **LLM Claim** column follows an automatic database rule: `open`,
`falsifiable`, and `decidable` map to `unresolved`; every other informal status
maps to `solved`, including rows without attempts. Individual attempt claims are
unchanged, and their original aggregate is stored in `attempt_status`.
The generated `llm_status_source` field identifies the rule as `database_rule`.
The original database status remains visible on problem detail pages.
Problems marked
proved, disproved, solved, or independent receive **100% Completion**, following
the database's definition of resolved problems. For other problems, completion
remains the existing LLM estimate. Statement formalization and solution formalization
are reported separately; an `open (Lean)` problem remains open. Attempt contents
and community reviews retain their separate meanings. Top Open Problems claim
labels, including its MathOverflow subset, reflect the hosted attempts; catalog
status and its qualifications are shown separately.

Run the checks before publishing:

```bash
python3 -m unittest discover -s tests
for test_file in tests/test_*.js; do node "$test_file"; done
python3 build_site.py
```

Ranked detail links use `problem.html?type=open_problems&id=problem.p-versus-np`.
Existing `problem.html?type=mo&id=<question_id>` links remain supported. Reviews
for ranked problems are stored in `reviews/open_problems/<problemId>.json`;
existing MathOverflow reviews retain their `reviews/mo/<question_id>.json` paths.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting new LLM attempts.

## Acknowledgments

- **Paata Ivanisvili** - For the idea and name "Problem Hunting with LLMs"
- **Terry Tao** - For the Erdos Problems database
- **Thomas Bloom** - For the erdosproblems.com website

## Disclaimer

**Important:** LLM output is not fully reliable. The attempts documented on this website represent exploratory work by frontier AI models and should not be considered verified mathematical proofs.

The Erdos **LLM Claim** label is assigned by the database rule above and does not
mean that an LLM has supplied a verified solution. The original **Problem Status**
comes from [Tao's collaborative database](https://teorth.github.io/erdosproblems/)
and does not validate the LLM attempts hosted here. Claims within individual
attempts still require mathematical verification.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
