"""Окно mind map для визуализации перевзвешенных д-сценариев."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import math
import textwrap
import tkinter as tk
from tkinter import font as tkfont
from typing import Any


@dataclass(frozen=True)
class MindMapScenario:
    """Нормализованный сценарий для отрисовки карты."""

    name: str
    weight: float


ScenarioSource = (
    Mapping[str, Any]
    | Iterable[Mapping[str, Any]]
    | Iterable[Any]
)


BACKGROUND = "#f4f6fb"
CENTER_FILL = "#fff8df"
CENTER_OUTLINE = "#f0b84f"
TEXT_DARK = "#151821"
TEXT_MUTED = "#4b5568"
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 760
WINDOW_DEFAULT_WIDTH = 1500
WINDOW_DEFAULT_HEIGHT = 950

BRANCH_COLOR = "#2563eb"


def show_mind_map(
    parent: tk.Misc,
    phrase: str,
    scenarios: ScenarioSource,
    *,
    title: str = "Mind map д-сценариев",
) -> "ScenarioMindMapWindow":
    """
    Открывает отдельное окно с mind map.

    Размер названия сценария зависит от итогового веса. Поддерживаются словари
    формата фильтра, пары scenario/weight, пары scenario/proximity и dataclass-объекты.
    """
    items = normalize_scenarios(scenarios)
    window = ScenarioMindMapWindow(parent, phrase, items, title=title)
    window.focus()
    return window


def normalize_scenarios(scenarios: ScenarioSource) -> tuple[MindMapScenario, ...]:
    """Приводит разные форматы входа к отсортированному набору сценариев."""
    if isinstance(scenarios, Mapping):
        if "scenario_proximities" in scenarios:
            raw_items = scenarios["scenario_proximities"]
            if not isinstance(raw_items, Iterable):
                raise TypeError("scenario_proximities must be iterable")
            return normalize_scenarios(raw_items)

        if _looks_like_scenario_item(scenarios):
            return (_scenario_from_item(scenarios),)

        items = (
            MindMapScenario(str(name), _checked_weight(weight))
            for name, weight in scenarios.items()
        )
    else:
        items = (_scenario_from_item(item) for item in scenarios)

    merged: dict[str, float] = {}
    for item in items:
        if not item.name.strip():
            continue
        # Если один сценарий пришел несколько раз, для карты важна сильнейшая активация.
        merged[item.name] = max(merged.get(item.name, 0.0), item.weight)

    return tuple(
        MindMapScenario(name, weight)
        for name, weight in sorted(merged.items(), key=lambda pair: pair[1], reverse=True)
    )


def _looks_like_scenario_item(item: Mapping[str, Any]) -> bool:
    return "scenario" in item and any(
        key in item
        for key in ("modified_weight", "weight", "proximity", "original_weight")
    )


def _scenario_from_item(item: Any) -> MindMapScenario:
    if isinstance(item, Mapping):
        scenario = item.get("scenario")
        if not isinstance(scenario, str) or not scenario.strip():
            raise ValueError("Scenario item must contain a non-empty scenario")

        for key in ("modified_weight", "weight", "proximity", "original_weight"):
            if key in item:
                return MindMapScenario(scenario, _checked_weight(item[key]))
        raise ValueError("Scenario item must contain modified_weight, weight or proximity")

    scenario = getattr(item, "scenario", None)
    if not isinstance(scenario, str) or not scenario.strip():
        raise TypeError("Each scenario item must be a mapping or have scenario attribute")

    for key in ("modified_weight", "weight", "proximity", "original_weight"):
        if hasattr(item, key):
            return MindMapScenario(scenario, _checked_weight(getattr(item, key)))
    raise ValueError("Scenario item must contain modified_weight, weight or proximity")


def _checked_weight(value: Any) -> float:
    if isinstance(value, bool):
        raise TypeError("Scenario weight must be numeric")
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("Scenario weight must be numeric") from exc
    return min(max(numeric_value, 0.0), 1.0)


class ScenarioMindMapWindow(tk.Toplevel):
    """Отдельное окно с интерактивно перерисовываемой mind map."""

    def __init__(
        self,
        parent: tk.Misc,
        phrase: str,
        scenarios: tuple[MindMapScenario, ...],
        *,
        title: str,
    ) -> None:
        super().__init__(parent)
        self.phrase = phrase.strip() or "Введенная фраза"
        self.scenarios = scenarios
        self._redraw_after_id: str | None = None

        self.title(title)
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.geometry(f"{WINDOW_DEFAULT_WIDTH}x{WINDOW_DEFAULT_HEIGHT}")
        self.configure(background=BACKGROUND)

        self.canvas = tk.Canvas(self, highlightthickness=0, background=BACKGROUND)
        self.canvas.pack(expand=True, fill=tk.BOTH)
        self.canvas.bind("<Configure>", self._schedule_redraw)
        self.bind("<Escape>", lambda _event: self.destroy())

        self._draw()

    def _schedule_redraw(self, _event: tk.Event) -> None:
        if self._redraw_after_id is not None:
            self.after_cancel(self._redraw_after_id)
        self._redraw_after_id = self.after(80, self._draw)

    def _draw(self) -> None:
        self._redraw_after_id = None
        width = max(self.canvas.winfo_width(), WINDOW_MIN_WIDTH)
        height = max(self.canvas.winfo_height(), WINDOW_MIN_HEIGHT)
        self.canvas.delete("all")

        self._draw_background(width, height)
        self._draw_title(width)

        if not self.scenarios:
            self._draw_empty_state(width, height)
            return

        center_x = width / 2
        center_y = height / 2 + 20
        center_radius = min(145, max(105, width * 0.12))
        weights = [item.weight for item in self.scenarios]
        min_weight = min(weights)
        max_weight = max(weights)

        nodes = self._layout_nodes(width, height, center_x, center_y)
        for item, x, y, ring in nodes:
            font_size = self._scenario_font_size(item.weight, min_weight, max_weight)
            self._draw_branch(center_x, center_y, x, y, BRANCH_COLOR, item.weight, ring)
            self._draw_scenario_node(x, y, item, BRANCH_COLOR, font_size)

        self._draw_center_node(center_x, center_y, center_radius)
        self._draw_legend(width, height, min_weight, max_weight)

    def _draw_background(self, width: int, height: int) -> None:
        self.canvas.create_rectangle(0, 0, width, height, fill=BACKGROUND, outline=BACKGROUND)

    def _draw_title(self, width: int) -> None:
        self.canvas.create_text(
            width / 2,
            32,
            text="Карта активации д-сценариев после правил",
            fill=TEXT_DARK,
            font=("Helvetica", 18, "bold"),
        )

    def _draw_empty_state(self, width: int, height: int) -> None:
        self._draw_center_node(width / 2, height / 2, 130)
        self.canvas.create_text(
            width / 2,
            height / 2 + 180,
            text="Нет сценариев для построения карты",
            fill=TEXT_MUTED,
            font=("Helvetica", 15, "bold"),
        )

    def _layout_nodes(
        self,
        width: int,
        height: int,
        center_x: float,
        center_y: float,
    ) -> list[tuple[MindMapScenario, float, float, int]]:
        count = len(self.scenarios)
        nodes: list[tuple[MindMapScenario, float, float, int]] = []
        base_radius_x = max(300, width * 0.34)
        base_radius_y = max(210, height * 0.30)

        for index, item in enumerate(self.scenarios):
            ring = 0 if count <= 14 or index < math.ceil(count * 0.62) else 1
            ring_index = index if ring == 0 else index - math.ceil(count * 0.62)
            ring_count = count if ring == 0 else count - math.ceil(count * 0.62)
            if count > 14 and ring == 0:
                ring_count = math.ceil(count * 0.62)

            angle = self._angle_for_index(ring_index, ring_count, ring)
            radius_x = base_radius_x + ring * 70
            radius_y = base_radius_y + ring * 52
            x = center_x + math.cos(angle) * radius_x
            y = center_y + math.sin(angle) * radius_y

            margin_x = 142
            margin_top = 142
            margin_bottom = 88
            x = min(max(x, margin_x), width - margin_x)
            y = min(max(y, margin_top), height - margin_bottom)
            nodes.append((item, x, y, ring))

        return nodes

    @staticmethod
    def _angle_for_index(index: int, count: int, ring: int) -> float:
        if count <= 0:
            return 0.0
        # Смещаем старт, чтобы самые тяжелые сценарии уходили в правый верхний сектор.
        start_angle = -math.pi / 3 + ring * math.pi / max(count, 1)
        return start_angle + index * (2 * math.pi / count)

    @staticmethod
    def _scenario_font_size(weight: float, min_weight: float, max_weight: float) -> int:
        if math.isclose(max_weight, min_weight):
            return 15
        ratio = (weight - min_weight) / (max_weight - min_weight)
        return int(round(12 + ratio * 8))

    def _draw_branch(
        self,
        center_x: float,
        center_y: float,
        node_x: float,
        node_y: float,
        color: str,
        weight: float,
        ring: int,
    ) -> None:
        dx = node_x - center_x
        dy = node_y - center_y
        distance = math.hypot(dx, dy) or 1.0
        start_x = center_x + dx / distance * 118
        start_y = center_y + dy / distance * 88
        end_x = node_x - dx / distance * 94
        end_y = node_y - dy / distance * 42
        curve = 0.20 + ring * 0.08
        control_1_x = start_x + dx * curve
        control_1_y = start_y + dy * 0.08
        control_2_x = end_x - dx * curve
        control_2_y = end_y - dy * 0.08
        width = max(2, int(round(2 + weight * 8)))

        self.canvas.create_line(
            start_x + 2,
            start_y + 2,
            control_1_x + 2,
            control_1_y + 2,
            control_2_x + 2,
            control_2_y + 2,
            end_x + 2,
            end_y + 2,
            smooth=True,
            width=width + 2,
            fill="#2f3548",
            stipple="gray50",
        )
        self.canvas.create_line(
            start_x,
            start_y,
            control_1_x,
            control_1_y,
            control_2_x,
            control_2_y,
            end_x,
            end_y,
            smooth=True,
            width=width,
            fill=color,
        )

    def _draw_scenario_node(
        self,
        x: float,
        y: float,
        item: MindMapScenario,
        color: str,
        font_size: int,
    ) -> None:
        wrapped_name = _wrap_scenario_name(
            item.name,
            max_chars=18 if font_size >= 18 else 22,
            max_lines=4,
        )
        title_font = tkfont.Font(family="Helvetica", size=font_size, weight="bold")
        subtitle_font = tkfont.Font(family="Helvetica", size=10)
        text_lines = wrapped_name.count("\n") + 1
        title_height = text_lines * max(title_font.metrics("linespace"), font_size + 3)
        box_width = max(214, min(292, int(220 + font_size * 2.4)))
        box_height = max(86, int(title_height + 58))

        x0 = x - box_width / 2
        y0 = y - box_height / 2
        x1 = x + box_width / 2
        y1 = y + box_height / 2

        self._rounded_rectangle(x0 + 5, y0 + 7, x1 + 5, y1 + 7, 22, "#000000", "")
        self.canvas.itemconfigure("shadow", stipple="gray75")
        self._rounded_rectangle(x0, y0, x1, y1, 22, "#ffffff", color, outline_width=3)
        self.canvas.create_oval(x0 + 12, y0 + 12, x0 + 28, y0 + 28, fill=color, outline="")
        self.canvas.create_text(
            x,
            y - 8,
            text=wrapped_name,
            fill=TEXT_DARK,
            font=title_font,
            justify=tk.CENTER,
            width=box_width - 34,
        )
        self.canvas.create_text(
            x,
            y1 - 20,
            text=f"вес {item.weight:.3f}",
            fill=TEXT_MUTED,
            font=subtitle_font,
        )

    def _draw_center_node(self, center_x: float, center_y: float, radius: float) -> None:
        box_width = radius * 2.45
        box_height = radius * 1.34
        x0 = center_x - box_width / 2
        y0 = center_y - box_height / 2
        x1 = center_x + box_width / 2
        y1 = center_y + box_height / 2

        self._rounded_rectangle(x0 + 8, y0 + 10, x1 + 8, y1 + 10, 36, "#000000", "")
        self.canvas.itemconfigure("shadow", stipple="gray75")
        self._rounded_rectangle(x0, y0, x1, y1, 36, CENTER_FILL, CENTER_OUTLINE, 4)
        self.canvas.create_text(
            center_x,
            y0 + 28,
            text="ФРАЗА",
            fill="#9b6512",
            font=("Helvetica", 11, "bold"),
        )
        self.canvas.create_text(
            center_x,
            center_y + 8,
            text=_wrap_text(self.phrase, max_chars=30),
            fill=TEXT_DARK,
            font=("Helvetica", 20, "bold"),
            justify=tk.CENTER,
            width=box_width - 48,
        )

    def _draw_legend(
        self,
        width: int,
        height: int,
        min_weight: float,
        max_weight: float,
    ) -> None:
        legend = f"min {min_weight:.3f}   max {max_weight:.3f}"
        self.canvas.create_text(
            width - 24,
            height - 24,
            text=legend,
            fill="#647084",
            font=("Helvetica", 10),
            anchor=tk.E,
        )

    def _rounded_rectangle(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        radius: float,
        fill: str,
        outline: str,
        outline_width: int = 1,
    ) -> None:
        radius = min(radius, abs(x1 - x0) / 2, abs(y1 - y0) / 2)
        points = (
            x0 + radius,
            y0,
            x1 - radius,
            y0,
            x1,
            y0,
            x1,
            y0 + radius,
            x1,
            y1 - radius,
            x1,
            y1,
            x1 - radius,
            y1,
            x0 + radius,
            y1,
            x0,
            y1,
            x0,
            y1 - radius,
            x0,
            y0 + radius,
            x0,
            y0,
        )
        tags = "shadow" if fill == "#000000" else ""
        self.canvas.create_polygon(
            points,
            smooth=True,
            splinesteps=16,
            fill=fill,
            outline=outline,
            width=outline_width,
            tags=tags,
        )


def _wrap_text(value: str, *, max_chars: int) -> str:
    chunks = textwrap.wrap(value, width=max_chars, break_long_words=False)
    if chunks:
        return "\n".join(chunks)
    return value


def _wrap_scenario_name(value: str, *, max_chars: int, max_lines: int) -> str:
    """
    Переносит имена сценариев предсказуемо.

    Имена F2Robot часто состоят из цепочек через дефис. Если оставить их одним
    словом, Canvas сам дробит текст и ломает расчет высоты карточки.
    """
    normalized = value.strip()
    if not normalized:
        return normalized

    tokens = _scenario_name_tokens(normalized)
    lines: list[str] = []
    current = ""

    for token in tokens:
        candidate = f"{current}{token}" if current else token
        if current and len(candidate.rstrip(" -")) > max_chars:
            lines.append(current.rstrip(" -"))
            current = token.lstrip("-")
        else:
            current = candidate

    if current:
        lines.append(current.rstrip(" -"))

    compact_lines = [line for line in lines if line]
    if len(compact_lines) <= max_lines:
        return "\n".join(compact_lines)

    visible_lines = compact_lines[:max_lines]
    visible_lines[-1] = f"{visible_lines[-1].rstrip('…')}…"
    return "\n".join(visible_lines)


def _scenario_name_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    for chunk in value.split():
        parts = chunk.split("-")
        for index, part in enumerate(parts):
            if not part:
                continue
            suffix = "-" if index < len(parts) - 1 else ""
            tokens.append(f"{part}{suffix}")
        tokens.append(" ")
    if tokens and tokens[-1] == " ":
        tokens.pop()
    return tokens
