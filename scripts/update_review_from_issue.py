#!/usr/bin/env python3
import csv
import json
import os
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
LISTS_DIR = BASE_DIR / "lists"
REVIEWS_DIR = BASE_DIR / "reviews"


FIELD_LABELS = {
    "problem_type": "Problem type",
    "problem_id": "Problem ID",
    "verdict": "Verdict",
    "explanation": "Explanation",
    "citations": "Citation links (required for accepted)",
    "discussion_link": "Related discussion link (optional)",
}

VERDICT_MAP = {
    "flagged": ("flagged", "flagged"),
    "incorrect": ("incorrect", "incorrect"),
    "known": ("known", "known"),
    "technicality": ("technicality", "technicality"),
    "trivial": ("trivial", "trivial"),
    "partial": ("partial", "partial"),
    "plausible": ("plausible", "plausible"),
    "accepted": ("accepted", "accepted"),
}


def extract_field(body, label):
    pattern = rf"^### {re.escape(label)}\s*$\n([\s\S]*?)(?=^### |\Z)"
    match = re.search(pattern, body, flags=re.MULTILINE)
    if not match:
        return ""
    value = match.group(1).strip()
    if value.lower() in ("_no response_", "no response"):
        return ""
    return value


def load_problem_ids(problem_type):
    if problem_type == "erdos":
        path = LISTS_DIR / "erdos_problems.csv"
        key = "number"
    else:
        path = LISTS_DIR / "mo_problems.csv"
        key = "question_id"
    ids = set()
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ids.add(row.get(key, "").strip())
    return ids


def parse_links(value):
    links = []
    for line in value.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^https?://", line):
            links.append(line)
    return links


def main():
    body = os.environ.get("ISSUE_BODY", "")
    issue_number = os.environ.get("ISSUE_NUMBER", "")
    issue_url = os.environ.get("ISSUE_URL", "")
    issue_author = os.environ.get("ISSUE_AUTHOR", "")
    review_labeler = os.environ.get("REVIEW_LABELER", "")
    issue_created_at = os.environ.get("ISSUE_CREATED_AT", "")

    problem_type_raw = extract_field(body, FIELD_LABELS["problem_type"])
    problem_id = extract_field(body, FIELD_LABELS["problem_id"])
    verdict = extract_field(body, FIELD_LABELS["verdict"])
    explanation = extract_field(body, FIELD_LABELS["explanation"])
    citations_value = extract_field(body, FIELD_LABELS["citations"])
    discussion_link = extract_field(body, FIELD_LABELS["discussion_link"])

    if not problem_type_raw or not problem_id or not verdict:
        raise SystemExit("Missing required fields: problem type, problem id, or verdict.")

    problem_type = problem_type_raw.strip().lower()
    if problem_type not in ("erdos", "mo"):
        raise SystemExit(f"Unknown problem type: {problem_type_raw}")

    problem_id = problem_id.strip()
    if not re.match(r"^\d+$", problem_id):
        raise SystemExit(f"Invalid problem id: {problem_id}")

    valid_ids = load_problem_ids(problem_type)
    if problem_id not in valid_ids:
        raise SystemExit(f"Problem id not found in lists: {problem_type} {problem_id}")

    if verdict not in VERDICT_MAP:
        raise SystemExit(f"Unknown verdict: {verdict}")

    status, label = VERDICT_MAP[verdict]
    if not explanation.strip():
        raise SystemExit("Explanation is required.")

    citations = parse_links(citations_value)
    if status == "accepted":
        if len(citations) < 1:
            raise SystemExit("Accepted verdict requires at least one citation link.")
        if len(explanation.strip()) < 20:
            raise SystemExit("Accepted verdict requires a short explanation (20+ characters).")

    reviewed_by = review_labeler.strip() or issue_author.strip()
    review_data = {
        "status": status,
        "label": label,
        "note": explanation.strip(),
        "citations": citations,
        "discussion_link": discussion_link.strip(),
        "reviewed_by": reviewed_by,
        "reviewed_at": issue_created_at[:10] if issue_created_at else "",
        "issue_number": issue_number,
        "issue_url": issue_url,
    }

    review_dir = REVIEWS_DIR / problem_type
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / f"{problem_id}.json"
    with open(review_path, "w", encoding="utf-8") as f:
        json.dump(review_data, f, indent=2, ensure_ascii=True)
        f.write("\n")

    print(f"Wrote review file: {review_path}")


if __name__ == "__main__":
    main()
