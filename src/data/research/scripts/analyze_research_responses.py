#!/usr/bin/env python3
"""Analyze questionnaire responses exported as CSV."""

import csv
import html
import re
import shutil
from pathlib import Path


def find_project_root(start: Path) -> Path:
    for directory in (start, *start.parents):
        if (
            (directory / "requirements.txt").exists()
            and (directory / "src").is_dir()
            and (directory / ".git").exists()
        ):
            return directory
    raise RuntimeError(f"Cannot find project root from {start}")


ROOT = find_project_root(Path(__file__).resolve().parent)
DEFAULT_INPUT_PATH = ROOT / "src/data/research/responses.csv"
DEFAULT_OUTPUT_DIR = ROOT / "src/data/research/analysis"
DEFAULT_REPORT_IMAGE_DIR = ROOT / "docs/report_system/report/inc/img"
REFERENCE_RESPONSE_INDEX = 2
LEVELS = ("Низкая", "Средняя", "Высокая")
HEADER_RE = re.compile(
    r"^(?P<scenario_id>\d+)\. В диалоге (?P<scenario>.*?)\. "
    r"Выберите.*?грани (?P<facet>.*?), выставленной.*? "
    r"\[(?P<level>.*?)\]$"
)
ANSWER_COUNT_FIELDS = ["scenario_id", "facet", "level", "answer_set", "count", "share"]
METHOD_MATCH_FIELDS = ["scenario_id", "facet", "level", "method_option", "hit", "n", "share"]
CONSENSUS_LEGEND = [
    ("#bf4d45", "<50%"),
    ("#d49436", "50-74%"),
    ("#72a84a", "75-99%"),
    ("#1f7a4d", "100%"),
]
METHOD_MATCH_LEGEND = [
    ("#bf4d45", "<25%"),
    ("#d49436", "25-49%"),
    ("#72a84a", "50-74%"),
    ("#1f7a4d", "75-100%"),
    ("#d5dbe3", "н/д"),
]
FONT_FAMILY = "Arial, sans-serif"


def parse_questions(headers: list[str]) -> list[dict[str, object]]:
    questions = []
    for column_index, header in enumerate(headers):
        if column_index == 0:
            continue

        match = HEADER_RE.match(header)
        if not match:
            raise ValueError(f"Cannot parse header in column {column_index + 1}: {header}")

        questions.append(
            {
                "column_index": column_index,
                "scenario_id": int(match.group("scenario_id")),
                "scenario": match.group("scenario").strip(),
                "facet": match.group("facet").strip(),
                "level": match.group("level").strip(),
            }
        )
    return questions


def summarize(rows: list[list[str]], questions: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """
    Считает согласованность и частоты полных наборов ответов по каждому вопросу
    """
    summaries = []
    count_rows = []
    response_rows = rows[1:] # строки ответов респондентов

    for i, question in enumerate(questions): # по каждому вопросу
        column_index = int(question["column_index"]) # в какой колонке ответ именно на этот вопрос
        answer_sets = [] # че ответили респонденты на данный вопрос
        for row in response_rows:
            answer = re.sub(r"\s+", " ", row[column_index]).strip() # тупо чистка пробелов
            if not answer:
                continue

            answer_sets.append(answer)
        # print(f"answer_sets: {answer_sets}")

        counts: dict[str, int] = {} # сколько раз встретился тот или иной ответ в вопросе
        for answer_set in answer_sets:
            counts[answer_set] = counts.get(answer_set, 0) + 1

        # print(f"counts: {counts}")
        respondents = len(answer_sets)
        # print(f"respondents: {respondents}")
        if counts:
            # какой полный набор выбрали чаще всего и сколько раз его выбрали
            top_answer_set, top_count = max(counts.items(), key=lambda item: item[1])
        else:
            top_answer_set = ""
            top_count = 0

        # согласованность --- доля респондентов, выбравших самый популярный полный набор реакций
        consensus_share = top_count / respondents if respondents else 0.0

        summaries.append(
            {
                "scenario_id": question["scenario_id"],
                "facet": question["facet"],
                "level": question["level"],
                "respondents": respondents,
                "unique_answer_sets": len(counts),
                "top_count": top_count,
                "consensus_share": consensus_share,
                "top_answer_set": top_answer_set,
                "scenario": question["scenario"],
            }
        )

        for answer_set, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            count_rows.append(
                {
                    "scenario_id": question["scenario_id"],
                    "facet": question["facet"],
                    "level": question["level"],
                    "answer_set": answer_set,
                    "count": count,
                    "share": count / respondents if respondents else 0.0,
                }
            )

        # if i in [0, 1]:
        #     print(f"summarizes[{i}] = {summaries[i]}")
        #     print(f"count_rows = {count_rows}")

    # summaries — одна краткая строка на каждый вопрос.
    # count_rows — все частоты ответов для CSV-таблицы.

    return summaries, count_rows


def serialize_csv_value(value: object) -> object:
    return f"{value:.3f}" if isinstance(value, float) else value


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: serialize_csv_value(value) for key, value in row.items()})


