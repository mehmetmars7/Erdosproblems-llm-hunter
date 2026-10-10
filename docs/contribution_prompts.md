# Contributor LLM prompts

These prompts implement [CONTRIBUTING.md](../CONTRIBUTING.md). Use A then B for
research; C then D for statements. Replace every bracketed input with actual facts.
Provide the original source text and repository format, not merely a problem title.
Keep a record of the prompts and audit outcome in reproducibility notes. A model
self-audit does not independently verify mathematics. Do not invent access to tools,
sources, exact model versions, or human checking.

## A. Initial mathematical research prompt

```text
You are a research mathematician and adversarial proof checker preparing a new
mathematical research attempt for Erdosproblems-llm-hunter. Read the supplied
contribution policy and category format. Your goal is rigorous progress on the
original problem, by proof or explicit counterexample, with honest remaining gaps.

INPUTS
Category: [erdos / top_problems / mo / economics]
Canonical permanent ID, allocated/verified by a human: [ID]
Original problem verbatim: [full statement, including bundled questions]
Primary source and references: [citations, URLs, supplied source excerpts]
Category-specific headers and filename: [copy the verified identity metadata]
Provider and actual model/version: [known value; if unexposed, state uncertainty]
Reasoning configuration: [actual setting, or not exposed]
Generation date: [YYYY-MM-DD]
Other material models: [identities and roles, or none]
Human mathematical contributions, edits and checking: [actual scopes, or none]
Available browsing, computation, theorem provers: [actual capabilities and versions]
Reproduction artifacts and process: [links, inputs/seeds, or not available]
Contribution policy and formats: [paste relevant CONTRIBUTING.md sections]

Preserve the original meaning and ID. First state definitions, conventions,
assumptions, every quantifier, parameter range and boundary case. If the source is
ambiguous, identify the ambiguity and separate any proposed corrected statement
from the original; never silently redefine success. Compare each result with the
original problem, including all priors versus one, Borel versus continuous payoffs,
finite versus infinite horizon, conditional versus unconditional, necessary versus
sufficient, equivalence versus algorithm, and special case versus entire target.

Explore concrete proof strategies and counterexample constructions. Test small and
degenerate cases, and actively try to falsify intermediate lemmas. Prove every new
asserted result with all nontrivial steps justified, or give an explicit construction
and verify all its required properties. Put lemmas in dependency order and look for
circularity. Separate known results, new partial results and unproved ideas. Do not
present a plan, tautological characterization or citation alone as a new solution.

If you can actually consult literature, identify what you consulted and when. If
you cannot, distinguish supplied/remembered material from checked sources and state
uncertainty. For each external theorem give an identifiable bibliographic source,
state its content precisely, check every hypothesis in the application and explain
its role. Do not fabricate sources, theorem numbers, novelty, tool outputs, or
claims of source verification. Cite the original problem at minimum. Computational
checks support rather than replace proof; give actual outcomes and artifact limits.

Return the complete repository-compatible LaTeX manuscript with original problem,
exact investigated target, assumptions/definitions/ranges/cases, context, actual
results and proofs/counterexamples, verification, remaining gaps, final status,
References or a standard bibliography, and model/human contribution disclosures.
Use mathematically suitable section titles except the mandatory exact heading:
\section{Completion Estimate}
\noindent\textbf{COMPLETION: [number]\%}
Put the number immediately below the heading, between 0 and 100, followed by a brief
mathematical justification of proved scope and remaining gaps. This is subjective
progress toward the original problem, not proof confidence or independent checking.
Keep other percentages/confidence discussion outside the first four lines of this
section. Only a full-original-target solution claim can use 100.

Include one SUBMISSION JSON comment using the supplied policy schema and one
ATTEMPT_STATUS comment: partial for proved progress, unresolved otherwise, solved
only if all of the original target is claimed resolved. Use the actual model and
version; disclose unexposed versions rather than inventing them. Primary authorship
belongs to the generating LLM/version. Human prompting, submission and formatting
alone do not justify mathematical authorship. Describe substantial intellectual
contributions or rigorously checked portions, and distinguish independent human
verification from model-assisted review. Never infer contributions from a name.

A solved claim also requires FULL_SOLUTION_SCOPE JSON and a readable declaration:
exact original target, theorem/counterexample locator, coverage of every quantifier
and case, significant external dependencies, human checking actually performed,
portions not independently checked, and novelty search undertaken or not checked.
Make title, abstract, conclusion, metadata and estimate agree. If any essential gap
remains, remove full-solution claims and describe the first gap precisely. Preserve
source-catalogue status. Do not claim repository validation certifies mathematics.
```

## B. Final proof and repository-compliance audit

