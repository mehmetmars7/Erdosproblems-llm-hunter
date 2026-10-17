#!/usr/bin/env python3
"""Import verified, offline We-Solve destinations without changing research text.

Identity comes from published aliases/API records and the contribution page's
Original source control. Display ranks and attempt ordering are never identifiers.
The checked-in manifest is enough for normal site builds; this importer is only
needed when refreshing it from a local copy of the published We-Solve exports.
"""

import argparse
import hashlib
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlparse


SITE_URL = "https://we-solve.github.io"
RESEARCH_URL = "https://github.com/we-solve/research/blob/main/"
OLD_REPOSITORY_PATH = "/mehmetmars7/Erdosproblems-llm-hunter/blob/"
DEFAULT_ROOT = Path(__file__).resolve().parents[1]


class MappingError(ValueError):
    """A destination cannot be established uniquely from the published records."""


class OriginalSourceParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a":
            if "".join(self._text).strip() == "Original source" and self._href:
                self.links.append(self._href)
            self._href = None
            self._text = []


def original_sources(html):
    parser = OriginalSourceParser()
    parser.feed(html)
    paths = []
    for link in parser.links:
        parsed = urlparse(link)
        if parsed.scheme != "https" or parsed.netloc != "github.com":
            continue
        if not parsed.path.startswith(OLD_REPOSITORY_PATH):
            continue
        revision_and_path = parsed.path[len(OLD_REPOSITORY_PATH):]
        if "/" not in revision_and_path:
            raise MappingError(f"Invalid Original source URL: {link}")
        revision, path = revision_and_path.split("/", 1)
        paths.append((revision, safe_relative(unquote(path))))
    return paths


def original_paths(html):
    return [path for _, path in original_sources(html)]


def safe_relative(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or any(c in value for c in "\\\n\r"):
        raise MappingError(f"Unsafe relative path: {value!r}")
    return path.as_posix()


def json_file(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_ids(root, references):
    """Read all pinned source blob IDs in one read-only Git operation."""
    references = sorted(set(references))
    if not references:
        return {}
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "--batch-check=%(objectname) %(objecttype)"],
        input="\n".join(references) + "\n", capture_output=True, text=True, check=False,
    )
    if result.returncode:
        return {}
    lines = result.stdout.splitlines()
    if len(lines) != len(references):
        raise MappingError("Git returned an incomplete pinned-source inventory")
    return {reference: line.split()[0] for reference, line in zip(references, lines)
            if re.fullmatch(r"[0-9a-f]{40} blob", line)}


def local_blob_id(path):
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def pinned_revision(value):
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def page_url(site, route):
    if not route.startswith("/") or route.startswith("//") or not route.endswith("/"):
        raise MappingError(f"Invalid published route: {route!r}")
    relative = safe_relative(route.strip("/"))
    if not (site / relative / "index.html").is_file():
        raise MappingError(f"Published destination is missing: {route}")
    return SITE_URL + route


def source_fields(root, research, local_path, exported_path):
    """Retain fingerprints of both files; exported sources have known cleanup.

    We-Solve removes import metadata and some provenance wording from manuscripts.
    Byte equality would therefore discard valid identity mappings. Runtime builds
    use local_sha256 to avoid redirecting later edits to an older imported file.
    """
    local_path = safe_relative(local_path)
    exported_path = safe_relative(exported_path)
    local = root / local_path
    exported = research / exported_path
    fields = {"source_path": local_path}
    if local.is_file():
        fields["local_sha256"] = sha256(local)
    if local.is_file() and exported.is_file():
        fields.update(source_url=RESEARCH_URL + quote(exported_path, safe="/"),
                      exported_sha256=sha256(exported))
    return fields


def load_site_records(root):
    specs = (
        ("erdos", "erdos_data.js", "erdosProblems"),
        ("mo", "mo_data.js", "moProblems"),
        ("open_problems", "open_problems_data.js", "openProblems"),
        ("economics", "economics_data.js", "ECONOMICS_DATA"),
    )
    result = {}
    for kind, filename, variable in specs:
        text = (root / "docs/data" / filename).read_text(encoding="utf-8")
        marker = re.search(r"(?:var |window\.)" + variable + r"\s*=\s*", text)
        if marker is None:
            raise MappingError(f"Cannot read {variable} from {filename}")
        data, _ = json.JSONDecoder().raw_decode(text[marker.end():].lstrip())
        rows = data.items() if isinstance(data, dict) else ((row["id"], row) for row in data)
        for identity, row in rows:
            identity = str(identity)
            # The same MO records are also exposed in the open-problems catalogue.
            key = identity if kind == "open_problems" and identity.startswith("mo:") else f"{kind}:{identity}"
            if key in result and result[key].get("attacks") != row.get("attacks"):
                raise MappingError(f"Conflicting duplicate catalogue identity: {key}")
            result.setdefault(key, row)
    return result


