import unittest
from dataclasses import dataclass

from scenario_mind_map import _wrap_scenario_name, normalize_scenarios


@dataclass(frozen=True)
class ScenarioObject:
    scenario: str
    modified_weight: float


class ScenarioMindMapTestCase(unittest.TestCase):
    def test_uses_modified_weight_first_and_sorts_descending(self) -> None:
        items = normalize_scenarios(
            [
                {"scenario": "low", "weight": 0.9, "modified_weight": 0.2},
                {"scenario": "high", "modified_weight": 0.8},
            ]
        )

        self.assertEqual([item.name for item in items], ["high", "low"])
        self.assertAlmostEqual(items[0].weight, 0.8)
        self.assertAlmostEqual(items[1].weight, 0.2)

    def test_accepts_mapping_api_result_and_objects(self) -> None:
        from_api = normalize_scenarios(
            {"scenario_proximities": [{"scenario": "api", "proximity": 0.4}]}
        )
        from_objects = normalize_scenarios([ScenarioObject("object", 0.7)])

        self.assertEqual(from_api[0].name, "api")
        self.assertAlmostEqual(from_api[0].weight, 0.4)
        self.assertEqual(from_objects[0].name, "object")
        self.assertAlmostEqual(from_objects[0].weight, 0.7)

    def test_merges_duplicate_scenarios_by_max_weight(self) -> None:
        items = normalize_scenarios(
            [
                {"scenario": "same", "modified_weight": 0.3},
                {"scenario": "same", "modified_weight": 0.6},
            ]
        )

        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0].weight, 0.6)

    def test_wraps_long_hyphenated_scenario_names_predictably(self) -> None:
        wrapped = _wrap_scenario_name(
            "я-попал-в-необычное-место-райза",
            max_chars=12,
            max_lines=4,
        )

        lines = wrapped.splitlines()
        self.assertLessEqual(len(lines), 4)
        self.assertTrue(all(line and not line.endswith("-") for line in lines))


if __name__ == "__main__":
    unittest.main()
