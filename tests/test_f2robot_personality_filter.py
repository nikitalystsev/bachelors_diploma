import unittest
from types import SimpleNamespace

from f2robot_personality_filter import (
    Condition,
    FilterRule,
    FuzzyTermSpec,
    FuzzyVariableSpec,
    F2RobotPersonalityFilter,
    terms,
)


def test_variable(
    feature: str,
    term_1: str,
    term_2: str,
    term_3: str,
    term_4: str,
) -> FuzzyVariableSpec:
    """Создает стандартную нечеткую переменную с четырьмя термами."""
    return FuzzyVariableSpec(
        feature=feature,
        terms=(
            FuzzyTermSpec.trapezoid(term_1, 0.0, 0.0, 0.15, 0.30),
            FuzzyTermSpec.triangle(term_2, 0.15, 0.30, 0.50),
            FuzzyTermSpec.triangle(term_3, 0.35, 0.55, 0.85),
            FuzzyTermSpec.trapezoid(term_4, 0.65, 0.85, 1.0, 1.0),
        ),
        universe=(0.0, 1.0),
    )


TEST_FUZZY_VARIABLES = (
    FuzzyVariableSpec(
        feature="message_valence",
        terms=(
            FuzzyTermSpec.trapezoid("negative", -1.0, -1.0, -0.60, -0.20),
            FuzzyTermSpec.trapezoid("neutral", -0.50, -0.20, 0.20, 0.50),
            FuzzyTermSpec.trapezoid("positive", 0.20, 0.60, 1.0, 1.0),
        ),
        universe=(-1.0, 1.0),
    ),
    test_variable("command", "none", "soft", "demand", "coercive"),
    test_variable(
        "boundary_violation",
        "none",
        "weak",
        "clear",
        "strong",
    ),
    test_variable("threat", "none", "potential", "direct", "severe"),
    test_variable(
        "criticism",
        "none",
        "mild",
        "direct",
        "humiliating",
    ),
    test_variable(
        "norm_violation",
        "none",
        "minor",
        "clear",
        "gross",
    ),
)


TEST_EFFECT_MULTIPLIERS = {
    "strong_decrease": 0.50,
    "decrease": 0.75,
    "no_change": 1.00,
    "increase": 1.25,
    "strong_increase": 1.50,
}


def filter_for_test(
    rules: tuple[FilterRule, ...],
    fuzzy_variables: tuple[FuzzyVariableSpec, ...] = (),
) -> F2RobotPersonalityFilter:
    """Создает фильтр с минимальной тестовой конфигурацией в памяти."""
    return F2RobotPersonalityFilter(
        SimpleNamespace(
            profile_config={
                "profile_id": "test_profile",
                "label": "Test profile",
                "traits": {
                    "test_trait": {
                        "value": "test_value",
                        "label": "test value",
                    }
                },
            },
            trait_labels_config={"labels": {"test_trait": "Test trait"}},
            relation_config={"parameters": []},
            situation_config={
                "parameters": [
                    {
                        "feature": variable.feature,
                        "label": variable.feature,
                        "input": "slider",
                        "default": variable.universe[0],
                        "minimum": variable.universe[0],
                        "maximum": variable.universe[1],
                        "fuzzy_terms": [
                            {
                                "term": term.term,
                                "label": term.term,
                                "function_type": term.function_type,
                                "points": list(term.points),
                            }
                            for term in variable.terms
                        ],
                    }
                    for variable in fuzzy_variables
                ]
            },
            rule_effects_config={
                "multipliers": TEST_EFFECT_MULTIPLIERS,
                "labels": {effect: effect for effect in TEST_EFFECT_MULTIPLIERS},
            },
            rules_config={
                "rules": [
                    {
                        "rule_id": rule.rule_id,
                        "conditions": [
                            {
                                "feature": condition.feature,
                                "terms": list(condition.terms),
                            }
                            for condition in rule.conditions
                        ],
                        "target_scenarios": list(rule.target_scenarios),
                        "effect": rule.effect,
                    }
                    for rule in rules
                ]
            },
        )
    )


