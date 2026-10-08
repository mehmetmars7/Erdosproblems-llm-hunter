/**
 * Problem Hunting with LLMs - Main Application JavaScript
 */

// Utility functions

/**
 * Get URL parameters
 */
function getUrlParams() {
    return new URLSearchParams(window.location.search);
}

/**
 * Update URL without page reload
 */
function updateUrl(params) {
    const url = new URL(window.location);
    for (const [key, value] of Object.entries(params)) {
        if (value === null || value === undefined || value === '') {
            url.searchParams.delete(key);
        } else {
            url.searchParams.set(key, value);
        }
    }
    window.history.replaceState({}, '', url);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    return String(text ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[character]);
}

/**
 * Format TeX content for display
 * Preserves LaTeX while making it HTML-safe
 */
function formatTeXContent(text) {
    if (!text) return '';

    // First, escape HTML entities
    let formatted = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Convert double newlines to paragraph breaks
    formatted = formatted.split(/\n\n+/).map(para => {
        return '<p>' + para.replace(/\n/g, '<br>') + '</p>';
    }).join('');

    return formatted;
}

/**
 * Trigger MathJax to re-render
 */
function renderMath() {
    if (typeof MathJax !== 'undefined' && MathJax.typesetPromise) {
        MathJax.typesetPromise().catch(function(err) {
            console.warn('MathJax typeset error:', err);
        });
    }
}

/**
 * Debounce function for search inputs
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Sort problems by number
 */
function sortByNumber(a, b) {
    const numA = parseInt(a.number || a.id) || 0;
    const numB = parseInt(b.number || b.id) || 0;
    return numA - numB;
}

/**
 * Sort problems by score (descending)
 */
function sortByScore(a, b) {
    return (b.score || 0) - (a.score || 0);
}

/**
 * Get unique models from attacks
 */
function getMathematicalAttempts(attacks) {
    return (attacks || []).filter(a => a.entry_kind !== 'statement_only' && a.entry_kind !== 'human_contribution');
}

// OpenAI partial results keep their scope visible. Other legacy partial
// attempts retain the existing unresolved label.
function getAttemptClaim(attack) {
    if (isPartialOpenAIClaim(attack)) return 'partial';
    if (isRelatedOpenAIClaim(attack)) return 'related';
    const status = String(attack.status || '').trim().toLowerCase();
    if (status === 'solved') return 'solved';
    if (status === 'partial' || status === 'unresolved') return 'unresolved';
    return /\b(?:unresolved|remains open|partial)\b/i.test(attack.raw || '') ? 'unresolved' : 'not stated';
}

function getOverallClaim(attacks) {
    const attempts = getMathematicalAttempts(attacks);
    if (attempts.some(isSolvedOpenAIClaim)) return 'solved';
    if (attempts.some(isPartialOpenAIClaim)) return 'partial';
    if (attempts.some(isRelatedOpenAIClaim)) return 'related';
    const claims = attempts.map(getAttemptClaim);
    if (!claims.length) return 'none';
    if (claims.includes('unresolved')) return 'unresolved';
    return claims.every(claim => claim === 'solved') ? 'solved' : 'not stated';
}

function getUniqueModels(attacks) {
    const attempts = getMathematicalAttempts(attacks);
    const authoredModels = new Set(attempts.filter(a => a.entry_kind !== 'reused_writeup').map(a => a.model));
    return [...new Set(attempts.flatMap(a => {
        if (a.entry_kind !== 'reused_writeup') return [a.model];
        const sourceModel = a.provenance.source_model.replace(/_/g, ' ');
        return authoredModels.has(a.model) ? [sourceModel] : [sourceModel, `${a.model} (collection)`];
    }))];
}

function getModelLabels(attacks) {
    const shorten = name => {
        if (/^openai$/i.test(name)) return 'openai';
        if (/gpt[ _]6[ _]astra[ _]ultra/i.test(name)) {
            return name.includes('(collection)') ? 'gpt 6 (collection)' : 'gpt 6';
        }
        if (/gpt[ _]pro/i.test(name)) return 'gpt pro';
        if (/gpt[ _]5\.2/i.test(name)) return 'gpt 5.2';
        if (/codex/i.test(name)) return 'codex';
        if (/claude|opus/i.test(name)) {
            return name.toLowerCase().replace(/_/g, ' ').replace(/^claude\s+(opus|sonnet|haiku)\b/, '$1');
        }
        if (/gemini/i.test(name)) return 'gemini';
        return name.toLowerCase();
    };
    return [...new Set(getUniqueModels(attacks).map(shorten))].sort((a, b) =>
        Number(b.startsWith('gpt 6')) - Number(a.startsWith('gpt 6')) || a.localeCompare(b)
    );
}