def problem_alias(key):
    kind, identity = key.split(":", 1)
    return {"erdos": "ERDOS-", "mo": "MO-", "open_problems": "TOP-", "economics": "ECON-"}[kind] + identity


def register_source(sources, path, entry):
    if path in sources and sources[path] != entry:
        raise MappingError(f"Ambiguous Original source mapping: {path}")
    sources[path] = entry


def published_problem_codes(site):
    """WS filenames retain each record's allocated code after canonical merges.

    The JSON number field identifies the canonical destination, so it cannot be
    used to recover a merged record's original allocation. Neither display labels
    nor ranks participate in this index.
    """
    by_record = {}
    by_code = {}
    for path in sorted((site / "api/v1/problems").glob("WS-*.json")):
        code = path.stem
        if not re.fullmatch(r"WS-[1-9][0-9]*", code):
            raise MappingError(f"Invalid permanent problem code: {code}")
        api = json_file(path)
        problem_id = api["record"]["problem_id"]
        if problem_id in by_record:
            raise MappingError(f"Multiple permanent codes for problem record: {problem_id}")
        by_record[problem_id] = code
        by_code[code] = api
    if not by_record:
        raise MappingError("Published permanent WS problem endpoints are missing")
    return by_record, by_code


def validate_existing_bindings(previous, problems, code_records, allow_canonical_merges):
    """Refuse to silently change a previously published old-ID to WS binding."""
    for key, old in previous.get("problems", {}).items():
        new = problems.get(key)
        if new is None:
            raise MappingError(f"Previously mapped problem disappeared: {key}")
        for field in ("alias", "record_code", "problem_id"):
            if field in old and old[field] != new[field]:
                raise MappingError(f"Permanent problem binding changed: {key}: {field}")
        changed = any(field in old and old[field] != new[field]
                      for field in ("code", "canonical_problem_id", "canonical_alias"))
        if not changed:
            continue
        prior_canonical = code_records.get(old.get("code"))
        confirmed_merge = (
            prior_canonical is not None
            and prior_canonical["canonical_problem_id"] == new["canonical_problem_id"]
            and prior_canonical["canonical_alias"] == new["canonical_alias"]
            and f"WS-{prior_canonical['number']}" == new["code"]
        )
        if not allow_canonical_merges or not confirmed_merge:
            raise MappingError(f"Canonical problem binding changed: {key}; "
                               "an explicit, published canonical merge is required")


