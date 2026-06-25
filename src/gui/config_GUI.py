"""Константы оформления графического интерфейса."""

# pylint: disable=invalid-name

class ConfigGUI:  # pylint: disable=too-few-public-methods
    """
    Класс общей конфигурации параметров экрана
    """

    # font
    FONT = "helvetica"
    FONT_SIZE = 12
    TEXT_INPUT_FONT_SIZE = 14
    BUTTON_FONT_SIZE = 14
    FONT_STYLE = "normal"

    # headers (размеры шрифта по уровням)
    H1 = 22
    H2 = 16

    # colors
    BLACK = "#000000"
    WHITE = "#FFFFFF"
    MAIN_BG = "#3d517f"

    PANEL_BORDER = "#d8deee"
    ACCENT = BLACK
    BUTTON_BG = WHITE
    BUTTON_ACTIVE_BG = MAIN_BG
    TEXT_MUTED = WHITE
    FIELD_BG = "#fffaff"
    FIELD_BORDER = "#b9a7d6"
    TABLE_HEADER_BG = "#ded6ea"
    MANIFESTED_TRAIT_BG = "#008D00"
    MANIFESTED_TRAIT_FG = WHITE