/**
 * Count problems with attacks
 */
function countWithAttacks(problems) {
    return Object.values(problems).filter(p => getMathematicalAttempts(p.attacks).length > 0).length;
}

/**
 * The ranked catalogue and the historical MathOverflow subset share one collection.
 * A catalogue status is source metadata, never evidence that an LLM solved a problem.
 */
function getOpenProblemCollection(problem) {
    return problem.collection === 'mo' ? 'mo' : 'ranked';
}

function getOpenProblemHref(problem) {
    if (getOpenProblemCollection(problem) === 'mo') {
        const id = problem.mo_id || String(problem.id).replace(/^mo:/, '');
        return `problem.html?type=mo&id=${encodeURIComponent(id)}`;
    }
    return `problem.html?type=open_problems&id=${encodeURIComponent(problem.id)}`;
}

function resolveOpenProblemId(problems, id) {
    if (Object.prototype.hasOwnProperty.call(problems, id)) return id;
    const matches = Object.values(problems).filter(problem =>
        Array.isArray(problem.legacy_ids) && problem.legacy_ids.includes(id));
    return matches.length === 1 ? String(matches[0].id) : id;
}

function getUnsolvedMathLink(problem, prefix = '') {
    if (getOpenProblemCollection(problem) === 'mo' || !problem.external_url) return '';
    const code = problem.problem_number;
    if (typeof code !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(code)) return '';
    const base = 'https://www.unsolvedmath.com/problems/';
    if (![base + code, base + problem.id].includes(problem.external_url)) return '';
    return `<a href="${escapeHtml(problem.external_url)}" target="_blank" rel="noopener noreferrer" title="UnsolvedMath ${escapeHtml(code)} (ID ${escapeHtml(problem.id)})">${escapeHtml(prefix + code)}</a>`;
}

function sortOpenProblems(a, b) {
    const aIsMO = getOpenProblemCollection(a) === 'mo';
    const bIsMO = getOpenProblemCollection(b) === 'mo';
    if (aIsMO !== bIsMO) return Number(aIsMO) - Number(bIsMO);
    if (aIsMO) return sortByScore(a, b) || String(a.id).localeCompare(String(b.id));
    const rankA = Number.isFinite(a.rank) ? a.rank : Infinity;
    const rankB = Number.isFinite(b.rank) ? b.rank : Infinity;
    return rankA - rankB || String(a.id).localeCompare(String(b.id));
}

function defaultOpenSortDirection(key) {
    return ['attempts', 'score', 'completion'].includes(key) ? 'desc' : 'asc';
}

function compareOpenProblems(a, b, key, direction) {
    const value = problem => {
        switch (key) {
            case 'rank': return problem.collection === 'mo' ? null : problem.rank;
            case 'title': return problem.title;
            case 'status': return getOpenProblemStatusLabel(problem);
            case 'review': return getReviewLabel(problem.review);
            case 'claim': return getOpenProblemClaim(problem);
            case 'completion': return getMathematicalAttempts(problem.attacks).length ? problem.completion : null;
            case 'attempts': return getMathematicalAttempts(problem.attacks).length;
            case 'score': return problem.score;
            case 'models': return getModelLabels(problem.attacks).join(', ');
            case 'source': return getOpenProblemSources(problem)[0]?.url;
            case 'unsolvedmath': return problem.external_url ? problem.problem_number : null;
        }
    };
    const x = value(a), y = value(b);
    const missing = value => value === null || value === undefined || value === '' ||
        (typeof value === 'number' && !Number.isFinite(value));
    // Empty cells remain last in either direction; ties retain catalogue order.
    if (missing(x) || missing(y)) return Number(missing(x)) - Number(missing(y)) || sortOpenProblems(a, b);
    const result = typeof x === 'number' && typeof y === 'number'
        ? x - y : String(x).localeCompare(String(y), undefined, { numeric: true, sensitivity: 'base' });
    return (direction === 'desc' ? -result : result) || sortOpenProblems(a, b);
}

function getOpenProblemDomains(problems) {
    const grouped = new Map();
    for (const problem of Object.values(problems)) {
        if (!problem.domain) continue;
        const label = problem.domain_label || problem.domain;
        const key = label.trim().toLowerCase();
        if (!grouped.has(key)) grouped.set(key, { label, counts: new Map() });
        const group = grouped.get(key);
        group.counts.set(problem.domain, (group.counts.get(problem.domain) || 0) + 1);
    }
    return [...grouped.values()].map(group => {
        // Prefer the most common source spelling, while retaining every alias for saved URLs.
        const aliases = [...group.counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([value]) => value);
        return { value: aliases[0], label: group.label, aliases };
    }).sort((a, b) => a.label.localeCompare(b.label));
}

