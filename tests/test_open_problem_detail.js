// Run with: node tests/test_open_problem_detail.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'docs/problem.html'), 'utf8');
const scripts = Array.from(html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g), m => m[1]);
for (const script of scripts) new vm.Script(script);
const detailScript = scripts.find(script => script.includes('function initGiscus'));
const ranked = (id, rank) => ({
    id, rank, title: `Title ${rank}`, collection: 'ranked',
    domain_label: 'Algebra & geometry', status: 'open', llm_status: 'none',
    exact_target: 'For every n < 10, prove the stated inequality.',
    definition_tex: String.raw`\subsection{Definitions and mathematical statement}
For every $n < 10$, prove the stated inequality.
\subsection{Sources}
\href{https://example.org/?x=1&y=2}{Definition <source>}`,
    definition_file: `attacks/open_problems/top_problems/definitions/${id}.tex`,
    status_qualification: 'Bounded review; still open.', status_reviewed_at: '2026-09-22',
    sources: [{ citation: 'Definition <source>', url: 'https://example.org/?x=1&y=2', role: 'formal_statement' }],
    attacks: []
});
const records = {
    '20000601': ranked(20000601, 1),
    '6': ranked(6, 2),
    'mo:42': { id: 'mo:42', collection: 'mo', rank: null }
};

const erdosRecords = {
    '1': { number: '1', status: 'open', llm_status: 'unresolved', problem_url: 'https://www.erdosproblems.com/1', attacks: [] }
};

async function render(query, open = records, fetchRecord = async () => ({ ok: false, status: 404 }), erdos = erdosRecords) {
    const elements = new Map();
    function element(id) {
        if (!elements.has(id)) elements.set(id, {
            innerHTML: '', textContent: '', style: {}, hidden: ['contribute-cta', 'erdos-main-link'].includes(id), children: [],
            appendChild(child) { this.children.push(child); },
            querySelector(selector) { return element(`${id} ${selector}`); }
        });
        return elements.get(id);
    }
    const callbacks = [];
    const document = {
        addEventListener(name, callback) { if (name === 'DOMContentLoaded') callbacks.push(callback); },
        getElementById: element,
        querySelector: element,
        documentElement: { getAttribute() { return 'light'; } },
        createElement() { return { dataset: {} }; }
    };
    const requests = [];
    const context = vm.createContext({
        document, URL, URLSearchParams, console,
        fetch: async (url, options) => {
            requests.push({ url, options });
            return fetchRecord(url, options);
        },
        window: { location: new URL(`https://example.org/problem.html${query}`),
            history: { replaceState(state, title, url) { this.lastURL = url; } }, OPEN_PROBLEMS_DATA: open,
            OPEN_PROBLEMS_CATALOG: { edition_date: '2026-09-22' } },
        moProblems: { '42': { id: '42', title: 'Legacy question', score: 5, link: 'https://mathoverflow.net/questions/42', attacks: [] } },
        erdosProblems: erdos
    });
    vm.runInContext(fs.readFileSync(path.join(root, 'docs/app.js'), 'utf8'), context);
    vm.runInContext(fs.readFileSync(path.join(root, 'docs/catalog-math.js'), 'utf8'), context);
    context.window.ProblemHunting.initAttemptPreviews = () => {};
    context.window.ProblemHunting.initTeXReferences = () => {};
    callbacks.length = 0;
    vm.runInContext(detailScript, context);
    await callbacks[0]();
    return { element, context, requests };
}

