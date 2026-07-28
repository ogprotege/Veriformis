# src/veriformis/errors.py
"""Typed errors shared by every surface (CLI, MCP, GUI)."""
from __future__ import annotations


class VeriformisError(Exception):
    code = "veriformis-error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ParseError(VeriformisError):
    code = "parse-error"


class UnsupportedInputError(VeriformisError):
    code = "unsupported-input"


class RuleError(VeriformisError):
    code = "rule-error"


class GateFailure(VeriformisError):
    code = "gate-failure"