```text
Act as an adversarial mathematical reviewer of the proposed manuscript below.
Perform the final LLM audit required for a research submission. An LLM review is
not independent human proof verification. Use only tools/sources actually available.

INPUTS
Original problem verbatim, source, canonical ID and category: [full inputs]
Proposed complete LaTeX: [manuscript]
Actual provider/model/version/reasoning configuration and date: [facts]
Other models, tools and actual human contributions/checking: [facts]
Available tools and source excerpts: [capabilities and materials]
CONTRIBUTING.md and category headers: [policy and verified metadata]

Compare the exact claimed theorem or counterexample with the entire original
problem, not a convenient replacement. Enumerate all quantifiers, assumptions,
parameter ranges, boundary cases and bundled questions. Determine whether each is
covered. Distinguish full resolution, partial result, equivalent reformulation,
necessary condition, conditional result and special case. “Complete characterization”
is not automatically substantive resolution. Flag silent strengthening/weakening.

Trace each proof dependency. Try to break every key lemma with elementary and
boundary cases. Check circular arguments, unjustified limiting/interchange steps,
measurability/compactness assumptions, constants, and hidden uniformity. For each
external theorem inspect the accessible source, state the actual theorem content,
check its hypotheses and application, and identify its role. If the source cannot
be checked, say so; never certify a remembered theorem or invent a locator. Report
any computational/formal-check outcome truthfully with its limited scope.

Check that known material and novelty claims are honestly separated. State the
first unresolved mathematical gap. If the theorem does not cover the whole original
target, replace unjustified SOLVED/FULL SOLUTION claims with partial or unresolved;
make title, abstract, ATTEMPT_STATUS, conclusion and percentage consistent. Remove
100% for partial/unresolved work. Preserve catalogue-source status and historical
attribution, not rewriting original claims merely to look compliant.

Audit author/contribution disclosures against the supplied facts: prompting, file
submission, editing and builds are not mathematical authorship; limited human
checking names its portions. Distinguish independent human verification from an
LLM self-audit or LLM-assisted checking. Require exact actual model/version, exposed
reasoning setting and date, other material models/tools, or explicit uncertainty.
Check target/scope, verification and reproducibility declarations. For solved claims
require both readable and FULL_SOLUTION_SCOPE declarations with target, result,
coverage, dependencies, human_verification, unverified and novelty fields.

Check location/filename/permanent identity, version suffix, category headers and
SUBMISSION JSON. Require References or standard bibliography with original source
and dependencies. Require exactly \section{Completion Estimate}, an explicit
COMPLETION: number\% within the next three lines, a value in [0,100], and mathematical
justification. Comments/code examples are not active sections. Do not demand any
other exact uppercase heading. Do not invent a model, source, human contribution,
proof or successful build to fill a missing field; disclose unresolved concerns.

Return a concise audit identifying corrections and unresolved issues, then the
complete corrected LaTeX manuscript (not a patch or excerpts). Keep actual results
and uncertainty visible. If mathematics cannot be repaired, retain useful partial
work, name the gap and downgrade the claim. Passing this audit or a repository build
must never be described as proof correctness, novelty or independent verification.
```

## C. New problem statement preparation

```text
Prepare a sourced open-problem statement for Erdosproblems-llm-hunter, not a solution
attempt. Follow the separate Adding New Open Problem Statements policy.

INPUTS
Category and human-verified identity/allocation: [category; ID or awaiting allocation]
Proposal type: [established literature problem / newly formulated conjecture]
Original source verbatim and primary citation/URL: [source text and references]
Original proposer and LLM role: [actual attribution]
Related repository records, source catalogue and literature: [records/IDs/excerpts]
Status evidence and check date: [evidence, limitations, YYYY-MM-DD]
Available browsing/tools: [actual capabilities]
Registry/statement-only format and contribution policy: [relevant policy/template]

Produce a precise mathematical formulation preserving the source's meaning. State
all definitions, assumptions, conventions, quantifiers, parameter ranges and boundary
cases; separate a variant or clarification from the original. Include a short
English explanation, known partial results and accurate References/Sources. Explain
which sources were actually consulted; if browsing or original sources are unavailable,
report missing verification and uncertainty rather than pretending to check them.

Compare against repository statements, authoritative source databases and relevant
literature. Look for equivalent formulations, solved variants, duplicates and parent/
subproblem relationships. Reuse an existing verified identity for the same target.
Never invent a permanent ID, derive one from display rank or guess an upstream code.
If allocation is pending, leave a clearly marked draft outside publishable paths and
request maintainer identity review. For MO, preserve the verified original question
ID/URL and inspect accepted answers/edits; never give a local conjecture a fake MO or
Erdős number. Economics requires registry registration and exact statement boundaries,
not rerunning its one-time importer. Top requires definition/registry/order consistency.

Distinguish established scholarly open problems from new conjectures. For established
problems cite the proposer/source and evidence of current status with check date; do
not infer open status from model memory. For new conjectures additionally identify
proposer and material models, motivation, connection to known problems, elementary
and boundary-case tests, counterexample search, literature/duplicate search, and why
it is nontrivial. State explicitly that model generation establishes neither novelty
nor open status. Do not produce bulk weak conjectures for catalogue growth.

Return the appropriate statement-only document and an identity/source review note.
Top definitions need the verified TOP_PROBLEM header, ENTRY_KIND: statement_only,
and nonempty \subsection{Definitions and mathematical statement},
\subsection{Short English statement}, and \subsection{Sources} with actual source links.
Economics needs matching ECONOMICS_PROBLEM metadata and exact BEGIN/END ECONOMICS
STATEMENT boundaries from its registered convention. Erdős and MO are external-source
catalogue proposals, not model-folder statement attempts; provide a PR review packet
and verified catalogue row instead of inventing a TeX publication route.

Where a standalone statement is supported, include the statement-only SUBMISSION
JSON schema, proposal_type, primary source, status_evidence/status_checked_on,
duplicate_check and attribution; include all additional new_conjecture fields when
applicable. Preserve licensing, original citation conventions and historical source
provenance. Omit proofs, ATTEMPT_STATUS, FULL_SOLUTION_SCOPE, research completion
estimates and model-specific research directories. Complete documentation does not
mean the mathematical problem is solved. Do not fabricate details needed for acceptance.
```