class F2RobotPersonalityFilterTestCase(unittest.TestCase):
    """Проверяет фаззификацию и пересчет весов сценариев фильтром."""

    def test_rejects_rules_without_conditions(self) -> None:
        """Проверяет отклонение правил без условий."""
        rule = FilterRule(
            rule_id="R_without_conditions",
            conditions=(),
            target_scenarios=("scenario",),
            effect="increase",
        )

        with self.assertRaisesRegex(ValueError, "at least one condition"):
            filter_for_test((rule,))

    def test_fuzzifies_numeric_situation_features_with_design_scales(self) -> None:
        """Проверяет преобразование числовых признаков ситуации в термы."""
        expected_memberships = {
            ("message_valence", "negative"): 1.0,
            ("command", "demand"): 0.1,
            ("command", "coercive"): 0.85,
            ("boundary_violation", "clear"): 0.2333333333,
            ("boundary_violation", "strong"): 0.65,
            ("threat", "direct"): 0.05,
            ("criticism", "direct"): 0.45,
            ("norm_violation", "gross"): 0.45,
        }
        scenario_by_membership = {
            (feature, term): f"scenario_{membership}"
            for membership, (feature, term) in enumerate(expected_memberships, start=1)
        }
        rules = tuple(
            FilterRule(
                rule_id=f"R_{feature}_{term}",
                conditions=(Condition(feature, terms(term)),),
                target_scenarios=(scenario_by_membership[(feature, term)],),
                effect="increase",
            )
            for feature, term in expected_memberships
        )
        filtered = filter_for_test(rules, TEST_FUZZY_VARIABLES).filter_scenario_weights(
            {scenario: 0.5 for scenario in scenario_by_membership.values()},
            situation={
                "message_valence": -0.72,
                "command": 0.82,
                "boundary_violation": 0.78,
                "threat": 0.36,
                "criticism": 0.44,
                "norm_violation": 0.74,
            },
        )
        by_scenario = {item.scenario: item for item in filtered}

        for membership, expected in expected_memberships.items():
            scenario = scenario_by_membership[membership]
            self.assertAlmostEqual(
                by_scenario[scenario].activations[0].strength,
                expected,
            )

    def test_accepts_numeric_relation_features(self) -> None:
        """Проверяет фаззификацию числовых признаков отношений."""
        trust_level_variable = FuzzyVariableSpec(
            feature="trust_level",
            terms=(
                FuzzyTermSpec.trapezoid("distrust", 0.0, 0.0, 0.2, 0.4),
                FuzzyTermSpec.triangle("cautious", 0.2, 0.5, 0.8),
                FuzzyTermSpec.trapezoid("confident", 0.6, 0.8, 1.0, 1.0),
            ),
            universe=(0.0, 1.0),
        )
        rules = (
            FilterRule(
                rule_id="R_numeric_relation",
                conditions=(Condition("trust_level", terms("cautious")),),
                target_scenarios=("scenario_care_from_f2",),
                effect="increase",
            ),
        )

        filtered = filter_for_test(
            rules,
            (trust_level_variable,),
        ).filter_scenario_weights(
            {"scenario_care_from_f2": 0.4},
            relation={"trust_level": 0.35},
        )

        self.assertAlmostEqual(filtered[0].activations[0].strength, 0.5)
        self.assertAlmostEqual(filtered[0].multiplier, 1.25)
        self.assertAlmostEqual(filtered[0].modified_weight, 0.5)

    def test_aggregates_multiple_rules_for_same_arbitrary_scenario(self) -> None:
        """Проверяет объединение нескольких срабатываний для одного сценария."""
        rules = (
            FilterRule(
                rule_id="R_command",
                conditions=(Condition("command", terms("demand", "coercive")),),
                target_scenarios=("@some_f2_scenario_name",),
                effect="increase",
            ),
            FilterRule(
                rule_id="R_operator",
                conditions=(Condition("instruction_right", terms("operator_command")),),
                target_scenarios=("@some_f2_scenario_name",),
                effect="decrease",
            ),
        )

        filtered = filter_for_test(
            rules,
            TEST_FUZZY_VARIABLES,
        ).filter_scenario_weights(
            {"@some_f2_scenario_name": 0.8},
            relation={"instruction_right": "operator_command"},
            situation={"command": 0.82},
        )

        self.assertAlmostEqual(
            filtered[0].multiplier,
            (0.85 * 1.25 + 1.0 * 0.75) / (0.85 + 1.0),
        )

    def test_uses_proximity_as_input_scenario_weight(self) -> None:
        """Проверяет использование proximity как исходного веса сценария."""
        filtered = filter_for_test(()).filter_scenario_weights(
            [{"scenario": "actual_scenario_name_from_api", "proximity": 0.4}],
        )

        self.assertAlmostEqual(filtered[0].original_weight, 0.4)
        self.assertAlmostEqual(filtered[0].multiplier, 1.0)
        self.assertAlmostEqual(filtered[0].modified_weight, 0.4)

if __name__ == "__main__":
    unittest.main()
