import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

from f2robot_personality_filter import F2RobotPersonalityFilter
from f2robot_profile_config import F2RobotProfileConfig


class ProfileConfigTestCase(unittest.TestCase):
    """
    Проверяет загрузку и целостность конфигурации профиля F2-робота.
    """

    def setUp(self) -> None:
        """
        Создает изолированные каталоги данных и профилей.
        """
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.temp_dir.name)
        self.data_dir = self.root_dir / "data"
        self.profiles_root = self.root_dir / "profiles"

        self._write_shared_config()
        self._write_profile(
            directory_name="01-first",
            profile_id="first_profile",
            profile_label="Первый профиль",
            trait_value="calm",
            trait_value_label="спокойный",
        )
        self._write_profile(
            directory_name="02-second",
            profile_id="second_profile",
            profile_label="Второй профиль",
            trait_value="strict",
            trait_value_label="строгий",
        )

        self.config = self._create_config(profile_id="second_profile")
        self.filter = F2RobotPersonalityFilter(self.config)

    def tearDown(self) -> None:
        """
        Удаляет временные файлы конфигурации.
        """
        self.temp_dir.cleanup()

    def _create_config(self, profile_id: str | None = None) -> F2RobotProfileConfig:
        """
        Создает конфигурацию, использующую только временные каталоги.
        """
        return F2RobotProfileConfig(
            profile_id=profile_id,
            profiles_root=self.profiles_root,
            data_dir=self.data_dir,
        )

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        """
        Записывает тестовый JSON-файл.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_shared_config(self) -> None:
        """
        Записывает общие подписи черт и эффекты правил.
        """
        self._write_json(
            self.data_dir / "trait_labels.json",
            {
                "section": "trait_labels",
                "labels": {"temperament": "Темперамент"},
            },
        )
        self._write_json(
            self.data_dir / "rule_effects.json",
            {
                "section": "rule_effects",
                "multipliers": {"increase": 1.25},
                "labels": {"increase": "усиление"},
            },
        )

    def _write_profile(
        self,
        *,
        directory_name: str,
        profile_id: str,
        profile_label: str,
        trait_value: str,
        trait_value_label: str,
    ) -> None:
        """
        Записывает полный набор файлов синтетического профиля.
        """
        profile_dir = self.profiles_root / directory_name
        self._write_json(
            profile_dir / "trait_profile.json",
            {
                "section": "profile",
                "profile_id": profile_id,
                "label": profile_label,
                "traits": {
                    "temperament": {
                        "value": trait_value,
                        "label": trait_value_label,
                    }
                },
            },
        )
        self._write_json(
            profile_dir / "relation_params.json",
            {
                "section": "relation",
                "parameters": [
                    {
                        "feature": "social_circle",
                        "label": "Круг общения",
                        "input": "select",
                        "default": "close",
                        "options": [
                            {"term": "close", "label": "близкий"},
                            {"term": "distant", "label": "дальний"},
                        ],
                    }
                ],
            },
        )
        self._write_json(
            profile_dir / "situation_params.json",
            {
                "section": "situation",
                "parameters": [
                    {
                        "feature": "pressure",
                        "label": "Давление",
                        "input": "slider",
                        "default": 0.5,
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "fuzzy_terms": [
                            {
                                "term": "low",
                                "label": "низкое",
                                "function_type": "trapezoid",
                                "points": [0.0, 0.0, 0.25, 0.5],
                            },
                            {
                                "term": "high",
                                "label": "высокое",
                                "function_type": "trapezoid",
                                "points": [0.5, 0.75, 1.0, 1.0],
                            },
                        ],
                    }
                ],
            },
        )
        self._write_json(
            profile_dir / "rules.json",
            {
                "rules": [
                    {
                        "rule_id": "R_all_terms",
                        "label": "Правило для всех термов",
                        "conditions": [
                            {
                                "feature": "temperament",
                                "terms": [trait_value],
                            },
                            {
                                "feature": "social_circle",
                                "terms": ["close", "distant"],
                            },
                            {
                                "feature": "pressure",
                                "terms": ["low", "high"],
                            },
                        ],
                        "target_scenarios": ["test_scenario"],
                        "effect": "increase",
                    }
                ],
            },
        )
        self._write_json(
            profile_dir / "robot_gif.json",
            {
                "gif_path": f"data/f2robot_gifs/{profile_id}.gif",
            },
        )

    def _write_abstract_profile(self, directory_name: str = "00-abstract") -> None:
        """
        Записывает тестовый абстрактный профиль без robot_gif.json.
        """
        profile_dir = self.profiles_root / directory_name
        self._write_json(
            profile_dir / "trait_profile.json",
            {
                "section": "profile",
                "profile_id": "abstract",
                "label": "Абстрактный профиль",
                "traits": {
                    "temperament": {
                        "terms": [
                            {"term": "low", "label": "низкий"},
                            {"term": "medium", "label": "средний"},
                            {"term": "high", "label": "высокий"},
                        ]
                    }
                },
            },
        )
        self._write_json(
            profile_dir / "relation_params.json",
            {
                "section": "relation",
                "parameters": [
                    {
                        "feature": "abstract_relation",
                        "label": "Общее отношение",
                        "input": "select",
                        "default": "trusted",
                        "options": [
                            {"term": "trusted", "label": "доверительное"},
                            {"term": "guarded", "label": "настороженное"},
                        ],
                    }
                ],
            },
        )
        self._write_json(
            profile_dir / "situation_params.json",
            {
                "section": "situation",
                "parameters": [
                    {
                        "feature": "abstract_pressure",
                        "label": "Общее давление",
                        "input": "slider",
                        "default": 0.5,
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "fuzzy_terms": [
                            {
                                "term": "low",
                                "label": "низкое",
                                "function_type": "trapezoid",
                                "points": [0.0, 0.0, 0.25, 0.5],
                            },
                            {
                                "term": "high",
                                "label": "высокое",
                                "function_type": "trapezoid",
                                "points": [0.5, 0.75, 1.0, 1.0],
                            },
                        ],
                    }
                ],
            },
        )
        self._write_json(
            profile_dir / "rules.json",
            {
                "rules": [
                    {
                        "rule_id": "AR_common",
                        "label": "Общее правило",
                        "conditions": [
                            {
                                "feature": "abstract_relation",
                                "terms": ["trusted"],
                            }
                        ],
                        "target_scenarios": ["test_scenario"],
                        "effect": "increase",
                    }
                ],
            },
        )

    def test_configuration_is_loaded_from_profile_json_files(self) -> None:
        """
        Проверяет загрузку JSON-профиля и перенос значений в фильтр.
        """
        for filename in (
            "trait_profile.json",
            "relation_params.json",
            "situation_params.json",
            "rules.json",
            "robot_gif.json",
        ):
            self.assertTrue((self.config.profile_dir / filename).is_file())

        self.assertEqual(self.config.current_profile_id, "second_profile")
        self.assertEqual(
            self.config.robot_gif_config,
            {"gif_path": "data/f2robot_gifs/second_profile.gif"},
        )
        self.assertEqual(
            self.config.robot_gif_path,
            self.root_dir / "data" / "f2robot_gifs" / "second_profile.gif",
        )
        self.assertEqual(self.config.profile_config["profile_id"], "second_profile")
        self.assertEqual(
            self.filter.robot_profile_values,
            {"second_profile": {"temperament": "strict"}},
        )
        self.assertEqual(
            self.filter.robot_profile_labels,
            {"second_profile": "Второй профиль"},
        )
        self.assertEqual(self.filter.feature_labels["temperament"], "Темперамент")
        self.assertEqual(self.filter.term_labels["temperament"]["strict"], "строгий")
        self.assertEqual(
            self.filter.profile_options["temperament"],
            ("strict",),
        )
        self.assertEqual(
            self.filter.relation_options["social_circle"],
            ("close", "distant"),
        )
        self.assertEqual(self.filter.default_relation["social_circle"], "close")
        self.assertIn(
            "pressure",
            {feature for feature, *_ in self.filter.slider_specs},
        )
        self.assertEqual(self.filter.feature_labels["pressure"], "Давление")
        self.assertEqual(len(self.filter.default_rules), 1)
        self.assertEqual(self.filter.rule_effect_multipliers, {"increase": 1.25})

    def test_profiles_are_discovered_from_profiles_directory(self) -> None:
        """
        Проверяет обнаружение профилей во временном каталоге.
        """
        profiles = self.config.available_profiles()

        self.assertEqual(
            tuple(profile.profile_id for profile in profiles),
            ("first_profile", "second_profile"),
        )
        self.assertEqual(
            tuple(profile.label for profile in profiles),
            ("Первый профиль", "Второй профиль"),
        )
        self.assertEqual(
            tuple(profile.profile_dir.name for profile in profiles),
            ("01-first", "02-second"),
        )

    def test_first_available_profile_is_used_by_default(self) -> None:
        """
        Проверяет выбор первого доступного профиля по умолчанию.
        """
        config = self._create_config()
        first_profile = config.available_profiles()[0]

        self.assertEqual(config.profile_dir, first_profile.profile_dir)
        self.assertEqual(config.current_profile_id, first_profile.profile_id)

    def test_abstract_profile_is_not_used_as_default_when_concrete_exists(self) -> None:
        """
        Проверяет, что конструктор не перехватывает профиль по умолчанию.
        """
        self._write_abstract_profile()

        config = self._create_config()

        self.assertEqual(config.current_profile_id, "first_profile")

    def test_can_load_profile_by_id(self) -> None:
        """
        Проверяет загрузку выбранного профиля по идентификатору.
        """
        config = self._create_config(profile_id="first_profile")
        personality_filter = F2RobotPersonalityFilter(config)

        self.assertEqual(config.current_profile_id, "first_profile")
        self.assertEqual(
            personality_filter.robot_profile_values,
            {"first_profile": {"temperament": "calm"}},
        )
        self.assertEqual(
            personality_filter.robot_profile_labels,
            {"first_profile": "Первый профиль"},
        )

    def test_abstract_profile_loads_without_robot_gif_and_exposes_trait_terms(self) -> None:
        """
        Проверяет прямую загрузку abstract как конструктора персонажа.
        """
        self._write_abstract_profile()

        config = self._create_config(profile_id="abstract")
        personality_filter = F2RobotPersonalityFilter(config)

        self.assertTrue(config.is_abstract_profile)
        self.assertIsNone(config.robot_gif_config)
        self.assertIsNone(config.robot_gif_path)
        self.assertEqual(personality_filter.default_profile["temperament"], "medium")
        self.assertEqual(
            personality_filter.profile_options["temperament"],
            ("low", "medium", "high"),
        )
        self.assertEqual(
            personality_filter.term_labels["temperament"],
            {
                "low": "низкий",
                "medium": "средний",
                "high": "высокий",
            },
        )
        self.assertEqual(len(personality_filter.default_rules), 1)
        self.assertEqual(personality_filter.default_rules[0].rule_id, "AR_common")

    def test_concrete_profile_is_extended_with_abstract_rules_and_parameters(self) -> None:
        """
        Проверяет добавление общих правил и параметров к конкретному профилю.
        """
        self._write_abstract_profile()

        config = self._create_config(profile_id="second_profile")
        personality_filter = F2RobotPersonalityFilter(config)

        self.assertFalse(config.is_abstract_profile)
        self.assertEqual(
            tuple(rule["rule_id"] for rule in config.rules_config["rules"]),
            ("R_all_terms", "AR_common"),
        )
        self.assertIn("social_circle", personality_filter.relation_options)
        self.assertIn("abstract_relation", personality_filter.relation_options)
        self.assertIn(
            "abstract_pressure",
            {feature for feature, *_ in personality_filter.slider_specs},
        )
        self.assertEqual(
            personality_filter.profile_options["temperament"],
            ("strict",),
        )

    def test_abstract_and_concrete_rules_for_same_scenario_are_aggregated(self) -> None:
        """
        Проверяет, что общее и конкретное правило одного сценария не конфликтуют.
        """
        self._write_abstract_profile()
        config = self._create_config(profile_id="second_profile")
        personality_filter = F2RobotPersonalityFilter(config)

        filtered = personality_filter.filter_scenario_weights(
            {"test_scenario": 0.4},
            profile={"temperament": "strict"},
            relation={"social_circle": "close", "abstract_relation": "trusted"},
            situation={"pressure": 0.2, "abstract_pressure": 0.5},
        )

        self.assertEqual(
            {activation.rule_id for activation in filtered[0].activations},
            {"R_all_terms", "AR_common"},
        )
        self.assertGreater(filtered[0].modified_weight, filtered[0].original_weight)

    def test_abstract_profile_does_not_load_concrete_rules_or_parameters(self) -> None:
        """
        Проверяет изоляцию режима конструктора от конкретных профилей.
        """
        self._write_abstract_profile()

        config = self._create_config(profile_id="abstract")
        personality_filter = F2RobotPersonalityFilter(config)

        self.assertNotIn("social_circle", personality_filter.relation_options)
        self.assertNotIn(
            "pressure",
            {feature for feature, *_ in personality_filter.slider_specs},
        )
        self.assertEqual(
            tuple(rule.rule_id for rule in personality_filter.default_rules),
            ("AR_common",),
        )

    def test_complete_rules_are_accepted(self) -> None:
        """
        Проверяет принятие основным валидатором полной конфигурации правил.
        """
        config = self._create_config(profile_id="second_profile")

        self.assertEqual(config.current_profile_id, "second_profile")
        self.assertEqual(config.rules_config["rules"][0]["rule_id"], "R_all_terms")

    def test_configuration_with_all_required_labels_is_accepted(self) -> None:
        """
        Проверяет принятие основным валидатором всех обязательных подписей.
        """
        config = self._create_config(profile_id="second_profile")

        self.assertEqual(
            config.rule_effects_config["labels"],
            {"increase": "усиление"},
        )

    def test_robot_gif_can_be_configured_by_filename(self) -> None:
        """
        Проверяет поиск GIF по имени файла в общем каталоге GIF-анимаций.
        """
        path = self.config.profile_dir / "robot_gif.json"
        self._write_json(path, {"gif_path": "appeal6.gif"})

        config = self._create_config(profile_id="second_profile")

        self.assertEqual(
            config.robot_gif_path,
            self.root_dir / "data" / "f2robot_gifs" / "appeal6.gif",
        )

    def test_robot_gif_project_relative_path_works_with_src_layout(self) -> None:
        """
        Проверяет путь от корня проекта при каталогах конфигурации внутри src.
        """
        src_dir = self.root_dir / "src"
        src_profiles_root = src_dir / "profiles"
        src_data_dir = src_dir / "data"
        shutil.copytree(self.profiles_root, src_profiles_root)
        shutil.copytree(self.data_dir, src_data_dir)
        self._write_json(
            src_profiles_root / "02-second" / "robot_gif.json",
            {"gif_path": "src/data/f2robot_gifs/second_profile.gif"},
        )

        config = F2RobotProfileConfig(
            profile_id="second_profile",
            profiles_root=src_profiles_root,
            data_dir=src_data_dir,
        )

        self.assertEqual(
            config.robot_gif_path,
            src_data_dir / "f2robot_gifs" / "second_profile.gif",
        )

    def test_missing_any_profile_file_is_rejected(self) -> None:
        """
        Проверяет ошибку загрузки при отсутствии любого файла профиля.
        """
        for filename in (
            "trait_profile.json",
            "relation_params.json",
            "situation_params.json",
            "rules.json",
            "robot_gif.json",
        ):
            with self.subTest(filename=filename):
                path = self.config.profile_dir / filename
                content = path.read_text(encoding="utf-8")
                path.unlink()
                try:
                    with self.assertRaisesRegex(FileNotFoundError, filename):
                        F2RobotProfileConfig(
                            profile_dir=self.config.profile_dir,
                            profiles_root=self.profiles_root,
                            data_dir=self.data_dir,
                        )
                finally:
                    path.write_text(content, encoding="utf-8")

    def test_empty_profiles_directory_is_rejected(self) -> None:
        """
        Проверяет ошибку создания конфигурации без доступных профилей.
        """
        empty_profiles_root = self.root_dir / "empty_profiles"
        empty_profiles_root.mkdir()

        with self.assertRaisesRegex(RuntimeError, "No profiles found"):
            F2RobotProfileConfig(
                profiles_root=empty_profiles_root,
                data_dir=self.data_dir,
            )

    def test_incomplete_rules_emit_warning(self) -> None:
        """
        Проверяет предупреждение о терме, не используемом ни в одном правиле.
        """
        rules_path = self.config.profile_dir / "rules.json"
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        rules["rules"][0]["conditions"][1]["terms"] = ["close"]
        self._write_json(rules_path, rules)

        with self.assertWarnsRegex(
            UserWarning,
            "Rules do not cover configured terms: social_circle: distant",
        ):
            config = self._create_config(profile_id="second_profile")

        self.assertEqual(config.current_profile_id, "second_profile")

    def test_missing_labels_are_detected(self) -> None:
        """
        Проверяет обнаружение отсутствующей подписи эффекта правила.
        """
        self._write_json(
            self.data_dir / "rule_effects.json",
            {
                "section": "rule_effects",
                "multipliers": {"increase": 1.25},
                "labels": {},
            },
        )

        with self.assertRaisesRegex(
            ValueError,
            "rule_effects.json labels must contain effects: increase",
        ):
            self._create_config(profile_id="second_profile")

    def test_missing_required_json_key_is_rejected(self) -> None:
        """
        Проверяет ошибку загрузки при отсутствии обязательного ключа JSON.
        """
        cases = (
            (self.config.profile_dir / "trait_profile.json", "traits"),
            (self.config.profile_dir / "relation_params.json", "parameters"),
            (self.config.profile_dir / "situation_params.json", "parameters"),
            (self.config.profile_dir / "rules.json", "rules"),
            (self.config.profile_dir / "robot_gif.json", "gif_path"),
            (self.data_dir / "trait_labels.json", "labels"),
            (self.data_dir / "rule_effects.json", "multipliers"),
        )

        for path, missing_key in cases:
            with self.subTest(filename=path.name, missing_key=missing_key):
                original = json.loads(path.read_text(encoding="utf-8"))
                invalid = dict(original)
                invalid.pop(missing_key)
                self._write_json(path, invalid)
                try:
                    with self.assertRaisesRegex(
                        ValueError,
                        f"must contain keys: {missing_key}",
                    ):
                        self._create_config(profile_id="second_profile")
                finally:
                    self._write_json(path, original)

    def test_robot_gif_json_rejects_extra_fields(self) -> None:
        """
        Проверяет, что robot_gif.json содержит только путь к GIF.
        """
        path = self.config.profile_dir / "robot_gif.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        invalid = dict(original)
        invalid["label"] = "Лишнее поле"
        self._write_json(path, invalid)

        try:
            with self.assertRaisesRegex(
                ValueError,
                "robot_gif.json: Additional properties are not allowed",
            ):
                self._create_config(profile_id="second_profile")
        finally:
            self._write_json(path, original)


if __name__ == "__main__":
    unittest.main()
