# Third-Party Notices

The root [LICENSE](LICENSE) contains Apache License 2.0 for this repository's
software. It does not relicense third-party datasets, quotations, or source
material. Their original terms continue to apply wherever that material is
reproduced, adapted, or included in generated website data.

## UnsolvedMath

This repository uses **UnsolvedMath: A Curated Collection of Open Mathematics
Problems**, provided by **[Ulam AI](https://www.ulam.ai/)**, with attribution to
the **UnsolvedMath Contributors**.

- Website: [UnsolvedMath](https://www.unsolvedmath.com/)
- Dataset: [ulamai/UnsolvedMath on Hugging Face](https://huggingface.co/datasets/ulamai/UnsolvedMath)
- Upstream attribution and licensing: [dataset card](https://huggingface.co/datasets/ulamai/UnsolvedMath/blob/main/README.md)
- Licence for the dataset's curation and original metadata:
  [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
  ([legal code](https://creativecommons.org/licenses/by/4.0/legalcode))

The UnsolvedMath curation and original metadata remain under CC BY 4.0.
They have not been relicensed under Apache-2.0. Reuse must retain appropriate
attribution, the licence link, and an indication of changes. This attribution
does not imply endorsement by Ulam AI, UnsolvedMath, or the original authors.

### Use and changes in this repository

The Top Open Problems database comes mainly from UnsolvedMath. This repository:

- Selects a catalogue subset and retains the imported numerical problem IDs,
  problem numbers, titles, categories, and source-status metadata.
- Provides extended mathematical statements, definitions, English summaries,
  and references in `.tex` files, and adds separately attributed LLM attempts.
- Maintains its own display order and produces JSON and JavaScript records
  for the website.
- Includes additional local entries where needed; these are not represented
  as published upstream records and have no upstream problem link until one exists.

The portable metadata subset is in `lists/unsolvedmath/problems.json`, with
display order in `lists/unsolvedmath/display_order.json`. Extended statements
are in `attacks/open_problems/top_problems/definitions/`, and model attempts
are in sibling model folders under `top_problems/`. Generated
representations appear in `docs/data/open_problems_data.js` and
`docs/data/top_problems/`. The CC BY 4.0 attribution applies to the imported
curation and metadata wherever reproduced; a file's location does not change
the licence of any third-party material within it. The separately sourced
MathOverflow subset is not attributed to UnsolvedMath.

### Underlying sources and provenance

UnsolvedMath's licence covers its curation and original metadata. Linked or
incorporated source material remains subject to its own terms. The upstream
dataset card identifies some Oberwolfach Reports source material as
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); those terms,
including ShareAlike where applicable, are not superseded by CC BY 4.0 or
this repository's Apache-2.0 licence.

Consult the matching upstream record and original source for attribution,
provenance, and rights information, including any `NEEDS_REVIEW` or other rights
notes. The portable catalogue is a metadata subset, not a complete copy of all
upstream provenance fields. Preserve the relevant notices, source-specific
terms, and indications of previous changes when reusing the underlying material.
