"""moodle-mcp: a read-only MCP server over Moodle Web Services.

Login happens in a terminal (`moodle-mcp login <site>`); only the token is kept, in the OS keychain.
The password never passes through Claude, and no function that writes to Moodle is ever called.
"""

__version__ = "0.1.0"
