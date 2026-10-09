# Economics catalogue

`problems.json` is the permanent identity registry. Each ID was assigned once as
`{JEL code}-{initial New rank}` using the supplied revised CSV. The ID stays fixed
when the displayed rank changes. For example, `C73-1` can later have rank 20
without changing its URL or statement filename.

The attachments contain **657 actual classified problem statements**, despite
the TeX introduction reporting 653. All 657 match the revised CSV exactly by
source OP ID, problem title and JEL code. Four OP IDs were reused by unrelated
problems, so an OP ID alone is insufficient to identify those statements. The
registry keeps original OP IDs, source names, labels, and source metadata as
provenance. Current display order lives separately in `rankings.csv`.

Statements are stored in
`attacks/open_problems/economics/statements/{permanent-id}.tex`. Each standalone
TeX file retains definitions, assumptions, questions, scope/status notes,
references, merged formulations, and applicable shared source conventions. Old
difficulty labels and the superseded top-level classification command are
removed. Research attempts live in sibling model folders, separately from the
canonical statements. Run the ordinary site build to emit embedded browser data
and identical local downloadable copies of the statements and attempts.

## Research attempts

Use `attacks/open_problems/economics/{model}/{permanent-id}.tex`. Further
versions use `{permanent-id}_v2.tex`, `_v3.tex`, and so on. For example,
`gpt_6_astra_pro/C73-1.tex` and `C73-1_v2.tex` are separate attacks on the
same stochastic-games problem. The build joins by permanent ID, never current
rank or the potentially reused source OP ID.

Each attempt is a complete standalone TeX document with one
`ECONOMICS_PROBLEM` JSON comment matching the statement's `id`, `title`,
`jel_code`, and `source_id`; one `FIRST_POSTED: YYYY-MM-DD` comment; and one
explicit `ATTEMPT_STATUS: unresolved`, `partial`, or `solved` comment. Partial
results remain unresolved for the full problem. Keep local paths, upload chatter,
unrelated problems, and unpublished companion-file references out of public TeX.
The website displays each version with its model, status, date, source link,
and downloadable TeX. Statement files, IDs and difficulty ranks are unchanged.

`jel_codes.json` stores the JEL descriptions from the supplied classification
text, with its source hash. The build includes one shared lookup containing the
codes used by the catalogue in `economics_data.js`. Problem pages display the
description in parentheses after the linked JEL code; no additional request or
runtime XML parsing is needed. Edit this JSON and rebuild to update descriptions.

## Updating ranks

1. Copy `rankings.csv` and edit only `New rank`. Include every permanent Problem
   ID exactly once, with each integer rank from 1 through 657 exactly once.
2. Validate the revised file:
   `python scripts/update_economics_ranks.py revised-ranks.csv --check`
3. Apply it:
   `python scripts/update_economics_ranks.py revised-ranks.csv`
4. Rebuild the full site with `python build_site.py` to refresh cache-versioned
   Economics data URLs as well as the complete static site.

`Problem title` and `JEL code` columns are optional when using permanent IDs;
when provided, they are cross-checked. Updates change `rankings.csv` and generated
data only. They preserve the registry, permanent IDs, statement filenames and
statement content.

For a future CSV still using legacy OP IDs, add `--allow-source-ids`. Reused OP IDs
must also include matching title and JEL columns. Ambiguous IDs, title/JEL
mismatches, missing/duplicate problems, and noncontiguous/duplicate ranks are
rejected before any ranking is written.

The original import command is intentionally one-time and refuses to run after
the identity registry exists. To revise a statement later, edit its permanent
TeX file between the `% BEGIN ECONOMICS STATEMENT` and
`% END ECONOMICS STATEMENT` markers and rebuild. Keep its permanent ID and
registry identity unchanged.

## Original import

```sh
python scripts/import_economics.py --tex Merged_Open_Problems_JEL_difficulty_ranked.tex \
  --ranks Open_Problems_Revised_Economics_Ranking_new.csv
```

The registry records SHA-256 hashes of both original attachments. Actual
section/`ProblemClassification` pairs govern parsing; stale or absent
`MERGED_PROBLEM` comments do not determine problem identity.
