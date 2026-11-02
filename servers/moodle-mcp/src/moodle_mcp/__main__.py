"""`python -m moodle_mcp` — run the MCP server over stdio."""
from __future__ import annotations

import sys

from .server import serve

if __name__ == "__main__":
    sys.exit(serve())
