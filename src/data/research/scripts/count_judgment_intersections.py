#!/usr/bin/env python3
"""Count how often separate reactions were selected by N respondents."""

import csv
import html
import json
import math
import re
import shutil
from pathlib import Path


ROOT_MARKERS = ("src", ".git")
RESPONSES_PATH = Path("src/data/research/responses.csv")
OUTPUT_DIR = Path("src/data/research/analysis")
REPORT_IMAGE_DIR = Path("docs/report_system/report/inc/img")
SLIDES_IMAGE_DIR = Path("docs/report_system/slides/inc/img")
DIPLOMA_REPORT_IMAGE_DIR = Path("docs/diplom-master/report/inc/img")
DIPLOMA_SLIDES_IMAGE_DIR = Path("docs/diplom-master/slides/assets")
LEVEL_ORDER = {"Низкая": 0, "Средняя": 1, "Высокая": 2}
HEADER_RE = re.compile(
    r"^(?P<scenario_id>\d+)\. В диалоге (?P<scenario>.*?)\. "
    r"Выберите.*?грани (?P<facet>.*?), выставленной.*? "
    r"\[(?P<level>.*?)\]$"
)
FONT_FAMILY = "Arial, sans-serif"


def find_project_root(start: Path) -> Path:
    for directory in (start, *start.parents):
        if all((directory / marker).exists() for marker in ROOT_MARKERS):
            return directory
    raise RuntimeError(f"Cannot find project root from {start}")


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
                "facet": match.group("facet").strip(),
                "level": match.group("level").strip(),
            }
        )

    return sorted(
        questions,
        key=lambda question: (
            int(question["scenario_id"]),
            LEVEL_ORDER.get(str(question["level"]), 99),
        ),
    )


def question_reactions(
    response_rows: list[list[str]],
    question: dict[str, int | str],
) -> list[str]:
    """
    Возвращает отдельные нормализованные реакции всех респондентов на один вопрос.
    """
    column_index = int(question["column_index"])
    reactions = []
    for row in response_rows:
        answer = row[column_index]
        parts = answer.split(";")
        judgments = []
        for part in parts:
            reaction = re.sub(r"\s+", " ", part).strip()
            if reaction:
                judgments.append(reaction)

        reactions.extend(judgments)

    # print(f"reactions: {reactions}")
    return reactions


def add_reaction_frequencies(
    reactions: list[str],
    distribution: list[int],
) -> None:
    frequencies: dict[str, int] = {}

    # сколько раз встретилась каждая реакция в вопросе
    for reaction in reactions:
        frequencies[reaction] = frequencies.get(reaction, 0) + 1

    for respondents_count in frequencies.values():
        distribution[respondents_count - 1] += 1



def svg_text(x: float, y: float, text: str, **attrs: object) -> str:
    attr_text = " ".join(f'{key.replace("_", "-")}="{html.escape(str(value))}"' for key, value in attrs.items())
    return f'<text x="{x}" y="{y}" {attr_text}>{html.escape(text)}</text>'


