// Resolve source references within their own writeup (and imported source version).
(function () {
    function renderedEquationName(label) {
        let display = label.nextElementSibling;
        while (display?.classList.contains('tex-label')) display = display.nextElementSibling;
        if (!display?.matches('mjx-container[display="true"]')) return null;
        // Read the actual accessible MathJax tag. A multi-tag alignment has no
        // unambiguous label-to-row correspondence here; retain its source key.
        const tags = display.querySelectorAll('mjx-assistive-mml mlabeledtr > mtd:first-child');
        if (tags.length !== 1) return null;
        const caption = tags[0].textContent.trim();
        return caption.replace(/^\(([\s\S]*)\)$/, '$1') || null;
    }

    function initTeXReferences(container, rankedProblems = null) {
        const maps = new Map();
        const rankedTargets = new Map(Object.values(rankedProblems || {})
            .filter(problem => Number.isInteger(problem.rank) && problem.rank > 0 &&
                typeof problem.id === 'string' && problem.id.startsWith('problem.'))
            .map(problem => [String(problem.rank), problem]));
        const keyFor = node => `${node.dataset.texScope || '0'}:${node.dataset.texLabel || node.dataset.texReference}`;
        container.querySelectorAll('.attempt').forEach((attempt, index) => {
            const targets = new Map();
            attempt.querySelectorAll('.tex-label').forEach((label, number) => {
                label.id = `tex-label-${index + 1}-${number + 1}`;
                label.tabIndex = -1;
                const block = label.closest('.theorem, .lemma, .proposition, .corollary, .claim, .definition, .remark');
                const heading = block?.querySelector('strong')?.textContent || '';
                const name = label.dataset.texLabelKind === 'math' ? renderedEquationName(label)
                    : heading.match(/\[([\s\S]+)\]:?\s*$/)?.[1];
                targets.set(keyFor(label), { label, name });
            });
            maps.set(attempt, targets);
        });

        document.querySelectorAll('.tex-reference').forEach(link => {
            let attempt = link.closest('.attempt');
            if (!attempt) {
                // A copied problem statement refers back to its original writeup.
                const source = link.closest('.writeup-statement')?.querySelector('.status-note a[href^="#attempt-"]');
                attempt = source ? document.getElementById(source.hash.slice(1)) : null;
            }
            const target = maps.get(attempt)?.get(keyFor(link));
            if (!target) {
                const ranked = link.dataset.texReferenceKind !== 'eqref'
                    ? rankedTargets.get(link.dataset.texReference) : null;
                if (ranked) {
                    link.href = `problem.html?type=open_problems&id=${encodeURIComponent(ranked.id)}`;
                    link.title = `View ${ranked.title || `problem ${ranked.rank}`}`;
                    return;
                }
                link.removeAttribute('href');
                link.title = `Reference ${link.dataset.texReference}: target not present in this writeup`;
                return;
            }
            link.href = `#${target.label.id}`;
            link.title = `View ${link.dataset.texReference} in this writeup`;
            if (target.name && !/[\\$]/.test(target.name)) {
                link.textContent = link.dataset.texReferenceKind === 'eqref' ? `(${target.name})` : target.name;
            }
            if (!link.dataset.texReferenceReady) {
                link.dataset.texReferenceReady = 'true';
                link.addEventListener('click', () => {
                    const remainder = target.label.closest('.attempt-remainder');
                    if (remainder?.hidden) {
                        attempt.querySelector('.attempt-read-more')?.click();
                    }
                });
            }
        });
    }
    window.ProblemHunting.initTeXReferences = initTeXReferences;
})();
