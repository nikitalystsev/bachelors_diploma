"""Минимальный пример Sugeno-вывода с использованием Simpful."""

import simpful as sf

# A simple fuzzy model describing how burner power depends on oxygen supply.

FS = sf.FuzzySystem(show_banner=False)

# Define a linguistic variable.
S_1 = sf.FuzzySet(points=[[0, 1.0], [1.0, 1.0], [1.5, 0]], term="low_flow")
S_2 = sf.FuzzySet(
    points=[[0.5, 0], [1.5, 1.0], [2.5, 1], [3.0, 0]],
    term="medium_flow",
)
S_3 = sf.FuzzySet(points=[[2.0, 0], [2.5, 1.0], [3.0, 1.0]], term="high_flow")
FS.add_linguistic_variable("OXI", sf.LinguisticVariable([S_1, S_2, S_3]))

# Define consequents.
FS.set_crisp_output_value("LOW_POWER", 0)
FS.set_crisp_output_value("MEDIUM_POWER", 25)
FS.set_output_function("HIGH_FUN", "OXI**2")

# Define fuzzy rules.
RULE1 = "IF (OXI IS low_flow) THEN (POWER IS LOW_POWER)"
RULE2 = "IF (OXI IS medium_flow) THEN (POWER IS MEDIUM_POWER)"
RULE3 = "IF (NOT (OXI IS low_flow)) THEN (POWER IS HIGH_FUN)"
FS.add_rules([RULE1, RULE2, RULE3])

# Set antecedents values, perform Sugeno inference and print output values.
FS.set_variable("OXI", 0.51)
print(FS.Sugeno_inference(["POWER"]))