def write_histogram(path: Path, distribution: list[int]) -> None:
    width = 1040
    height = 500
    margin_left = 74
    margin_right = 44
    margin_top = 96
    margin_bottom = 76
    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom
    max_value = max(distribution) if distribution else 0
    bar_gap = 6
    bar_width = (chart_width - bar_gap * (len(distribution) - 1)) / len(distribution)
    y_axis_max = ((max_value + 9) // 10) * 10 if max_value else 10

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        svg_text(
            28,
            32,
            "Распределение числа ситуаций в данных от числа респондентов, давших идентичный ответ",
            font_family=FONT_FAMILY,
            font_size=20,
            font_weight=700,
            fill="#172033",
        ),
        f'<line x1="{margin_left}" y1="{margin_top + chart_height}" x2="{margin_left + chart_width}" y2="{margin_top + chart_height}" stroke="#98a2b3"/>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + chart_height}" stroke="#98a2b3"/>',
    ]

    for tick in range(0, y_axis_max + 1, max(1, y_axis_max // 5)):
        y = margin_top + chart_height - chart_height * tick / y_axis_max
        parts.append(f'<line x1="{margin_left - 5}" y1="{y:.1f}" x2="{margin_left + chart_width}" y2="{y:.1f}" stroke="#eef1f5"/>')
        parts.append(
            svg_text(
                margin_left - 12,
                y + 4,
                str(tick),
                font_family=FONT_FAMILY,
                font_size=11,
                fill="#475467",
                text_anchor="end",
            )
        )

    for index, value in enumerate(distribution):
        x = margin_left + index * (bar_width + bar_gap)
        bar_height = chart_height * value / y_axis_max if y_axis_max else 0
        y = margin_top + chart_height - bar_height
        fill = "#2f6f9f" if index + 1 >= 10 else "#74a8cf"
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="3" fill="{fill}"/>')
        parts.append(
            svg_text(
                x + bar_width / 2,
                y - 6,
                str(value),
                font_family=FONT_FAMILY,
                font_size=10,
                fill="#263244",
                text_anchor="middle",
            )
        )
        parts.append(
            svg_text(
                x + bar_width / 2,
                margin_top + chart_height + 20,
                str(index + 1),
                font_family=FONT_FAMILY,
                font_size=11,
                fill="#344054",
                text_anchor="middle",
            )
        )

    parts.extend(
        [
            svg_text(
                margin_left + chart_width / 2,
                height - 20,
                "Число респондентов, давших идентичный ответ",
                font_family=FONT_FAMILY,
                font_size=12,
                fill="#344054",
                text_anchor="middle",
            ),
            svg_text(
                18,
                margin_top + chart_height / 2,
                "Число ситуаций в данных",
                font_family=FONT_FAMILY,
                font_size=12,
                fill="#344054",
                text_anchor="middle",
                transform=f"rotate(-90 18 {margin_top + chart_height / 2})",
            ),
            "</svg>",
        ]
    )
    path.write_text("\n".join(parts), encoding="utf-8")


def pie_slice_path(cx: float, cy: float, radius: float, start_angle: float, end_angle: float) -> str:
    start_x = cx + radius * math.cos(start_angle)
    start_y = cy + radius * math.sin(start_angle)
    end_x = cx + radius * math.cos(end_angle)
    end_y = cy + radius * math.sin(end_angle)
    large_arc = 1 if end_angle - start_angle > math.pi else 0
    return (
        f"M {cx:.1f} {cy:.1f} "
        f"L {start_x:.1f} {start_y:.1f} "
        f"A {radius:.1f} {radius:.1f} 0 {large_arc} 1 {end_x:.1f} {end_y:.1f} Z"
    )


def grouped_intersection_distribution(distribution: list[int]) -> list[dict[str, object]]:
    respondents_count = len(distribution)
    return [
        {
            "label": "Уникальные ответы",
            "description": "выбраны 1 респондентом",
            "count": distribution[0] if respondents_count else 0,
            "color": "#2f6f9f",
        },
        {
            "label": f"Не менее 10 из {respondents_count}",
            "description": "выбраны не менее чем 10 респондентами",
            "count": sum(distribution[9:]),
            "color": "#72a84a",
        },
        {
            "label": "2 респондента",
            "description": "выбраны двумя респондентами",
            "count": distribution[1] if respondents_count > 1 else 0,
            "color": "#d49436",
        },
        {
            "label": "3-9 респондентов",
            "description": "выбраны от 3 до 9 респондентами",
            "count": sum(distribution[2:9]),
            "color": "#bf4d45",
        },
    ]


def write_pie_chart(path: Path, distribution: list[int]) -> None:
    total = sum(distribution)
    if total <= 0:
        raise ValueError("Cannot build pie chart for an empty distribution")

    groups = grouped_intersection_distribution(distribution)
    width = 980
    height = 520
    cx = 282
    cy = 284
    radius = 160
    legend_x = 520
    legend_y = 145

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        svg_text(
            36,
            38,
            "Распределение ответов по числу респондентов, давших идентичный ответ",
            font_family=FONT_FAMILY,
            font_size=20,
            font_weight=700,
            fill="#172033",
        ),
    ]

    angle = -math.pi / 2
    for group in groups:
        count = int(group["count"])
        if count <= 0:
            continue

        sweep = 2 * math.pi * count / total
        next_angle = angle + sweep
        parts.append(
            f'<path d="{pie_slice_path(cx, cy, radius, angle, next_angle)}" '
            f'fill="{group["color"]}" stroke="#ffffff" stroke-width="3"/>'
        )

        label_angle = angle + sweep / 2
        label_radius = radius * 0.65
        label_x = cx + label_radius * math.cos(label_angle)
        label_y = cy + label_radius * math.sin(label_angle)
        parts.append(
            svg_text(
                label_x,
                label_y + 4,
                f"{count / total:.0%}",
                font_family=FONT_FAMILY,
                font_size=16,
                font_weight=700,
                fill="#ffffff",
                text_anchor="middle",
            )
        )
        angle = next_angle

    for index, group in enumerate(groups):
        count = int(group["count"])
        percent = count / total
        y = legend_y + index * 74
        parts.append(f'<rect x="{legend_x}" y="{y - 15}" width="18" height="18" rx="4" fill="{group["color"]}"/>')
        parts.append(
            svg_text(
                legend_x + 30,
                y,
                f'{group["label"]}: {count}/{total} ({percent:.0%})',
                font_family=FONT_FAMILY,
                font_size=16,
                font_weight=700,
                fill="#172033",
            )
        )
        parts.append(
            svg_text(
                legend_x + 30,
                y + 22,
                str(group["description"]),
                font_family=FONT_FAMILY,
                font_size=12,
                fill="#667085",
            )
        )

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def short_circle_label(label: str, respondents_count: int) -> str:
    if label == "Уникальные ответы":
        return "Уникальные"
    if label.startswith("Не менее 10"):
        return f"10+ из {respondents_count}"
    return label.replace("респондентов", "респ.").replace("респондента", "респ.")


def write_pie_circle(path: Path, distribution: list[int]) -> None:
    total = sum(distribution)
    if total <= 0:
        raise ValueError("Cannot build pie chart for an empty distribution")

    groups = grouped_intersection_distribution(distribution)
    respondents_count = len(distribution)
    width = 520
    height = 520
    cx = width / 2
    cy = height / 2
    radius = 235

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    ]

    angle = -math.pi / 2
    for group in groups:
        count = int(group["count"])
        if count <= 0:
            continue

        sweep = 2 * math.pi * count / total
        next_angle = angle + sweep
        parts.append(
            f'<path d="{pie_slice_path(cx, cy, radius, angle, next_angle)}" '
            f'fill="{group["color"]}" stroke="#ffffff" stroke-width="4"/>'
        )

        label_angle = angle + sweep / 2
        label_radius = radius * 0.60
        label_x = cx + label_radius * math.cos(label_angle)
        label_y = cy + label_radius * math.sin(label_angle)
        label_attrs = {
            "font_family": FONT_FAMILY,
            "fill": "#ffffff",
            "text_anchor": "middle",
            "stroke": "#172033",
            "stroke_width": 2,
            "stroke_opacity": 0.28,
            "stroke_linejoin": "round",
            "paint_order": "stroke",
        }
        parts.append(
            svg_text(
                label_x,
                label_y - 18,
                short_circle_label(str(group["label"]), respondents_count),
                font_size=15,
                font_weight=700,
                **label_attrs,
            )
        )
        parts.append(
            svg_text(
                label_x,
                label_y + 5,
                f"{count / total:.0%}",
                font_size=23,
                font_weight=700,
                **label_attrs,
            )
        )
        parts.append(
            svg_text(
                label_x,
                label_y + 25,
                f"{count}/{total}",
                font_size=13,
                **label_attrs,
            )
        )
        angle = next_angle

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    root = find_project_root(Path(__file__).resolve().parent)
    with (root / RESPONSES_PATH).open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.reader(file))

    if len(rows) < 2:
        raise ValueError("responses.csv must contain a header row and at least one response row")

    questions = parse_questions(rows[0])

    response_rows = rows[1:]

    if len(questions) != 90:
        raise ValueError(f"Expected 90 questions, got {len(questions)}")

    distribution = [0] * len(response_rows)
    for i, question in enumerate(questions):
        reactions = question_reactions(response_rows, question)
        add_reaction_frequencies(reactions, distribution)
        if i in [0, 1]:
            print(f"distribution: {distribution}")


    output_dir = root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    histogram_path = output_dir / "judgment_intersections_histogram.svg"
    pie_chart_path = output_dir / "judgment_intersections_pie.svg"
    pie_circle_path = output_dir / "judgment_intersections_pie_circle.svg"
    write_histogram(histogram_path, distribution)
    write_pie_chart(pie_chart_path, distribution)
    write_pie_circle(pie_circle_path, distribution)

    for image_dir in (root / REPORT_IMAGE_DIR, root / SLIDES_IMAGE_DIR):
        image_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(histogram_path, image_dir / "research_judgment_intersections_histogram.svg")
        shutil.copyfile(pie_chart_path, image_dir / "research_judgment_intersections_pie.svg")
        shutil.copyfile(pie_circle_path, image_dir / "research_judgment_intersections_pie_circle.svg")

    for image_dir in (root / DIPLOMA_REPORT_IMAGE_DIR, root / DIPLOMA_SLIDES_IMAGE_DIR):
        image_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pie_chart_path, image_dir / "research_judgment_intersections_pie.svg")
        shutil.copyfile(pie_circle_path, image_dir / "research_judgment_intersections_pie_circle.svg")

    print(json.dumps(distribution, ensure_ascii=False))
    print(f"Histogram: {histogram_path.relative_to(root)}")
    print(f"Pie chart: {pie_chart_path.relative_to(root)}")
    print(f"Pie circle: {pie_circle_path.relative_to(root)}")


if __name__ == "__main__":
    main()
