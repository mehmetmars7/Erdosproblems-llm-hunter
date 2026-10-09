// Run with: node tests/test_economics_detail.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'docs/problem.html'), 'utf8');
const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(match => match[1]);
const detailScript = scripts.find(script => script.includes('function formatTeX'));
const economicsScript = fs.readFileSync(path.join(root, 'docs/economics-detail.js'), 'utf8');
const sample = {
    'C73-1': { id: 'C73-1', title: 'Game <one>', jel_code: 'C73', rank: 3, source_id: 'OP-0042',
        statement_url: 'data/economics/statements/C73-1.tex', attacks: [],
        definition_tex: String.raw`\subsection*{Definitions and assumptions}
For $x < 1$, use $\E[x]$.
\subsection*{Formal question}
See \Problemref{OP-0050}. Local references [S1].
\subsection*{References}
[S1] \url{https://example.org/}` },
    'C73-2': { id: 'C73-2', title: 'Game two', jel_code: 'C73', rank: 1, source_id: 'OP-0042',
        definition_tex: String.raw`\label{game:GT-002}Other statement.` },
    'H41-4': { id: 'H41-4', title: 'Public goods', jel_code: 'H41', rank: 2, source_id: 'OP-0050',
        definition_tex: String.raw`\label{game:GT-050}Third statement.` }
};

async function render(query, data = sample, lazy = false, loadError = false, assetUrl = '') {
    const elements = new Map();
    let createdScripts = 0;
    function element(id) {
        if (!elements.has(id)) elements.set(id, {
            innerHTML: '', textContent: '', style: {}, hidden: false, labels: [], references: [],
            querySelectorAll(selector) {
                return selector === '.tex-label' ? this.labels : this.references;
            }
        });
        return elements.get(id);
    }
    const callbacks = [];
    const document = {
        addEventListener(name, callback) { if (name === 'DOMContentLoaded') callbacks.push(callback); },
        getElementById: element,
        createElement(name) { assert.equal(name, 'script'); createdScripts += 1; return {}; },
        head: { appendChild(script) {
            assert.equal(script.src, assetUrl || 'data/economics_data.js');
            if (loadError) script.onerror();
            else { context.window.ECONOMICS_DATA = data; script.onload(); }
        } }
    };
    const context = vm.createContext({
        document, URL, URLSearchParams, console, setTimeout, clearTimeout,
        window: { location: new URL('file:///site/problem.html' + query),
            ECONOMICS_JEL_LABELS: JSON.parse(fs.readFileSync(path.join(root, 'lists/economics/jel_codes.json'), 'utf8')).labels,
            ...(lazy ? {} : { ECONOMICS_DATA: data }) }
    });
    vm.runInContext(fs.readFileSync(path.join(root, 'docs/app.js'), 'utf8'), context);
    vm.runInContext(scripts.find(script => script.includes('window.MathJax =')), context);
    vm.runInContext(economicsScript, context);
    vm.runInContext(detailScript, context);
    if (assetUrl) element('economics-detail-script').dataset = { economicsSrc: assetUrl };
    const reference = (key, kind = 'ref') => ({
        dataset: { texReference: key, texReferenceKind: kind, texScope: '0' },
        removeAttribute(name) { delete this[name]; }
    });
    element('problem-links').labels = [{ dataset: { texLabel: 'local:eq', texScope: '0' } }];
    element('problem-links').references = [
        reference('local:eq', 'eqref'), reference('game:GT-050'), reference('problem:OP-0042'),
        reference('app:audited-crosswalk')
    ];
    await callbacks[callbacks.length - 1]();
    return { element, context, createdScripts };
}

