copy-covert-from-pretty_j1939:
	git submodule update --remote --merge
	(python ./fix_pretty_create_file.py < ./docs/pretty_j1939/create_j1939db-json.py)  > src/decoda/sae_spec_converter/create_j1939db_json.py

format:
	black --extend-exclude=submodules src tests setup.py demo.py
	isort --extend-skip=submodules .
	python format_json.py extract.json

lint:
	python -m mypy src tests

test:
	pytest

all: copy-covert-from-pretty_j1939 format test lint

clean: 
	rm -rf dist

build: clean all
	python setup.py sdist