def aggregate_by_facet(summaries: list[dict[str, object]]) -> list[dict[str, object]]:
    """
    Агрегирует согласованность трех уровней в одну строку по каждой грани
    """
    grouped: dict[tuple[int, str, str], list[dict[str, object]]] = {}
    # группировка по номеру ситуации, названию грани и тексту ситуации
    for summary in summaries:
        key = (int(summary["scenario_id"]), str(summary["facet"]), str(summary["scenario"]))
        grouped.setdefault(key, []).append(summary)

    rows: list[dict[str, object]] = []
    for (scenario_id, facet, scenario), items in grouped.items():
        avg_consensus_share = sum(float(item["consensus_share"]) for item in items) / len(items)
        min_consensus_share = min(float(item["consensus_share"]) for item in items)
        rows.append(
            {
                "scenario_id": scenario_id,
                "facet": facet,
                "scenario": scenario,
                "avg_consensus_share": avg_consensus_share,
                "min_consensus_share": min_consensus_share,
                "full_consensus_levels": sum(float(item["consensus_share"]) == 1.0 for item in items), # сколько уровней имели полное совпадение ответов, то есть consensus_share == 1.0.
                "levels": len(items), # сколько уровней было в группе
            }
        )

    return rows


def read_reference_answers(
    rows: list[list[str]],
    questions: list[dict[str, object]],
) -> dict[tuple[int, str, str], str]:
    """
    Берет эталонные ответы из строки третьего респондента
    """
    response_rows = rows[1:]
    if REFERENCE_RESPONSE_INDEX >= len(response_rows):
        raise ValueError(f"Cannot read reference answers: response #{REFERENCE_RESPONSE_INDEX + 1} is missing")

    reference_row = response_rows[REFERENCE_RESPONSE_INDEX]
    method_options: dict[tuple[int, str, str], str] = {}

    for question in questions:
        column_index = int(question["column_index"]) # где лежит ответ на этот вопрос
        method_option = re.sub(r"\s+", " ", reference_row[column_index]).strip() # тупо чистка лишних пробелов
        if not method_option:
            continue

        key = (int(question["scenario_id"]), str(question["facet"]), str(question["level"]))
        method_options[key] = method_option
    # print(f"method_options = {method_options}")
    return method_options


def summarize_method_matches(
    rows: list[list[str]],
    questions: list[dict[str, object]],
    method_options: dict[tuple[int, str, str], str],
) -> list[dict[str, object]]:
    """
    Считает долю ответов, полностью совпавших с эталонными ответами третьего респондента
    """
    summaries = []
    response_rows = rows[1:]
    for question in questions:
        key = (int(question["scenario_id"]), str(question["facet"]), str(question["level"]))
        method_option = method_options.get(key)
        if method_option is None:
            continue

        normalized_method_option = re.sub(r"\s+", " ", method_option).strip() # тупо чистка лишних пробелов
        column_index = int(question["column_index"]) # где лежит ответ на вопрос
        answers = []
        for row in response_rows:
            answer = re.sub(r"\s+", " ", row[column_index]).strip() # тупо чистка лишних пробелов
            if not answer:
                continue

            answers.append(answer)

        respondents = len(answers)
        matches = sum(normalized_method_option == answer for answer in answers) # строго по полному набору реакций

        summaries.append(
            {
                "scenario_id": question["scenario_id"],
                "facet": question["facet"],
                "level": question["level"],
                "method_option": method_option,
                "hit": matches,
                "n": respondents,
                "share": matches / respondents if respondents else 0.0,
            }
        )

    return summaries


def svg_text(x: float, y: float, text: str, **attrs: object) -> str:
    attr_text = " ".join(f'{key.replace("_", "-")}="{html.escape(str(value))}"' for key, value in attrs.items())
    return f'<text x="{x}" y="{y}" {attr_text}>{html.escape(text)}</text>'