async function main() {
    let page = await render('?type=economics&id=C73-1');
    assert.equal(page.element('page-title').textContent, 'Game <one>');
    assert.match(page.element('problem-meta').innerHTML, /Field:<\/strong> Economics/);
    assert.match(page.element('problem-meta').innerHTML, /Problem Status:<\/strong> open/);
    assert.match(page.element('problem-meta').innerHTML, /LLM Claim:<\/strong> no attempt/);
    assert.match(page.element('problem-meta').innerHTML, /Community Review:<\/strong> unreviewed/);
    assert.doesNotMatch(page.element('problem-meta').innerHTML, /Problem ID:|Source catalogue ID:|Original catalogue:|Difficulty ranks can change/);
    assert.match(page.element('problem-meta').innerHTML, /Difficulty rank:<\/strong> 3 of 3/);
    assert.match(page.element('problem-meta').innerHTML, /economics\.html\?jel=C73/);
    assert.match(page.element('problem-meta').innerHTML, /C73<\/a> \(Stochastic and Dynamic Games - Evolutionary Games - Repeated Games\)/);
    assert.match(page.element('problem-links').innerHTML, /<h3>Definitions and assumptions<\/h3>/);
    assert.match(page.element('problem-links').innerHTML, /<h3>Formal question<\/h3>/);
    assert.match(page.element('problem-links').innerHTML, /\$x &lt; 1\$/);
    assert.match(page.element('problem-links').innerHTML, /data-tex-reference="problem:OP-0050"/);
    assert.match(page.element('problem-links').innerHTML, /Local references \[S1\]/);
    assert.equal(page.element('prev-problem').href, 'problem.html?type=economics&id=H41-4');
    assert.equal(page.element('next-problem').style.visibility, 'hidden');
    assert.match(page.element('problem-statement-source').innerHTML, /href="data\/economics\/statements\/C73-1\.tex" download="C73-1\.tex"/);
    for (const id of ['llm-attempts-section', 'comments', 'contribute-cta', 'other-llm-attacks']) {
        assert.equal(page.element(id).hidden, true);
    }
    assert.equal(page.createdScripts, 0, 'Embedded data needs neither fetch nor a script request');
    assert.equal(page.context.window.MathJax.tex.macros.E, '{\\mathbb{E}}');
    assert.equal(page.context.window.MathJax.tex.macros.argmin, '{\\operatorname*{arg\\,min}}');
    const targets = page.context.window.EconomicsDetail.referenceTargets(sample);
    assert.equal(targets.has('OP-0042'), false, 'Duplicate legacy IDs must not link arbitrarily');
    assert.equal(targets.has('problem:OP-0042'), false);
    assert.equal(targets.get('problem:OP-0050').id, 'H41-4');
    assert.equal(targets.get('game:GT-002').id, 'C73-2');
    const links = page.element('problem-links').references;
    assert.equal(links[0].href, '#economics-tex-label-1');
    assert.equal(links[1].href, 'problem.html?type=economics&id=H41-4');
    assert.equal(links[1].textContent, 'H41-4');
    assert.equal(links[2].href, undefined);
    assert.match(links[2].title, /no unique target/);
    assert.equal(links[3].href, undefined);
    assert.equal(links[3].textContent, 'audited crosswalk in the source catalogue');
    assert.equal(page.context.window.EconomicsDetail.normalizedReferences('\\JELref{H41}{OP-0050}'),
        '\\ref{jel:H41:OP-0050}');
    const normalize = page.context.window.EconomicsDetail.normalizedStatement;
    const metadata = normalize('\\entrymeta{SC-06}{Control and \\textbf{optimization}}{Research agenda}');
    const metadataHtml = page.context.formatTeX(metadata, false, false);
    assert.match(metadataHtml, /<strong><code>SC-06<\/code><\/strong>/);
    assert.match(metadataHtml, /Control and <strong>optimization<\/strong>/);
    assert.match(metadataHtml, /Research agenda/);
    assert.doesNotMatch(metadataHtml, /\\entrymeta/);
    const styled = normalize('{\\sffamily\\small\\color{muted}\\textbf{GT-001}\\par Status.\\par}');
    assert.doesNotMatch(styled, /sffamily|small|color|^\{|}$|raggedright/);
    assert.match(page.context.formatTeX(styled, false, false), /<strong>GT-001<\/strong>/);
    const math = '$ {\\color{red}a+b}^2 + {\\rm ext}_i $';
    assert.equal(normalize('\\footnotesize\\raggedright ' + math), math);
    assert.equal(normalize('\\hypertarget{definitions:source:1}{}Reference'),
        '\\label{definitions:source:1}Reference');
    assert.equal(normalize('Four-agent \\ensuremath{\\leq}9-good result'), 'Four-agent $\\leq$9-good result');
    assert.equal(normalize('(page~\\pageref{audited:conventions})'), '(\\ref{audited:conventions})');
    assert.equal(normalize('\\nolinkurl{10.1257/aer.20211319}'), '\\texttt{10.1257/aer.20211319}');
    const explicitReference = { ...sample, 'C73-1': { ...sample['C73-1'],
        reference_aliases: { 'problem:OP-0042': 'C73-2' } } };
    page = await render('?type=economics&id=C73-1', explicitReference);
    assert.equal(page.element('problem-links').references[2].href, 'problem.html?type=economics&id=C73-2');

    // A new ordering changes navigation and displayed rank while retaining every fixed route.
    const reordered = Object.fromEntries(Object.entries(sample).map(([id, record]) =>
        [id, { ...record, rank: 4 - record.rank }]));
    page = await render('?type=economics&id=C73-1', reordered);
    assert.doesNotMatch(page.element('problem-meta').innerHTML, /Problem ID:/);
    assert.match(page.element('problem-meta').innerHTML, /Difficulty rank:<\/strong> 1 of 3/);
    assert.equal(page.element('prev-problem').style.visibility, 'hidden');
    assert.equal(page.element('next-problem').href, 'problem.html?type=economics&id=H41-4');

    page = await render('?type=economics&id=C73-2', sample, true);
    assert.equal(page.createdScripts, 1);
    assert.equal(page.element('next-problem').href, 'problem.html?type=economics&id=H41-4');
    page = await render('?type=economics&id=C73-2', sample, true, false, 'data/economics_data.js?v=test');
    assert.equal(page.createdScripts, 1, 'The lazy loader uses the build-versioned data URL');
    page = await render('?type=economics&id=C73-2', sample, true, true);
    assert.match(page.element('problem-meta').innerHTML, /could not be loaded/);
    page = await render('?type=economics&id=__proto__');
    assert.match(page.element('problem-meta').innerHTML, /not found/);
    page = await render('?type=economics');
    assert.match(page.element('problem-meta').innerHTML, /not found/);
    console.log('Economics detail tests passed');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
