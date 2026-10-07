#!/usr/bin/env python3
"""Inventory the exact OpenAI snapshot without copying source prose to the site."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from html import unescape
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import unicodedata
from urllib.parse import unquote

PIN = "adc7f1241b42e322a6451854ab7e4b4c146bf78a"
SOURCE_REPO = "https://github.com/openai/math"


def public_comparator_metadata(comparator: dict) -> dict:
    """Retain the path and declaration bindings needed by claim validation."""
    return {key: comparator[key] for key in ("json", "lean", "file", "declaration")
            if key in comparator and comparator[key] is not None}


def markdown_links(text: str) -> list[tuple[str, str]]:
    """Read links with nested brackets and parenthesis-balanced destinations.

    This handles the CAT(0) folder and math labels with internal brackets.
    Images use the same path syntax. Escaped delimiters do not affect balance.
    """
    links = []
    offset = 0
    while offset < len(text):
        start = text.find("[", offset)
        if start < 0:
            break
        pos, depth = start + 1, 1
        while pos < len(text) and depth:
            if text[pos] == "\\":
                pos += 2
                continue
            depth += (text[pos] == "[") - (text[pos] == "]")
            pos += 1
        if depth or pos >= len(text) or text[pos] != "(":
            offset = start + 1
            continue
        label = text[start + 1:pos - 1]
        target_start = pos + 1
        pos, depth = target_start, 1
        while pos < len(text) and depth:
            if text[pos] == "\\":
                pos += 2
                continue
            depth += (text[pos] == "(") - (text[pos] == ")")
            pos += 1
        if depth:
            raise ValueError(f"Unbalanced Markdown destination at offset {start}")
        destination = text[target_start:pos - 1].strip()
        if destination.startswith("<") and destination.endswith(">"):
            destination = destination[1:-1]
        destination = re.sub(r"\\([()])", r"\1", destination)
        links.append((label.strip(), unquote(destination)))
        offset = pos
    return links


def braced(text: str, offset: int) -> tuple[str, int]:
    while offset < len(text) and text[offset].isspace():
        offset += 1
    if offset >= len(text) or text[offset] != "{":
        raise ValueError(f"Expected TeX brace at {offset}")
    start, depth, pos = offset + 1, 1, offset + 1
    while pos < len(text) and depth:
        if text[pos] == "\\" and pos + 1 < len(text) and text[pos + 1] in "{}%":
            pos += 2
            continue
        depth += (text[pos] == "{") - (text[pos] == "}")
        pos += 1
    if depth:
        raise ValueError(f"Unbalanced TeX braces at {offset}")
    return text[start:pos - 1], pos


def overview_families(text: str) -> dict[str, dict]:
    result = {}
    subject = None
    for match in re.finditer(r"^\\(cataloguesection|resultentry)\{", text, re.M):
        count = 2 if match.group(1) == "cataloguesection" else 4
        arguments, offset = [], match.end() - 1
        for _ in range(count):
            argument, offset = braced(text, offset)
            arguments.append(argument)
        if count == 2:
            subject = arguments[0]
        else:
            family, title, summary, links = arguments
            if subject is None or family in result:
                raise ValueError(f"Missing subject or repeated family {family}")
            result[family] = {"title": title, "subject": subject, "summary": summary}
    assert len(result) == 372, len(result)
    assert len({entry["subject"] for entry in result.values()}) == 17
    return result


def contents_families(text: str) -> dict[str, dict]:
    families = {}
    family = None
    lines = text.splitlines()
    for number, line in enumerate(lines):
        heading = re.match(r"^\*\*(\d{3})\. (.*?)\.\*\*\s*(.*)$", line)
        if heading:
            family = heading.group(1)
            if family in families:
                raise ValueError(f"Repeated family {family}")
            lean_paths = [path for _, path in markdown_links(heading.group(3)) if re.fullmatch(r"lean/docs/\d{3}\.md", path)]
            families[family] = {"title": heading.group(2), "summary": heading.group(3), "lean_doc": lean_paths[0] if lean_paths else None, "papers": []}
        elif re.match(r"^&emsp;\s*\[", line):
            if family is None:
                raise ValueError("Paper without preceding family")
            paper_links = [(title, path) for title, path in markdown_links(line) if path.startswith("preprints/") and path.endswith(".pdf")]
            if len(paper_links) != 1:
                raise ValueError(f"Expected one manuscript link at line {number + 1}, got {paper_links}")
            title, path = paper_links[0]
            following = []
            for abstract_line in lines[number + 1:]:
                if "</td>" in abstract_line:
                    break
                following.append(abstract_line)
            families[family]["papers"].append({"title": title, "pdf_path": path, "abstract": "\n".join(following).strip()})
    assert len(families) == 372, len(families)
    assert sum(len(family["papers"]) for family in families.values()) == 722
    assert sum(bool(family["lean_doc"]) for family in families.values()) == 235
    return families


def repo_path(path: str, base: str = "") -> str:
    """Normalise a relative Markdown destination to a checkout-root path."""
    if path.startswith(SOURCE_REPO + "/blob/") or path.startswith(SOURCE_REPO + "/raw/"):
        path = path.split("/", 7)[7]
    path = path.split("#", 1)[0]
    if path.startswith("lean/") or path.startswith("preprints/") or path.startswith("reasoning_traces/"):
        return str(PurePosixPath(path))
    combined = PurePosixPath(base) / path
    stack = []
    for part in combined.parts:
        if part == "..":
            if not stack:
                raise ValueError(f"Path escapes checkout: {combined}")
            stack.pop()
        elif part not in (".", ""):
            stack.append(part)
    return "/".join(stack)


def date_from_dir(directory: str) -> str:
    iso_match = re.search(r"-(\d{4}-\d{2}-\d{2})$", directory)
    if iso_match:
        return datetime.strptime(iso_match.group(1), "%Y-%m-%d").date().isoformat()
    match = re.search(r"-([A-Za-z]+)-(\d{1,2})-(\d{4})$", directory)
    if not match:
        raise ValueError(f"Cannot read date: {directory}")
    return datetime.strptime(" ".join(match.groups()), "%B %d %Y").date().isoformat()


def manuscript_title(readme: str) -> str:
    """Use the manuscript's citation title, rather than an index display alias."""
    match = re.search(r"(?mi)^\s*title\s*=\s*\{", readme)
    if match:
        title, _ = braced(readme, match.end() - 1)
        while title.startswith("{"):
            inner, end = braced(title, 0)
            if end != len(title):
                break
            title = inner
    else:
        heading = re.search(r"(?m)^#\s+(.+)$", readme)
        links = markdown_links(heading[1]) if heading else []
        if not links:
            raise ValueError("Manuscript README requires a citation title or linked heading")
        title = links[0][0]
    title = unescape(title)
    accent_marks = {"'": '\u0301', '"': '\u0308', '`': '\u0300',
                    '^': '\u0302', '~': '\u0303', '=': '\u0304',
                    '.': '\u0307', 'c': '\u0327', 'u': '\u0306',
                    'v': '\u030c', 'H': '\u030b'}
    title = re.sub(r'''\\(['"`^~=.cuvH])\s*(?:\{([^{}])\}|([A-Za-z]))''',
                   lambda m: unicodedata.normalize('NFC', (m[2] or m[3]) + accent_marks[m[1]]), title)
    # Keep titles as plain metadata; equivalent Unicode math avoids embedding
    # HTML or TeX source in link labels and citation keys.
    alphabets = {'C': 'ℂ', 'R': 'ℝ', 'Q': 'ℚ', 'N': 'ℕ', 'Z': 'ℤ'}
    title = re.sub(r"\\mathbb\s*(?:\{([A-Za-z])\}|([A-Za-z]))",
                   lambda m: alphabets.get(m[1] or m[2], m[1] or m[2]), title)
    title = re.sub(r"\\(?:mathcal|mathsf|mathrm|mathit|text)\s*(?:\{([^{}]*)\}|([A-Za-z]))",
                   lambda m: ' ' + (m[1] if m[1] is not None else m[2]) + ' ', title)
    commands = {'ell': 'ℓ', 'pi': 'π', 'Gamma': 'Γ', 'alpha': 'α',
                'times': '×', 'infty': '∞', 'le': '≤', 'leq': '≤',
                'gt': '>', 'lt': '<', 'arcsin': 'arcsin', 'o': 'ø',
                'mu': 'μ', 'log': 'log '}
    title = re.sub(r'\\([A-Za-z]+)\s*', lambda m: commands.get(m[1], '\\' + m[1]), title)
    subs = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    supers = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    title = re.sub(r"_(?:\{(\d+)\}|(\d+))", lambda m: (m[1] or m[2]).translate(subs), title)
    title = re.sub(r"\^(?:\{(\d+)\}|(\d+))", lambda m: (m[1] or m[2]).translate(supers), title)
    title = title.replace("$", "").replace("`", "")
    title = title.replace("---", "—").replace("--", "–")
    title = re.sub(r'\{([^{}])\}', r'\1', title)
    if '\\' in title:
        raise ValueError(f'Unsupported manuscript-title TeX: {title}')
    return " ".join(title.split())


