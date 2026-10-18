const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../docs/app.js'), 'utf8');

function setup(query = '') {
    const control = () => ({ handlers: {}, focus() { this.focused = true; },
        addEventListener(event, callback) { this.handlers[event] = callback; } });
    const hosts = ['top', 'bottom'].map(() => {
        const controls = Object.fromEntries(['size', 'previous', 'next', 'status'].map(key => [key, control()]));
        return { controls, querySelector(selector) { return controls[selector.slice(11, -1)]; },
            scrollIntoView() { this.scrolled = true; } };
    });
    const window = { location: new URL('https://example.org/list.html' + query) };
    const document = { addEventListener() {}, getElementById(id) {
        return id === 'pagination-top' ? hosts[0] : id === 'pagination-bottom' ? hosts[1] : null;
    } };
    const context = vm.createContext({ window, document, URL, URLSearchParams });
    vm.runInContext(source, context);
    let rows = Array.from({ length: 1221 }, (_, index) => index + 1), visible;
    const pager = window.ProblemHunting.createPagination(() => { visible = pager.select(rows); });
    visible = pager.select(rows);
    return { hosts, pager, get visible() { return Array.from(visible); },
        replace(records) { rows = records; visible = pager.select(rows); } };
}
const page = setup();
assert.deepEqual(page.visible, Array.from({ length: 100 }, (_, i) => i + 1));
assert.equal(page.hosts[0].controls.previous.disabled, true);
page.hosts[1].controls.next.handlers.click();
assert.equal(page.visible[0], 101);
assert.equal(page.hosts[0].scrolled, true);
assert.equal(page.hosts[0].controls.next.focused, true);
assert.equal(page.pager.urlParams().page, 2);
for (const size of [200, 400, 500, 1000]) {
    page.hosts[1].controls.size.value = String(size);
    page.hosts[1].controls.size.handlers.change();
    assert.equal(page.visible.length, size);
    assert.equal(page.visible[0], 1);
    assert.equal(page.hosts[0].controls.size.value, String(size));
    page.hosts[0].controls.next.handlers.click();
    assert.equal(page.visible[0], size + 1);
    assert.equal(page.visible.length, Math.min(size, 1221 - size));
    page.hosts[0].controls.previous.handlers.click();
    assert.equal(page.visible[0], 1);
}
const restored = setup('?size=400&page=3');
assert.equal(restored.visible[0], 801);
assert.equal(restored.visible.length, 400);
restored.hosts[0].controls.next.handlers.click();
assert.deepEqual(restored.visible, Array.from({ length: 21 }, (_, i) => 1201 + i));
assert.equal(restored.hosts[0].controls.next.disabled, true);
restored.replace([]);
assert.equal(restored.visible.length, 0);
assert.equal(restored.hosts[0].controls.previous.disabled, true);
assert.equal(restored.hosts[0].controls.next.disabled, true);
assert.equal(restored.hosts[0].controls.status.textContent, '0–0 of 0 · Page 1 of 1');
for (const query of ['?size=999999&page=-1', '?size=Infinity&page=NaN', '?size=101&page=0']) {
    const invalid = setup(query);
    assert.equal(invalid.visible.length, 100);
    assert.equal(invalid.visible[0], 1);
}
const last = setup('?size=1000&page=999');
assert.equal(last.visible[0], 1001);
last.pager.reset();
last.replace([9, 2, 1]);
assert.deepEqual(last.visible, [9, 2, 1]);
console.log('Pagination defaults, allowed sizes, navigation, restoration, boundaries and empty results passed.');
