"""Точка входа графического приложения."""

from gui.GUI import MyWindow


def main() -> None:
    """
    Главная функция
    """
    root = MyWindow()

    root.mainloop()


if __name__ == "__main__":
    main()
