#!/usr/bin/env python3
"""Calculate summary metrics for the research section."""

import csv
from pathlib import Path


LEVELS = ("Низкая", "Средняя", "Высокая")


def find_project_root(start: Path) -> Path:
    for directory in (start, *start.parents):
        if (directory / "requirements.txt").exists() and (directory / "src").is_dir():
            return directory
    raise RuntimeError(f"Cannot find project root from {start}")


ROOT = find_project_root(Path(__file__).resolve().parent)
ANALYSIS_DIR = ROOT / "src/data/research/analysis"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def calculate_consensus(rows: list[dict[str, str]]) -> tuple[float, dict[str, float]]:
    # Для каждой пары "ситуация + степень" берем самый частый полный набор ответов.
    max_share_by_question: dict[tuple[str, str, str], float] = {}

    for row in rows:
        key = (row["scenario_id"], row["facet"], row["level"])
        share = float(row["share"])
        max_share_by_question[key] = max(max_share_by_question.get(key, 0.0), share)

    shares = list(max_share_by_question.values())
    by_level = {}
    for level in LEVELS:
        # Отбираем согласованность только для одной степени проявления.
        values = []
        for key, share in max_share_by_question.items():
            question_level = key[2]
            if question_level == level:
                values.append(share)

        by_level[level] = sum(values) / len(values)

    return sum(shares) / len(shares), by_level


def calculate_method_match(rows: list[dict[str, str]]) -> tuple[float, dict[str, float]]:
    # В этом CSV одна строка уже соответствует одной паре "ситуация + степень".
    shares = [float(row["share"]) for row in rows]
    by_level = {}
    for level in LEVELS:
        # Считаем среднее соответствие методу отдельно для каждой степени.
        values = [float(row["share"]) for row in rows if row["level"] == level]
        by_level[level] = sum(values) / len(values)

    return sum(shares) / len(shares), by_level


def main() -> None:
    answer_counts = read_csv(ANALYSIS_DIR / "answer_set_counts.csv")
    method_matches = read_csv(ANALYSIS_DIR / "method_option_match.csv")

    consensus_average, consensus_by_level = calculate_consensus(answer_counts)
    method_average, method_by_level = calculate_method_match(method_matches)

    print(f"Средняя согласованность: {consensus_average:.0%}")
    print("Средняя согласованность по степеням:")
    for level, value in consensus_by_level.items():
        print(f"{level}: {value:.0%}")

    print()
    print(f"Среднее соответствие разработанному методу: {method_average:.0%}")
    print("Соответствие разработанному методу по степеням:")
    for level, value in method_by_level.items():
        print(f"{level}: {value:.0%}")


if __name__ == "__main__":
    main()
