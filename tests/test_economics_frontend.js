// Run with node tests/test_economics_frontend.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const ids = ['economics-tbody', 'results-count', 'search', 'filter-jel-family', 'filter-jel',
    'sort-by', 'sort-direction', 'reset-filters'];
const elements = Object.fromEntries(ids.map(id => [id, {
    value: '', textContent: '', innerHTML: '', handlers: {},
    addEventListener(type, handler) { this.handlers[type] = handler; }
}]));
const headers = Object.fromEntries(['rank', 'title', 'status', 'completion', 'claim', 'review', 'jel_code', 'models'].map(key => {
    const header = { attributes: {}, setAttribute(name, value) { this.attributes[name] = value; } };
    const indicator = { textContent: '' };
    return [key, { dataset: { sort: key }, header, indicator, handlers: {},
        closest() { return header; }, querySelector() { return indicator; },
        addEventListener(type, handler) { this.handlers[type] = handler; }
    }];
}));
const document = {
    addEventListener() {}, getElementById(id) { return elements[id] || null; },
    querySelectorAll() { return Object.values(headers); }
};
const window = { location: new URL('https://example.org/economics.html?jel=C73&sort=status&dir=desc'),
    history: { replaceState(state, title, url) { window.location = url; } } };
const context = vm.createContext({ window, document, URL, URLSearchParams, setTimeout, clearTimeout });
vm.runInContext(fs.readFileSync(path.join(root, 'docs/app.js'), 'utf8'), context);
vm.runInContext(fs.readFileSync(path.join(root, 'docs/economics.js'), 'utf8'), context);
const api = window.EconomicsCatalogue;
// These fixed IDs were minted with a different initial order. Current ranks win.
const records = [
    { id: 'C73-1', title: 'Beta & <target>', jel_code: 'C73', rank: 3, source_id: 'OP-0590', definition_tex: 'A stochastic payoff bound' },
    { id: 'C72-2', title: 'Alpha', jel_code: 'C72', rank: 1, source_id: 'OP-0131', definition_tex: 'A computational equilibrium target' },
    { id: 'D63-3', title: 'Gamma', jel_code: 'D63', rank: 2, source_id: 'OP-0186', definition_tex: 'A fair allocation' }
];
const resultIds = values => Array.from(values, record => record.id);
assert.deepEqual(resultIds(records.slice().sort((a, b) => api.compare(a, b))), ['C72-2', 'D63-3', 'C73-1']);
assert.deepEqual(resultIds(records.slice().sort((a, b) => api.compare(a, b, 'rank', 'desc'))), ['C73-1', 'D63-3', 'C72-2']);
assert.deepEqual(resultIds(api.filter(records, { search: '1' })), ['C72-2']);
assert.deepEqual(resultIds(api.filter(records, { search: 'c73-1' })), ['C73-1']);
assert.deepEqual(resultIds(api.filter(records, { search: 'stochastic bound' })), ['C73-1']);
assert.deepEqual(resultIds(api.filter(records, { family: 'C', jel: 'C72' })), ['C72-2']);
assert.deepEqual(resultIds(api.filter(records, { family: 'D', jel: 'C72' })), []);
assert.match(api.rows(records), /Beta &amp; &lt;target&gt;/);
assert.match(api.rows(records), /problem\.html\?type=economics&id=C73-1/);
assert.match(api.rows([]), /colspan="8"/);
const statementRow = api.rows([records[0]]);
assert.equal((statementRow.match(/<td\b/g) || []).length, 8);
assert.doesNotMatch(statementRow, /<td>C73-1<\/td>/);
assert.match(statementRow, />unreviewed<\/td>/);
assert.match(statementRow, />no attempt<\/a>/);
assert.match(statementRow, />0 attempts<\/span>/);
assert.equal((statementRow.match(/>—<\/td>/g) || []).length, 2);
const attempted = { ...records[0], completion: 25, attacks: [{ model: 'GPT', status: 'unresolved' }] };
assert.match(api.rows([attempted]), />25%<\/td>/);
const solvedClaim = { ...records[0], status: 'solved', source_status: 'open', status_source: 'llm_claim',
    llm_status: 'solved', completion: 100, completion_source: 'llm_claim',
    attacks: [{ model: 'GPT 6 Astra Pro', status: 'solved', completion: 100 },
        { model: 'GPT 6 Astra Ultra', status: 'unresolved', completion: 15 }] };
