PYTHON="$(CURDIR)/.venv/bin/python"

install:
	python -m venv .venv
	.venv/bin/pip install -r requirements.txt

task1:
	cd bat_stigmergy_swarm && $(PYTHON) -m src.main 1

task2:
	cd bat_stigmergy_swarm && $(PYTHON) -m src.main 2

all-gifs:
	cd bat_stigmergy_swarm && $(PYTHON) -m src.run_all_gifs

batch1:
	cd bat_stigmergy_swarm && $(PYTHON) -m src.task1_batch --n-seeds $(or $(N),10)

batch2:
	cd bat_stigmergy_swarm && $(PYTHON) -m src.task2_batch

analyze:
	cd bat_stigmergy_swarm && $(PYTHON) -m src.analyze_results

run-all: batch1 batch2 analyze
