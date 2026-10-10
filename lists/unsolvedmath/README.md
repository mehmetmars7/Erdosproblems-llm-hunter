# UnsolvedMath catalogue subset

This directory contains selected catalogue metadata based on
[UnsolvedMath](https://www.unsolvedmath.com/) by [Ulam AI](https://www.ulam.ai/)
and the UnsolvedMath Contributors. The upstream dataset is available on
[Hugging Face](https://huggingface.co/datasets/ulamai/UnsolvedMath).

Imported curation and original metadata remain licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), not the software's
Apache-2.0 licence. Referenced or incorporated source material may have separate
terms. See [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md) for attribution,
changes, and source-specific licensing information.

`problems.json` retains imported problem IDs and categories and includes our
English statement summaries. Additional local records are distinguished by
the absence of an upstream problem URL. `display_order.json` controls the
website's ordering independently of problem identity. Extended `.tex`
statements are stored in `attacks/open_problems/top_problems/definitions/`;
LLM attempts use the sibling model folders under `top_problems/`.

`id` is the permanent numeric identity used in our URLs and filenames.
`problem_number` is UnsolvedMath's public code (for example, `MPP-001`), shown
in the **UnsolvedMath #** column. `external_url` uses this code unless the
full upstream registry reuses it for different records; those entries use
UnsolvedMath's unambiguous numeric route. Unpublished local additions have no
external link. Never derive a public code from an ID or display position.

`legacy_ids` preserves the exact former `problem.*` identifiers as URL aliases.
Old links resolve to the numeric ID and update the browser address while
retaining other query parameters and fragments. These aliases do not affect
ordering, filenames, or mathematical identity.

## New statements and prospective submissions

Follow [CONTRIBUTING.md](../../CONTRIBUTING.md#adding-new-open-problem-statements)
for source, duplicate/equivalence, status and attribution review. Reuse canonical
upstream IDs; display rank never allocates identity. New local targets need approved
identity review and an allocation against the complete external registry/watermark,
`LOCAL-<id>`, `published: false`, parent IDs when applicable, and no invented upstream
URL. The OpenAI allocator is specialized and does not publish or approve a record.

Commit the definition, portable registry and complete display order together.
Statement-only TeX preserves TOP_PROBLEM, ENTRY_KIND: statement_only, and the three
Definitions and mathematical statement / Short English statement / Sources subsections.
Use the prospective statement SUBMISSION declaration; omit research statuses and
completion estimates. New model attempts instead require research declarations, exact
model/version, References and Completion Estimate. Existing importer workflows remain
available; import success alone does not satisfy prospective submission validation.