assert.match(api.rows([solvedClaim]), />solved \(LLM claim\)<\/td>/);
assert.match(api.rows([solvedClaim]), />100%<\/td>/);
assert.match(api.rows([solvedClaim]), />solved<\/a>/);
assert.equal(window.ProblemHunting.getOpenProblemSourceStatusLabel(solvedClaim), 'open');
assert.equal(window.ProblemHunting.getCompletionSourceLabel(solvedClaim), 'LLM claim');
for (const direction of ['asc', 'desc']) {
    assert.deepEqual(resultIds([records[1], attempted].sort((a, b) => api.compare(a, b, 'completion', direction))), ['C73-1', 'C72-2']);
}
const estimatedRecords = [attempted,
    { ...records[1], completion: 0, attacks: [{ model: 'GPT', status: 'unresolved' }] },
    { ...records[2], completion: 45.5, attacks: [{ model: 'GPT', status: 'unresolved' }] },
    { id: 'C73-4', rank: 4, attacks: [{ model: 'GPT', status: 'solved' }] }
];
assert.deepEqual(resultIds(estimatedRecords.slice().sort((a, b) => api.compare(a, b, 'completion', 'asc'))),
    ['C72-2', 'C73-1', 'D63-3', 'C73-4']);
assert.deepEqual(resultIds(estimatedRecords.slice().sort((a, b) => api.compare(a, b, 'completion', 'desc'))),
    ['D63-3', 'C73-1', 'C72-2', 'C73-4']);
assert.match(api.rows(estimatedRecords), />0%<\/td>/);
assert.match(api.rows(estimatedRecords), />45.5%<\/td>/);
const html = fs.readFileSync(path.join(root, 'docs/economics.html'), 'utf8');
assert.deepEqual(Array.from(html.matchAll(/data-sort="([^"]+)"/g), match => match[1]), Object.keys(headers));
assert.match(html, /data-sort="rank">Rank /);
assert.doesNotMatch(html, /Difficulty rank|<option value="id">|UnsolvedMath #|data-sort="source"/);
records[0].attacks = [{ model: 'GPT 6 Astra Ultra', status: 'unresolved' }, { entry_kind: 'statement_only' }];
records[1].attacks = [{ model: 'GPT 6 Astra Pro', status: 'unresolved' }];
assert.match(api.rows([records[0]]), />gpt 6 astra ultra<\/td>/);
assert.match(api.rows([records[1]]), />gpt 6 astra pro<\/td>/);
window.ECONOMICS_DATA = Object.fromEntries(records.map(record => [record.id, record]));
api.init();
assert.equal(elements['results-count'].textContent, '1 of 3 entries · 1 research attempt');
assert.match(elements['economics-tbody'].innerHTML, /C73-1/);
assert.equal(headers.status.header.attributes['aria-sort'], 'descending');
elements['reset-filters'].handlers.click();
assert.equal(elements['results-count'].textContent, '3 of 3 entries · 2 research attempts');
assert.equal(elements['sort-by'].value, 'rank');
assert.equal(headers.rank.header.attributes['aria-sort'], 'ascending');
assert.equal(window.location.search, '');
headers.rank.handlers.click();
assert.equal(elements['sort-direction'].value, 'desc');
assert.equal(headers.rank.header.attributes['aria-sort'], 'descending');
assert.equal(window.location.search, '?dir=desc');
elements['filter-jel-family'].value = 'D';
elements['filter-jel-family'].handlers.change();
assert.equal(elements['results-count'].textContent, '1 of 3 entries · 0 research attempts');
assert.match(elements['filter-jel'].innerHTML, />D63</);
assert.doesNotMatch(elements['filter-jel'].innerHTML, />C72</);
assert.equal(window.location.search, '?dir=desc&family=D');
console.log('Economics search, JEL filters, current-rank sorting, permanent links, reset and accessible sort state verified.');
