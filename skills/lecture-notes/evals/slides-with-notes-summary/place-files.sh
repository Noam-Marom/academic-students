#!/usr/bin/env bash
# Copy files/ into the run directory and build lecture5.pptx from build_deck.py (no binary fixture in git).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dest="${1:-$PWD}"
cp -R "$here/files/." "$dest/"
python3 -I "$here/build_deck.py" "$dest/lecture5.pptx"