def color_for_share(share: float) -> str:
    if share >= 0.999:
        return "#2f8f5b"
    if share >= 0.75:
        return "#8fbd5a"
    if share >= 0.5:
        return "#e0a646"
    return "#c55a5a"


def color_for_consensus_share(share: float) -> tuple[str, str]:
    if share >= 0.999:
        return "#1f7a4d", "#ffffff"
    if share >= 0.75:
        return "#72a84a", "#ffffff"
    if share >= 0.5:
        return "#d49436", "#2f2416"
    return "#bf4d45", "#ffffff"


def color_for_method_share(share: float | None) -> tuple[str, str, str]:
    if share is None:
        return "#d5dbe3", "#52606d", "н/д"
    if share >= 0.75:
        return "#1f7a4d", "#ffffff", f"{share:.0%}"
    if share >= 0.5:
        return "#72a84a", "#ffffff", f"{share:.0%}"
    if share >= 0.25:
        return "#d49436", "#2f2416", f"{share:.0%}"
    return "#bf4d45", "#ffffff", f"{share:.0%}"


def write_level_heatmap(
    path: Path,
    facet_rows: list[dict[str, object]],
    title: str,
    subtitle: str,
    legend_items: list[tuple[str, str]],
    cell_value,
    level_header_offset: float,
) -> None:
    rows = sorted(facet_rows, key=lambda row: int(row["scenario_id"]))
    width = 860
    row_height = 30
    top = 114
    bottom = 38
    height = top + row_height * len(rows) + bottom
    label_x = 44
    cell_x = 450
    cell_width = 116
    cell_height = 24

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#f7f8fb"/>',
        f'<rect x="34" y="18" width="{width - 68}" height="{height - 36}" rx="18" fill="#ffffff"/>',
        svg_text(
            label_x,
            34,
            title,
            font_family=FONT_FAMILY,
            font_size=20,
            font_weight=700,
            fill="#172033",
        ),
        svg_text(
            label_x,
            58,
            subtitle,
            font_family=FONT_FAMILY,
            font_size=12,
            fill="#667085",
        ),
    ]

    for index, (color, label) in enumerate(legend_items):
        x = label_x + index * 90
        parts.append(f'<rect x="{x}" y="70" width="18" height="10" rx="5" fill="{color}"/>')
        parts.append(
            svg_text(
                x + 24,
                79,
                label,
                font_family=FONT_FAMILY,
                font_size=11,
                fill="#475467",
            )
        )

    parts.append(
        svg_text(
            label_x,
            112,
            "Грань",
            font_family=FONT_FAMILY,
            font_size=12,
            font_weight=700,
            fill="#344054",
        )
    )
    for index, level in enumerate(LEVELS):
        x = cell_x + index * cell_width
        parts.append(
            svg_text(
                x + level_header_offset,
                112,
                level,
                font_family=FONT_FAMILY,
                font_size=12,
                font_weight=700,
                fill="#344054",
                text_anchor="middle",
            )
        )

    for row_index, row in enumerate(rows):
        y = top + row_index * row_height
        scenario_id = int(row["scenario_id"])
        label = f'{scenario_id}. {row["facet"]}'
        if row_index % 2 == 0:
            parts.append(f'<rect x="32" y="{y}" width="764" height="{row_height}" rx="7" fill="#f9fafc"/>')

        parts.append(
            svg_text(
                label_x,
                y + 18,
                label[:47],
                font_family=FONT_FAMILY,
                font_size=12,
                fill="#263244",
            )
        )
        for col_index, level in enumerate(LEVELS):
            x = cell_x + col_index * cell_width
            fill, text_fill, text = cell_value(scenario_id, level)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_width - 12}" height="{cell_height}" '
                f'rx="8" fill="{fill}"/>'
            )
            parts.append(
                svg_text(
                    x + (cell_width - 12) / 2,
                    y + 16,
                    text,
                    font_family=FONT_FAMILY,
                    font_size=12,
                    font_weight=700,
                    fill=text_fill,
                    text_anchor="middle",
                )
            )

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def write_heatmap(path: Path, summaries: list[dict[str, object]]) -> None:
    by_key = {(int(summary["scenario_id"]), str(summary["level"])): summary for summary in summaries}

    def consensus_cell(scenario_id: int, level: str) -> tuple[str, str, str]:
        share = float(by_key[(scenario_id, level)]["consensus_share"])
        fill, text_fill = color_for_consensus_share(share)
        return fill, text_fill, f"{share:.0%}"

    write_level_heatmap(
        path,
        aggregate_by_facet(summaries),
        "Согласованность ответов",
        "Доля респондентов, выбравших наиболее частый полный набор реакций",
        CONSENSUS_LEGEND,
        consensus_cell,
        52.0,
    )


