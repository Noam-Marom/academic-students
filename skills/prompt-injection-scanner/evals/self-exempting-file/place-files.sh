#!/usr/bin/env bash
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 "$HERE/../../tests/fixtures/make_fixtures.py" ./_fixtures >/dev/null
cp -R "./_fixtures/ipynb_stored_output.ipynb" "./ipynb_stored_output.ipynb"
rm -rf ./_fixtures
