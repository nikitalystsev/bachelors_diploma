#!/usr/bin/env python3
"""Print top-voted response scenarios for each questionnaire situation/level."""

import argparse
import csv
import json
import re
from pathlib import Path


ROOT_MARKERS = ("requirements.txt", "src")
DEFAULT_INPUT_PATH = Path("src/data/research/responses.csv")
LEVEL_ORDER = {"Низкая": 0, "Средняя": 1, "Высокая": 2}
HEADER_RE = re.compile(
    r"^(?P<scenario_id>\d+)\. В диалоге (?P<situation>.*?)\. "
    r"Выберите.*?грани (?P<facet>.*?), выставленной.*? "
    r"\[(?P<level>.*?)\]$"
)
CONTINUATION_RE = re.compile(r"^[Чч]то\s+(?!ж(?:,|\s|$))")


def find_project_root(start: Path) -> Path:
    for directory in (start, *start.parents):
        if all((directory / marker).exists() for marker in ROOT_MARKERS):
            return directory
    raise RuntimeError(f"Cannot find project root from {start}")


def resolve_project_path(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def split_answer(answer: str) -> list[str]:
    scenarios: list[str] = []
    for part in answer.split(";"):
        scenario = normalize_text(part)
        if not scenario:
            continue

        if scenarios and CONTINUATION_RE.match(scenario):
            scenarios[-1] = f"{scenarios[-1]}; {scenario}"
        else:
            scenarios.append(scenario)

    return scenarios


def parse_questions(headers: list[str]) -> list[dict[str, int | str]]:
    questions: list[dict[str, int | str]] = []
    for column_index, header in enumerate(headers[1:], start=1):
        match = HEADER_RE.match(header)
        if not match:
            raise ValueError(f"Cannot parse header in column {column_index + 1}: {header}")

        questions.append(
            {
                "column_index": column_index,
                "scenario_id": int(match.group("scenario_id")),
                "situation": normalize_text(match.group("situation")),
                "facet": normalize_text(match.group("facet")),
                "level": normalize_text(match.group("level")),
            }
        )

    return sorted(
        questions,
        key=lambda question: (
            int(question["scenario_id"]),
            LEVEL_ORDER.get(str(question["level"]), 99),
        ),
    )


def read_rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.reader(file))


def top_voted_scenarios(
    response_rows: list[list[str]],
    question: dict[str, int | str],
) -> dict[str, object]:
    column_index = int(question["column_index"])
    counts: dict[str, int] = {}
    respondents = 0
    total_votes = 0

    for row_number, row in enumerate(response_rows, start=2):
        if column_index >= len(row):
            raise ValueError(f"Row {row_number} has no column {column_index + 1}")

        answer = normalize_text(row[column_index])
        if not answer:
            continue

        respondents += 1
        for scenario in split_answer(answer):
            counts[scenario] = counts.get(scenario, 0) + 1
            total_votes += 1

    max_votes = max(counts.values(), default=0)
    top_scenarios = [
        {
            "scenario": scenario,
            "votes": votes,
            "respondent_share": round(votes / respondents, 3) if respondents else 0.0,
        }
        for scenario, votes in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if votes == max_votes
    ]

    return {
        "scenario_id": question["scenario_id"],
        "situation": question["situation"],
        "facet": question["facet"],
        "level": question["level"],
        "respondents": respondents,
        "total_votes": total_votes,
        "max_votes": max_votes,
        "top_scenarios": top_scenarios,
    }


def build_report(root: Path, input_path: Path) -> dict[str, object]:
    rows = read_rows(input_path)
    if len(rows) < 2:
        raise ValueError("responses.csv must contain a header row and at least one response row")

    questions = parse_questions(rows[0])
    response_rows = rows[1:]
    results = [top_voted_scenarios(response_rows, question) for question in questions]

    return {
        "source": display_path(root, input_path),
        "questions": len(results),
        "respondents": len(response_rows),
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count top-voted response scenarios for each situation/level in responses.csv."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"CSV file to parse, relative to project root by default ({DEFAULT_INPUT_PATH}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path, relative to project root by default.",
    )
    return parser.parse_args()


def main() -> None:
    root = find_project_root(Path(__file__).resolve().parent)
    args = parse_args()
    input_path = resolve_project_path(root, args.input)

    if not input_path.exists():
        raise FileNotFoundError(f"Cannot find input file: {input_path}")

    report = build_report(root, input_path)
    json_text = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        output_path = resolve_project_path(root, args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_text + "\n", encoding="utf-8")
    else:
        print(json_text)


if __name__ == "__main__":
    main()
