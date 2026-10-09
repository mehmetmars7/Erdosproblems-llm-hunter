# Problem Hunting with LLMs

A collection of attempts by advanced Large Language Models (LLMs) to solve [Erdos Problems](https://www.erdosproblems.com/) and **Top Open Problems** across mathematics and theoretical computer science, alongside an **Economics** catalogue of open problem statements. MathOverflow is retained as a subset of the open-problems collection.


**Live Site:** [mehmetmars7.github.io/Erdosproblems-llm-hunter](https://mehmetmars7.github.io/Erdosproblems-llm-hunter)

## Overview

This project documents and tracks LLM attempts to solve challenging open mathematical problems. The website automatically updates when new TeX files are added to the repository.

The Erdos index and the [GPT_6_Astra_Ultra collection](attacks/open_problems/erdos/GPT_6_Astra_Ultra/) cover all **1,221 problem numbers** in the saved collaborative database, including resolved problems. New and revised writeups state their proved results, remaining gaps, external theorem dependencies, and numerical completion estimates. The collection still includes attributed imports awaiting individual review; complete file coverage does not imply that every proof claim has been verified. Reused work retains its original model attribution, and reviewed replacements preserve that provenance. Only `.tex` writeups are published from this collection; working notes, manifests, source snapshots, and verification reports are kept outside the repository.

### Problem Sources

- **Erdos Problems**: Open problems posed by Paul Erdos, one of the most prolific mathematicians in history
  - Problem statements: [erdosproblems.com](https://www.erdosproblems.com/)
  - Latest status and formalization links: [Terry Tao's Erdos Problems Database](https://teorth.github.io/erdosproblems/)

- **Top Open Problems**: The database comes mainly from [UnsolvedMath](https://www.unsolvedmath.com/) by [Ulam AI](https://www.ulam.ai/), available on [Hugging Face](https://huggingface.co/datasets/ulamai/UnsolvedMath). We retain imported problem IDs and categories and add [extended TeX statements](attacks/open_problems/top_problems/definitions/) and LLM attempts, with mathematical definitions, English summaries, and cited sources.
  - The build reads these TeX files and the website displays their mathematical definitions, summaries, and sources, with a link to each original `.tex` file. Research-attempt subsections appear as separate research notebooks. Permanent numerical UnsolvedMath IDs identify statements, attempts, links and reviews. Display positions come only from `lists/unsolvedmath/display_order.json`; catalog quotations are excluded from the page display.
  - The existing 100 [MathOverflow](https://mathoverflow.net/) problems remain available as a separate source subset within this collection, preserving their attempts and links. Entries from different sources may refer to related mathematical questions.
  - Catalog inclusion does not count as an LLM attempt. A ranked problem with no submitted mathematical writeup is shown without an attempt.

- **Economics**: Problem statements from the supplied merged TeX catalogue, organized by JEL code and difficulty rank. Each statement has its own detail page. These entries contain statements only and do not count as LLM attempts.
  - Permanent problem IDs use the primary JEL code and the initial revised rank, such as `C73-1`. Subsequent ranking changes preserve IDs, filenames and links.
  - See [Economics catalogue maintenance](lists/economics/README.md) for the source files and validation rules.

### Accepted LLM Models

Only the most advanced frontier LLMs with demonstrated mathematical reasoning capabilities are featured:

- GPT Pro (OpenAI)
- GPT (OpenAI)
- GPT Codex (OpenAI)
- Gemini Deep Think (Google)
- Opus (Anthropic)
- Comparable frontier models with demonstrated mathematical reasoning capabilities, such as Aristotle (Harmonic)

Record the exact model and version used with each submission.

## Repository Structure

```
Erdosproblems-llm-hunter/
├── .github/
│   ├── ISSUE_TEMPLATE/             # Community review forms
│   └── workflows/
│       ├── build.yml               # Test, build, and deploy GitHub Pages
│       └── review-issue-to-pr.yml  # Turn labeled review issues into PRs
├── attacks/
│   └── open_problems/
│       ├── erdos/
│       │   └── <model>/            # Erdos attempts: <number>.tex or <number>_v2.tex
│       ├── mo/
│       │   └── <model>/            # MathOverflow attempts: <question_id>-<slug>.tex
│       └── top_problems/
│           ├── definitions/        # Canonical definitions and sources: <id>.tex
│           └── <model>/            # Ranked attempts: <unsolvedmath_id>.tex or <unsolvedmath_id>_v2.tex
├── docs/                          # Published GitHub Pages site
│   ├── data/                      # Generated site data
│   │   ├── erdos_data.js
│   │   ├── mo_data.js
│   │   ├── open_problems_data.js
│   │   ├── economics_data.js        # Generated statement-only Economics catalogue
│   │   ├── stats.js
│   │   └── top_problems/           # Per-problem JSON detail records
│   ├── index.html
│   ├── erdos.html
│   ├── open_problems.html          # Ranked problems and MathOverflow subset
│   ├── economics.html              # Economics statements with JEL and difficulty filters
│   ├── mo.html                     # Compatible MathOverflow listing
│   ├── problem.html               # Shared problem and attempt detail page
│   ├── about.html
│   ├── styles.css
│   ├── app.js                      # Shared frontend behavior
│   ├── attempt-previews.js
│   ├── catalog-math.js
│   ├── tex-bare-math.js
│   └── tex-references.js
├── lists/
│   ├── erdos_problems.csv
│   ├── erdos_status.json           # Saved collaborative database status
│   ├── mo_problems.csv
│   ├── economics/
│   │   ├── problems.json           # Permanent IDs and statement metadata
│   │   ├── rankings.csv            # Mutable difficulty ranks keyed by permanent ID
│   │   └── README.md               # Economics catalogue maintenance
│   └── unsolvedmath/
│       ├── problems.json           # Portable canonical catalogue subset
│       └── display_order.json      # Ordered canonical IDs, independent of identity
├── reviews/
│   ├── erdos/                      # Community reviews: <number>.json
│   ├── mo/                         # Community reviews: <question_id>.json
│   └── open_problems/              # Community reviews: <unsolvedmath_id>.json
├── scripts/
│   ├── audit_tex_rendering.mjs
│   ├── import_top_problem_attempts.py
│   ├── migrate_unsolvedmath.py      # One-time audited local migration
│   ├── sync_erdos_status.py
│   └── update_review_from_issue.py
├── tests/                         # Python, JavaScript, and browser checks
├── build_site.py                  # Generate site data from TeX, lists, and reviews
├── requirements.txt               # Optional status-sync dependency
├── CONTRIBUTING.md                # Contribution guidelines
├── README.md
├── THIRD_PARTY_NOTICES.md          # Dataset attribution, licences, and changes
└── LICENSE                        # Apache-2.0 for the software
```

## How It Works

1. **Problem Statements**: Every new writeup includes the mathematical statement, definitions, and relevant source citations:
   - Erdos problems: [erdosproblems.com/X](https://www.erdosproblems.com/) for problem X
   - Ranked open problems: Definitions and references from `attacks/open_problems/top_problems/definitions/<unsolvedmath_id>.tex`, with primary sources checked when preparing an attempt
   - MathOverflow subset: Original MathOverflow question links
2. **LLM Attempts**: Stored as TeX files in `attacks/`. Ranked writeups use `attacks/open_problems/top_problems/<model>/<unsolvedmath_id>.tex` (or `<unsolvedmath_id>_v2.tex`); the research writeups are in `gpt_6_astra_ultra/` and `gpt_6_astra_pro/`. Numbered files in `definitions/` provide definitions and sources separately and do not count as attempts. Each attempt contains actual mathematical work, references for definitions and concepts, citations for results used, and an honest account of remaining gaps. Lean contributions use a short TeX description linking to the complete source and original output in an external repository, as described in the [Lean contribution guidelines](CONTRIBUTING.md#lean-code-contributions). A statement or research plan alone is not an attempt.
3. **Build Process**: `build_site.py` processes the catalogs, attempts, and reviews into JSON and JavaScript data in `docs/data/`
4. **Auto-Update**: GitHub Actions automatically rebuilds the site when:
   - Files in `attacks/`, `lists/`, or `reviews/` are modified
   - Site pages, build scripts, or tests are modified
5. **Rendering**: The detail page renders the TeX definition and model attempts in the browser, with MathJax for mathematics. The build normalizes the catalogue's supported macros and source links for display while leaving the downloadable TeX unchanged. TeX document layout and preambles are omitted from the browser view.

## Canonical catalogue and display order

`lists/unsolvedmath/problems.json` is the portable catalogue subset derived from
`_Local/Erdos_problems/UnsolvedMath/problems.json`, the authoritative local registry.
It retains canonical IDs, titles and categories; mathematical text on this site
comes from our own TeX statements. `lists/unsolvedmath/display_order.json` lists
canonical IDs in display order. Edit only that ordered list to reorder the site,
then run `python3 build_site.py`; filenames, URLs and attempts remain unchanged.
For example, Hodge has ID **6** and initially appears in display position **4**.

Statements are `attacks/open_problems/top_problems/definitions/<unsolvedmath_id>.tex`;
model attempts add `<model>/` before the same filename. IDs are sparse and are
never used as array offsets. Established UnsolvedMath entries link to their
problem page in the **UnsolvedMath #** column, using their public problem code
(for example, `MPP-001`). Reused codes use an unambiguous numeric URL.
Previously published `problem.*` URLs resolve to the permanent numeric ID.
Newly allocated local records have no public
UnsolvedMath URL until published upstream; this migration does not publish to
that third-party site. Their local detail pages remain available.

## Updating Economics difficulty ranks

Economics identities are stored in `lists/economics/problems.json`; current
difficulty ranks are stored separately in `lists/economics/rankings.csv`.
Prepare a CSV with `Problem ID` and `New rank` columns, using the existing IDs
and one unique rank for every problem. Apply it and rebuild:

```bash
python3 scripts/update_economics_ranks.py /path/to/ranks.csv
python3 build_site.py
```

An ID such as `C73-1` remains `C73-1` even if its difficulty rank later changes.
Do not rename IDs or statement files when reordering. The initial ranks were
matched against the supplied revised-ranking CSV; the original catalogue ranks
are retained for audit. See [Economics catalogue maintenance](lists/economics/README.md)
for source details and validation.

## Importing Research Batches

Use the batch importer to copy each complete problem section containing a
`Research attempt` subsection into its model folder:

```bash
python3 scripts/import_top_problem_attempts.py --model gpt_6_astra_ultra /path/to/research_batch_101_103.tex
python3 build_site.py
```

The importer checks each section's numerical `problemId` against the canonical
`id` in its root definition. It preserves the original preamble and full section word for word,
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
without scraping individual pages on erdosproblems.com. If refreshing fails, the
workflow warns and uses the checked-in snapshot so a temporary upstream failure
does not prevent publication.

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

These are the automated CI checks. The optional browser regression check in
`tests/test_tex_references_browser.mjs` additionally requires Node 22+ and a
separate Chrome debugging session; see the instructions at the top of that file.

Ranked detail links use `problem.html?type=open_problems&id=1`.
Existing `problem.html?type=mo&id=<question_id>` links remain supported. Reviews
for ranked problems are stored in `reviews/open_problems/<unsolvedmath_id>.json`;
existing MathOverflow reviews retain their `reviews/mo/<question_id>.json` paths.

## OpenAI external claims

Records of claims from [openai/math](https://github.com/openai/math) use
`attacks/open_problems/top_problems/openai/<id>.tex` and the **OpenAI** tag.
The Tag filter and Search can find these records. Each record links to the
manuscript, PDF download, and any Lean scope and Comparator files at a pinned
source commit; OpenAI manuscripts and Lean sources are not copied into this repository.

The strict `OPENAI_CLAIM` JSON header identifies the claimed result and its scope.
A full or stronger match sets **Problem Status** to **solved (OpenAI claim)**
and the **LLM claim** to solved even when other attempts remain unresolved.
A partial match displays **partially solved** in the **LLM claim**, while
**Problem Status** retains the source-catalogue status: the complete question
remains open if the catalogue records it as open. The original catalogue status is
retained as `source_status` and displayed separately. Community Review records
human checking independently; these status labels do not verify the proof.
A related result is labelled related and keeps the problem's catalogue status.
Disproofs can settle a conjecture.

`scripts/import_openai_math.py` generates records from an inventory, approved
paper-level adjudication, and original TeX explanations, including the
mathematical hypotheses and conclusion of the claimed result. It preserves existing
records and requires a new version for changed content. The pinned path manifest
in `lists/openai_math/manifest.json` supports offline metadata and link validation.
Proposed solved labels require a separate scope review and user confirmation
before records are generated. See the contribution guide for the record contract.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting new LLM attempts.
Lean formalizations follow the same problem/model folder and filename conventions:
submit a short `.tex` description with a public external source link, scope,
model attribution, Lean/Mathlib versions, and actual checking outcome. The website
does not download or run linked Lean code. A Lean Web reproduction link is optional.

## Acknowledgments

- **Paata Ivanisvili** - For the idea and name "Problem Hunting with LLMs"
- **Terry Tao** - For the Erdos Problems database
- **Thomas Bloom** - For the erdosproblems.com website
- **[Ulam AI](https://www.ulam.ai/) and the UnsolvedMath Contributors** - For the [UnsolvedMath database](https://huggingface.co/datasets/ulamai/UnsolvedMath)

## Disclaimer

**Important:** LLM output is not fully reliable. The attempts documented on this website represent exploratory work by frontier AI models and should not be considered verified mathematical proofs.

The Erdos **LLM Claim** label is assigned by the database rule above and does not
mean that an LLM has supplied a verified solution. The original **Problem Status**
comes from [Tao's collaborative database](https://teorth.github.io/erdosproblems/)
and does not validate the LLM attempts hosted here. Claims within individual
attempts still require mathematical verification.

Linked Lean code is not manually reviewed for correctness or safety. Do not run
untrusted submitted Lean code locally, including through an editor's automatic
checking. Browser reproduction links are not correctness or safety certifications.

## License

The repository's software is licensed under [Apache License 2.0](LICENSE).
Third-party data and source material retain their respective licences.

The Top Open Problems catalogue uses the [UnsolvedMath dataset](https://huggingface.co/datasets/ulamai/UnsolvedMath)
by [Ulam AI](https://www.ulam.ai/) and the UnsolvedMath Contributors. Its curation
and original metadata are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
not Apache-2.0. We select catalogue entries, retain imported problem IDs and
categories, and add extended `.tex` statements and LLM attempts.

Underlying source material may have separate terms, including CC BY-SA 4.0.
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for attribution, a description
of changes, applicable paths, and links to upstream provenance and rights information.
