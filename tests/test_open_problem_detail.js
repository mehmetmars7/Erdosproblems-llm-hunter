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
    definition_file: `attacks/open_problems/top_problems/${rank}.tex`,
    status_qualification: 'Bounded review; still open.', status_reviewed_at: '2026-09-22',
    sources: [{ citation: 'Definition <source>', url: 'https://example.org/?x=1&y=2', role: 'formal_statement' }],
    attacks: []
});
const records = {
    'problem.z-first': ranked('problem.z-first', 1),
    'problem.a-second': ranked('problem.a-second', 2),
    'mo:42': { id: 'mo:42', collection: 'mo', rank: null }
};

async function render(query, open = records, fetchRecord = async () => ({ ok: false, status: 404 })) {
    const elements = new Map();
    function element(id) {
        if (!elements.has(id)) elements.set(id, {
            innerHTML: '', textContent: '', style: {}, hidden: false, children: [],
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
        document, URLSearchParams, console,
        fetch: async (url, options) => {
            requests.push({ url, options });
            return fetchRecord(url, options);
        },
        window: { location: { search: query }, OPEN_PROBLEMS_DATA: open,
            OPEN_PROBLEMS_CATALOG: { edition_date: '2026-09-22' } },
        moProblems: { '42': { id: '42', title: 'Legacy question', score: 5, link: 'https://mathoverflow.net/questions/42', attacks: [] } },
        erdosProblems: { '1': { number: '1', status: 'open', llm_status: 'unresolved', problem_url: 'https://www.erdosproblems.com/1', attacks: [] } }
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
let page = await render('?type=open_problems&id=problem.z-first');
assert.equal(page.element('page-title').textContent, 'Title 1');
assert.match(page.element('problem-meta').innerHTML, /Problem Status:/);
assert.doesNotMatch(page.element('problem-meta').innerHTML, /Problem ID:|Catalog status:|Rank:/);
assert.match(page.element('problem-meta').innerHTML, /No attempts yet/);
assert.match(page.element('problem-links').innerHTML, /\$n &lt; 10\$/);
assert.match(page.element('problem-links').innerHTML, /Definition &lt;source&gt;/);
assert.doesNotMatch(page.element('problem-links').innerHTML, /Catalog edition:|2026-09-22/);
assert.match(page.element('problem-links').innerHTML, /x=1&amp;y=2/);
assert.match(page.element('problem-links').innerHTML, /View TeX definition \(1\.tex\)/);
assert.equal(page.element('prev-problem').style.visibility, 'hidden');
assert.equal(page.element('next-problem').href, 'problem.html?type=open_problems&id=problem.a-second');
assert.match(page.element('attempts-container').innerHTML, /No LLM attempts yet/);
assert.notEqual(page.element('llm-attempts-section').style.display, 'none');
assert.equal(page.element('.giscus').children[0].dataset.term, 'OpenProblem-problem.z-first');
assert.equal(page.requests.length, 1);
assert.equal(page.requests[0].url, 'data/top_problems/1.json');
assert.equal(page.requests[0].options.cache, 'no-store');
const reviewURL = new URL(page.context.getReviewIssueUrl('open_problems', 'problem.z-first'));
assert.equal(reviewURL.searchParams.get('problem_type'), 'Open Problems');
assert.equal(reviewURL.searchParams.get('problem_id'), 'problem.z-first');

page = await render('?type=open_problems&id=problem.a-second');
assert.equal(page.element('prev-problem').href, 'problem.html?type=open_problems&id=problem.z-first');
assert.equal(page.element('next-problem').style.visibility, 'hidden');

page = await render('?type=open_problems&id=mo%3A42');
assert.match(page.element('problem-meta').innerHTML, /MathOverflow subset/);
assert.equal(page.element('.giscus').children[0].dataset.term, 'MO-42');
assert.equal(page.requests.length, 0);
page = await render('?type=erdos&id=1');
assert.equal(page.element('page-title').textContent, 'Erdos Problem #1');
assert.equal(page.element('.giscus').children[0].dataset.term, 'Erdos-1');
assert.equal(page.requests.length, 0);

for (const id of ['problem.missing', '__proto__', 'constructor']) {
    assert.match((await render(`?type=open_problems&id=${id}`)).element('problem-meta').innerHTML, /Problem not found/);
}
assert.match((await render('?type=open_problems&id=problem.z-first', null)).element('problem-meta').innerHTML, /Error loading Top Open Problems data/);
const unsafeSource = { ...records['problem.z-first'], sources: [
    { citation: '<img src=x onerror=alert(1)>', url: 'javascript:alert(1)' },
    { citation: 'Quoted URL', url: 'https://example.org/" onmouseover="alert(1)' }
], definition_tex: String.raw`\href{javascript:alert(1)}{<img src=x onerror=alert(1)>}
\url{https://example.org/" onmouseover="alert(1)}` };
page = await render('?type=open_problems&id=problem.z-first', { 'problem.z-first': unsafeSource });
assert.doesNotMatch(page.element('problem-links').innerHTML, /href="javascript:|<img| onmouseover="/);
assert.match(page.element('problem-links').innerHTML, /&quot;/);

const tateSource = fs.readFileSync(path.join(root, 'attacks/open_problems/top_problems/15.tex'), 'utf8');
const tate = JSON.parse(tateSource.match(/^% TOP_PROBLEM: (.+)$/m)[1]);
const tateProblem = { ...ranked(tate.problemId, tate.releaseRank),
    exact_target: 'This fallback must not be used.',
    definition_tex: tateSource.slice(tateSource.indexOf('\\subsection{Definitions')).replace(/\\end\{document\}\s*$/, ''),
    definition_file: 'attacks/open_problems/top_problems/15.tex' };
page = await render(`?type=open_problems&id=${tate.problemId}`, { [tate.problemId]: tateProblem });
const statement = page.element('problem-links').innerHTML;
assert.match(statement, /class="problem-statement-text tex-content"/);
assert.match(statement, /\\operatorname\{CH\}/);
assert.match(statement, /\\mathbb\{Q\}\}_\\ell/);
assert.match(statement, /\\longrightarrow H\^\{2i\}/);
assert.match(statement, /View TeX definition/);
assert.match(statement, /top_problems\/15\.tex/);
assert.match(statement, /TateConjecture.html/);
assert.doesNotMatch(statement, /fallback must not|cataloguescope|X_bar|H\^\(2i\)|Q_l/);
assert.doesNotMatch(page.element('problem-meta').innerHTML, /Problem ID:|Catalog status:|Rank:/);

const missingDefinition = { ...records['problem.z-first'], definition_tex: null, definition_file: null,
    exact_target: 'Stale ProofAtlas statement must not be displayed.' };
page = await render('?type=open_problems&id=problem.z-first', { 'problem.z-first': missingDefinition });
assert.match(page.element('problem-links').innerHTML, /TeX definition could not be loaded/);
assert.match(page.element('problem-links').innerHTML, /top_problems\/1\.tex/);
assert.doesNotMatch(page.element('problem-links').innerHTML, /Stale ProofAtlas/);

// A cached index can lack definitions or retain an older attempt list. The
// current detail record must replace both together without using catalog prose.
const freshRecord = { ...records['problem.z-first'], title: 'Fresh title',
    definition_tex: String.raw`\subsection{Definitions and mathematical statement}
Fresh definition with $x^2$ and \textbf{proper formatting}.`,
    llm_status: 'unresolved',
    attacks: [{ model: 'GPT_6_Astra_Ultra', status: 'unresolved',
        file_path: 'attacks/open_problems/top_problems/GPT_6_Astra_Ultra/1.tex',
        raw: String.raw`\section{Fresh attempt}\[x^2=1\]Still unresolved.` }]
};
page = await render('?type=open_problems&id=problem.z-first', { 'problem.z-first': missingDefinition },
    async () => ({ ok: true, json: async () => freshRecord }));
assert.equal(page.element('page-title').textContent, 'Fresh title');
assert.match(page.element('problem-links').innerHTML, /Fresh definition with \$x\^2\$/);
assert.match(page.element('problem-links').innerHTML, /<strong>proper formatting<\/strong>/);
assert.doesNotMatch(page.element('problem-links').innerHTML, /could not be loaded|Stale ProofAtlas/);
assert.match(page.element('attempts-container').innerHTML, /GPT 6 Astra Ultra/);
assert.match(page.element('attempts-container').innerHTML, /Fresh attempt/);
assert.match(page.element('attempts-container').innerHTML, /top_problems\/GPT_6_Astra_Ultra\/1\.tex/);
assert.match(page.element('problem-meta').innerHTML, /unresolved/);
assert.equal(page.element('next-problem').style.visibility, 'hidden');

// Offline access, a non-JSON response, or a detail record for another rank
// must preserve a complete embedded record instead of losing its definition.
const failedResponses = [
    async () => { throw new Error('Network unavailable'); },
    async () => ({ ok: false, status: 503 }),
    async () => ({ ok: true, json: async () => { throw new SyntaxError('Not JSON'); } }),
    ...[null, { ...freshRecord, id: 'problem.a-second' },
        { ...freshRecord, rank: 2 }, { ...freshRecord, definition_tex: '  ' },
        { ...freshRecord, definition_tex: {} }, { ...freshRecord, attacks: null }]
        .map(value => async () => ({ ok: true, json: async () => value }))
];
for (const fetchRecord of failedResponses) {
    page = await render('?type=open_problems&id=problem.z-first', records, fetchRecord);
    assert.equal(page.element('page-title').textContent, 'Title 1');
    assert.match(page.element('problem-links').innerHTML, /For every \$n &lt; 10\$/);
    assert.doesNotMatch(page.element('problem-links').innerHTML, /could not be loaded|Fresh definition/);
    assert.match(page.element('attempts-container').innerHTML, /No LLM attempts yet/);
}

// Exercise the actual source-to-page pipeline for an imported model attempt.
const pnp = JSON.parse(execFileSync('python3', ['-B', '-c',
    "import json, build_site; print(json.dumps(build_site.build_open_problems_data({}, build_site.load_open_problems_catalog())['problem.p-versus-np']))"
], { cwd: root, encoding: 'utf8' }));
page = await render('?type=open_problems&id=problem.p-versus-np', { [pnp.id]: pnp });
const pnpStatement = page.element('problem-links').innerHTML;
assert.match(pnpStatement, /A language is a set/);
assert.match(pnpStatement, /\\exists y\\in/);
assert.match(pnpStatement, /View TeX definition \(1\.tex\)/);
assert.match(pnpStatement, /claymath\.org\/library\/monographs\/MPPc\.pdf/);
assert.doesNotMatch(pnpStatement, /cataloguescope|hypertarget|\\[se]ref|Research attempt|When a yes-or-no problem/);
const notebook = page.element('attempts-container').innerHTML;
assert.match(notebook, /Attempt 1: GPT 6 Astra Ultra/);
assert.match(notebook, /top_problems\/GPT_6_Astra_Ultra\/1\.tex/);
assert.equal((notebook.match(/class="attempt"/g) || []).length, 1);
assert.match(notebook, /Current frontier and source audit/);
assert.match(notebook, /unresolved gap/);
assert.doesNotMatch(notebook, /No LLM attempts yet|Research notebook|\\[se]ref|hypertarget/);
console.log('Ranked TeX definitions, fresh data recovery, model attempts, citations and legacy detail routes passed.');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
