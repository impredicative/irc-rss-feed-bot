.PHONY: help build build-hostnet clean compile fmt install install-py prep push setup setup-ppa setup-venv test

help:
	@echo "build         : Build, tag, and list Docker image."
	@echo "build-hostnet : Build, tag, and list Docker image using the host network. This can be relevant in a virtual machine."
	@echo "clean         : Remove auto-created files and directories."
	@echo "compile       : Compile required third-party Python packages."
	@echo "fmt           : Autoformat Python code in-place using various tools in sequence."
	@echo "install       : Install required third-party Python packages."
	@echo "install-py    : Install Python."
	@echo "prep          : Autoformat and run tests."
	@echo "push          : Push tagged Docker image to Docker Hub (requires prior Docker login)"
	@echo "setup         : Install third-party Python package requirements and run tests."
	@echo "setup-ppa     : Add deadsnakes PPA on Ubuntu to subsequently install Python."
	@echo "setup-venv    : Create a Python virtual environment."
	@echo "test          : Run tests."

build:
	#docker build -t "${PWD##*/}" .
	docker build -t irc-rss-feed-bot -t ascensive/irc-rss-feed-bot .
	docker images

build-hostnet:
	docker build --network host -t irc-rss-feed-bot -t ascensive/irc-rss-feed-bot .
	docker images

clean:
	rm -rf ./.*_cache

compile:
	pip install -U pip
	pip install -U pip-tools
	pip-compile -U --resolver=backtracking

fmt:
	isort .
	black .

install:
	pip install -U pip wheel
	pip install -U -r ./requirements.txt
	pip install -U -r ./requirements-dev.in

install-py:
	sudo apt install python3.11-full

prep: fmt test

push:
	docker push ascensive/irc-rss-feed-bot

setup: install test

setup-ppa:
	sudo add-apt-repository ppa:deadsnakes/ppa

setup-venv:
	python3.11 -m venv ./venv

test:
	isort --check-only .
	black --check .
	mypy .
	pycodestyle
	pydocstyle
	pylint .
