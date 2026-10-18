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
const wsMapping = JSON.parse(fs.readFileSync(path.join(root, 'lists/we_solve_links.json'), 'utf8')).problems;
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

function readDataExport(file, declaration) {
    const source = fs.readFileSync(path.join(docs, file), 'utf8');
    const start = source.indexOf(declaration);
    assert.ok(start >= 0, `Missing data declaration in ${file}`);
    return JSON.parse(source.slice(start + declaration.length).split(/;\r?\n/, 1)[0]);
}

async function collectPages(expression) {
    return evaluate(`(() => {
        const size = document.querySelector('#page-size-top');
        size.value = '1000';
        size.dispatchEvent(new Event('change'));
        const rows = [];
        for (let page = 0; page < 100; page++) {
            rows.push(...(${expression}));
            const next = document.querySelector('#pagination-top [data-page-next]');
            if (next.disabled) return rows;
            next.click();
        }
        throw new Error('Pagination did not reach its last page');
    })()`);
}

async function checkPagination(category, tbody) {
    const result = await evaluate(`(() => {
        const body = document.getElementById(${JSON.stringify(tbody)});
        const size = document.querySelector('#page-size-top');
        const bottomSize = document.querySelector('#page-size-bottom');
        const next = document.querySelector('#pagination-top [data-page-next]');
        const previous = document.querySelector('#pagination-top [data-page-previous]');
        const links = () => [...body.querySelectorAll('tr')].flatMap(row => {
            const link = row.querySelector('td:first-child a') || row.querySelector('.catalogue-problem a');
            return link ? [link.getAttribute('href')] : [];
        });
        const initial = { count: links().length, size: size.value, previous: previous.disabled,
            choices: [...size.options].map(option => Number(option.value)),
            dataFiles: performance.getEntriesByType('resource').map(entry => new URL(entry.name).pathname)
                .filter(path => path.includes('/data/') && path.endsWith('.js')) };
        const first = links(); next.click(); const second = links(); previous.click();
        const returned = links();
        const sizes = [];
        for (const value of [200, 400, 500, 1000]) {
            size.value = String(value); size.dispatchEvent(new Event('change'));
            sizes.push({ value, count: links().length, bottom: bottomSize.value,
                page: new URL(location.href).searchParams.get('page') });
        }
        size.value = '200'; size.dispatchEvent(new Event('change')); next.click();
        let all, compare, href;
        if (${JSON.stringify(category)} === 'erdos') {
            document.getElementById('completion-header').click();
            document.getElementById('completion-header').click();
            all = Object.values(erdosProblems);
            compare = (a, b) => (b.completion ?? -1) - (a.completion ?? -1);
            href = record => 'problem.html?type=erdos&id=' + record.number;
        } else if (${JSON.stringify(category)} === 'economics') {
            document.querySelector('[data-sort="rank"]').click();
            all = Object.values(window.ECONOMICS_DATA);
            compare = (a, b) => window.EconomicsCatalogue.compare(a, b, 'rank', 'desc');
            href = record => 'problem.html?type=economics&id=' + record.id;
        } else {
            document.querySelector('[data-sort="rank"]').click();
            all = Object.values(window.OPEN_PROBLEMS_DATA);
            compare = (a, b) => window.ProblemHunting.compareOpenProblems(a, b, 'rank', 'desc');
            href = window.ProblemHunting.getOpenProblemHref;
        }
        const expected = all.sort(compare).map(href);
        const sortedFirst = links(), sortedPage = new URL(location.href).searchParams.get('page');
        next.click();
        return { initial, first, second, returned, sizes, total: all.length,
            sortedFirst, sortedPage, sortedSecond: links(),
            expectedFirst: expected.slice(0, 200), expectedSecond: expected.slice(200, 400),
            search: ${JSON.stringify(category)} === 'open_problems' ? all[300].title : String(all[300].id || all[300].number),
            searchHref: href(all[300]),
            saved: location.href };
    })()`);
    assert.equal(result.initial.count, 100, category);
    assert.equal(result.initial.size, '100', category);
    assert.equal(result.initial.previous, true, category);
    assert.deepEqual(result.initial.choices, [100, 200, 400, 500, 1000], category);
    assert.ok(result.initial.dataFiles.some(path => path.endsWith(`/data/${category}_catalogue.js`)), category);
    assert.ok(result.initial.dataFiles.every(path => !path.endsWith('_data.js')), `${category}: no full detail dataset downloaded`);
    assert.equal(result.second.length, 100, category);
    assert.ok(result.second.every(href => !result.first.includes(href)), category);
    assert.deepEqual(result.returned, result.first, category);
    for (const row of result.sizes) {
        assert.equal(row.count, Math.min(row.value, result.total), category);
        assert.equal(row.bottom, String(row.value), category);
        assert.equal(row.page, null, category);
    }
    assert.equal(result.sortedPage, null, `${category}: sorting resets to page 1`);
    assert.deepEqual(result.sortedFirst, result.expectedFirst, `${category}: sort full collection before page 1`);
    assert.deepEqual(result.sortedSecond, result.expectedSecond, `${category}: page 2 continues global sort`);
    await visit(result.saved, `document.querySelector('#${tbody} .claim-status a')`);
    assert.equal(await evaluate("document.querySelector('#page-size-top').value"), '200');
    assert.match(await evaluate("document.querySelector('#pagination-top [data-page-status]').textContent"), /^201–400 /);
    await evaluate(`document.getElementById('search').value = ${JSON.stringify(result.search)};
        document.getElementById('search').dispatchEvent(new Event('input'));`);
    await evaluate(`new Promise(resolve => setTimeout(resolve, 300))`);
    assert.equal(await evaluate("new URL(location.href).searchParams.get('page')"), null);
    assert.ok(await evaluate(`[...document.querySelectorAll('#${tbody} td:first-child a')].some(link => link.getAttribute('href') === ${JSON.stringify(result.searchHref)})`),
        `${category}: search reaches records beyond the current page`);
    await evaluate(`document.getElementById('search').value = 'zzzz-no-matching-problem-zzzz';
        document.getElementById('search').dispatchEvent(new Event('input'));`);
    await evaluate(`new Promise(resolve => setTimeout(resolve, 300))`);
    assert.equal(await evaluate(`document.querySelectorAll('#${tbody} .claim-status a').length`), 0);
    assert.equal(await evaluate("document.querySelector('#pagination-top [data-page-previous]').disabled && document.querySelector('#pagination-top [data-page-next]').disabled"), true);
    await visit(`${category}.html`, `document.querySelector('#${tbody} .claim-status a')`);
    await call('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, mobile: true, deviceScaleFactor: 1 });
    const mobile = await evaluate(`(() => {
        const top = document.getElementById('pagination-top');
        document.querySelector('#pagination-bottom [data-page-next]').click();
        return { top: top.getBoundingClientRect().top, width: innerWidth,
            controls: [...document.querySelectorAll('.pagination > *')].map(element => {
                const rect = element.getBoundingClientRect();
                return { left: rect.left, right: rect.right, width: rect.width };
            }) };
    })()`);
    assert.ok(mobile.top >= 0 && mobile.top < 100, `${category}: bottom navigation returns to controls`);
    assert.ok(mobile.controls.every(rect => rect.width > 0 && rect.left >= 0 && rect.right <= mobile.width + 1),
        `${category}: pagination controls fit mobile viewport`);
    await call('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, mobile: false, deviceScaleFactor: 1 });
}

async function checkResponsiveActions(type, id, record, viewport) {
    const label = `${type}:${id} at ${viewport.width}px`;
    await visit(`problem.html?type=${type}&id=${encodeURIComponent(id)}`,
        "document.querySelector('#attempts-container .attempt-header') && document.querySelector('#problem-meta > p:first-child a')?.textContent === 'Contribute'");
    // Allow the browser to complete layout before measuring the controls.
    await evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))');
    const result = await evaluate(`(() => {
        const bounds = element => {
            const rect = element.getBoundingClientRect();
            return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom,
                width: rect.width, height: rect.height };
        };
        window.scrollTo(0, 0);
        const contribute = document.querySelector('#problem-meta > p:first-child a');
        const metadata = document.querySelector('#problem-meta strong');
        const identity = document.querySelector('#problem-meta .we-solve-id');
        const otherMetadata = [...document.querySelectorAll('#problem-meta > p')].find(paragraph =>
            paragraph !== identity && paragraph.querySelector('strong'));
        const topLink = { label: contribute.textContent, href: contribute.href, rect: bounds(contribute),
            beforeMetadata: !!(contribute.compareDocumentPosition(metadata) & Node.DOCUMENT_POSITION_FOLLOWING),
            aboveMetadata: contribute.getBoundingClientRect().bottom <= metadata.getBoundingClientRect().top + 1 };
        const identityRow = identity ? { text: identity.textContent.trim(), rect: bounds(identity),
            immediatelyAfterContribute: contribute.parentElement.nextElementSibling === identity,
            beforeOtherMetadata: !!(identity.compareDocumentPosition(otherMetadata) & Node.DOCUMENT_POSITION_FOLLOWING),
            links: [...identity.querySelectorAll('a')].map(link => [link.textContent, link.href]) } : null;
        const headers = [...document.querySelectorAll('.attempt-header')].map(header => {
            // Scroll each header into view vertically, keeping horizontal scroll at zero.
            // Mathematical content elsewhere can legitimately exceed the viewport.
            window.scrollTo(0, Math.max(0, header.getBoundingClientRect().top + window.scrollY - 10));
            return { rect: bounds(header), direction: getComputedStyle(header).flexDirection,
                links: [...header.querySelectorAll('a')].map(link => ({
                    label: link.textContent, href: link.href, download: link.getAttribute('download'), rect: bounds(link)
                })) };
        });
        return { width: innerWidth, height: innerHeight, topLink, identityRow, headers };
    })()`);
    const contributeUrl = record.we_solve?.url ? record.we_solve.url + '#contribute' : 'https://we-solve.github.io/contribute/';
    assert.equal(result.width, viewport.width, label);
    assert.equal(result.topLink.label, 'Contribute', label);
    assert.equal(result.topLink.href, contributeUrl, label);
    assert.ok(result.topLink.beforeMetadata && result.topLink.aboveMetadata, `${label}: Contribute precedes metadata`);
    const inViewport = (rect, description) => {
        assert.ok(rect.width > 0 && rect.height > 0, `${label}: ${description} is visible`);
        assert.ok(rect.left >= -1 && rect.right <= result.width + 1,
            `${label}: ${description} fits horizontally (${rect.left}, ${rect.right})`);
        assert.ok(rect.top >= -1 && rect.bottom <= result.height + 1,
            `${label}: ${description} fits vertically after scrolling`);
    };
    inViewport(result.topLink.rect, 'top Contribute');
    if (record.we_solve) {
        const originalCode = record.we_solve.record_code || record.we_solve.code;
        const sharedPage = originalCode !== record.we_solve.code;
        assert.equal(result.identityRow?.text,
            `We-Solve ID: ${originalCode}${sharedPage ? ` (shared page: ${record.we_solve.code})` : ''}`, label);
        assert.ok(result.identityRow.immediatelyAfterContribute && result.identityRow.beforeOtherMetadata,
            `${label}: We-Solve ID follows Contribute and precedes other metadata`);
        assert.deepEqual(result.identityRow.links,
            (sharedPage ? [originalCode, record.we_solve.code] : [originalCode]).map(code => [code, record.we_solve.url]), label);
        inViewport(result.identityRow.rect, 'We-Solve ID');
    } else {
        assert.equal(result.identityRow, null, `${label}: unmapped problems have no invented We-Solve ID`);
    }
    assert.equal(result.headers.length, record.attacks.length, label);
    for (const [index, header] of result.headers.entries()) {
        assert.deepEqual(header.links.slice(0, 4).map(link => link.label), ['contribute', 'source', 'comments', 'review'], label);
        assert.equal(header.links[0].href, contributeUrl, label);
        assert.equal(new URL(header.links[2].href).hash, '#comments', label);
        assert.equal(header.direction, viewport.mobile ? 'column' : 'row', label);
        for (const [linkIndex, link] of header.links.entries()) {
            inViewport(link.rect, `attempt ${index + 1} ${link.label}`);
            assert.ok(link.rect.left >= header.rect.left - 1 && link.rect.right <= header.rect.right + 1 &&
                link.rect.top >= header.rect.top - 1 && link.rect.bottom <= header.rect.bottom + 1,
                `${label}: ${link.label} stays inside its header`);
            if (linkIndex > 0) {
                const previous = header.links[linkIndex - 1].rect;
                assert.ok(link.rect.top >= previous.top - 1, `${label}: link order survives wrapping`);
                assert.ok(Math.abs(link.rect.top - previous.top) > 1 || link.rect.left >= previous.right - 1,
                    `${label}: adjacent action links do not overlap`);
            }
        }
        if (type === 'economics') {
            assert.equal(header.links[4].label, 'Download attack TeX', label);
            assert.ok(header.links[4].download?.endsWith('.tex'), label);
        } else {
            assert.equal(header.links.length, 4, label);
        }
    }
    assert.deepEqual(result.headers.map(header => [header.links[1].href, header.links[3].href]).sort(),
        record.attacks.map(attack => [attack.we_solve?.source_url ||
            encodeURI('https://github.com/mehmetmars7/Erdosproblems-llm-hunter/blob/main/' + attack.file_path),
            attack.we_solve?.url || 'https://we-solve.github.io/contribute/review/']).sort(), label);
}

