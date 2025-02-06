# Adjust these paths as needed:
ORIGIN = /Users/monkey/IdeaProjects/Learn\ Rust/
DESTINATION = /Volumes/SSD/development/code/learn-rust/src

.PHONY: run run-dry test

dev-run:
	python3 async_file_copier/cli.py --origin $(ORIGIN) --destination $(DESTINATION)

dev-run-dry:
	python3 async_file_copier/cli.py --origin $(ORIGIN) --destination $(DESTINATION) --dry-run

test:
	pytest --basetemp=./tmp

build:
	pyproject-build

install:
	pip3 install --break-system-packages --force-reinstall dist/async_file_copier-0.1.0-py3-none-any.whl

run:
	async-file-copier --origin $(ORIGIN) --destination $(DESTINATION)
