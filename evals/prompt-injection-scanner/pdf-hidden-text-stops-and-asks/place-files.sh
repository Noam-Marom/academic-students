#!/usr/bin/env bash
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 "$HERE/../../tests/fixtures/make_fixtures.py" ./_fixtures >/dev/null
cp -R "./_fixtures/pdf_white_text.pdf" "./pdf_white_text.pdf"
rm -rf ./_fixtures
