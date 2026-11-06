#!/usr/bin/env bash
# Copy the synthetic synced course folder into the eval's run directory.
set -euo pipefail
cp -R "$(dirname "$0")/files/." "${1:-.}/"
