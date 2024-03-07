"""
hosteria/cli/completion.py - Completion placeholders
"""
from dataclasses import dataclass


@dataclass
class Completion:
    """
    Acts as a placeholder for a possible completion. When completing, the
    ``display`` will be shown in the list. When completed, the ``value`` will
    be inserted.
    """
    value: str
    display: str