try {
    await call('Page.enable');
    await call('Runtime.enable');
    await call('Network.enable');
    await call('Network.setCacheDisabled', { cacheDisabled: true });
    // Only the project's routing/rendering is under test; omit third-party widgets.
    await call('Network.setBlockedURLs', { urls: ['*cdn.jsdelivr.net*', '*fonts.googleapis.com*', '*fonts.gstatic.com*', '*giscus.app*'] });
    const responsiveRecords = [
        ['open_problems', '1', JSON.parse(fs.readFileSync(path.join(docs, 'data/top_problems/1.json'), 'utf8'))],
        ['open_problems', '3395', JSON.parse(fs.readFileSync(path.join(docs, 'data/top_problems/3395.json'), 'utf8'))],
        // This page includes both an exported manuscript and a changed manuscript
        // whose original source must remain available through the fallback.
        ['economics', 'C23-429', readDataExport('data/economics_data.js', 'window.ECONOMICS_DATA = ')['C23-429']],
        ['erdos', '1', readDataExport('data/erdos_data.js', 'var erdosProblems = ')['1']]
    ];
    assert.ok(responsiveRecords.some(([, , record]) => record.attacks.some(attack => attack.we_solve?.source_url)),
        'Responsive checks include a mapped source');
    assert.ok(responsiveRecords.some(([, , record]) => record.attacks.some(attack => !attack.we_solve?.source_url)),
        'Responsive checks include an original-source fallback');
    assert.ok(responsiveRecords.some(([, , record]) => record.we_solve?.record_code &&
        record.we_solve.record_code !== record.we_solve.code), 'Responsive checks distinguish merged record and shared-page codes');
    for (const viewport of [{ width: 1280, height: 900, mobile: false }, { width: 390, height: 844, mobile: true }]) {
        await call('Emulation.setDeviceMetricsOverride', { ...viewport, deviceScaleFactor: 1 });
        for (const [type, id, record] of responsiveRecords) {
            await checkResponsiveActions(type, id, record, viewport);
        }
    }
    await call('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, mobile: false, deviceScaleFactor: 1 });
    for (const [legacy, id, code] of [['problem.p-versus-np', 1, 'MPP-001'], ['problem.hodge-conjecture', 6, 'MPP-006']]) {
        const record = JSON.parse(fs.readFileSync(path.join(docs, 'data/top_problems', `${id}.json`), 'utf8'));
        const contributeUrl = record.we_solve?.url ? record.we_solve.url + '#contribute' : 'https://we-solve.github.io/contribute/';
        for (const requested of [legacy, String(id)]) {
            await visit(`problem.html?type=open_problems&id=${requested}&view=all#llm-attempts-section`,
                "document.querySelector('#attempts-container .attempt') && document.querySelector('#problem-statement-source a')");
            const result = await evaluate(`({
                id: new URL(location.href).searchParams.get('id'), hash: location.hash,
                title: document.querySelector('#page-title').textContent,
                statement: document.querySelector('#problem-links').textContent.length,
                attempts: document.querySelectorAll('#attempts-container .attempt').length,
                external: [...document.querySelectorAll('#problem-statement-source a')].map(a => [a.href, a.textContent, a.target]),
                contribute: document.querySelector('#problem-meta > p:first-child a')?.href,
                headers: [...document.querySelectorAll('.attempt-header')].map(header =>
                    [...header.querySelectorAll('a')].map(a => [a.textContent, a.href]))
            })`);
            assert.equal(result.id, String(id));
            assert.equal(result.hash, '#llm-attempts-section');
            assert.equal(result.title, registry.find(record => record.id === id).title);
            assert.ok(result.statement > 100 && result.attempts > 0);
            assert.equal(result.external.length, 1);
            assert.equal(result.external[0][0], record.we_solve?.source_url ||
                `https://github.com/mehmetmars7/Erdosproblems-llm-hunter/blob/main/attacks/open_problems/top_problems/definitions/${id}.tex`);
            assert.ok(result.external.every(([url]) => !url.includes('unsolvedmath.com')));
            assert.equal(result.contribute, contributeUrl);
            for (const header of result.headers) {
                assert.deepEqual(header.map(([label]) => label), ['contribute', 'source', 'comments', 'review']);
                assert.equal(header[0][1], contributeUrl);
                assert.equal(new URL(header[2][1]).hash, '#comments');
            }
            assert.deepEqual(result.headers.map(header => [header[1][1], header[3][1]]).sort(),
                record.attacks.map(attack => [attack.we_solve?.source_url ||
                    encodeURI('https://github.com/mehmetmars7/Erdosproblems-llm-hunter/blob/main/' + attack.file_path),
                    attack.we_solve?.url || 'https://we-solve.github.io/contribute/review/']).sort());
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
    await checkPagination('open_problems', 'open-problems-tbody');
    const catalogue = { headings: await evaluate("[...document.querySelectorAll('th')].map(th => th.textContent)"),
        links: await collectPages(`[...document.querySelectorAll('#open-problems-tbody tr')].map(row => ({
            href: row.querySelector('td:first-child a')?.getAttribute('href'),
            problem: row.querySelector('.catalogue-problem a').href,
            claim: row.querySelector('.claim-status a').href,
            external: [...row.querySelectorAll('td:last-child a')].map(a => [a.href, a.textContent, a.target, a.rel])
        }))`) };
    assert.ok(catalogue.headings.some(label => label.trim().startsWith('UnsolvedMath #')));
    for (const record of registry) {
        const row = catalogue.links.find(row => row.href === `problem.html?type=open_problems&id=${record.id}`);
        assert.ok(row, `Missing numeric link for ${record.id}`);
        assert.equal(row.problem, wsMapping[`open_problems:${record.id}`].url);
        assert.equal(row.claim, row.problem);
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
        assert.equal(states.rows, Math.min(1000, catalogue.links.length));
    }
    await call('Page.bringToFront');
    await evaluate(`document.querySelector('[data-sort="title"]').focus()`);
    await call('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' });
    await call('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    assert.equal(await evaluate(`document.querySelector('[data-sort="title"]').closest('th').getAttribute('aria-sort')`), 'ascending');
    for (const [category, declaration] of [['economics', 'window.ECONOMICS_DATA = '], ['erdos', 'var erdosProblems = ']]) {
        const records = readDataExport(`data/${category}_data.js`, declaration);
        await visit(`${category}.html`, `document.querySelector('#${category}-tbody .claim-status a')`);
        await checkPagination(category, `${category}-tbody`);
        if (category === 'erdos') {
            await evaluate(`(() => {
                const filter = document.querySelector('input[type="checkbox"]');
                filter.checked = false;
                filter.dispatchEvent(new Event('change'));
            })()`);
        }
        const rows = await collectPages(`Array.from(document.querySelectorAll('#${category}-tbody tr'), row => ({
            local: row.querySelector('td:first-child a').getAttribute('href'),
            number: row.querySelector('td:first-child a').textContent,
            problem: row.querySelector('.catalogue-problem a')?.href,
            claim: row.querySelector('.claim-status a').href
        }))`);
        assert.equal(rows.length, Object.keys(records).length, category);
        for (const row of rows) {
            const id = new URL(row.local, base).searchParams.get('id');
            const record = records[id];
            assert.ok(record, `${category}: unknown local problem ${id}`);
            assert.equal(row.local, `problem.html?type=${category}&id=${id}`);
            assert.equal(row.number, category === 'erdos' ? `#${record.number}` : String(record.rank));
            assert.equal(row.claim, wsMapping[`${category}:${id}`].url);
            if (category === 'economics') assert.equal(row.problem, row.claim);
        }
    }
    assert.deepEqual(errors, []);
    console.log(`Browser verified pagination sizes, global sorting, navigation, saved pages, empty results, all list destinations, detail controls and keyboard activation.`);
} finally {
    socket.close();
    await fetch(`${debug}/json/close/${target.id}`);
    if (server) await new Promise(resolve => server.close(resolve));
}