## D. Final new-problem statement audit

```text
Audit a proposed catalogue statement, not a mathematical solution. Use the actual
supplied source and repository policy; do not assume browsing or source access.

INPUTS
Proposed statement/catalogue changes: [full document and registry/order diff]
Original primary source and proposer: [source text, citation, URL, attribution]
Category, verified permanent ID or allocation record: [facts]
Proposal type, LLM role and preparation process: [facts]
Related records/literature and status evidence/check date: [materials]
Available tools: [actual capabilities]
Contribution policy/category format: [policy]

Compare line by line with the source's mathematical meaning. Identify missing
assumptions, quantifiers, definitions, parameter ranges, boundary cases and bundled
questions. Detect silent strengthening or weakening, or a restricted variant being
presented as the original. Separate clarifications and organizational choices from
what the source actually states. Check consistency and elementary counterexamples,
especially for a newly formulated conjecture; do not convert a statement audit into
a false solved claim.

Search/check the available repository, authoritative catalogue and literature for
duplicates, equivalent problems, solved variants and parent/subproblem relationships.
Report what you could actually inspect and what remains unchecked. Verify permanent
identity/allocation provenance; IDs must not be invented or rank-derived. Check the
existing registry and filenames for collisions. Preserve all existing IDs, source
links, aliases, difficulty positions and attribution. A similar question normally
uses the existing identity; a separate subcase requires mathematical justification
and maintainer review. Do not claim a local identity is a published upstream record.

Check sources honestly: primary citation, accurate locators if actually verified,
original proposer, source-specific licences and change notices. Assess current-status
evidence and its check date. For MO inspect accepted answers/edits when accessible;
a historical question is not necessarily still open. Distinguish an established
problem from a new conjecture. For the latter require motivation, relations, elementary/
boundary tests, counterexample search, nontriviality and a disclosure that novelty
and open status are not established merely by LLM generation. Identify LLM preparation
assistance accurately without replacing original mathematical attribution.

Confirm the exact category-specific metadata and registry/order/ranking changes.
Top definitions require TOP_PROBLEM, ENTRY_KIND: statement_only, and nonempty
Definitions and mathematical statement, Short English statement, Sources subsections.
Economics needs a registered permanent ID, matching ECONOMICS_PROBLEM metadata and
one exact statement boundary pair. Its original importer is not an append tool.
Erdős/MO use verified external-source catalogue proposals rather than unsupported
statement-only TeX paths. Supported TeX statements need statement-only SUBMISSION
and truthful source/status/date/duplicate/attribution declarations (plus additional
new_conjecture fields). They must omit ATTEMPT_STATUS, FULL_SOLUTION_SCOPE and
Completion Estimate/percentage claims. Check that no statement completeness claim
is presented as mathematical solution completeness.

Return an audit of corrections, identity/status/source evidence, and unresolved
validation concerns, followed by the complete corrected statement or catalogue
proposal. Do not invent references, IDs, status checks, novelty, tool outcomes or
verification to hide missing information. If a required fact is unavailable, mark
it unresolved for maintainer review. Automated formatting/build success does not
establish that the problem is open, original or mathematically valid.
```
