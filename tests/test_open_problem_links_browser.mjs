// Node 22+, with an isolated Chromium/Edge remote-debugging session.
// CHROME_DEBUG_URL=http://127.0.0.1:9226 node tests/test_open_problem_links_browser.mjs
// Set SITE_BASE_URL to verify a deployment; otherwise serves docs locally.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const docs = path.join(root, 'docs');
const registry = JSON.parse(fs.readFileSync(path.join(root, 'lists/unsolvedmath/problems.json'), 'utf8'));
let server;
let base = process.env.SITE_BASE_URL;
if (!base) {
    server = http.createServer((req, res) => {
        const file = path.resolve(docs, '.' + new URL(req.url, 'http://localhost').pathname);
        if (!file.startsWith(docs + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
            res.writeHead(404).end(); return;
        }
        const mime = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.css': 'text/css' };
        res.setHeader('Content-Type', mime[path.extname(file)] || 'text/plain');
        fs.createReadStream(file).pipe(res);
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    base = `http://127.0.0.1:${server.address().port}/`;
}
const debug = process.env.CHROME_DEBUG_URL || 'http://127.0.0.1:9226';
const target = await (await fetch(`${debug}/json/new?about:blank`, { method: 'PUT' })).json();
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true });
    socket.addEventListener('error', reject, { once: true });
});
let sequence = 0;
const pending = new Map();
const errors = [];
socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails);
    const handler = pending.get(message.id);
    if (!handler) return;
    pending.delete(message.id);
    clearTimeout(handler.timeout);
    if (message.error) handler.reject(new Error(JSON.stringify(message.error)));
    else handler.resolve(message.result);
});
const call = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const timeout = setTimeout(() => { pending.delete(id); reject(new Error(`Timed out: ${method}`)); }, 30000);
    pending.set(id, { resolve, reject, timeout });
    socket.send(JSON.stringify({ id, method, params }));
});
async function evaluate(expression) {
    const result = await call('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    assert.ok(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
    return result.result.value;
}
async function visit(route, ready) {
    await call('Page.navigate', { url: new URL(route, base).href });
    await evaluate(`new Promise((resolve, reject) => {
        const until = Date.now() + 25000;
        function check() {
            if (${ready}) return resolve(true);
            if (Date.now() > until) return reject(new Error('Page did not render'));
            setTimeout(check, 100);
        }
        check();
    })`);
}
try {
    await call('Page.enable');
    await call('Runtime.enable');
    await call('Network.enable');
    await call('Network.setCacheDisabled', { cacheDisabled: true });
    // Only the project's routing/rendering is under test; omit third-party widgets.
    await call('Network.setBlockedURLs', { urls: ['*cdn.jsdelivr.net*', '*fonts.googleapis.com*', '*fonts.gstatic.com*', '*giscus.app*'] });
    for (const [legacy, id, code] of [['problem.p-versus-np', 1, 'MPP-001'], ['problem.hodge-conjecture', 6, 'MPP-006']]) {
        for (const requested of [legacy, String(id)]) {
            await visit(`problem.html?type=open_problems&id=${requested}&view=all#llm-attempts-section`,
                "document.querySelector('#attempts-container .attempt') && document.querySelector('#problem-statement-source a')");
            const result = await evaluate(`({
                id: new URL(location.href).searchParams.get('id'), hash: location.hash,
                title: document.querySelector('#page-title').textContent,
                statement: document.querySelector('#problem-links').textContent.length,
                attempts: document.querySelectorAll('#attempts-container .attempt').length,
                external: [...document.querySelectorAll('#problem-statement-source a')].map(a => [a.href, a.textContent, a.target])
            })`);
            assert.equal(result.id, String(id));
            assert.equal(result.hash, '#llm-attempts-section');
            assert.equal(result.title, registry.find(record => record.id === id).title);
            assert.ok(result.statement > 100 && result.attempts > 0);
            assert.equal(result.external.length, 1);
            assert.ok(result.external[0][0].endsWith(`/top_problems/definitions/${id}.tex`));
            assert.ok(result.external.every(([url]) => !url.includes('unsolvedmath.com')));
        }
    }
    await visit('problem.html?type=open_problems&id=1881', "document.querySelector('#erdos-main-link a')");
    const erdosLink = await evaluate(`({
        href: document.querySelector('#erdos-main-link a').getAttribute('href'),
        hidden: document.querySelector('#erdos-main-link').hidden,
        beforeStatement: !!(document.querySelector('#erdos-main-link').compareDocumentPosition(document.querySelector('.problem-statement')) & Node.DOCUMENT_POSITION_FOLLOWING)
    })`);
    assert.equal(erdosLink.href, 'problem.html?type=erdos&id=9');
    assert.equal(erdosLink.hidden, false);
    assert.equal(erdosLink.beforeStatement, true);
    await visit('open_problems.html', "document.querySelector('#open-problems-tbody .catalogue-problem')");
    const catalogue = await evaluate(`({
        headings: [...document.querySelectorAll('th')].map(th => th.textContent),
        links: [...document.querySelectorAll('#open-problems-tbody tr')].map(row => ({
            href: row.querySelector('.catalogue-problem a').getAttribute('href'),
            external: [...row.querySelectorAll('td:last-child a')].map(a => [a.href, a.textContent, a.target, a.rel])
        }))
    })`);
    assert.ok(catalogue.headings.some(label => label.trim().startsWith('UnsolvedMath #')));
    for (const record of registry) {
        const row = catalogue.links.find(row => row.href === `problem.html?type=open_problems&id=${record.id}`);
        assert.ok(row, `Missing numeric link for ${record.id}`);
        assert.deepEqual(row.external, record.external_url ? [[record.external_url, record.problem_number, '_blank', 'noopener noreferrer']] : []);
    }
    for (const key of ['title', 'rank', 'status', 'review', 'claim', 'completion', 'models', 'source', 'unsolvedmath']) {
        const states = await evaluate(`(() => {
            const button = document.querySelector('[data-sort="${key}"]');
            const states = [];
            for (let i = 0; i < 2; i++) {
                button.click();
                states.push(button.closest('th').getAttribute('aria-sort'));
            }
            return { states, selected: document.querySelector('#sort-by').value,
                rows: document.querySelectorAll('#open-problems-tbody tr').length };
        })()`);
        assert.deepEqual(states.states, ['ascending', 'descending']);
        assert.equal(states.selected, key);
        assert.equal(states.rows, catalogue.links.length);
    }
    await call('Page.bringToFront');
    await evaluate(`document.querySelector('[data-sort="title"]').focus()`);
    await call('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' });
    await call('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    assert.equal(await evaluate(`document.querySelector('[data-sort="title"]').closest('th').getAttribute('aria-sort')`), 'ascending');
    assert.deepEqual(errors, []);
    console.log(`Browser verified detail routes, ${registry.length} catalogue links, external links, all nine sortable columns and keyboard activation.`);
} finally {
    socket.close();
    await fetch(`${debug}/json/close/${target.id}`);
    if (server) await new Promise(resolve => server.close(resolve));
}