function filterOpenProblems(problems, filters = {}) {
    const search = String(filters.search || '').trim().toLowerCase();
    const domainGroup = filters.domain && getOpenProblemDomains(problems).find(group => group.aliases.includes(filters.domain));
    const domainAliases = domainGroup ? domainGroup.aliases : [filters.domain];
    return Object.values(problems).filter(problem => {
        if (filters.source && getOpenProblemCollection(problem) !== filters.source) return false;
        if (filters.domain && !domainAliases.includes(problem.domain)) return false;
        if (filters.tag && !(problem.tags || []).includes(filters.tag)) return false;
        if (filters.withAttempts && !getMathematicalAttempts(problem.attacks).length) return false;
        if (!search) return true;
        const sourceText = (problem.sources || []).map(source => `${source.citation || ''} ${source.url || ''}`).join(' ');
        const openAITitles = (problem.attacks || []).flatMap(attack =>
            (attack.openai?.families || []).flatMap(family =>
                [family.title || '', ...(family.manuscripts || []).map(manuscript => manuscript.title || '')]));
        return [problem.id, problem.problem_number, problem.mo_id, problem.rank, problem.title, problem.exact_target,
            problem.definition_tex, problem.domain_label, ...(problem.aliases || []), ...(problem.tags || []),
            (problem.tags || []).includes('openai') ? 'OpenAI' : '', ...openAITitles, sourceText]
            .filter(value => value !== null && value !== undefined).join(' ').toLowerCase().includes(search);
    });
}

function getOpenProblemClaim(problem) {
    const attempts = getMathematicalAttempts(problem.attacks);
    if (!attempts.length) return 'no attempt';
    if (attempts.some(isSolvedOpenAIClaim)) return 'solved';
    if (attempts.some(isPartialOpenAIClaim)) return 'partial';
    if (attempts.some(isRelatedOpenAIClaim)) return 'related';
    if (problem.llm_status && problem.llm_status !== 'none') return problem.llm_status;
    return getOverallClaim(attempts);
}

function getOpenProblemStatus(problem) {
    const attempts = getMathematicalAttempts(problem.attacks);
    if (attempts.some(isSolvedOpenAIClaim)) return 'solved';
    const sourceStatus = problem.source_status ?? problem.status;
    if (attempts.some(isPartialOpenAIClaim) && sourceStatus !== 'solved') return 'partial';
    return problem.status || 'unreviewed';
}

function isOpenAIProblemStatus(problem) {
    const attempts = getMathematicalAttempts(problem.attacks);
    return attempts.some(isSolvedOpenAIClaim) ||
        (attempts.some(isPartialOpenAIClaim) && (problem.source_status ?? problem.status) !== 'solved');
}

function getOpenProblemStatusLabel(problem) {
    const status = getOpenProblemStatus(problem);
    const label = status === 'partial' ? 'partially solved' : String(status).replace(/_/g, ' ');
    return label + (isOpenAIProblemStatus(problem) ? ' (OpenAI claim)' : '');
}

function getOpenProblemSourceStatusLabel(problem) {
    return String(problem.source_status ?? problem.status ?? 'unreviewed').replace(/_/g, ' ');
}

