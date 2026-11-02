#!/usr/bin/env bash
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 "$HERE/../../tests/fixtures/make_fixtures.py" ./_fixtures >/dev/null
cp -R "./_fixtures/hebrew_injection_docx.docx" "./hebrew_injection_docx.docx"
rm -rf ./_fixtures