def main() -> None:
    import yaml

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="Pinned OpenAI checkout, outside site repo.")
    parser.add_argument("--output", type=Path, required=True, help="External local output directory for inventory and extracted text.")
    parser.add_argument("--manifest", type=Path, required=True, help="Public manifest path; titles and paths only, never source prose.")
    args = parser.parse_args()
    head = subprocess.check_output(["git", "-C", str(args.repo), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN:
        raise SystemExit(f"Refusing inventory: HEAD {head} differs from required snapshot {PIN}")
    changes = subprocess.check_output(["git", "-C", str(args.repo), "status", "--porcelain",
                                       "--untracked-files=all"], text=True).strip()
    if changes:
        raise SystemExit("Refusing inventory: source checkout has working-tree changes")
    tracked = set(subprocess.check_output(["git", "-C", str(args.repo), "ls-tree", "-r", "--name-only", PIN], text=True).splitlines())
    tracked_dirs = {str(parent) for path in tracked for parent in PurePosixPath(path).parents}
    manuscript_tex = defaultdict(list)
    for path in tracked:
        parts = PurePosixPath(path).parts
        if len(parts) > 3 and parts[0] == "preprints" and parts[2] == "build" and path.endswith(".tex"):
            manuscript_tex[f"preprints/{parts[1]}/build"].append(path)
    overview = overview_families((args.repo / "overview.tex").read_text())
    contents = contents_families((args.repo / "CONTENTS.md").read_text())
    assert set(overview) == set(contents)
    assert len([path for path in tracked if re.fullmatch(r"lean/docs/\d{3}\.md", path)]) == 235
    assert len([path for path in tracked if re.fullmatch(r"lean/ComparatorChallenges/[^/]+\.json", path)]) == 405
    formalization = yaml.safe_load((args.repo / "lean/formalization.yaml").read_text())
    # The final comparator join is filled from the scope table and formalization.
    main_results = formalization.get("status", {}).get("main_results", [])
    assert len(main_results) == 185, len(main_results)
    config_rows = {}
    for row in main_results:
        config = row.get("comparator_config")
        if config:
            config_rows.setdefault(repo_path(config, "lean"), []).append(row)
    readme = (args.repo / "README.md").read_text()
    traces = {}
    for line in readme.splitlines():
        paths = [repo_path(path) for _, path in markdown_links(line) if path.startswith("reasoning_traces/") and path.endswith(".pdf")]
        if paths:
            family_match = re.search(r"(?<!\d)(\d{3})(?!\d)", line)
            if family_match:
                traces[family_match.group(1)] = paths[0]
    families, extracts = [], {}
    eligible = {"CONTENTS.md", "overview.tex", "README.md"}

    def present(path: str, directory: bool = False) -> str:
        if directory:
            if not (args.repo / path).is_dir() or path not in tracked_dirs:
                raise ValueError(f"Missing source directory at snapshot: {path}")
        elif path not in tracked or not (args.repo / path).is_file():
            raise ValueError(f"Missing file at snapshot: {path}")
        eligible.add(path)
        return path

    formalized_sources = {repo_path(source["id"], "lean") for source in formalization.get("sources", [])}
    for path in formalized_sources:
        present(path)

    all_pdfs = set()
    for family_id in sorted(contents):
        entry = contents[family_id]
        lean_doc = present(entry["lean_doc"]) if entry["lean_doc"] else None
        reasoning_trace = present(traces[family_id]) if family_id in traces else None
        family_comparators = []
        scope_papers = set()
        if lean_doc:
            scope = (args.repo / lean_doc).read_text()
            configs = []
            for _, link in markdown_links(scope):
                normal = repo_path(link, str(PurePosixPath(lean_doc).parent))
                if normal.startswith("preprints/") and normal.endswith(".pdf"):
                    scope_papers.add(normal)
                if normal.startswith("lean/ComparatorChallenges/") and normal.endswith((".json", ".lean")):
                    configs.append(normal.removesuffix(".lean").removesuffix(".json") + ".json")
            for config in sorted(set(configs)):
                config = present(config)
                lean = present(config.removesuffix(".json") + ".lean")
                comparator = json.loads((args.repo / config).read_text())
                rows = config_rows.get(config, [])
                # A comparator can expose several formalization main_results.
                # Keep every declaration/file binding instead of dropping rows.
                for row in rows or [{}]:
                    source_file = repo_path(row["file"], "lean") if row.get("file") else None
                    if source_file:
                        present(source_file)
                    family_comparators.append({"json": config, "lean": lean, "theorem_names": comparator.get("theorem_names", []), "solution_module": comparator.get("solution_module"), "declaration": row.get("declaration"), "file": source_file})
        papers = []
        for paper in entry["papers"]:
            pdf_path = present(paper["pdf_path"])
            if pdf_path in all_pdfs:
                raise ValueError(f"Manuscript listed twice: {pdf_path}")
            all_pdfs.add(pdf_path)
            directory = PurePosixPath(pdf_path).parent.name
            readme_path = present(f"preprints/{directory}/README.md")
            inputs_path = f"preprints/{directory}/INPUTS.md"
            inputs_md = present(inputs_path) if inputs_path in tracked else None
            # Actual snapshot stores most sources directly in build/, sometimes
            # with sections/ or other subdirectories; build/source is not a
            # universal layout despite the supplied prompt's description.
            source_dir = present(f"preprints/{directory}/build", directory=True)
            source_files = sorted(manuscript_tex[source_dir])
            if not source_files:
                raise ValueError(f"Manuscript has no TeX sources under build/: {directory}")
            for path in source_files:
                present(path)
            title = manuscript_title((args.repo / readme_path).read_text())
            papers.append({"title": title, "dir": directory, "pdf_path": pdf_path, "date": date_from_dir(directory), "readme_path": readme_path, "inputs_md": inputs_md, "source_tex_dir": source_dir, "source_tex_files": source_files, "lean_scope_listed": pdf_path in scope_papers, "comparator_join_scope": "family_scope_document; no individual comparator-to-paper assertion" if pdf_path in scope_papers else None, "comparators": family_comparators if pdf_path in scope_papers else []})
            extracts[directory] = {"family": family_id, "family_summary": entry["summary"], "overview_summary": overview[family_id]["summary"], "abstract": paper["abstract"]}
        families.append({"family": family_id, "title": entry["title"], "subject": overview[family_id]["subject"], "lean_doc": lean_doc, "reasoning_trace": reasoning_trace, "manuscripts": papers})
    inventory = {"schema_version": 1, "source_repo": SOURCE_REPO, "source_commit": PIN, "repo_path": str(args.repo.resolve()), "families": families, "counts": {"families": len(families), "manuscripts": len(all_pdfs), "lean_docs": sum(bool(family["lean_doc"]) for family in families), "subjects": len({family["subject"] for family in families}), "reasoning_traces": len(traces)}}
    assert inventory["counts"]["families"] == 372
    assert inventory["counts"]["manuscripts"] == 722
    assert inventory["counts"]["lean_docs"] == 235
    assert inventory["counts"]["subjects"] == 17
    args.output.mkdir(exist_ok=True, parents=True)
    (args.output / "inventory.json").write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n")
    (args.output / "extracted_text.json").write_text(json.dumps(extracts, indent=2, ensure_ascii=False) + "\n")
    manifest_families = []
    for family in families:
        manifest_family = {key: value for key, value in family.items() if key != "manuscripts"}
        manifest_family["manuscripts"] = []
        for paper in family["manuscripts"]:
            manifest_paper = {key: value for key, value in paper.items() if key not in {"source_tex_files", "comparators", "lean_scope_listed", "comparator_join_scope"}}
            manifest_paper["comparators"] = [public_comparator_metadata(comparator)
                                            for comparator in paper["comparators"]]
            manifest_family["manuscripts"].append(manifest_paper)
        manifest_families.append(manifest_family)
    manifest = {"schema_version": 1, "source_repo": SOURCE_REPO, "source_commit": PIN, "families": manifest_families, "eligible_paths": sorted(eligible)}
    args.manifest.parent.mkdir(exist_ok=True, parents=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"counts": inventory["counts"], "eligible_paths": len(eligible), "subjects": dict(Counter(family["subject"] for family in families)), "comparator_configs_in_yaml": len(config_rows)}, indent=2))


if __name__ == "__main__":
    main()
