// Run with: node tests/test_tex_renderer.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'docs/problem.html'), 'utf8');
const scripts = Array.from(html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g), m => m[1]);
const context = vm.createContext({ document: { addEventListener() {} }, window: {} });
vm.runInContext(fs.readFileSync(path.join(root, 'docs/tex-bare-math.js'), 'utf8'), context);
vm.runInContext(scripts.find(script => script.includes('window.MathJax =')), context);
vm.runInContext(scripts.find(script => script.includes('function formatTeX')), context);
const render = context.formatTeX;
const tex = String.raw;

assert.equal(render(tex`C\textasciicircum{}r and O\textasciitilde{}(n)`, false, false),
             '<p>C^r and O~(n)</p>');

// Source-defined diameter and the Tate--Shafarevich symbol need browser aliases.
assert.equal(context.window.MathJax.tex.macros.diam, tex`{\operatorname{diam}}`);
assert.equal(context.window.MathJax.tex.macros.Sha, tex`{\unicode{x0428}}`);

// The reported fragment must behave like a full document and a collection.
const heading = tex`\section{Erd\H{o}s Problem \#3: independent continuation}`;
for (const preserve of [false, true]) {
    assert.equal(render(heading, preserve), '<h2>Erdős Problem #3: independent continuation</h2>');
}
assert.equal(render(tex`\documentclass{article}
\begin{document}
${heading}
\end{document}`), render(heading));
const collection = render(tex`Earlier attribution.

\begin{document}
${heading}
\end{document}`, true);
assert.match(collection, /Earlier attribution/);
assert.match(collection, /Problem #3/);

assert.equal(render(tex`The entire supplied \texttt{3.tex} was checked.`), '<p>The entire supplied <code>3.tex</code> was checked.</p>');
for (const source of [
    tex`\texttt{https://www.erdosproblems.com/3}`,
    tex`\texttt{[https://www.erdosproblems.com/3](https://www.erdosproblems.com/3)}`,
    tex`\url{https://www.erdosproblems.com/3}`,
    tex`\href{https://www.erdosproblems.com/3}{https://www.erdosproblems.com/3}`,
    '[https://www.erdosproblems.com/3](https://www.erdosproblems.com/3)',
]) {
    const result = render(source);
    assert.equal((result.match(/<a /g) || []).length, 1, result);
    assert.match(result, /href="https:\/\/www\.erdosproblems\.com\/3"/);
    assert.doesNotMatch(result, /\\texttt|\[https:|<a [^>]*>[^<]*<a /);
}
const links = render('Read https://example.org/result. Also (https://example.org/second), and https://example.org/A_(B).');
assert.match(links, /href="https:\/\/example.org\/result"[^>]*>https:\/\/example.org\/result<\/a>\./);
assert.match(links, /href="https:\/\/example.org\/second"/);
assert.match(links, /href="https:\/\/example.org\/A_\(B\)"/);
assert.doesNotMatch(render(tex`\href{javascript:alert(1)}{source}`), /href=/);
assert.match(render(tex`\url{https://example.org/?a=1\&b=2}`), /href="https:\/\/example.org\/\?a=1&amp;b=2"/);
assert.match(render(tex`\url{https://users.renyi.hu/\~{}p_erdos/1982-01.pdf}`), /href="https:\/\/users\.renyi\.hu\/~p_erdos\/1982-01\.pdf"/);
assert.match(render(tex`\href{https://example.org/}{\emph{Source} $x^2$}`), /<em>Source<\/em> \$x\^2\$/);

assert.equal(render('Round~2 and Round&nbsp;4.'), '<p>Round\u00a02 and Round\u00a04.</p>');
assert.equal(render(tex`A prize of \$250 for $\alpha=\omega_1^{\omega+2}$ and \$500 otherwise.`),
    tex`<p>A prize of \$250 for $\alpha=\omega_1^{\omega+2}$ and \$500 otherwise.</p>`);
assert.equal(render(tex`First\qquad\text{and}\qquad second.`), '<p>First\u2003\u2003and\u2003\u2003 second.</p>');
assert.equal(render(tex`Erd\H{o}s\textquotesingle{}s question: 50\% \& \#3.`), "<p>Erdős's question: 50% &amp; #3.</p>");
assert.equal(render(tex`Erd\H{o}s\textquotesingle s`), "<p>Erdős's</p>");
assert.equal(render(tex`Invent.\ Math.\ 85; W.\,D.`), '<p>Invent. Math. 85; W.\u2009D.</p>');
assert.equal(render(tex`$a\,b\ c$`), '<p>$a\\,b\\ c$</p>');
assert.match(render(tex`\url{https://example.org/a\,b}`), /href="https:\/\/example\.org\/a\\,b"/);
const quote = render(tex`\begin{quote}
*If $A$ satisfies $\sum^*_{n\in A}1/n=\infty$, then $A$
contains progressions of every length.*
\end{quote}`);
assert.match(quote, /<blockquote>\s*<em>If \$A\$/);
assert.match(quote, /length\.<\/em>/);
assert.match(quote, /\\sum\^\*/);
assert.equal(render('*x* and **bold**.'), '<p><em>x</em> and <strong>bold</strong>.</p>');
assert.match(render(tex`\textbf{FINAL: \textbf{UNRESOLVED}.}`), /<strong>FINAL: <strong>UNRESOLVED<\/strong>\.<\/strong>/);
assert.equal(render(tex`\subparagraph{A nested {title}.}`), '<h6>A nested {title}.</h6>');
assert.equal(render(tex`{\small\textit{Source \textbf{with nested formatting}, $\{x\}$.}}`),
    '<p><em>Source <strong>with nested formatting</strong>, $\\{x\\}$.</em></p>');
assert.equal(render(tex`\textit{\small Source note.} {\footnotesize A {nested} group.}`),
    '<p><em>Source note.</em> A {nested} group.</p>');
assert.equal(render(tex`{\small\textit{Literal \{braces\}, unmatched \{, and $\small x$.}}`),
    '<p><em>Literal {braces}, unmatched {, and $\\small x$.</em></p>');
assert.equal(render(tex`\section{\texorpdfstring{A bound for $N^{\varepsilon}$}{Plain PDF title}}`), '<h2>A bound for $N^{\\varepsilon}$</h2>');
assert.equal(render(tex`\addcontentsline{toc}{section}{Hidden {metadata}}
\textnormal{Visible} \textup{content}. \newblock See \S~2.`), '<p>Visible content.   See §\u00a02.</p>');
assert.equal(render(tex`\S3, \S5.2, \S{}7; $\Sigma$.`), '<p>§3, §5.2, §7; $\\Sigma$.</p>');
const footnote = render(tex`A claim.\footnote{Compare \emph{Source}, $x^{2}$, \url{https://example.org/paper}.}`);
assert.match(footnote, /A claim\.\(Compare <em>Source<\/em>, \$x\^\{2\}\$, <a /);
assert.match(footnote, /paper<\/a>\.\)/);
assert.doesNotMatch(footnote, /\\footnote|\\emph|\\url/);

// Prose processing must preserve all mathematical commands and stars, HTML
// comparisons, line breaks, alignment separators, and escaped set braces.
for (const math of [
    tex`$f*g*h + \sum^*_{n=1}^N a_n$`,
    tex`$$\textbf{A} * \textit{B} + \texttt{x_y}$$`,
    tex`$\{x\in\mathbb R:x\ge0\}\quad\#A\quad x\&y$`,
    tex`\[\begin{array}{cc}a&b\\c&d\end{array}\]`,
    tex`\begin{align*}f(x)&=(x+1)^2\\g(x)&=x^2\end{align*}`,
    tex`$$a=b

c=d$$`,
]) {
    const expected = math.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    assert.equal(render(math), `<p>${expected}</p>`);
}
assert.equal(render(tex`\(x^2+1\)`), '<p>$x^2+1$</p>');
assert.equal(render(tex`A graph has \chi(G[X])\le\aleph_0.`), '<p>A graph has $\\chi(G[X])\\le\\aleph_0$.</p>');
assert.equal(render(tex`Use H_\kappa and \texttt{H_\kappa}.`), '<p>Use $H_\\kappa$ and <code>H_\\kappa</code>.</p>');
assert.equal(render('(x^2+1)'), '<p>$x^2+1$</p>');
assert.equal(render(tex`\[\begin{psmallmatrix}1&0\\0&1\end{psmallmatrix}\]`),
    tex`<p>\[\begin{pmatrix}1&amp;0\\0&amp;1\end{pmatrix}\]</p>`);
assert.match(render(tex`$\Bigl(x\Bigr)$`), /\$\\left\(x\\right\)\$/);
assert.equal(render(tex`\paragraph{A bound for $N^{\varepsilon}$.}`), '<h5>A bound for $N^{\\varepsilon}$.</h5>');
assert.match(render(tex`\begin{theorem}[Known result]$x>0$.\end{theorem}`), /<div class="theorem"><strong>Theorem\[Known result\]:<\/strong> \$x&gt;0\$\.<\/div>/);
assert.equal(render(tex`(\emph{cographs}) and (\*)`), '<p>(<em>cographs</em>) and (*)</p>');
assert.equal(render(tex`\[x
>y\]`), '<p>\\[x\n&gt;y\\]</p>');
assert.equal(render(tex`> \[
> x>y
> \]`), '<blockquote> \\[\nx&gt;y\n\\] </blockquote>');
assert.equal(render(tex`\[x=1\label{eq:shared}\qedhere\]`), '<p><span class="tex-label" data-tex-label="eq:shared" data-tex-scope="0" data-tex-label-kind="math"></span>\\[x=1\\square\\]</p>');
const references = render(tex`\begin{lemma}[Packing]\label{lem:packing}Claim.\end{lemma}
By Lemma~\ref{lem:packing}, use \eqref{eq:missing}.`);
assert.match(references, /data-tex-label="lem:packing"/);
assert.match(references, /data-tex-reference="lem:packing"/);
assert.match(references, />\(eq:missing\)<\/a>/);
const importedReferences = render(tex`% BEGIN REUSED SOURCE: one.tex
\label{shared}First \ref{shared}.
% END REUSED SOURCE: one.tex
% BEGIN REUSED SOURCE: two.tex
\label{shared}Second \ref{shared}.`, true);
assert.match(importedReferences, /data-tex-label="shared" data-tex-scope="1"/);
assert.match(importedReferences, /data-tex-label="shared" data-tex-scope="2"/);
assert.match(render(tex`$x=\ref{eq:value}$`), /\\text\{eq:value\}/);
const multilineDelimiter = tex`\[\begin{aligned}X&=\Biggl(a+b\\&+c\Biggr).\end{aligned}\]`;
assert.match(render(multilineDelimiter), /\\Biggl\(/);
assert.match(render(multilineDelimiter), /\\Biggr\)/);
assert.doesNotMatch(render(multilineDelimiter), /\\left|\\right/);

// A missing source delimiter must not pull later list items/sections into math.
const malformed = render(tex`\begin{enumerate}
\item For some $c>0.
\item For every $k$, prove $k>0$.
\end{enumerate}

\section{Next result}`);
assert.match(malformed, /<li>For some \$c&gt;0\.\s*<\/li><li>For every \$k\$/);
assert.match(malformed, /<h2>Next result<\/h2>/);
assert.doesNotMatch(malformed, /\\item|\\end\{enumerate\}/);

const list = render(tex`\begin{enumerate}
\item[(i)] First.
\begin{enumerate}\item Nested.\end{enumerate}
\item[(ii)] Second.
\end{enumerate}`);
assert.equal((list.match(/<ol>/g) || []).length, 2);
assert.equal((list.match(/<li>/g) || []).length, 3);
assert.match(list, /Nested\.<\/li><\/ol>\s*<\/li><li>\(ii\) Second\./);
assert.doesNotMatch(list, /\\item|\\(?:begin|end)\{enumerate\}/);
assert.equal(render(tex`\item[(i)] A complete fragment.`), '<p>(i) A complete fragment.</p>');

const code = render(tex`\texttt{cost_\$x *literal* <tag>}`);
assert.equal(code, '<p><code>cost_$x *literal* &lt;tag&gt;</code></p>');
assert.equal(render(tex`\begin{verbatim}
<tag> $x$ **literal**
\end{verbatim}`), '<pre>\n&lt;tag&gt; $x$ **literal**\n</pre>');
assert.match(html, /skipHtmlTags: \[[^\]]*'code'/);
assert.deepEqual(Array.from(context.window.MathJax.tex.macros.Mg), [tex`{\mathcal{M}_{#1}}`, 1]);
assert.equal(context.window.MathJax.tex.macros.poly, tex`{\operatorname{poly}}`);
assert.equal(context.window.MathJax.tex.macros.coloneqq, tex`{\mathrel{:=}}`);

// Exercise the actual reported source, not only a synthetic copy.
const problem3 = render(fs.readFileSync(path.join(root, 'attacks/open_problems/erdos/GPT_6_Astra_Ultra/3.tex'), 'utf8'));
assert.match(problem3, /Erdős Problem #3: independent continuation/);
assert.match(problem3, /<code>3\.tex<\/code>/);
assert.doesNotMatch(problem3, /\\texttt|\\#|&amp;nbsp;|\\textquotesingle/);
const problem5 = render(fs.readFileSync(path.join(root, 'attacks/open_problems/erdos/gpt_pro_5.2/5_v2.tex'), 'utf8'));
assert.match(problem5, /<h2>ROUND-4 OBJECTIVE<\/h2>/);
assert.doesNotMatch(problem5, /\\(?:begin|end)\{(?:enumerate|itemize|theorem|lemma|proof)\}|\\item\b/);
const problem642 = render(fs.readFileSync(path.join(root, 'attacks/open_problems/erdos/gpt_pro_5.2/642.tex'), 'utf8'));
assert.match(problem642, /<div class="definition"><strong>Construction:<\/strong>/);
assert.match(problem642, /\\begin\{align\*\}[\s\S]*?E\(T_1\)&amp;:=[\s\S]*?\\end\{align\*\}/);
assert.doesNotMatch(problem642, /\\(?:begin|end)\{construction\}/);
// Additional corpus issues: prose accents, layout commands and optional citations.
assert.equal(render(tex`Lidick\'y; Ne\v{s}et\v{r}il; Pra\l at; St\o rmer; D{\o}vling; Garc\'{\i}a; Is\u{a}mailescu; \~n.`),
    '<p>Lidický; Nešetřil; Prałat; Størmer; Døvling; García; Isămailescu; ñ.</p>');
assert.equal(render(tex`Erd\H{o}s and F\H{u}redi, \v S, \c{c}, \L{}.`), '<p>Erdős and Fűredi, Š, ç, Ł.</p>');
assert.equal(render(tex`\cite[Thm.~3.2]{Source} and (\cite{GreenTao2017r4}).`),
    '<p>[Source, Thm.\u00a03.2] and ([GreenTao2017r4]).</p>');
assert.equal(render(tex`\cite[see][p.~2]{Source}`), '<p>[see Source, p.\u00a02]</p>');
assert.equal(render('(**#874 ⇒ #357**) and (#874 ⇒ #357).'),
    '<p>(<strong>#874 ⇒ #357</strong>) and (#874 ⇒ #357).</p>');
const layout = render(tex`First\\[2pt]Second\newline Third\par Fourth

\hrule
\centerline{A \textbf{centered} result}

\LaTeX{} {\em above} a\allowbreak b \dots\quad end.
\small
\normalsize
\newpage`);
assert.match(layout, /First<br>Second<br> Third<\/p><p>Fourth/);
assert.match(layout, /<hr> <div style="text-align: center;">A <strong>centered<\/strong> result<\/div>/);
assert.match(layout, /LaTeX <em>above<\/em> a<wbr> b …\u2003 end\./);
assert.doesNotMatch(layout, /\\(?:hrule|par|centerline|newline|small|normalsize|newpage)/);
assert.equal(render(tex`\MO{314626}{A \emph{question}}`), '<h3>MathOverflow #314626: A <em>question</em></h3>');
assert.match(render(tex`\begin{claim}A claim.\end{claim}`), /<div class="lemma"><strong>Claim:<\/strong> A claim\.<\/div>/);
assert.match(render(tex`\begin{description}[leftmargin=*]\item[(A)] First.\item[(B)] Second.\end{description}`),
    /<ul><li>\(A\) First\.<\/li><li>\(B\) Second\.<\/li><\/ul>/);
const tableSource = tex`\begin{tabular}{@{}lcr@{}}
\toprule
Name & $x_1$ & $\frac{a}{b}$\\
\midrule
A\&B & $2$ & $3$\\[2pt]
\bottomrule
\end{tabular}`;
for (const source of [tableSource, tex`\[${tableSource}\]`, `$$${tableSource}$$`]) {
    const table = render(source);
    assert.equal((table.match(/<tr>/g) || []).length, 2);
    assert.equal((table.match(/<td /g) || []).length, 6);
    assert.match(table, /text-align: left;">A&amp;B/);
    assert.match(table, /text-align: center;">\$x_1\$/);
    assert.match(table, /text-align: right;">\$\\frac\{a\}\{b\}\$/);
    assert.doesNotMatch(table, /\\(?:begin|end|toprule|midrule|bottomrule)|@\{|lll/);
}
for (const fixture of ['244', '529', '530', '533', '535']) {
    const result = render(fs.readFileSync(path.join(root, `attacks/open_problems/erdos/gpt_pro_5.2/${fixture}.tex`), 'utf8'));
    assert.match(result, /<table class="latex-table">/);
    assert.doesNotMatch(result, /\\(?:begin|end)\{tabular\}|\\(?:toprule|midrule|bottomrule)/);
}
const spacedRows = render(tex`\begin{tabular}{cc}A & B\\ \hline 1 & 2\\ \end{tabular}`);
assert.equal((spacedRows.match(/<tr>/g) || []).length, 2);
assert.equal((spacedRows.match(/<td /g) || []).length, 4);
const problem529 = render(fs.readFileSync(path.join(root, 'attacks/open_problems/erdos/gpt_pro_5.2/529.tex'), 'utf8'));
const tables529 = [...problem529.matchAll(/<table\b[^>]*>([\s\S]*?)<\/table>/g)].map(match =>
    [...match[1].matchAll(/<tr>([\s\S]*?)<\/tr>/g)].map(row =>
        [...row[1].matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/g)].map(cell => cell[1].trim())));
assert.deepEqual(tables529.map(rows => rows.length), [13, 11]);
for (const rows of tables529) {
    assert(rows.every(cells => cells.length === 4), 'Each header/data row must have four cells');
    assert.equal(rows[1][0], '1', 'The first data row must remain separate from the header');
}
assert.equal(tables529[0][0][3], tex`$d_2(n)/\sqrt n$`);
// Commands handled in prose must keep their meaning inside actual math/code.
assert.equal(render(tex`$\quad\qquad\dots\l\v{x}\begin{array}{cc}a&b\\c&d\end{array}$`),
    tex`<p>$\quad\qquad\dots\l\v{x}\begin{array}{cc}a&amp;b\\c&amp;d\end{array}$</p>`);
assert.equal(render(tex`\verb|\v{s} \\ \par \cite[p. 2]{x}|`), '<p><code>\\v{s} \\\\ \\par \\cite[p. 2]{x}</code></p>');
const qedFallback = render(tex`\providecommand{\qed}{\hfill\textit{(end of proof)}}
Proof ends here.\qed`);
assert.doesNotMatch(qedFallback, /\\providecommand|end of proof/);
assert.match(qedFallback, /Proof ends here\.\$\\square\$/);
console.log('TeX prose, citations, protected math/code, nested lists and Problem 3 rendering regressions passed.');
