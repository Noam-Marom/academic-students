#!/usr/bin/env bash
# Copy this case's files/ into the run directory (cwd under `claude plugin eval --scaffold`, or $1 when given).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dest="${1:-$PWD}"
cp -R "$here/files/." "$dest/"
