// Economics statements and attempts share the site's TeX renderer and status labels.
(function () {
    'use strict';

    const fixedId = /^[A-Z]\d{2}-[1-9]\d*$/;
    let dataPromise;

    function escapeHtml(value) {
        return String(value == null ? '' : value).replace(/[&<>"']/g, character => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        })[character]);
    }

    function problemUrl(id) {
        return 'problem.html?type=economics&id=' + encodeURIComponent(id);
    }

    function loadData() {
        if (window.ECONOMICS_DATA) return Promise.resolve(window.ECONOMICS_DATA);
        if (!dataPromise) {
            // A script works in the downloadable site's file:// preview as well as on GitHub Pages.
            dataPromise = new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = document.getElementById('economics-detail-script')?.dataset?.economicsSrc ||
                    'data/economics_data.js';
                script.onload = () => window.ECONOMICS_DATA
                    ? resolve(window.ECONOMICS_DATA)
                    : reject(new Error('Economics data is missing'));
                script.onerror = () => reject(new Error('Economics data could not be loaded'));
                document.head.appendChild(script);
            });
        }
        return dataPromise;
    }

    function orderedProblems(data) {
        return Object.values(data).filter(problem => problem && fixedId.test(problem.id))
            .sort((a, b) => {
                const rankA = Number.isSafeInteger(a.rank) ? a.rank : Infinity;
                const rankB = Number.isSafeInteger(b.rank) ? b.rank : Infinity;
                return rankA - rankB || a.id.localeCompare(b.id);
            });
    }

    function referenceKey(node) {
        return (node.dataset.texScope || '0') + ':' + (node.dataset.texLabel || node.dataset.texReference);
    }

    function referenceTargets(data) {
        const candidates = new Map();
        function add(key, problem) {
            if (!key) return;
            if (!candidates.has(key)) candidates.set(key, new Map());
            candidates.get(key).set(problem.id, problem);
        }
        for (const problem of Object.values(data)) {
            if (!problem || !fixedId.test(problem.id)) continue;
            add(problem.id, problem);
            if (problem.source_id) {
                add(problem.source_id, problem);
                add('problem:' + problem.source_id, problem);
                add('jel:' + (problem.source_jel_code || problem.jel_code) + ':' + problem.source_id, problem);
            }
            for (const key of problem.source_labels || []) add(key, problem);
            const text = String(problem.definition_tex || '').replace(/^[ \t]*%[^\r\n]*/gm, '');
            for (const match of text.matchAll(/\\label\{([^}]+)\}/g)) {
                // A bare JEL classification repeats across entries; it is only a local target.
                if (!/^[A-Z]\d{2}$/.test(match[1]) && !/^difficulty-rank:/.test(match[1])) {
                    add(match[1], problem);
                }
            }
        }
        return new Map([...candidates].filter(([, records]) => records.size === 1)
            .map(([key, records]) => [key, records.values().next().value]));
    }

    function initReferences(container, data, problem, prefix = 'economics-tex-label-') {
        const localTargets = new Map();
        container.querySelectorAll('.tex-label').forEach((label, index) => {
            label.id = prefix + (index + 1);
            label.tabIndex = -1;
            localTargets.set(referenceKey(label), label);
        });
        const crossTargets = referenceTargets(data);
        container.querySelectorAll('.tex-reference').forEach(link => {
            const local = localTargets.get(referenceKey(link));
            if (local) {
                link.href = '#' + local.id;
                link.title = 'View ' + link.dataset.texReference + ' in this statement';
                if (link.dataset.texReference === 'audited:conventions') {
                    link.textContent = 'additional-source conventions below';
                }
                return;
            }
            const explicitId = problem.reference_aliases?.[link.dataset.texReference];
            const target = link.dataset.texReferenceKind !== 'eqref'
                ? (explicitId && Object.prototype.hasOwnProperty.call(data, explicitId) ? data[explicitId]
                    : crossTargets.get(link.dataset.texReference)) : null;
            if (target) {
                link.href = problemUrl(target.id);
                link.title = 'View ' + target.id + ': ' + (target.title || '');
                link.textContent = target.id;
            } else {
                link.removeAttribute('href');
                if (link.dataset.texReference === 'app:audited-crosswalk') {
                    link.textContent = 'audited crosswalk in the source catalogue';
                    link.title = 'This appendix belongs to the supplied merged catalogue';
                } else {
                    if (/^problem:OP-\d+$/.test(link.dataset.texReference)) {
                        link.textContent = link.dataset.texReference.slice('problem:'.length) + ' (source reference)';
                    }
                    link.title = 'Source reference ' + link.dataset.texReference + ': no unique target in this catalogue';
                }
            }
        });
    }

    function normalizedReferences(text) {
        return String(text || '')
            .replace(/\\Problemref\{([^}]+)\}/g, '\\ref{problem:$1}')
            .replace(/\\JELref\{([^}]+)\}\{([^}]+)\}/g, '\\ref{jel:$1:$2}');
    }

    function bracedGroup(text, start) {
        while (/\s/.test(text[start] || '') && start < text.length) start += 1;
        if (text[start] !== '{') return null;
        let depth = 1;
        for (let end = start + 1; end < text.length; end += 1) {
            if (text[end] === '\\') { end += 1; continue; }
            if (text[end] === '{') depth += 1;
            if (text[end] === '}' && --depth === 0) {
                return { content: text.slice(start + 1, end), end: end + 1 };
            }
        }
        return null;
    }

    function replaceCommand(text, name, arity, renderCommand) {
        const pattern = new RegExp('\\\\' + name + '(?![A-Za-z])', 'g');
        let output = '', cursor = 0, match;
        while ((match = pattern.exec(text))) {
            const args = [];
            let end = pattern.lastIndex;
            for (let index = 0; index < arity; index += 1) {
                const group = bracedGroup(text, end);
                if (!group) break;
                args.push(group.content);
                end = group.end;
            }
            if (args.length !== arity) continue;
            output += text.slice(cursor, match.index) + renderCommand(...args);
            cursor = end;
            pattern.lastIndex = end;
        }
        return output + text.slice(cursor);
    }

    function normalizedStatement(text) {
        const protectedFragments = [];
        const protect = fragment => {
            protectedFragments.push(fragment);
            return '\uE110ECON' + (protectedFragments.length - 1) + '\uE111';
        };
        // PDF presentation commands are prose metadata. Keep every mathematical
        // expression and literal source example intact while unwrapping that metadata.
        let source = String(text || '')
            .replace(/\\begin\{(verbatim\*?|Verbatim|Code)\}(?:\[[^\]]*\])?[\s\S]*?\\end\{\1\}/g, protect)
            .replace(/\\verb\*?([^\w\s])([^\n]*?)\1/g, protect)
            .replace(/\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|(?<!\\)\$\$[\s\S]*?(?<!\\)\$\$|(?<!\\)\$(?!\$)(?:\\[\s\S]|[^$\\])*?\$|\\begin\{((?:equation|align|alignat|gather|multline|flalign|eqnarray|math|displaymath)\*?)\}[\s\S]*?\\end\{\1\}/g, protect);
        source = replaceCommand(source, 'ensuremath', 1, content => protect('$' + content + '$'));
        function unwrapStyles(input) {
            let output = '';
            for (let index = 0; index < input.length; index += 1) {
                if (input[index] === '{' && input[index - 1] !== '\\' &&
                        /^\s*\\(?:sffamily|rmfamily|small|footnotesize|scriptsize|normalsize|large|Large|raggedright|color)\b/.test(input.slice(index + 1))) {
                    const group = bracedGroup(input, index);
                    if (group) {
                        output += unwrapStyles(group.content);
                        index = group.end - 1;
                        continue;
                    }
                }
                output += input[index];
            }
            return output;
        }
        source = unwrapStyles(source)
            .replace(/\\(?:sffamily|rmfamily|raggedright|footnotesize|scriptsize|tiny|small|normalsize|large|Large|LARGE|huge|Huge|bfseries|mdseries|upshape|itshape|scshape|phantomsection)\b[ \t]*/g, '')
            .replace(/\\color\{[^}]+\}[ \t]*/g, '');
        source = replaceCommand(source, 'entrymeta', 3, (id, subject, status) =>
            '\\textbf{\\texttt{' + id + '}}\\quad|\\quad ' + subject + '\\par ' + status + '\\par');
        source = replaceCommand(source, 'hypertarget', 2, (key, caption) => '\\label{' + key + '}' + caption);
        source = replaceCommand(source, 'nolinkurl', 1, content => '\\texttt{' + content + '}');
        source = source.replace(/(?:page\s*~?\s*)?\\pageref\{([^}]+)\}/g, '\\ref{$1}')
            // The source double-escaped an ampersand in this journal's prose name.
            .replace(/\\textbackslash\{\}(?=\\&)/g, '');
        source = normalizedReferences(source);
        return source.replace(/\uE110ECON(\d+)\uE111/g, (match, index) => protectedFragments[Number(index)]);
    }

    async function render(id) {
        for (const section of ['llm-attempts-section', 'comments', 'contribute-cta', 'other-llm-attacks']) {
            document.getElementById(section).hidden = true;
        }
        const previous = document.getElementById('prev-problem');
        const next = document.getElementById('next-problem');
        previous.style.visibility = 'hidden';
        next.style.visibility = 'hidden';
        const metadata = document.getElementById('problem-meta');
        const title = document.getElementById('page-title');
        title.textContent = 'Economics';
        document.title = 'Economics Problem - Erdos Problems LLM Hunter (beta)';
        metadata.innerHTML = '<p>Loading Economics statement…</p>';

        let data;
        try {
            data = await loadData();
        } catch (error) {
            metadata.innerHTML = '<p>The Economics data could not be loaded. <a href="economics.html">Return to Economics</a>.</p>';
            return;
        }
        if (!id || !fixedId.test(id) || !Object.prototype.hasOwnProperty.call(data, id)) {
            metadata.innerHTML = '<p>Economics problem not found. <a href="economics.html">Browse Economics problems</a>.</p>';
            return;
        }
        const problem = data[id];
        const shared = window.ProblemHunting;
        const jelDescription = window.ECONOMICS_JEL_LABELS?.[problem.jel_code] || '';
        const ordered = orderedProblems(data);
        const currentIndex = ordered.findIndex(record => record.id === id);
        title.textContent = problem.title;
        document.title = problem.title + ' (' + problem.id + ') - Economics';
        metadata.innerHTML = '<p><a href="economics.html">&larr; Economics</a></p>' +
            '<p><strong>JEL code:</strong> <a href="economics.html?jel=' + encodeURIComponent(problem.jel_code) + '">' + escapeHtml(problem.jel_code) + '</a>' +
                (jelDescription ? ' (' + escapeHtml(jelDescription) + ')' : '') + '</p>' +
            '<p><strong>Rank:</strong> ' + escapeHtml(problem.rank) + '</p>' +
            '<p><strong>Problem Status:</strong> ' + escapeHtml(shared.getOpenProblemStatusLabel({ ...problem, status: problem.status || 'open' })) + '</p>' +
            '<p><strong>LLM Claim:</strong> ' + escapeHtml(shared.getOpenProblemClaimLabel(problem)) + '</p>' +
            '<p><strong>Community Review:</strong> ' + escapeHtml(shared.getReviewLabel(problem.review)) + '</p>';
        const statement = document.getElementById('problem-links');
        statement.innerHTML = '<div class="problem-statement-text tex-content">' + formatTeX(normalizedStatement(problem.definition_tex), false, false) + '</div>';
        const statementUrl = problem.statement_url || '';
        if (statementUrl === 'data/economics/statements/' + problem.id + '.tex') {
            document.getElementById('problem-statement-source').innerHTML =
                '<a href="' + escapeHtml(statementUrl) + '" download="' + escapeHtml(problem.id) + '.tex">Download statement TeX</a>';
        }
        if (currentIndex > 0) {
            previous.href = problemUrl(ordered[currentIndex - 1].id);
            previous.style.visibility = 'visible';
        }
        if (currentIndex >= 0 && currentIndex < ordered.length - 1) {
            next.href = problemUrl(ordered[currentIndex + 1].id);
            next.style.visibility = 'visible';
        }
        initReferences(statement, data, problem);
        const attempts = shared.sortAttemptsNewestFirst(problem.attacks || []);
        const attemptsSection = document.getElementById('llm-attempts-section');
        const attemptsContainer = document.getElementById('attempts-container');
        if (attempts.length) {
            attemptsSection.hidden = false;
            attemptsSection.style.display = '';
            attemptsContainer.innerHTML = attempts.map((attack, index) => {
                const version = Number.isSafeInteger(attack.version) ? attack.version : 1;
                const filename = problem.id + (version > 1 ? '_v' + version : '') + '.tex';
                const download = attack.download_url || '';
                const safeDownload = /^data\/economics\/attempts\/[a-zA-Z0-9_-]+\/[A-Z]\d{2}-[1-9]\d*(?:_v[1-9]\d*)?\.tex$/.test(download);
                const source = attack.file_path && /^attacks\/open_problems\/economics\/[a-zA-Z0-9_-]+\/[A-Z]\d{2}-[1-9]\d*(?:_v[1-9]\d*)?\.tex$/.test(attack.file_path)
                    ? 'https://github.com/mehmetmars7/Erdosproblems-llm-hunter/blob/main/' + attack.file_path : '';
                // Repeated equation and source labels belong to their own version.
                const content = formatTeX(normalizedStatement(attack.raw), false, false)
                    .replace(/data-tex-scope="0"/g, 'data-tex-scope="attempt-' + (index + 1) + '"');
                return '<div class="attempt"><div class="attempt-header"><h3>' +
                    escapeHtml((attack.model || '').replace(/_/g, ' ')) + ' (v' + version + ')</h3>' +
                    '<span class="status-text">' + escapeHtml(shared.getAttemptClaim(attack)) + '</span>' +
                    ' <a href="#comments">comments</a>' +
                    (source ? ' <a href="' + escapeHtml(source) + '" target="_blank" rel="noopener">source</a>' : '') +
                    (safeDownload ? ' <a href="' + escapeHtml(download) + '" download="' + escapeHtml(filename) + '">Download attack TeX</a>' : '') +
                    '</div>' + (attack.date_posted ? '<div class="attack-date">Posted: ' + escapeHtml(attack.date_posted) + '</div>' : '') +
                    '<div class="attempt-content tex-content">' + content + '</div></div>';
            }).join('');
            initReferences(attemptsContainer, data, problem, 'economics-attempt-tex-label-');
        } else {
            attemptsContainer.innerHTML = '';
        }
        const math = window.MathJax;
        if (math && typeof math.typesetPromise === 'function') {
            try {
                if (math.startup && math.startup.promise) await math.startup.promise;
                await math.typesetPromise(attempts.length ? [statement, attemptsContainer] : [statement]);
                initReferences(statement, data, problem);
                if (attempts.length) initReferences(attemptsContainer, data, problem, 'economics-attempt-tex-label-');
            } catch (error) {
                console.warn('Economics statement typesetting failed:', error);
            }
        }
        return true;
    }

    window.EconomicsDetail = { render, orderedProblems, referenceTargets, normalizedReferences, normalizedStatement };
})();
