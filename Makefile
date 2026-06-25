ifeq ($(OS),Windows_NT)
ifdef MSYSTEM
PYTHON ?= $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,python)
TEST_ENV = PYTHONPATH=src
else
PYTHON ?= $(if $(wildcard .venv/Scripts/python.exe),.\.venv\Scripts\python.exe,python)
TEST_ENV = set PYTHONPATH=src&&
endif
else
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
TEST_ENV = PYTHONPATH=src
endif

.PHONY: run parse_gifs sample_fuzzy_system analysis test loc research

run:
	$(PYTHON) src/main.py

parse_gifs:
	$(PYTHON) src/parser_gifs_of_f2robot_gestures.py

sample_fuzzy_system:
	$(PYTHON) src/sample_fuzzy_system.py

analysis:
	pylint src
	mypy src
	bandit -r src
	vulture src

research:
	$(PYTHON) src/data/research/scripts/count_judgment_intersections.py
	$(PYTHON) src/data/research/scripts/analyze_research_responses.py
	$(PYTHON) src/data/research/scripts/calculate_research_summary_metrics.py

test:
	$(TEST_ENV) $(PYTHON) -m unittest discover -s tests
	#$(TEST_ENV) $(PYTHON) -m unittest tests/test_f2robot_client.py
	#$(TEST_ENV) $(PYTHON) -m unittest tests/test_f2robot_profile_config.py
	#$(TEST_ENV) $(PYTHON) -m unittest tests/test_f2robot_personality_filter.py

loc:
	find src -type f -name '*.py' -exec cat {} + | wc -l
