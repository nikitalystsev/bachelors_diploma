"""Загрузка профилей робота и связанных JSON-конфигураций."""

import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError


ABSTRACT_PROFILE_ID = "abstract"

REQUIRED_PROFILE_FILES = (
    "trait_profile.json",
    "relation_params.json",
    "situation_params.json",
    "rules.json",
)
CONCRETE_PROFILE_FILES = REQUIRED_PROFILE_FILES + ("robot_gif.json",)


@dataclass(frozen=True)
class RobotProfileDescriptor:
    """
    Краткое описание профиля, доступного для выбора в интерфейсе.
    """

    profile_id: str
    label: str
    profile_dir: Path


class F2RobotProfileValidator:
    """
    Валидирует JSON-конфигурации профиля робота.
    """

    TRAIT_PROFILE_SCHEMA: dict[str, Any] = {
        "type": "object",
        "required": ["profile_id", "label", "traits"],
        "properties": {
            "section": {"const": "profile"},
            "profile_id": {},
            "label": {},
            "traits": {
                "type": "object",
                "minProperties": 1,
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "value": {},
                        "label": {},
                        "terms": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "required": ["term", "label"],
                                "properties": {
                                    "term": {},
                                    "label": {},
                                },
                            },
                        },
                    },
                },
            },
        },
    }
    TRAIT_LABELS_SCHEMA: dict[str, Any] = {
        "type": "object",
        "required": ["labels"],
        "properties": {
            "section": {"const": "trait_labels"},
            "labels": {"type": "object"},
        },
    }
    PARAMETERS_SCHEMA: dict[str, Any] = {
        "type": "object",
        "required": ["parameters"],
        "properties": {
            "section": {"enum": ["relation", "situation"]},
            "parameters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["feature", "label", "input", "default"],
                    "properties": {
                        "feature": {},
                        "label": {},
                        "input": {"enum": ["select", "slider"]},
                        "default": {},
                        "options": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "required": ["term", "label"],
                                "properties": {
                                    "term": {},
                                    "label": {},
                                },
                            },
                        },
                        "minimum": {"type": "number"},
                        "maximum": {"type": "number"},
                        "fuzzy_terms": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": [
                                    "term",
                                    "label",
                                    "function_type",
                                    "points",
                                ],
                                "properties": {
                                    "term": {},
                                    "label": {},
                                    "function_type": {},
                                    "points": {
                                        "type": "array",
                                        "minItems": 1,
                                    },
                                },
                            },
                        },
                    },
                    "allOf": [
                        {
                            "if": {"properties": {"input": {"const": "select"}}},
                            "then": {"required": ["options"]},
                        },
                        {
                            "if": {"properties": {"input": {"const": "slider"}}},
                            "then": {"required": ["minimum", "maximum"]},
                        },
                    ],
                },
            },
        },
    }
    RULE_EFFECTS_SCHEMA: dict[str, Any] = {
        "type": "object",
        "required": ["multipliers", "labels"],
        "properties": {
            "section": {"const": "rule_effects"},
            "multipliers": {
                "type": "object",
                "minProperties": 1,
                "additionalProperties": {"type": "number"},
            },
            "labels": {"type": "object"},
        },
    }
    RULES_SCHEMA: dict[str, Any] = {
        "type": "object",
        "required": ["rules"],
        "properties": {
            "rules": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": [
                        "rule_id",
                        "label",
                        "conditions",
                        "target_scenarios",
                        "effect",
                    ],
                    "properties": {
                        "rule_id": {},
                        "label": {},
                        "conditions": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "required": ["feature", "terms"],
                                "properties": {
                                    "feature": {},
                                    "terms": {
                                        "type": "array",
                                        "minItems": 1,
                                    },
                                },
                            },
                        },
                        "target_scenarios": {
                            "type": "array",
                            "minItems": 1,
                        },
                        "effect": {},
                    },
                },
            },
        },
    }
    ROBOT_GIF_SCHEMA: dict[str, Any] = {
        "type": "object",
        "required": ["gif_path"],
        "properties": {
            "gif_path": {"type": "string", "minLength": 1},
        },
        "additionalProperties": False,
    }

    def validate(
        self,
        *,
        profile_config: dict[str, Any],
        trait_labels_config: dict[str, Any],
        relation_config: dict[str, Any],
        situation_config: dict[str, Any],
        rule_effects_config: dict[str, Any],
        rules_config: dict[str, Any],
        robot_gif_config: dict[str, Any] | None,
        additional_profile_configs: tuple[dict[str, Any], ...] = (),
    ) -> None:
        """
        Проверяет структуру файлов и целостность ссылок между ними.
        """
        trait_labels = self._validate_trait_labels(trait_labels_config)
        configured_terms = self._validate_profile_config(
            profile_config,
            trait_labels,
        )
        coverage_terms = {
            feature: set(terms)
            for feature, terms in configured_terms.items()
        }
        for additional_profile_config in additional_profile_configs:
            for feature, terms in self._validate_profile_config(
                additional_profile_config,
                trait_labels,
            ).items():
                configured_terms.setdefault(feature, set()).update(terms)
        for filename, config in (
            ("relation_params.json", relation_config),
            ("situation_params.json", situation_config),
        ):
            for feature, terms in self._validate_parameters(filename, config).items():
                configured_terms.setdefault(feature, set()).update(terms)
                coverage_terms.setdefault(feature, set()).update(terms)

        configured_effects = self._validate_rule_effects(rule_effects_config)
        self._validate_rules(
            rules_config,
            configured_terms,
            configured_effects,
            coverage_terms=coverage_terms,
        )
        if robot_gif_config is not None:
            self._validate_robot_gif(robot_gif_config)

    @classmethod
    def validate_profile_descriptor(
        cls,
        profile_config: dict[str, Any],
        path: Path,
    ) -> dict[str, Any]:
        """
        Проверяет минимальную структуру trait_profile.json при поиске профилей.
        """
        cls._validate_json_schema(profile_config, cls.TRAIT_PROFILE_SCHEMA, str(path))
        return profile_config

    @classmethod
    def _validate_trait_labels(cls, config: dict[str, Any]) -> dict[str, Any]:
        """
        Проверяет структуру файла подписей черт.
        """
        cls._validate_json_schema(config, cls.TRAIT_LABELS_SCHEMA, "trait_labels.json")
        return config["labels"]

    @classmethod
    def _validate_profile_config(
        cls,
        config: dict[str, Any],
        trait_labels: dict[str, Any],
    ) -> dict[str, set[str]]:
        """
        Проверяет структуру профиля и возвращает настроенные термы черт.
        """
        cls._validate_json_schema(config, cls.TRAIT_PROFILE_SCHEMA, "trait_profile.json")
        configured_terms: dict[str, set[str]] = {}
        for feature, trait in config["traits"].items():
            if feature not in trait_labels:
                raise ValueError(f"trait_labels.json labels must contain {feature}")
            if not isinstance(trait, dict):
                raise ValueError(f"trait_profile.json traits {feature} must be an object")

            if "terms" in trait:
                configured_terms[str(feature)] = cls._trait_terms(feature, trait)
                continue

            if "value" not in trait or "label" not in trait:
                raise ValueError(
                    "trait_profile.json traits "
                    f"{feature} must contain value and label or terms"
                )
            configured_terms[str(feature)] = {str(trait["value"])}
        return configured_terms

    @staticmethod
    def _trait_terms(feature: str, trait: dict[str, Any]) -> set[str]:
        """
        Возвращает доступные термы абстрактной черты.
        """
        raw_terms = trait.get("terms")
        if not isinstance(raw_terms, list) or not raw_terms:
            raise ValueError(f"trait_profile.json traits {feature} terms must be non-empty")

        terms: set[str] = set()
        for term_index, raw_term in enumerate(raw_terms):
            if not isinstance(raw_term, dict):
                raise ValueError(
                    "trait_profile.json traits "
                    f"{feature} terms[{term_index}] must be an object"
                )
            if "term" not in raw_term or "label" not in raw_term:
                raise ValueError(
                    "trait_profile.json traits "
                    f"{feature} terms[{term_index}] must contain term and label"
                )
            terms.add(str(raw_term["term"]))
        return terms

    @classmethod
    def _validate_parameters(
        cls,
        filename: str,
        config: dict[str, Any],
    ) -> dict[str, set[str]]:
        """
        Проверяет параметры отношений или ситуации и возвращает их термы.
        """
        cls._validate_json_schema(config, cls.PARAMETERS_SCHEMA, filename)
        configured_terms: dict[str, set[str]] = {}

        for parameter in config["parameters"]:
            feature = str(parameter["feature"])
            input_type = parameter["input"]
            terms_for_feature: set[str] = set()

            if input_type == "select":
                terms_for_feature.update(
                    str(option["term"]) for option in parameter["options"]
                )
            elif input_type == "slider":
                terms_for_feature.update(
                    str(term["term"]) for term in parameter.get("fuzzy_terms", [])
                )

            configured_terms.setdefault(feature, set()).update(terms_for_feature)

        return configured_terms

    @classmethod
    def _validate_rule_effects(cls, config: dict[str, Any]) -> set[str]:
        """
        Проверяет структуру эффектов правил и наличие их подписей.
        """
        cls._validate_json_schema(config, cls.RULE_EFFECTS_SCHEMA, "rule_effects.json")
        multipliers = config["multipliers"]
        labels = config["labels"]
        missing_labels = set(multipliers) - set(labels)
        if missing_labels:
            raise ValueError(
                "rule_effects.json labels must contain effects: "
                f"{', '.join(sorted(missing_labels))}"
            )
        return {str(effect) for effect in multipliers}

    @classmethod
    def _validate_rules(
        cls,
        config: dict[str, Any],
        configured_terms: dict[str, set[str]],
        configured_effects: set[str],
        *,
        coverage_terms: dict[str, set[str]] | None = None,
    ) -> None:
        """
        Проверяет ссылки правил и покрытие настроенных термов.
        """
        cls._validate_json_schema(config, cls.RULES_SCHEMA, "rules.json")
        covered_terms: dict[str, set[str]] = {}

        for rule_index, rule in enumerate(config["rules"]):
            source = f"rules.json rules[{rule_index}]"
            effect = str(rule["effect"])
            if effect not in configured_effects:
                raise ValueError(f"{source} references undefined effect {effect}")

            for condition_index, condition in enumerate(rule["conditions"]):
                condition_source = f"{source} conditions[{condition_index}]"
                feature = str(condition["feature"])
                condition_terms = {str(term) for term in condition["terms"]}
                if feature not in configured_terms:
                    raise ValueError(
                        f"{condition_source} references undefined feature {feature}"
                    )
                undefined_terms = condition_terms - configured_terms[feature]
                if undefined_terms:
                    raise ValueError(
                        f"{condition_source} references undefined terms: "
                        f"{', '.join(sorted(undefined_terms))}"
                    )
                covered_terms.setdefault(feature, set()).update(condition_terms)

        uncovered_terms = {
            feature: terms - covered_terms.get(feature, set())
            for feature, terms in (coverage_terms or configured_terms).items()
            if terms - covered_terms.get(feature, set())
        }
        if uncovered_terms:
            details = "; ".join(
                f"{feature}: {', '.join(sorted(terms))}"
                for feature, terms in uncovered_terms.items()
            )
            warnings.warn(
                f"Rules do not cover configured terms: {details}",
                UserWarning,
                stacklevel=2,
            )

    @classmethod
    def _validate_robot_gif(cls, config: dict[str, Any]) -> None:
        """
        Проверяет структуру файла с путем к GIF-анимации профиля.
        """
        cls._validate_json_schema(config, cls.ROBOT_GIF_SCHEMA, "robot_gif.json")

    @staticmethod
    def _validate_json_schema(
        value: dict[str, Any],
        schema: dict[str, Any],
        source: str,
    ) -> None:
        """
        Запускает jsonschema и приводит ошибки к сообщениям загрузчика.
        """
        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(value), key=lambda error: error.path)
        if not errors:
            return

        raise ValueError(
            F2RobotProfileValidator._format_schema_error(source, errors[0])
        )

    @staticmethod
    def _format_schema_error(source: str, error: ValidationError) -> str:
        """
        Формирует компактное сообщение об ошибке схемы.
        """
        if error.validator == "required":
            missing_keys = error.message.split("'")[1]
            return f"{source} must contain keys: {missing_keys}"

        location = source
        if error.path:
            location += " " + " ".join(str(part) for part in error.path)

        if error.validator == "type" and error.validator_value == "object":
            return f"{location} must be an object"
        if error.validator == "type" and error.validator_value == "array":
            return f"{location} must be an array"
        if error.validator == "minProperties":
            return f"{location} must be a non-empty object"
        if error.validator == "minItems":
            return f"{location} must be a non-empty array"

        return f"{location}: {error.message}"


