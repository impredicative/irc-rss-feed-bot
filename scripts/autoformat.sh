#!/usr/bin/env bash
# Autoformat Python code in-place using various tools in sequence.
set -euxo pipefail
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "${DIR}"/..

isort --apply
black .
autopep8 --in-place --aggressive --recursive .
