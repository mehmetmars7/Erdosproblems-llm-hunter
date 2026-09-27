// Recognize complete ASCII mathematical expressions in catalogue snippets
// without interpreting ordinary prose or changing existing TeX/source data.
(function (host) {
    const greek = new Set(('alpha beta gamma delta epsilon varepsilon zeta eta theta iota kappa lambda mu nu xi pi rho sigma tau upsilon phi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega').split(' '));
    const functions = new Set(('Re Im Gal char Aut Hom Ext Tor Spec Pic CH dim rank rad poly ord det gcd lcm log ln exp sin cos tan sup inf max min lim zeta').split(' '));
    const operators = { '<=': '\\le', '>=': '\\ge', '!=': '\\ne', '->': '\\to', subseteq: '\\subseteq', subset: '\\subset', '=>': '\\Rightarrow' };
    const classes = new Set(('NP coNP PSPACE BQP BPP NC ZFC CH GRH RH ETH SETH EXP NEXP RP ZPP PH AC TC').split(' '));

    function catalogMath(text) {
        text = String(text || '');
        const space = index => { while (/\s/.test(text[index] || '')) index++; return index; };
        const identifier = index => /^[A-Za-z][A-Za-z0-9]*|^[α-ωΑ-Ω]/.exec(text.slice(index))?.[0];

        function group(index, script = false, depth = 0) {
            if (depth > 24 || !'([{|'.includes(text[index] || '\0')) return null;
            const open = text[index], close = { '(': ')', '[': ']', '{': '}', '|': '|' }[open];
            let cursor = index + 1, parts = [], evidence = false;
            while (cursor < text.length) {
                cursor = space(cursor);
                const end = text[cursor];
                if (end === close || (!script && (open === '(' || open === '[') && (end === ')' || end === ']'))) {
                    if (!parts.length) return null;
                    const body = parts.join('');
                    const tex = script ? body : (open === '{' ? '\\{' : open) + body + (end === '}' ? '\\}' : end);
                    return { end: cursor + 1, tex, evidence: evidence || open === '|' };
                }
                if (/[,;|:]/.test(text[cursor] || '')) { parts.push(text[cursor++]); continue; }
                const item = expression(cursor, true, depth + 1);
                if (!item) return null;
                parts.push(item.tex); evidence ||= item.evidence; cursor = item.end;
            }
            return null;
        }

        function atom(index, depth = 0) {
            if (depth > 24) return null;
            let cursor = index, tex = '', evidence = false, name = '';
            const number = /^\d+(?:\.\d+)?/.exec(text.slice(cursor));
            if (number) { tex = number[0]; cursor += tex.length; }
            else if ('([{|'.includes(text[cursor] || '\0')) {
                const value = group(cursor, false, depth + 1);
                if (!value) return null;
                ({ tex, evidence } = value); cursor = value.end;
            } else {
                name = identifier(cursor);
                if (!name) return null;
                if (greek.has(name)) { tex = '\\' + name; evidence = true; }
                else if (name === 'infinity') { tex = '\\infty'; evidence = true; }
                else if (['sum', 'prod', 'int'].includes(name)) tex = '\\' + name;
                else if (functions.has(name)) tex = name === 'zeta' ? '\\zeta' : '\\operatorname{' + name + '}';
                else if (classes.has(name)) tex = '\\mathrm{' + name + '}';
                else if (name.length === 1) tex = name;
                else return null;
                cursor += name.length;
                if (name === 'C' && text.slice(cursor, cursor + 9) === '-infinity') {
                    tex = 'C^{\\infty}'; cursor += 9; evidence = true;
                }
            }
            const scripts = new Set();
            while (cursor < text.length) {
                const mark = text[cursor];
                if (mark === '_' || mark === '^') {
                    if (scripts.has(mark)) return null;
                    scripts.add(mark);
                    const start = cursor + 1;
                    if (mark === '_' && /^bar\b/.test(text.slice(start))) {
                        tex = '\\overline{' + tex + '}'; cursor = start + 3;
                    } else {
                        let value;
                        if ('([{'.includes(text[start] || '\0')) value = group(start, true, depth + 1);
                        else {
                            const word = identifier(start) || /^\d+/.exec(text.slice(start))?.[0];
                            if (word) {
                                const content = greek.has(word) ? '\\' + word : word === 'infinity' ? '\\infty' : word;
                                if (word.length > 1 && !greek.has(word) && word !== 'infinity' && !functions.has(word) && !/^\d+$/.test(word)) return null;
                                value = { end: start + word.length, tex: content };
                                if (functions.has(word) && text[value.end] === '(') {
                                    const args = group(value.end, false, depth + 1);
                                    if (!args) return null;
                                    value = { end: args.end, tex: '\\operatorname{' + word + '}' + args.tex };
                                }
                            }
                        }
                        if (!value) return null;
                        tex += mark + '{' + value.tex + '}'; cursor = value.end;
                    }
                    evidence = true;
                } else if (mark === '(' && name) {
                    const args = group(cursor, false, depth + 1);
                    if (!args) break;
                    tex += args.tex; cursor = args.end; evidence = true;
                    scripts.clear();
                } else break;
            }
            // A function word without arguments or bounds can be ordinary prose.
            if (name.length > 1 && !greek.has(name) && name !== 'infinity' && !evidence && !classes.has(name)) return null;
            return { tex, end: cursor, evidence };
        }

        function expression(index, inside = false, depth = 0) {
            let sign = '';
            if (inside && /^[+-]/.test(text.slice(index))) { sign = text[index]; index = space(index + 1); }
            const first = atom(index, depth + 1);
            if (!first) return null;
            let tex = sign + first.tex, end = first.end, evidence = first.evidence;
            for (;;) {
                const next = space(end);
                const op = /^(?:<=|>=|!=|->|=>|subseteq\b|subset\b|[=<>+*/-])/.exec(text.slice(next));
                if (op) {
                    const right = atom(space(next + op[0].length), depth + 1);
                    if (!right) break;
                    // Section ranges and dates are not subtraction formulas.
                    if (!inside && op[0] === '-' && !evidence && /^\d+(?:\.\d+)?$/.test(tex) && /^\d+(?:\.\d+)?$/.test(right.tex)) break;
                    tex += ' ' + (operators[op[0]] || op[0]) + ' ' + right.tex;
                    end = right.end; evidence = true;
                } else {
                    if (inside && text[next] === '|') break;
                    const right = atom(next, depth + 1);
                    // Only groups allow unmarked juxtaposition (e.g. 2i).
                    // Outside groups, both sides need an explicit math signal.
                    if (!right || !(inside || (evidence && right.evidence))) break;
                    tex += ' ' + right.tex; end = right.end; evidence ||= right.evidence;
                }
            }
            return { tex, end, evidence };
        }

        let result = '';
        for (let index = 0; index < text.length;) {
            const literal = /^(?:https?:\/\/\S+|`[^`]*`|\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$|\$(?:\\.|[^$\\])*?\$)/.exec(text.slice(index));
            if (literal) { result += literal[0]; index += literal[0].length; continue; }
            // Do not start a new expression in the middle of a word or TeX command.
            const value = /[A-Za-z0-9_\\]/.test(text[index - 1] || '') ? null : expression(index);
            if (value?.evidence) { result += '\\(' + value.tex + '\\)'; index = value.end; }
            else { result += text[index]; index++; }
        }
        return result;
    }

    host.ProblemHunting.catalogMath = catalogMath;
})(window);
