// Run with: node tests/test_frontend_models.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const context = vm.createContext({ window: {}, document: { addEventListener() {} } });
vm.runInContext(fs.readFileSync(path.join(root, 'docs/app.js'), 'utf8'), context);
const api = context.window.ProblemHunting;
const astra = { model: 'GPT 6 Astra Ultra', status: 'unresolved' };
const imported = { ...astra, entry_kind: 'reused_writeup', provenance: { source_model: 'gpt_pro_5.2' } };
const labels = attacks => Array.from(api.getModelLabels(attacks));
assert.deepEqual(labels([astra]), ['gpt 6']);
assert.deepEqual(labels([imported]), ['gpt 6 (collection)', 'gpt pro']);
assert.deepEqual(labels([imported, astra]), ['gpt 6', 'gpt pro']);
assert.deepEqual(labels([{ ...astra, entry_kind: 'statement_only' }]), []);
const many = labels([astra, { model: 'gpt pro 5.4' }, { model: 'codex 5.2 extra high' }, { model: 'claude opus 4.5' }]);
assert.equal(many.length, 4);
assert.equal(many[0], 'gpt 6');
assert.ok(many.every(label => label === label.toLowerCase()));
assert.deepEqual(labels([{ model: 'Custom Model' }]), ['custom model']);
assert.deepEqual(labels([{ model: 'claude opus 4.5' }, { model: 'claude_opus_4.8' }]), ['opus 4.5', 'opus 4.8']);
assert.equal(astra.model, 'GPT 6 Astra Ultra');
assert.deepEqual(Array.from(api.getUniqueModels([astra])), ['GPT 6 Astra Ultra']);
const detail = fs.readFileSync(path.join(root, 'docs/problem.html'), 'utf8');
const listing = fs.readFileSync(path.join(root, 'docs/erdos.html'), 'utf8');
assert.doesNotMatch(detail, /Open, falsifiable, or decidable maps to unresolved/);
assert.match(listing, /open, falsifiable, or decidable means unresolved/);
assert.match(listing, /getModelLabels\(p\.attacks\)/);
assert.doesNotMatch(listing, /uniqueModels\.slice\(0, 2\)/);
for (const html of [detail, listing]) {
    for (const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) new vm.Script(match[1]);
}
console.log('Model labels, collection attribution, model visibility, detail notice and inline syntax passed.');
