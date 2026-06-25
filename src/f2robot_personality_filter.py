"""Нечеткий фильтр весов сценариев с учетом профиля и контекста."""

from dataclasses import dataclass
from typing import Any

from simpful import (
    FuzzySystem,
    FuzzySet,
    LinguisticVariable,
    Singletons_MF,
    Trapezoidal_MF,
    Triangular_MF,
)

from checks import check_float


SCENARIO_KEY = "scenario"
WEIGHT_KEY = "weight"
PROXIMITY_KEY = "proximity"
DEFAULT_OUTPUT_KEY = "scenario_proximities"


@dataclass(frozen=True)
class Condition:
    """
    Описывает одно условие правила: признак и допустимые термы.
    """

    feature: str
    terms: tuple[str, ...]


@dataclass(frozen=True)
class FilterRule:
    """
    Задает правило перевзвешивания для конкретных сценариев.
    """

    rule_id: str
    conditions: tuple[Condition, ...]
    target_scenarios: tuple[str, ...]
    effect: str


@dataclass(frozen=True)
class RuleActivation:
    """
    Хранит результат срабатывания одного правила.
    """

    rule_id: str
    strength: float
    effect: str
    effect_multiplier: float
    condition_features: tuple[str, ...]


@dataclass(frozen=True)
class FilteredScenario:
    """
    Хранит исходный и пересчитанный вес сценария.
    """

    scenario: str
    original_weight: float
    multiplier: float
    modified_weight: float
    activations: tuple[RuleActivation, ...]


@dataclass(frozen=True)
class FuzzyTermSpec:
    """
    Описывает терм нечеткого признака и его функцию принадлежности.
    """

    term: str
    function_type: str
    points: tuple[float, ...]

    @classmethod
    def triangle(cls, term: str, a: float, b: float, c: float) -> "FuzzyTermSpec":
        """
        Создает терм с треугольной функцией принадлежности.
        """
        return cls(term=term, function_type="triangle", points=(a, b, c))

    @classmethod
    # Четыре точки являются естественной сигнатурой трапециевидной функции.
    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def trapezoid(
        cls,
        term: str,
        a: float,
        b: float,
        c: float,
        d: float,
    ) -> "FuzzyTermSpec":
        """
        Создает терм с трапециевидной функцией принадлежности.
        """
        return cls(term=term, function_type="trapezoid", points=(a, b, c, d))

    def to_fuzzy_set(self) -> FuzzySet:
        """
        Преобразует описание терма в объект Simpful.
        """
        if self.function_type == "triangle":
            a, b, c = self.points
            return FuzzySet(function=Triangular_MF(a=a, b=b, c=c), term=self.term)

        if self.function_type == "trapezoid":
            a, b, c, d = self.points
            return FuzzySet(
                function=Trapezoidal_MF(a=a, b=b, c=c, d=d),
                term=self.term,
            )

        raise ValueError(f"Unsupported membership function: {self.function_type}")


@dataclass(frozen=True)
class FuzzyVariableSpec:
    """
    Описывает численный признак, который нужно фаззифицировать.
    """

    feature: str
    terms: tuple[FuzzyTermSpec, ...]
    universe: tuple[float, float]


NumericValue = str | int | float
FactDict = dict[str, NumericValue]
ScenarioItem = dict[str, NumericValue]
ScenarioMapping = dict[str, NumericValue]
F2RobotResult = dict[str, list[ScenarioItem]]
ScenarioInput = ScenarioMapping | F2RobotResult | list[ScenarioItem] | tuple[ScenarioItem, ...]
RuleActivationDict = dict[str, str | float | list[str]]
FilteredScenarioDict = dict[str, str | float | list[RuleActivationDict]]


def terms(*values: str) -> tuple[str, ...]:
    """
    Формирует кортеж термов для компактной записи условий.
    """
    return tuple(values)


@dataclass(frozen=True)
class _SimpfulRuleBinding:
    """
    Связывает сгенерированное Simpful-правило с исходным правилом фильтра.
    """

    rule: FilterRule  # Исходное правило фильтра.
    scenario: str  # Сценарий, вес которого изменяет правило.
    output_name: str  # Имя выходной переменной сценария в Simpful.


