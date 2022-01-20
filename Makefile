.PHONY: help build build-v clean compile fmt install prep setup test

help:
	@echo "build  : Build Docker image."
	@echo "build-v: Build Docker image using the host network, as can be relevant in a virtual machine."
	@echo "clean  : Remove auto-created files and directories."
	@echo "compile: Compile required third-party Python packages."
	@echo "fmt    : Autoformat Python code in-place using various tools in sequence."
	@echo "install: Install required third-party Python packages."
	@echo "prep   : Autoformat and run tests."
	@echo "setup  : Install requirements and run tests."
	@echo "test   : Run tests."

build:
	#docker build -t "${PWD##*/}" .
	docker build -t irc-rss-feed-bot .

build-v:
	docker build --network host -t irc-rss-feed-bot .

clean:
	rm -rf ./.*_cache

compile:
	pip-compile -U

fmt:
	isort .
	black .
	autopep8 --in-place --aggressive --recursive .

install:
	pip install -U pip wheel
	pip install -U -r ./requirements.txt -U -r ./requirements-dev.in

prep: fmt test

setup: install test

test:
	black --check .
	pytest
