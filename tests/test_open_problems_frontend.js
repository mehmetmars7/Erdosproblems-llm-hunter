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
    const headers = Object.fromEntries(['rank', 'title', 'status', 'review', 'claim', 'completion', 'models', 'source', 'unsolvedmath'].map(key => {
        const header = { attributes: {}, setAttribute(name, value) { this.attributes[name] = value; } };
        const indicator = { textContent: '' };
        return [key, { dataset: { sort: key }, handlers: {}, header, indicator,
            addEventListener(type, handler) { this.handlers[type] = handler; },
            closest() { return header; }, querySelector() { return indicator; } }];
    }));
    const document = {
        body: { dataset: { collection: subset ? 'mo' : 'all' } },
        addEventListener() {},
        querySelectorAll() { return Object.values(headers); },
        getElementById(id) { return elements[id] || null; }
    };
    const window = {
        location,
        history: { replaceState(state, title, url) { this.lastURL = url; } }
    };
    const context = vm.createContext({ window, document, URL, URLSearchParams, setTimeout, clearTimeout });
    vm.runInContext(fs.readFileSync(path.join(root, 'docs/app.js'), 'utf8'), context);
    return { api: window.ProblemHunting, window, elements, headers, context };
}

const browser = createBrowser();
const { api } = browser;
const attempt = { model: 'GPT 6 Astra Ultra', status: 'unresolved' };
const statement = { ...attempt, entry_kind: 'statement_only' };
const records = {
    '6': { id: 6, title: 'Beta & "target"', collection: 'ranked', rank: 2,
        domain: 'algebra', domain_label: 'Algebra', exact_target: 'A special target about groups',
        status: 'open_with_solved_subcases', status_qualification: 'See "partial" result <not a resolution>.',
        status_reviewed_at: '2026-09-14', llm_status: 'solved', completion: 100,
        problem_number: 'MPP-006', external_url: 'https://www.unsolvedmath.com/problems/MPP-006',
        sources: [{ citation: 'Source & "description"', url: 'https://example.org/?a=1&b=2' }],
        attacks: [{ ...attempt, status: 'solved' }] },
    'mo:23': { id: 'mo:23', mo_id: '23', title: 'MO question', collection: 'mo', rank: null, score: 23,
        domain: 'geometry', domain_label: 'Geometry', status: 'unreviewed', llm_status: 'unresolved',
        attacks: [attempt], sources: [{ citation: 'Question', url: 'https://mathoverflow.net/questions/23' }] },
    '20000601': { id: 20000601, title: 'Alpha', collection: 'ranked', rank: 1,
        domain: 'number_theory', domain_label: 'Number theory', exact_target: 'A target involving primes',
        aliases: ['Prime problem'], status: 'open', llm_status: 'none', attacks: [statement] },
    'mo:40': { id: 'mo:40', title: 'Older MO question', collection: 'mo', rank: null, score: 40,
        status: 'unreviewed', llm_status: 'none', attacks: [] }
};
const ids = rows => Array.from(rows, row => String(row.id));
assert.deepEqual(ids(Object.values(records).sort(api.sortOpenProblems)), ['20000601', '6', 'mo:40', 'mo:23']);
assert.deepEqual(ids(api.filterOpenProblems(records, { withAttempts: true })), ['6', 'mo:23']);
assert.deepEqual(ids(api.filterOpenProblems(records, { source: 'ranked', withAttempts: true })), ['6']);
assert.deepEqual(ids(api.filterOpenProblems(records, { domain: 'geometry', source: 'mo' })), ['mo:23']);
assert.deepEqual(ids(api.filterOpenProblems(records, { search: '  PRIME PROBLEM ' })), ['20000601']);
assert.deepEqual(ids(api.filterOpenProblems(records, { search: 'special target' })), ['6']);
assert.deepEqual(ids(api.filterOpenProblems(records, { search: 'example.org' })), ['6']);
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
assert.equal(api.getOpenProblemClaim(records['20000601']), 'no attempt');
assert.equal(api.getOpenProblemClaim(records['6']), 'solved');
assert.equal(api.getOpenProblemStatusLabel(records['6']), 'open with solved subcases');
assert.equal(api.getOpenProblemClaim({ status: 'solved', attacks: [attempt] }), 'unresolved');
assert.equal(api.getOpenProblemClaim({ attacks: [{ model: 'unknown' }] }), 'not stated');
assert.equal(api.getOpenProblemClaim({ attacks: [{ status: 'partial' }] }), 'unresolved');
assert.equal(api.getOpenProblemClaim({ attacks: [{ status: 'solved' }, { status: 'partial' }] }), 'unresolved');
assert.equal(api.getAttemptClaim({ status: ' PARTIAL ', raw: 'A formalized special case.' }), 'unresolved');
assert.equal(api.getAttemptClaim({ raw: 'FINAL: PARTIAL.' }), 'unresolved');
assert.equal(api.getOverallClaim([{ entry_kind: 'statement_only', status: 'solved' }]), 'none');
assert.equal(api.getOverallClaim([{ status: 'solved' }, { model: 'unknown' }]), 'not stated');
assert.equal(api.getOpenProblemHref(records['mo:23']), 'problem.html?type=mo&id=23');
assert.equal(api.getOpenProblemHref(records['mo:40']), 'problem.html?type=mo&id=40');
assert.equal(api.getOpenProblemHref(records['20000601']), 'problem.html?type=open_problems&id=20000601');
assert.equal(api.getOpenProblemHref({ id: 'problem.a&b#c' }), 'problem.html?type=open_problems&id=problem.a%26b%23c');
assert.equal(api.escapeHtml(null), '');
assert.equal(api.escapeHtml('a"<&\''), 'a&quot;&lt;&amp;&#39;');
const rendered = api.renderOpenProblemRows([records['6'], records['mo:23'], records['20000601']]);
assert.match(rendered, /Beta &amp; &quot;target&quot;/);
assert.match(rendered, /href="https:\/\/www\.unsolvedmath\.com\/problems\/MPP-006" target="_blank" rel="noopener noreferrer"[^>]*>MPP-006<\/a>/);
assert.match(rendered, /<td>2<\/td>/);
assert.match(rendered, />Source<\/a><\/td>\s*<td><a[^>]*>MPP-006<\/a><\/td>/);
assert.deepEqual(ids(api.filterOpenProblems(records, { search: 'mpp-006' })), ['6']);
const duplicateCode = { id: 1479, problem_number: 'TOP-001', external_url: 'https://www.unsolvedmath.com/problems/1479' };
assert.match(api.getUnsolvedMathLink(duplicateCode), /problems\/1479"[^>]*>TOP-001<\/a>/);
assert.equal(api.getUnsolvedMathLink({ ...duplicateCode, external_url: 'https://www.unsolvedmath.com/problems/18' }), '');
assert.equal(api.getUnsolvedMathLink({ ...duplicateCode, external_url: 'javascript:alert(1)' }), '');
assert.equal(api.getUnsolvedMathLink({ id: 30006988, problem_number: 'LOCAL-30006988', external_url: null }), '');
const registry = JSON.parse(fs.readFileSync(path.join(root, 'lists/unsolvedmath/problems.json'), 'utf8'));
const canonicalRecords = Object.fromEntries(registry.map(record => [record.id, record]));
assert.equal(registry.flatMap(record => record.legacy_ids).length, 500);
for (const record of registry) {
    assert.equal(api.getOpenProblemHref(record), `problem.html?type=open_problems&id=${record.id}`);
    for (const legacy of record.legacy_ids) {
        assert.equal(api.resolveOpenProblemId(canonicalRecords, legacy), String(record.id));
    }
}
assert.match(fs.readFileSync(path.join(root, 'docs/open_problems.html'), 'utf8'), /data-sort="unsolvedmath">UnsolvedMath #/);
assert.doesNotMatch(rendered, /<td>20000601<\/td>/);
assert.deepEqual(ids(api.filterOpenProblems(records, { search: '20000601' })), ['20000601']);
assert.match(rendered, /title="See &quot;partial&quot; result &lt;not a resolution&gt;\."/);
assert.match(rendered, /open with solved subcases/);
assert.match(rendered, /class="claim-status"><a href="problem\.html\?type=open_problems&amp;id=6">solved<\/a>/);
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
assert.ok(preview.some(row => row.label.startsWith('Top Open Problem:')));
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

// Column buttons toggle direction, update the dropdown/URL and preserve filters.
const sorted = loadPage(createBrowser());
const rowIds = page => [...page.elements['open-problems-tbody'].innerHTML.matchAll(/class="catalogue-problem"><a href="[^"]*id=([^"]+)"/g)].map(m => m[1]);
assert.equal(sorted.headers.rank.header.attributes['aria-sort'], 'ascending');
sorted.headers.title.handlers.click();
assert.equal(sorted.elements['sort-by'].value, 'title');
assert.deepEqual(rowIds(sorted), ['20000601', '6', '23', '40']);
assert.equal(sorted.headers.title.indicator.textContent, '↑');
sorted.headers.title.handlers.click();
assert.deepEqual(rowIds(sorted), ['40', '23', '6', '20000601']);
assert.equal(sorted.headers.title.header.attributes['aria-sort'], 'descending');
assert.equal(sorted.headers.rank.header.attributes['aria-sort'], 'none');
assert.equal(sorted.window.history.lastURL.searchParams.get('dir'), 'desc');
sorted.elements['filter-source'].value = 'ranked';
sorted.elements['filter-source'].handlers.change();
assert.deepEqual(rowIds(sorted), ['6', '20000601']);
assert.equal(sorted.headers.title.indicator.textContent, '↓');
sorted.elements['sort-by'].value = 'completion';
sorted.elements['sort-by'].handlers.change();
assert.equal(sorted.headers.completion.header.attributes['aria-sort'], 'descending');
assert.deepEqual(rowIds(sorted), ['6', '20000601']);
sorted.headers.completion.handlers.click();
assert.deepEqual(rowIds(sorted), ['6', '20000601']); // missing completion stays last
sorted.elements['reset-filters'].handlers.click();
assert.equal(sorted.headers.rank.header.attributes['aria-sort'], 'ascending');
assert.equal(sorted.window.history.lastURL.search, '');
const restored = loadPage(createBrowser('?sort=title&dir=desc&source=ranked'));
assert.deepEqual(rowIds(restored), ['6', '20000601']);
assert.equal(restored.headers.title.header.attributes['aria-sort'], 'descending');
for (const [key, low, high] of [
    ['rank', { rank: 2 }, { rank: 10 }],
    ['status', { status: 'open' }, { status: 'solved' }],
    ['claim', { attacks: [attempt], llm_status: 'solved' }, { attacks: [attempt], llm_status: 'unresolved' }],
    ['completion', { attacks: [attempt], completion: 9 }, { attacks: [attempt], completion: 100 }],
    ['models', { attacks: [{ model: 'Alpha' }] }, { attacks: [{ model: 'Beta' }] }],
    ['source', { sources: [{ url: 'https://a.org' }] }, { sources: [{ url: 'https://b.org' }] }],
    ['unsolvedmath', { external_url: 'https://example.org', problem_number: 'EP-2' }, { external_url: 'https://example.org', problem_number: 'EP-10' }]
]) {
    assert.ok(api.compareOpenProblems(low, high, key, 'asc') < 0, key);
    assert.ok(api.compareOpenProblems(low, high, key, 'desc') > 0, key);
}
for (const page of ['open_problems.html', 'mo.html']) {
    const html = fs.readFileSync(path.join(root, 'docs', page), 'utf8');
    assert.equal((html.match(/<button type="button" class="column-sort" data-sort=/g) || []).length, 9);
}

const query = loadPage(createBrowser('?source=mo&attempts=1&q=question&sort=title'));
assert.match(query.elements['results-count'].textContent, /^1 of 4/);
assert.equal(query.elements.search.value, 'question');
assert.equal(query.elements['sort-by'].value, 'title');
const subset = loadPage(createBrowser('?source=ranked', true));
assert.equal(subset.elements['filter-source'].value, 'mo');
assert.equal(subset.elements['sort-by'].value, 'score');
assert.match(subset.elements['results-count'].textContent, /^2 of 2/);
assert.doesNotMatch(subset.elements['open-problems-tbody'].innerHTML, /id=20000601|id=6/);
const unavailable = createBrowser();
unavailable.api.initOpenProblemsPage();
assert.equal(unavailable.elements['results-count'].textContent, 'Catalogue unavailable');

for (const filename of ['index.html', 'open_problems.html', 'mo.html', 'erdos.html']) {
    const html = fs.readFileSync(path.join(root, 'docs', filename), 'utf8');
    assert.match(html, /href="open_problems.html"[^>]*>Top Open Problems<\/a>/);
    for (const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) new vm.Script(match[1]);
    const config = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)]
        .map(match => match[1]).find(script => script.includes('window.MathJax ='));
    const mathContext = vm.createContext({ window: {} });
    vm.runInContext(config, mathContext);
    assert.ok(mathContext.window.MathJax.loader.load.includes('ui/safe'), filename);
    assert.equal(mathContext.window.MathJax.options.safeOptions.allow.URLs, 'none', filename);
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
