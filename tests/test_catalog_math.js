const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const context = vm.createContext({ window: { ProblemHunting: {} } });
vm.runInContext(fs.readFileSync(path.join(root, 'docs/catalog-math.js'), 'utf8'), context);
const prepare = context.window.ProblemHunting.catalogMath;
const tex = String.raw;

assert.equal(prepare('H^(2i)(X_bar,Q_l(i))^Gal(k_bar/k)'),
    tex`\(H^{2 i}(\overline{X},Q_{l}(i))^{\operatorname{Gal}(\overline{k} / k)}\)`);
assert.equal(prepare('zeta(s)=sum_{n>=1} n^(-s)'), tex`\(\zeta(s) = \sum_{n \ge 1} n^{-s}\)`);
assert.equal(prepare('0<Re(s)<1'), tex`\(0 < \operatorname{Re}(s) < 1\)`);
assert.equal(prepare('NP subseteq BQP'), tex`\(\mathrm{NP} \subseteq \mathrm{BQP}\)`);
assert.equal(prepare('C-infinity(R^3 x [0,infinity))'), tex`\(C^{\infty}(R^{3} x [0,\infty))\)`);
assert.equal(prepare('|u(x,t)|^2'), tex`\(|u(x,t)|^{2}\)`);
for (const plain of [
    'For every smooth geometrically irreducible projective variety.',
    'Fefferman statement (A), sections 3-4, reviewed 2026-09-24.',
    'The l-adic cycle-class map over a finitely generated field.',
    'https://example.org/a?x=2', '`Q_l`', tex`$Q_\ell$`, tex`\(x^2\)`,
    'H^(unfinished prose', 'Q_',
]) assert.equal(prepare(plain), plain);

// Already-delimited TeX from the numbered definitions must stay unchanged.
const definitions = path.join(root, 'attacks/open_problems/top_problems/definitions');
let withMath = 0;
const order = JSON.parse(fs.readFileSync(path.join(root, 'lists/unsolvedmath/display_order.json'), 'utf8'));
for (const number of order) {
    const source = fs.readFileSync(path.join(definitions, `${number}.tex`), 'utf8');
    const fragments = source.replace(/^%[^\n]*$/gm, '').match(/\\\[[\s\S]*?\\\]|(?<!\\)\$(?:\\.|[^$\\])*?\$/g) || [];
    for (const fragment of fragments) assert.equal(prepare(fragment), fragment, `Definition ${number}`);
    if (fragments.length) withMath++;
}
assert.ok(withMath > 300);
console.log(`Catalog notation tests passed; protected TeX checked in ${withMath}/${order.length} definitions.`);