def write_method_match_heatmap(
    path: Path,
    facet_rows: list[dict[str, object]],
    summaries: list[dict[str, object]],
) -> None:
    by_key = {(int(summary["scenario_id"]), str(summary["level"])): summary for summary in summaries}

    def method_cell(scenario_id: int, level: str) -> tuple[str, str, str]:
        summary = by_key.get((scenario_id, level))
        return color_for_method_share(float(summary["share"]) if summary else None)

    write_level_heatmap(
        path,
        facet_rows,
        "Агрегированные данные опроса респондентов",
        "Доля респондентов, выбравших вариант реакции, порождённой описанными в ходе исследования правилами",
        METHOD_MATCH_LEGEND,
        method_cell,
        58.0,
    )


def write_bar_chart(path: Path, facet_rows: list[dict[str, object]]) -> None:
    rows = sorted(facet_rows, key=lambda row: (float(row["avg_consensus_share"]), int(row["scenario_id"])))
    label_width = 300
    bar_width = 260
    row_height = 24
    top = 54
    width = label_width + bar_width + 70
    height = top + row_height * len(rows) + 35

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        svg_text(20, 25, "Средняя согласованность по граням", font_size=16, font_weight=700, fill="#202124"),
        svg_text(20, 45, "Среднее значение по трем уровням выраженности", font_size=11, fill="#5f6368"),
    ]

    for index, row in enumerate(rows):
        y = top + index * row_height
        share = float(row["avg_consensus_share"])
        label = f'{row["scenario_id"]}. {row["facet"]}'
        fill = color_for_share(share)
        parts.append(svg_text(20, y + 15, str(label)[:42], font_size=11, fill="#202124"))
        parts.append(f'<rect x="{label_width}" y="{y + 4}" width="{bar_width}" height="12" fill="#edf0f2"/>')
        parts.append(f'<rect x="{label_width}" y="{y + 4}" width="{bar_width * share:.1f}" height="12" fill="{fill}"/>')
        parts.append(svg_text(label_width + bar_width + 10, y + 15, f"{share:.0%}", font_size=11, fill="#202124"))

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def copy_report_images(output_dir: Path, report_image_dir: Path) -> None:
    report_image_dir.mkdir(parents=True, exist_ok=True)
    images = {
        "agreement_heatmap.svg": "research_agreement_heatmap.svg",
        "agreement_by_facet.svg": "research_agreement_by_facet.svg",
        "method_match_heatmap.svg": "research_method_match_heatmap.svg",
    }
    for source_name, destination_name in images.items():
        source = output_dir / source_name
        if source.exists():
            shutil.copyfile(source, report_image_dir / destination_name)


def main() -> None:
    source_path = DEFAULT_INPUT_PATH
    if not source_path.exists():
        raise FileNotFoundError(f"Cannot find input file: {source_path.relative_to(ROOT)}")

    output_dir = DEFAULT_OUTPUT_DIR.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with source_path.open(newline="", encoding="utf-8-sig") as file:
        rows = [row for row in csv.reader(file)]

    if len(rows) < 2:
        raise ValueError("The CSV file must contain a header row and at least one response row")

    questions = parse_questions(rows[0])

    summaries, answer_counts = summarize(rows, questions) # понял
    facet_rows = aggregate_by_facet(summaries) # понял
    method_options = read_reference_answers(rows, questions) # понял
    method_summaries = summarize_method_matches(rows, questions, method_options) # понял

    if method_summaries:
        write_csv(
            output_dir / "method_option_match.csv",
            method_summaries,
            METHOD_MATCH_FIELDS,
        )
    write_csv(
        output_dir / "answer_set_counts.csv",
        answer_counts,
        ANSWER_COUNT_FIELDS,
    )
    write_heatmap(output_dir / "agreement_heatmap.svg", summaries)
    write_bar_chart(output_dir / "agreement_by_facet.svg", facet_rows)
    if method_summaries:
        write_method_match_heatmap(output_dir / "method_match_heatmap.svg", facet_rows, method_summaries)

    copy_report_images(output_dir, DEFAULT_REPORT_IMAGE_DIR.resolve())

    print(f"Input: {source_path.relative_to(ROOT)}")
    print(f"Responses: {len(rows) - 1}")
    print(f"Questions: {len(summaries)}")
    if method_summaries:
        print(f"Method match questions: {len(method_summaries)}")
    print(f"Output: {output_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
