#!/usr/bin/env bash
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 "$HERE/../../../skills/prompt-injection-scanner/tests/fixtures/make_fixtures.py" ./_fixtures >/dev/null
cp -R "./_fixtures/semantic_no_keyword.md" "./semantic_no_keyword.md"
rm -rf ./_fixtures
