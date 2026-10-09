/* Economics catalogue: current rank is independent of permanent identity. */
(function () {
    'use strict';
    const families = {
        A: 'General Economics and Teaching', B: 'History of Economic Thought and Methodology',
        C: 'Mathematical and Quantitative Methods', D: 'Microeconomics',
        E: 'Macroeconomics and Monetary Economics', F: 'International Economics',
        G: 'Financial Economics', H: 'Public Economics', I: 'Health, Education and Welfare',
        J: 'Labor and Demographic Economics', K: 'Law and Economics', L: 'Industrial Organization',
        M: 'Business, Marketing, Accounting and Personnel Economics', N: 'Economic History',
        O: 'Economic Development, Innovation and Growth', P: 'Economic Systems',
        Q: 'Agricultural, Natural Resource and Environmental Economics',
        R: 'Urban, Rural, Regional, Real Estate and Transportation Economics',
        Y: 'Miscellaneous Categories', Z: 'Other Special Topics'
    };
    const validSorts = ['rank', 'title', 'jel_code', 'id'];
    const escape = value => window.ProblemHunting.escapeHtml(value);
    const href = record => `problem.html?type=economics&id=${encodeURIComponent(record.id)}`;
    const familyLabel = code => families[String(code).charAt(0)] || 'Economics';
    function compare(a, b, key = 'rank', direction = 'asc') {
        const order = key === 'rank' ? a.rank - b.rank
            : String(a[key]).localeCompare(String(b[key]), undefined, { numeric: true, sensitivity: 'base' });
        return (direction === 'desc' ? -order : order) || a.rank - b.rank || String(a.id).localeCompare(String(b.id));
    }
    function filter(records, options = {}) {
        const query = String(options.search || '').trim().toLocaleLowerCase();
        const terms = query.split(/\s+/).filter(Boolean);
        return records.filter(record => {
            if (options.family && !record.jel_code.startsWith(options.family)) return false;
            if (options.jel && record.jel_code !== options.jel) return false;
            // A number searches the current rank; a full ID always names one statement.
            if (/^\d+$/.test(query)) return record.rank === Number(query);
            if (/^[a-z]\d{2}-\d+$/i.test(query)) return record.id.toLowerCase() === query;
            const text = [record.title, record.id, record.jel_code, record.rank, record.source_id,
                familyLabel(record.jel_code), record.definition_tex].join(' ').toLocaleLowerCase();
            return terms.every(term => text.includes(term));
        });
    }
    function rows(records) {
        if (!records.length) return '<tr><td colspan="4">No problems match these filters.</td></tr>';
        return records.map(record => `<tr>
            <td>${escape(record.rank)}</td>
            <td class="catalogue-problem"><a href="${href(record)}">${escape(record.title)}</a></td>
            <td><span title="${escape(familyLabel(record.jel_code))}">${escape(record.jel_code)}</span></td>
            <td>${escape(record.id)}</td>
        </tr>`).join('');
    }
    function init() {
        const body = document.getElementById('economics-tbody');
        if (!body) return;
        const count = document.getElementById('results-count');
        if (!window.ECONOMICS_DATA) {
            body.innerHTML = '<tr><td colspan="4">Unable to load the Economics catalogue.</td></tr>';
            count.textContent = 'Catalogue unavailable';
            return;
        }
        const records = Object.values(window.ECONOMICS_DATA);
        const search = document.getElementById('search');
        const family = document.getElementById('filter-jel-family');
        const jel = document.getElementById('filter-jel');
        const sort = document.getElementById('sort-by');
        const direction = document.getElementById('sort-direction');
        const headers = Array.from(document.querySelectorAll('#economics-table [data-sort]'));
        const categoryCodes = [...new Set(records.map(record => record.jel_code.charAt(0)))].sort();
        family.innerHTML = '<option value="">All categories</option>' + categoryCodes.map(code =>
            `<option value="${escape(code)}">${escape(code + ' — ' + familyLabel(code))}</option>`).join('');
        const params = new URLSearchParams(window.location.search);
        family.value = categoryCodes.includes(params.get('family')) ? params.get('family') : '';
        function codeOptions(selected) {
            const codes = [...new Set(records.filter(record => !family.value || record.jel_code.startsWith(family.value))
                .map(record => record.jel_code))].sort();
            jel.innerHTML = '<option value="">All JEL codes</option>' + codes.map(code =>
                `<option value="${escape(code)}">${escape(code)}</option>`).join('');
            jel.value = codes.includes(selected) ? selected : '';
        }
        codeOptions(params.get('jel'));
        search.value = params.get('q') || '';
        sort.value = validSorts.includes(params.get('sort')) ? params.get('sort') : 'rank';
        direction.value = params.get('dir') === 'desc' ? 'desc' : 'asc';
        function render(sync = true) {
            const selected = filter(records, { search: search.value, family: family.value, jel: jel.value })
                .sort((a, b) => compare(a, b, sort.value, direction.value));
            body.innerHTML = rows(selected);
            count.textContent = `${selected.length} of ${records.length} entries · Statements only`;
            headers.forEach(button => {
                const active = button.dataset.sort === sort.value;
                button.closest('th').setAttribute('aria-sort', active ?
                    (direction.value === 'asc' ? 'ascending' : 'descending') : 'none');
                button.querySelector('.sort-indicator').textContent = active ?
                    (direction.value === 'asc' ? '↑' : '↓') : '⇅';
            });
            if (sync) {
                // Some browsers restrict replaceState on file:// previews; filtering still works.
                try { window.ProblemHunting.updateUrl({ q: search.value.trim(), family: family.value,
                    jel: jel.value, sort: sort.value === 'rank' ? null : sort.value,
                    dir: direction.value === 'asc' ? null : direction.value }); } catch (_) {}
            }
        }
        search.addEventListener('input', window.ProblemHunting.debounce(() => render(), 200));
        family.addEventListener('change', () => { codeOptions(jel.value); render(); });
        [jel, sort, direction].forEach(control => control.addEventListener('change', () => render()));
        headers.forEach(button => button.addEventListener('click', () => {
            direction.value = sort.value === button.dataset.sort && direction.value === 'asc' ? 'desc' : 'asc';
            sort.value = button.dataset.sort;
            render();
        }));
        document.getElementById('reset-filters').addEventListener('click', () => {
            search.value = ''; family.value = ''; codeOptions(''); sort.value = 'rank'; direction.value = 'asc'; render();
        });
        render(false);
    }
    window.EconomicsCatalogue = { compare, filter, rows, href, familyLabel, init };
    document.addEventListener('DOMContentLoaded', init);
})();
