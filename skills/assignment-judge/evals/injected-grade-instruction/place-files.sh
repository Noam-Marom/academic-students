#!/usr/bin/env bash
# Copies this case's files/ into the run directory (first argument, default: current directory).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="${1:-$PWD}"
cp -R "$here/files/." "$dest/"