class SimpfulRuleEngine:  # pylint: disable=too-many-instance-attributes,too-few-public-methods
    """
    Выполняет правила перевзвешивания через Sugeno-вывод библиотеки Simpful.
    """

    _MISSING_VALUE = -1.0

    def __init__(
        self,
        rules: tuple[FilterRule, ...],
        fuzzy_variables: tuple[FuzzyVariableSpec, ...],
        effect_multipliers: dict[str, float],
    ) -> None:
        """
        Создает и настраивает систему нечеткого вывода.
        """
        # Исходные правила перевзвешивания сценариев.
        self._rules = tuple(rules)
        print(f"self.rules: {self._rules}\n")
        if any(not rule.conditions for rule in self._rules):
            raise ValueError("Each filter rule must contain at least one condition")
        # Описания числовых признаков и их функций принадлежности.
        self._fuzzy_variables = tuple(fuzzy_variables)
        print(f"self.fuzzy_variables: {self._fuzzy_variables}\n")
        # Описания числовых признаков, доступные по имени признака.
        self._fuzzy_variables_by_feature = {
            variable.feature: variable for variable in self._fuzzy_variables
        }
        print(f"self.fuzzy_variables_by_feature: {self._fuzzy_variables_by_feature}\n")
        # Числовые множители, соответствующие эффектам правил.
        self._effect_multipliers = dict(effect_multipliers)
        print(f"self.effect_multipliers: {self._effect_multipliers}\n")
        # Числовые идентификаторы строковых категориальных термов.
        self._categorical_values = self._categorical_values_from_rules()
        print(f"self._categorical_values: {self._categorical_values}\n")
        # Соответствие сценариев именам выходных переменных Simpful.
        self._scenario_outputs: dict[str, str] = {}
        # Настраиваемая система нечеткого вывода Simpful.
        self._system = FuzzySystem(show_banner=False, verbose=False)
        # Связи правил Simpful с исходными правилами и сценариями.
        self._bindings: tuple[_SimpfulRuleBinding, ...] = ()

        self._build_system()

    def evaluate(
        self,
        facts: FactDict,
        scenarios: tuple[str, ...],
    ) -> dict[str, tuple[float, tuple[RuleActivation, ...]]]:
        """
        Возвращает Sugeno-множитель и сработавшие правила для каждого сценария.
        """
        if not self._bindings:
            return {
                scenario: (1.0, ())
                for scenario in scenarios
            }

        self._set_variables(facts)
        firing_strengths = self._system.get_firing_strengths()
        activations_by_scenario: dict[str, list[RuleActivation]] = {
            scenario: []
            for scenario in scenarios
        }
        active_outputs: set[str] = set()

        for binding, raw_strength in zip(self._bindings, firing_strengths):
            if binding.scenario not in activations_by_scenario:
                continue
            if not self._rule_context_is_complete(binding.rule, facts):
                continue

            strength = float(raw_strength)
            if strength <= 0.0:
                continue

            active_outputs.add(binding.output_name)
            activations_by_scenario[binding.scenario].append(
                RuleActivation(
                    rule_id=binding.rule.rule_id,
                    strength=strength,
                    effect=binding.rule.effect,
                    effect_multiplier=self._effect_multipliers[binding.rule.effect],
                    condition_features=tuple(
                        condition.feature
                        for condition in binding.rule.conditions
                    ),
                )
            )

        inferred_outputs: dict[str, float] = {}
        if active_outputs:
            inferred_outputs = {
                output: float(value)
                for output, value in self._system.Sugeno_inference(
                    list(active_outputs),
                ).items()
            }

        return {
            scenario: (
                inferred_outputs.get(self._scenario_outputs.get(scenario, ""), 1.0),
                tuple(activations_by_scenario[scenario]),
            )
            for scenario in scenarios
        }

    def _categorical_values_from_rules(self) -> dict[str, dict[str, float]]:
        """
        Назначает числовые значения категориальным термам из правил.
        """
        values: dict[str, dict[str, float]] = {}
        for rule in self._rules:
            for condition in rule.conditions:
                if condition.feature in self._fuzzy_variables_by_feature:
                    continue
                feature_values = values.setdefault(condition.feature, {})
                for term in condition.terms:
                    feature_values.setdefault(term, float(len(feature_values) + 1))
        return values

    def _build_system(self) -> None:
        """
        Добавляет в Simpful переменные, выходы и правила.
        """
        # добавляем лингвистические переменные с термами
        self._add_input_variables()
        # добавляем четкие значение выходных переменных (множителей)
        self._add_outputs()
        # добавили правила
        self._add_rules()

        rules = self._system.get_rules()
        for rule in rules:
            print(f"rule: {rule}")
        print("\n")

    def _add_input_variables(self) -> None:
        """
        Добавляет числовые и категориальные входные переменные.
        """
        for variable in self._fuzzy_variables:
            self._system.add_linguistic_variable(
                variable.feature,
                LinguisticVariable(
                    [term.to_fuzzy_set() for term in variable.terms],
                    universe_of_discourse=list(variable.universe),
                ),
            )

        # параметры, заданные сразу термами обрабатываются вот так
        # (у них нет числовой области значений)
        for feature, values in self._categorical_values.items():
            self._system.add_linguistic_variable(
                feature,
                LinguisticVariable(
                    [
                        FuzzySet(
                            function=Singletons_MF([[value, 1.0]]),
                            term=term,
                        )
                        for term, value in values.items()
                    ],
                    universe_of_discourse=[
                        self._MISSING_VALUE,
                        float(len(values)),
                    ],
                ),
            )

    def _add_outputs(self) -> None:
        """
        Добавляет выходные значения множителей эффектов.
        """
        for effect, multiplier in self._effect_multipliers.items():
            self._system.set_crisp_output_value(effect, multiplier)

    def _add_rules(self) -> None:
        """
        Преобразует правила фильтра в правила Simpful.
        """
        simpful_rules: list[str] = [] # строки правил simpful
        bindings: list[_SimpfulRuleBinding] = []

        for rule in self._rules:
            for scenario in rule.target_scenarios:
                output_name = self._output_for_scenario(scenario)
                simpful_rule = self._rule_to_simpful(rule, output_name)
                simpful_rules.append(simpful_rule)
                bindings.append(
                    _SimpfulRuleBinding(
                        rule=rule,
                        scenario=scenario,
                        output_name=output_name,
                    )
                )

        if simpful_rules:
            self._system.add_rules(simpful_rules)
        self._bindings = tuple(bindings)

    def _output_for_scenario(self, scenario: str) -> str:
        """
        Возвращает уникальное имя выхода Simpful для сценария.
        """
        if scenario not in self._scenario_outputs:
            self._scenario_outputs[scenario] = (
                f"scenario_output_{len(self._scenario_outputs) + 1}"
            )
        return self._scenario_outputs[scenario]

    def _rule_to_simpful(self, rule: FilterRule, output_name: str) -> str:
        """
        Формирует строковое представление правила Simpful.
        """
        clauses = [self._condition_to_simpful(condition) for condition in rule.conditions]
        antecedent = " AND ".join(clauses)
        return f"IF ({antecedent}) THEN ({output_name} IS {rule.effect})"

    @staticmethod
    def _condition_to_simpful(condition: Condition) -> str:
        """
        Формирует строковое представление условия Simpful.
        """
        term_checks = [
            f"({condition.feature} IS {term})"
            for term in condition.terms
        ]
        if len(term_checks) == 1:
            return term_checks[0]
        return "(" + " OR ".join(term_checks) + ")"

    def _set_variables(self, facts: FactDict) -> None:
        """
        Передает значения признаков в систему Simpful.
        """
        for variable in self._fuzzy_variables:
            self._system.set_variable(
                variable.feature,
                self._numeric_value(variable, facts.get(variable.feature)),
            )

        for feature, values in self._categorical_values.items():
            self._system.set_variable(
                feature,
                values.get(str(facts.get(feature)), self._MISSING_VALUE),
            )

    def _numeric_value(
        self,
        variable: FuzzyVariableSpec,
        value: NumericValue | None,
    ) -> float:
        """
        Преобразует и ограничивает числовое значение признака.
        """
        if value is None:
            return self._MISSING_VALUE

        numeric_value = _checked_float(value)
        return _clamp(numeric_value, variable.universe[0], variable.universe[1])

    @staticmethod
    def _rule_context_is_complete(rule: FilterRule, facts: FactDict) -> bool:
        """
        Проверяет наличие всех признаков правила в контексте.
        """
        return all(condition.feature in facts for condition in rule.conditions)


