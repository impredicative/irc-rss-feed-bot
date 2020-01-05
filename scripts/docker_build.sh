#!/usr/bin/env bash
# This script builds a containerized image. It can be run locally or in a remote CI workflow.
set -euxo pipefail
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "${DIR}"/..

BASEDIR="${PWD##*/}"
IMAGE_NAME="${BASEDIR}"

docker build -t "${IMAGE_NAME}" .
docker images
