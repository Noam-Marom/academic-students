#!/usr/bin/env bash
# Copies this case's files/ into the run directory (first argument, default: current directory).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="${1:-$PWD}"
cp -R "$here/files/." "$dest/"
# Rasterise the synthetic "scan" when a converter is available (no binaries are committed).
if command -v rsvg-convert >/dev/null 2>&1; then rsvg-convert "$dest/solution-scan.svg" -o "$dest/solution-scan.png"
elif command -v magick >/dev/null 2>&1; then magick "$dest/solution-scan.svg" "$dest/solution-scan.png"
elif command -v convert >/dev/null 2>&1; then convert "$dest/solution-scan.svg" "$dest/solution-scan.png"
fi
