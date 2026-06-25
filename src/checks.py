"""Вспомогательные функции проверки числовых строк."""


def check_float(x: str) -> bool:
    """
    Проверка числа на float. Возвращает True, если число вещественное и
    False, если число нельзя привести к вещественному типу данных
    :param x: потенциальное вещественное число
    :return: True, если строка - вещественное число. Иначе - False
    """
    if not x:
        return False

    if x[0] in "-+":
        x = x[1:]

    point_split = x.split(".")

    if len(point_split) == 1:  # Нет точки
        exp_split = x.split("e")
        if len(exp_split) == 1:  # Нет е и нет точки
            return x.isdigit()
        if len(exp_split) == 2:  # Есть один символ е и нет точки
            exponent = exp_split[1]
            return exp_split[0].isdigit() and (
                exponent.isdigit()
                or bool(exponent)
                and exponent[0] in "+-"
                and exponent[1:].isdigit()
            )

    if len(point_split) == 2:  # Есть одна точка
        exp_split = point_split[1].split("e")
        if len(exp_split) == 1:  # Есть точка и нет е
            return point_split[0].isdigit() and exp_split[0].isdigit()
        if len(exp_split) == 2:  # Есть точка и есть е
            exponent = exp_split[1]
            return (
                point_split[0].isdigit()
                and exp_split[0].isdigit()
                and (
                    exponent.isdigit()
                    or bool(exponent)
                    and exponent[0] in "+-"
                    and exponent[1:].isdigit()
                )
            )

    return False
