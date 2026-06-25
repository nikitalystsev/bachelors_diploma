import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import f2robot_client
from f2robot_client import F2RobotClient


TEST_API_URL = "http://test_url_f2robot_api"
ENVIRONMENT_API_URL = "https://environment.example/api"


class F2RobotClientTestCase(unittest.TestCase):
    """
    Класс для теста клиента робота Ф-2
    """
    def setUp(self) -> None:
        """
        Готовит изолированный .env и окружение для каждого теста клиента.
        """
        self.env_var = "TEST_F2_ROBOT_API_LINK"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.temp_dir.name) / ".env"
        self.env_path.write_text(
            f"{self.env_var}={TEST_API_URL}\n",
            encoding="utf-8",
        )

        # очистка окружения и подмена значений двух переменных в модуле f2robot_client
        self.env_patch = patch.dict(os.environ, {}, clear=True)
        self.env_path_patch = patch.object(f2robot_client, "ENV_PATH", self.env_path)
        self.env_var_patch = patch.object(
            f2robot_client,
            "F2_ROBOT_API_LINK_ENV",
            "TEST_F2_ROBOT_API_LINK",
        )

        self.env_path_patch.start()
        self.env_var_patch.start()
        self.env_patch.start()

        self.client = F2RobotClient()

    def tearDown(self) -> None:
        """
        Откатывает подмены окружения и удаляет временные файлы теста.
        """
        self.env_var_patch.stop()
        self.env_path_patch.stop()
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def test_build_request_body_uses_sentence_variant(self) -> None:
        """
        Проверяет формат тела запроса для одной пользовательской фразы.
        """
        body = self.client._build_request_body("hello robot")

        self.assertEqual(body, {"variants": ["hello robot"]})

    def test_client_reads_api_url_from_env_file(self) -> None:
        """
        Проверяет чтение URL API из тестового .env файла.
        """
        url = self.client._get_api_url()

        self.assertEqual(url, TEST_API_URL)

    def test_client_uses_constant_env_var(self) -> None:
        """
        Проверяет, что клиент читает URL именно определенной нами переменной окружения
        """
        self.env_path.write_text(
            "OTHER_URL=other_url\n"
            f"{self.env_var}={TEST_API_URL}\n",
            encoding="utf-8",
        )

        # удаляем значения если они уже есть
        os.environ.pop(self.env_var, None)
        os.environ.pop("OTHER_URL", None)

        client = F2RobotClient()

        self.assertEqual(
            client._get_api_url(),
            TEST_API_URL,
        )

    def test_client_prefers_env_file_api_url(self) -> None:
        """
        Проверяет, что значение из .env файла имеет приоритет над окружением.
        """
        os.environ[self.env_var] = ENVIRONMENT_API_URL

        client = F2RobotClient()

        self.assertEqual(client._get_api_url(), TEST_API_URL)

    def test_parse_scenario_proximities_filters_at_prefixed_scenarios(self) -> None:
        """
        Проверяет формирование итогового множества без сценариев с префиксом @.
        """
        response = {
            "result": [
                {
                    "scenario": "greeting",
                    "proximity": 0.2537211166030776,
                },
                {
                    "variants": [
                        {"scenario": "@run_167_VERB_2", "proximity": 0.0},
                        {
                            "nested": {
                                "scenario": "positive_quality",
                                "proximity": 0.10742675209112622,
                            }
                        },
                    ]
                },
                {"scenario": "@SA_positive_quality", "proximity": 0.05},
            ]
        }

        self.assertEqual(
            self.client._parse_pairs(response),
            {
                "scenario_proximities": [
                    {
                        "scenario": "greeting",
                        "proximity": 0.2537211166030776,
                    },
                    {
                        "scenario": "positive_quality",
                        "proximity": 0.10742675209112622,
                    },
                ]
            },
        )

    def test_build_request_body_rejects_empty_sentence(self) -> None:
        """
        Проверяет ошибку формирования тела запроса для пустой фразы.
        """
        with self.assertRaisesRegex(ValueError, "non-empty string"):
            self.client._build_request_body("")

    def test_client_creation_requires_configured_api_url(self) -> None:
        """
        Проверяет ошибку создания клиента без настроенного URL API.
        """
        missing_env_path = Path(self.temp_dir.name) / "missing.env"

        # удаляем тестовую переменную из окружения
        os.environ.pop(self.env_var, None)

        with patch.object(f2robot_client, "ENV_PATH", missing_env_path):
            with self.assertRaisesRegex(RuntimeError, self.env_var):
                F2RobotClient()

    def test_parse_scenario_proximities_returns_empty_for_only_at_prefixed_scenarios(
        self,
    ) -> None:
        """
        Проверяет пустой результат, если все сценарии начинаются на @.
        """
        response = {
            "result": [
                {"scenario": "@run_167_VERB_2", "proximity": 0.0},
                {
                    "nested": {
                        "scenario": "@SA_positive_quality",
                        "proximity": 0.10742675209112622,
                    }
                },
            ]
        }

        self.assertEqual(
            self.client._parse_pairs(response),
            {"scenario_proximities": []},
        )

if __name__ == "__main__":
    unittest.main()