def build_manifest(root, site, research, *, allow_canonical_merges=False):
    aliases = json_file(research / "browse/aliases.json")
    record_codes, code_records = published_problem_codes(site)
    records = load_site_records(root)
    problems = {}
    sources = {}
    unmapped_problems = []
    unavailable_sources = []
    unverified_sources = []
    stale_sources = []

    for key, row in sorted(records.items()):
        alias = problem_alias(key)
        meta = aliases["problems"].get(alias)
        if meta is None:
            unmapped_problems.append(key)
            continue
        api = json_file(site / "api/v1/problems" / f"{alias}.json")
        record = api["record"]
        if api["alias"] != alias or record["problem_id"] != meta["id"]:
            raise MappingError(f"Problem identity mismatch: {alias}")
        if record["statement_revision_id"] != meta["statement_revision_id"]:
            raise MappingError(f"Statement revision mismatch: {alias}")
        canonical = aliases["problems"].get(api["canonical_alias"])
        if not canonical or canonical["id"] != api["canonical_problem_id"]:
            raise MappingError(f"Canonical identity mismatch: {alias}")
        problem_id = record["problem_id"]
        canonical_id = api["canonical_problem_id"]
        if problem_id not in record_codes or canonical_id not in record_codes:
            raise MappingError(f"Permanent problem code is missing: {alias}")
        canonical_code = f"WS-{api['number']}"
        if (record_codes[canonical_id] != canonical_code
                or code_records[canonical_code]["record"]["problem_id"] != canonical_id):
            raise MappingError(f"Permanent canonical code mismatch: {alias}")
        original_api = code_records[record_codes[problem_id]]
        if (original_api["alias"] != alias
                or original_api["canonical_problem_id"] != canonical_id
                or original_api["canonical_alias"] != api["canonical_alias"]
                or original_api["url"] != api["url"]):
            raise MappingError(f"Permanent problem endpoint mismatch: {alias}")
        entry = {"alias": alias, "code": canonical_code,
                 "record_code": record_codes[problem_id], "problem_id": problem_id,
                 "canonical_problem_id": canonical_id, "canonical_alias": api["canonical_alias"],
                 "url": page_url(site, api["url"])}
        local_path = row.get("definition_file") or row.get("definitionFile")
        if local_path:
            exported = f"{safe_relative(meta['path'])}/{safe_relative(record['statement_artifact']['path'])}"
            entry.update(source_fields(root, research, local_path, exported))
            commits = {source["snapshot"].get("commit") for source in record.get("sources", [])
                       if source.get("snapshot", {}).get("repository_url") == "https://github.com/mehmetmars7/Erdosproblems-llm-hunter"}
            if len(commits) == 1 and pinned_revision(next(iter(commits))):
                entry["original_revision"] = next(iter(commits))
            if "source_url" not in entry:
                unavailable_sources.append(local_path)
        problems[key] = entry

    previous_path = root / "lists/we_solve_links.json"
    if previous_path.exists():
        validate_existing_bindings(json_file(previous_path), problems, code_records, allow_canonical_merges)

    for alias, meta in sorted(aliases["contributions"].items()):
        api_dir = site / "api/v1/contributions" / alias
        revisions = [json_file(path) for path in sorted(api_dir.glob("r*.json"))]
        matching = [api for api in revisions if api["record"]["revision_id"] == meta["revision_id"]]
        if len(matching) != 1:
            raise MappingError(f"Expected one matching published revision: {alias}")
        api = matching[0]
        record = api["record"]
        if api["alias"] != alias or record["contribution_id"] != meta["id"]:
            raise MappingError(f"Contribution identity mismatch: {alias}")
        url = page_url(site, api["url"])
        html = (site / api["url"].strip("/") / "index.html").read_text(encoding="utf-8")
        paths = original_sources(html)
        if len(paths) > 1:
            raise MappingError(f"Multiple Original source controls: {alias}")
        for original_revision, path in paths:
            # Reviews may point to a metadata file while exporting a history file.
            # Only redirect a source when the exact filename is an exported artifact.
            artifacts = [item for item in record.get("artifacts", [])
                         if item.get("location") == "in_repository"
                         and PurePosixPath(item["path"]).name == PurePosixPath(path).name]
            if len(artifacts) > 1:
                raise MappingError(f"Ambiguous exported artifact: {alias}: {path}")
            entry = {"kind": "contribution", "alias": alias,
                     "revision": api["revision"], "url": url,
                     "original_revision": original_revision}
            if (root / path).is_file():
                entry["local_sha256"] = sha256(root / path)
            if artifacts:
                exported = f"{safe_relative(meta['path'])}/{safe_relative(artifacts[0]['path'])}"
                entry.update(source_fields(root, research, path, exported))
            if "source_url" not in entry:
                unavailable_sources.append(path)
            register_source(sources, path, entry)

    verifiable = [(entry.get("source_path"), entry) for entry in problems.values() if entry.get("source_path")]
    verifiable += list(sources.items())
    references = [f"{entry['original_revision']}:{path}" for path, entry in verifiable
                  if pinned_revision(entry.get("original_revision"))]
    blobs = git_blob_ids(root, references)
    verified_count = 0
    for path, entry in verifiable:
        reference = f"{entry.get('original_revision', '')}:{path}"
        blob = blobs.get(reference)
        if not blob or not (root / path).is_file():
            unverified_sources.append(path)
            entry.pop("source_url", None)
            if entry.get("kind") == "contribution":
                sources.pop(path, None)
        elif local_blob_id(root / path) != blob:
            stale_sources.append(path)
            entry.pop("source_url", None)
            if entry.get("kind") == "contribution":
                sources.pop(path, None)
        else:
            entry["original_blob"] = blob
            verified_count += 1

    exposed_paths = {attack["file_path"] for row in records.values()
                     for attack in row.get("attacks", []) if attack.get("file_path")}
    unmapped_sources = sorted(exposed_paths - sources.keys())
    return {
        "schema_version": 1,
        "problems": problems,
        "sources": dict(sorted(sources.items())),
        "audit": {
            "identity_evidence": "Published API records, research alias index, and Original source controls",
            "source_policy": "Keep the original source link when unmapped, unavailable, or changed since this import",
            "unmapped_problems": unmapped_problems,
            "unmapped_sources": unmapped_sources,
            "unavailable_source_files": sorted(set(unavailable_sources)),
            "unverified_source_files": sorted(set(unverified_sources)),
            "stale_source_files": sorted(set(stale_sources)),
            "verified_original_blobs": verified_count,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--research", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-canonical-merges", action="store_true",
                        help="Accept changed canonical destinations only when the old WS endpoint confirms the merge")
    args = parser.parse_args()
    manifest = build_manifest(args.root, args.site, args.research,
                              allow_canonical_merges=args.allow_canonical_merges)
    output = args.output or args.root / "lists/we_solve_links.json"
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    audit = manifest["audit"]
    print(f"Mapped {len(manifest['problems'])} problems and {len(manifest['sources'])} source paths; "
          f"preserved {len(audit['unmapped_problems'])} unmapped problems, "
          f"{len(audit['unmapped_sources'])} unmapped attempts, and "
          f"{len(audit['unavailable_source_files'])} unavailable source files; "
          f"verified {audit['verified_original_blobs']} pinned original blobs, "
          f"{len(audit['stale_source_files'])} stale and {len(audit['unverified_source_files'])} unverified sources.")


if __name__ == "__main__":
    main()
