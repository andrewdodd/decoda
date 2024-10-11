copy-convert-from-pretty_j1939:
	#git submodule update --remote --merge
	#(python ./fix_pretty_create_file.py < ./submodules/pretty_j1939/create_j1939db-json.py)  > src/decoda/sae_spec_converter/create_j1939db_json.py

format:
	black --extend-exclude=submodules src tests setup.py demo.py
	isort --extend-skip=submodules .
	python format_json.py extract.json

lint:
	python -m mypy src tests

test:
	pytest

all: copy-convert-from-pretty_j1939 format test lint

clean: 
	rm -rf dist

check_build_deps:
	@bash check_build_deps.sh

build: check_build_deps clean all
	rm -rf build dist
	python -m build .
