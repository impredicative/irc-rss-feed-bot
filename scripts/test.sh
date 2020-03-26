#!/usr/bin/env bash
# Run static analysis checks and unit tests using various tools in sequence.
# If an command returns non-zero, any remaining commands are skipped.
set -euxo pipefail
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "${DIR}"/..

black --check .  # This is done separately from pytest because pytest-black==0.3.7 is incompatible with black==19.10b0
pytest -v
