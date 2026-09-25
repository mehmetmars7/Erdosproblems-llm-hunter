// Run with: node tests/test_open_problems_frontend.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');

function createBrowser(search = '', subset = false) {
    const ids = ['open-problems-tbody', 'results-count', 'search', 'filter-domain', 'filter-source',
        'filter-attacks', 'sort-by', 'catalogue-edition', 'reset-filters'];
    const elements = Object.fromEntries(ids.map(id => [id, {
        innerHTML: '', textContent: '', value: '', checked: false, handlers: {},
        addEventListener(type, handler) { this.handlers[type] = handler; }
    }]));
    const location = new URL(`https://example.org/${subset ? 'mo' : 'open_problems'}.html${search}`);
    const document = {
        body: { dataset: { collection: subset ? 'mo' : 'all' } },
        addEventListener() {},
        getElementById(id) { return elements[id] || null; }
    };
    const window = {
        location,
        history: { replaceState(state, title, url) { this.lastURL = url; } }
    };
    const context = vm.createContext({ window, document, URL, URLSearchParams, setTimeout, clearTimeout });
    vm.runInContext(fs.readFileSync(path.join(root, 'docs/app.js'), 'utf8'), context);
    return { api: window.ProblemHunting, window, elements, context };
}

const browser = createBrowser();
const { api } = browser;
const attempt = { model: 'GPT 6 Astra Ultra', status: 'unresolved' };
const statement = { ...attempt, entry_kind: 'statement_only' };
const records = {
    'problem.beta': { id: 'problem.beta', title: 'Beta & "target"', collection: 'ranked', rank: 2,
        domain: 'algebra', domain_label: 'Algebra', exact_target: 'A special target about groups',
        status: 'open_with_solved_subcases', status_qualification: 'See "partial" result <not a resolution>.',
        status_reviewed_at: '2026-09-14', llm_status: 'solved', completion: 100,
        sources: [{ citation: 'Source & "description"', url: 'https://example.org/?a=1&b=2' }],
        attacks: [{ ...attempt, status: 'solved' }] },
    'mo:23': { id: 'mo:23', mo_id: '23', title: 'MO question', collection: 'mo', rank: null, score: 23,
        domain: 'geometry', domain_label: 'Geometry', status: 'unreviewed', llm_status: 'unresolved',
        attacks: [attempt], sources: [{ citation: 'Question', url: 'https://mathoverflow.net/questions/23' }] },
    'problem.alpha': { id: 'problem.alpha', title: 'Alpha', collection: 'ranked', rank: 1,
        domain: 'number_theory', domain_label: 'Number theory', exact_target: 'A target involving primes',
        aliases: ['Prime problem'], status: 'open', llm_status: 'none', attacks: [statement] },
    'mo:40': { id: 'mo:40', title: 'Older MO question', collection: 'mo', rank: null, score: 40,
        status: 'unreviewed', llm_status: 'none', attacks: [] }
};
const ids = rows => Array.from(rows, row => row.id);
assert.deepEqual(ids(Object.values(records).sort(api.sortOpenProblems)), ['problem.alpha', 'problem.beta', 'mo:40', 'mo:23']);
assert.deepEqual(ids(api.filterOpenProblems(records, { withAttempts: true })), ['problem.beta', 'mo:23']);
assert.deepEqual(ids(api.filterOpenProblems(records, { source: 'ranked', withAttempts: true })), ['problem.beta']);
assert.deepEqual(ids(api.filterOpenProblems(records, { domain: 'geometry', source: 'mo' })), ['mo:23']);
assert.deepEqual(ids(api.filterOpenProblems(records, { search: '  PRIME PROBLEM ' })), ['problem.alpha']);
assert.deepEqual(ids(api.filterOpenProblems(records, { search: 'special target' })), ['problem.beta']);
assert.deepEqual(ids(api.filterOpenProblems(records, { search: 'example.org' })), ['problem.beta']);
assert.deepEqual(ids(api.filterOpenProblems(records, { search: 'missing target' })), []);
// Distinct source domain identifiers can name the same display category.
const aliasRecords = [
    { id: 'a', domain: 'geometry_topology', domain_label: 'Geometry & topology' },
    { id: 'b', domain: 'geometry_and_topology', domain_label: 'Geometry & topology' },
    { id: 'c', domain: 'geometry_topology', domain_label: 'Geometry & topology' },
    { id: 'd', domain: 'algebra', domain_label: 'Algebra' }
];
const groups = Array.from(api.getOpenProblemDomains(aliasRecords));
assert.equal(groups.length, 2);
assert.equal(groups[1].value, 'geometry_topology');
assert.deepEqual(ids(api.filterOpenProblems(aliasRecords, { domain: 'geometry_topology' })), ['a', 'b', 'c']);
assert.deepEqual(ids(api.filterOpenProblems(aliasRecords, { domain: 'geometry_and_topology' })), ['a', 'b', 'c']);
assert.equal(aliasRecords[1].domain, 'geometry_and_topology');
const aliasPage = createBrowser('?domain=geometry_and_topology');
aliasPage.window.OPEN_PROBLEMS_DATA = aliasRecords;
aliasPage.api.initOpenProblemsPage();
assert.equal(aliasPage.elements['filter-domain'].value, 'geometry_topology');
assert.equal((aliasPage.elements['filter-domain'].innerHTML.match(/Geometry &amp; topology/g) || []).length, 1);
assert.match(aliasPage.elements['results-count'].textContent, /^3 of 4 entries/);
assert.equal(api.countWithAttacks(records), 2);
assert.equal(api.getOpenProblemClaim(records['problem.alpha']), 'no attempt');
assert.equal(api.getOpenProblemClaim(records['problem.beta']), 'solved');
assert.equal(api.getOpenProblemStatusLabel(records['problem.beta']), 'open with solved subcases');
assert.equal(api.getOpenProblemClaim({ status: 'solved', attacks: [attempt] }), 'unresolved');
assert.equal(api.getOpenProblemClaim({ attacks: [{ model: 'unknown' }] }), 'not stated');
assert.equal(api.getOpenProblemHref(records['mo:23']), 'problem.html?type=mo&id=23');
assert.equal(api.getOpenProblemHref(records['mo:40']), 'problem.html?type=mo&id=40');
assert.equal(api.getOpenProblemHref(records['problem.alpha']), 'problem.html?type=open_problems&id=problem.alpha');
assert.equal(api.getOpenProblemHref({ id: 'problem.a&b#c' }), 'problem.html?type=open_problems&id=problem.a%26b%23c');
assert.equal(api.escapeHtml(null), '');
assert.equal(api.escapeHtml('a"<&\''), 'a&quot;&lt;&amp;&#39;');
const rendered = api.renderOpenProblemRows([records['problem.beta'], records['mo:23'], records['problem.alpha']]);
assert.match(rendered, /Beta &amp; &quot;target&quot;/);
assert.match(rendered, /title="See &quot;partial&quot; result &lt;not a resolution&gt;\."/);
assert.match(rendered, /open with solved subcases/);
assert.match(rendered, /class="claim-status">solved/);
assert.match(rendered, /Reviewed 2026-09-14/);
assert.match(rendered, /<td>—<\/td>/);
assert.match(rendered, /no attempt/);
assert.match(rendered, /gpt 6/);
assert.doesNotMatch(rendered, /<not a resolution>/);
const unsafe = api.renderOpenProblemRows([{ id: 'problem.x', title: '<script>alert(1)</script>', attacks: [],
    sources: [{ url: 'javascript:alert(1)', citation: 'bad' }] }]);