class F2RobotProfileConfig:
    """
    Загружает JSON-конфигурацию профиля F2Robot из файлов.
    """

    def __init__(
        self,
        profile_dir: Path | str | None = None,
        *,
        profile_id: str | None = None,
        profiles_root: Path | str | None = None,
        data_dir: Path | str | None = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent
        self.data_dir = Path(data_dir) if data_dir is not None else base_dir / "data"
        self.profiles_root = (
            Path(profiles_root) if profiles_root is not None else base_dir / "profiles"
        )
        data_parent = self.data_dir.parent
        self.project_root = data_parent.parent if data_parent.name == "src" else data_parent
        if profile_dir is not None:
            self.profile_dir = Path(profile_dir)
        elif profile_id is not None:
            self.profile_dir = self.profile_dir_by_id(profile_id)
        else:
            self.profile_dir = self._default_profile_dir()
        self.current_profile_id: str | None = None
        self.is_abstract_profile = False
        self.robot_gif_config: dict[str, Any] | None = None
        self.robot_gif_path: Path | None = None
        self._load_f2robot_profile()

    def _default_profile_dir(self) -> Path:
        """
        Возвращает каталог профиля по умолчанию.
        """
        profiles = self.available_profiles()
        for profile in profiles:
            if profile.profile_id != ABSTRACT_PROFILE_ID:
                return profile.profile_dir
        if profiles:
            return profiles[0].profile_dir
        raise RuntimeError(f"No profiles found in {self.profiles_root}")

    def available_profiles(self) -> tuple[RobotProfileDescriptor, ...]:
        """
        Возвращает профили из src/profiles.
        """
        return self._profiles_from_directory_tree()

    def _profiles_from_directory_tree(self) -> tuple[RobotProfileDescriptor, ...]:
        """
        Собирает профили из отдельных папок внутри profiles_root.
        """
        if not self.profiles_root.is_dir():
            return ()

        profiles: list[RobotProfileDescriptor] = []
        for profile_dir in sorted(self.profiles_root.iterdir(), key=lambda path: path.name):
            if not profile_dir.is_dir():
                continue
            trait_profile_path = profile_dir / "trait_profile.json"
            if not trait_profile_path.is_file():
                continue
            profile_config = self._read_json_file(trait_profile_path)
            profile = self._single_profile(profile_config, trait_profile_path)
            profile_id = str(profile.get("profile_id", profile_dir.name))
            profiles.append(
                RobotProfileDescriptor(
                    profile_id=profile_id,
                    label=str(profile.get("label", profile_id)),
                    profile_dir=profile_dir,
                )
            )
        return tuple(profiles)

    def profile_dir_by_id(self, profile_id: str) -> Path:
        """
        Находит каталог профиля по идентификатору.
        """
        for profile in self.available_profiles():
            if profile.profile_id == profile_id:
                return profile.profile_dir
        return self.profiles_root / profile_id

    def _load_f2robot_profile(self) -> None:
        """
        Загружает все файлы конфигурации профиля.
        """
        self._validate_required_profile_files()
        self.profile_config = self.load_profile_json(
            "trait_profile.json",
            "profile",
        )
        self.trait_labels_config = self.load_profile_json(
            "trait_labels.json",
            "trait_labels",
        )
        self.relation_config = self.load_profile_json(
            "relation_params.json",
            "relation",
        )
        self.situation_config = self.load_profile_json(
            "situation_params.json",
            "situation",
        )
        self.rule_effects_config = self.load_profile_json(
            "rule_effects.json",
            "rule_effects",
        )
        self.rules_config = self.load_profile_json("rules.json")
        self.current_profile_id = self._current_profile_id()
        self.is_abstract_profile = self.current_profile_id == ABSTRACT_PROFILE_ID
        additional_profile_configs: tuple[dict[str, Any], ...] = ()
        if not self.is_abstract_profile:
            additional_profile_configs = self._apply_abstract_extensions()
        self.robot_gif_config = (
            self.load_profile_json("robot_gif.json")
            if self._json_path("robot_gif.json").is_file()
            else None
        )
        F2RobotProfileValidator().validate(
            profile_config=self.profile_config,
            trait_labels_config=self.trait_labels_config,
            relation_config=self.relation_config,
            situation_config=self.situation_config,
            rule_effects_config=self.rule_effects_config,
            rules_config=self.rules_config,
            robot_gif_config=self.robot_gif_config,
            additional_profile_configs=additional_profile_configs,
        )
        if self.robot_gif_config is not None:
            self.robot_gif_path = self._resolve_robot_gif_path(
                str(self.robot_gif_config["gif_path"])
            )

    def _validate_required_profile_files(self) -> None:
        """
        Проверяет наличие всех обязательных файлов выбранного профиля.
        """
        required_files = self._required_profile_files()
        missing_files = [
            filename
            for filename in required_files
            if not (self.profile_dir / filename).is_file()
        ]
        if missing_files:
            raise FileNotFoundError(
                f"{self.profile_dir} is missing required profile files: "
                f"{', '.join(missing_files)}"
            )

    def _required_profile_files(self) -> tuple[str, ...]:
        """
        Возвращает обязательные файлы с учетом особого профиля-конструктора.
        """
        trait_profile_path = self.profile_dir / "trait_profile.json"
        if not trait_profile_path.is_file():
            return CONCRETE_PROFILE_FILES

        profile_config = self._read_json_file(trait_profile_path)
        if str(profile_config.get("profile_id", self.profile_dir.name)) == ABSTRACT_PROFILE_ID:
            return REQUIRED_PROFILE_FILES
        return CONCRETE_PROFILE_FILES

    def _apply_abstract_extensions(self) -> tuple[dict[str, Any], ...]:
        """
        Добавляет общие правила и параметры abstract к выбранному конкретному профилю.
        """
        abstract_dir = self.profile_dir_by_id(ABSTRACT_PROFILE_ID)
        if not abstract_dir.is_dir() or abstract_dir == self.profile_dir:
            return ()

        abstract_profile_config = self._read_json_file(
            abstract_dir / "trait_profile.json"
        )
        abstract_relation_config = self._read_json_file(
            abstract_dir / "relation_params.json"
        )
        abstract_situation_config = self._read_json_file(
            abstract_dir / "situation_params.json"
        )
        abstract_rules_config = self._read_json_file(abstract_dir / "rules.json")

        if abstract_profile_config.get("section") != "profile":
            raise ValueError("abstract trait_profile.json must describe the profile section")
        if abstract_relation_config.get("section") != "relation":
            raise ValueError("abstract relation_params.json must describe the relation section")
        if abstract_situation_config.get("section") != "situation":
            raise ValueError("abstract situation_params.json must describe the situation section")

        self.relation_config = self._merge_parameters(
            self.relation_config,
            abstract_relation_config,
        )
        self.situation_config = self._merge_parameters(
            self.situation_config,
            abstract_situation_config,
        )
        self.rules_config = {
            "rules": [
                *self.rules_config.get("rules", []),
                *abstract_rules_config.get("rules", []),
            ]
        }
        return (abstract_profile_config,)

    @staticmethod
    def _merge_parameters(
        primary_config: dict[str, Any],
        additional_config: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Добавляет параметры additional, не дублируя признаки основного профиля.
        """
        merged_parameters = list(primary_config.get("parameters", []))
        known_features = {
            str(parameter.get("feature"))
            for parameter in merged_parameters
            if isinstance(parameter, dict)
        }
        for parameter in additional_config.get("parameters", []):
            if not isinstance(parameter, dict):
                merged_parameters.append(parameter)
                continue
            feature = str(parameter.get("feature"))
            if feature in known_features:
                continue
            known_features.add(feature)
            merged_parameters.append(parameter)

        return {
            **primary_config,
            "parameters": merged_parameters,
        }

    def load_profile_json(
        self,
        filename: str,
        expected_section: str | None = None,
    ) -> dict[str, Any]:
        """
        Читает JSON-файл из каталога профиля.
        """
        path = self._json_path(filename)
        data = self._read_json_file(path)

        if expected_section is not None and data.get("section") != expected_section:
            raise ValueError(f"{filename} must describe the {expected_section} section")

        return data

    def _json_path(self, filename: str) -> Path:
        """
        Ищет JSON сначала в каталоге выбранного профиля, затем в общих данных.
        """
        profile_path = self.profile_dir / filename
        if profile_path.is_file():
            return profile_path

        shared_path = self.data_dir / filename
        if shared_path.is_file():
            return shared_path

        return profile_path

    def _resolve_robot_gif_path(self, gif_path: str) -> Path:
        """
        Преобразует путь из robot_gif.json в абсолютный путь.
        """
        path = Path(gif_path)
        if path.is_absolute():
            return path
        if path.parent == Path("."):
            return self.data_dir / "f2robot_gifs" / path
        return self.project_root / path

    @staticmethod
    def _read_json_file(path: Path) -> dict[str, Any]:
        """
        Читает JSON-объект из файла.
        """
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise TypeError(f"{path} must contain a JSON object")

        return data

    @staticmethod
    def _single_profile(
        profile_config: dict[str, Any],
        path: Path,
    ) -> dict[str, Any]:
        """
        Проверяет и возвращает профиль из trait_profile.json.
        """
        return F2RobotProfileValidator.validate_profile_descriptor(profile_config, path)

    def _current_profile_id(self) -> str | None:
        """
        Определяет идентификатор профиля из загруженного trait_profile.json.
        """
        profile_id = self.profile_config.get("profile_id")
        if profile_id is None:
            return None
        return str(profile_id)
