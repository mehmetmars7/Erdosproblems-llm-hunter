#!/usr/bin/env python3
"""Reproducible, deliberately high-recall candidate generation (never verdicts).

This script keeps copied research text and work packets outside the public site.
TF-IDF requires scikit-learn; no network calls or repository writes occur here.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import unicodedata

def normalise(text: str) -> str:
    # Replace punctuation before ASCII folding; dropping an en dash would
    # otherwise concatenate two surnames into one token.
    text = text.translate(str.maketrans({character: " " for character in "–—−‐‑‒"}))
    text = text.replace("’", "'").replace("‘", "'")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower().replace("neighborhood", "neighbourhood")
    text = re.sub(r"(?:'s|’s)\b", "", text)
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    # 'Erdos and Gallai', 'Erdos-Gallai', and 'Erdos–Gallai' agree.
    text = re.sub(r"\band\b", " ", text)
    return " ".join(text.split())


def title_key(title: str) -> str:
    return re.sub(r"^(?:the |a )", "", normalise(title))


def eponyms(title: str) -> set[str]:
    """Collect possessive surnames and named conjecture/hypothesis prefixes.

    These deliberately add hits beyond top ten. They do not establish identity.
    """
    clean = title.replace("’", "'").replace("–", "-").replace("—", "-")
    hits = {
        normalise(m.group(1))
        for m in re.finditer(r"\b([A-Z][A-Za-zÀ-ž-]*(?:[ -][A-Z][A-Za-zÀ-ž-]*)*)'s\b", clean)
    }
    generic = {
        "the", "general", "generalized", "generalised", "strong", "weak", "little",
        "small", "large", "finite", "infinite", "minimal", "maximal", "universal",
        "linear", "nonlinear", "non", "positive", "negative", "direct", "stable",
        "global", "local", "rational", "integral", "complex", "real", "open",
        "problem", "conjecture", "hypothesis", "question", "theorem", "bound",
        "for", "on", "of", "in", "a", "an", "with", "over", "about", "to",
    }
    for match in re.finditer(
        r"\b((?:[A-Z][A-Za-zÀ-ž'-]*[ -]){1,5})(?:Conjecture|Hypothesis|Problem|Question)\b", clean
    ):
        words = normalise(match.group(1)).split()
        names = [word for word in words if word not in generic]
        if names:
            hits.add(" ".join(names))
    # Acronyms occurring in title are useful exact named targets (e.g. BSD).
    hits.update(normalise(m.group()) for m in re.finditer(r"\b[A-Z]{2,8}\b", clean))
    return {hit for hit in hits if len(hit) >= 3 and hit not in generic}


def definition_text(path: Path) -> tuple[str, str]:
    raw = path.read_text(encoding="utf-8")
    statement = re.search(
        r"\\subsection\*?\{Definitions and mathematical statement\}(.*?)(?=\\subsection|\\end\{document\})",
        raw, re.S,
    )
    scopes = re.findall(r"\\cataloguescope\{(.*?)\}\s*(?=\\|\n|$)", raw, re.S)
    selected = (statement.group(1) if statement else raw) + "\n" + "\n".join(scopes)
    return selected, raw


def named_targets(text: str) -> list[str]:
    patterns = (
        r"(?:proves?|disproves?|resolves?|settles?|answers?|counterexample to|negative answer to)\s+[^.!?\n]{5,220}",
        r"[^.!?\n]{0,90}(?:conjecture|hypothesis|open problem|question of|problem of)[^.!?\n]{0,160}",
    )
    return list(dict.fromkeys(m.group().strip() for pat in patterns for m in re.finditer(pat, text, re.I)))


def source_erdos_references(repo: Path, source_dir: str) -> dict[int, list[str]]:
    """Index explicit numbered source citations separately from match verdicts.

    Bibliographies can name a numbered target absent from the abstract. Ignore
    copied companion manuscripts so their citations do not become this paper's
    declared source references.
    """
    references = defaultdict(set)
    for path in sorted((repo / source_dir).rglob("*")):
        if path.suffix not in {".tex", ".bib"} or "companions" in path.parts:
            continue
        for match in re.finditer(r"erdosproblems\.com/(\d+)", path.read_text(encoding="utf-8")):
            references[int(match.group(1))].add(path.relative_to(repo).as_posix())
    return {number: sorted(paths) for number, paths in sorted(references.items())}


def main() -> None:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", type=Path, required=True, help="External OpenAI_math directory containing inventory.json/extracted_text.json; copied source text remains here.")
    parser.add_argument("--site", type=Path, required=True, help="Site checkout with lists/unsolvedmath/problems.json and definition TeX.")
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--target-expansions", type=Path, help="Optional JSON array of additional manuscript/candidate retrieval pairs supported by main-source references.")
    parser.add_argument("--preserve-candidates", type=Path, help="Earlier candidate JSON whose Pool A keys must remain available (for additive Pool B work).")
    args = parser.parse_args()
    inventory = json.loads((args.local / "inventory.json").read_text())
    previous = json.loads(args.preserve_candidates.read_text()) if args.preserve_candidates else None
    previous_a = defaultdict(dict)
    if previous:
        for manuscript in previous["manuscripts"]:
            for candidate in manuscript["candidates"]:
                if candidate["pool"] == "A":
                    previous_a[manuscript["manuscript_dir"]][int(candidate["candidate_id"])] = candidate
    extracts = json.loads((args.local / "extracted_text.json").read_text())
    records = json.loads((args.site / "lists/unsolvedmath/problems.json").read_text())
    expansion_path = args.target_expansions or args.local / "target_expansions.json"
    expansions = json.loads(expansion_path.read_text()) if expansion_path.is_file() else []
    pool_a_ids = {int(record["id"]) for record in records}
    pools = {"A": {"searched": True, "count": len(records), "source": str(args.site / "lists/unsolvedmath/problems.json")}}
    if args.registry and args.registry.is_file():
        full = json.loads(args.registry.read_text())
        if isinstance(full, dict):
            full = full.get("problems", full.get("records", []))
        extras = [record for record in full if int(record["id"]) not in pool_a_ids]
        records += extras
        pools["B"] = {"searched": True, "count": len(extras), "source": str(args.registry)}
    else:
        pools["B"] = {"searched": False, "count": None, "reason": "Authoritative local UnsolvedMath registry has not been supplied; absence of a Pool A match cannot establish no catalogue match."}
    definitions = {}
    searchable = []
    for record in records:
        problem_id = int(record["id"])
        path = args.site / "attacks/open_problems/top_problems/definitions" / f"{problem_id}.tex"
        selected, full = definition_text(path) if path.is_file() else ("", "")
        definitions[problem_id] = full
        searchable.append(normalise(" ".join((record["title"] * 3, record.get("statement", ""), record.get("background", ""), selected))))
    clusters = defaultdict(list)
    for record in records:
        clusters[title_key(record["title"])].append(int(record["id"]))
    duplicates = [
        {"key": key, "ids": sorted(ids), "basis": "normalised exact title; statement equivalence requires adjudication"}
        for key, ids in sorted(clusters.items()) if len(ids) > 1
    ]
    # Title-only duplicates are aids for the human pass, never auto-verdicts.
    duplicate_lookup = {problem_id: ids for ids in clusters.values() if len(ids) > 1 for problem_id in ids}
    eponym_index = defaultdict(list)
    for index, record in enumerate(records):
        for name in eponyms(record["title"]):
            eponym_index[name].append(index)
    manuscripts = [(family, paper) for family in inventory["families"] for paper in family["manuscripts"]]
    record_index = {int(record["id"]): index for index, record in enumerate(records)}
    erdos_number_index = {}
    for index, record in enumerate(records):
        match = re.search(r"erdos problem\s+(\d+)", normalise(record["title"]))
        if match:
            erdos_number_index.setdefault(int(match.group(1)), []).append(index)
    manuscript_dirs = {paper["dir"] for _, paper in manuscripts}
    for expansion in expansions:
        if expansion["manuscript_dir"] not in manuscript_dirs:
            raise ValueError(f"Target expansion names an unknown manuscript: {expansion['manuscript_dir']}")
        if int(expansion["candidate_id"]) not in record_index:
            raise ValueError(f"Target expansion names an unavailable catalogue ID: {expansion['candidate_id']}")
    queries = []
    for family, paper in manuscripts:
        extract = extracts[paper["dir"]]
        queries.append(normalise(" ".join((paper["title"] * 3, family["title"], extract["family_summary"], extract["abstract"]))))
    # Fit each pool independently so adding B cannot change the existing A
    # ordering, scores, or review keys. Keep top ten from EACH pool.
    pool_indices = {
        "A": [index for index, record in enumerate(records) if int(record["id"]) in pool_a_ids],
        "B": [index for index, record in enumerate(records) if int(record["id"]) not in pool_a_ids],
    }
    scores = np.zeros((len(queries), len(records)))
    for indices in pool_indices.values():
        if indices:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True, min_df=1, norm="l2")
            corpus = vectorizer.fit_transform([searchable[index] for index in indices])
            scores[:, indices] = (vectorizer.transform(queries) @ corpus.T).toarray()
    rows = []
    erdos_hits = []
    for index, (family, paper) in enumerate(manuscripts):
        score = scores[index]
        selected = set()
        for indices in pool_indices.values():
            selected.update(sorted(indices, key=lambda j: (-float(score[j]), int(records[j]["id"])))[:10])
        selected.update(record_index[problem_id] for problem_id in previous_a[paper["dir"]])
        exact_names = defaultdict(list)
        evidence_expansions = defaultdict(list)
        padded_query = f" {queries[index]} "
        for name, indices in eponym_index.items():
            if f" {name} " in padded_query:
                for candidate in indices:
                    selected.add(candidate)
                    exact_names[candidate].append(name)
        for expansion in expansions:
            if expansion["manuscript_dir"] == paper["dir"]:
                candidate = record_index[int(expansion["candidate_id"])]
                selected.add(candidate)
                evidence_expansions[candidate].append(expansion)
        targets = named_targets(" ".join((paper["title"], extracts[paper["dir"]]["family_summary"], extracts[paper["dir"]]["abstract"])))
        # Explicit numbered Erdős lookups are separate from ordinary topic hits.
        explicit_erdos = {int(match.group(1)) for match in re.finditer(r"erdos\s+(?:problem\s+)?(?:number\s+)?(\d+)", queries[index])}
        source_erdos = source_erdos_references(Path(inventory["repo_path"]), paper["source_tex_dir"])
        explicit_erdos.update(source_erdos)
        for number in source_erdos:
            selected.update(erdos_number_index.get(number, []))
        candidates = []
        for candidate in sorted(selected, key=lambda j: (-float(score[j]), int(records[j]["id"]))):
            record = records[candidate]
            problem_id = int(record["id"])
            erdos_match = re.search(r"erdos problem\s+(\d+)", normalise(record["title"]))
            item = {
                "row_key": f"{paper['dir']}::{('A' if problem_id in pool_a_ids else 'B')}::{problem_id}",
                "candidate_id": problem_id, "pool": "A" if problem_id in pool_a_ids else "B",
                "title": record["title"], "score": round(float(score[candidate]), 6),
                "exact_eponyms": sorted(exact_names[candidate]),
                "main_source_expansions": evidence_expansions[candidate],
                "duplicate_cluster": duplicate_lookup.get(problem_id, [problem_id]),
                "category": record.get("category", {}).get("display_name"),
                "definition_path": str(args.site / "attacks/open_problems/top_problems/definitions" / f"{problem_id}.tex") if problem_id in pool_a_ids else None,
                "statement": record.get("statement", ""), "background": record.get("background", ""),
                "published": record.get("published"), "problem_number": record.get("problem_number"),
                "erdos_out_of_scope": bool(erdos_match),
                "explicit_erdos_number_hit": bool(erdos_match and int(erdos_match.group(1)) in explicit_erdos),
                "explicit_erdos_source_paths": source_erdos.get(int(erdos_match.group(1)), []) if erdos_match else [],
            }
            if item["pool"] == "A" and problem_id in previous_a[paper["dir"]]:
                # Preserve old retrieval evidence exactly; scores are not
                # verdicts, but stability helps reviewers audit additive work.
                prior = previous_a[paper["dir"]][problem_id]
                added_expansions = item["main_source_expansions"]
                explicit_source_paths = item["explicit_erdos_source_paths"]
                explicit_hit = item["explicit_erdos_number_hit"]
                item = {**item, **prior}
                item["explicit_erdos_number_hit"] = explicit_hit or prior["explicit_erdos_number_hit"]
                item["explicit_erdos_source_paths"] = sorted(set(explicit_source_paths + prior.get("explicit_erdos_source_paths", [])))
                # Scores and stable keys remain exact; genuinely new primary
                # source evidence augments the previous retrieval annotations.
                item["main_source_expansions"] = list({json.dumps(value, sort_keys=True): value for value in prior["main_source_expansions"] + added_expansions}.values())
            candidates.append(item)
            if erdos_match:
                erdos_hits.append({"family": family["family"], "manuscript_dir": paper["dir"], **item})
        rows.append({
            "family": family["family"], "subject": family["subject"], "manuscript_dir": paper["dir"],
            "title": paper["title"], "pdf_path": paper["pdf_path"], "source_tex_dir": paper["source_tex_dir"],
            "source_tex_files": paper["source_tex_files"],
            "inputs_md": paper["inputs_md"], "lean_doc": family["lean_doc"], "named_targets": targets,
            "numbered_erdos_source_references": [{"number": number, "source_paths": paths, "catalogue_ids": [int(records[j]["id"]) for j in erdos_number_index.get(number, [])]} for number, paths in source_erdos.items()],
            "candidates": candidates,
        })
    output = {
        "schema_version": 1, "source_commit": inventory["source_commit"],
        "method": "Title-weighted word/unigram+bigram TF-IDF cosine top ten PER POOL, plus exact normalised eponym/acronym hits; diacritic/dash/and and neighbourhood normalisation; additive Pool A preservation when requested.",
        "warning": "Candidate scores and normalised-title clusters are retrieval aids, not equivalence or solved verdicts.",
        "pools": pools, "duplicate_clusters": duplicates, "manuscripts": rows,
        "main_source_target_expansions": expansions,
        "new_target_proposal_policy": "After exhausting both pools and checking statement-level duplicates, propose each unmatched main claim or distinct standalone subcase with a precise independently posed statement, source theorem and original problem source, known parent IDs, and duplicate-check evidence. Do not allocate IDs: the coordinating agent reserves monotonic IDs above the registry watermark. Numbered Erdős matches remain report-only. Proposed full/stronger new targets require independent review and the same user approval gate as existing targets.",
        "counts": {"manuscripts": len(rows), "candidate_pairs": sum(len(row["candidates"]) for row in rows), "duplicate_clusters": len(duplicates)},
    }
    (args.local / "candidates.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    (args.local / "erdos_candidate_hits.json").write_text(json.dumps(erdos_hits, indent=2, ensure_ascii=False) + "\n")
    packet_dir = args.local / "work_packets"
    packet_dir.mkdir(exist_ok=True)
    by_subject = defaultdict(list)
    for row in rows:
        by_subject[row["subject"]].append(row)
    subjects = []
    for subject, subset in by_subject.items():
        slug = re.sub(r"[^a-z0-9]+", "-", normalise(subject)).strip("-")
        subjects.append({"subject": subject, "slug": slug, "manuscripts": len(subset), "candidate_pairs": sum(len(row["candidates"]) for row in subset)})
        (packet_dir / f"{slug}.json").write_text(json.dumps({"subject": subject, "source_commit": inventory["source_commit"], "pools": pools, "new_target_proposal_policy": output["new_target_proposal_policy"], "manuscripts": subset}, indent=2, ensure_ascii=False) + "\n")
        if previous:
            earlier_keys = {candidate["row_key"] for manuscript in previous["manuscripts"] for candidate in manuscript["candidates"]}
            delta = []
            for manuscript in subset:
                new_candidates = [candidate for candidate in manuscript["candidates"] if candidate["row_key"] not in earlier_keys]
                if new_candidates:
                    delta.append({**manuscript, "candidates": new_candidates})
            (packet_dir / f"{slug}-delta-b.json").write_text(json.dumps({"subject": subject, "source_commit": inventory["source_commit"], "pools": pools, "manuscripts": delta, "note": "Additive rows only; previous Pool A keys retained in full packet."}, indent=2, ensure_ascii=False) + "\n")
        text = [f"# {subject}: adjudication work packet", "", f"Pinned source: {inventory['source_commit']}", f"OpenAI clone: {inventory['repo_path']}", "Pool B: " + ("searched" if pools["B"]["searched"] else "UNSEARCHED; authoritative full registry is missing."), "", "Read main theorem sources, INPUTS.md where present, and Lean scope before assigning any full/stronger/partial verdict. Every candidate is retrieval only. Erdős collection is excluded. A duplicate title needs statement comparison.", "", output["new_target_proposal_policy"], ""]
        for row in subset:
            extract = extracts[row["manuscript_dir"]]
            text += [f"## Family {row['family']}: {row['title']}", f"Manuscript: {row['manuscript_dir']}", f"Sources: {inventory['repo_path']}/{row['source_tex_dir']}", f"PDF: {inventory['repo_path']}/{row['pdf_path']}", f"INPUTS: {row['inputs_md'] or 'none'}", f"Lean scope: {row['lean_doc'] or 'none'}", "", "OpenAI abstract (local retrieval aid; never publish):", extract["abstract"], ""]
            for candidate in row["candidates"]:
                text += [f"### Candidate {candidate['candidate_id']}: {candidate['title']}", f"Pool {candidate['pool']}; cosine {candidate['score']}; exact eponyms {candidate['exact_eponyms']}; possible duplicate IDs {candidate['duplicate_cluster']}", f"Erdős out of scope: {candidate['erdos_out_of_scope']}", "", candidate["statement"], candidate["background"], ""]
                if definitions[candidate["candidate_id"]]:
                    text += ["Full on-site definition (including statement and catalogue scope):", "```tex", definitions[candidate["candidate_id"]], "```", ""]
        (packet_dir / f"{slug}.md").write_text("\n".join(text), encoding="utf-8")
    (packet_dir / "subjects.json").write_text(json.dumps(subjects, indent=2) + "\n")
    assert len(rows) == 722
    assert len(subjects) == 17
    print(json.dumps({"counts": output["counts"], "pools": pools, "subjects": subjects}, indent=2))


if __name__ == "__main__":
    main()
