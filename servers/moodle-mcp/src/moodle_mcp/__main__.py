"""`python -m moodle_mcp` — same as the `moodle-mcp` command (serve by default)."""
from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
