"""HTTP-клиент API F2Robot."""

import os
from pathlib import Path
from typing import Any

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
F2_ROBOT_API_LINK_ENV = "F2_ROBOT_API_LINK"
RESULT_KEY = "scenario_proximities"
REQUEST_TIMEOUT = 30.0


class F2RobotClient:  # pylint: disable=too-few-public-methods
    """
    Клиент для запроса семантических сценариев F2Robot.
    """

    def __init__(self) -> None:
        """
        Создает клиента с настройкой URL через переменную окружения.
        """
        self._api_url: str = self._get_api_url()

    def _get_api_url(self) -> str:
        """
        Возвращает нормализованный URL API из настроек клиента или окружения.
        """
        self._load_env_file()

        url = os.getenv(F2_ROBOT_API_LINK_ENV)

        if not url:
            raise RuntimeError(
                f"F2Robot API URL is not configured. Set {F2_ROBOT_API_LINK_ENV} "
                f"in the environment or in {ENV_PATH}."
            )

        return url

    @staticmethod
    def _load_env_file() -> None:
        """
        Загружает переменные из .env файла с приоритетом над окружением.
        """
        if not ENV_PATH.exists():
            return

        with ENV_PATH.open("r", encoding="utf-8") as file:
            for raw_line in file:
                line = raw_line.strip()

                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                    value = value[1:-1]

                os.environ[key] = value

    def get_activated_scenarios(
        self,
        sentence: str,
    ) -> dict[str, list[dict[str, str | float]]]:
        """
        Запрашивает F2Robot и возвращает найденные пары scenario/proximity.
        """
        response = self._get_f2robot_response(sentence)

        return self._parse_pairs(response)

    def _get_f2robot_response(self, sentence: str) -> dict | list:
        """
        Отправляет текст в API F2Robot и возвращает сырой JSON-ответ.
        """
        body = self._build_request_body(sentence)

        try:
            response = requests.post(
                self._api_url,
                json=body,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"F2Robot API request failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError("F2Robot API returned invalid JSON") from exc

    @staticmethod
    def _build_request_body(sentence: str) -> dict[str, list[str]]:
        """
        Формирует тело запроса F2Robot из одной входной реплики.
        """
        if not isinstance(sentence, str) or not sentence.strip():
            raise ValueError("sentence must be a non-empty string")

        return {"variants": [sentence]}

    @staticmethod
    def _parse_pairs(
        response: Any,
    ) -> dict[str, list[dict[str, str | float]]]:
        """
        Извлекает из вложенного ответа все пары scenario/proximity.
        """
        pairs: list[dict[str, str | float]] = []

        F2RobotClient._collect_pairs(response, pairs)

        return {RESULT_KEY: pairs}

    @staticmethod
    def _collect_pairs(
        value: Any,
        pairs: list[dict[str, str | float]],
    ) -> None:
        """
        Рекурсивно собирает пары scenario/proximity из словарей и списков.
        """
        if isinstance(value, dict):
            scenario = value.get("scenario")
            proximity = value.get("proximity")
            if (
                isinstance(scenario, str)
                and not scenario.startswith("@")
                and isinstance(proximity, int | float)
            ):
                pairs.append({"scenario": scenario, "proximity": float(proximity)})

            for child in value.values():
                F2RobotClient._collect_pairs(child, pairs)
        elif isinstance(value, list):
            for item in value:
                F2RobotClient._collect_pairs(item, pairs)
