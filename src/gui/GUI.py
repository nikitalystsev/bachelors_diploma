"""Графический интерфейс настройки и применения фильтра сценариев."""

# Имя файла сохранено для совместимости с существующей точкой входа.
# pylint: disable=invalid-name,too-many-lines

import ctypes
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from f2robot_client import F2RobotClient
from gui.config_GUI import ConfigGUI
from f2robot_personality_filter import F2RobotPersonalityFilter
from f2robot_profile_config import F2RobotProfileConfig
from scenario_mind_map import show_mind_map


def setup_dpi_awareness() -> None:
    """
    Корректная работа масштабирования на Windows.
    На Linux просто ничего не делает.
    """
    if not sys.platform.startswith("win"):
        return

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


class MyWindow(tk.Tk):  # pylint: disable=too-many-instance-attributes
    """
    Интерфейс дипломной программы в структуре GUI-шаблона лабораторных работ.
    """

    def __init__(self, profile_config: F2RobotProfileConfig | None = None) -> None:
        super().__init__()

        setup_dpi_awareness()

        self.profile_config = profile_config or F2RobotProfileConfig()
        self._scenario_counter = 0
        self.profile_vars: dict[str, tk.StringVar] = {}
        self.relation_vars: dict[str, tk.StringVar] = {}
        self.situation_vars: dict[str, tk.StringVar] = {}
        self.robot_profile_var = tk.StringVar()
        self.robot_profile_id_by_label: dict[str, str] = {}
        self.robot_profile_label_by_id: dict[str, str] = {}
        self.combo_value_by_label: dict[str, dict[str, str]] = {}
        self.combo_label_by_value: dict[str, dict[str, str]] = {}
        self.slider_vars: dict[str, tk.DoubleVar] = {}
        self.slider_owners: dict[str, str] = {}
        self.slider_value_labels: dict[str, tk.Label] = {}
        self.profile_trait_labels: dict[str, list[tk.Label]] = {}
        self._highlighted_profile_traits: set[str] = set()
        self.header_stats_var = tk.StringVar()
        self.f2robot_client = F2RobotClient()
        self.personality_filter = F2RobotPersonalityFilter(self.profile_config)
        self.sentence_text: tk.Text
        self.fetch_button: tk.Button
        self.scenario_tree: ttk.Treeview
        self._context_panel: tk.Frame
        self.result_tree: ttk.Treeview

        self.__configure_window()
        self.__configure_ttk()
        self.__create_layout()
        self.__create_widgets()
        self._load_default_context()
        self.bind("<Configure>", self.__adapt_layout)

    def __configure_window(self) -> None:
        self.title("Дипломная программа")
        self.configure(background=ConfigGUI.MAIN_BG)
        self.option_add("*TCombobox*Listbox.font", (ConfigGUI.FONT, ConfigGUI.FONT_SIZE))

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        root_width = min(max(int(screen_width * 0.88), 1280), screen_width)
        root_height = min(max(int(screen_height * 0.86), 780), screen_height)
        pos_x = max((screen_width - root_width) // 2, 0)
        pos_y = max((screen_height - root_height) // 2, 0)

        self.geometry(f"{root_width}x{root_height}+{pos_x}+{pos_y}")
        self.minsize(1180, 740)
        self.resizable(True, True)
        if sys.platform.startswith("win"):
            self.state("zoomed")

    def __configure_ttk(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(
            "App.Treeview",
            background=ConfigGUI.FIELD_BG,
            fieldbackground=ConfigGUI.FIELD_BG,
            foreground=ConfigGUI.BLACK,
            bordercolor=ConfigGUI.FIELD_BORDER,
            rowheight=28,
            font=(ConfigGUI.FONT, ConfigGUI.FONT_SIZE),
        )
        style.configure(
            "App.Treeview.Heading",
            background=ConfigGUI.TABLE_HEADER_BG,
            foreground=ConfigGUI.BLACK,
            font=(ConfigGUI.FONT, ConfigGUI.FONT_SIZE, "bold"),
            relief=tk.FLAT,
        )
        style.map(
            "App.Treeview",
            background=[("selected", ConfigGUI.ACCENT)],
            foreground=[("selected", ConfigGUI.WHITE)],
        )
        style.configure(
            "App.TCombobox",
            fieldbackground=ConfigGUI.FIELD_BG,
            background=ConfigGUI.FIELD_BG,
            foreground=ConfigGUI.BLACK,
            arrowcolor=ConfigGUI.ACCENT,
            padding=(8, 4),
        )
        style.configure(
            "App.TNotebook",
            background=ConfigGUI.MAIN_BG,
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        style.configure(
            "App.TNotebook.Tab",
            background=ConfigGUI.MAIN_BG,
            foreground=ConfigGUI.WHITE,
            padding=(18, 8),
            font=(ConfigGUI.FONT, ConfigGUI.FONT_SIZE),
            relief=tk.RAISED,
            borderwidth=2,
            width=14,
        )
        style.map(
            "App.TNotebook.Tab",
            background=[
                ("selected", ConfigGUI.FIELD_BG),
                ("!selected", ConfigGUI.MAIN_BG),
            ],
            foreground=[
                ("selected", ConfigGUI.BLACK),
                ("!selected", ConfigGUI.WHITE),
            ],
            padding=[
                ("selected", (18, 8)),
                ("!selected", (18, 8)),
            ],
            expand=[
                ("selected", (0, 0, 0, 0)),
                ("!selected", (0, 0, 0, 0)),
            ],
        )
        style.configure(
            "App.Horizontal.TScale",
            background=ConfigGUI.FIELD_BG,
            troughcolor=ConfigGUI.MAIN_BG,
        )

    def __create_layout(self) -> None:
        self._main_frame = self.__create_frame(self, ConfigGUI.MAIN_BG)
        self._main_frame.pack(expand=True, fill=tk.BOTH)
        self._main_frame.columnconfigure(0, weight=1)
        self._main_frame.rowconfigure(1, weight=1)

        self._tabs = ttk.Notebook(self._main_frame, style="App.TNotebook")
        self._tabs.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

        self._work_frame = self.__create_frame(self._tabs, ConfigGUI.MAIN_BG)
        self._result_tab = self.__create_frame(self._tabs, ConfigGUI.MAIN_BG)
        self._tabs.add(self._work_frame, text="Настройка")
        self._tabs.add(self._result_tab, text="Результат")

        self._work_frame.columnconfigure(0, minsize=430, weight=1)
        self._work_frame.columnconfigure(1, weight=2)
        self._work_frame.rowconfigure(1, weight=1)

        self._result_tab.columnconfigure(0, weight=1)
        self._result_tab.rowconfigure(0, weight=1)

    def __create_widgets(self) -> None:
        self.__create_header()
        self.__create_sentence_panel()
        self.__create_scenario_panel()
        self.__create_context_panel()
        self.__create_result_panel()

    def __adapt_layout(self, _event: tk.Event) -> None:
        if not hasattr(self, "scenario_tree"):
            return

        height = self.winfo_height()
        if height < 760:
            sentence_height = 2
            scenario_height = 4
        elif height < 900:
            sentence_height = 3
            scenario_height = 6
        else:
            sentence_height = 4
            scenario_height = 8

        if int(self.sentence_text.cget("height")) != sentence_height:
            self.sentence_text.configure(height=sentence_height)
        if int(self.scenario_tree.cget("height")) != scenario_height:
            self.scenario_tree.configure(height=scenario_height)

    def __create_header(self) -> None:
        header = self.__create_frame(self._main_frame, ConfigGUI.MAIN_BG)
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        header.columnconfigure(0, weight=1)

        self.__create_label(
            header,
            "Модуль модификации поведения на основе персональных черт",
            font_size=ConfigGUI.H1,
            foreground=ConfigGUI.WHITE,
            background=ConfigGUI.MAIN_BG,
            anchor=tk.CENTER,
            wraplength=0,
        ).grid(row=0, column=0, sticky="ew")
        self.__create_label(
            header,
            "",
            font_size=ConfigGUI.FONT_SIZE,
            foreground=ConfigGUI.TEXT_MUTED,
            background=ConfigGUI.MAIN_BG,
            anchor=tk.CENTER,
            textvariable=self.header_stats_var,
        ).grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self._refresh_header_stats()

    def _refresh_header_stats(self) -> None:
        self.header_stats_var.set(
            "Правил: "
            f"{len(self.personality_filter.default_rules)}; "
            "нечётких признаков: "
            f"{len(self.personality_filter.default_fuzzy_variables)}"
        )

    def __create_sentence_panel(self) -> None:
        frame = self.__create_panel(
            self._work_frame,
            "Предложение роботу Ф-2",
            ConfigGUI.MAIN_BG,
            ConfigGUI.WHITE,
        )
        frame.grid(row=0, column=0, sticky="ew", padx=(0, 9), pady=(12, 14))
        frame.columnconfigure(0, weight=1)

        self.sentence_text = tk.Text(
            frame,
            height=3,
            wrap=tk.WORD,
            undo=True,
            relief=tk.FLAT,
            borderwidth=0,
            background=ConfigGUI.FIELD_BG,
            foreground=ConfigGUI.BLACK,
            insertbackground=ConfigGUI.ACCENT,
            font=(ConfigGUI.FONT, ConfigGUI.TEXT_INPUT_FONT_SIZE, ConfigGUI.FONT_STYLE),
            highlightthickness=1,
            highlightbackground=ConfigGUI.FIELD_BORDER,
            highlightcolor=ConfigGUI.ACCENT,
        )
        self.sentence_text.grid(row=1, column=0, sticky="ew", padx=12, pady=(8, 12))
        self._bind_sentence_text_shortcuts()
        self.sentence_text.insert("1.0", "Я заработал много денег в этом месяце")

        buttons = self.__create_frame(frame, ConfigGUI.MAIN_BG)
        buttons.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        buttons.columnconfigure((0, 1), weight=1)

        self.fetch_button = self.__create_button(
            buttons,
            "Получить сценарии",
            self.fetch_scenarios_from_api,
        )
        self.fetch_button.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))
        self.__create_button(
            buttons,
            "Применить правила",
            self.apply_filter,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 8))

    def __create_scenario_panel(self) -> None:
        frame = self.__create_panel(
            self._work_frame,
            "Активированные д-сценарии",
            ConfigGUI.MAIN_BG,
            ConfigGUI.WHITE,
        )
        frame.grid(row=1, column=0, sticky="nsew", padx=(0, 9), pady=(0, 14))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        columns = ("number", "scenario", "weight")
        self.scenario_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=6,
            style="App.Treeview",
        )
        self.scenario_tree.heading("number", text="№")
        self.scenario_tree.heading("scenario", text="Сценарий")
        self.scenario_tree.heading("weight", text="Вес")
        self.scenario_tree.column(
            "number",
            width=48,
            minwidth=48,
            anchor=tk.CENTER,
            stretch=False,
        )
        self.scenario_tree.column("scenario", width=275, minwidth=160, stretch=True)
        self.scenario_tree.column("weight", width=74, minwidth=62, anchor=tk.E, stretch=False)
        self.scenario_tree.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(8, 8))

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.scenario_tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 12), pady=(8, 8))
        self.scenario_tree.configure(yscrollcommand=scrollbar.set)

        self.__create_button(
            frame,
            "Очистить",
            self.clear_scenarios,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))

    def _bind_sentence_text_shortcuts(self) -> None:
        paste_sequences = (
            "<Command-v>",
            "<Command-V>",
            "<Command-Cyrillic_em>",
            "<Command-Cyrillic_EM>",
            "<Control-v>",
            "<Control-V>",
            "<<Paste>>",
        )
        for sequence in paste_sequences:
            try:
                self.sentence_text.bind(sequence, self._paste_into_sentence_text)
            except tk.TclError:
                pass

        select_all_sequences = (
            "<Command-a>",
            "<Command-A>",
            "<Command-Cyrillic_ef>",
            "<Command-Cyrillic_EF>",
            "<Control-a>",
            "<Control-A>",
            "<<SelectAll>>",
        )
        for sequence in select_all_sequences:
            try:
                self.sentence_text.bind(sequence, self._select_all_sentence_text)
            except tk.TclError:
                pass

    def _paste_into_sentence_text(self, event: tk.Event) -> str:
        widget = event.widget
        if not isinstance(widget, tk.Text):
            return "break"

        try:
            clipboard_text = self.clipboard_get()
        except tk.TclError:
            return "break"

        if not clipboard_text:
            return "break"

        widget.edit_separator()
        try:
            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass
        widget.insert(tk.INSERT, clipboard_text)
        widget.edit_separator()
        widget.see(tk.INSERT)
        return "break"

    def _select_all_sentence_text(self, event: tk.Event) -> str:
        widget = event.widget
        if not isinstance(widget, tk.Text):
            return "break"

        widget.tag_add(tk.SEL, "1.0", "end-1c")
        widget.mark_set(tk.INSERT, "end-1c")
        widget.see(tk.INSERT)
        return "break"

    def __create_context_panel(self) -> None:
        frame = self.__create_panel(
            self._work_frame,
            "Профиль и контекст",
            ConfigGUI.MAIN_BG,
            ConfigGUI.WHITE,
        )
        self._context_panel = frame
        frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(9, 0), pady=(12, 0))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        tabs = ttk.Notebook(frame, style="App.TNotebook")
        tabs.grid(row=1, column=0, sticky="nsew", padx=12, pady=(8, 12))

        profile_tab, profile_content = self._create_scrollable_context_tab(tabs)
        relation_tab, relation_content = self._create_scrollable_context_tab(tabs)
        situation_tab, situation_content = self._create_scrollable_context_tab(tabs)
        tabs.add(profile_tab, text="Профиль")
        tabs.add(relation_tab, text="Отношение")
        tabs.add(situation_tab, text="Ситуация")

        self._build_robot_profile_selector(profile_content)
        self._build_combo_section(
            profile_content,
            self.personality_filter.profile_options,
            self.profile_vars,
            start_row=1,
            as_labels=not self.profile_config.is_abstract_profile,
        )
        self._build_combo_section(
            relation_content,
            self.personality_filter.relation_options,
            self.relation_vars,
        )
        self._build_combo_section(
            situation_content,
            self.personality_filter.situation_options,
            self.situation_vars,
        )
        self._build_slider_section(profile_content, "profile")
        self._build_slider_section(relation_content, "relation")
        self._build_slider_section(situation_content, "situation")

    def _create_scrollable_context_tab(self, parent: ttk.Notebook) -> tuple[tk.Frame, tk.Frame]:
        """
        Создает вкладку с вертикальной прокруткой для динамических полей контекста.
        """
        container = self.__create_frame(parent, ConfigGUI.FIELD_BG)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        canvas = tk.Canvas(
            container,
            background=ConfigGUI.FIELD_BG,
            borderwidth=0,
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(
            container,
            orient=tk.VERTICAL,
            command=canvas.yview,
        )
        content = self.__create_frame(canvas, ConfigGUI.FIELD_BG)
        content_id = canvas.create_window((0, 0), window=content, anchor=tk.NW)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        content.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox(tk.ALL)),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(content_id, width=event.width),
        )
        self._bind_context_mousewheel(canvas)

        return container, content

    def _bind_context_mousewheel(self, canvas: tk.Canvas) -> None:
        """
        Привязывает колесо мыши к прокрутке активной вкладки контекста.
        """
        def scroll(event: tk.Event) -> str:
            if getattr(event, "num", None) == 4:
                units = -1
            elif getattr(event, "num", None) == 5:
                units = 1
            else:
                delta = int(getattr(event, "delta", 0))
                units = -1 if delta > 0 else 1
            canvas.yview_scroll(units, "units")
            return "break"

        def bind_mousewheel(_event: tk.Event) -> None:
            canvas.bind_all("<MouseWheel>", scroll)
            canvas.bind_all("<Button-4>", scroll)
            canvas.bind_all("<Button-5>", scroll)

        def unbind_mousewheel(_event: tk.Event) -> None:
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", bind_mousewheel)
        canvas.bind("<Leave>", unbind_mousewheel)

    def __create_result_panel(self) -> None:
        result_frame = self.__create_panel(
            self._result_tab,
            "Результат перевзвешивания",
            ConfigGUI.MAIN_BG,
            ConfigGUI.WHITE,
        )
        result_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=0,
            pady=12,
        )
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(1, weight=1)

        columns = ("number", "scenario", "original", "multiplier", "modified", "rules")
        self.result_tree = ttk.Treeview(
            result_frame,
            columns=columns,
            show="headings",
            style="App.Treeview",
        )
        headings = {
            "number": "№",
            "scenario": "Сценарий",
            "original": "Исходный",
            "multiplier": "Множитель",
            "modified": "Итоговый",
            "rules": "Правила",
        }
        for column, title in headings.items():
            self.result_tree.heading(column, text=title)

        self.result_tree.column(
            "number",
            width=48,
            minwidth=48,
            anchor=tk.CENTER,
            stretch=False,
        )
        self.result_tree.column("scenario", width=330, minwidth=260, stretch=False)
        self.result_tree.column("original", width=115, minwidth=110, anchor=tk.E, stretch=False)
        self.result_tree.column("multiplier", width=125, minwidth=120, anchor=tk.E, stretch=False)
        self.result_tree.column("modified", width=115, minwidth=110, anchor=tk.E, stretch=False)
        self.result_tree.column("rules", width=420, minwidth=300, stretch=True)
        self.result_tree.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(8, 0))

        result_y_scrollbar = ttk.Scrollbar(
            result_frame,
            orient=tk.VERTICAL,
            command=self.result_tree.yview,
        )
        result_y_scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 12), pady=(8, 0))

        result_x_scrollbar = ttk.Scrollbar(
            result_frame,
            orient=tk.HORIZONTAL,
            command=self.result_tree.xview,
        )
        result_x_scrollbar.grid(row=2, column=0, sticky="ew", padx=(12, 0), pady=(0, 8))
        self.result_tree.configure(
            yscrollcommand=result_y_scrollbar.set,
            xscrollcommand=result_x_scrollbar.set,
        )

    # Набор аргументов описывает отдельную секцию динамической формы.
    # pylint: disable-next=too-many-arguments
    def _build_combo_section(
        self,
        parent: tk.Frame,
        options: dict[str, tuple[str, ...]],
        storage: dict[str, tk.StringVar],
        *,
        start_row: int = 0,
        as_labels: bool = False,
    ) -> None:
        parent.columnconfigure(1, weight=1)
        for row_offset, (feature, values) in enumerate(options.items()):
            row = start_row + row_offset
            labels = [self._term_label(feature, value) for value in values]
            self.combo_value_by_label[feature] = dict(zip(labels, values))
            self.combo_label_by_value[feature] = dict(zip(values, labels))
            is_profile_trait = storage is self.profile_vars

            feature_label = self.__create_label(
                parent,
                self._feature_label(feature),
                ConfigGUI.FONT_SIZE,
                ConfigGUI.BLACK,
                ConfigGUI.FIELD_BG,
                padx=4,
            )
            feature_label.grid(row=row, column=0, sticky="w", padx=(0, 10), pady=5)
            if is_profile_trait:
                self.profile_trait_labels.setdefault(feature, []).append(feature_label)
            variable = tk.StringVar(value=labels[0])
            storage[feature] = variable
            if as_labels:
                value_label = self.__create_label(
                    parent,
                    "",
                    ConfigGUI.FONT_SIZE,
                    ConfigGUI.BLACK,
                    ConfigGUI.TABLE_HEADER_BG,
                    textvariable=variable,
                    anchor=tk.W,
                    relief=tk.SOLID,
                    borderwidth=1,
                    padx=8,
                    pady=4,
                    wraplength=360,
                )
                if is_profile_trait:
                    self.profile_trait_labels.setdefault(feature, []).append(value_label)
                self._bind_profile_trait_label_hover(value_label, feature)
                value_label.grid(
                    row=row,
                    column=1,
                    sticky="ew",
                    padx=(0, 4),
                    pady=5,
                )
                continue

            combo = ttk.Combobox(
                parent,
                textvariable=variable,
                values=labels,
                state="readonly",
                style="App.TCombobox",
            )
            combo.grid(row=row, column=1, sticky="ew", padx=(0, 4), pady=5)

    def _bind_profile_trait_label_hover(self, label: tk.Label, feature: str) -> None:
        normal_background = ConfigGUI.TABLE_HEADER_BG
        hover_background = ConfigGUI.FIELD_BG

        def leave(_event: tk.Event) -> None:
            if feature in self._highlighted_profile_traits:
                label.configure(
                    background=ConfigGUI.MANIFESTED_TRAIT_BG,
                    foreground=ConfigGUI.MANIFESTED_TRAIT_FG,
                )
                return
            label.configure(background=normal_background, foreground=ConfigGUI.BLACK)

        label.bind(
            "<Enter>",
            lambda _event: label.configure(background=hover_background),
        )
        label.bind("<Leave>", leave)

    def _build_robot_profile_selector(self, parent: tk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        profile_descriptors = self.profile_config.available_profiles()
        if profile_descriptors:
            profile_ids = tuple(profile.profile_id for profile in profile_descriptors)
            labels = tuple(profile.label for profile in profile_descriptors)
        else:
            profile_ids = self.personality_filter.robot_profile_options
            labels = tuple(
                self.personality_filter.robot_profile_labels[profile_id]
                for profile_id in profile_ids
            )
        self.robot_profile_id_by_label = dict(zip(labels, profile_ids))
        self.robot_profile_label_by_id = dict(zip(profile_ids, labels))

        self.__create_label(
            parent,
            "Профиль робота",
            ConfigGUI.FONT_SIZE,
            ConfigGUI.BLACK,
            ConfigGUI.FIELD_BG,
            padx=4,
        ).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)

        current_profile_id = (
            self.profile_config.current_profile_id
            or self.personality_filter.default_robot_profile_id
        )
        self.robot_profile_var.set(
            self.robot_profile_label_by_id[current_profile_id]
        )
        combo = ttk.Combobox(
            parent,
            textvariable=self.robot_profile_var,
            values=labels,
            state="readonly",
            style="App.TCombobox",
        )
        combo.grid(row=0, column=1, sticky="ew", padx=(0, 4), pady=5)
        combo.bind("<<ComboboxSelected>>", self._select_robot_profile)

    def _build_slider_section(self, parent: tk.Frame, target: str) -> None:
        start_row = (
            max(
                (
                    int(widget.grid_info().get("row", 0))
                    for widget in parent.grid_slaves()
                ),
                default=-1,
            )
            + 1
        )
        parent.columnconfigure(1, weight=1)
        row = start_row
        for feature, title, minimum, maximum, owner in (
            self.personality_filter.slider_specs
        ):
            if owner != target:
                continue

            variable = tk.DoubleVar(value=0.0)
            self.slider_vars[feature] = variable
            self.slider_owners[feature] = owner
            self.__create_label(
                parent,
                self._feature_label(feature, title),
                ConfigGUI.FONT_SIZE,
                ConfigGUI.BLACK,
                ConfigGUI.FIELD_BG,
                padx=4,
            ).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=5)

            scale = ttk.Scale(
                parent,
                from_=minimum,
                to=maximum,
                variable=variable,
                command=lambda _value, name=feature: self._refresh_slider_label(name),
                style="App.Horizontal.TScale",
            )
            scale.grid(row=row, column=1, sticky="ew", pady=5)

            label = self.__create_label(
                parent,
                "",
                ConfigGUI.FONT_SIZE,
                ConfigGUI.ACCENT,
                ConfigGUI.FIELD_BG,
                anchor=tk.E,
                width=6,
                padx=4,
            )
            label.grid(row=row, column=2, sticky="e", padx=(10, 0), pady=5)
            self.slider_value_labels[feature] = label
            row += 1

    def _load_default_context(self) -> None:
        self.robot_profile_var.set(
            self.robot_profile_label_by_id[
                self.personality_filter.default_robot_profile_id
            ]
        )
        self._apply_context_values(
            self.personality_filter.default_profile,
            self.personality_filter.default_relation,
            self.personality_filter.default_situation,
        )
        self._set_status("Контекст сброшен к демонстрационным значениям")

    def _select_robot_profile(self, _event: tk.Event) -> None:
        profile_id = self.robot_profile_id_by_label[self.robot_profile_var.get()]
        try:
            self.profile_config = F2RobotProfileConfig(
                profile_id=profile_id,
                profiles_root=self.profile_config.profiles_root,
                data_dir=self.profile_config.data_dir,
            )
            self.personality_filter = F2RobotPersonalityFilter(self.profile_config)
            self._refresh_header_stats()
            self._rebuild_context_panel()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            messagebox.showerror("Ошибка профиля", str(exc))
            self._set_status("Профиль не загружен")
            return
        self._clear_result()
        self._set_status("Профиль загружен")

    def _rebuild_context_panel(self) -> None:
        self._reset_context_controls()
        if hasattr(self, "_context_panel"):
            self._context_panel.destroy()
        self.__create_context_panel()
        self._load_default_context()

    def _reset_context_controls(self) -> None:
        self.profile_vars.clear()
        self.relation_vars.clear()
        self.situation_vars.clear()
        self.combo_value_by_label.clear()
        self.combo_label_by_value.clear()
        self.slider_vars.clear()
        self.slider_owners.clear()
        self.slider_value_labels.clear()
        self.profile_trait_labels.clear()
        self._highlighted_profile_traits.clear()

    def _apply_context_values(
        self,
        profile: dict[str, str | float],
        relation: dict[str, str | float],
        situation: dict[str, str | float],
    ) -> None:
        for feature, variable in self.profile_vars.items():
            variable.set(self._display_value(feature, str(profile.get(feature, ""))))
        for feature, variable in self.relation_vars.items():
            variable.set(self._display_value(feature, str(relation.get(feature, ""))))
        for feature, variable in self.situation_vars.items():
            variable.set(self._display_value(feature, str(situation.get(feature, ""))))
        for feature, variable in self.slider_vars.items():
            owner = self.slider_owners[feature]
            source = {
                "profile": profile,
                "relation": relation,
                "situation": situation,
            }[owner]
            value = source.get(feature, 0.0)
            variable.set(float(value))
            self._refresh_slider_label(feature)

    def _refresh_slider_label(self, feature: str) -> None:
        label = self.slider_value_labels.get(feature)
        if label is not None:
            label.configure(text=f"{self.slider_vars[feature].get():.2f}")

    def clear_scenarios(self) -> None:
        """Очищает таблицу сценариев и связанные результаты."""
        for item in self.scenario_tree.get_children():
            self.scenario_tree.delete(item)
        self._clear_result()
        self._set_status("Список сценариев очищен")

    def fetch_scenarios_from_api(self) -> None:
        """Запрашивает активированные сценарии для введенной реплики."""
        sentence = self.sentence_text.get("1.0", tk.END).strip()
        if not sentence:
            messagebox.showerror("Ошибка ввода", "Введите реплику пользователя.")
            return

        self.fetch_button.configure(state=tk.DISABLED)
        self._set_status("Отправляю запрос в F2Robot...")

        thread = threading.Thread(
            target=self._fetch_scenarios_worker,
            args=(sentence,),
            daemon=True,
        )
        thread.start()

    def _fetch_scenarios_worker(self, sentence: str) -> None:
        try:
            result = self.f2robot_client.get_activated_scenarios(sentence)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.after(0, self._handle_fetch_error, exc)
            return
        self.after(0, self._handle_fetch_success, result)

    def _handle_fetch_error(self, exc: Exception) -> None:
        self.fetch_button.configure(state=tk.NORMAL)
        self._set_status("Запрос к F2Robot не выполнен")
        messagebox.showerror("Ошибка F2Robot", str(exc))

    def _handle_fetch_success(self, result: dict[str, list[dict[str, str | float]]]) -> None:
        self.fetch_button.configure(state=tk.NORMAL)
        self.clear_scenarios()
        for item in result.get("scenario_proximities", []):
            scenario = item.get("scenario")
            proximity = item.get("proximity")
            if isinstance(scenario, str) and isinstance(proximity, int | float):
                self._insert_scenario(scenario, float(proximity))
        self._set_status(f"Получено сценариев: {len(self.scenario_tree.get_children())}")

    def apply_filter(self) -> None:
        """Применяет персональный фильтр к активированным сценариям."""
        self._clear_manifested_traits()
        try:
            scenarios = self._read_scenarios()
            if not scenarios:
                raise ValueError("Добавьте хотя бы один активированный сценарий.")
            filtered = self.personality_filter.filter_scenario_weights_as_dicts(
                scenarios,
                profile=self._read_profile(),
                relation=self._read_relation(),
                situation=self._read_situation(),
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            messagebox.showerror("Ошибка фильтра", str(exc))
            self._set_status("Фильтр не применен")
            return

        self._render_result(filtered)
        self._highlight_manifested_traits(filtered)
        self._tabs.select(self._result_tab)
        show_mind_map(
            self,
            self.sentence_text.get("1.0", tk.END).strip(),
            self._unique_result_items(filtered),
        )
        changed = sum(1 for item in filtered if abs(item["multiplier"] - 1.0) > 1e-9)
        self._set_status(f"Фильтр применен: изменено сценариев {changed} из {len(filtered)}")

    def _read_scenarios(self) -> list[dict[str, str | float]]:
        scenarios: list[dict[str, str | float]] = []
        for item_id in self.scenario_tree.get_children():
            _, scenario, weight = self.scenario_tree.item(item_id, "values")
            scenarios.append({"scenario": scenario, "weight": self._parse_weight(str(weight))})
        return scenarios

    def _read_profile(self) -> dict[str, str | float]:
        profile: dict[str, str | float] = {
            feature: self._internal_value(feature, variable.get())
            for feature, variable in self.profile_vars.items()
        }
        self._append_slider_values(profile, "profile")
        return profile

    def _read_relation(self) -> dict[str, str | float]:
        relation: dict[str, str | float] = {
            feature: self._internal_value(feature, variable.get())
            for feature, variable in self.relation_vars.items()
        }
        self._append_slider_values(relation, "relation")
        return relation

    def _read_situation(self) -> dict[str, str | float]:
        situation: dict[str, str | float] = {
            feature: self._internal_value(feature, variable.get())
            for feature, variable in self.situation_vars.items()
        }
        self._append_slider_values(situation, "situation")
        return situation

    def _append_slider_values(self, values: dict[str, str | float], owner: str) -> None:
        for feature, variable in self.slider_vars.items():
            if self.slider_owners[feature] == owner:
                values[feature] = variable.get()

    def _render_result(self, filtered: list[dict[str, object]]) -> None:
        self._clear_result()

        unique_items = self._unique_result_items(filtered)
        sorted_items = sorted(
            unique_items,
            key=lambda item: float(item["modified_weight"]),
            reverse=True,
        )
        for number, item in enumerate(sorted_items, start=1):
            rules = item["rules"]
            rule_names = ", ".join(
                self._rule_label(str(rule["rule_id"])) for rule in rules
            ) if rules else "нет"
            self.result_tree.insert(
                "",
                tk.END,
                values=(
                    number,
                    item["scenario"],
                    f"{float(item['original_weight']):.4f}",
                    f"{float(item['multiplier']):.4f}",
                    f"{float(item['modified_weight']):.4f}",
                    rule_names,
                ),
            )

    def _clear_result(self) -> None:
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self._clear_manifested_traits()

    def _highlight_manifested_traits(self, filtered: list[dict[str, object]]) -> None:
        manifested_traits = self._manifested_profile_traits(filtered)
        self._highlighted_profile_traits = manifested_traits

        for feature, labels in self.profile_trait_labels.items():
            is_manifested = feature in manifested_traits
            for label in labels:
                label.configure(
                    background=(
                        ConfigGUI.MANIFESTED_TRAIT_BG
                        if is_manifested
                        else self._profile_trait_label_background(label)
                    ),
                    foreground=(
                        ConfigGUI.MANIFESTED_TRAIT_FG
                        if is_manifested
                        else ConfigGUI.BLACK
                    ),
                )

    def _clear_manifested_traits(self) -> None:
        self._highlighted_profile_traits.clear()
        for labels in self.profile_trait_labels.values():
            for label in labels:
                label.configure(
                    background=self._profile_trait_label_background(label),
                    foreground=ConfigGUI.BLACK,
                )

    def _manifested_profile_traits(
        self,
        filtered: list[dict[str, object]],
    ) -> set[str]:
        profile_features = set(self.profile_trait_labels)
        manifested_traits: set[str] = set()

        for item in filtered:
            rules = item.get("rules")
            if not isinstance(rules, list):
                continue
            for rule in rules:
                if not isinstance(rule, dict):
                    continue
                condition_features = rule.get("condition_features", ())
                if not isinstance(condition_features, list):
                    continue
                manifested_traits.update(
                    str(feature)
                    for feature in condition_features
                    if str(feature) in profile_features
                )

        return manifested_traits

    @staticmethod
    def _profile_trait_label_background(label: tk.Label) -> str:
        column = int(label.grid_info().get("column", 0))
        if column == 1:
            return ConfigGUI.TABLE_HEADER_BG
        return ConfigGUI.FIELD_BG

    def _insert_scenario(self, scenario: str, weight: float) -> None:
        formatted_weight = f"{weight:.4f}"
        if self._scenario_exists(scenario, formatted_weight):
            return

        self._scenario_counter += 1
        self.scenario_tree.insert(
            "",
            tk.END,
            iid=f"scenario_{self._scenario_counter}",
            values=("", scenario, formatted_weight),
        )
        self._sort_scenarios_by_weight()
        self._renumber_scenarios()

    def _scenario_exists(self, scenario: str, weight: str) -> bool:
        for item_id in self.scenario_tree.get_children():
            values = self.scenario_tree.item(item_id, "values")
            if len(values) >= 3 and str(values[1]) == scenario and str(values[2]) == weight:
                return True
        return False

    def _unique_result_items(
        self,
        filtered: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        seen: set[tuple[str, str]] = set()
        unique_items: list[dict[str, object]] = []
        for item in filtered:
            key = (
                str(item["scenario"]),
                f"{float(item['modified_weight']):.4f}",
            )
            if key in seen:
                continue
            seen.add(key)
            unique_items.append(item)
        return unique_items

    def _sort_scenarios_by_weight(self) -> None:
        rows = []
        for index, item_id in enumerate(self.scenario_tree.get_children()):
            values = self.scenario_tree.item(item_id, "values")
            rows.append((self._parse_weight(str(values[2])), index, item_id))

        for position, (_, _, item_id) in enumerate(
            sorted(rows, key=lambda row: (-row[0], row[1]))
        ):
            self.scenario_tree.move(item_id, "", position)

    def _renumber_scenarios(self) -> None:
        for number, item_id in enumerate(self.scenario_tree.get_children(), start=1):
            _, scenario, weight = self.scenario_tree.item(item_id, "values")
            self.scenario_tree.item(item_id, values=(number, scenario, weight))

    def _parse_weight(self, raw_value: str) -> float:
        try:
            value = float(raw_value.strip().replace(",", "."))
        except ValueError as exc:
            raise ValueError("Вес сценария должен быть числом.") from exc
        if not 0.0 <= value <= 1.0:
            raise ValueError("Вес сценария должен быть в диапазоне от 0 до 1.")
        return value

    def _feature_label(self, feature: str, fallback: str | None = None) -> str:
        return self.personality_filter.feature_labels.get(feature, fallback or feature)

    def _term_label(self, feature: str, value: str) -> str:
        return self.personality_filter.term_labels.get(feature, {}).get(value, value)

    def _rule_label(self, rule_id: str) -> str:
        return self.personality_filter.rule_labels.get(rule_id, rule_id)

    def _display_value(self, feature: str, value: str) -> str:
        return self.combo_label_by_value.get(feature, {}).get(value, value)

    def _internal_value(self, feature: str, label: str) -> str:
        return self.combo_value_by_label.get(feature, {}).get(label, label)

    def _set_status(self, message: str) -> None:
        if hasattr(self, "status_var"):
            self.status_var.set(message)

    def __create_frame(self, master: tk.Misc, background: str) -> tk.Frame:
        return tk.Frame(master=master, background=background, borderwidth=0)

    def __create_panel(
        self,
        master: tk.Misc,
        text: str,
        background: str,
        foreground: str,
    ) -> tk.Frame:
        frame = tk.Frame(
            master=master,
            background=background,
            relief=tk.RAISED,
            borderwidth=2,
            highlightthickness=1,
            highlightbackground=ConfigGUI.PANEL_BORDER,
            highlightcolor=ConfigGUI.PANEL_BORDER,
        )
        frame.columnconfigure(0, weight=1)
        self.__create_label(
            frame,
            text,
            ConfigGUI.H2,
            foreground,
            background,
            anchor=tk.W,
            wraplength=0,
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 0))
        return frame

    # Аргументы соответствуют поддерживаемым параметрам создаваемого Tkinter Label.
    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def __create_label(
        self,
        master: tk.Misc,
        text: str,
        font_size: int,
        foreground: str,
        background: str,
        *,
        textvariable: tk.StringVar | None = None,
        anchor: str = tk.W,
        width: int | None = None,
        wraplength: int = 400,
        relief: str = tk.FLAT,
        borderwidth: int = 0,
        padx: int = 0,
        pady: int = 0,
    ) -> tk.Label:
        return tk.Label(
            master=master,
            text=text,
            textvariable=textvariable,
            font=(ConfigGUI.FONT, font_size, ConfigGUI.FONT_STYLE),
            background=background,
            foreground=foreground,
            anchor=anchor,
            justify=tk.LEFT,
            width=width,
            wraplength=wraplength,
            relief=relief,
            borderwidth=borderwidth,
            padx=padx,
            pady=pady,
        )

    def __create_button(
        self,
        master: tk.Misc,
        text: str,
        command,
    ) -> tk.Button:
        return tk.Button(
            master=master,
            text=text,
            command=command,
            font=(ConfigGUI.FONT, ConfigGUI.BUTTON_FONT_SIZE, ConfigGUI.FONT_STYLE),
            relief=tk.RAISED,
            borderwidth=2,
            background=ConfigGUI.BUTTON_BG,
            activebackground=ConfigGUI.BUTTON_ACTIVE_BG,
            foreground=ConfigGUI.BLACK,
            activeforeground=ConfigGUI.WHITE,
            cursor="hand2",
            padx=10,
            pady=8,
        )


def run() -> None:
    """Запускает графическое приложение."""
    app = MyWindow()
    app.mainloop()


if __name__ == "__main__":
    run()