class F2RobotPersonalityFilter:  # pylint: disable=too-many-instance-attributes
    """
    Объединяет нормализацию сценариев, проверку правил и пересчет весов.
    """

    def __init__(
        self,
        profile_config: Any,
    ) -> None:
        """
        Создает фильтр из конфигурации профиля.
        """
        self._build_from_profile_config(profile_config)
        self._rules = self.default_rules
        self._fuzzy_variables = self.default_fuzzy_variables
        self._rule_effect_multipliers = self.rule_effect_multipliers
        self._rule_engine = SimpfulRuleEngine(
            self._rules,
            self._fuzzy_variables,
            self._rule_effect_multipliers,
        )
        self._clip_min = 0.0
        self._clip_max = 1.0

    def _build_from_profile_config(self, profile_config: Any) -> None:
        """
        Формирует правила, fuzzy-шкалы, значения по умолчанию и подписи из JSON-конфига.
        """
        print("\n==================== ИСХОДНЫЕ КОНФИГУРАЦИИ ====================\n")
        profile = profile_config.profile_config
        # print(f"profile: {profile}\n")
        trait_labels = profile_config.trait_labels_config
        # print(f"trait_labels: {trait_labels}\n")
        relation = profile_config.relation_config
        # print(f"relation: {relation}\n")
        situation = profile_config.situation_config
        # print(f"situation: {situation}\n")
        rule_effects = profile_config.rule_effects_config
        # print(f"rule_effects: {rule_effects}\n")
        rules = profile_config.rules_config
        # print(f"rules: {rules}\n")

        print("\n================ ПАРАМЕТРЫ ПРОФИЛЯ И КОНТЕКСТА ================\n")
        self.relation_parameters = tuple(relation["parameters"])
        print(f"self.relation_parameters: {self.relation_parameters}\n")
        self.situation_parameters = tuple(situation["parameters"])
        print(f"self.situation_parameters: {self.situation_parameters}\n")
        self.robot_profile_values = self._profile_trait_values_by_id(profile)
        print(f"self.robot_profile_values: {self.robot_profile_values}\n")
        self.robot_profile_labels = self._profile_trait_labels_by_id(profile)
        print(f"self.robot_profile_labels: {self.robot_profile_labels}\n")
        self.robot_profile_options = tuple(self.robot_profile_values)
        print(f"self.robot_profile_options: {self.robot_profile_options}\n")
        self.default_robot_profile_id = self._default_profile_id(
            profile,
            self.robot_profile_values,
        )
        print(f"self.default_robot_profile_id: {self.default_robot_profile_id}\n")
        self.trait_labels = self._trait_labels(trait_labels)
        print(f"self.trait_labels: {self.trait_labels}\n")
        self.profile_parameters = self._profile_trait_parameters(
            profile,
            self.trait_labels,
            self.robot_profile_values,
            self.default_robot_profile_id,
        )
        print(f"self.profile_parameters: {self.profile_parameters}\n")

        print("\n======================= ДАННЫЕ ДЛЯ GUI ========================\n")
        self.profile_options = self._select_options(self.profile_parameters)
        print(f"self.profile_options: {self.profile_options}\n")
        self.relation_options = self._select_options(self.relation_parameters)
        print(f"self.relation_options: {self.relation_options}\n")
        self.situation_options = self._select_options(self.situation_parameters)
        print(f"self.situation_options: {self.situation_options}\n")
        self.slider_specs = (
            *self._slider_specs("profile", self.profile_parameters),
            *self._slider_specs("relation", self.relation_parameters),
            *self._slider_specs("situation", self.situation_parameters),
        )
        print(f"self.slider_specs: {self.slider_specs}\n")

        print("\n====================== ПОДПИСИ И ЭФФЕКТЫ ======================\n")
        self.feature_labels = self._feature_labels(
            self.profile_parameters,
            self.relation_parameters,
            self.situation_parameters,
        )
        print(f"self.feature_labels: {self.feature_labels}\n")
        self.term_labels = self._term_labels(
            self.profile_parameters,
            self.relation_parameters,
            self.situation_parameters,
        )
        print(f"self.term_labels: {self.term_labels}\n")
        self.effect_labels = dict(rule_effects["labels"])
        print(f"self.effect_labels: {self.effect_labels}\n")
        self.rule_effect_multipliers = self._normalize_effect_multipliers(
            rule_effects["multipliers"],
        )
        print(f"self.rule_effect_multipliers: {self.rule_effect_multipliers}\n")
        self.rule_labels = {
            str(rule["rule_id"]): str(rule.get("label", rule["rule_id"]))
            for rule in rules["rules"]
        }
        print(f"self.rule_labels: {self.rule_labels}\n")

        print("\n=================== ЗНАЧЕНИЯ ПО УМОЛЧАНИЮ ====================\n")
        self.default_profile = dict(
            self.robot_profile_values[self.default_robot_profile_id],
        )
        print(f"self.default_profile: {self.default_profile}\n")
        self.default_relation = self._parameter_defaults(self.relation_parameters)
        print(f"self.default_relation: {self.default_relation}\n")
        self.default_situation = self._parameter_defaults(self.situation_parameters)
        print(f"self.default_situation: {self.default_situation}\n")

        print("\n=============== КОНФИГУРАЦИЯ ДВИЖКА ПРАВИЛ =================\n")
        self.default_fuzzy_variables = self._fuzzy_variables_from_parameters(
            self.profile_parameters,
            self.relation_parameters,
            self.situation_parameters,
        )
        print(f"self.default_fuzzy_variables: {self.default_fuzzy_variables}\n")
        self.default_rules = tuple(self._build_rule(rule) for rule in rules["rules"])
        print(f"self.default_rules: {self.default_rules}\n")

    @staticmethod
    def _profile_trait_values_by_id(
        config: dict[str, Any],
    ) -> dict[str, dict[str, str | float]]:
        """
        Собирает значения термов для единственного профиля робота.
        """
        profile_id, raw_traits = F2RobotPersonalityFilter._single_profile(config)
        values: dict[str, str | float] = {}
        for feature, raw_trait in raw_traits.items():
            if not isinstance(raw_trait, dict):
                raise ValueError(
                    f"{profile_id}.{feature} trait must be an object"
                )
            if "value" in raw_trait:
                values[str(feature)] = str(raw_trait["value"])
                continue
            values[str(feature)] = F2RobotPersonalityFilter._default_trait_term(
                raw_trait,
            )
        return {profile_id: values}

    @staticmethod
    def _profile_trait_labels_by_id(config: dict[str, Any]) -> dict[str, str]:
        """
        Собирает отображаемые названия профилей робота.
        """
        profile_id, _ = F2RobotPersonalityFilter._single_profile(config)
        return {profile_id: str(config.get("label", profile_id))}

    @staticmethod
    def _default_profile_id(
        config: dict[str, Any],
        profile_values: dict[str, dict[str, str | float]],
    ) -> str:
        """
        Определяет профиль робота по умолчанию.
        """
        profile_id = str(config.get("profile_id", ""))
        if profile_id in profile_values:
            return profile_id

        return next(iter(profile_values))

    @staticmethod
    def _trait_labels(config: dict[str, Any]) -> dict[str, str]:
        """
        Загружает переводы названий черт робота из отдельного JSON-файла.
        """
        raw_labels = config.get("labels", {})
        if not isinstance(raw_labels, dict):
            raise ValueError("trait_labels.json labels must be an object")

        return {str(feature): str(label) for feature, label in raw_labels.items()}

    def _profile_trait_parameters(
        self,
        config: dict[str, Any],
        feature_labels: dict[str, str],
        profile_values: dict[str, dict[str, str | float]],
        default_profile_id: str,
    ) -> tuple[dict[str, Any], ...]:
        """
        Формирует общие черты и термы из значений, заданных в профилях робота.
        """
        default_values = profile_values[default_profile_id]
        feature_names = tuple(default_values)
        term_labels = self._profile_term_labels(config)
        parameters: list[dict[str, Any]] = []

        for feature in feature_names:
            term_values = self._profile_trait_terms(config, feature, profile_values)
            parameters.append(
                {
                    "feature": feature,
                    "label": feature_labels[feature],
                    "input": "select",
                    "default": str(default_values[feature]),
                    "options": [
                        {
                            "term": term,
                            "label": term_labels[feature][term],
                        }
                        for term in term_values
                    ],
                }
            )
        return tuple(parameters)

    @staticmethod
    def _profile_term_labels(
        config: dict[str, Any],
    ) -> dict[str, dict[str, str]]:
        """
        Собирает подписи термов из описания traits внутри профилей робота.
        """
        _, raw_traits = F2RobotPersonalityFilter._single_profile(config)
        labels: dict[str, dict[str, str]] = {}
        for feature, raw_trait in raw_traits.items():
            if not isinstance(raw_trait, dict):
                continue
            if "terms" in raw_trait:
                feature_labels = labels.setdefault(str(feature), {})
                for term in raw_trait.get("terms", ()):
                    if not isinstance(term, dict):
                        continue
                    value = str(term.get("term", ""))
                    if value:
                        feature_labels.setdefault(
                            value,
                            str(term.get("label", value)),
                        )
                continue
            value = str(raw_trait.get("value", ""))
            if not value:
                continue
            label = str(raw_trait["label"])
            labels.setdefault(str(feature), {}).setdefault(value, label)
        return labels

    @staticmethod
    def _profile_trait_terms(
        config: dict[str, Any],
        feature: str,
        profile_values: dict[str, dict[str, str | float]],
    ) -> list[str]:
        """
        Возвращает доступные термы черты из abstract terms или из фиксированных профилей.
        """
        _, raw_traits = F2RobotPersonalityFilter._single_profile(config)
        raw_trait = raw_traits.get(feature, {})
        if isinstance(raw_trait, dict) and "terms" in raw_trait:
            return [
                str(term["term"])
                for term in raw_trait.get("terms", ())
                if isinstance(term, dict) and "term" in term
            ]

        term_values: list[str] = []
        for values in profile_values.values():
            term = str(values[feature])
            if term not in term_values:
                term_values.append(term)
        return term_values

    @staticmethod
    def _default_trait_term(raw_trait: dict[str, Any]) -> str:
        """
        Выбирает значение по умолчанию для абстрактной черты конструктора.
        """
        raw_terms = raw_trait.get("terms", ())
        if not isinstance(raw_terms, list) or not raw_terms:
            raise ValueError("abstract trait must contain non-empty terms")

        term_values = [
            str(term["term"])
            for term in raw_terms
            if isinstance(term, dict) and "term" in term
        ]
        if not term_values:
            raise ValueError("abstract trait must contain at least one term")
        if "medium" in term_values:
            return "medium"
        return term_values[0]

    @staticmethod
    def _single_profile(
        config: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """
        Валидирует и возвращает единственный профиль из trait_profile.json.
        """
        profile_id = config.get("profile_id")
        if profile_id is None:
            raise ValueError("trait_profile.json must contain profile_id")
        raw_traits = config.get("traits")
        if not isinstance(raw_traits, dict) or not raw_traits:
            raise ValueError(f"{profile_id} profile must contain non-empty traits")
        return str(profile_id), raw_traits

    @staticmethod
    def _select_options(
        parameters: tuple[dict[str, Any], ...],
    ) -> dict[str, tuple[str, ...]]:
        """
        Извлекает варианты для выпадающих списков интерфейса.
        """
        options: dict[str, tuple[str, ...]] = {}
        for parameter in parameters:
            if parameter.get("input") != "select":
                continue
            options[str(parameter["feature"])] = terms(
                *(str(option["term"]) for option in parameter["options"])
            )
        return options

    @staticmethod
    def _slider_specs(
        section: str,
        parameters: tuple[dict[str, Any], ...],
    ) -> tuple[tuple[str, str, float, float, str], ...]:
        """
        Формирует компактные описания слайдеров для динамического построения GUI.
        """
        specs: list[tuple[str, str, float, float, str]] = []
        for parameter in parameters:
            if parameter.get("input") != "slider":
                continue
            specs.append(
                (
                    str(parameter["feature"]),
                    str(parameter.get("label", parameter["feature"])),
                    float(parameter["minimum"]),
                    float(parameter["maximum"]),
                    section,
                )
            )
        return tuple(specs)

    @staticmethod
    def _feature_labels(
        *parameter_groups: tuple[dict[str, Any], ...],
    ) -> dict[str, str]:
        """
        Собирает человекочитаемые подписи признаков для интерфейса.
        """
        labels: dict[str, str] = {}
        for parameters in parameter_groups:
            for parameter in parameters:
                labels[str(parameter["feature"])] = str(
                    parameter.get("label", parameter["feature"])
                )
        return labels

    @staticmethod
    def _term_labels(
        *parameter_groups: tuple[dict[str, Any], ...],
    ) -> dict[str, dict[str, str]]:
        """
        Собирает подписи дискретных и нечетких термов по каждому признаку.
        """
        labels: dict[str, dict[str, str]] = {}
        for parameters in parameter_groups:
            for parameter in parameters:
                feature = str(parameter["feature"])
                feature_labels: dict[str, str] = {}
                for option in parameter.get("options", ()):
                    feature_labels[str(option["term"])] = str(
                        option.get("label", option["term"])
                    )
                for fuzzy_term in parameter.get("fuzzy_terms", ()):
                    feature_labels[str(fuzzy_term["term"])] = str(
                        fuzzy_term.get("label", fuzzy_term["term"])
                    )
                if feature_labels:
                    labels[feature] = feature_labels
        return labels

    @staticmethod
    def _normalize_effect_multipliers(
        raw_multipliers: dict[str, int | float],
    ) -> dict[str, float]:
        """
        Загружает численные множители эффектов правил.
        """
        return {
            str(effect): float(multiplier)
            for effect, multiplier in raw_multipliers.items()
        }

    @staticmethod
    def _parameter_defaults(
        parameters: tuple[dict[str, Any], ...],
    ) -> dict[str, str | float]:
        """
        Собирает значения по умолчанию для раздела профиля, отношения или ситуации.
        """
        defaults: dict[str, str | float] = {}
        for parameter in parameters:
            value = parameter.get("default")
            if parameter.get("input") == "slider":
                defaults[str(parameter["feature"])] = float(value)
            else:
                defaults[str(parameter["feature"])] = str(value)
        return defaults

    def _fuzzy_variables_from_parameters(
        self,
        *parameter_groups: tuple[dict[str, Any], ...],
    ) -> tuple[FuzzyVariableSpec, ...]:
        """
        Создает нечеткие переменные из slider-параметров, у которых заданы fuzzy_terms.
        """
        variables: list[FuzzyVariableSpec] = []
        for parameters in parameter_groups:
            for parameter in parameters:
                if parameter.get("input") != "slider" or not parameter.get("fuzzy_terms"):
                    continue
                variables.append(
                    FuzzyVariableSpec(
                        feature=str(parameter["feature"]),
                        terms=tuple(
                            self._build_fuzzy_term(term)
                            for term in parameter["fuzzy_terms"]
                        ),
                        universe=(
                            float(parameter["minimum"]),
                            float(parameter["maximum"]),
                        ),
                    )
                )
        return tuple(variables)

    @staticmethod
    def _build_fuzzy_term(raw_term: dict[str, Any]) -> FuzzyTermSpec:
        """
        Преобразует JSON-описание терма в спецификацию нечеткого множества.
        """
        return FuzzyTermSpec(
            term=str(raw_term["term"]),
            function_type=str(raw_term["function_type"]),
            points=tuple(float(point) for point in raw_term["points"]),
        )

    def _build_rule(self, raw_rule: dict[str, Any]) -> FilterRule:
        """
        Преобразует JSON-правило перевзвешивания в объект FilterRule.
        """
        return FilterRule(
            rule_id=str(raw_rule["rule_id"]),
            conditions=tuple(
                self._build_condition(condition)
                for condition in raw_rule.get("conditions", ())
            ),
            target_scenarios=terms(
                *(str(scenario) for scenario in raw_rule["target_scenarios"])
            ),
            effect=str(raw_rule["effect"]),
        )

    @staticmethod
    def _build_condition(raw_condition: dict[str, Any]) -> Condition:
        """
        Преобразует JSON-условие правила в объект Condition.
        """
        return Condition(
            feature=str(raw_condition["feature"]),
            terms=terms(*(str(term) for term in raw_condition["terms"])),
        )

    def filter_scenario_weights(
        self,
        activated_scenarios: ScenarioInput,
        *,
        profile: FactDict | None = None,
        relation: FactDict | None = None,
        situation: FactDict | None = None,
    ) -> list[FilteredScenario]:
        """
        Перевзвешивает активированные сценарии по правилам и контексту.
        """
        normalized_scenarios = self._normalize_scenarios(activated_scenarios)
        rule_context = self._build_rule_context(profile, relation, situation)
        print(f"rule_context: {rule_context}")
        scenario_names = tuple(scenario for scenario, _ in normalized_scenarios)
        rule_results = self._rule_engine.evaluate(rule_context, scenario_names)
        print(f"rule_results: {rule_results}")

        result: list[FilteredScenario] = []
        for scenario, weight in normalized_scenarios:
            multiplier, activations = rule_results.get(scenario, (1.0, ()))
            result.append(
                FilteredScenario(
                    scenario=scenario,
                    original_weight=weight,
                    multiplier=multiplier,
                    modified_weight=_clamp(
                        weight * multiplier,
                        self._clip_min,
                        self._clip_max,
                    ),
                    activations=activations,
                )
            )

        return result

    def filter_scenario_weights_as_dicts(
        self,
        activated_scenarios: ScenarioInput,
        *,
        profile: FactDict | None = None,
        relation: FactDict | None = None,
        situation: FactDict | None = None,
    ) -> list[FilteredScenarioDict]:
        """
        Возвращает результат перевзвешивания JSON-совместимыми словарями.
        """
        filtered = self.filter_scenario_weights(
            activated_scenarios,
            profile=profile,
            relation=relation,
            situation=situation,
        )
        return [
            {
                SCENARIO_KEY: item.scenario,
                "original_weight": item.original_weight,
                "multiplier": item.multiplier,
                "modified_weight": item.modified_weight,
                "rules": [
                    {
                        "rule_id": activation.rule_id,
                        "strength": activation.strength,
                        "effect": activation.effect,
                        "effect_multiplier": activation.effect_multiplier,
                        "condition_features": list(activation.condition_features),
                    }
                    for activation in item.activations
                ],
            }
            for item in filtered
        ]

    @staticmethod
    def _build_rule_context(*fact_sources: FactDict | None) -> FactDict:
        """
        Собирает профиль, отношение и ситуацию в единый контекст правил.
        """
        merged: FactDict = {}
        for source in fact_sources:
            if source:
                merged.update(source)
        return merged

    @staticmethod
    def _normalize_scenarios(activated_scenarios: ScenarioInput) -> list[tuple[str, float]]:
        """
        Приводит поддерживаемые форматы сценариев к парам имя-вес.
        """
        if isinstance(activated_scenarios, dict):
            if DEFAULT_OUTPUT_KEY in activated_scenarios:
                value = activated_scenarios[DEFAULT_OUTPUT_KEY]
                if not isinstance(value, (list, tuple)):
                    raise TypeError(f"{DEFAULT_OUTPUT_KEY} must be iterable")
                return F2RobotPersonalityFilter._normalize_scenarios(value)

            return [
                (str(scenario), _checked_float(weight))
                for scenario, weight in activated_scenarios.items()
            ]

        normalized: list[tuple[str, float]] = []
        for item in activated_scenarios:
            if not isinstance(item, dict):
                raise TypeError("Each scenario item must be a mapping")

            scenario = item.get(SCENARIO_KEY)
            if not isinstance(scenario, str) or not scenario:
                raise ValueError("Scenario item must contain a non-empty scenario")

            if WEIGHT_KEY in item:
                weight = item[WEIGHT_KEY]
            elif PROXIMITY_KEY in item:
                weight = item[PROXIMITY_KEY]
            else:
                raise ValueError("Scenario item must contain weight or proximity")

            normalized.append((scenario, _checked_float(weight)))

        return normalized


def _checked_float(value: str | int | float) -> float:
    """
    Проверяет значение через check_float и приводит его к float.
    """
    if isinstance(value, bool) or not check_float(str(value)):
        raise TypeError(f"Expected a numeric value, got {type(value).__name__}")
    return float(value)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """
    Ограничивает число заданным закрытым диапазоном.
    """
    if minimum > maximum:
        raise ValueError("minimum must not be greater than maximum")
    return min(max(value, minimum), maximum)
