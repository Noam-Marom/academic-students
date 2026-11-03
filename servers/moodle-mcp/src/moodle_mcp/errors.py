"""Exceptions raised by the Moodle client.

Moodle answers most failures with HTTP 200 and a JSON body carrying `errorcode`; those become
`MoodleError`. The two codes that mean "your token is dead" (`invalidtoken`, expired →
`accessexception`) become `AuthError`, whose message tells the student how to log in again.
Anything that is not a Moodle-shaped answer (HTTP ≥ 400, non-JSON, network) is a `TransportError`.
"""
from __future__ import annotations


class MoodleError(Exception):
    """A Moodle web-service error: `errorcode` plus the (token-stripped) message."""

    def __init__(self, errorcode: str, message: str = ""):
        self.errorcode = errorcode
        self.message = message or errorcode
        super().__init__(f"{errorcode}: {self.message}" if message else errorcode)


class AuthError(MoodleError):
    """The token is invalid or expired; re-authenticate with `moodle-mcp login <site>`."""


class TransportError(Exception):
    """HTTP ≥ 400, a non-JSON body, or a network failure."""