assert.doesNotMatch(unsafe, /href="javascript:|<script>/);
assert.match(unsafe, /&lt;script&gt;/);
assert.match(api.renderOpenProblemRows([]), /No problems match/);
const reused = { ...attempt, entry_kind: 'reused_writeup', provenance: { source_model: 'gpt_pro_5.2' } };
assert.match(api.renderOpenProblemRows([{ id: 'problem.reuse', attacks: [reused] }]), /gpt 6 \(collection\), gpt pro/);

const erdos = { 1: { number: '1', attacks: [statement] }, 2: { number: '2', attacks: [attempt] },
    3: { number: '3', attacks: [attempt] } };
const preview = api.getAttemptPreview(erdos, records);
assert.equal(preview.length, 4);
assert.equal(new Set(preview.map(row => row.href)).size, 4);
assert.equal(preview.filter(row => row.href.includes('type=mo')).length, 1);
assert.ok(preview.some(row => row.label.startsWith('MathOverflow:')));
assert.ok(preview.some(row => row.label.startsWith('Top Open Problem #2:')));
assert.ok(preview.every(row => !row.label.includes('#null')));
assert.equal(api.getAttemptPreview(erdos, records, 2).length, 2);

// Exercise the page initializer and interactions without a browser dependency.
function loadPage(page) {
    page.window.OPEN_PROBLEMS_DATA = records;
    page.window.OPEN_PROBLEMS_CATALOG = { edition_date: '2026-09-22', release_version: 22 };
    page.api.initOpenProblemsPage();
    return page;
}
loadPage(browser);
assert.match(browser.elements['results-count'].textContent, /^4 of 4 entries · 2 with LLM attempts$/);
assert.equal(browser.elements['sort-by'].value, 'rank');
assert.equal(browser.elements['filter-attacks'].checked, false);
assert.equal(browser.elements['catalogue-edition'].textContent, '');
assert.ok(browser.elements['open-problems-tbody'].innerHTML.indexOf('>Alpha<') < browser.elements['open-problems-tbody'].innerHTML.indexOf('>Beta'));
browser.elements['filter-attacks'].checked = true;
browser.elements['filter-attacks'].handlers.change();
assert.match(browser.elements['results-count'].textContent, /^2 of 4/);
assert.equal(browser.window.history.lastURL.searchParams.get('attempts'), '1');
browser.elements['filter-source'].value = 'ranked';
browser.elements['filter-source'].handlers.change();
assert.match(browser.elements['results-count'].textContent, /^1 of 4/);
browser.elements['reset-filters'].handlers.click();
assert.match(browser.elements['results-count'].textContent, /^4 of 4/);
assert.equal(browser.window.history.lastURL.search, '');

const query = loadPage(createBrowser('?source=mo&attempts=1&q=question&sort=title'));
assert.match(query.elements['results-count'].textContent, /^1 of 4/);
assert.equal(query.elements.search.value, 'question');
assert.equal(query.elements['sort-by'].value, 'title');
const subset = loadPage(createBrowser('?source=ranked', true));
assert.equal(subset.elements['filter-source'].value, 'mo');
assert.equal(subset.elements['sort-by'].value, 'score');
assert.match(subset.elements['results-count'].textContent, /^2 of 2/);
assert.doesNotMatch(subset.elements['open-problems-tbody'].innerHTML, /problem\.alpha|problem\.beta/);
const unavailable = createBrowser();
unavailable.api.initOpenProblemsPage();
assert.equal(unavailable.elements['results-count'].textContent, 'Catalogue unavailable');

for (const filename of ['index.html', 'open_problems.html', 'mo.html', 'erdos.html']) {
    const html = fs.readFileSync(path.join(root, 'docs', filename), 'utf8');
    assert.match(html, /href="open_problems.html"[^>]*>Top Open Problems<\/a>/);
    for (const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) new vm.Script(match[1]);
    if (filename !== 'erdos.html') {
        assert.match(html, /src="data\/open_problems_data\.js(?:\?v=[0-9a-f]{16})?"/);
        assert.doesNotMatch(html, /src="data\/mo_data.js"/);
    }
}
const home = fs.readFileSync(path.join(root, 'docs/index.html'), 'utf8');
assert.match(home, /<h3>Top Open Problems<\/h3>/);
assert.match(home, /entries tracked/);
assert.doesNotMatch(home, /MathOverflow Problems<\/h3>/);
console.log('Open-problem ranking, filtering, statuses, escaping, attribution, previews, page interactions and navigation passed.');