function getOpenProblemSources(problem) {
    return (problem.sources || []).filter(source => /^https?:\/\//i.test(source.url || ''));
}

function isSolvedOpenAIClaim(attack) {
    return attack.entry_kind === 'external_claim' &&
        ['full', 'stronger'].includes(attack.openai?.match) && attack.status === 'solved';
}

function isPartialOpenAIClaim(attack) {
    return attack.entry_kind === 'external_claim' && attack.claimant === 'OpenAI' &&
        attack.openai?.match === 'partial';
}

function isRelatedOpenAIClaim(attack) {
    return attack.entry_kind === 'external_claim' && attack.claimant === 'OpenAI' &&
        attack.openai?.match === 'related';
}

// Only construct links to the reviewed snapshot. Reject traversal and URL
// syntax before encoding each path segment (including parentheses in titles).
function getOpenAIFileUrl(metadata, path, download = false) {
    const commit = 'adc7f1241b42e322a6451854ab7e4b4c146bf78a';
    if (metadata?.source_repo !== 'https://github.com/openai/math' || metadata.source_commit !== commit ||
        typeof path !== 'string' || /[\\%?#\u0000-\u001f\u007f]/.test(path) ||
        path.split('/').some(part => !part || part === '.' || part === '..')) return '';
    const knownPath = /^preprints\/[^/]+\/(?:[^/]+\.pdf|README\.md)$/.test(path) ||
        /^preprints\/[^/]+\/build\/(?:[^/]+\/)*[^/]+\.tex$/.test(path) ||
        /^lean\/docs\/\d{3}\.md$/.test(path) ||
        /^lean\/ComparatorChallenges\/[^/]+\.(?:lean|json)$/.test(path) ||
        /^reasoning_traces\/[^/]+\.pdf$/.test(path) || path === 'CONTENTS.md';
    if (!knownPath || (download && !path.endsWith('.pdf'))) return '';
    const encoded = path.split('/').map(part => encodeURIComponent(part)
        .replace(/[!'()*]/g, character => `%${character.charCodeAt(0).toString(16).toUpperCase()}`)).join('/');
    return `https://github.com/openai/math/${download ? 'raw' : 'blob'}/${commit}/${encoded}`;
}

function getOpenAIStatementUrl(metadata, manuscript, source) {
    if (!source || typeof source !== 'object' || Array.isArray(source) ||
        Object.keys(source).sort().join(',') !== 'label,line,path' ||
        !Number.isSafeInteger(source.line) || source.line < 1 ||
        typeof source.label !== 'string' || !source.label.trim() ||
        typeof source.path !== 'string' || typeof manuscript?.pdf_path !== 'string') return '';
    const folder = /^preprints\/([^/]+)\/[^/]+\.pdf$/.exec(manuscript.pdf_path)?.[1];
    if (!folder || !source.path.startsWith(`preprints/${folder}/build/`) || !source.path.endsWith('.tex')) return '';
    const url = getOpenAIFileUrl(metadata, source.path);
    return url ? `${url}#L${source.line}` : '';
}

function getOpenAIPaperTitles(attack) {
    return [...new Set((attack.openai?.families || []).flatMap(family =>
        (family.manuscripts || []).map(manuscript => manuscript.title)
            .filter(title => typeof title === 'string' && title.trim())))];
}

function getOpenAIMatchLabel(attack) {
    return {
        full: 'Full solution claimed for this problem',
        stronger: 'Stronger result claimed, covering this problem',
        partial: 'Partial solution claimed for this problem',
        related: 'Related result; no solution to this problem claimed'
    }[attack.openai?.match] || 'Scope not specified';
}

// Display the imported scope before external papers so readers can distinguish
// the catalogue question from the result they are about to open.
function splitOpenAIClaimContent(attack) {
    const raw = typeof attack.raw === 'string' ? attack.raw : '';
    const heading = /^[ \t]*\\subsection\*?\{Scope relative to this problem\}[ \t]*\r?$/m.exec(raw);
    if (!heading) return { scope: '', raw };
    const bodyStart = heading.index + heading[0].length;
    const remainder = raw.slice(bodyStart);
    const next = /^[ \t]*\\(?:subsection|section)\*?\{|^[ \t]*\\end\{document\}/m.exec(remainder);
    const bodyEnd = next ? bodyStart + next.index : raw.length;
    return { scope: raw.slice(bodyStart, bodyEnd).trim(),
        raw: raw.slice(0, heading.index) + raw.slice(bodyEnd) };
}

function renderOpenAIProvenance(attack) {
    const metadata = attack.openai;
    if (!metadata) return '';
    const externalLink = (url, label) => {
        return url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>` : '';
    };
    const link = (path, label, download = false) => externalLink(getOpenAIFileUrl(metadata, path, download), label);
    const families = (metadata.families || []).map(family => {
        const papers = (family.manuscripts || []).map(manuscript => {
            const links = [link(manuscript.pdf_path, 'PDF'), link(manuscript.pdf_path, 'PDF (download)', true),
                link(manuscript.readme_path, 'Manuscript page')].filter(Boolean);
            if (Array.isArray(manuscript.statement_sources)) {
                links.push(...manuscript.statement_sources.map(source =>
                    externalLink(getOpenAIStatementUrl(metadata, manuscript, source), `Statement: ${source?.label || ''}`)
                ).filter(Boolean));
            }
            const date = /^\d{4}-\d{2}-\d{2}$/.test(manuscript.date || '') ? ` (${manuscript.date})` : '';
            return `<li><strong>Paper: ${escapeHtml(manuscript.title || 'Manuscript')}</strong>${escapeHtml(date)}: ${links.join(' · ')}</li>`;
        }).join('');
        const lean = family.lean;
        const leanLinks = lean ? [link(lean.doc_path, 'Lean scope'),
            ...(lean.comparators || []).map(path => link(path, `Comparator: ${String(path).split('/').pop()}`))].filter(Boolean) : [];
        const additionalLinks = [...leanLinks, link(family.reasoning_trace, 'Reasoning summary'),
            link('CONTENTS.md', 'Catalogue entry')].filter(Boolean);
        return `<li>OpenAI catalogue family: ${escapeHtml(family.title || `Family ${family.family}`)}` +
            `${papers ? `<ul>${papers}</ul>` : ''}${additionalLinks.length ? `<p>${additionalLinks.join(' · ')}</p>` : ''}</li>`;
    }).join('');
    return `<div class="status-note"><p><strong>Relationship to this problem:</strong> ${escapeHtml(getOpenAIMatchLabel(attack))}.</p>` +
        '<p>OpenAI produced these results with an internal model. ' +
        'Unformalised results may contain errors. This claim has not been independently verified here, ' +
        'and this site has not run the Lean code. Links refer to the pinned release snapshot.</p>' +
        `${families ? `<ul>${families}</ul>` : ''}</div>`;
}

function renderOpenProblemRows(problems) {
    if (!problems.length) return '<tr><td colspan="9">No problems match these filters.</td></tr>';
    return problems.map(problem => {
        const isMO = getOpenProblemCollection(problem) === 'mo';
        const rank = !isMO && Number.isFinite(problem.rank) ? problem.rank : '—';
        const attempts = getMathematicalAttempts(problem.attacks);
        const labels = getModelLabels(problem.attacks);
        const sourceLabel = isMO ? 'MathOverflow subset' : 'Ranked catalogue';
        const metadata = [problem.domain_label, sourceLabel,
            (problem.tags || []).includes('openai') ? 'OpenAI' : '',
            isMO && Number.isFinite(problem.score) ? `MO score: ${problem.score}` : ''].filter(Boolean).join(' · ');
        const claimLabel = getOpenProblemClaim(problem) +
            (problem.llm_status_source === 'openai_claim' ||
                attempts.some(attack => isSolvedOpenAIClaim(attack) || isPartialOpenAIClaim(attack)) ? ' · OpenAI' : '');
        const reviewed = problem.status_reviewed_at
            ? `<span class="catalogue-meta">${isOpenAIProblemStatus(problem) ? 'Source reviewed' : 'Reviewed'} ${escapeHtml(String(problem.status_reviewed_at).slice(0, 10))}</span>` : '';
        const sourceStatus = attempts.some(attack => isSolvedOpenAIClaim(attack) || isPartialOpenAIClaim(attack))
            ? `<span class="catalogue-meta">Source catalogue: ${escapeHtml(getOpenProblemSourceStatusLabel(problem))}</span>` : '';
        const qualification = problem.status_qualification
            ? ` title="${escapeHtml(problem.status_qualification)}"` : '';
        const reviewHandles = getReviewHandles(problem.review);
        const reviewTitle = reviewHandles.length ? ` title="${escapeHtml(`Reviewed by ${reviewHandles.map(handle => `@${handle}`).join(', ')}`)}"` : '';
        const source = getOpenProblemSources(problem)[0];
        const sourceLink = source
            ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener" title="${escapeHtml(source.citation || 'Original source')}">Source</a>` : '—';
        const externalLink = getUnsolvedMathLink(problem);
        return `<tr>
            <td>${rank}</td>
            <td class="catalogue-problem"><a href="${escapeHtml(getOpenProblemHref(problem))}">${escapeHtml(problem.title || problem.id)}</a><span class="catalogue-meta">${escapeHtml(metadata)}</span></td>
            <td${qualification}>${escapeHtml(getOpenProblemStatusLabel(problem))}${sourceStatus}${reviewed}</td>
            <td class="${escapeHtml(getReviewClass(problem.review))}"${reviewTitle}>${escapeHtml(getReviewLabel(problem.review))}</td>
            <td class="claim-status"><a href="${escapeHtml(getOpenProblemHref(problem))}">${escapeHtml(claimLabel)}</a><span class="catalogue-meta">${attempts.length} attempt${attempts.length === 1 ? '' : 's'}</span></td>
            <td>${attempts.length ? escapeHtml(formatCompletion(problem.completion)) || '—' : '—'}</td>
            <td>${labels.length ? labels.map(escapeHtml).join(', ') : '—'}</td>
            <td>${sourceLink}</td>
            <td>${externalLink}</td>
        </tr>`;
    }).join('');
}

/**
 * Show examples from both collections; the MO subset is already included in openProblems.
 */
function getAttemptPreview(erdos, openProblems, limit = 10) {
    const erdosRows = Object.values(erdos || {}).filter(problem => getMathematicalAttempts(problem.attacks).length)
        .sort(sortByNumber).map(problem => ({
            href: `problem.html?type=erdos&id=${encodeURIComponent(problem.number || problem.id)}`,
            label: `Erdos Problem #${problem.number || problem.id}`,
            count: getMathematicalAttempts(problem.attacks).length
        }));
    const openRows = Object.values(openProblems || {}).filter(problem => getMathematicalAttempts(problem.attacks).length)
        .sort(sortOpenProblems).map(problem => ({
            href: getOpenProblemHref(problem),
            label: `${getOpenProblemCollection(problem) === 'mo' ? 'MathOverflow' : 'Top Open Problem'}: ${problem.title || problem.id}`,
            count: getMathematicalAttempts(problem.attacks).length
        }));
    const result = [];
    for (let i = 0; result.length < limit && (i < erdosRows.length || i < openRows.length); i++) {
        if (erdosRows[i]) result.push(erdosRows[i]);
        if (openRows[i] && result.length < limit) result.push(openRows[i]);
    }
    return result;
}

function initOpenProblemsPage() {
    const tbody = document.getElementById('open-problems-tbody');
    if (!tbody) return;
    const catalogue = window.OPEN_PROBLEMS_DATA;
    const count = document.getElementById('results-count');
    if (!catalogue) {
        tbody.innerHTML = '<tr><td colspan="9">Unable to load the problem catalogue.</td></tr>';
        count.textContent = 'Catalogue unavailable';
        return;
    }
    const subset = document.body.dataset.collection === 'mo';
    const search = document.getElementById('search');
    const domains = document.getElementById('filter-domain');
    const tags = document.getElementById('filter-tag');
    const sources = document.getElementById('filter-source');
    const attempts = document.getElementById('filter-attacks');
    const sort = document.getElementById('sort-by');
    const params = getUrlParams();
    const records = Object.values(catalogue).filter(problem => !subset || getOpenProblemCollection(problem) === 'mo');
    const domainOptions = getOpenProblemDomains(records);
    domains.innerHTML = '<option value="">All domains</option>' + domainOptions
        .map(({ value, label }) => `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`).join('');
    search.value = params.get('q') || '';
    domains.value = domainOptions.find(group => group.aliases.includes(params.get('domain')))?.value || '';
    if (tags) tags.value = params.get('tag') === 'openai' ? 'openai' : '';
    sources.value = subset ? 'mo' : ['ranked', 'mo'].includes(params.get('source')) ? params.get('source') : '';
    attempts.checked = params.get('attempts') === '1';
    const validSorts = ['rank', 'title', 'attempts', 'score', 'status', 'review', 'claim', 'completion', 'models', 'source', 'unsolvedmath'];
    sort.value = validSorts.includes(params.get('sort')) ? params.get('sort') : subset ? 'score' : 'rank';
    let direction = ['asc', 'desc'].includes(params.get('dir')) ? params.get('dir') : defaultOpenSortDirection(sort.value);
    const sortButtons = Array.from(document.querySelectorAll('[data-sort]'));

    function renderTable(syncUrl = true) {
        const filtered = filterOpenProblems(records, {
            search: search.value, domain: domains.value, tag: tags?.value || '',
            source: sources.value, withAttempts: attempts.checked
        });
        filtered.sort((a, b) => compareOpenProblems(a, b, sort.value, direction));
        sortButtons.forEach(button => {
            const active = button.dataset.sort === sort.value;
            button.closest('th').setAttribute('aria-sort', active ? (direction === 'asc' ? 'ascending' : 'descending') : 'none');
            button.querySelector('.sort-indicator').textContent = active ? (direction === 'asc' ? '↑' : '↓') : '⇅';
        });
        if (typeof MathJax !== 'undefined' && MathJax.typesetClear) MathJax.typesetClear([tbody]);
        tbody.innerHTML = renderOpenProblemRows(filtered);
        count.textContent = `${filtered.length} of ${records.length} entries · ${countWithAttacks(filtered)} with LLM attempts`;
        if (syncUrl) updateUrl({ q: search.value.trim(), domain: domains.value, tag: tags?.value || null,
            source: subset ? null : sources.value,
            attempts: attempts.checked ? '1' : null, sort: sort.value === (subset ? 'score' : 'rank') ? null : sort.value,
            dir: direction === defaultOpenSortDirection(sort.value) ? null : direction });
        renderMath();
    }
    search.addEventListener('input', debounce(() => renderTable(), 200));
    [domains, tags, sources, attempts].filter(Boolean).forEach(input => input.addEventListener('change', () => renderTable()));
    sort.addEventListener('change', () => {
        direction = defaultOpenSortDirection(sort.value);
        renderTable();
    });
    sortButtons.forEach(button => button.addEventListener('click', () => {
        direction = sort.value === button.dataset.sort && direction === 'asc' ? 'desc' : 'asc';
        sort.value = button.dataset.sort;
        renderTable();
    }));
    document.getElementById('reset-filters').addEventListener('click', () => {
        search.value = '';
        domains.value = '';
        if (tags) tags.value = '';
        sources.value = subset ? 'mo' : '';
        attempts.checked = false;
        sort.value = subset ? 'score' : 'rank';
        direction = defaultOpenSortDirection(sort.value);
        renderTable();
    });
    renderTable(false);
}

/**
 * Format date string
 */
function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch {
        return dateStr;
    }
}

/**
 * Get status class for styling
 */
function getStatusClass(status) {
    switch (status?.toLowerCase()) {
        case 'solved':
            return 'status-solved';
        case 'partial':
            return 'status-partial';
        case 'unresolved':
            return 'status-unresolved';
        default:
            return '';
    }
}

/**
 * Theme handling
 */
function getStoredTheme() {
    try {
        return localStorage.getItem('theme');
    } catch {
        return null;
    }
}

function getPreferredTheme() {
    const stored = getStoredTheme();
    if (stored === 'light' || stored === 'dark') return stored;
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
    }
    return 'light';
}

function updateThemeToggle(theme) {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;
    toggle.textContent = theme === 'dark' ? 'Dark' : 'Light';
    toggle.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
    toggle.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`);
}

function updateGiscusTheme(theme) {
    const frame = document.querySelector('iframe.giscus-frame');
    if (!frame || !frame.contentWindow) return;
    frame.contentWindow.postMessage(
        { giscus: { setConfig: { theme: theme === 'dark' ? 'dark' : 'light' } } },
        'https://giscus.app'
    );
}

function applyTheme(theme, persist) {
    const nextTheme = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', nextTheme);
    if (persist) {
        try {
            localStorage.setItem('theme', nextTheme);
        } catch {
            // Ignore storage errors
        }
    }
    updateThemeToggle(nextTheme);
    updateGiscusTheme(nextTheme);
}

function initThemeToggle() {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;

    const initialTheme = getPreferredTheme();
    applyTheme(initialTheme, false);

    toggle.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next, true);
    });

    if (window.matchMedia) {
        const media = window.matchMedia('(prefers-color-scheme: dark)');
        if (media.addEventListener) {
            media.addEventListener('change', (event) => {
                if (getStoredTheme()) return;
                applyTheme(event.matches ? 'dark' : 'light', false);
            });
        }
    }
}

/**
 * Get review label for display
 */
function getReviewLabel(review) {
    const status = (review && review.status ? review.status : '').toLowerCase();
    switch (status) {
        case 'submitted':
            return review.submission_role === 'authors' ? 'submitted by authors' : 'submitted';
        case 'flagged':
        case 'incorrect':
        case 'known':
        case 'technicality':
        case 'trivial':
        case 'partial':
        case 'plausible':
        case 'accepted':
            return status;
        default:
            return 'unreviewed';
    }
}

/**
 * Get review class for styling
 */
function getReviewClass(review) {
    if (!review || !review.status) return 'review-unreviewed';
    return `review-${review.status.toLowerCase()}`;
}

function normalizeReviewHandle(handle) {
    if (handle === null || handle === undefined) return '';
    let cleaned = String(handle).trim();
    if (!cleaned) return '';
    if (cleaned.startsWith('@')) cleaned = cleaned.slice(1);
    cleaned = cleaned.replace(/[^A-Za-z0-9-]/g, '');
    return cleaned;
}

function getReviewHandles(review) {
    if (!review) return [];
    const raw = review.status === 'submitted' ? review.submitted_by : review.reviewed_by;
    if (!raw) return [];
    let items = [];
    if (Array.isArray(raw)) {
        items = raw;
    } else if (raw !== null && raw !== undefined) {
        const text = String(raw).trim();
        if (text) items = text.split(',');
    }

    const handles = [];
    const seen = new Set();
    items.forEach((item) => {
        const normalized = normalizeReviewHandle(item);
        if (!normalized) return;
        const key = normalized.toLowerCase();
        if (seen.has(key)) return;
        seen.add(key);
        handles.push(normalized);
    });
    return handles;
}

function formatReviewHandles(review) {
    const handles = getReviewHandles(review);
    if (handles.length === 0) return '';
    return handles.map((handle) => `@${handle}`).join(', ');
}

function formatReviewHandleLinks(review) {
    const handles = getReviewHandles(review);
    if (handles.length === 0) return '';
    return handles
        .map((handle) => `<a href="https://github.com/${handle}" target="_blank" rel="noopener">@${handle}</a>`)
        .join(', ');
}

/**
 * Format completion percentage for display.
 */
function formatCompletion(value) {
    if (value === null || value === undefined) return '';
    const num = Number(value);
    if (!Number.isFinite(num)) return '';
    const rounded = Math.round(num * 10) / 10;
    if (Math.abs(rounded - Math.round(rounded)) < 1e-9) {
        return `${Math.round(rounded)}%`;
    }
    return `${rounded}%`;
}

/**
 * Keep the database's mathematical status separate from claims by LLMs.
 */
function getProblemStatus(problem) {
    return problem.status || 'not available';
}

function getProblemStatusClass(problem) {
    return problem.is_solved ? 'problem-status-solved' : 'problem-status-open';
}

function getCompletionSourceLabel(problem) {
    if (!formatCompletion(problem.completion)) return '';
    if (problem.completion_source === 'database') return 'Resolved in Tao\'s database';
    if (!getMathematicalAttempts(problem.attacks).length &&
        (problem.attacks || []).some(a => a.entry_kind === 'statement_only')) {
        return 'Statement only; awaiting a mathematical attempt';
    }
    return 'LLM estimate';
}

function formatStatusSync(sync) {
    if (!sync || !sync.checked_at) return '';
    const checkedDate = escapeHtml(String(sync.checked_at).slice(0, 10));
    const commit = /^[a-f0-9]{40}$/i.test(sync.source_commit || '') ? sync.source_commit : '';
    const sourceUrl = commit
        ? `https://github.com/teorth/erdosproblems/commit/${commit}`
        : 'https://github.com/teorth/erdosproblems';
    return `Problem status and formalization data checked ${checkedDate} against ` +
        `<a href="${sourceUrl}" target="_blank" rel="noopener">Tao's database${commit ? ` (${commit.slice(0, 7)})` : ''}</a>.`;
}

function formatFormalization(formalization, label) {
    if (!formalization || !formalization.state) return '';
    const stateLabel = { yes: 'formalized', no: 'not formalized', unformalized: 'not formalized' };
    let state = escapeHtml(stateLabel[formalization.state] || formalization.state);
    if (formalization.url && /^https?:\/\//i.test(formalization.url)) {
        const url = escapeHtml(formalization.url).replace(/"/g, '&quot;');
        state = `<a href="${url}" target="_blank" rel="noopener">${state}</a>`;
    }
    return `<li><strong>${escapeHtml(label)} formalization:</strong> ${state}</li>`;
}

/**
 * Initialize collapsible sections
 */
function initCollapsibles() {
    document.querySelectorAll('.collapsible-header').forEach(header => {
        header.addEventListener('click', () => {
            const content = header.nextElementSibling;
            if (content && content.classList.contains('collapsible-content')) {
                content.classList.toggle('collapsed');
                header.classList.toggle('expanded');
            }
        });
    });
}

/**
 * Smooth scroll to element
 */
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (err) {
        console.error('Failed to copy:', err);
        return false;
    }
}

/**
 * Show a temporary message
 */
function showMessage(message, duration = 3000) {
    const existing = document.querySelector('.temp-message');
    if (existing) existing.remove();

    const div = document.createElement('div');
    div.className = 'temp-message';
    div.textContent = message;
    div.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 10px 20px;
        background: #333;
        color: white;
        border-radius: 4px;
        z-index: 1000;
    `;
    document.body.appendChild(div);

    setTimeout(() => div.remove(), duration);
}

// Export for use in other scripts
window.ProblemHunting = {
    getUrlParams,
    updateUrl,
    escapeHtml,
    formatTeXContent,
    renderMath,
    debounce,
    sortByNumber,
    sortByScore,
    getUniqueModels,
    getModelLabels,
    getMathematicalAttempts,
    getAttemptClaim,
    getOverallClaim,
    countWithAttacks,
    getOpenProblemCollection,
    getOpenProblemHref,
    resolveOpenProblemId,
    getUnsolvedMathLink,
    sortOpenProblems,
    compareOpenProblems,
    getOpenProblemDomains,
    filterOpenProblems,
    getOpenProblemClaim,
    getOpenProblemStatus,
    getOpenProblemStatusLabel,
    getOpenProblemSourceStatusLabel,
    getOpenProblemSources,
    isSolvedOpenAIClaim,
    isPartialOpenAIClaim,
    isRelatedOpenAIClaim,
    getOpenAIFileUrl,
    getOpenAIStatementUrl,
    getOpenAIPaperTitles,
    getOpenAIMatchLabel,
    splitOpenAIClaimContent,
    renderOpenAIProvenance,
    renderOpenProblemRows,
    getAttemptPreview,
    initOpenProblemsPage,
    formatDate,
    getStatusClass,
    getReviewLabel,
    getReviewClass,
    getReviewHandles,
    formatReviewHandles,
    formatReviewHandleLinks,
    formatCompletion,
    getProblemStatus,
    getProblemStatusClass,
    getCompletionSourceLabel,
    formatStatusSync,
    formatFormalization,
    initThemeToggle,
    initCollapsibles,
    scrollToElement,
    copyToClipboard,
    showMessage
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    initThemeToggle();
    initCollapsibles();
    initOpenProblemsPage();
});