async function main() {
let page = await render('?type=open_problems&id=20000601');
assert.equal(page.element('page-title').textContent, 'Title 1');
assert.match(page.element('problem-meta').innerHTML, /Problem Status:/);
assert.doesNotMatch(page.element('problem-meta').innerHTML, /Problem ID:|Catalog status:|Rank:/);
assert.match(page.element('problem-meta').innerHTML, /No attempts yet/);
assert.match(page.element('problem-links').innerHTML, /\$n &lt; 10\$/);
assert.match(page.element('problem-links').innerHTML, /Definition &lt;source&gt;/);
assert.doesNotMatch(page.element('problem-links').innerHTML, /Catalog edition:|2026-09-22/);
assert.match(page.element('problem-links').innerHTML, /x=1&amp;y=2/);
assert.match(page.element('problem-statement-source').innerHTML, /View TeX definition \(20000601\.tex\)/);
assert.match(page.element('problem-statement-source').innerHTML, />source<\/a>/);
assert.doesNotMatch(page.element('problem-links').innerHTML, /View TeX definition/);
assert.equal(page.element('prev-problem').style.visibility, 'hidden');
assert.equal(page.element('next-problem').href, 'problem.html?type=open_problems&id=6');
assert.match(page.element('attempts-container').innerHTML, /No LLM attempts yet/);
assert.notEqual(page.element('llm-attempts-section').style.display, 'none');
assert.equal(page.element('.giscus').children[0].dataset.term, 'OpenProblem-20000601');
assert.equal(page.requests.length, 1);
assert.equal(page.requests[0].url, 'data/top_problems/20000601.json');
assert.equal(page.requests[0].options.cache, 'no-store');
assert.doesNotMatch(page.element('problem-meta').innerHTML, /UnsolvedMath #/);
const reviewURL = new URL(page.context.getReviewIssueUrl('open_problems', '20000601'));
assert.equal(reviewURL.searchParams.get('problem_type'), 'Open Problems');
assert.equal(reviewURL.searchParams.get('problem_id'), '20000601');

const authorSubmission = JSON.parse(fs.readFileSync(path.join(root,
    'reviews/open_problems/30007169.json'), 'utf8'));
page = await render('?type=open_problems&id=20000601', {
    '20000601': { ...records['20000601'], review: authorSubmission }
});
const submissionMeta = page.element('problem-meta').innerHTML;
assert.match(submissionMeta, /Community Review:<\/strong> submitted \(/);
assert.match(submissionMeta, /href="https:\/\/github.com\/ckkogler"/);
assert.match(submissionMeta, /href="https:\/\/github.com\/samuel-kittle"/);
assert.doesNotMatch(submissionMeta, /submitted by authors|independent review pending/);
assert.doesNotMatch(submissionMeta, /accepted/);

const acceptedReview = JSON.parse(fs.readFileSync(path.join(root, 'reviews/erdos/652.json'), 'utf8'));
page = await render('?type=erdos&id=1', records, undefined, {
    '1': { ...erdosRecords['1'], review: acceptedReview }
});
assert.match(page.element('problem-meta').innerHTML, /Community Review:<\/strong> accepted/);
assert.match(page.element('problem-meta').innerHTML, /href="https:\/\/github.com\/plby"/);
assert.match(page.element('problem-meta').innerHTML, /href="https:\/\/github.com\/teorth"/);
assert.doesNotMatch(page.element('problem-meta').innerHTML, /independent review pending/);

page = await render('?type=open_problems&id=6');
assert.equal(page.element('erdos-main-link').hidden, true);
assert.equal(page.element('prev-problem').href, 'problem.html?type=open_problems&id=20000601');
assert.equal(page.element('next-problem').style.visibility, 'hidden');

// OpenAI claims show attributed problem status, keep source status separate, use their own release date, and
// expose safe links to all manuscripts and formalisation files in the snapshot.
const openAIMetadata = {
    source_repo: 'https://github.com/openai/math',
    source_commit: 'adc7f1241b42e322a6451854ab7e4b4c146bf78a',
    release_date: '2026-10-06', match: 'full', resolution: 'disproved',
    families: [{ family: '197', title: 'Example family <title>',
        manuscripts: [{ title: 'Example manuscript', pdf_path: 'preprints/Result-in-CAT(0)-spaces/custom.pdf',
            readme_path: 'preprints/Result-in-CAT(0)-spaces/README.md', date: '2026-09-23',
            statement_sources: [{ path: 'preprints/Result-in-CAT(0)-spaces/build/source/main.tex',
                line: 57, label: 'Theorem 1.1' }] }],
        lean: { doc_path: 'lean/docs/197.md', comparators: ['lean/ComparatorChallenges/Result.lean',
            'lean/ComparatorChallenges/Result.json'], covers_main_theorem: true },
        reasoning_trace: 'reasoning_traces/197.pdf' }]
};
const openAIAttempt = { model: 'OpenAI', claimant: 'OpenAI', entry_kind: 'external_claim',
    status: 'solved', date_posted: '2026-10-06', openai: openAIMetadata,
    file_path: 'attacks/open_problems/top_problems/openai/20000601.tex',
    raw: String.raw`\subsection{OpenAI's claim}
An original summary with $x^2$.
\subsection{Scope relative to this problem}
The claimed counterexample has $x^2=1$.
\subsection{Status caveat}
These are claims, not verified proofs.` };
const openAIProblem = { ...records['20000601'], tags: ['openai'], llm_status: 'solved',
    llm_status_source: 'openai_claim', completion: 100,
    attacks: [{ model: 'GPT 6 Astra Ultra', status: 'solved', date_posted: '2026-01-01', raw: 'Earlier claim.' },
        { model: 'GPT 6 Astra Ultra', status: 'unresolved', raw: 'Unresolved attempt.' }, openAIAttempt] };
page = await render('?type=open_problems&id=20000601', { '20000601': openAIProblem });
assert.match(page.element('problem-meta').innerHTML, /Tags:<\/strong> <a href="open_problems\.html\?tag=openai">OpenAI/);
assert.match(page.element('problem-meta').innerHTML, /Problem Status:<\/strong> solved \(OpenAI claim\)/);
assert.match(page.element('problem-meta').innerHTML, /Source catalogue status:<\/strong> open/);
assert.equal(page.element('contribute-cta').hidden, true);
assert.match(page.element('problem-meta').innerHTML, /LLM Claim:<\/strong> solved \(OpenAI claim, 2026-10-06\)/);
assert.doesNotMatch(page.element('problem-meta').innerHTML, /solved \(2026-01-01\)/);
assert.equal(page.element('llm-attempts-section h2').textContent, 'LLM claims and collection records');
let openAIHtml = page.element('attempts-container').innerHTML;
assert.ok(openAIHtml.indexOf('<h3>OpenAI paper:') < openAIHtml.indexOf('Earlier claim.'));
assert.ok(openAIHtml.indexOf('Earlier claim.') < openAIHtml.indexOf('Unresolved attempt.'));
assert.match(openAIHtml, /<h3>OpenAI paper: Example manuscript<\/h3>/);
assert.match(openAIHtml, /OpenAI catalogue family: Example family &lt;title&gt;/);
assert.match(openAIHtml, /Relationship to this problem:<\/strong> Full solution claimed for this problem/);
assert.match(openAIHtml, /OpenAI claim: solved \(disproved\), not independently verified/);
assert.match(openAIHtml, /\/blob\/adc7f1241b42e322a6451854ab7e4b4c146bf78a\/preprints\/Result-in-CAT%280%29-spaces\/custom\.pdf/);
assert.match(openAIHtml, /\/raw\/adc7f1241b42e322a6451854ab7e4b4c146bf78a\/preprints\/Result-in-CAT%280%29-spaces\/custom\.pdf/);
assert.match(openAIHtml, />PDF<\/a>/);
assert.match(openAIHtml, />PDF \(download\)<\/a>/);
assert.match(openAIHtml, />Lean scope<\/a>/);
assert.match(openAIHtml, />Manuscript page<\/a>/);
assert.match(openAIHtml, /\/build\/source\/main\.tex#L57/);
assert.match(openAIHtml, />Statement: Theorem 1\.1<\/a>/);
assert.match(openAIHtml, /Comparator: Result\.json/);
assert.match(openAIHtml, />Reasoning summary<\/a>/);
assert.match(openAIHtml, /not run the Lean code/);
assert.match(openAIHtml, /2026-09-23/);
assert.match(openAIHtml, /An original summary with \$x\^2\$/);
assert.match(openAIHtml, /The claimed counterexample has \$x\^2=1\$/);
assert.equal((openAIHtml.match(/Scope relative to this problem/g) || []).length, 1);
assert.ok(openAIHtml.indexOf('The claimed counterexample') < openAIHtml.indexOf('>PDF</a>'));
assert.doesNotMatch(openAIHtml, /<title>|<iframe/);
const partialAttempt = { ...openAIAttempt, status: 'unresolved',
    openai: { ...openAIMetadata, match: 'partial', resolution: 'partial' } };
page = await render('?type=open_problems&id=20000601', { '20000601': { ...openAIProblem,
    status: 'partial', source_status: 'open', llm_status: 'partial', llm_status_source: 'openai_claim',
    attacks: [partialAttempt] } });
assert.match(page.element('problem-meta').innerHTML, /Problem Status:<\/strong> open<\/p>/);
assert.match(page.element('problem-meta').innerHTML, /Source catalogue status:<\/strong> open/);
assert.match(page.element('problem-meta').innerHTML, /LLM Claim:<\/strong> partially solved \(OpenAI claim, 2026-10-06\)/);
assert.match(page.element('attempts-container').innerHTML, /OpenAI claim: partially solved/);
assert.match(page.element('problem-meta').innerHTML, /Community Review:<\/strong> unreviewed/);
assert.equal(page.element('contribute-cta').hidden, false);
assert.doesNotMatch(page.element('attempts-container').innerHTML, /OpenAI claim: solved/);
assert.match(page.element('attempts-container').innerHTML,
    /Relationship to this problem:<\/strong> Partial solution claimed for this problem/);
page = await render('?type=open_problems&id=20000601', { '20000601': { ...openAIProblem,
    status: 'solved', source_status: 'solved', llm_status: 'partial', attacks: [partialAttempt] } });
assert.match(page.element('problem-meta').innerHTML, /Problem Status:<\/strong> solved<\/p>/);
assert.match(page.element('problem-meta').innerHTML, /LLM Claim:<\/strong> partially solved \(OpenAI claim/);
assert.equal(page.element('contribute-cta').hidden, true);
const hostileAttempt = { ...openAIAttempt, openai: { ...openAIMetadata,
    families: [{ title: '<script>alert(1)</script>', manuscripts: [{ title: '<img src=x onerror=alert(1)>',
        pdf_path: 'javascript:alert(1)', readme_path: 'https://evil.example/paper' }],
        lean: { doc_path: 'lean/docs/../evil.md', comparators: ['https://evil.example/Comparator.lean'] } }] } };
page = await render('?type=open_problems&id=20000601', { '20000601': { ...openAIProblem, attacks: [hostileAttempt] } });
openAIHtml = page.element('attempts-container').innerHTML;
assert.doesNotMatch(openAIHtml, /<script|<img|href="(?:javascript:|https:\/\/evil)/);
assert.match(openAIHtml, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
assert.match(openAIHtml, /<h3>OpenAI paper: &lt;img src=x onerror=alert\(1\)&gt;<\/h3>/);

// A catalogue question keeps its identity while the claim card names the papers
// actually opened by its PDF links and presents their scope before those links.
const maxCutProblem = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/top_problems/2800802.json'), 'utf8'));
page = await render('?type=open_problems&id=2800802', { '2800802': maxCutProblem });
assert.equal(page.element('page-title').textContent,
    '10 Lectures and 42 Open Problems — Sum of Squares approximation ratio for Max-Cut');
openAIHtml = page.element('attempts-container').innerHTML;
assert.match(openAIHtml, /<h3>OpenAI papers: A Direct Proof of Optimal Max-Cut Hardness; The Unique Games Theorem<\/h3>/);
assert.ok(openAIHtml.indexOf('Scope relative to this problem') < openAIHtml.indexOf('>PDF</a>'));
assert.ok(openAIHtml.indexOf('Paper: A Direct Proof of Optimal Max-Cut Hardness') < openAIHtml.indexOf('>PDF</a>'));
const relatedAttempt = { ...openAIAttempt, status: 'unresolved',
    openai: { ...openAIMetadata, match: 'related', resolution: 'partial' } };
page = await render('?type=open_problems&id=20000601', { '20000601': { ...openAIProblem,
    status: 'open', source_status: 'open', llm_status: 'related', attacks: [relatedAttempt] } });
assert.match(page.element('problem-meta').innerHTML, /Problem Status:<\/strong> open<\/p>/);
assert.match(page.element('attempts-container').innerHTML,
    /Relationship to this problem:<\/strong> Related result; no solution to this problem claimed/);
assert.doesNotMatch(page.element('attempts-container').innerHTML, /OpenAI claim: solved|OpenAI claim: partially solved/);

// The Hodge withdrawal is a separate short v2 notice, with a current source
// link, while the original pinned release record remains available.
const hodgeWithNotice = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/top_problems/6.json'), 'utf8'));
const hodgeNotice = hodgeWithNotice.attacks.find(a => a.model === 'OpenAI' && a.version === 2);
assert.equal(hodgeNotice.openai.resolution, 'withdrawn');
assert.ok(hodgeWithNotice.attacks.some(a => a.model === 'OpenAI' && a.version === 1));
page = await render('?type=open_problems&id=6', { '6': hodgeWithNotice });
const hodgeCards = page.element('attempts-container').innerHTML;
assert.equal(hodgeWithNotice.status, 'open');
assert.match(page.element('problem-meta').innerHTML, /Problem Status:<\/strong> open<\/p>/);
assert.match(page.element('problem-meta').innerHTML, /LLM Claim:<\/strong> partially solved \(OpenAI claim, 2026-10-06\)/);
assert.ok(hodgeCards.indexOf('<h3>OpenAI withdrawal notice (v2):') < hodgeCards.indexOf('<h3>OpenAI papers:'));
assert.ok(hodgeCards.indexOf('<h3>OpenAI papers:') < hodgeCards.indexOf('<h3>Attempt 3:'));
assert.match(hodgeCards, /OpenAI withdrawal notice \(v2\): The rational Hodge conjecture for products of K3 surfaces/);
assert.match(hodgeCards, /OpenAI notice: withdrawn/);
assert.match(hodgeCards, /Withdrawn on October 6, 2026/);
assert.match(hodgeCards, /href="https:\/\/github.com\/openai\/math\/blob\/main\/preprints\/The-rational-Hodge-conjecture-for-products-of-K3-surfaces-October-4-2026\/hodge-conjecture-products-k3.pdf"/);
assert.match(hodgeCards, /OpenAI papers:/);
assert.match(hodgeCards, /Archived manuscript/);

page = await render('?type=open_problems&id=mo%3A42');
assert.match(page.element('problem-meta').innerHTML, /MathOverflow subset/);
assert.equal(page.element('.giscus').children[0].dataset.term, 'MO-42');
assert.equal(page.requests.length, 0);
page = await render('?type=erdos&id=1');
assert.equal(page.element('page-title').textContent, 'Erdos Problem #1');
assert.equal(page.element('.giscus').children[0].dataset.term, 'Erdos-1');
assert.equal(page.requests.length, 0);
assert.equal(page.element('contribute-cta').hidden, false);
assert.equal(page.element('erdos-main-link').hidden, true);

// The UnsolvedMath ID and the Erdős number are separate namespaces.
const erdosNine = { '9': { ...erdosRecords['1'], number: '9' } };
const epNine = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/top_problems/1881.json'), 'utf8'));
page = await render('?type=open_problems&id=1881', { '1881': epNine }, undefined, erdosNine);
assert.equal(page.element('erdos-main-link').hidden, false);
assert.match(page.element('erdos-main-link').innerHTML, /href="problem\.html\?type=erdos&amp;id=9">Erdős Problem #9<\/a>/);
assert.ok(html.indexOf('id="erdos-main-link"') < html.indexOf('<section class="problem-statement">'));
for (const code of ['MPP-001', 'EP-0', 'EP-999999', 'EP-9<script>', 'EP--9']) {
    page = await render('?type=open_problems&id=1881', { '1881': { ...epNine, problem_number: code } }, undefined, erdosNine);
    assert.equal(page.element('erdos-main-link').hidden, true, code);
}
const erdosDataSource = fs.readFileSync(path.join(root, 'docs/data/erdos_data.js'), 'utf8');
const erdosData = JSON.parse(erdosDataSource.slice('var erdosProblems = '.length).split(';\n', 1)[0]);
const registry = JSON.parse(fs.readFileSync(path.join(root, 'lists/unsolvedmath/problems.json'), 'utf8'));
for (const entry of registry.filter(entry => /^EP-\d+$/.test(entry.problem_number))) {
    const id = String(Number(entry.problem_number.slice(3)));
    assert.ok(Object.hasOwn(erdosData, id), `Missing main Erdős page for ${entry.id} (${entry.problem_number})`);
}

// A partial Lean formalization is an unresolved claim, and its external code
// link is displayed as a link rather than embedded or executed.
const leanAttempt = { model: 'Lean contributor', status: 'partial',
    file_path: 'attacks/open_problems/erdos/Lean_contributor/1.tex',
    raw: String.raw`\section{Lean formalization}This proves a special case only.
\href{https://github.com/example/proofs/blob/0123456789abcdef/Main.lean}{Lean source}
\url{https://live.lean-lang.org/#codez=ExamplePayload}` };
page = await render('?type=erdos&id=1', records, undefined,
    { '1': { ...erdosRecords['1'], llm_status: null, attacks: [leanAttempt] } });
assert.match(page.element('problem-meta').innerHTML, /LLM Claim:<\/strong> unresolved/);
assert.match(page.element('attempts-container').innerHTML, /class="status-text">unresolved</);
assert.match(page.element('attempts-container').innerHTML,
    /href="https:\/\/github.com\/example\/proofs\/blob\/0123456789abcdef\/Main\.lean" target="_blank" rel="noopener noreferrer">Lean source<\/a>/);
assert.match(page.element('attempts-container').innerHTML, /href="https:\/\/live\.lean-lang\.org\/#codez=ExamplePayload"/);
assert.doesNotMatch(page.element('attempts-container').innerHTML, /<iframe|<script|class="status-text">solved/);
assert.equal(page.element('contribute-cta').hidden, false);
assert.equal(page.requests.length, 0);

// Invitations follow the problem's status even when the LLM claim disagrees.
for (const status of ['open', 'open (Lean)', 'proved', 'disproved', 'independent', null]) {
    const isOpen = status === 'open' || status === 'open (Lean)';
    const erdos = { '1': { ...erdosRecords['1'], status, llm_status: isOpen ? 'solved' : 'unresolved' } };
    page = await render('?type=erdos&id=1', records, undefined, erdos);
    assert.equal(page.element('contribute-cta').hidden, !isOpen, `Erdos status: ${status}`);
}
for (const status of ['open', 'open_with_solved_subcases', 'open_disputed_claim', 'solved', 'unreviewed', 'reviewed_hold', null]) {
    const isOpen = ['open', 'open_with_solved_subcases', 'open_disputed_claim'].includes(status);
    const problem = { ...records['20000601'], status, llm_status: isOpen ? 'solved' : 'unresolved' };
    page = await render('?type=open_problems&id=20000601', { [problem.id]: problem });
    assert.equal(page.element('contribute-cta').hidden, !isOpen, `Ranked status: ${status}`);
}
// A current detail record can resolve a problem still marked open in a cached index.
page = await render('?type=open_problems&id=20000601', records,
    async () => ({ ok: true, json: async () => ({ ...records['20000601'], status: 'solved' }) }));
assert.equal(page.element('contribute-cta').hidden, true);
page = await render('?type=mo&id=42');
assert.equal(page.element('contribute-cta').hidden, true);

for (const id of ['problem.missing', '__proto__', 'constructor']) {
    page = await render(`?type=open_problems&id=${id}`);
    assert.match(page.element('problem-meta').innerHTML, /Problem not found/);
    assert.equal(page.element('contribute-cta').hidden, true);
}
assert.match((await render('?type=open_problems&id=20000601', null)).element('problem-meta').innerHTML, /Error loading Top Open Problems data/);
const unsafeSource = { ...records['20000601'], sources: [
    { citation: '<img src=x onerror=alert(1)>', url: 'javascript:alert(1)' },
    { citation: 'Quoted URL', url: 'https://example.org/" onmouseover="alert(1)' }
], definition_tex: String.raw`\href{javascript:alert(1)}{<img src=x onerror=alert(1)>}
\url{https://example.org/" onmouseover="alert(1)}` };
page = await render('?type=open_problems&id=20000601', { '20000601': unsafeSource });
assert.doesNotMatch(page.element('problem-links').innerHTML, /href="javascript:|<img| onmouseover="/);
assert.match(page.element('problem-links').innerHTML, /&quot;/);

const tateEntry = JSON.parse(fs.readFileSync(path.join(root, 'lists/unsolvedmath/problems.json'), 'utf8'))
    .find(record => /^Tate Conjecture for Algebraic Cycles$/i.test(record.title));
const tatePath = `attacks/open_problems/top_problems/definitions/${tateEntry.id}.tex`;
const tateSource = fs.readFileSync(path.join(root, tatePath), 'utf8');
const tate = JSON.parse(tateSource.match(/^% TOP_PROBLEM: (.+)$/m)[1]);
const tateProblem = { ...ranked(tate.id, 15),
    exact_target: 'This fallback must not be used.',
    definition_tex: tateSource.slice(tateSource.indexOf('\\subsection{Definitions')).replace(/\\end\{document\}\s*$/, ''),
    definition_file: tatePath };
page = await render(`?type=open_problems&id=${tate.id}`, { [tate.id]: tateProblem });
const statement = page.element('problem-links').innerHTML;
assert.match(statement, /class="problem-statement-text tex-content"/);
assert.match(statement, /\\operatorname\{CH\}/);
assert.match(statement, /\\mathbb\{Q\}\}_\\ell/);
assert.match(statement, /\\longrightarrow H\^\{2i\}/);
assert.ok(page.element('problem-statement-source').innerHTML.includes(tatePath));
assert.doesNotMatch(statement, /View TeX definition/);
assert.match(statement, /TateConjecture.html/);
assert.doesNotMatch(statement, /fallback must not|cataloguescope|X_bar|H\^\(2i\)|Q_l/);
assert.doesNotMatch(page.element('problem-meta').innerHTML, /Problem ID:|Catalog status:|Rank:/);

const missingDefinition = { ...records['20000601'], definition_tex: null, definition_file: null,
    exact_target: 'Stale catalogue statement must not be displayed.' };
page = await render('?type=open_problems&id=20000601', { '20000601': missingDefinition });
assert.match(page.element('problem-links').innerHTML, /TeX definition could not be loaded/);
assert.match(page.element('problem-statement-source').innerHTML, /top_problems\/definitions\/20000601\.tex/);
assert.doesNotMatch(page.element('problem-links').innerHTML, /Stale catalogue/);

// A cached index can lack definitions or retain an older attempt list. The
// current detail record must replace both together without using catalog prose.
const freshRecord = { ...records['20000601'], title: 'Fresh title',
    definition_tex: String.raw`\subsection{Definitions and mathematical statement}
Fresh definition with $x^2$ and \textbf{proper formatting}.`,
    llm_status: 'unresolved',
    attacks: [{ model: 'gpt_6_astra_ultra', status: 'unresolved',
        file_path: 'attacks/open_problems/top_problems/gpt_6_astra_ultra/1.tex',
        raw: String.raw`\section{Fresh attempt}\[x^2=1\]Still unresolved.` }]
};
page = await render('?type=open_problems&id=20000601', { '20000601': missingDefinition },
    async () => ({ ok: true, json: async () => freshRecord }));
assert.equal(page.element('page-title').textContent, 'Fresh title');
assert.match(page.element('problem-links').innerHTML, /Fresh definition with \$x\^2\$/);
assert.match(page.element('problem-links').innerHTML, /<strong>proper formatting<\/strong>/);
assert.doesNotMatch(page.element('problem-links').innerHTML, /could not be loaded|Stale catalogue/);
assert.match(page.element('attempts-container').innerHTML, /gpt 6 astra ultra/);
assert.match(page.element('attempts-container').innerHTML, /Fresh attempt/);
assert.match(page.element('attempts-container').innerHTML, /top_problems\/gpt_6_astra_ultra\/1\.tex/);
assert.match(page.element('problem-meta').innerHTML, /unresolved/);
assert.equal(page.element('next-problem').style.visibility, 'hidden');

// Changing display position must not invalidate a freshly fetched canonical record.
page = await render('?type=open_problems&id=20000601', records,
    async () => ({ ok: true, json: async () => ({ ...freshRecord, rank: 20 }) }));
assert.equal(page.element('page-title').textContent, 'Fresh title');
assert.equal(page.requests[0].url, 'data/top_problems/20000601.json');

// Offline access, a non-JSON response, or a detail record for another ID
// must preserve a complete embedded record instead of losing its definition.
const failedResponses = [
    async () => { throw new Error('Network unavailable'); },
    async () => ({ ok: false, status: 503 }),
    async () => ({ ok: true, json: async () => { throw new SyntaxError('Not JSON'); } }),
    ...[null, { ...freshRecord, id: '6' },
        { ...freshRecord, definition_tex: '  ' },
        { ...freshRecord, definition_tex: {} }, { ...freshRecord, attacks: null }]
        .map(value => async () => ({ ok: true, json: async () => value }))
];
for (const fetchRecord of failedResponses) {
    page = await render('?type=open_problems&id=20000601', records, fetchRecord);
    assert.equal(page.element('page-title').textContent, 'Title 1');
    assert.match(page.element('problem-links').innerHTML, /For every \$n &lt; 10\$/);
    assert.doesNotMatch(page.element('problem-links').innerHTML, /could not be loaded|Fresh definition/);
    assert.match(page.element('attempts-container').innerHTML, /No LLM attempts yet/);
}

// Exercise the actual source-to-page pipeline for an imported model attempt.
const pnp = JSON.parse(execFileSync('python3', ['-B', '-c',
    "import json, build_site; print(json.dumps(build_site.build_open_problems_data({}, build_site.load_open_problems_catalog())['1']))"
], { cwd: root, encoding: 'utf8' }));
page = await render('?type=open_problems&id=1', { [pnp.id]: pnp });
const pnpStatement = page.element('problem-links').innerHTML;
assert.match(pnpStatement, /A language is a set/);
assert.match(pnpStatement, /\\exists y\\in/);
assert.match(page.element('problem-statement-source').innerHTML, /View TeX definition \(1\.tex\)/);
assert.doesNotMatch(pnpStatement, /View TeX definition/);
assert.match(pnpStatement, /claymath\.org\/library\/monographs\/MPPc\.pdf/);
assert.doesNotMatch(pnpStatement, /cataloguescope|hypertarget|\\[se]ref|Research attempt|When a yes-or-no problem/);
const notebook = page.element('attempts-container').innerHTML;
assert.match(notebook, /Attempt [0-9]+: gpt 6 astra ultra/);
assert.match(notebook, /top_problems\/gpt_6_astra_ultra\/1\.tex/);
assert.equal((notebook.match(/class="attempt"/g) || []).length, pnp.attacks.length);
assert.match(notebook, /Current frontier and source audit/);
assert.match(notebook, /unresolved gap/);
assert.doesNotMatch(notebook, /No LLM attempts yet|Research notebook|\\[se]ref|hypertarget/);

// Previously published name-based URLs load the same statement and attempts,
// then replace the address with the permanent numeric ID, retaining fragments.
const hodge = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/top_problems/6.json'), 'utf8'));
for (const [legacy, record] of [['problem.p-versus-np', pnp], ['problem.hodge-conjecture', hodge]]) {
    page = await render(`?type=open_problems&id=${legacy}&view=all#llm-attempts-section`, { [record.id]: record });
    assert.equal(page.element('page-title').textContent, record.title);
    assert.equal(page.requests[0].url, `data/top_problems/${record.id}.json`);
    assert.equal(page.context.window.history.lastURL.searchParams.get('id'), String(record.id));
    assert.equal(page.context.window.history.lastURL.searchParams.get('view'), 'all');
    assert.equal(page.context.window.history.lastURL.hash, '#llm-attempts-section');
    assert.equal(page.element('.giscus').children[0].dataset.term, `OpenProblem-${record.id}`);
    assert.doesNotMatch(page.element('problem-statement-source').innerHTML, /unsolvedmath\.com|UnsolvedMath/);
    assert.ok(page.element('problem-statement-source').innerHTML.includes(`/top_problems/definitions/${record.id}.tex`));
    assert.equal((page.element('attempts-container').innerHTML.match(/class="attempt"/g) || []).length, record.attacks.length);
    assert.equal(new URL(page.context.getReviewIssueUrl('open_problems', String(record.id))).searchParams.get('problem_id'), String(record.id));
}
console.log('Ranked TeX definitions, fresh data recovery, model attempts, citations and legacy detail routes passed.');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
